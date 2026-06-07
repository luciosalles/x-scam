from pathlib import Path
import sqlite3
import sys
import time


def main() -> int:
    db_path = Path(sys.argv[1])
    dedupe_key = sys.argv[2]
    ttl_seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 86400

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

    row = conn.execute(
        "SELECT sent_at FROM sent_alerts WHERE dedupe_key = ?",
        (dedupe_key,),
    ).fetchone()

    now = int(time.time())
    if row is None or now - int(row[0]) >= ttl_seconds:
        print("ALLOW")
    else:
        print("BLOCK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
