import sqlite3
from datetime import datetime, timezone

def initialize_sync_database(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS synced_records (
                source_id TEXT PRIMARY KEY NOT NULL,
                source_updated_at TEXT NOT NULL,
                destination_result TEXT NOT NULL,
                synced_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def should_skip_record(db_path: str, source_id: str, source_updated_at: datetime) -> bool:
    conn = sqlite3.connect(db_path)

    try:
        row = conn.execute(
            "SELECT source_updated_at FROM synced_records WHERE source_id = ?",
            (source_id,),
        ).fetchone()

        if row is None:
            return False

        saved_source_updated_at = datetime.fromisoformat(row[0])
        return source_updated_at <= saved_source_updated_at
    finally:
        conn.close()


def record_success(db_path: str, source_id: str, source_updated_at: datetime, destination_result: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO synced_records (
                source_id,
                source_updated_at,
                destination_result,
                synced_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                source_updated_at = excluded.source_updated_at,
                destination_result = excluded.destination_result,
                synced_at = excluded.synced_at
            """,
            (
                source_id,
                source_updated_at.isoformat(),
                destination_result,
                datetime.now(timezone.utc).isoformat()
            )
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
