from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hashlib
import html
import json
import sqlite3
import sys
import time
import urllib.parse
import urllib.request


DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/alerts.sqlite")
HOST = "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8787

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_CHECKS = [
    {
        "id": "google_trump_tariff_china",
        "type": "news",
        "url": "https://news.google.com/rss/search?q=Trump+tariff+China&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "google_ustr_section_301",
        "type": "news",
        "url": "https://news.google.com/rss/search?q=USTR+Section+301+tariff&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "google_trump_trade_brazil",
        "type": "news",
        "url": "https://news.google.com/rss/search?q=Trump+trade+Brazil&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "id": "yahoo_es",
        "type": "market",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/ES=F?interval=1d&range=5d",
    },
    {
        "id": "yahoo_nq",
        "type": "market",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?interval=1d&range=5d",
    },
    {
        "id": "yahoo_gold",
        "type": "market",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=5d",
    },
    {
        "id": "yahoo_dxy",
        "type": "market",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?interval=1d&range=5d",
    },
]


def configured_source_checks() -> list[dict]:
    sources = list(SOURCE_CHECKS)
    config_path = PROJECT_ROOT / "config" / "brazil_local_rss_app_urls.json"
    if not config_path.exists():
        return sources
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return sources
    for feed in config.get("feeds", []):
        rss_url = str(feed.get("rss_url", "")).strip()
        source_id = str(feed.get("source_id", "")).strip()
        if not feed.get("enabled") or not rss_url.startswith(("http://", "https://")):
            continue
        sources.append(
            {
                "id": f"br_{source_id or len(sources)}",
                "type": "brazil_local",
                "url": rss_url,
            }
        )
    return sources


def ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
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
        CREATE TABLE IF NOT EXISTS alert_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            level TEXT,
            regime TEXT,
            score REAL,
            title TEXT,
            source TEXT,
            link TEXT,
            tendency TEXT,
            conviction TEXT,
            win_read TEXT,
            dollar_read TEXT,
            us_read TEXT,
            reason TEXT,
            channels TEXT,
            raw_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_checks (
            source_id TEXT PRIMARY KEY,
            source_type TEXT,
            url TEXT,
            status TEXT,
            status_code INTEGER,
            latency_ms INTEGER,
            checked_at INTEGER,
            detail TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def normalize_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.strip().encode("utf-8", errors="ignore")).hexdigest()


def check_key(dedupe_key: str, ttl_seconds: int) -> dict:
    raw_key = dedupe_key
    dedupe_key = normalize_key(dedupe_key)
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT sent_at FROM sent_alerts WHERE dedupe_key = ?",
        (dedupe_key,),
    ).fetchone()
    conn.close()
    now = int(time.time())
    allowed = row is None or now - int(row[0]) >= ttl_seconds
    return {
        "status": "ALLOW" if allowed else "BLOCK",
        "dedupe_key": dedupe_key,
        "raw_key_preview": raw_key[:120],
        "ttl_seconds": ttl_seconds,
    }


def store_key(payload: dict) -> dict:
    raw_key = payload["dedupe_key"]
    dedupe_key = normalize_key(raw_key)
    conn = sqlite3.connect(DB_PATH)
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
        (
            dedupe_key,
            payload.get("title", ""),
            payload.get("link", ""),
            payload.get("source", "rss"),
            int(time.time()),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "STORED", "dedupe_key": dedupe_key, "raw_key_preview": raw_key[:120]}


