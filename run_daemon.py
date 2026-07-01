#!/usr/bin/env python3
"""
Plex Auto Subs — standalone daemon.

Polls Plex Media Server for active playback sessions, auto-syncs subtitle
timing with ffsubsync, and auto-translates to Hebrew with argostranslate.
Fully automatic — no user involvement needed.

Usage:
    plex-auto-subs                                  # local Plex, no auth
    plex-auto-subs --token YOUR_TOKEN               # with auth
    plex-auto-subs --url http://192.168.1.5:32400 --token TOKEN

Config via environment variables:
    PLEX_URL      — default: http://localhost:32400
    PLEX_TOKEN    — default: (empty)
    POLL_INTERVAL — seconds between polls, default: 15
    TARGET_LANG   — translate to this language code, default: he (Hebrew)
    SOURCE_LANG   — subtitle source language, default: en
"""

import argparse
import logging
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from Contents.Code.subtitle_sync import PlexPoller
from Contents.Code.subtitle_translate import normalize_language_code

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [subtitle_autosync] %(levelname)s %(message)s',
)
log = logging.getLogger('subtitle_autosync')


def _check_environment(args):
    print('Plex Auto Subs preflight check')
    print('============================')
    print(f'Plex URL: {args.url}')
    print(f'Target language: {args.target_lang or "off"}')
    print(f'Source language: {args.source_lang}')

    checks = []

    ffsubsync = shutil.which('ffs')
    checks.append(('ffsubsync (ffs)', ffsubsync is not None, ffsubsync or 'not found'))

    python = sys.executable
    checks.append(('Python entrypoint', True, python))

    translator = None
    try:
        import argostranslate  # noqa: F401
        translator = 'installed'
    except ImportError:
        translator = 'missing'
    checks.append(('argostranslate', translator == 'installed', translator))

    normalized_target = normalize_language_code(args.target_lang) if args.target_lang else None
    normalized_source = normalize_language_code(args.source_lang) if args.source_lang else None
    checks.append(('language config', bool(normalized_target or not args.target_lang),
                   f'{normalized_source or args.source_lang} -> {normalized_target or "off"}'))

    if args.token:
        req = urllib.request.Request(f'{args.url}/status/sessions', headers={'X-Plex-Token': args.token, 'Accept': 'application/xml'})
    else:
        req = urllib.request.Request(f'{args.url}/status/sessions', headers={'Accept': 'application/xml'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            checks.append(('Plex API reachability', True, f'HTTP {status}'))
    except Exception as exc:
        checks.append(('Plex API reachability', False, str(exc)))

    for name, ok, detail in checks:
        marker = 'OK' if ok else 'FAIL'
        print(f'[{marker}] {name}: {detail}')

    if not all(ok for _, ok, _ in checks[:-1]):
        print('\nPreflight failed. Fix the items marked FAIL before running the daemon.')
        return 1
    print('\nPreflight passed. The daemon should be able to start.')
    return 0


def main():
    parser = argparse.ArgumentParser(description='Plex Auto Subs — auto-sync and translate subtitles')
    parser.add_argument('--url', default=os.environ.get('PLEX_URL', 'http://localhost:32400'))
    parser.add_argument('--token', default=os.environ.get('PLEX_TOKEN', ''))
    parser.add_argument('--interval', type=int,
                        default=int(os.environ.get('POLL_INTERVAL', '15')),
                        help='Seconds between polls (default: 15)')
    parser.add_argument('--target-lang', default=os.environ.get('TARGET_LANG', 'he'),
                        help='Translate subtitles to this language code (default: he)')
    parser.add_argument('--source-lang', default=os.environ.get('SOURCE_LANG', 'en'),
                        help='Source language of subtitles (default: en)')
    parser.add_argument('--check', action='store_true',
                        help='Run a preflight check and exit without starting the daemon')
    args = parser.parse_args()

    if args.check:
        return _check_environment(args)

    log.info('Plex Auto Subs starting — PMS: %s  interval: %ds  translate: %s',
             args.url, args.interval, args.target_lang or 'off')
    log.info('Requires: ffsubsync + argostranslate  (pip install plex-auto-subs)')
    if args.target_lang:
        log.info('Translation enabled (%s→%s) — install: pip install argostranslate',
                 args.source_lang, args.target_lang)

    poller = PlexPoller(plex_url=args.url, token=args.token, poll_interval=args.interval,
                        target_lang=args.target_lang, source_lang=args.source_lang)

    while True:
        try:
            poller.tick()
        except KeyboardInterrupt:
            log.info('Stopped.')
            break
        except Exception as exc:
            log.exception('Unexpected error: %s', exc)
        time.sleep(args.interval)

    return 0


if __name__ == '__main__':
    sys.exit(main())


if __name__ == '__main__':
    main()
