#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import pathlib
import sys
import unicodedata
from collections import Counter


DANGEROUS_READING_SUFFIXES = (
    "したい",
    "について",
    "において",
    "によって",
    "として",
    "ように",
    "ために",
    "られる",
    "ました",
    "ません",
    "たい",
    "ない",
    "ます",
    "てる",
    "でる",
    "れる",
    "のに",
)


@dataclasses.dataclass(frozen=True)
class Entry:
    path: pathlib.Path
    line_number: int
    key: str
    lid: int
    rid: int
    cost: int
    value: str


@dataclasses.dataclass(frozen=True)
class Candidate:
    entry: Entry
    suffix: str
    shape: str
    left_pos: str
    right_pos: str
    reason: str


def repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def is_hiragana(ch: str) -> bool:
    return "\u3040" <= ch <= "\u309f"


def is_katakana(ch: str) -> bool:
    return (
        "\u30a0" <= ch <= "\u30ff"
        or "\uff66" <= ch <= "\uff9f"
    )


def is_kanji(ch: str) -> bool:
    return (
        "\u3400" <= ch <= "\u4dbf"
        or "\u4e00" <= ch <= "\u9fff"
        or "\uf900" <= ch <= "\ufaff"
        or ch in "々〆ヶ"
    )


def is_ascii_alnum(ch: str) -> bool:
    return ord(ch) < 128 and ch.isalnum()


def has_hiragana(text: str) -> bool:
    return any(is_hiragana(ch) for ch in text)


def has_katakana(text: str) -> bool:
    return any(is_katakana(ch) for ch in text)


def has_kanji(text: str) -> bool:
    return any(is_kanji(ch) for ch in text)


def is_katakana_like(text: str) -> bool:
    if not text:
        return False

    allowed = set("・ー")
    visible = False

    for ch in text:
        if ch.isspace():
            continue

        visible = True

        if is_katakana(ch):
            continue

        if ch in allowed:
            continue

        return False

    return visible


def is_kanji_or_katakana_without_hiragana(text: str) -> bool:
    if not text:
        return False

    if has_hiragana(text):
        return False

    return has_kanji(text) or has_katakana(text)


def value_shape(value: str) -> str:
    if has_hiragana(value):
        return "has_hiragana"

    if has_kanji(value) and has_katakana(value):
        return "kanji_katakana_no_hiragana"

    if has_kanji(value):
        return "kanji_no_hiragana"

    if is_katakana_like(value):
        return "katakana_only"

    if all(is_ascii_alnum(ch) or ch.isspace() for ch in value):
        return "ascii_alnum"

    return "other"


def normalize_for_compare(text: str) -> str:
    return unicodedata.normalize("NFKC", text).strip()


def load_pos_names(id_def: pathlib.Path) -> dict[int, str]:
    pos_names: dict[int, str] = {}

    if not id_def.exists():
        return pos_names

    with id_def.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            try:
                pos_id = int(parts[0])
            except ValueError:
                continue

            pos_names[pos_id] = " ".join(parts[1:])

    return pos_names


def pos_name(pos_names: dict[int, str], pos_id: int) -> str:
    return pos_names.get(pos_id, "")


def is_noun_like(entry: Entry, pos_names: dict[int, str]) -> bool:
    left = pos_name(pos_names, entry.lid)
    right = pos_name(pos_names, entry.rid)

    # If id.def parsing failed or this id is unknown, do not drop the entry.
    # This tool is diagnostic; false negatives are worse than extra candidates.
    if not left and not right:
        return True

    return "名詞" in left or "名詞" in right


def dangerous_suffix_for_key(key: str) -> str | None:
    for suffix in DANGEROUS_READING_SUFFIXES:
        if key.endswith(suffix) and len(key) >= len(suffix) + 2:
            return suffix

    return None


def parse_entry(path: pathlib.Path, line_number: int, line: str) -> Entry | None:
    cols = line.rstrip("\n\r").split("\t")
    if len(cols) != 5:
        return None

    key, lid_text, rid_text, cost_text, value = cols

    try:
        return Entry(
            path=path,
            line_number=line_number,
            key=key,
            lid=int(lid_text),
            rid=int(rid_text),
            cost=int(cost_text),
            value=value,
        )
    except ValueError:
        return None


def should_skip_obvious_grammar_like(entry: Entry) -> bool:
    # Natural grammar/conjugation entries usually contain hiragana in value:
    #   行きたい
    #   愛してる
    #   ありがとうございます
    # These should not be treated as suspicious noun collisions.
    if has_hiragana(entry.value):
        return True

    # Same-reading kana/katakana style entries are often intentionally included.
    # Do not skip all katakana here; pure katakana is handled by --include-katakana.
    if normalize_for_compare(entry.key) == normalize_for_compare(entry.value):
        return True

    return False


def classify_candidate(
    entry: Entry,
    pos_names: dict[int, str],
    include_katakana: bool,
    require_noun_like: bool,
) -> Candidate | None:
    suffix = dangerous_suffix_for_key(entry.key)
    if suffix is None:
        return None

    if should_skip_obvious_grammar_like(entry):
        return None

    if require_noun_like and not is_noun_like(entry, pos_names):
        return None

    shape = value_shape(entry.value)

    if shape in {"kanji_no_hiragana", "kanji_katakana_no_hiragana"}:
        reason = "kanji-like value with syntax-like reading"
    elif shape == "katakana_only":
        if not include_katakana:
            return None
        reason = "katakana value with syntax-like reading"
    else:
        return None

    return Candidate(
        entry=entry,
        suffix=suffix,
        shape=shape,
        left_pos=pos_name(pos_names, entry.lid),
        right_pos=pos_name(pos_names, entry.rid),
        reason=reason,
    )


