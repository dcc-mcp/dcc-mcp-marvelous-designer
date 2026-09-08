"""Optional Qt host pump, enabled only when a live host Qt binding is available."""

import importlib
import sys

from dcc_mcp_core import HostUiDispatcherBase

from .server import start_server, stop_server

_pump = None


class QtPump(HostUiDispatcherBase):
    def __init__(self, core, app):
        if core.QThread.currentThread() != app.thread():
            raise RuntimeError("Bootstrap must run on the Qt application thread")
        super().__init__(label="Marvelous Designer Qt")
        self.timer = core.QTimer(app)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._drain)
        self.timer.start()

    def _drain(self):
        self.drain_queue(budget_ms=8)

    def poke_host_pump(self):
        # The recurring native QTimer owns queue draining. No worker touches Qt.
        pass

    def close(self):
        self.timer.stop()
        self.timer.deleteLater()
        self.shutdown()


def start(roots, dcc_version="unknown", **kwargs):
    """Do not load a new Qt ABI into the host; reuse its existing Python binding."""
    global _pump
    if _pump is not None:
        raise RuntimeError("Qt pump already running")
    for binding in ("PySide6", "PySide2"):
        if binding not in sys.modules:
            continue
        core = importlib.import_module(binding + ".QtCore")
        app = core.QCoreApplication.instance()
        if app is not None:
            pump = QtPump(core, app)
            try:
                result = start_server(roots, pump, dcc_version, **kwargs)
            except BaseException:
                pump.close()
                raise
            _pump = pump
            return result
    raise RuntimeError("No loaded compatible Qt binding; a verified native dispatcher is required")


def stop():
    global _pump
    stop_server()
    if _pump is not None:
        _pump.close()
    _pump = None
