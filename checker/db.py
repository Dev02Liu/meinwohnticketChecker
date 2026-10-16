"""SQLite storage for seen listings and check runs (safe to use from several threads)."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    angebot_uuid TEXT PRIMARY KEY,
    first_seen   TEXT NOT NULL,
    last_seen    TEXT NOT NULL,
    removed_at   TEXT,
    notified_at  TEXT,
    data         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    TEXT NOT NULL,
    finished_at   TEXT NOT NULL,
    status        TEXT NOT NULL,
    total_hits    INTEGER,
    new_count     INTEGER,
    removed_count INTEGER,
    error         TEXT
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


class Database:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- meta -----------------------------------------------------------------
    def get_meta(self, key: str, default: str | None = None) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_meta(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            self._conn.commit()

    def delete_meta(self, key: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM meta WHERE key = ?", (key,))
            self._conn.commit()

    def reset_baseline(self) -> None:
        """Make the next check a 'first run' again (store silently instead of notifying)."""
        self.delete_meta("initialized")

    # -- listings ---------------------------------------------------------------
    def record_listings(
        self, hits: list[dict[str, Any]], now_iso: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Store the current search result. Returns ``(new, reappeared, removed)`` listings."""
        new: list[dict[str, Any]] = []
        reappeared: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        seen: set[str] = set()
        with self._lock:
            for hit in hits:
                uuid = hit["angebotUuid"]
                if uuid in seen:
                    continue
                seen.add(uuid)
                payload = json.dumps(hit, ensure_ascii=False)
                row = self._conn.execute(
                    "SELECT removed_at FROM listings WHERE angebot_uuid = ?", (uuid,)
                ).fetchone()
                if row is None:
                    self._conn.execute(
                        "INSERT INTO listings (angebot_uuid, first_seen, last_seen, data) VALUES (?, ?, ?, ?)",
                        (uuid, now_iso, now_iso, payload),
                    )
                    new.append(hit)
                elif row["removed_at"] is not None:
                    self._conn.execute(
                        "UPDATE listings SET removed_at = NULL, notified_at = NULL, last_seen = ?, data = ? "
                        "WHERE angebot_uuid = ?",
                        (now_iso, payload, uuid),
                    )
                    reappeared.append(hit)
                else:
                    self._conn.execute(
                        "UPDATE listings SET last_seen = ?, data = ? WHERE angebot_uuid = ?",
                        (now_iso, payload, uuid),
                    )

            rows = self._conn.execute("SELECT angebot_uuid, data FROM listings WHERE removed_at IS NULL").fetchall()
            for row in rows:
                if row["angebot_uuid"] not in seen:
                    removed.append(json.loads(row["data"]))
                    self._conn.execute(
                        "UPDATE listings SET removed_at = ? WHERE angebot_uuid = ?", (now_iso, row["angebot_uuid"])
                    )
            self._conn.commit()
        return new, reappeared, removed

    def mark_notified(self, uuids: list[str], now_iso: str) -> None:
        with self._lock:
            self._conn.executemany(
                "UPDATE listings SET notified_at = ? WHERE angebot_uuid = ?", [(now_iso, uuid) for uuid in uuids]
            )
            self._conn.commit()

    def active_count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM listings WHERE removed_at IS NULL").fetchone()
        return int(row["n"])

    def active_listings(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data, first_seen FROM listings WHERE removed_at IS NULL ORDER BY first_seen DESC"
            ).fetchall()
        listings = []
        for row in rows:
            data = json.loads(row["data"])
            data["_first_seen"] = row["first_seen"]
            listings.append(data)
        return listings

    # -- runs -------------------------------------------------------------------
    def record_run(
        self,
        started_at: str,
        finished_at: str,
        status: str,
        total_hits: int | None = None,
        new_count: int = 0,
        removed_count: int = 0,
        error: str | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO runs (started_at, finished_at, status, total_hits, new_count, removed_count, error) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (started_at, finished_at, status, total_hits, new_count, removed_count, error),
            )
            self._conn.commit()

    def last_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]
