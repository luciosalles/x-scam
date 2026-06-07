from pathlib import Path
import sqlite3
import sys
import time


def main() -> int:
    db_path = Path(sys.argv[1])
    dedupe_key = sys.argv[2]
    title = sys.argv[3]
    link = sys.argv[4]
    source = sys.argv[5]

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sent_alerts (
            dedupe_key TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            source TEXT,
            sent_at INTEGER
        )
        """
    )

    conn.execute(
        """
        INSERT INTO sent_alerts (dedupe_key, title, link, source, sent_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(dedupe_key) DO UPDATE SET
            title = excluded.title,
            link = excluded.link,
            source = excluded.source,
            sent_at = excluded.sent_at
        """,
        (dedupe_key, title, link, source, int(time.time())),
    )
    conn.commit()
    print("STORED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
