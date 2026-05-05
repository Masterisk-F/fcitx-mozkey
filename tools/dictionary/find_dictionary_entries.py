#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    source: pathlib.Path
    line_number: int
    key: str
    lid: str
    rid: str
    cost: str
    value: str


def repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def candidate_dictionary_paths(root: pathlib.Path) -> list[pathlib.Path]:
    paths: list[pathlib.Path] = []

    paths.extend(sorted((root / "src" / "data" / "dictionary_oss").glob("dictionary[0-9][0-9].txt")))

    koyasi = root / "src" / "data" / "dictionary_koyasi"

    generated_candidates = [
        koyasi / "generated" / "profiled" / "mozcdic-ut-daily.txt",
        koyasi / "generated" / "profiled" / "dic-nico-pixiv-delta.txt",
        koyasi / "generated" / "profiled" / "mozcdic-ut-rich.txt",
        koyasi / "generated" / "mozcdic-ut-safe.txt",
        koyasi / "sample" / "mozcdic-ut-sample.txt",
    ]

    for path in generated_candidates:
        if path.exists():
            paths.append(path)

    bazel_bin_dictionary = root / "src" / "bazel-bin" / "data" / "dictionary_oss" / "dictionary.txt"
    if bazel_bin_dictionary.exists():
        paths.append(bazel_bin_dictionary)

    return paths


def parse_line(path: pathlib.Path, line_number: int, line: str) -> Entry | None:
    cols = line.rstrip("\n\r").split("\t")
    if len(cols) != 5:
        return None

    return Entry(
        source=path,
        line_number=line_number,
        key=cols[0],
        lid=cols[1],
        rid=cols[2],
        cost=cols[3],
        value=cols[4],
    )


def entry_matches(entry: Entry, key: str | None, value: str | None, contains: str | None) -> bool:
    if key is not None and entry.key != key:
        return False

    if value is not None and entry.value != value:
        return False

    if contains is not None and contains not in entry.key and contains not in entry.value:
        return False

    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", default=None)
    parser.add_argument("--value", default=None)
    parser.add_argument("--contains", default=None)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--path", type=pathlib.Path, action="append", default=None)

    args = parser.parse_args()

    if args.key is None and args.value is None and args.contains is None:
        print("error: specify at least one of --key, --value, --contains", file=sys.stderr)
        return 1

    root = repo_root()
    paths = args.path if args.path else candidate_dictionary_paths(root)

    found = 0

    for path in paths:
        if not path.exists():
            continue

        try:
            f = path.open("r", encoding="utf-8-sig", errors="replace", newline="")
        except OSError as e:
            print(f"warning: failed to open {path}: {e}", file=sys.stderr)
            continue

        with f:
            for line_number, line in enumerate(f, start=1):
                entry = parse_line(path, line_number, line)
                if entry is None:
                    continue

                if not entry_matches(entry, args.key, args.value, args.contains):
                    continue

                found += 1
                print(f"{entry.source}:{entry.line_number}")
                print(f"  {entry.key}\t{entry.lid}\t{entry.rid}\t{entry.cost}\t{entry.value}")

                if found >= args.limit:
                    print(f"limit reached: {args.limit}")
                    return 0

    print(f"found: {found}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
