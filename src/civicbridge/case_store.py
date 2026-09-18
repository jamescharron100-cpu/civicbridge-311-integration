import sqlite3


def initialize_database(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_cases (
                external_id TEXT PRIMARY KEY NOT NULL,
                property_id TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT NOT NULL,
                reported_at TEXT NOT NULL,
                source_updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()

def upsert_case(db_path: str, fields: dict[str, str]) -> str:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT 1 FROM maintenance_cases WHERE external_id = ?",
            (fields["ExternalId"],),
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO maintenance_cases (
                    external_id, property_id, category, priority,
                    status, description, reported_at, source_updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fields["ExternalId"],
                    fields["PropertyId"],
                    fields["Category"],
                    fields["Priority"],
                    fields["Status"],
                    fields["Description"],
                    fields["ReportedAt"],
                    fields["SourceUpdatedAt"],
                ),
            )
            result = "CREATED"
        else:
            conn.execute(
                """
                UPDATE maintenance_cases
                SET property_id = ?,
                    category = ?,
                    priority = ?,
                    status = ?,
                    description = ?,
                    reported_at = ?,
                    source_updated_at = ?
                WHERE external_id = ?
                """,
                (
                    fields["PropertyId"],
                    fields["Category"],
                    fields["Priority"],
                    fields["Status"],
                    fields["Description"],
                    fields["ReportedAt"],
                    fields["SourceUpdatedAt"],
                    fields["ExternalId"],
                ),
            )
            result = "UPDATED"

        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
