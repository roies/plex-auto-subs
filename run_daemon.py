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
import json
import logging
import os
import shutil
import sys
import time
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from Contents.Code.subtitle_sync import PlexPoller
from Contents.Code.subtitle_translate import normalize_language_code

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [subtitle_autosync] %(levelname)s %(message)s',
)
log = logging.getLogger('subtitle_autosync')


def configure_logging(log_path: Optional[Path] = None):
    log_path = log_path or DEFAULT_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s [subtitle_autosync] %(levelname)s %(message)s'))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False

DEFAULT_CONFIG_PATH = Path.home() / '.plex-auto-subs.json'
DEFAULT_LOG_PATH = Path.home() / '.plex-auto-subs.log'


def load_config(config_path: Optional[Path] = None) -> dict:
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return {}
    try:
        with path.open('r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        log.warning('Could not read config %s: %s', path, exc)
        return {}
    if not isinstance(data, dict):
        raise ValueError('Config must be a JSON object')
    return data


def resolve_runtime_settings(args, config: dict, env: Optional[dict] = None) -> dict:
    env = env or os.environ
    return {
        'url': _pick_value(args.url, config.get('url') or config.get('plex_url'), env.get('PLEX_URL'), 'http://localhost:32400'),
        'token': _pick_value(args.token, config.get('token'), env.get('PLEX_TOKEN'), ''),
        'interval': _pick_value(args.interval, config.get('interval'), env.get('POLL_INTERVAL'), 15),
        'target_lang': _pick_value(args.target_lang, config.get('target_lang'), env.get('TARGET_LANG'), 'he'),
        'source_lang': _pick_value(args.source_lang, config.get('source_lang'), env.get('SOURCE_LANG'), 'en'),
    }


def _pick_value(cli_value, config_value, env_value, default):
    if cli_value is not None:
        return cli_value
    if config_value is not None:
        return config_value
    if env_value is not None:
        return env_value
    return default


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
    parser.add_argument('--config', default=os.environ.get('PLEX_AUTO_SUBS_CONFIG', str(DEFAULT_CONFIG_PATH)),
                        help='Path to a JSON config file (default: ~/.plex-auto-subs.json)')
    parser.add_argument('--log-file', default=os.environ.get('PLEX_AUTO_SUBS_LOG', str(DEFAULT_LOG_PATH)),
                        help='Path to the rotating log file (default: ~/.plex-auto-subs.log)')
    parser.add_argument('--url', default=None)
    parser.add_argument('--token', default=None)
    parser.add_argument('--interval', type=int, default=None,
                        help='Seconds between polls (default: 15)')
    parser.add_argument('--target-lang', default=None,
                        help='Translate subtitles to this language code (default: he)')
    parser.add_argument('--source-lang', default=None,
                        help='Source language of subtitles (default: en)')
    parser.add_argument('--check', action='store_true',
                        help='Run a preflight check and exit without starting the daemon')
    args = parser.parse_args()

    config = load_config(Path(args.config))
    settings = resolve_runtime_settings(args, config)
    args.url = settings['url']
    args.token = settings['token']
    args.interval = settings['interval']
    args.target_lang = settings['target_lang']
    args.source_lang = settings['source_lang']

    configure_logging(Path(args.log_file))

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
