# Plex Auto Subs

Automatically **syncs** and **translates** subtitles while you watch — no buttons, no config files, no API keys.

## What it does

Every time you start playing something in Plex with a subtitle selected:

1. 🎯 **Detects** the active subtitle (local sidecar or online/downloaded)
2. ⏱️ **Fixes the timing** using [ffsubsync](https://github.com/smacke/ffsubsync) — analyzes the audio and auto-corrects the offset
3. 🌐 **Translates** from the subtitle’s detected language to your target language (default: English → Hebrew) using [argostranslate](https://github.com/argosopentech/argostranslate) (fully offline after first run)
4. 🔄 **Refreshes Plex** so the corrected subtitle loads live

Zero user involvement. Works for any subtitle Plex can play.

---

## Legal / usage note

This project is intended for lawful personal/home use and local subtitle processing. It does not collect or transmit personal data by default; it processes subtitle files on the machine running the daemon.

You remain responsible for complying with:
- the Plex Terms of Service and the terms of your media/service provider,
- copyright and related rights in the media and subtitles you process,
- local laws regarding translation, distribution, and access control.

Do not use this tool to access or redistribute copyrighted content without permission, or to bypass access controls or regional restrictions. This is not legal advice; if you plan to use it in a business, enterprise, or redistributed context, obtain appropriate legal review.

---

## Install (one command)

### Linux / macOS / Plex server

Run this on your Plex server:

```bash
curl -fsSL https://raw.githubusercontent.com/roies/plex-auto-subs/master/install.sh | bash
```

The script will:
- Install Python and ffmpeg if missing
- Install the package and all dependencies
- Ask for your Plex token *(or leave blank for local no-auth)*
- Set up a systemd service that starts automatically on boot

### Windows

For a one-time run from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-windows.ps1
```

For a persistent install that starts at boot:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
```

The scripts will:
- Check for Python and ffmpeg
- Install the package and dependencies
- Ask for your Plex token and URL
- Start the daemon immediately (run script) or create a Windows scheduled task (install script)

---

## Manual install

```bash
pip install git+https://github.com/roies/plex-auto-subs
plex-auto-subs --token YOUR_PLEX_TOKEN
```

---

## Getting your Plex token

1. Open Plex Web → **Settings** → **Account**
2. Scroll to the bottom → click **"Get your Plex token"**
3. Or visit: https://support.plex.tv/articles/204059436

---

## Service management

```bash
sudo systemctl status plex-auto-subs     # check status
sudo journalctl -u plex-auto-subs -f     # live logs
sudo systemctl restart plex-auto-subs    # restart
sudo systemctl stop plex-auto-subs       # stop
```

---

## Configuration

| Flag | Env var | Default | Description |
|------|---------|---------|-------------|
| `--url` | `PLEX_URL` | `http://localhost:32400` | Plex server URL |
| `--token` | `PLEX_TOKEN` | *(empty)* | Plex auth token |
| `--interval` | `POLL_INTERVAL` | `15` | Seconds between polls |
| `--target-lang` | `TARGET_LANG` | `he` | Translate to this language |
| `--source-lang` | `SOURCE_LANG` | `en` | Source subtitle language |

### Change translation language

```bash
plex-auto-subs --target-lang fr    # French
plex-auto-subs --target-lang es    # Spanish
plex-auto-subs --target-lang ar    # Arabic
plex-auto-subs --target-lang ''    # Disable translation (sync only)
```

If Plex exposes the selected subtitle’s language, the daemon uses that as the source language automatically. Otherwise it falls back to `--source-lang` / `SOURCE_LANG` (default: `en`). If the subtitle is already in the target language, translation is skipped.

### Preflight check

```bash
plex-auto-subs --check
```

This validates the local runtime (Python, ffsubsync, argostranslate model support) and checks whether Plex responds at the configured URL/token before the daemon starts.

> First run per language pair downloads a ~100MB model. Fully offline after that.

---

## Requirements

- Python 3.8+
- ffmpeg on PATH
- ffsubsync *(installed automatically)*
- argostranslate *(installed automatically)*

---

## Run tests

```bash
git clone https://github.com/roies/plex-auto-subs
cd plex-auto-subs
pip install pytest
python -m pytest tests/ -v
```

---

## License

This repository's own source code is licensed under the MIT License (see [LICENSE](LICENSE)).

The project also depends on third-party packages such as [ffsubsync](https://github.com/smacke/ffsubsync) and [argostranslate](https://github.com/argosopentech/argostranslate), which remain subject to their own upstream license terms. See [NOTICE](NOTICE) for details.