def record_alert(payload: dict) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO alert_events (
            created_at, alert_type, level, regime, score, title, source, link,
            tendency, conviction, win_read, dollar_read, us_read, reason,
            channels, raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(time.time()),
            str(payload.get("alert_type", "unknown")),
            payload.get("level", ""),
            payload.get("regime", ""),
            payload.get("score", None),
            payload.get("title", ""),
            payload.get("source", ""),
            payload.get("link", ""),
            payload.get("tendency", ""),
            payload.get("conviction", ""),
            payload.get("win_read", ""),
            payload.get("dollar_read", ""),
            payload.get("us_read", ""),
            payload.get("reason", ""),
            json.dumps(payload.get("channels", [])),
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    alert_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return {"status": "RECORDED", "id": alert_id}


def list_alerts(query: dict) -> dict:
    filters = []
    params = []
    if query.get("type"):
        filters.append("alert_type = ?")
        params.append(query["type"][0])
    if query.get("level"):
        filters.append("(level = ? OR regime = ?)")
        params.extend([query["level"][0], query["level"][0]])
    if query.get("q"):
        filters.append("(title LIKE ? OR source LIKE ? OR reason LIKE ?)")
        term = f"%{query['q'][0]}%"
        params.extend([term, term, term])
    limit = min(int(query.get("limit", ["100"])[0]), 500)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"""
        SELECT * FROM alert_events
        {where}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        [*params, limit],
    ).fetchall()
    conn.close()
    return {"alerts": [dict(row) for row in rows]}


def check_source(source: dict) -> dict:
    started = time.time()
    request = urllib.request.Request(
        source["url"],
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read(512).decode("utf-8", errors="ignore").lower()
            status_code = response.status
        status = "ok"
        detail = "responded"
        if "<html" in body and "rss" not in body and "chart" not in body:
            status = "bad_content"
            detail = "html_response"
    except Exception as exc:
        status_code = 0
        status = "error"
        detail = str(exc)[:180]
    latency_ms = int((time.time() - started) * 1000)
    return {
        "source_id": source["id"],
        "source_type": source["type"],
        "url": source["url"],
        "status": status,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "checked_at": int(time.time()),
        "detail": detail,
    }


def run_source_checks() -> dict:
    results = [check_source(source) for source in configured_source_checks()]
    conn = sqlite3.connect(DB_PATH)
    for result in results:
        conn.execute(
            """
            INSERT INTO source_checks (
                source_id, source_type, url, status, status_code,
                latency_ms, checked_at, detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                source_type = excluded.source_type,
                url = excluded.url,
                status = excluded.status,
                status_code = excluded.status_code,
                latency_ms = excluded.latency_ms,
                checked_at = excluded.checked_at,
                detail = excluded.detail
            """,
            (
                result["source_id"],
                result["source_type"],
                result["url"],
                result["status"],
                result["status_code"],
                result["latency_ms"],
                result["checked_at"],
                result["detail"],
            ),
        )
    conn.commit()
    conn.close()
    return {"sources": results}


def list_source_checks() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT * FROM source_checks
        ORDER BY source_type, source_id
        """
    ).fetchall()
    conn.close()
    if not rows:
        return run_source_checks()
    return {"sources": [dict(row) for row in rows]}


def dashboard_html() -> bytes:
    return """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Macro Alerts Brasil</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b0c0f;
      --bg2: #111318;
      --panel: rgba(20, 23, 28, 0.92);
      --panel2: rgba(24, 27, 33, 0.96);
      --line: rgba(255,255,255,0.08);
      --line-strong: rgba(255,255,255,0.14);
      --text: #f2f4f7;
      --muted: #98a2ad;
      --muted2: #6c7682;
      --ok: #48d08f;
      --warn: #f3b84c;
      --bad: #ff5b61;
      --accent: #7fb0ff;
      --shadow: 0 22px 60px rgba(0,0,0,0.45);
      --radius: 20px;
      --radius-sm: 14px;
      --sidebar: 260px;
      --rail: 320px;
    }
    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    html { overflow-y: auto; overflow-x: hidden; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.05), transparent 26%),
        radial-gradient(circle at top right, rgba(127,176,255,0.07), transparent 30%),
        linear-gradient(180deg, #090a0d 0%, #0d1014 55%, #090a0d 100%);
      color: var(--text);
      font: 14px/1.45 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      overflow-y: auto;
      overflow-x: hidden;
    }
    * {
      scrollbar-width: thin;
      scrollbar-color: var(--border-accent) transparent;
    }
    *::-webkit-scrollbar {
      width: 10px;
      height: 10px;
    }
    *::-webkit-scrollbar-track {
      background: transparent;
    }
    *::-webkit-scrollbar-thumb {
      background: var(--border-accent);
      border-radius: 999px;
      border: 2px solid transparent;
      background-clip: content-box;
    }
    a { color: var(--accent); text-decoration: none; }
    .app {
      display: grid;
      grid-template-columns: var(--sidebar) 1fr var(--rail);
      min-height: 100svh;
    }
    .sidebar {
      padding: 22px 16px;
      border-right: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(17,19,24,0.98), rgba(13,15,19,0.94));
      box-shadow: inset -1px 0 0 rgba(255,255,255,0.03);
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 6px 4px 14px;
      border-bottom: 1px solid var(--line);
    }
    .brand-mark {
      width: 42px;
      height: 42px;
      border-radius: 14px;
      display: grid;
      place-items: center;
      background: linear-gradient(180deg, rgba(255,196,60,0.18), rgba(255,196,60,0.06));
      color: #ffc94d;
      border: 1px solid rgba(255,196,60,0.25);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
      font-size: 20px;
    }
    .brand h1 {
      margin: 0;
      font: 700 15px/1.1 ui-sans-serif, system-ui, sans-serif;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .brand span {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
    }
    .nav { display: grid; gap: 10px; }
    .nav a {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 13px 14px;
      border-radius: 14px;
      color: var(--text);
      border: 1px solid transparent;
      background: transparent;
    }
    .nav a.active {
      background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
      border-color: var(--line-strong);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }
    .nav .tag {
      margin-left: auto;
      color: var(--muted);
      font-size: 12px;
      padding: 2px 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
    }
    .sidebar-card {
      margin-top: auto;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015));
      box-shadow: var(--shadow);
    }
    .sidebar-card .label {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 11px;
      margin-bottom: 10px;
    }
    .sidebar-card .title {
      font-size: 16px;
      font-weight: 700;
      margin: 0 0 8px;
    }
    .sidebar-card .sub {
      color: var(--muted);
      margin: 0 0 14px;
    }
    .sidebar-card button {
      width: 100%;
      border: 1px solid rgba(255,196,60,0.24);
      background: linear-gradient(180deg, rgba(255,196,60,0.24), rgba(255,196,60,0.12));
      color: #fff1cb;
      font-weight: 700;
      padding: 11px 14px;
      border-radius: 13px;
    }
    .content {
      min-width: 0;
      overflow: visible;
      padding: 18px 18px 20px;
    }
    .topbar {
      display: grid;
      grid-template-columns: 1fr minmax(260px, 380px) auto;
      gap: 16px;
      align-items: center;
      margin-bottom: 14px;
    }
    .hero h2 {
      margin: 0;
      font: 800 clamp(26px, 2.8vw, 40px)/1.02 ui-sans-serif, system-ui, sans-serif;
      letter-spacing: -0.03em;
    }
    .hero p {
      margin: 8px 0 0;
      color: var(--muted);
    }
    .searchbox {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 13px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(10,12,15,0.72);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }
    .searchbox input {
      width: 100%;
      border: 0;
      outline: 0;
      background: transparent;
      color: var(--text);
      font: inherit;
    }
    .status-pills {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .status-pills .pill {
      padding: 10px 13px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
      color: var(--text);
      display: inline-flex;
      align-items: center;
      gap: 8px;
      white-space: nowrap;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--ok);
      box-shadow: 0 0 0 4px rgba(72,208,143,0.12);
    }
    .dot.warn {
      background: var(--warn);
      box-shadow: 0 0 0 4px rgba(243,184,76,0.12);
    }
    .dot.bad {
      background: var(--bad);
      box-shadow: 0 0 0 4px rgba(255,91,97,0.12);
    }
    .workspace {
      display: grid;
      grid-template-columns: minmax(0, 1.6fr) minmax(0, 0.9fr);
      gap: 14px;
      align-items: start;
    }
    .stack { display: grid; gap: 14px; min-width: 0; }
    .card {
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: linear-gradient(180deg, rgba(23,26,32,0.94), rgba(14,16,19,0.96));
      box-shadow: var(--shadow), inset 0 1px 0 var(--border-subtle);
      overflow: hidden;
      min-width: 0;
      border-top-color: var(--border-accent);
    }
    .card-head {
      padding: 16px 18px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
    }
    .card-head h3 {
      margin: 0;
      font-size: 14px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--steel-light);
    }
    .card-head .sub {
      margin: 6px 0 0;
      color: var(--steel-mid);
      font-size: 12px;
    }
    .badge {
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
      background: rgba(255,255,255,0.02);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
    }
    .main-alert {
      padding: 18px 18px 16px;
      display: grid;
      gap: 14px;
    }
    .main-alert-top {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .alert-type {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.03);
      font-weight: 800;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
    }
    .alert-type .flag {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--warn);
      box-shadow: 0 0 0 4px rgba(243,184,76,0.12);
    }
    .alert-title {
      margin: 2px 0 0;
      font: 800 clamp(22px, 2vw, 30px)/1.08 ui-sans-serif, system-ui, sans-serif;
      letter-spacing: -0.02em;
      max-width: 24ch;
    }
    .alert-grid {
      display: grid;
      grid-template-columns: 1.08fr 0.92fr;
      gap: 14px;
      min-width: 0;
    }
    .alert-panel {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      background: rgba(255,255,255,0.025);
      min-width: 0;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }
    .alert-panel h4 {
      margin: 0 0 12px;
      color: var(--steel-dim);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 10px;
    }
    .stat-row { display: grid; gap: 10px; }
    .stat {
      display: grid;
      grid-template-columns: 96px 1fr;
      gap: 10px;
      align-items: start;
      min-width: 0;
    }
    .stat strong {
      font: 700 12px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace;
      letter-spacing: 0.08em;
      color: #dce2ea;
      text-transform: uppercase;
    }
    .stat span {
      color: var(--text);
      min-width: 0;
      overflow-wrap: anywhere;
    }
    .market-strip {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }
    .market-tile {
      padding: 16px 16px 14px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015));
      min-width: 0;
    }
    .market-tile .symbol {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 10px;
    }
    .market-tile .value {
      font: 800 clamp(18px, 1.8vw, 24px)/1.02 ui-monospace, SFMono-Regular, Menlo, monospace;
      margin-bottom: 6px;
    }
    .market-tile .delta {
      color: var(--muted);
      font-size: 13px;
    }
    .market-tile .delta.up { color: var(--ok); }
    .market-tile .delta.down { color: var(--bad); }
    .list { display: grid; gap: 0; }
    .list-item {
      display: grid;
      grid-template-columns: 104px 110px minmax(0, 1fr);
      gap: 10px 12px;
      align-items: center;
      padding: 12px 16px;
      border-top: 1px solid rgba(34,37,43,0.6);
      min-width: 0;
      transition: background 80ms ease;
    }
    .list-item:first-child { border-top: 0; }
    .list-item:hover { background: rgba(255,255,255,0.025); }
    .list-time {
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
      font-family: var(--font-display);
      line-height: 1;
    }
    .list-tag {
      color: var(--text);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      min-width: 0;
      justify-self: start;
    }
    .list-text {
      min-width: 0;
      overflow: hidden;
    }
    .list-text .title {
      font-weight: 700;
      margin-bottom: 4px;
      overflow-wrap: anywhere;
      line-height: 1.25;
    }
    .list-text .meta {
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
      line-height: 1.35;
    }
    .rail {
      padding-top: 58px;
      display: grid;
      gap: 14px;
    }
    .rail .mini {
      padding: 18px 18px 16px;
      display: grid;
      gap: 10px;
    }
    .mini-row {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      color: var(--muted);
    }
    .mini-row strong { color: var(--text); font-size: 13px; }
    .mono { font: 700 13px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; }
    .bad { color: var(--bad); }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    .table-wrap {
      overflow: auto;
      max-height: 420px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      padding: 12px 14px;
      border-bottom: 1px solid rgba(34,37,43,0.6);
      text-align: left;
      vertical-align: top;
      white-space: normal;
    }
    th {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      position: sticky;
      top: 0;
      background: rgba(14,16,19,0.94);
      backdrop-filter: blur(8px);
      z-index: 1;
    }
    td {
      color: var(--text);
      overflow-wrap: anywhere;
    }
    tr:hover td {
      background: rgba(255,255,255,0.02);
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 12px;
      white-space: nowrap;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
    }
    .pill.RED, .pill.RISK_OFF { color: var(--bad); }
    .pill.ORANGE, .pill.YELLOW { color: var(--warn); }
    .pill.RISK_ON, .pill.ok { color: var(--ok); }
    .toolbar {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      padding: 0 2px 2px;
    }
    .filters {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
      gap: 10px;
      min-width: 0;
      flex: 1;
    }
    input, select, button {
      background: rgba(10,12,15,0.88);
      border: 1px solid var(--line);
      color: var(--text);
      border-radius: 12px;
      padding: 12px 14px;
      font: inherit;
      min-width: 0;
    }
    button {
      cursor: pointer;
      background: linear-gradient(180deg, rgba(127,176,255,0.18), rgba(127,176,255,0.1));
      border-color: rgba(127,176,255,0.26);
    }
    .subtle-btn {
      background: rgba(255,255,255,0.04);
      border-color: var(--line);
    }
    input:focus, select:focus, button:focus-visible,
    .searchbox:focus-within {
      box-shadow: var(--shadow-focus);
      border-color: var(--border-accent);
      outline: none;
    }
    @media (max-width: 1440px) {
      .app { grid-template-columns: var(--sidebar) 1fr 240px; }
      .rail { width: 240px; }
    }
    @media (max-width: 1320px) {
      .app { grid-template-columns: 86px 1fr; }
      .rail { display: none; }
      .sidebar .brand span, .sidebar .nav span, .sidebar .sidebar-card { display: none; }
      .sidebar { padding: 18px 10px; }
      .sidebar .nav a { justify-content: center; padding: 14px 10px; }
      .sidebar .nav .tag { display: none; }
      .sidebar .brand { justify-content: center; }
    }
    @media (max-width: 1100px) {
      body { overflow: auto; }
      .app { grid-template-columns: 1fr; }
      .sidebar { display: none; }
      .topbar { grid-template-columns: 1fr; }
      .status-pills { justify-content: flex-start; }
      .workspace { grid-template-columns: 1fr; }
      .market-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .alert-grid { grid-template-columns: 1fr; }
      .filters { grid-template-columns: 1fr; }
      .list-item { grid-template-columns: 88px minmax(0, 1fr); }
      .list-item .list-tag { display: none; }
    }
    @media (max-width: 768px) {
      .content { padding: 14px 12px 16px; }
      .workspace { gap: 12px; }
      .card-head, .main-alert { padding-left: 14px; padding-right: 14px; }
      .market-strip, .alert-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">?</div>
        <div>
          <h1>Macro Alerts</h1>
          <span>Brasil | Market bias | Live monitoring</span>
        </div>
      </div>
      <nav class="nav">
        <a class="active" href="/dashboard">Dashboard <span class="tag">Home</span></a>
        <a href="/dashboard/alerts">Alert Feed <span class="tag">Live</span></a>
        <a href="/dashboard/health">Health <span class="tag">OK</span></a>
        <a href="/dashboard/history">History <span class="tag">DB</span></a>
        <a href="/dashboard/integrations">Integrations <span class="tag">WS</span></a>
        <a href="/dashboard/rtd">RTD Flow <span class="tag">Soon</span></a>
      </nav>
      <div class="sidebar-card">
        <div class="label">Proximo passo</div>
        <div class="title">Home shell first</div>
        <p class="sub">Cards sem excesso, sem overlap, pronto para ligar dados reais depois.</p>
        <button id="refresh">Refresh live</button>
      </div>
    </aside>

    <section class="content">
      <div class="topbar">
        <div class="hero">
          <h2>Dashboard</h2>
          <p>Home enxuta para bias macro, fontes e alerta principal.</p>
        </div>
        <div class="searchbox">
          <span style="color:var(--muted)">?</span>
          <input id="q" placeholder="Buscar titulo, fonte, motivo">
        </div>
        <div class="status-pills">
          <div class="pill"><span class="dot"></span><span>LIVE</span></div>
          <div class="pill"><span class="dot warn"></span><span>SOURCES OK</span></div>
          <div class="pill"><span class="dot bad"></span><span id="summaryState">RISK MONITOR</span></div>
        </div>
      </div>
      <div class="toolbar" data-view="alerts history" style="margin:0 0 18px; padding:0;">
        <div class="filters" style="grid-template-columns: repeat(4, minmax(0, 1fr));">
          <div class="badge">Feed completo</div>
          <div class="badge" id="alertsCount">0 alerts</div>
          <div class="badge" id="alertsRed">0 red</div>
          <div class="badge" id="alertsRecent">0 recentes</div>
        </div>
      </div>

      <div class="workspace">
        <div class="stack">
          <article class="card">
            <div class="card-head">
              <div>
                <h3>Main Alert</h3>
                <div class="sub">Alerta principal atual, sem ru?do de canal.</div>
              </div>
              <div class="badge" id="mainBadge">Aguardando sinal</div>
            </div>
            <div class="main-alert" id="mainAlert">
              <div class="main-alert-top">
                <div class="alert-type"><span class="flag"></span><span id="mainType">NO ALERT</span></div>
                <div class="alert-meta">
                  <span id="mainTime">-</span>
                  <span class="badge" id="mainSeverity">-</span>
                </div>
              </div>
              <div class="alert-title" id="mainTitle">Sem alerta principal no momento</div>
              <div class="alert-grid">
                <div class="alert-panel">
                  <h4>Leituras</h4>
                  <div class="stat-row">
                    <div class="stat"><strong>Regime</strong><span id="mainRegime">-</span></div>
                    <div class="stat"><strong>Tendencia</strong><span id="mainTendency">-</span></div>
                    <div class="stat"><strong>Conviccao</strong><span id="mainConviction">-</span></div>
                    <div class="stat"><strong>WIN</strong><span id="mainWin">-</span></div>
                    <div class="stat"><strong>Dolar</strong><span id="mainDollar">-</span></div>
                    <div class="stat"><strong>ES/NQ</strong><span id="mainUs">-</span></div>
                  </div>
                </div>
                <div class="alert-panel">
                  <h4>O que mudou</h4>
                  <div class="stat-row">
                    <div class="stat"><strong>Motivo</strong><span id="mainReason">-</span></div>
                    <div class="stat"><strong>Confirmar</strong><span id="mainConfirm">-</span></div>
                    <div class="stat"><strong>Invalidar</strong><span id="mainInvalidate">-</span></div>
                    <div class="stat"><strong>Fonte</strong><span id="mainSource">-</span></div>
                  </div>
                </div>
              </div>
            </div>
          </article>

          <article class="card">
            <div class="card-head">
              <div>
                <h3>Market Strip</h3>
                <div class="sub">Quatro leituras-chave, visual limpo e compacto.</div>
              </div>
              <div class="badge">Bias snapshots</div>
            </div>
            <div class="main-alert" style="padding-top:16px;">
              <div class="market-strip" id="marketStrip"></div>
            </div>
          </article>

          <article class="card">
            <div class="card-head">
              <div>
                <h3>Recent Alerts</h3>
                <div class="sub">Feed curto para validar qualidade sem poluir a Home.</div>
              </div>
              <div class="badge">Latest 8</div>
            </div>
            <div class="toolbar" style="padding:14px 18px 0;">
              <div class="filters">
                <select id="type">
                  <option value="">Todos os tipos</option>
                  <option value="news">News</option>
                  <option value="market">Market</option>
                  <option value="brazil_local">Brasil Local</option>
                  <option value="bcb_direct">BCB Direct</option>
                </select>
                <select id="level">
                  <option value="">Todos os niveis</option>
                  <option>YELLOW</option>
                  <option>ORANGE</option>
                  <option>RED</option>
                  <option>RISK_ON</option>
                  <option>RISK_OFF</option>
                </select>
                <select id="regime">
                  <option value="">Todos os regimes</option>
                  <option>BR_LOCAL</option>
                  <option>GLOBAL_RISK</option>
                  <option>RISK_OFF</option>
                  <option>RISK_ON</option>
                </select>
                <button id="checkSources" class="subtle-btn">Checar fontes</button>
              </div>
            </div>
            <div class="list" id="alerts"></div>
          </article>

          <article class="card" data-history-card>
            <div class="card-head">
              <div>
                <h3>Alert History</h3>
                <div class="sub">Tabela tecnica para investigar o que disparou.</div>
              </div>
              <div class="badge">DB log</div>
            </div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Hora</th><th>Tipo</th><th>Nivel</th><th>Regime</th><th>Tendencia</th><th>WIN</th><th>Titulo</th><th>Fonte</th>
                  </tr>
                </thead>
                <tbody id="history"></tbody>
              </table>
            </div>
          </article>
        </div>

        <aside class="rail">
          <article class="card mini">
            <div class="card-head" style="padding:0 0 8px;border-bottom:0;">
              <div>
                <h3>System Rail</h3>
                <div class="sub">Saude resumida sem ocupar a Home.</div>
              </div>
            </div>
            <div class="mini-row"><strong>Sources</strong><span id="railSources" class="mono">-</span></div>
            <div class="mini-row"><strong>Stale</strong><span id="railStale" class="mono">-</span></div>
            <div class="mini-row"><strong>Last check</strong><span id="railCheck" class="mono">-</span></div>
          </article>
          <article class="card mini" data-health-card>
            <div class="card-head" style="padding:0 0 8px;border-bottom:0;">
              <div>
                <h3>Health</h3>
                <div class="sub">Falhas e latencia das fontes.</div>
              </div>
            </div>
            <div id="sourcesMini" class="list"></div>
          </article>
          <article class="card mini">
            <div class="card-head" style="padding:0 0 8px;border-bottom:0;">
              <div>
                <h3>View Modes</h3>
                <div class="sub">Home, alerts, health, history, integrations, RTD.</div>
              </div>
            </div>
            <div class="mini-row"><strong>Mode</strong><span class="pill ok">Home shell</span></div>
            <div class="mini-row"><strong>RTD</strong><span class="pill warn">Separate page</span></div>
            <div class="mini-row"><strong>Integrations</strong><span class="pill">Telegram / Discord</span></div>
          </article>
        </aside>
      </div>

      <div class="workspace" style="grid-template-columns:1fr; margin-top:18px;">
        <article class="card">
          <div class="card-head">
            <div>
              <h3>Sources</h3>
              <div class="sub">Lista tecnica para validar o estado das fontes.</div>
            </div>
            <div class="badge">Live status</div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Fonte</th><th>Tipo</th><th>Status</th><th>HTTP</th><th>Latencia</th><th>Detalhe</th></tr>
              </thead>
              <tbody id="sources"></tbody>
            </table>
          </div>
        </article>
      </div>
    </section>
  </div>
  <script>
    const $ = (id) => document.getElementById(id);
    const fmt = (ts) => ts ? new Date(ts * 1000).toLocaleString() : '-';
    const levelLabel = (value) => ({
      RED: 'Vermelho',
      ORANGE: 'Laranja',
      YELLOW: 'Amarelo',
      RISK_ON: 'Vi?s de alta',
      RISK_OFF: 'Vi?s de baixa'
    })[value] || value || '';
    const esc = (value) => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
    const first = (items) => (items && items.length ? items[0] : null);
    const currentView = (() => {
      const p = location.pathname.toLowerCase();
      if (p.endsWith('/alerts')) return 'alerts';
      if (p.endsWith('/health')) return 'health';
      if (p.endsWith('/history')) return 'history';
      if (p.endsWith('/integrations')) return 'integrations';
      if (p.endsWith('/rtd')) return 'rtd';
      return 'home';
    })();
    function applyView() {
      const stackCards = Array.from(document.querySelectorAll('.stack > .card'));
      const rail = document.querySelector('.rail');
      const sourcesCard = document.querySelector('.content > .workspace + .workspace .card');
      const search = document.querySelector('.searchbox');
      const heroTitle = document.querySelector('.hero h2');
      const heroSub = document.querySelector('.hero p');
      const navs = Array.from(document.querySelectorAll('[data-nav]'));
      const setCardVisibility = (predicate) => stackCards.forEach((card, idx) => { card.style.display = predicate(card, idx) ? '' : 'none'; });
      const titleMap = {
        home: ['Dashboard', 'Home enxuta para bias macro, fontes e alerta principal.'],
        alerts: ['Alert Feed', 'Lista completa para depurar e acompanhar alertas.'],
        health: ['Health', 'Saude das fontes, latencia e falhas.'],
        history: ['History', 'Historico tecnico e dedupe.'],
        integrations: ['Integrations', 'Telegram, Discord e testes de envio.'],
        rtd: ['RTD Flow', 'Fluxo separado para scanner Profit RTD.']
      };
      const pair = titleMap[currentView] || titleMap.home;
      heroTitle.textContent = pair[0];
      heroSub.textContent = pair[1];
      search.style.display = (currentView === 'alerts' || currentView === 'history') ? 'flex' : 'none';
      navs.forEach(link => link.classList.toggle('active', link.getAttribute('data-nav') === currentView || (currentView === 'home' && link.getAttribute('data-nav') === 'home')));
      if (currentView === 'home') {
        setCardVisibility(() => true);
        if (rail) rail.style.display = 'none';
        if (sourcesCard) sourcesCard.style.display = '';
      } else if (currentView === 'alerts') {
        setCardVisibility((card, idx) => idx === 0 || idx === 1 || idx === 2 || idx === 3);
        if (rail) rail.style.display = 'none';
        if (sourcesCard) sourcesCard.style.display = 'none';
      } else if (currentView === 'health') {
        setCardVisibility((card, idx) => idx === 0 || idx === 4);
        if (rail) rail.style.display = '';
        if (sourcesCard) sourcesCard.style.display = '';
      } else if (currentView === 'history') {
        setCardVisibility((card, idx) => idx === 3);
        if (rail) rail.style.display = 'none';
        if (sourcesCard) sourcesCard.style.display = 'none';
      } else if (currentView === 'integrations') {
        setCardVisibility(() => false);
        if (rail) rail.style.display = 'none';
        if (sourcesCard) sourcesCard.style.display = 'none';
        document.querySelector('.stack').insertAdjacentHTML('afterbegin', `
          <article class="card">
            <div class="card-head">
              <div>
                <h3>Onboarding</h3>
                <div class="sub">Fluxo guiado para o usuario final conectar canais sem ver detalhe tecnico demais.</div>
              </div>
              <div class="badge">5 passos</div>
            </div>
            <div class="main-alert" style="gap:14px;">
              <div class="alert-panel"><h4>1. Escolha o canal</h4><div class="stat-row"><div class="stat"><strong>Telegram</strong><span>Ideal para alerta rapido e mobile.</span></div><div class="stat"><strong>Discord</strong><span>Ideal para grupo tecnico e canal persistente.</span></div></div></div>
              <div class="alert-panel"><h4>2. Conecte</h4><div class="stat-row"><div class="stat"><strong>Telegram</strong><span>Colar bot token e chat_id.</span></div><div class="stat"><strong>Discord</strong><span>Colar webhook URL do canal.</span></div></div></div>
              <div class="alert-panel"><h4>3. Teste</h4><div class="stat-row"><div class="stat"><strong>Smoke test</strong><span>Enviar 1 alerta falso e confirmar entrega.</span></div></div></div>
              <div class="alert-panel"><h4>4. Ajuste o ruido</h4><div class="stat-row"><div class="stat"><strong>Densidade</strong><span>Escolher agressivo, equilibrado ou ultra seletivo.</span></div></div></div>
              <div class="alert-panel"><h4>5. Ative live</h4><div class="stat-row"><div class="stat"><strong>Go live</strong><span>Ligar o fluxo de producao depois que a entrega funcionar.</span></div></div></div>
            </div>
          </article>
        `);
      } else if (currentView === 'rtd') {
        setCardVisibility(() => false);
        if (rail) rail.style.display = 'none';
        if (sourcesCard) sourcesCard.style.display = 'none';
        document.querySelector('.stack').insertAdjacentHTML('afterbegin', `
          <article class="card">
            <div class="card-head">
              <div>
                <h3>RTD Flow</h3>
                <div class="sub">Painel pronto para o scanner Profit RTD e leitura de micro-vies em tempo quase real.</div>
              </div>
              <div class="badge">Pipeline</div>
            </div>
            <div class="main-alert" style="gap:14px;">
              <div class="market-strip" style="grid-template-columns: repeat(3, minmax(0, 1fr));">
                <div class="market-tile"><div class="symbol">Estado</div><div class="value">Aguardando RTD</div><div class="delta">feed separado da Home</div></div>
                <div class="market-tile"><div class="symbol">Buffer</div><div class="value">Parquet</div><div class="delta">historico e replay</div></div>
                <div class="market-tile"><div class="symbol">Bias</div><div class="value">Neutro</div><div class="delta">sem scanner conectado</div></div>
              </div>
              <div class="alert-panel">
                <h4>Arquitetura operacional</h4>
                <div class="stat-row">
                  <div class="stat"><strong>Input</strong><span>Profit RTD scanner e serie de ticks normalizada.</span></div>
                  <div class="stat"><strong>Processing</strong><span>Delta detection, cache e agregacao de fluxo.</span></div>
                  <div class="stat"><strong>Output</strong><span>Bias intraday, historico parquet e alertas derivados.</span></div>
                </div>
              </div>
              <div class="alert-panel">
                <h4>Checklist de produto</h4>
                <div class="stat-row">
                  <div class="stat"><strong>1</strong><span>Scanner RTD validado.</span></div>
                  <div class="stat"><strong>2</strong><span>Buffer com ultimos ticks.</span></div>
                  <div class="stat"><strong>3</strong><span>Feed pronto para dashboard e bias.</span></div>
                </div>
              </div>
            </div>
          </article>
        `);
      }
    }

    async function loadAlerts() {
      const params = new URLSearchParams();
      if ($('type').value) params.set('type', $('type').value);
      if ($('level').value) params.set('level', $('level').value);
      if ($('regime').value) params.set('regime', $('regime').value);
      if ($('q').value) params.set('q', $('q').value);
      const alertLimit = currentView === 'alerts' ? 200 : currentView === 'history' ? 120 : 80;
      params.set('limit', String(alertLimit));
      const res = await fetch('/api/alerts?' + params.toString());
      const data = await res.json();
      const alerts = data.alerts || [];
      renderAlerts(alerts);
      renderHistory(alerts);
      renderMain(alerts);
      renderMarketStrip(alerts);
    }

    function renderMain(alerts) {
      const main = first(alerts);
      if (!main) {
        $('mainBadge').textContent = 'Aguardando sinal';
        $('mainType').textContent = 'NO ALERT';
        $('mainTime').textContent = '-';
        $('mainSeverity').textContent = '-';
        $('mainTitle').textContent = 'Sem alerta principal no momento';
        $('mainRegime').textContent = '-';
        $('mainTendency').textContent = '-';
        $('mainConviction').textContent = '-';
        $('mainWin').textContent = '-';
        $('mainDollar').textContent = '-';
        $('mainUs').textContent = '-';
        $('mainReason').textContent = '-';
        $('mainConfirm').textContent = '-';
        $('mainInvalidate').textContent = '-';
        $('mainSource').textContent = '-';
        $('summaryState').textContent = 'RISK MONITOR';
        return;
      }
      const regime = main.regime || main.level || '-';
      const tendency = main.tendency || main.direction || '-';
      const conviction = main.conviction || main.confidence || '-';
      $('mainBadge').textContent = (main.level || main.regime || 'SINAL').toString();
      $('mainType').textContent = (main.alert_type || 'ALERT').toUpperCase();
      $('mainTime').textContent = fmt(main.created_at);
      $('mainSeverity').textContent = levelLabel(main.level || main.regime || '');
      $('mainTitle').textContent = main.title || main.regime || '-';
      $('mainRegime').textContent = regime;
      $('mainTendency').textContent = tendency;
      $('mainConviction').textContent = conviction;
      $('mainWin').textContent = main.win_read || main.winPlan || '-';
      $('mainDollar').textContent = main.dollar_read || main.dolar_read || '-';
      $('mainUs').textContent = main.us_read || main.esnq_read || '-';
      $('mainReason').textContent = main.reason || '-';
      $('mainConfirm').textContent = main.confirm || main.confirm_text || main.confirmation || '-';
      $('mainInvalidate').textContent = main.invalidate || main.invalidate_text || main.invalidar || '-';
      $('mainSource').textContent = main.source || '-';
      $('summaryState').textContent = (main.level || main.regime || 'RISK MONITOR').toString();
    }

    function renderAlerts(alerts) {
      const recent = currentView === 'alerts' ? alerts.slice(0, 30) : alerts.slice(0, 8);
      const total = alerts.length;
      const red = alerts.filter(a => String(a.level || a.regime || '').toUpperCase() === 'RED' || String(a.level || a.regime || '').toUpperCase() === 'RISK_OFF').length;
      const orange = alerts.filter(a => String(a.level || a.regime || '').toUpperCase() === 'ORANGE').length;
      const yellow = alerts.filter(a => String(a.level || a.regime || '').toUpperCase() === 'YELLOW').length;
      const topTrend = alerts.find(a => a.tendency)?.tendency || alerts.find(a => a.direction)?.direction || 'Sem tendencia forte';
      const feedTitle = currentView === 'alerts' ? 'Alert Feed completo' : 'Recent Alerts';
      const feedSub = currentView === 'alerts'
        ? 'Lista densa para depurar, comparar e validar o que realmente merece canal.'
        : 'Feed curto para validar qualidade sem poluir a Home.';
      const feedBadge = currentView === 'alerts' ? `Latest ${recent.length}` : 'Latest 8';
      const alertsCard = document.querySelector('.stack > .card:nth-of-type(3)');
      if (alertsCard) {
        const head = alertsCard.querySelector('.card-head h3');
        const sub = alertsCard.querySelector('.card-head .sub');
        const badge = alertsCard.querySelector('.card-head .badge');
        if (head) head.textContent = feedTitle;
        if (sub) sub.textContent = feedSub;
        if (badge) badge.textContent = feedBadge;
        if (currentView === 'alerts' && !document.getElementById('alertsSummary')) {
          const toolbar = alertsCard.querySelector('.toolbar');
          const summaryHtml = `
            <div id="alertsSummary" style="padding: 14px 18px 0;">
              <div class="market-strip" style="grid-template-columns: repeat(4, minmax(0, 1fr));">
                <div class="market-tile"><div class="symbol">Total</div><div class="value">${total}</div><div class="delta">alertas carregados</div></div>
                <div class="market-tile"><div class="symbol">Red / Risk off</div><div class="value">${red}</div><div class="delta down">impacto forte</div></div>
                <div class="market-tile"><div class="symbol">Orange / Yellow</div><div class="value">${orange + yellow}</div><div class="delta">ruido util</div></div>
                <div class="market-tile"><div class="symbol">Tendencia dominante</div><div class="value" style="font-size:18px; line-height:1.15;">${esc(topTrend)}</div><div class="delta">ultimo viés visto</div></div>
              </div>
            </div>
          `;
          if (toolbar && toolbar.nextElementSibling) {
            toolbar.insertAdjacentHTML('afterend', summaryHtml);
          } else {
            alertsCard.insertAdjacentHTML('beforeend', summaryHtml);
          }
        }
      }
      $('alerts').innerHTML = recent.length ? recent.map(a => `
        <div class="list-item">
          <div class="list-time">${fmt(a.created_at)}</div>
          <div class="list-tag">${esc(a.alert_type || a.level || a.regime || '')}</div>
          <div class="list-text">
            <div class="title">${esc(a.title || a.regime || 'Sem titulo')}</div>
            <div class="meta">${esc(a.tendency || a.direction || '')}${a.source ? ' · ' + esc(a.source) : ''}${a.reason ? ' · ' + esc(a.reason) : ''}</div>
          </div>
        </div>
      `).join('') : '<div class="list-item"><div class="list-time">-</div><div class="list-tag">-</div><div class="list-text"><div class="title">Sem alertas</div><div class="meta">Nenhum item recente retornou da API.</div></div></div>';
    }

    function renderMarketStrip(alerts) {
      const market = alerts.find(a => String(a.alert_type || '').toLowerCase() === 'market') || first(alerts);
      if (!market) {
        $('marketStrip').innerHTML = `
          <div class="market-tile"><div class="symbol">WIN</div><div class="value">-</div><div class="delta">Aguardando feed</div></div>
          <div class="market-tile"><div class="symbol">Dolar</div><div class="value">-</div><div class="delta">Aguardando feed</div></div>
          <div class="market-tile"><div class="symbol">ES / NQ</div><div class="value">-</div><div class="delta">Aguardando feed</div></div>
          <div class="market-tile"><div class="symbol">DXY / Gold</div><div class="value">-</div><div class="delta">Aguardando feed</div></div>
        `;
        return;
      }
      const tone = (market.level || market.regime || '').toString();
      const score = market.score != null ? `${market.score}` : '-';
      const win = market.win_read || market.winPlan || '-';
      const dollar = market.dollar_read || market.dolar_read || '-';
      const us = market.us_read || market.esnq_read || '-';
      const reason = market.reason || market.title || '-';
      $('marketStrip').innerHTML = `
        <div class="market-tile">
          <div class="symbol">Regime</div>
          <div class="value">${esc(market.regime || market.level || '-')}</div>
          <div class="delta ${esc(tone)}">${esc(market.tendency || market.direction || market.conviction || '-')}</div>
        </div>
        <div class="market-tile">
          <div class="symbol">Score</div>
          <div class="value">${esc(score)}</div>
          <div class="delta">Convicção ${esc(market.conviction || '-')}</div>
        </div>
        <div class="market-tile">
          <div class="symbol">WIN</div>
          <div class="value">${esc(win)}</div>
          <div class="delta">Leitura principal</div>
        </div>
        <div class="market-tile">
          <div class="symbol">Dolar / ES</div>
          <div class="value">${esc(dollar)}</div>
          <div class="delta">${esc(us)}</div>
        </div>
      `;
      $('mainReason').textContent = reason;
    }

    function renderHistory(alerts) {
      const rows = alerts.slice(0, 25);
      const totals = {
        total: alerts.length,
        red: alerts.filter(a => String(a.level || a.regime || '').toUpperCase() === 'RED' || String(a.level || a.regime || '').toUpperCase() === 'RISK_OFF').length,
        orange: alerts.filter(a => String(a.level || a.regime || '').toUpperCase() === 'ORANGE').length,
        yellow: alerts.filter(a => String(a.level || a.regime || '').toUpperCase() === 'YELLOW').length,
      };
      const topReason = alerts.find(a => a.reason)?.reason || 'Sem motivo forte nos registros recentes.';
      const historyCard = document.querySelector('[data-history-card]');
      if (historyCard && !document.getElementById('historySummary')) {
        historyCard.insertAdjacentHTML('afterbegin', `
          <div id="historySummary" style="padding: 16px 20px 0;">
            <div class="market-strip" style="grid-template-columns: repeat(4, minmax(0, 1fr));">
              <div class="market-tile"><div class="symbol">Total</div><div class="value" id="histTotal">0</div><div class="delta">alertas salvos</div></div>
              <div class="market-tile"><div class="symbol">Red</div><div class="value" id="histRed">0</div><div class="delta down">sinais fortes</div></div>
              <div class="market-tile"><div class="symbol">Orange / Yellow</div><div class="value" id="histSoft">0</div><div class="delta">ruido util</div></div>
              <div class="market-tile"><div class="symbol">Ultimo motivo</div><div class="value" id="histReason" style="font-size:14px; line-height:1.2;">-</div><div class="delta">base para dedupe</div></div>
            </div>
          </div>
        `);
      }
      if ($('histTotal')) $('histTotal').textContent = String(totals.total);
      if ($('histRed')) $('histRed').textContent = String(totals.red);
      if ($('histSoft')) $('histSoft').textContent = String(totals.orange + totals.yellow);
      if ($('histReason')) $('histReason').textContent = topReason.length > 60 ? topReason.slice(0, 60) + '?' : topReason;
      $('history').innerHTML = rows.map(a => `
        <tr>
          <td>${fmt(a.created_at)}</td>
          <td>${esc(a.alert_type || '')}</td>
          <td><span class="pill ${esc(a.level || a.regime || '')}">${esc(levelLabel(a.level || a.regime || ''))}</span></td>
          <td>${esc(a.regime || '')}</td>
          <td>${esc(a.tendency || a.direction || '')}</td>
          <td>${esc(a.win_read || a.winPlan || '')}</td>
          <td>${esc(a.title || '')}</td>
          <td>${esc(a.source || '')}</td>
        </tr>
      `).join('') || '<tr><td colspan="8" class="muted">Sem registros</td></tr>';
    }

    async function loadSources(runCheck = false) {
      const res = await fetch(runCheck ? '/api/source-health?refresh=1' : '/api/source-health');
      const data = await res.json();
      const sources = data.sources || [];
      const okSources = sources.filter(s => String(s.status || '').toLowerCase() === 'ok');
      const staleSources = sources
        .filter(s => String(s.status || '').toLowerCase() !== 'ok')
        .sort((a, b) => Number(b.latency_ms || 0) - Number(a.latency_ms || 0));
      const worstLatency = sources.reduce((max, s) => Math.max(max, Number(s.latency_ms || 0)), 0);
      $('sources').innerHTML = sources.map(s => `
        <tr>
          <td>${esc(s.source_id)}</td>
          <td>${esc(s.source_type || '')}</td>
          <td class="${esc(s.status || '')}">${esc(s.status || '')}</td>
          <td>${s.status_code || ''}</td>
          <td>${s.latency_ms ?? ''}ms</td>
          <td>${esc(s.detail || '')}</td>
        </tr>
      `).join('') || '<tr><td colspan="6" class="muted">Sem fontes</td></tr>';

      const healthTitle = currentView === 'health' ? 'Saude das fontes' : 'Health';
      const healthSub = currentView === 'health' ? 'Falhas primeiro, stale data depois, latencia em terceiro.' : 'Falhas e latencia das fontes.';
      const healthCard = document.querySelector('[data-health-card]');
      if (healthCard) {
        healthCard.querySelector('h3').textContent = healthTitle;
        healthCard.querySelector('.sub').textContent = healthSub;
      }
      $('sourcesMini').innerHTML = `
        <div class="alert-panel" style="padding:14px;">
          <h4>Resumo</h4>
          <div class="stat-row">
            <div class="mini-row"><strong>OK</strong><span class="ok">${okSources.length}</span></div>
            <div class="mini-row"><strong>Stale / falha</strong><span class="${staleSources.length ? 'bad' : 'ok'}">${staleSources.length}</span></div>
            <div class="mini-row"><strong>Pior latencia</strong><span class="mono">${worstLatency}ms</span></div>
          </div>
        </div>
        ${staleSources.slice(0, 4).map(s => `
          <div class="alert-panel" style="padding:14px; border-color: rgba(255,91,97,0.18);">
            <h4>${esc(s.source_id)}</h4>
            <div class="stat-row">
              <div class="mini-row"><strong>Status</strong><span class="${esc(s.status || '')}">${esc(s.status || '')}</span></div>
              <div class="mini-row"><strong>Latencia</strong><span class="mono">${s.latency_ms ?? '-'}ms</span></div>
              <div class="mini-row"><strong>Detalhe</strong><span>${esc(s.detail || '')}</span></div>
            </div>
          </div>
        `).join('') || '<div class="alert-panel" style="padding:14px;"><h4>Sem falhas</h4><div class="meta">Todas as fontes principais responderam.</div></div>'}
      `;

      $('railSources').textContent = String(sources.length);
      $('railStale').textContent = String(staleSources.length);
      $('railCheck').textContent = new Date().toLocaleTimeString();
      if (currentView === 'health') {
        $('checkSources').textContent = 'Refresh health';
        const healthCard = document.querySelector('[data-health-card]');
        if (healthCard) {
          const badge = healthCard.querySelector('.card-head .badge');
          if (badge) badge.textContent = `OK ${okSources.length} · Falhas ${staleSources.length}`;
        }
      }
    }

    $('refresh').onclick = () => { loadAlerts(); loadSources(); };
    $('checkSources').onclick = () => loadSources(true);
    $('q').addEventListener('input', loadAlerts);
    $('type').addEventListener('change', loadAlerts);
    $('level').addEventListener('change', loadAlerts);
    $('regime').addEventListener('change', loadAlerts);

    applyView();
    loadAlerts();
    loadSources();
  </script>
</body>
</html>""".encode("utf-8")



class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        try:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/healthz":
                self._send(200, {"ok": True})
                return
            if parsed.path in ("/", "/dashboard") or parsed.path.startswith("/dashboard/"):
                body = dashboard_html()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path == "/api/alerts":
                self._send(200, list_alerts(urllib.parse.parse_qs(parsed.query)))
                return
            if parsed.path == "/api/source-health":
                query = urllib.parse.parse_qs(parsed.query)
                self._send(200, run_source_checks() if query.get("refresh") else list_source_checks())
                return
            if parsed.path != "/check":
                self._send(404, {"error": "not_found"})
                return
            query = urllib.parse.parse_qs(parsed.query)
            dedupe_key = query.get("key", [""])[0]
            ttl_seconds = int(query.get("ttl", ["86400"])[0])
            if not dedupe_key:
                self._send(400, {"error": "missing_key"})
                return
            self._send(200, check_key(dedupe_key, ttl_seconds))
        except Exception as exc:
            self._send(500, {"error": "check_failed", "detail": str(exc)})

    def do_POST(self) -> None:
        try:
            if self.path == "/api/alerts":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                self._send(200, record_alert(payload))
                return
            if self.path != "/store":
                self._send(404, {"error": "not_found"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not payload.get("dedupe_key"):
                self._send(400, {"error": "missing_dedupe_key"})
                return
            self._send(200, store_key(payload))
        except Exception as exc:
            self._send(500, {"error": "store_failed", "detail": str(exc)})

    def log_message(self, format: str, *args) -> None:
        return


if __name__ == "__main__":
    ensure_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()
