from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pythoncom
import win32com.client
from win32com.server.util import wrap

try:
    import comtypes
    from ctypes import POINTER, c_long
    from comtypes import COMMETHOD, GUID, HRESULT
    from comtypes.automation import IDispatch
except Exception:  # pragma: no cover
    comtypes = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "profit_rtd_config.json"
RTD_ROOT = PROJECT_ROOT / "data" / "rtd"
SMOKE_PATH = RTD_ROOT / "smoke_test.json"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ensure_dirs() -> None:
    RTD_ROOT.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def safe_write(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    return repr(value)


@dataclass
class StepResult:
    step: str
    ok: bool
    detail: str = ""
    value: Any = None
    elapsed_ms: int = 0


class PyWin32Callback:
    _public_methods_ = ["UpdateNotify", "Disconnect"]
    _public_attrs_ = ["HeartbeatInterval"]

    def __init__(self) -> None:
        self.HeartbeatInterval = 2
        self.notify_count = 0

    def UpdateNotify(self) -> None:
        self.notify_count += 1

    def Disconnect(self) -> None:
        return None


def make_comtypes_callback():
    if comtypes is None:
        raise RuntimeError("comtypes not installed")

    # IRTDUpdateEvent is a dual interface in the Excel RTD contract.
    # comtypes must expose it as IDispatch, otherwise some servers reject the callback
    # even when Dispatch() succeeds.
    class IRTDUpdateEvent(IDispatch):
        _iid_ = GUID("{A43788C1-D91B-11D3-8F39-00C04F3651B8}")
        _methods_ = [
            COMMETHOD([], HRESULT, "UpdateNotify"),
            COMMETHOD([], HRESULT, "Disconnect"),
            COMMETHOD(["propget"], HRESULT, "HeartbeatInterval", (["out", "retval"], POINTER(c_long), "value")),
            COMMETHOD(["propput"], HRESULT, "HeartbeatInterval", (["in"], c_long, "value")),
        ]

    class Callback(comtypes.COMObject):
        _com_interfaces_ = [IRTDUpdateEvent]

        def __init__(self) -> None:
            super().__init__()
            self.interval = 2
            self.notify_count = 0

        def UpdateNotify(self):
            self.notify_count += 1
            return 0

        def Disconnect(self):
            return 0

        def _get_HeartbeatInterval(self):
            return self.interval

        def _set_HeartbeatInterval(self, value):
            self.interval = value
            return 0

    return Callback()


def timed_step(name: str, fn):
    started = time.time()
    try:
        value = fn()
        step = StepResult(name, True, value=json_safe(value), elapsed_ms=int((time.time() - started) * 1000))
        setattr(step, "_raw_value", value)
        return step
    except Exception as exc:  # pragma: no cover
        return StepResult(name, False, detail=str(exc), elapsed_ms=int((time.time() - started) * 1000))


def run_smoke(symbol: str = "WINQ26_F_0", field: str = "ULT", wait_seconds: int = 3) -> dict[str, Any]:
    ensure_dirs()
    cfg = load_config()
    results: list[StepResult] = []
    pythoncom.CoInitialize()
    server = None
    callback_mode = "none"
    callback = None

    def dispatch_server():
        return win32com.client.Dispatch(cfg.get("prog_id", "RTDTrading.RTDServer"))

    dispatch_result = timed_step("dispatch", dispatch_server)
    results.append(dispatch_result)
    if dispatch_result.ok:
        server = getattr(dispatch_result, "_raw_value", None)
    else:
        payload = {
            "updated_at_iso": now_iso(),
            "symbol": symbol,
            "field": field,
            "status": "dispatch_error",
            "steps": [asdict(step) for step in results],
        }
        safe_write(SMOKE_PATH, payload)
        return payload

    results.append(
        timed_step(
            "heartbeat",
            lambda: server.Heartbeat(),
        )
    )

    def serverstart_pywin32():
        nonlocal callback_mode, callback
        callback = wrap(PyWin32Callback())
        callback_mode = "pywin32_wrap"
        return server.ServerStart(callback)

    serverstart_result = timed_step("serverstart_pywin32", serverstart_pywin32)
    results.append(serverstart_result)

    if not serverstart_result.ok:
        def serverstart_comtypes():
            nonlocal callback_mode, callback
            callback = make_comtypes_callback()
            callback_mode = "comtypes"
            return server.ServerStart(callback)

        results.append(timed_step("serverstart_comtypes", serverstart_comtypes))

    connect_step = None
    if any(step.step.startswith("serverstart") and step.ok for step in results):
        def connect_data():
            return server.ConnectData(1, (symbol, field), True)

        connect_step = timed_step("connectdata", connect_data)
        results.append(connect_step)

        time.sleep(wait_seconds)

        def refresh_data():
            topic_count = 0
            return server.RefreshData(topic_count)

        results.append(timed_step("refreshdata", refresh_data))

    notify_count = None
    if callback is not None:
        notify_count = getattr(callback, "notify_count", None)

    status = "ok" if connect_step and connect_step.ok else "partial"
    if connect_step and not connect_step.ok:
        status = "connectdata_error"
    elif not any(step.step.startswith("serverstart") and step.ok for step in results):
        status = "serverstart_error"

    payload = {
        "updated_at_iso": now_iso(),
        "symbol": symbol,
        "field": field,
        "status": status,
        "callback_mode": callback_mode,
        "update_notify_count": notify_count,
        "steps": [asdict(step) for step in results],
    }
    safe_write(SMOKE_PATH, payload)
    return payload


if __name__ == "__main__":
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False, indent=2))
