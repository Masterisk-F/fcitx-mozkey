# Secure Offline Release Checklist

Use this checklist before publishing a Windows release.

## Source revision

- [ ] Release branch:
- [ ] Commit SHA:
- [ ] Upstream base commit:
- [ ] Build machine:
- [ ] Build date:

## Build command

Expected command:

```powershell
cd C:\Users\Makoto\dev\mozc\src

bazelisk --output_user_root=C:/bzl build `
  --config oss_windows `
  --config release_build `
  package
```

## Source checks

- [ ] No obvious runtime networking API usage

```powershell
cd C:\Users\Makoto\dev\mozc
python tools\check_no_network_symbols.py
```

## Tests

- [ ] StatsConfigUtil test passed
- [ ] ConfigHandler test passed

```powershell
cd C:\Users\Makoto\dev\mozc\src

bazelisk --output_user_root=C:/bzl test `
  --config oss_windows `
  --config release_build `
  --test_output=errors `
  //config:stats_config_util_test //config:config_handler_test
```

## Build artifact checks

- [ ] Bazel output binaries do not import prohibited networking DLLs

```powershell
cd C:\Users\Makoto\dev\mozc
python tools\check_no_network_imports.py --root src\bazel-bin
```

- [ ] Bazel output binaries do not contain hard-deny telemetry / updater / crash-upload / usage-statistics markers
- [ ] Report-only URL-like markers are reviewed

```powershell
cd C:\Users\Makoto\dev\mozc
python tools\check_no_network_strings.py --root src\bazel-bin
```

## MSI-extracted binary checks

Extract the MSI and check the files that will actually be installed.

```powershell
cd C:\Users\Makoto\dev\mozc

$extractDir = "msi_extract"
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $extractDir | Out-Null

msiexec.exe /a "src\bazel-bin\win32\installer\Mozc64.msi" /qn TARGETDIR="$PWD\$extractDir"
```

- [ ] MSI-extracted runtime binaries do not import prohibited networking DLLs

```powershell
python tools\check_no_network_imports.py --root msi_extract
```

- [ ] MSI-extracted runtime binaries do not contain hard-deny telemetry / updater / crash-upload / usage-statistics markers
- [ ] Report-only URL-like markers are reviewed

```powershell
python tools\check_no_network_strings.py --root msi_extract
```

## Installed binary checks

Use the actual install directory. On many Windows systems, Mozc is installed
under `C:\Program Files (x86)\Mozc`.

- [ ] Installed runtime binaries do not import prohibited networking DLLs

```powershell
cd C:\Users\Makoto\dev\mozc

python tools\check_no_network_imports.py `
  "C:\Program Files (x86)\Mozc\mozc_server.exe" `
  "C:\Program Files (x86)\Mozc\mozc_tool.exe" `
  "C:\Program Files (x86)\Mozc\mozc_renderer.exe" `
  "C:\Program Files (x86)\Mozc\mozc_broker.exe" `
  "C:\Program Files (x86)\Mozc\mozc_cache_service.exe" `
  "C:\Program Files (x86)\Mozc\mozc_tip64.dll"
```

- [ ] Installed runtime binaries do not contain hard-deny telemetry / updater / crash-upload / usage-statistics markers
- [ ] Report-only URL-like markers are reviewed

```powershell
cd C:\Users\Makoto\dev\mozc

python tools\check_no_network_strings.py `
  "C:\Program Files (x86)\Mozc\mozc_server.exe" `
  "C:\Program Files (x86)\Mozc\mozc_tool.exe" `
  "C:\Program Files (x86)\Mozc\mozc_renderer.exe" `
  "C:\Program Files (x86)\Mozc\mozc_broker.exe" `
  "C:\Program Files (x86)\Mozc\mozc_cache_service.exe" `
  "C:\Program Files (x86)\Mozc\mozc_tip64.dll"
```

## Windows Firewall checks

- [ ] Outbound block rules exist for Mozc runtime executables

```powershell
Get-NetFirewallRule -DisplayName "Mozc Offline - Block *"
```

- [ ] Firewall rules target Mozc executable paths

```powershell
Get-NetFirewallRule -DisplayName "Mozc Offline - Block *" |
  Get-NetFirewallApplicationFilter |
  Select-Object Program
```

Expected programs:

```text
C:\Program Files (x86)\Mozc\mozc_server.exe
C:\Program Files (x86)\Mozc\mozc_tool.exe
C:\Program Files (x86)\Mozc\mozc_renderer.exe
C:\Program Files (x86)\Mozc\mozc_broker.exe
C:\Program Files (x86)\Mozc\mozc_cache_service.exe
```

- [ ] Firewall rules are outbound block rules

```powershell
Get-NetFirewallRule -DisplayName "Mozc Offline - Block *" |
  Select-Object DisplayName, Direction, Action, Enabled, Profile
```

Expected values:

```text
Direction: Outbound
Action: Block
Enabled: True
Profile: Any
```

- [ ] IME still works with the firewall rules enabled
- [ ] Uninstall removes Mozc firewall rules

```powershell
Get-NetFirewallRule -DisplayName "Mozc Offline - Block *" -ErrorAction SilentlyContinue
```

Expected after uninstall: no rules are returned.

## Runtime checks

Use a clean Windows VM.

- [ ] Install MSI
- [ ] Enable Mozc IME
- [ ] Type Japanese text
- [ ] Open config dialog
- [ ] Open dictionary tool
- [ ] Open administration dialog
- [ ] Confirm IME works with network disabled
- [ ] Confirm no outbound connection from Mozc processes

Recommended tools:

- Windows Defender Firewall log
- Resource Monitor
- Process Monitor
- pktmon
- Wireshark

## Release artifacts

- [ ] MSI file:
- [ ] SHA256:
- [ ] Source commit SHA included in release notes
- [ ] Build command included in release notes
- [ ] Known limitations documented

## Documentation

- [ ] README links to `docs/security/offline_guarantee.md`
- [ ] README links to `docs/security/release_checklist.md`
- [ ] README states that Windows installer adds outbound firewall block rules for Mozc runtime executables
- [ ] Release notes state that offline behavior means runtime behavior, not build-time dependency fetching
- [ ] Release notes state that local data protection requires OS-level disk encryption for stronger protection
