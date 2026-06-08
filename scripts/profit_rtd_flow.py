from __future__ import annotations

import argparse
import json
import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import win32com.client

try:
    import pythoncom
except Exception:  # pragma: no cover
    pythoncom = None

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "profit_rtd_config.json"
RTD_ROOT = PROJECT_ROOT / "data" / "rtd"
STATE_PATH = RTD_ROOT / "state.json"
SNAPSHOT_PATH = RTD_ROOT / "snapshot.json"
DISCOVERY_PATH = RTD_ROOT / "discovery.json"
RECENT_PARQUET_PATH = RTD_ROOT / "latest_ticks.parquet"
PLOT_PATH = RTD_ROOT / "flow_overview.png"


@dataclass
class RTDConfig:
    prog_id: str
    candidate_prog_ids: list[str]
    poll_interval_ms: int
    flush_interval_seconds: int
    plot_interval_seconds: int
    rolling_tick_limit: int
    chunk_tick_limit: int
    topic_id_start: int
    symbols: list[str]
    fields: list[str]
    scanner_symbols: list[str]
    scanner_fields: list[str]


def load_config() -> RTDConfig:
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return RTDConfig(
        prog_id=str(raw.get("prog_id", "PROFIT.RTD")),
        candidate_prog_ids=[str(x) for x in raw.get("candidate_prog_ids", ["PROFIT.RTD"])],
        poll_interval_ms=int(raw.get("poll_interval_ms", 120)),
        flush_interval_seconds=int(raw.get("flush_interval_seconds", 5)),
        plot_interval_seconds=int(raw.get("plot_interval_seconds", 30)),
        rolling_tick_limit=int(raw.get("rolling_tick_limit", 10000)),
        chunk_tick_limit=int(raw.get("chunk_tick_limit", 1000)),
        topic_id_start=int(raw.get("topic_id_start", 1)),
        symbols=[str(x) for x in raw.get("symbols", [])],
        fields=[str(x) for x in raw.get("fields", [])],
        scanner_symbols=[str(x) for x in raw.get("scanner_symbols", [])],
        scanner_fields=[str(x) for x in raw.get("scanner_fields", [])],
    )


def ensure_dirs() -> None:
    RTD_ROOT.mkdir(parents=True, exist_ok=True)
    (RTD_ROOT / "chunks").mkdir(parents=True, exist_ok=True)


