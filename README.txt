Plex Auto Subs
==============

Automatically syncs AND translates subtitles while you watch — no buttons,
no config files, no manual offsets, no API keys.

What it does
------------
Every time you start playing something in Plex with a subtitle track selected:

  1. Detects the active subtitle (local sidecar OR online/downloaded subtitle)
  2. Runs ffsubsync to auto-detect and fix the timing offset against the audio
  3. Translates the subtitle from the detected source language to your target
     language (default: English to Hebrew) using argostranslate
     (fully offline after the first model download, ~100MB one-time)
  4. Refreshes Plex metadata — the corrected, translated subtitle loads live

Zero user involvement required. Works with any subtitle Plex can play.

Legal / usage note
-------------------
  This project is intended for lawful personal/home use and local subtitle
  processing. It does not collect or transmit personal data by default; it
  processes subtitle files on the machine running the daemon.

  You remain responsible for complying with the Plex Terms of Service and the
  terms of your media/service provider, copyright and related rights in the
  media and subtitles you process, and local laws regarding translation,
  distribution, and access control.

  Do not use this tool to access or redistribute copyrighted content without
  permission, or to bypass access controls or regional restrictions. This is
  not legal advice; if you plan to use it in a business, enterprise, or
  redistributed context, obtain appropriate legal review.

Requirements
------------
- Python 3.8+
- ffmpeg on PATH  (used by ffsubsync for audio analysis)
- pip install git+https://github.com/roies/plex-auto-subs

Quick install (Linux/macOS — where Plex lives)
----------------------------------------------
  curl -fsSL https://raw.githubusercontent.com/roies/plex-auto-subs/v1.1.0/install.sh | bash

That's it. The script installs Python/ffmpeg if missing, installs the package,
asks for your Plex token, and registers a systemd service that starts on boot.

Windows install
---------------
  powershell -ExecutionPolicy Bypass -File .\run-windows.ps1 -ReleaseTag v1.1.0

For a one-time run from PowerShell. For a persistent install that starts at
boot, use:

  powershell -ExecutionPolicy Bypass -File .\install-windows.ps1 -ReleaseTag v1.1.0

The PowerShell scripts check for Python/ffmpeg, install the package and
dependencies, ask for your Plex token and URL, and either start the daemon
immediately or create a Windows scheduled task that starts it at boot.

Manual install
--------------
  pip install git+https://github.com/roies/plex-auto-subs
  plex-auto-subs                                 # local Plex, no auth needed
  plex-auto-subs --token YOUR_PLEX_TOKEN         # remote or authenticated
  plex-auto-subs --url http://192.168.1.5:32400 --token TOKEN

Service management (after install.sh)
--------------------------------------
  sudo systemctl status plex-auto-subs
  sudo journalctl -u plex-auto-subs -f     # live logs
  sudo systemctl stop plex-auto-subs
  sudo systemctl restart plex-auto-subs

Environment variables
---------------------
  PLEX_URL      — Plex server URL (default: http://localhost:32400)
  PLEX_TOKEN    — Plex auth token (default: empty)
  POLL_INTERVAL — seconds between polls (default: 15)
  TARGET_LANG   — translate to this language code (default: he)
  SOURCE_LANG   — subtitle source language (default: en)

Change translation language
----------------------------
  plex-auto-subs --target-lang fr    # French
  plex-auto-subs --target-lang es    # Spanish
  plex-auto-subs --target-lang ar    # Arabic
  TARGET_LANG=de plex-auto-subs      # German via env var

  Disable translation:
  plex-auto-subs --target-lang ''

  If Plex exposes the selected subtitle's language, plex-auto-subs uses that
  as the source language automatically. Otherwise it falls back to
  SOURCE_LANG / --source-lang (default: en). If the subtitle is already in
  the target language, translation is skipped.

Preflight check
---------------
  plex-auto-subs --check

  This validates the local runtime (Python, ffsubsync, argostranslate model
  support) and checks whether Plex responds at the configured URL/token before
  the daemon starts.

Config file
-----------
  You can store settings in a JSON file and point the daemon at it:

     plex-auto-subs --config /path/to/plex-auto-subs.json

  A sample file is included as config.example.json. Supported keys are url,
  token, interval, target_lang, and source_lang.

Logging
-------
  The daemon writes a rotating log file by default to ~/.plex-auto-subs.log
  (or the path passed via --log-file). Logs rotate at 2MB with 3 backups
  retained.

Startup self-update
-------------------
  If you want the daemon to upgrade itself before each startup, pass
  --self-update (or set PLEX_AUTO_SUBS_RELEASE_TAG to a newer tag). The
  daemon will install the package from the configured release tag before it
  begins polling.

Getting your Plex token
-----------------------
  Plex Web → Settings → Account → scroll down → "Get your Plex token"
  https://support.plex.tv/articles/204059436

Online subtitle support
-----------------------
  When you select an online subtitle in Plex, Plex downloads it to its cache.
  plex-auto-subs finds this file via the PMS API and syncs + translates it.
  If no local path exists, the subtitle is downloaded and saved alongside the
  video as <videoname>.autosync.srt, which Plex picks up after metadata refresh.

Tests
-----
  python -m pytest tests/ -v

License
-------
  This repository's own source code is licensed under the MIT License
  (see LICENSE).

  The project also depends on third-party packages such as ffsubsync and
  argostranslate, which remain subject to their own upstream license terms.
  See NOTICE for details.