def default_dictionary_paths(root: pathlib.Path, include_bazel_bin: bool) -> list[pathlib.Path]:
    paths: list[pathlib.Path] = []

    dictionary_oss = root / "src" / "data" / "dictionary_oss"
    paths.extend(sorted(dictionary_oss.glob("dictionary[0-9][0-9].txt")))

    if include_bazel_bin:
        bazel_dictionary = root / "src" / "bazel-bin" / "data" / "dictionary_oss" / "dictionary.txt"
        if bazel_dictionary.exists():
            paths.append(bazel_dictionary)

    return paths


def scan(
    paths: list[pathlib.Path],
    pos_names: dict[int, str],
    max_cost: int,
    limit: int,
    include_katakana: bool,
    require_noun_like: bool,
    output_tsv: pathlib.Path | None,
) -> int:
    found = 0
    suffix_counter = Counter()
    shape_counter = Counter()
    path_counter = Counter()

    out = None
    if output_tsv is not None:
        output_tsv.parent.mkdir(parents=True, exist_ok=True)
        out = output_tsv.open("w", encoding="utf-8", newline="\n")
        out.write(
            "path\tline\tkey\tlid\trid\tcost\tvalue\tsuffix\tshape\tleft_pos\tright_pos\treason\n"
        )

    try:
        for path in paths:
            if not path.exists():
                print(f"warning: path does not exist: {path}", file=sys.stderr)
                continue

            with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
                for line_number, line in enumerate(f, start=1):
                    entry = parse_entry(path, line_number, line)
                    if entry is None:
                        continue

                    if entry.cost > max_cost:
                        continue

                    candidate = classify_candidate(
                        entry=entry,
                        pos_names=pos_names,
                        include_katakana=include_katakana,
                        require_noun_like=require_noun_like,
                    )
                    if candidate is None:
                        continue

                    found += 1
                    suffix_counter[candidate.suffix] += 1
                    shape_counter[candidate.shape] += 1
                    path_counter[str(candidate.entry.path)] += 1

                    if out is not None:
                        e = candidate.entry
                        out.write(
                            f"{e.path}\t{e.line_number}\t{e.key}\t{e.lid}\t{e.rid}\t"
                            f"{e.cost}\t{e.value}\t{candidate.suffix}\t{candidate.shape}\t"
                            f"{candidate.left_pos}\t{candidate.right_pos}\t{candidate.reason}\n"
                        )

                    if found <= limit:
                        e = candidate.entry
                        print(f"{e.path}:{e.line_number}")
                        print(f"  {e.key}\t{e.lid}\t{e.rid}\t{e.cost}\t{e.value}")
                        print(f"  suffix: {candidate.suffix}")
                        print(f"  shape:  {candidate.shape}")
                        print(f"  L-POS:  {candidate.left_pos}")
                        print(f"  R-POS:  {candidate.right_pos}")
                        print(f"  reason: {candidate.reason}")

        print("")
        print("Summary:")
        print(f"  found: {found}")
        print(f"  max_cost: {max_cost}")
        print(f"  include_katakana: {include_katakana}")
        print(f"  require_noun_like: {require_noun_like}")

        print("")
        print("By suffix:")
        for key, count in suffix_counter.most_common():
            print(f"  {key}: {count}")

        print("")
        print("By shape:")
        for key, count in shape_counter.most_common():
            print(f"  {key}: {count}")

        print("")
        print("By path:")
        for key, count in path_counter.most_common():
            print(f"  {key}: {count}")

        if found > limit:
            print("")
            print(f"Printed first {limit} candidates. Total candidates: {found}")

        if output_tsv is not None:
            print("")
            print(f"Wrote TSV: {output_tsv}")

    finally:
        if out is not None:
            out.close()

    return 0


def main() -> int:
    root = repo_root()

    parser = argparse.ArgumentParser(
        description="Scan base dictionaries for noun-like entries whose readings look like ordinary Japanese syntax."
    )
    parser.add_argument(
        "--max-cost",
        type=int,
        default=8500,
        help="Only scan entries with cost <= this value.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=120,
        help="Number of candidates to print. Summary always counts all candidates.",
    )
    parser.add_argument(
        "--include-katakana",
        action="store_true",
        help="Also include pure katakana candidates. This increases false positives.",
    )
    parser.add_argument(
        "--no-require-noun-like",
        action="store_true",
        help="Do not require noun-like POS ids.",
    )
    parser.add_argument(
        "--include-bazel-bin",
        action="store_true",
        help="Also scan src/bazel-bin/data/dictionary_oss/dictionary.txt if it exists.",
    )
    parser.add_argument(
        "--path",
        type=pathlib.Path,
        action="append",
        default=None,
        help="Dictionary path to scan. Can be passed multiple times. Defaults to dictionary00-09.",
    )
    parser.add_argument(
        "--id-def",
        type=pathlib.Path,
        default=root / "src" / "data" / "dictionary_oss" / "id.def",
    )
    parser.add_argument(
        "--output-tsv",
        type=pathlib.Path,
        default=None,
        help="Optional TSV output path for all candidates.",
    )

    args = parser.parse_args()

    pos_names = load_pos_names(args.id_def)

    if args.path:
        paths = args.path
    else:
        paths = default_dictionary_paths(
            root=root,
            include_bazel_bin=args.include_bazel_bin,
        )

    return scan(
        paths=paths,
        pos_names=pos_names,
        max_cost=args.max_cost,
        limit=args.limit,
        include_katakana=args.include_katakana,
        require_noun_like=not args.no_require_noun_like,
        output_tsv=args.output_tsv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
