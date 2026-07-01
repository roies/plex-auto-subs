Plex Auto Subs
==============

Automatically syncs AND translates subtitles while you watch — no buttons,
no config files, no manual offsets, no API keys.

What it does
------------
Every time you start playing something in Plex with a subtitle track selected:

  1. Detects the active subtitle (local sidecar OR online/downloaded subtitle)
  2. Runs ffsubsync to auto-detect and fix the timing offset against the audio
  3. Translates the subtitle from English to Hebrew using argostranslate
     (fully offline after the first model download, ~100MB one-time)
  4. Refreshes Plex metadata — the corrected, translated subtitle loads live

Zero user involvement required. Works with any subtitle Plex can play.

Requirements
------------
- Python 3.8+
- ffmpeg on PATH  (used by ffsubsync for audio analysis)
- pip install git+https://github.com/roies/plex-auto-subs

Quick install (Linux/macOS — where Plex lives)
----------------------------------------------
  curl -fsSL https://raw.githubusercontent.com/roies/plex-auto-subs/master/install.sh | bash

That's it. The script installs Python/ffmpeg if missing, installs the package,
asks for your Plex token, and registers a systemd service that starts on boot.

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


