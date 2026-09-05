import json
import logging

import sqlalchemy as sa
from alembic import op

revision = 'e1a3c5d7f9b2'
down_revision = 'd5a9c3e7b1f4'
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)

CENTER_OFFSET = 0.5

TABLES = (('library_settings', 'library_id'), ('style_profile', 'id'))

def _repin(raw):
    if not raw:
        return None
    try:
        options = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return None
    if not isinstance(options, dict) or options.get('gravity') != 'center':
        return None
    if options.get('text_offset_ratio') == CENTER_OFFSET:
        return None
    options['text_offset_ratio'] = CENTER_OFFSET
    return json.dumps(options)

def _patch_tables(connection):
    for table, key in TABLES:
        rows = connection.execute(
            sa.text(f"SELECT {key}, text_options FROM {table} WHERE text_options IS NOT NULL")
        ).fetchall()
        for row_key, raw in rows:
            patched = _repin(raw)
            if patched is not None:
                connection.execute(
                    sa.text(f"UPDATE {table} SET text_options = :opts WHERE {key} = :key"),
                    {"opts": patched, "key": row_key},
                )

def _patch_defaults_file():
    from affiche.config.env_config import POSTER_CONFIG_FILE
    from pathlib import Path

    path = Path(POSTER_CONFIG_FILE)
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding='utf-8'))
    text_options = data.get('text_options')
    if not isinstance(text_options, dict) or text_options.get('gravity') != 'center':
        return
    if text_options.get('text_offset_ratio') == CENTER_OFFSET:
        return
    text_options['text_offset_ratio'] = CENTER_OFFSET
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')

def upgrade() -> None:
    connection = op.get_bind()
    _patch_tables(connection)
    try:
        _patch_defaults_file()
    except Exception:
        logger.warning("Could not pin the global style's center offset; set it by hand in "
                       "Settings -> Style Options if the title has moved", exc_info=True)

def downgrade() -> None:
    pass
