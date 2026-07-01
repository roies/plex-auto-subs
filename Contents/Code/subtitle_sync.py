"""
Core subtitle auto-sync logic.

Flow:
  PlexPoller  →  get active sessions from PMS API
              →  for each new session, resolve the selected subtitle file path
              →  run ffsubsync to compute and apply the correct offset
              →  optionally translate subtitles to target language (argostranslate)
              →  refresh Plex metadata so the fixed sub is picked up immediately
"""

import json
import logging
import shutil
import subprocess
import tempfile
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
import os

log = logging.getLogger('subtitle_autosync')

_SUBTITLE_EXTENSIONS = {'.srt', '.vtt', '.ass', '.ssa', '.sub'}
_VIDEO_EXTENSIONS    = {'.mp4', '.mkv', '.mov', '.avi', '.m4v', '.wmv', '.ts', '.m2ts'}
# Directories that must never be touched regardless of what the API returns
_BLOCKED_PREFIXES = ('/etc', '/bin', '/sbin', '/usr/bin', '/usr/sbin',
                     '/boot', '/sys', '/proc', '/dev', '/root',
                     '/home', '/var/log')


def _safe_subtitle_path(path_str: str) -> bool:
    """Return True only if the path looks like a legitimate subtitle file."""
    try:
        p = Path(path_str).resolve()
    except (ValueError, OSError):
        return False
    if not p.is_absolute():
        return False
    if p.suffix.lower() not in _SUBTITLE_EXTENSIONS:
        log.warning('Rejected non-subtitle path from API: %s', path_str)
        return False
    for blocked in _BLOCKED_PREFIXES:
        if str(p).startswith(blocked):
            log.warning('Rejected blocked path from API: %s', path_str)
            return False
    return True


def _safe_media_path(path_str: str) -> bool:
    """Return True only if the path looks like a legitimate video file."""
    try:
        p = Path(path_str).resolve()
    except (ValueError, OSError):
        return False
    if not p.is_absolute():
        return False
    if p.suffix.lower() not in _VIDEO_EXTENSIONS:
        return False
    if not p.exists():
        return False
    for blocked in _BLOCKED_PREFIXES:
        if str(p).startswith(blocked):
            log.warning('Rejected blocked video path from API: %s', path_str)
            return False
    return True


def translate_subtitle_file(path: Path, target_lang: str, source_lang: str = 'en'):
    """Translate subtitle file in-place."""
    from .subtitle_translate import translate_srt
    text = path.read_text(encoding='utf-8', errors='replace')
    translated = translate_srt(text, target_lang=target_lang, source_lang=source_lang)
    path.write_text(translated, encoding='utf-8')
    log.info('Translated subtitle to [%s]: %s', target_lang, path.name)


