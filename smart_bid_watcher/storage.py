from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import app_data_dir
from .models import Notice


class Storage:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "bid.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS notices (
                    source TEXT NOT NULL,
                    notice_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    organization TEXT NOT NULL DEFAULT '',
                    published_at TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '',
                    matched_keywords TEXT NOT NULL DEFAULT '[]',
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    notification_status TEXT NOT NULL DEFAULT 'pending',
                    notification_error TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (source, notice_id)
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_notices_first_seen
                    ON notices(first_seen_at DESC);
                """
            )

    def has_seen(self, source: str, notice_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM notices WHERE source = ? AND notice_id = ?",
                (source, notice_id),
            ).fetchone()
        return row is not None

    def save_notice(self, notice: Notice, status: str = "pending") -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO notices (
                    source, notice_id, title, organization, published_at, url,
                    category, matched_keywords, notification_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notice.source,
                    notice.notice_id,
                    notice.title,
                    notice.organization,
                    notice.published_at,
                    notice.url,
                    notice.category,
                    json.dumps(notice.matched_keywords, ensure_ascii=False),
                    status,
                ),
            )
            return cursor.rowcount > 0

    def mark_notification(self, notice: Notice, status: str, error: str = "") -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE notices
                SET notification_status = ?, notification_error = ?
                WHERE source = ? AND notice_id = ?
                """,
                (status, error[:1000], notice.source, notice.notice_id),
            )

    def mark_all_pending_as_baseline(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE notices
                SET notification_status = 'baseline', notification_error = ''
                WHERE notification_status = 'pending'
                """
            )

    def pending_notices(self, limit: int = 20) -> list[Notice]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM notices
                WHERE notification_status = 'pending'
                ORDER BY first_seen_at ASC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_notice(row) for row in rows]

    def recent_notices(self, limit: int = 50) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM notices ORDER BY first_seen_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_meta(self, key: str, default: str = "") -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = ?", (key,)
            ).fetchone()
        return str(row["value"]) if row else default

    def set_meta(self, key: str, value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO metadata(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    @staticmethod
    def _row_to_notice(row: sqlite3.Row) -> Notice:
        return Notice(
            source=row["source"],
            notice_id=row["notice_id"],
            title=row["title"],
            organization=row["organization"],
            published_at=row["published_at"],
            url=row["url"],
            category=row["category"],
            matched_keywords=json.loads(row["matched_keywords"] or "[]"),
        )
