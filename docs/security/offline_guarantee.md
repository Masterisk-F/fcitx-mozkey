# Secure Offline Guarantee

## Goal

This fork is designed to operate as an offline Japanese IME.

Mozc runtime processes should not initiate Internet communication during normal
IME operation.

## Runtime network policy

Mozc runtime binaries must not initiate outbound Internet communication.

This includes:

- cloud conversion
- usage statistics upload
- crash report upload
- auto-update
- online dictionary update
- online suggestion service
- remote configuration fetch
- telemetry
- opening external URLs from Mozc runtime processes

## Local-only design

This fork uses local resources for normal IME operation:

- local system dictionary
- local user dictionary
- local user history
- local settings

Input text is processed locally.

## Usage statistics and crash reports

The usage-statistics and crash-report option inherited from upstream is removed
from the administration and configuration dialogs.

The default `StatsConfigUtil` implementation is fixed to the null implementation
in this fork. Usage statistics cannot be enabled through the normal runtime
path.

## Source checks

Obvious runtime networking APIs are rejected by:

```powershell
python tools\check_no_network_symbols.py
```

## Binary import checks

Windows release binaries should be checked so that Mozc runtime executables do
not import common networking DLLs such as:

- ws2_32.dll
- winhttp.dll
- wininet.dll
- urlmon.dll
- webio.dll
- dnsapi.dll

The check is implemented by:

```powershell
python tools\check_no_network_imports.py --root src\bazel-bin
```

For release validation, the installed or MSI-extracted runtime binaries should
also be checked.

## Binary string checks

Windows release binaries should be checked so that Mozc runtime executables do
not contain hard-deny telemetry, updater, crash-upload, or usage-statistics
markers.

Generic URL-like markers such as `http://`, `https://`, `googleapis.com`, and
protobuf field names such as `usage_stats` are reported for audit. They are not
treated as hard failures by themselves.

The check is implemented by:

```powershell
python tools\check_no_network_strings.py --root src\bazel-bin
```

For release validation, run the same check against installed or MSI-extracted
runtime binaries.

## Windows Firewall hardening

The Windows installer adds outbound Windows Firewall block rules for Mozc
runtime executables as an additional offline hardening layer.

The rules target Mozc executable files such as:

- mozc_server.exe
- mozc_tool.exe
- mozc_renderer.exe
- mozc_broker.exe
- mozc_cache_service.exe

The rules are outbound-only. They are removed during uninstall. Firewall rule
creation and removal are best-effort operations; installation and uninstall do
not fail solely because local policy rejects firewall changes.

The TIP DLL is not managed by a firewall rule because Windows Firewall program
rules are executable-oriented. Instead, TIP DLL network capability is checked by
source, import, and string audits.

## Runtime checks

Before publishing a release, install the MSI in a clean Windows VM and confirm
that no Mozc runtime process initiates outbound communication during normal IME
operation.

Recommended tools:

- Windows Defender Firewall log
- Resource Monitor
- Process Monitor
- pktmon
- Wireshark

## Build-time network access

Building from source may require network access to download build dependencies.

This is separate from runtime behavior of the installed IME.

## Local data protection

Offline operation means that the IME does not send input data to external
servers.

Local data protection is a separate concern. User dictionary, user history, and
settings are stored on the local machine. Users who need stronger local data
protection should enable OS-level disk encryption such as BitLocker.
