import tomllib
from pathlib import Path

CONFIG_DIR = Path.home() / '.config' / 'musicplayer'
CONFIG_FILE = CONFIG_DIR / 'config.toml'

DEFAULTS = {
    'music_folders': [],
    'theme': 'default',
    'mascot_enabled': True,
    'notes_folder': '',   # resolved at runtime to DATA_DIR/notes
}


def load_config():
    if not CONFIG_FILE.exists():
        return dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, 'rb') as f:
            loaded = tomllib.load(f)
        merged = dict(DEFAULTS)
        merged.update(loaded)
        return merged
    except Exception:
        return dict(DEFAULTS)


def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in config.items():
        if isinstance(value, list):
            if value:
                items = ', '.join(f'"{v}"' for v in value)
                lines.append(f'{key} = [{items}]')
            else:
                lines.append(f'{key} = []')
        elif isinstance(value, bool):
            lines.append(f'{key} = {"true" if value else "false"}')
        elif isinstance(value, str):
            escaped = value.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        elif isinstance(value, (int, float)):
            lines.append(f'{key} = {value}')
    with open(CONFIG_FILE, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def has_music_folders(config):
    return bool(config.get('music_folders'))
