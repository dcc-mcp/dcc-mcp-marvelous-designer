import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from dcc_mcp_marvelous_designer.api import GarmentAPI


@pytest.fixture
def host(tmp_path):
    state = {"count": 0, "calls": []}

    def create(points):
        state["calls"].append(points)
        state["count"] += 1
        return state["count"] - 1

    def export(path, option):
        state["calls"].append(option)
        Path(path).write_bytes(b"test artifact")
        return [path]

    def save(path, thumbnail):
        Path(path).write_bytes(b"test project")
        return path

    modules = {
        "pattern_api": SimpleNamespace(
            GetPatternCount=lambda: state["count"],
            GetPatternInformation=lambda i: '{"index":%d}' % i,
            CreatePatternWithPoints=create,
        ),
        "utility_api": SimpleNamespace(Simulate=lambda steps: True),
        "import_api": SimpleNamespace(ImportZprj=lambda path, option: True),
        "export_api": SimpleNamespace(
            ExportOBJ=export, ExportFBX=export, ExportAlembic=export, ExportZPrj=save
        ),
        "ApiTypes": SimpleNamespace(
            ImportZPRJOption=lambda: SimpleNamespace(
                bAppend=True, bLoadGarment=False, bLoadAvatar=False
            ),
            ImportExportOption=lambda: SimpleNamespace(
                bExportGarment=False,
                bExportAvatar=True,
                bSingleObject=False,
                bSaveInZip=True,
                bExportAnimation=False,
                scale=0,
            ),
        ),
    }
    return GarmentAPI([tmp_path], modules), state


def test_create_readback_and_pagination(host):
    api, state = host
    assert api.create_rectangle(600, 900)["pattern_index"] == 0
    assert state["calls"][0][2] == (600.0, 900.0, 0)
    assert len(api.list_patterns()["patterns"]) == 1
    assert api.list_patterns(offset=1)["patterns"] == []


@pytest.mark.parametrize("value", [False, float("nan"), float("inf"), 0, -1, 10001, "600"])
def test_bad_dimensions_before_mutation(host, value):
    api, state = host
    with pytest.raises(ValueError):
        api.create_rectangle(value, 900)
    assert state["calls"] == []


@pytest.mark.parametrize("value", [False, 0, -1, 31, 1.5, "2"])
def test_simulation_bounded(host, value):
    with pytest.raises(ValueError):
        host[0].simulate_steps(value)


def test_simulation_native_failure(host):
    api, _ = host
    api.modules["utility_api"].Simulate = lambda steps: False
    with pytest.raises(RuntimeError, match="simulation failed"):
        api.simulate_steps(2)


def test_wrong_thread_refused(host):
    errors = []

    def worker():
        try:
            host[0].get_status()
        except RuntimeError as error:
            errors.append(str(error))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert errors and "bootstrap thread" in errors[0]


@pytest.mark.parametrize("format", ["obj", "fbx", "abc"])
def test_export_checks_and_explicit_options(host, tmp_path, format):
    api, state = host
    result = api.export_garment(str(tmp_path), format, 0.001)
    assert result["artifacts"][0]["bytes"] > 0
    assert len(result["artifacts"][0]["sha256"]) == 64
    assert state["calls"][0].bExportAvatar is False
    assert state["calls"][0].bExportAnimation == (format == "abc")
    assert result["engine_import_verified"] is False
    with pytest.raises(ValueError, match="empty"):
        api.export_garment(str(tmp_path), format)


def test_export_rejects_native_wrong_location(host, tmp_path):
    api, _ = host
    other = tmp_path / "other.obj"
    other.write_bytes(b"old")
    out = tmp_path / "out"
    out.mkdir()
    api.modules["export_api"].ExportOBJ = lambda *args: [str(other)]
    with pytest.raises(RuntimeError, match="paths differ"):
        api.export_garment(str(out))


def test_path_escape_and_relative_refused(host, tmp_path):
    for value in ["relative.zprj", str(tmp_path.parent / "escape.zprj")]:
        with pytest.raises(ValueError):
            host[0].save_project(value)


def test_save_verify_no_overwrite(host, tmp_path):
    target = tmp_path / "safe.zprj"
    assert host[0].save_project(str(target))["bytes"] > 0
    with pytest.raises(ValueError):
        host[0].save_project(str(target))


def test_missing_option_fails_closed(host, tmp_path):
    api, _ = host
    api.modules["ApiTypes"].ImportExportOption = lambda: SimpleNamespace()
    with pytest.raises(RuntimeError, match="Unsupported host option"):
        api.export_garment(str(tmp_path))
    assert not list(tmp_path.iterdir())


def test_missing_api_report_and_refusal(host):
    api, _ = host
    api.modules["utility_api"] = SimpleNamespace()
    assert api.get_status()["available_api"]["utility_api"] == []
    with pytest.raises(RuntimeError, match="Unsupported host API"):
        api.simulate_steps()


def test_creation_count_failure_not_success(host):
    api, _ = host
    api.modules["pattern_api"].CreatePatternWithPoints = lambda points: 0
    with pytest.raises(RuntimeError, match="readback failed"):
        api.create_rectangle(10, 10)


def test_import_no_generic_dialog(host, tmp_path):
    api, _ = host
    target = tmp_path / "source.zprj"
    target.write_bytes(b"test")
    seen = []

    def importer(path, option):
        seen.append(option)
        return True

    api.modules["import_api"].ImportZprj = importer
    api.import_project(str(target))
    assert seen[0].bAppend is False
    assert seen[0].bLoadGarment is True


def test_no_inline_gui_bootstrap():
    from dcc_mcp_marvelous_designer.server import MarvelousDesignerServer

    with pytest.raises(ValueError, match="dispatcher"):
        MarvelousDesignerServer(dispatcher=None)


def test_skills_validate():
    from dcc_mcp_core import validate_skill

    root = Path(__file__).parents[1] / "src/dcc_mcp_marvelous_designer/skills"
    for folder in root.iterdir():
        report = validate_skill(str(folder))
        assert not report.has_errors, report.issues


def test_core_skill_discovery_load_and_unload(monkeypatch):
    from dcc_mcp_core.host import BlockingDispatcher
    from dcc_mcp_marvelous_designer.server import MarvelousDesignerServer

    monkeypatch.setenv("DCC_MCP_DISABLE_DEFAULT_SKILL_PATHS", "1")
    server = MarvelousDesignerServer(dispatcher=BlockingDispatcher())
    try:
        server.register_builtin_actions()
        names = {item["name"] for item in server.list_skills()}
        assert {"marvelous-project", "marvelous-garment"} <= names
        assert server.load_skill("marvelous-project")
        assert server.load_skill("marvelous-garment")
        tools = {item["name"] for item in server.list_actions()}
        assert len([name for name in tools if name.startswith("marvelous_")]) == 8
        assert server.unload_skill("marvelous-garment")
        assert not server.is_skill_loaded("marvelous-garment")
    finally:
        server.stop()


def test_skill_script_real_entrypoint(host, monkeypatch):
    import runpy
    from dcc_mcp_marvelous_designer import server

    monkeypatch.setattr(server, "_api", host[0])
    script = (
        Path(__file__).parents[1]
        / "src/dcc_mcp_marvelous_designer/skills/marvelous-garment/scripts/create_rectangle.py"
    )
    result = runpy.run_path(
        str(script), init_globals={"__mcp_params__": {"width_mm": 500, "height_mm": 800}}
    )
    assert result["__mcp_result__"]["context"]["pattern_count"] == 1
