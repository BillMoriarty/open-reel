import os
import threading
from pathlib import Path

from gi.repository import GLib
import mutagen

from musicplayer import database

ART_CACHE_DIR = Path.home() / '.cache' / 'musicplayer' / 'art'

AUDIO_EXTENSIONS = {'.flac', '.mp3', '.ogg', '.opus', '.m4a', '.mp4', '.wav', '.aac'}

COVER_FILENAMES = [
    'cover.jpg', 'cover.jpeg', 'cover.png',
    'folder.jpg', 'folder.jpeg', 'folder.png',
    'front.jpg',  'front.jpeg',  'front.png',
    'artwork.jpg', 'albumart.jpg',
]


class Scanner:
    def __init__(self, music_folders, on_progress, on_complete, on_error=None):
        self.music_folders = music_folders
        self.on_progress   = on_progress   # (scanned, total, filename) -> None
        self.on_complete   = on_complete   # (album_count, track_count) -> None
        self.on_error      = on_error      # (message) -> None
        self._cancelled    = False
        self._thread       = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        self._cancelled = True

    # ------------------------------------------------------------------ #
    # internal

    def _run(self):
        try:
            ART_CACHE_DIR.mkdir(parents=True, exist_ok=True)

            all_audio_files = self._collect_audio_files()
            total_count = len(all_audio_files)

            GLib.idle_add(self.on_progress, 0, total_count, 'Starting scan...')

            conn = database.get_connection()
            database.initialize_database(conn)

            albums_processed = {}   # album_id -> art_path
            batch_size = 50

            for scan_index, filepath in enumerate(all_audio_files):
                if self._cancelled:
                    break
                try:
                    self._process_file(conn, filepath, albums_processed)
                except Exception:
                    pass  # skip unreadable files silently

                if (scan_index + 1) % batch_size == 0:
                    conn.commit()

                GLib.idle_add(
                    self.on_progress,
                    scan_index + 1,
                    total_count,
                    filepath.name,
                )

            # Remove DB records for files that no longer exist on disk
            known_paths = {str(f) for f in all_audio_files}
            db_paths = {row[0] for row in conn.execute('SELECT file_path FROM tracks').fetchall()}
            stale = db_paths - known_paths
            if stale:
                conn.executemany('DELETE FROM tracks WHERE file_path = ?', [(p,) for p in stale])
                conn.execute(
                    'DELETE FROM albums WHERE id NOT IN '
                    '(SELECT DISTINCT album_id FROM tracks WHERE album_id IS NOT NULL)'
                )

            database.update_album_track_counts(conn)
            conn.commit()

            album_count = len(database.get_all_albums(conn))
            conn.close()

            GLib.idle_add(self.on_complete, album_count, total_count)

        except Exception as error:
            if self.on_error:
                GLib.idle_add(self.on_error, str(error))

    def _collect_audio_files(self):
        found = []
        for music_folder in self.music_folders:
            folder_path = Path(music_folder)
            if not folder_path.exists():
                continue
            for root, dirs, files in os.walk(folder_path):
                dirs.sort()
                for filename in sorted(files):
                    filepath = Path(root) / filename
                    if filepath.suffix.lower() in AUDIO_EXTENSIONS:
                        found.append(filepath)
        return found

    def _process_file(self, conn, filepath, albums_processed):
        current_mtime = filepath.stat().st_mtime
        cached_mtime  = database.get_file_mtime(conn, str(filepath))

        if cached_mtime is not None and abs(cached_mtime - current_mtime) < 1.0:
            return  # unchanged

        audio_easy = mutagen.File(str(filepath), easy=True)
        if audio_easy is None:
            return

        title        = self._tag(audio_easy, 'title')   or filepath.stem
        artist       = self._tag(audio_easy, 'artist')  or 'Unknown Artist'
        album_artist = self._tag(audio_easy, 'albumartist') or artist
        album        = self._tag(audio_easy, 'album')   or filepath.parent.name
        disc_number  = self._int_tag(self._tag(audio_easy, 'discnumber'))
        track_number = self._int_tag(self._tag(audio_easy, 'tracknumber'))
        year         = self._tag(audio_easy, 'date') or self._tag(audio_easy, 'year') or ''
        genre        = self._tag(audio_easy, 'genre') or ''
        duration     = getattr(getattr(audio_easy, 'info', None), 'length', 0) or 0

        album_id = database.make_album_id(str(filepath.parent))

        if album_id not in albums_processed:
            art_path, has_art = self._extract_art(filepath, album_id)
            albums_processed[album_id] = art_path

            database.upsert_album(conn, {
                'id':           album_id,
                'album_title':  album,
                'album_artist': album_artist,
                'year':         year[:4] if year else '',
                'art_path':     art_path,
                'track_count':  0,
            })
        else:
            art_path = albums_processed[album_id]

        database.upsert_track(conn, {
            'file_path':        str(filepath),
            'title':            title,
            'artist':           artist,
            'album_artist':     album_artist,
            'album':            album,
            'disc_number':      disc_number or 1,
            'track_number':     track_number or 0,
            'year':             year[:4] if year else '',
            'genre':            genre,
            'duration_seconds': duration,
            'file_mtime':       current_mtime,
            'has_embedded_art': 1 if art_path else 0,
            'album_id':         album_id,
        })

    def _extract_art(self, filepath, album_id):
        art_cache_path = ART_CACHE_DIR / f'{album_id}.jpg'
        if art_cache_path.exists():
            return str(art_cache_path), True

        # Try embedded art via non-easy mutagen
        try:
            audio_full = mutagen.File(str(filepath), easy=False)
            if audio_full is not None:
                art_data = self._embedded_art_bytes(audio_full)
                if art_data:
                    art_cache_path.write_bytes(art_data)
                    return str(art_cache_path), True
        except Exception:
            pass

        # Fall back to folder image files
        folder = filepath.parent
        for cover_filename in COVER_FILENAMES:
            candidate = folder / cover_filename
            if candidate.exists():
                return str(candidate), False

        return None, False

    def _embedded_art_bytes(self, audio_full):
        # FLAC
        if hasattr(audio_full, 'pictures') and audio_full.pictures:
            return audio_full.pictures[0].data

        tags = getattr(audio_full, 'tags', None)
        if tags is None:
            return None

        # ID3 (MP3)
        for key in tags.keys():
            if key.startswith('APIC'):
                return tags[key].data

        # MP4 / M4A
        if 'covr' in tags:
            covers = tags['covr']
            if covers:
                return bytes(covers[0])

        # Ogg / Opus (metadata_block_picture)
        if hasattr(tags, 'get'):
            raw = tags.get('metadata_block_picture')
            if raw:
                import base64
                import struct
                try:
                    block = base64.b64decode(raw[0])
                    # Skip the picture block header to get to the data
                    offset = 4 + 4 + struct.unpack('>I', block[4:8])[0] + 4 * 4
                    data_len = struct.unpack('>I', block[offset - 4:offset])[0]
                    return block[offset:offset + data_len]
                except Exception:
                    pass

        return None

    @staticmethod
    def _tag(audio, key):
        try:
            value = audio.get(key)
            if value:
                raw = value[0] if isinstance(value, list) else value
                return str(raw).strip() or None
        except Exception:
            pass
        return None

    @staticmethod
    def _int_tag(value):
        if value is None:
            return None
        try:
            return int(str(value).split('/')[0].strip())
        except (ValueError, AttributeError):
            return None
