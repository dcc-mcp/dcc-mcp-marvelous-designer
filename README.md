# dcc-mcp-marvelous-designer

Typed garment operations for Marvelous Designer, using DCC-MCP Core discovery,
execution and lifecycle. Initial integration targets the documented 2025 Python
API; **no licensed host or engine acceptance has been completed**.

## Supported API contracts

- Read API availability and paginated pattern information.
- Import ZPRJ without the general import dialog; this replaces the current project.
- Create a rectangular pattern and verify the pattern count.
- Simulate 1–30 synchronous steps. The documented API has no verified interrupt
  operation. A timeout is not proof simulation stopped; do not retry blindly.
- Save to a new ZPRJ; export OBJ, FBX or offline Alembic into an empty directory.
- Hash and check the actual returned nonempty artifacts, restricted to configured roots.

No arbitrary Python, shell, HTTP proxy, login, activation or UI input is exposed.
API presence does not prove a license is available. No vendor files are bundled.

## Host bootstrap

Install the package and a compatible official Core wheel in the host Python
environment only after operator authorization. Register a Python plugin in the
Marvelous Designer Plugin Manager, or use its Python editor. On the host main
thread:

```python
from dcc_mcp_marvelous_designer.qt_bootstrap import start
server = start(roots=["C:/garment-project"], dcc_version="YOUR_ACTUAL_VERSION")
```

This optional bootstrap only reuses an **already loaded** PySide2/PySide6 binding
with a live Qt application. Its availability in Marvelous Designer is unverified.
It refuses unsupported hosts instead of loading another Qt ABI or calling host
APIs on workers. If absent, `server.start_server(roots, dispatcher, ...)` requires
a verified host-thread dispatcher. Do not use an inline dispatcher for GUI calls.
Stop with `qt_bootstrap.stop()` before unloading. Core owns registration and the
OS-assigned endpoint. Discover with `dcc-mcp-cli list`, then search/load the
`marvelous-project` and `marvelous-garment` skills for that exact instance.

## Validation

```shell
python -m pytest
python -m build
```

Tests use deterministic host doubles and prove adapter contracts, not cloth
physics, host integration, Unreal or Unity compatibility. See
[acceptance](docs/acceptance.md) for the required live chain and gaps.

## Sources

[Official API](https://developer.marvelousdesigner.com/list.html),
[option types](https://developer.marvelousdesigner.com/optiontype.html),
[simulation examples](https://developer.marvelousdesigner.com/scenario.html),
[plugin registration](https://developer.marvelousdesigner.com/register.html).

Independent integration; not affiliated with or endorsed by the software vendor.
