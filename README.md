# CoX Raid Dashboard

A local Windows dashboard for viewing and analyzing Chambers of Xeric raid data
recorded by RuneLite.

The project is intentionally open source so users can inspect the code and the
exact GitHub Actions workflow that produces release installers before deciding
whether to run them.

> [!IMPORTANT]
> Release installers are currently **unsigned**. Windows Defender SmartScreen may
> display an "unrecognized app" or "unknown publisher" warning. Do not disable
> SmartScreen or antivirus software for this project. Review the source/build
> workflow, verify the release hash/provenance, or build the application yourself
> if you are not comfortable running an unsigned binary.

## What it does

The dashboard:

- reads a local CoX raid tracker log beneath `.runelite`;
- discovers RuneLite screenshot accounts from
  `.runelite\screenshots\<account>`;
- matches personal purple drops to local `Boss Kills` screenshots using CoX,
  KC, date, and timestamp information;
- serves the dashboard only on `127.0.0.1:8081`;
- opens the dashboard in the user's default browser;
- stores dashboard preferences under `%LOCALAPPDATA%\CoXRaidDashboard`;
- does not intentionally upload raid data or screenshots;
- does not modify RuneLite raid logs or screenshots.
- exits automatically after all dashboard tabs stop sending local heartbeats.

The first launch displays this local-data behavior before raid data is loaded.

## Dashboard features

Current functionality includes:

- raid history with filtering, sorting, and CSV export;
- CM / Regular raid mode handling;
- purple, kit, and dust tracking;
- regular and special-loot value totals;
- global Stats filters for `All | CM | Regular`;
- Stats time ranges:
  `All Time | Last 30 Days | Last 3 Months | Last 6 Months | Last 50 Raids | Last 100 Raids`;
- purple luck versus expected rate at 1 purple per 860,000 points;
- current and longest personal purple dry streaks;
- team-size performance;
- rolling 10 / 25 / 50 raid performance with team-size selection;
- personal points/hour metrics in the top summary, team-size performance, rolling performance, and CSV export;
- purple distribution and purple history;
- per-player special loot totals;
- local Boss Kills screenshot viewing from Purple History;
- automatic screenshot-account selection based on the account with the most
  verified matches to raid history.
- automatic process shutdown about 30 seconds after all dashboard browser tabs are closed;
- an explicit **Quit Dashboard** button for immediate shutdown.

## Downloading a release

Use the repository's **Releases** page rather than downloading an executable
from an unrelated mirror.

Each tagged release produced by GitHub Actions contains:

- `CoXRaidDashboard-Setup.exe`
- `CoXRaidDashboard.exe`
- `SHA256SUMS.txt`

The release workflow also creates GitHub artifact attestations for the EXE and
installer.

## Verify a release

### 1. Verify SHA-256

From PowerShell:

```powershell
Get-FileHash .\CoXRaidDashboard-Setup.exe -Algorithm SHA256
```

Compare the resulting hash with `SHA256SUMS.txt` attached to the same GitHub
release.

### 2. Verify GitHub build provenance

With the GitHub CLI installed:

```powershell
gh attestation verify .\CoXRaidDashboard-Setup.exe -R OWNER/cox-raid-dashboard
```

Replace `OWNER` with the GitHub account or organization hosting this repository.

A valid result verifies that GitHub has an attestation tying that artifact to a
workflow in the specified repository. This is **not the same thing as Windows
Authenticode code signing**, but it gives users a way to verify how the release
artifact was produced.

### 3. Review the source

The Windows release is built from:

- `app/server.py`
- `app/dashboard.html`
- `CoXRaidDashboard.spec`
- `installer/CoXRaidDashboard.iss`
- `.github/workflows/release.yml`

The release workflow runs on a GitHub-hosted Windows runner.

## Build it yourself

### Requirements

- Windows
- Python 3.11+
- PowerShell
- Inno Setup 6 if you want `Setup.exe`

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\BUILD_WINDOWS.ps1
```

The build script:

1. installs the pinned build dependencies from `requirements-build.txt`;
2. runs Bandit against the Python application;
3. builds `CoXRaidDashboard.exe` with PyInstaller;
4. builds `CoXRaidDashboard-Setup.exe` when Inno Setup is available;
5. creates a SHA-256 checksum file.

## Creating a release

Releases are automated.

1. Merge the code you want to release into `main`.
2. Create and push a version tag, for example:

```bash
git tag v1.0.0
git push origin v1.0.0
```

3. `.github/workflows/release.yml` builds the Windows artifacts on GitHub.
4. The workflow creates a GitHub Release and attaches the installer, standalone
   executable, and SHA-256 file.
5. GitHub artifact attestations are generated for the two binaries.

## Security

Please read [SECURITY.md](SECURITY.md) before reporting a vulnerability.

Do **not** post exploitable security details in a public GitHub issue.

## Privacy / network behavior

The application binds its HTTP server to:

```text
127.0.0.1:8081
```

That is the local loopback interface, not an externally listening interface.

The dashboard currently loads Old School RuneScape Wiki item images in the
browser using `oldschool.runescape.wiki`. Those image requests are separate
from the local RuneLite raid/screenshot data; the application does not send
the raid log or screenshot contents with those requests.

## Project status

This is an unofficial community project. It is not affiliated with, endorsed
by, or sponsored by Jagex, RuneLite, or the Old School RuneScape Wiki.

Old School RuneScape and related names/assets are the property of their
respective owners.

## License

Project source code is available under the [MIT License](LICENSE).
