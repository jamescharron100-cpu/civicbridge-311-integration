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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS integration_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                fetched INTEGER NOT NULL DEFAULT 0,
                unmatched INTEGER NOT NULL DEFAULT 0,
                created INTEGER NOT NULL DEFAULT 0,
                updated INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,
                error_message TEXT
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


def start_run(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("""
            INSERT INTO integration_runs (started_at, status)
            VALUES (?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            "RUNNING",
        )
        )

        run_id = cursor.lastrowid
        if run_id is None:
            raise RuntimeError("SQLite did not generate a run ID")

        conn.commit()
        return run_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def finish_run(
    db_path: str,
    run_id: int,
    status: str,
    summary: dict[str, int],
    error_message: str | None = None,
) -> None:
    if status not in {"SUCCEEDED", "FAILED"}:
        raise ValueError("Status must be SUCCEEDED or FAILED")
    conn = sqlite3.connect(db_path)

    try:
        cursor = conn.execute("""
            UPDATE integration_runs
            SET finished_at = ?,
                status = ?,
                fetched = ?,
                unmatched = ?,
                created = ?,
                updated = ?,
                skipped = ?,
                error_message = ?
            WHERE run_id = ?
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            status,
            summary["fetched"],
            summary["unmatched"],
            summary["created"],
            summary["updated"],
            summary["skipped"],
            error_message,
            run_id,
        )
        )

        if cursor.rowcount != 1:
            raise ValueError(f"Run ID not found: {run_id}")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_last_successful_run_started_at(db_path: str) -> datetime | None:
    conn = sqlite3.connect(db_path)

    try:
        row = conn.execute(
            """
            SELECT started_at
            FROM integration_runs
            WHERE status = ?
            ORDER BY run_id DESC
            LIMIT 1
            """,
            ("SUCCEEDED",)
        ).fetchone()

        if row is None:
            return None

        return datetime.fromisoformat(row[0])

    finally:
        conn.close()
