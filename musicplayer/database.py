import sqlite3
import hashlib
import time
from pathlib import Path

DATA_DIR = Path.home() / '.local' / 'share' / 'musicplayer'
DATABASE_FILE = DATA_DIR / 'library.db'

SCHEMA_VERSION = 1


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATABASE_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(conn):
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS tracks (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path        TEXT UNIQUE NOT NULL,
            title            TEXT,
            artist           TEXT,
            album_artist     TEXT,
            album            TEXT,
            disc_number      INTEGER,
            track_number     INTEGER,
            year             TEXT,
            genre            TEXT,
            duration_seconds REAL,
            file_mtime       REAL,
            has_embedded_art INTEGER DEFAULT 0,
            album_id         TEXT
        );

        CREATE TABLE IF NOT EXISTS albums (
            id           TEXT PRIMARY KEY,
            album_title  TEXT,
            album_artist TEXT,
            year         TEXT,
            art_path     TEXT,
            track_count  INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_tracks_album_id  ON tracks(album_id);
        CREATE INDEX IF NOT EXISTS idx_tracks_file_path ON tracks(file_path);

        CREATE TABLE IF NOT EXISTS play_events (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT    NOT NULL,
            played_at INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_play_events_file_path ON play_events(file_path);
        CREATE INDEX IF NOT EXISTS idx_play_events_played_at ON play_events(played_at);
    ''')
    conn.execute(
        'INSERT OR IGNORE INTO meta (key, value) VALUES (?, ?)',
        ('schema_version', str(SCHEMA_VERSION))
    )
    conn.commit()


def make_album_id(album_title, album_artist):
    key = f"{(album_artist or 'Unknown').lower()}|{(album_title or 'Unknown').lower()}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def get_file_mtime(conn, file_path):
    row = conn.execute(
        'SELECT file_mtime FROM tracks WHERE file_path = ?', (file_path,)
    ).fetchone()
    return row['file_mtime'] if row else None


def upsert_track(conn, track_data):
    conn.execute('''
        INSERT OR REPLACE INTO tracks
            (file_path, title, artist, album_artist, album, disc_number,
             track_number, year, genre, duration_seconds, file_mtime,
             has_embedded_art, album_id)
        VALUES
            (:file_path, :title, :artist, :album_artist, :album, :disc_number,
             :track_number, :year, :genre, :duration_seconds, :file_mtime,
             :has_embedded_art, :album_id)
    ''', track_data)


def upsert_album(conn, album_data):
    conn.execute('''
        INSERT OR REPLACE INTO albums
            (id, album_title, album_artist, year, art_path, track_count)
        VALUES
            (:id, :album_title, :album_artist, :year, :art_path, :track_count)
    ''', album_data)


def update_album_track_counts(conn):
    conn.execute('''
        UPDATE albums
        SET track_count = (
            SELECT COUNT(*) FROM tracks WHERE tracks.album_id = albums.id
        )
    ''')


def get_all_albums(conn):
    return conn.execute('''
        SELECT id, album_title, album_artist, year, art_path, track_count
        FROM   albums
        ORDER BY album_artist COLLATE NOCASE,
                 year,
                 album_title  COLLATE NOCASE
    ''').fetchall()


def get_tracks_for_album(conn, album_id):
    return conn.execute('''
        SELECT id, file_path, title, artist, track_number, disc_number, duration_seconds
        FROM   tracks
        WHERE  album_id = ?
        ORDER BY disc_number, track_number
    ''', (album_id,)).fetchall()


def record_play(conn, file_path: str):
    """Insert one play event for the given track. Call when playback starts."""
    conn.execute(
        'INSERT INTO play_events (file_path, played_at) VALUES (?, ?)',
        (file_path, int(time.time()))
    )
    conn.commit()


def get_recently_played_albums(conn, limit: int = 20):
    """Albums ordered by the most recent play of any track in them."""
    return conn.execute('''
        SELECT a.id, a.album_title, a.album_artist, a.art_path,
               MAX(e.played_at) AS last_played
        FROM   play_events e
        JOIN   tracks t ON t.file_path = e.file_path
        JOIN   albums a ON a.id = t.album_id
        GROUP  BY a.id
        ORDER  BY last_played DESC
        LIMIT  ?
    ''', (limit,)).fetchall()


def get_most_played_albums(conn, limit: int = 20):
    """Albums ordered by total track-play count."""
    return conn.execute('''
        SELECT a.id, a.album_title, a.album_artist, a.art_path,
               COUNT(*) AS play_count
        FROM   play_events e
        JOIN   tracks t ON t.file_path = e.file_path
        JOIN   albums a ON a.id = t.album_id
        GROUP  BY a.id
        ORDER  BY play_count DESC
        LIMIT  ?
    ''', (limit,)).fetchall()


def get_most_played_tracks(conn, limit: int = 50):
    """Individual tracks ordered by play count."""
    return conn.execute('''
        SELECT t.file_path, t.title, t.artist, t.album_artist,
               t.album_id, t.duration_seconds,
               COUNT(*) AS play_count,
               MAX(e.played_at) AS last_played
        FROM   play_events e
        JOIN   tracks t ON t.file_path = e.file_path
        GROUP  BY t.file_path
        ORDER  BY play_count DESC
        LIMIT  ?
    ''', (limit,)).fetchall()


def search_albums_and_tracks(conn, query):
    like = f'%{query}%'
    return conn.execute('''
        SELECT DISTINCT a.id, a.album_title, a.album_artist, a.art_path
        FROM   albums a
        JOIN   tracks t ON t.album_id = a.id
        WHERE  t.title        LIKE ?
            OR t.artist       LIKE ?
            OR a.album_title  LIKE ?
            OR a.album_artist LIKE ?
        ORDER BY a.album_artist COLLATE NOCASE, a.album_title COLLATE NOCASE
        LIMIT 300
    ''', (like, like, like, like)).fetchall()