def now_ts() -> float:
    return time.time()


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_json_write(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def normalize_scalar(value: Any) -> Any:
    if value in (None, "", [], (), {}):
        return None
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return normalize_scalar(value[0])
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        text_up = text.upper()
        if text_up in {"NONE", "NULL", "NAN", "#N/A", "ERRO", "ERROR"}:
            return None
        try:
            return float(text.replace(",", ".")) if any(ch.isdigit() for ch in text) else text
        except Exception:
            return text
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


class ProfitRTDClient:
    def __init__(self, prog_id: str, candidate_prog_ids: list[str] | None = None) -> None:
        self.prog_id = prog_id
        self.candidate_prog_ids = candidate_prog_ids or [prog_id]
        self.dispatch = None

    def connect(self) -> None:
        if pythoncom is not None:
            pythoncom.CoInitialize()
        errors: list[str] = []
        for prog_id in self.candidate_prog_ids:
            try:
                self.dispatch = win32com.client.Dispatch(prog_id)
                self.prog_id = prog_id
                return
            except Exception as exc:
                errors.append(f"{prog_id}: {exc}")
        raise RuntimeError(" | ".join(errors) or f"Unable to connect to {self.prog_id}")

    def query(self, topic_id: int, symbol: str, field: str) -> Any:
        if self.dispatch is None:
            raise RuntimeError("RTD dispatch not connected")
        return normalize_scalar(self.dispatch.ConnectData(topic_id, (symbol, field), True))


class RTDCollector:
    def __init__(self, config: RTDConfig) -> None:
        self.config = config
        self.client = ProfitRTDClient(config.prog_id, config.candidate_prog_ids)
        self.cache: dict[tuple[str, str], Any] = {}
        self.symbol_stats: dict[str, dict[str, Any]] = {}
        self.recent_ticks: deque[dict[str, Any]] = deque(maxlen=config.rolling_tick_limit)
        self.chunk_ticks: list[dict[str, Any]] = []
        self.discovery: list[dict[str, Any]] = []
        self.topic_map: dict[tuple[str, str], int] = {}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.started_at = now_ts()
        self.last_error = ""
        self.last_flush = 0.0
        self.last_plot = 0.0
        self.total_updates = 0
        self.total_ticks = 0

    def topic_id_for(self, symbol: str, field: str) -> int:
        key = (symbol, field)
        if key not in self.topic_map:
            self.topic_map[key] = self.config.topic_id_start + len(self.topic_map)
        return self.topic_map[key]

    def write_state(self, connected: bool, status: str) -> None:
        with self.lock:
            payload = {
                "updated_at": now_ts(),
                "updated_at_iso": iso_now(),
                "status": status,
                "connected": connected,
                "prog_id": self.client.prog_id,
                "candidate_prog_ids": self.config.candidate_prog_ids,
                "started_at": self.started_at,
                "last_error": self.last_error,
                "symbols": self.config.symbols,
                "fields": self.config.fields,
                "topic_count": len(self.topic_map),
                "total_updates": self.total_updates,
                "total_ticks": self.total_ticks,
                "buffer_size": len(self.recent_ticks),
                "chunk_buffer_size": len(self.chunk_ticks),
                "recent_parquet": str(RECENT_PARQUET_PATH),
                "plot_path": str(PLOT_PATH),
                "symbol_stats": self.symbol_stats,
            }
        safe_json_write(STATE_PATH, payload)

    def write_snapshot(self) -> None:
        with self.lock:
            last_ticks = list(self.recent_ticks)[-120:]
            payload = {
                "updated_at": now_ts(),
                "updated_at_iso": iso_now(),
                "symbols": self.symbol_stats,
                "last_ticks": last_ticks,
                "buffer_size": len(self.recent_ticks),
                "total_ticks": self.total_ticks,
            }
        safe_json_write(SNAPSHOT_PATH, payload)

    def flush_parquet(self, force_chunk: bool = False) -> None:
        with self.lock:
            recent_rows = list(self.recent_ticks)
            chunk_rows = list(self.chunk_ticks)
            if force_chunk:
                self.chunk_ticks.clear()
        if recent_rows:
            pd.DataFrame(recent_rows).to_parquet(RECENT_PARQUET_PATH, index=False)
        if chunk_rows and (force_chunk or len(chunk_rows) >= self.config.chunk_tick_limit):
            day_dir = RTD_ROOT / "chunks" / datetime.now().strftime("%Y%m%d")
            day_dir.mkdir(parents=True, exist_ok=True)
            chunk_path = day_dir / f"ticks_{datetime.now().strftime('%H%M%S')}.parquet"
            pd.DataFrame(chunk_rows).to_parquet(chunk_path, index=False)
            with self.lock:
                self.chunk_ticks.clear()

    def plot_overview(self) -> None:
        if plt is None:
            return
        with self.lock:
            rows = list(self.recent_ticks)
        if not rows:
            return
        df = pd.DataFrame(rows)
        if df.empty or "symbol" not in df or "field" not in df:
            return
        price_df = df[df["field"].isin(["ULT", "LAST"])]
        volume_df = df[df["field"] == "VOLUME"]
        fig, axes = plt.subplots(2, 1, figsize=(12, 7), facecolor="#0f1012")
        for ax in axes:
            ax.set_facecolor("#16181c")
            ax.grid(color="#2e3138", alpha=0.35)
            ax.tick_params(colors="#c8cdd6")
            for spine in ax.spines.values():
                spine.set_color("#2e3138")
        if not price_df.empty:
            for symbol, grp in price_df.groupby("symbol"):
                axes[0].plot(grp["timestamp"], grp["value"], label=symbol)
            axes[0].legend(facecolor="#16181c", edgecolor="#2e3138", labelcolor="#c8cdd6")
            axes[0].set_title("RTD Price Flow", color="#f2f4f7")
        if not volume_df.empty:
            for symbol, grp in volume_df.groupby("symbol"):
                axes[1].plot(grp["timestamp"], grp["value"], label=symbol)
            axes[1].legend(facecolor="#16181c", edgecolor="#2e3138", labelcolor="#c8cdd6")
            axes[1].set_title("RTD Volume Flow", color="#f2f4f7")
        fig.tight_layout()
        fig.savefig(PLOT_PATH, dpi=120)
        plt.close(fig)

    def scan(self) -> dict[str, Any]:
        ensure_dirs()
        started = now_ts()
        valid_results: list[dict[str, Any]] = []
        query_errors: list[dict[str, Any]] = []
        try:
            self.client.connect()
            connected = True
            status = "connected"
            self.last_error = ""
        except Exception as exc:
            connected = False
            status = "dispatch_error"
            self.last_error = str(exc)
            payload = {
                "updated_at": now_ts(),
                "updated_at_iso": iso_now(),
                "status": status,
                "connected": False,
                "prog_id": self.config.prog_id,
                "candidate_prog_ids": self.config.candidate_prog_ids,
                "error": self.last_error,
                "valid_results": [],
            }
            safe_json_write(DISCOVERY_PATH, payload)
            self.write_state(False, status)
            return payload
        for sym in self.config.scanner_symbols:
            for field in self.config.scanner_fields:
                try:
                    data = self.client.query(self.topic_id_for(sym, field), sym, field)
                    if data is not None:
                        valid_results.append({"symbol": sym, "field": field, "value": data})
                    time.sleep(0.05)
                except Exception as exc:
                    query_errors.append({"symbol": sym, "field": field, "error": str(exc)})
                    self.last_error = str(exc)
                    continue
        if query_errors and not valid_results:
            status = "query_error"
        payload = {
            "updated_at": now_ts(),
            "updated_at_iso": iso_now(),
            "status": status,
            "connected": connected,
            "prog_id": self.client.prog_id,
            "elapsed_ms": int((now_ts() - started) * 1000),
            "valid_results": valid_results,
            "query_error_count": len(query_errors),
            "query_errors": query_errors[:12],
        }
        safe_json_write(DISCOVERY_PATH, payload)
        self.write_state(connected and status != "query_error", status)
        return payload

    def run(self) -> None:
        ensure_dirs()
        try:
            self.client.connect()
            self.write_state(True, "connected")
        except Exception as exc:
            self.last_error = str(exc)
            self.write_state(False, "dispatch_error")
            raise
        while not self.stop_event.is_set():
            loop_started = now_ts()
            for symbol in self.config.symbols:
                for field in self.config.fields:
                    topic_id = self.topic_id_for(symbol, field)
                    try:
                        value = self.client.query(topic_id, symbol, field)
                    except Exception as exc:
                        self.last_error = str(exc)
                        continue
                    if value is None:
                        continue
                    key = (symbol, field)
                    old = self.cache.get(key)
                    if old == value:
                        continue
                    self.cache[key] = value
                    tick = {
                        "symbol": symbol,
                        "field": field,
                        "value": value,
                        "timestamp": now_ts(),
                        "iso_time": iso_now(),
                        "topic_id": topic_id,
                    }
                    with self.lock:
                        self.recent_ticks.append(tick)
                        self.chunk_ticks.append(tick)
                        self.total_updates += 1
                        self.total_ticks += 1
                        stats = self.symbol_stats.setdefault(
                            symbol,
                            {
                                "symbol": symbol,
                                "last_price": None,
                                "last_bid": None,
                                "last_ask": None,
                                "last_volume": None,
                                "updates": 0,
                                "tick_frequency": 0.0,
                                "last_update": 0.0,
                                "direction_bias": "flat",
                            },
                        )
                        stats["updates"] += 1
                        stats["last_update"] = tick["timestamp"]
                        if field in {"ULT", "LAST"}:
                            previous_price = stats.get("last_price")
                            stats["last_price"] = value
                            if isinstance(previous_price, (int, float)) and isinstance(value, (int, float)):
                                if value > previous_price:
                                    stats["direction_bias"] = "up"
                                elif value < previous_price:
                                    stats["direction_bias"] = "down"
                                else:
                                    stats["direction_bias"] = "flat"
                        elif field == "BID":
                            stats["last_bid"] = value
                        elif field == "ASK":
                            stats["last_ask"] = value
                        elif field == "VOLUME":
                            stats["last_volume"] = value
                        elapsed = max(tick["timestamp"] - self.started_at, 1.0)
                        stats["tick_frequency"] = round(stats["updates"] / elapsed, 4)
            if now_ts() - self.last_flush >= self.config.flush_interval_seconds:
                self.flush_parquet(force_chunk=True)
                self.write_snapshot()
                self.write_state(True, "streaming")
                self.last_flush = now_ts()
            if now_ts() - self.last_plot >= self.config.plot_interval_seconds:
                self.plot_overview()
                self.last_plot = now_ts()
            remaining = max(0.0, (self.config.poll_interval_ms / 1000.0) - (now_ts() - loop_started))
            time.sleep(remaining)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "read_error", "error": str(exc), "path": str(path)}


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_scan(config: RTDConfig) -> int:
    collector = RTDCollector(config)
    print_json(collector.scan())
    return 0


