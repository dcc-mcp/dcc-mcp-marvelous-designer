"""Core-owned registration and execution; the host supplies a verified dispatcher."""

from pathlib import Path

from dcc_mcp_core import DccServerOptions, HostExecutionBridge, MinimalModeConfig
from dcc_mcp_core.server_base import DccServerBase

from . import __version__
from .api import GarmentAPI

_api = None
_server = None


def current_api():
    if _api is None:
        raise RuntimeError("Start the adapter inside Marvelous Designer first")
    return _api


class MarvelousDesignerServer(DccServerBase):
    def __init__(self, *, dispatcher, dcc_version="unknown", **kwargs):
        if dispatcher is None:
            raise ValueError("A verified host-thread dispatcher is required")
        options = DccServerOptions.from_env(
            "marvelous_designer",
            Path(__file__).parent / "skills",
            server_name="dcc-mcp-marvelous-designer",
            server_version=__version__,
            adapter_version=__version__,
            dcc_version=dcc_version,
            instance_type="gui",
            execution_bridge=HostExecutionBridge(dispatcher=dispatcher),
            **kwargs,
        )
        super().__init__(options=options)
        self.host_version = dcc_version

    def _version_string(self):
        return self.host_version


def start_server(roots, dispatcher, dcc_version="unknown", **kwargs):
    """Invoke on the host thread; importing the package alone has no effects."""
    global _api, _server
    if _server is not None:
        raise RuntimeError("Adapter already running; stop it before rebinding")
    api = GarmentAPI(roots)
    server = MarvelousDesignerServer(dispatcher=dispatcher, dcc_version=dcc_version, **kwargs)
    _api = api
    try:
        server.register_builtin_actions(
            minimal_mode=MinimalModeConfig(
                skills=("marvelous-project",),
                env_var_minimal="DCC_MCP_MARVELOUS_DESIGNER_MINIMAL",
                env_var_default_tools="DCC_MCP_MARVELOUS_DESIGNER_DEFAULT_TOOLS",
            )
        )
        server.start()
    except BaseException:
        _api = None
        server.stop()
        raise
    _server = server
    return server


def stop_server():
    global _server, _api
    if _server is not None:
        _server.stop()
    _server = None
    _api = None
