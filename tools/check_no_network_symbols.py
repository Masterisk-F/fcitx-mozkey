#!/usr/bin/env python3
# Copyright 2026
#
# Fails when obvious runtime networking APIs are introduced into Mozc-owned
# source files.
#
# This is a source-level guard. It intentionally skips generated trees,
# external dependencies, SDK headers, and platform code that is not part of the
# Windows runtime binaries we ship.

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

# Only scan Mozc-owned Windows/runtime-relevant source directories.
# Do not scan src/bazel-src, external repositories, SDK headers, or generated
# Bazel output.
SCAN_ROOTS = [
    SRC_ROOT / "base",
    SRC_ROOT / "config",
    SRC_ROOT / "converter",
    SRC_ROOT / "data_manager",
    SRC_ROOT / "dictionary",
    SRC_ROOT / "engine",
    SRC_ROOT / "gui",
    SRC_ROOT / "prediction",
    SRC_ROOT / "protocol",
    SRC_ROOT / "renderer",
    SRC_ROOT / "rewriter",
    SRC_ROOT / "session",
    SRC_ROOT / "storage",
    SRC_ROOT / "win32",
]

SKIP_DIR_NAMES = {
    ".git",
    ".github",
    "bazel-bin",
    "bazel-out",
    "bazel-testlogs",
    "bazel-src",
    "external",
    "third_party",
    "third_party_cache",
    "data",
    "testing",
    "testdata",
}

TARGET_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".mm",
    ".m",
    ".bzl",
    ".bazel",
}

TARGET_FILENAMES = {
    "BUILD",
    "BUILD.bazel",
}

DENY_PATTERNS = {
    # Windows networking headers and APIs.
    "winhttp.h": "WinHTTP must not be used by Mozc runtime code.",
    "wininet.h": "WinINet must not be used by Mozc runtime code.",
    "winsock.h": "Winsock must not be used by Mozc runtime code.",
    "winsock2.h": "Winsock2 must not be used by Mozc runtime code.",
    "ws2tcpip.h": "Winsock TCP/IP helpers must not be used by Mozc runtime code.",
    "urlmon.h": "URLMon must not be used by Mozc runtime code.",
    "websocket.h": "WebSocket APIs must not be used by Mozc runtime code.",

    "InternetOpen": "WinINet InternetOpen is prohibited.",
    "InternetConnect": "WinINet InternetConnect is prohibited.",
    "HttpOpenRequest": "WinINet HTTP request APIs are prohibited.",
    "HttpSendRequest": "WinINet HTTP send APIs are prohibited.",

    "WinHttpOpen": "WinHTTP APIs are prohibited.",
    "WinHttpConnect": "WinHTTP APIs are prohibited.",
    "WinHttpSendRequest": "WinHTTP send APIs are prohibited.",
    "WinHttpReceiveResponse": "WinHTTP receive APIs are prohibited.",

    "WSAStartup": "Winsock initialization is prohibited.",
    "getaddrinfo": "DNS/network address lookup is prohibited.",
    "gethostbyname": "DNS/network address lookup is prohibited.",

    "URLDownloadToFile": "URL download APIs are prohibited.",
    "URLOpenBlockingStream": "URLMon stream APIs are prohibited.",

    # Qt networking / external URL opening.
    "QNetworkAccessManager": "Qt network access is prohibited.",
    "QNetworkRequest": "Qt network request is prohibited.",
    "QTcpSocket": "Qt TCP socket is prohibited.",
    "QUdpSocket": "Qt UDP socket is prohibited.",
    "QWebSocket": "Qt WebSocket is prohibited.",
    "QDesktopServices::openUrl": "Opening external URLs from Mozc runtime is prohibited.",

    # External networking libraries.
    "libcurl": "libcurl is prohibited.",
    "curl_easy_": "libcurl easy API is prohibited.",
}

# These files mention updater-related words, but they do not by themselves prove
# that the final Mozc runtime binaries can perform network communication.
# The stronger guard is the binary import check after build.
ALLOWLIST: dict[str, set[str]] = {
    "src/base/update_util.cc": {"Omaha"},
    "src/base/update_util.h": {"Omaha"},
    "src/config/stats_config_util.cc": {"Omaha"},
    "src/config/stats_config_util_test.cc": {"Omaha"},
    "src/win32/base/omaha_util.cc": {"Omaha"},
    "src/win32/base/omaha_util.h": {"Omaha"},
    "src/win32/base/omaha_util_test.cc": {"Omaha"},
    "src/win32/custom_action/custom_action.cc": {"Omaha"},
    "src/win32/custom_action/custom_action.h": {"Omaha"},
    "src/win32/tip/tip_text_service.cc": {"Omaha"},
}


def is_under_skipped_dir(path: Path) -> bool:
    rel_parts = path.relative_to(ROOT).parts
    return any(part in SKIP_DIR_NAMES for part in rel_parts)


def is_target_file(path: Path) -> bool:
    return path.suffix in TARGET_SUFFIXES or path.name in TARGET_FILENAMES


def line_number_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def main() -> int:
    violations: list[str] = []

    for scan_root in SCAN_ROOTS:
        if not scan_root.exists():
            continue

        for path in scan_root.rglob("*"):
            if is_under_skipped_dir(path):
                continue

            try:
                if not path.is_file():
                    continue
            except OSError:
                continue

            if not is_target_file(path):
                continue

            rel = path.relative_to(ROOT).as_posix()
            allowed_patterns = ALLOWLIST.get(rel, set())

            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError as e:
                violations.append(f"{rel}: failed to read file: {e}")
                continue

            for pattern, reason in DENY_PATTERNS.items():
                if pattern in allowed_patterns:
                    continue

                index = text.find(pattern)
                if index >= 0:
                    line = line_number_of(text, index)
                    violations.append(
                        f"{rel}:{line}: contains prohibited pattern "
                        f"{pattern!r}. {reason}"
                    )

    if violations:
        print("[NO_NETWORK_SYMBOL_CHECK_FAILED]")
        for violation in violations:
            print(violation)
        return 1

    print("[NO_NETWORK_SYMBOL_CHECK_PASSED]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