def cmd_status() -> int:
    print_json(read_json(STATE_PATH))
    return 0


def cmd_run(config: RTDConfig) -> int:
    collector = RTDCollector(config)
    try:
        collector.run()
    except KeyboardInterrupt:
        collector.stop_event.set()
        collector.flush_parquet(force_chunk=True)
        collector.write_snapshot()
        collector.write_state(True, "stopped")
        return 0
    except Exception as exc:
        collector.last_error = str(exc)
        collector.write_state(False, "crashed")
        raise
    return 0


def cmd_plot() -> int:
    if not RECENT_PARQUET_PATH.exists():
        print_json({"status": "missing_parquet", "path": str(RECENT_PARQUET_PATH)})
        return 1
    df = pd.read_parquet(RECENT_PARQUET_PATH)
    if df.empty:
        print_json({"status": "empty_parquet", "path": str(RECENT_PARQUET_PATH)})
        return 1
    collector = RTDCollector(load_config())
    with collector.lock:
        collector.recent_ticks.extend(df.to_dict("records"))
    collector.plot_overview()
    print_json({"status": "plot_written", "plot_path": str(PLOT_PATH)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Profit RTD flow collector")
    parser.add_argument("command", choices=["scan", "run", "status", "plot"], help="Action to run")
    return parser


def main() -> int:
    ensure_dirs()
    args = build_parser().parse_args()
    config = load_config()
    if args.command == "scan":
        return cmd_scan(config)
    if args.command == "run":
        return cmd_run(config)
    if args.command == "status":
        return cmd_status()
    if args.command == "plot":
        return cmd_plot()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