class PlexPoller:
    """Polls /status/sessions and syncs subtitles for newly-started playback."""

    def __init__(self, plex_url: str = 'http://localhost:32400', token: str = '',
                 poll_interval: int = 15, target_lang: str = 'he', source_lang: str = 'en'):
        self.base = plex_url.rstrip('/')
        self.token = token
        self.poll_interval = poll_interval
        self.target_lang = target_lang
        self.source_lang = source_lang
        # track sessions we've already processed: session_key → subtitle_stream_id
        self._processed: dict = {}

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    def tick(self):
        """Call once per poll cycle; processes any new/changed sessions."""
        sessions = self._get_sessions()
        for session in sessions:
            self._handle_session(session)

    # ------------------------------------------------------------------
    # Plex API helpers
    # ------------------------------------------------------------------

    def _api(self, path: str) -> Optional[ET.Element]:
        url = f'{self.base}{path}'
        req = urllib.request.Request(url, headers={'Accept': 'application/xml'})
        if self.token:
            req.add_header('X-Plex-Token', self.token)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return ET.fromstring(resp.read())
        except (urllib.error.URLError, ET.ParseError) as exc:
            log.warning('Plex API error %s: %s', path, exc)
            return None

    def _api_download(self, path: str, dest: Path):
        url = f'{self.base}{path}'
        req = urllib.request.Request(url)
        if self.token:
            req.add_header('X-Plex-Token', self.token)
        with urllib.request.urlopen(req, timeout=30) as resp, dest.open('wb') as out:
            shutil.copyfileobj(resp, out)

    def _refresh(self, rating_key: str):
        path = f'/library/metadata/{rating_key}/refresh'
        url = f'{self.base}{path}'
        req = urllib.request.Request(url, method='PUT')
        if self.token:
            req.add_header('X-Plex-Token', self.token)
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.URLError as exc:
            log.warning('Refresh failed for %s: %s', rating_key, exc)

    # ------------------------------------------------------------------
    # Session / subtitle resolution
    # ------------------------------------------------------------------

    def _get_sessions(self) -> list:
        root = self._api('/status/sessions')
        if root is None:
            return []
        return root.findall('.//Video') + root.findall('.//Track')

    def _handle_session(self, video: ET.Element):
        session_key = video.get('sessionKey', '')
        rating_key = video.get('ratingKey', '')
        if not session_key or not rating_key:
            return

        selected_sub = self._find_selected_subtitle(video)
        if selected_sub is None:
            return

        sub_id = selected_sub.get('id', selected_sub.get('streamIdentifier', ''))
        cache_key = f'{session_key}:{sub_id}'
        if self._processed.get(session_key) == cache_key:
            return  # already done for this session+subtitle combo
        self._processed[session_key] = cache_key

        video_file = self._video_file_path(video)
        if not video_file:
            log.info('No local video file for session %s, skipping', session_key)
            return

        sub_file = self._resolve_subtitle_path(selected_sub, rating_key)
        if not sub_file:
            log.info('Could not resolve subtitle for session %s', session_key)
            return

        log.info('Syncing subtitles for: %s', Path(video_file).name)
        synced = run_ffsubsync(video_file, str(sub_file))
        if synced:
            if self.target_lang:
                translate_subtitle_file(sub_file, self.target_lang, self.source_lang)
            self._refresh(rating_key)
            log.info('Done — refreshed Plex metadata for %s', rating_key)
        else:
            log.warning('ffsubsync failed for session %s', session_key)

    def _find_selected_subtitle(self, video: ET.Element) -> Optional[ET.Element]:
        for stream in video.iter('Stream'):
            if stream.get('streamType') == '3' and stream.get('selected') == '1':
                return stream
        return None

    def _video_file_path(self, video: ET.Element) -> Optional[str]:
        for part in video.iter('Part'):
            f = part.get('file')
            if f and _safe_media_path(f):
                return f
        return None

    def _resolve_subtitle_path(self, stream: ET.Element, rating_key: str) -> Optional[Path]:
        # Local sidecar or Plex-cached file: 'file' attribute is the real path
        file_attr = stream.get('file')
        if file_attr and _safe_subtitle_path(file_attr):
            p = Path(file_attr)
            if p.exists():
                return p

        # Online/embedded subtitle: download via the stream key into a temp sidecar
        stream_key = stream.get('key')
        if stream_key:
            # Fetch full metadata to get the video's local file path for naming
            meta = self._api(f'/library/metadata/{rating_key}')
            video_file = None
            if meta is not None:
                for part in meta.iter('Part'):
                    f = part.get('file')
                    if f and _safe_media_path(f):   # validate before trusting API path
                        video_file = Path(f)
                        break

            if video_file:
                # ponytail: save alongside video so Plex picks it up as external sub
                dest = video_file.with_suffix('.autosync.srt')
            else:
                dest = Path(tempfile.gettempdir()) / f'autosync_{rating_key}.srt'

            try:
                self._api_download(stream_key, dest)
                log.info('Downloaded online subtitle to %s', dest)
                return dest
            except Exception as exc:
                log.warning('Could not download subtitle stream %s: %s', stream_key, exc)

        return None


# ------------------------------------------------------------------
# ffsubsync wrapper
# ------------------------------------------------------------------

def run_ffsubsync(video_path: str, subtitle_path: str) -> bool:
    """
    Run ffsubsync to auto-detect and fix the subtitle offset in-place.
    Returns True on success.
    Requires: pip install ffsubsync  (MIT license)
    """
    cmd = ['ffs', video_path, '-i', subtitle_path, '-o', subtitle_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return True
        log.warning('ffsubsync stderr: %s', result.stderr[-500:])
        return False
    except FileNotFoundError:
        log.error('ffsubsync (ffs) not found — install it: pip install ffsubsync')
        return False
    except subprocess.TimeoutExpired:
        log.warning('ffsubsync timed out for %s', subtitle_path)
        return False
