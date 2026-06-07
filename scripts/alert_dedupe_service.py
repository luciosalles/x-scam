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
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Alert Dashboard</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #101113;
      --panel: #17191d;
      --line: #30333a;
      --text: #f1f3f5;
      --muted: #9aa3ad;
      --ok: #3ddc84;
      --warn: #f5b84b;
      --bad: #ff5c5c;
      --accent: #4da3ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.45 ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
    }}
    header {{
      padding: 20px 24px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
    }}
    h1 {{ margin: 0; font-size: 20px; }}
    main {{ padding: 20px 24px; display: grid; gap: 18px; }}
    .filters, .grid, .sources {{ display: grid; gap: 12px; }}
    .filters {{ grid-template-columns: repeat(4, minmax(120px, 1fr)); }}
    input, select, button {{
      background: #0d0f12;
      border: 1px solid var(--line);
      color: var(--text);
      padding: 10px 12px;
      border-radius: 6px;
    }}
    button {{ cursor: pointer; background: #172033; border-color: #2d4671; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); }}
    th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    .pill {{ display: inline-block; padding: 3px 8px; border-radius: 999px; font-size: 12px; border: 1px solid var(--line); }}
    .RED, .RISK_OFF, .error, .bad_content {{ color: var(--bad); }}
    .ORANGE, .YELLOW, .warn {{ color: var(--warn); }}
    .ok, .RISK_ON {{ color: var(--ok); }}
    .muted {{ color: var(--muted); }}
    a {{ color: var(--accent); }}
    @media (max-width: 900px) {{ .filters {{ grid-template-columns: 1fr; }} table {{ font-size: 12px; }} }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Alert Dashboard</h1>
      <div class="muted">Historico, filtros e saude das fontes</div>
    </div>
    <button id="refresh">Refresh</button>
  </header>
  <main>
    <section class="filters">
      <select id="type">
        <option value="">Todos os tipos</option>
        <option value="news">News</option>
        <option value="market">Market</option>
        <option value="brazil_local">Brasil Local</option>
      </select>
      <select id="level">
        <option value="">Todos os niveis</option>
        <option>YELLOW</option>
        <option>ORANGE</option>
        <option>RED</option>
        <option>RISK_ON</option>
        <option>RISK_OFF</option>
      </select>
      <input id="q" placeholder="Buscar titulo, fonte, motivo">
      <button id="checkSources">Checar fontes</button>
    </section>
    <section>
      <h2>Alertas</h2>
      <table>
        <thead>
          <tr><th>Hora</th><th>Tipo</th><th>Nivel</th><th>Tendência real</th><th>Leitura WIN</th><th>Titulo / Regime</th><th>Fonte</th><th>Motivo</th></tr>
        </thead>
        <tbody id="alerts"></tbody>
      </table>
    </section>
    <section>
      <h2>Fontes</h2>
      <table>
        <thead>
          <tr><th>Fonte</th><th>Tipo</th><th>Status</th><th>HTTP</th><th>Latencia</th><th>Detalhe</th></tr>
        </thead>
        <tbody id="sources"></tbody>
      </table>
    </section>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);
    const fmt = (ts) => ts ? new Date(ts * 1000).toLocaleString() : '-';
    const levelLabel = (value) => ({{
      RED: 'Vermelho',
      ORANGE: 'Laranja',
      YELLOW: 'Amarelo',
      RISK_ON: 'Viés de alta',
      RISK_OFF: 'Viés de baixa'
    }})[value] || value || '';
    async function loadAlerts() {{
      const params = new URLSearchParams();
      if ($('type').value) params.set('type', $('type').value);
      if ($('level').value) params.set('level', $('level').value);
      if ($('q').value) params.set('q', $('q').value);
      const res = await fetch('/api/alerts?' + params.toString());
      const data = await res.json();
      $('alerts').innerHTML = data.alerts.map(a => `
        <tr>
          <td>${{fmt(a.created_at)}}</td>
          <td>${{a.alert_type || ''}}</td>
          <td><span class="pill ${{a.level || a.regime || ''}}">${{levelLabel(a.level || a.regime || '')}}</span></td>
          <td>${{escapeHtml(a.tendency || a.regime || '')}}${{a.conviction ? `<br><span class="muted">Convicção: ${{escapeHtml(a.conviction)}}</span>` : ''}}</td>
          <td>${{escapeHtml(a.win_read || a.winPlan || '')}}</td>
          <td>${{escapeHtml(a.title || a.regime || '')}}${{a.link ? `<br><a href="${{a.link}}" target="_blank">link</a>` : ''}}</td>
          <td>${{escapeHtml(a.source || '')}}</td>
          <td>${{escapeHtml(a.reason || '')}}</td>
        </tr>
      `).join('');
    }}
    async function loadSources(runCheck = false) {{
      const res = await fetch(runCheck ? '/api/source-health?refresh=1' : '/api/source-health');
      const data = await res.json();
      $('sources').innerHTML = data.sources.map(s => `
        <tr>
          <td>${{escapeHtml(s.source_id)}}</td>
          <td>${{escapeHtml(s.source_type || '')}}</td>
          <td class="${{s.status}}">${{escapeHtml(s.status || '')}}</td>
          <td>${{s.status_code || ''}}</td>
          <td>${{s.latency_ms ?? ''}}ms</td>
          <td>${{escapeHtml(s.detail || '')}}</td>
        </tr>
      `).join('');
    }}
    function escapeHtml(value) {{
      return String(value ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}}[ch]));
    }}
    $('refresh').onclick = () => {{ loadAlerts(); loadSources(); }};
    $('checkSources').onclick = () => loadSources(true);
    ['type', 'level', 'q'].forEach(id => $(id).addEventListener('input', loadAlerts));
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
            if parsed.path in ("/", "/dashboard"):
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
