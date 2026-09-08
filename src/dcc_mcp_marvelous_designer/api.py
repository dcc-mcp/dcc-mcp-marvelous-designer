"""Bounded operations against the documented embedded Marvelous Designer API."""

import hashlib
import importlib
import math
import threading
from pathlib import Path


class GarmentAPI:
    """Host-thread owned API facade; no scripts, shell, network, or UI fallback."""

    def __init__(self, roots, modules=None):
        self.roots = tuple(Path(root).resolve(strict=True) for root in roots)
        if not self.roots or not all(root.is_dir() for root in self.roots):
            raise ValueError("At least one existing project directory is required")
        self.modules = (
            modules
            if modules is not None
            else {
                name: importlib.import_module(name)
                for name in ("import_api", "export_api", "utility_api", "pattern_api", "ApiTypes")
            }
        )
        self.owner_thread = threading.get_ident()

    def _host(self, module, method):
        if threading.get_ident() != self.owner_thread:
            raise RuntimeError("Host APIs must execute on the bootstrap thread")
        fn = getattr(self.modules[module], method, None)
        if not callable(fn):
            raise RuntimeError(f"Unsupported host API: {module}.{method}")
        return fn

    def _path(self, value, exists=True):
        path = Path(value)
        if not path.is_absolute():
            raise ValueError("An absolute path is required")
        path = path.resolve(strict=exists)
        if not any(path == root or root in path.parents for root in self.roots):
            raise ValueError("Path is outside configured project roots")
        return path

    def _option(self, name, values):
        obj = self._host("ApiTypes", name)()
        for key, value in values.items():
            if not hasattr(obj, key):
                raise RuntimeError(f"Unsupported host option: {name}.{key}")
            setattr(obj, key, value)
        return obj

    def get_status(self):
        return {
            "pattern_count": self._host("pattern_api", "GetPatternCount")(),
            "simulation": "synchronous_steps_only",
            "native_interrupt_supported": False,
            "license_verified": False,
            "available_api": {
                module: sorted(
                    name for name in names if callable(getattr(self.modules[module], name, None))
                )
                for module, names in {
                    "import_api": ["ImportZprj"],
                    "export_api": ["ExportZPrj", "ExportOBJ", "ExportFBX", "ExportAlembic"],
                    "pattern_api": [
                        "GetPatternCount",
                        "GetPatternInformation",
                        "CreatePatternWithPoints",
                    ],
                    "utility_api": ["Simulate"],
                }.items()
            },
        }

    def list_patterns(self, offset=0, limit=50):
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Invalid pagination")
        count = self._host("pattern_api", "GetPatternCount")()
        info = self._host("pattern_api", "GetPatternInformation")
        return {
            "total": count,
            "patterns": [
                {"index": i, "information": info(i)}
                for i in range(offset, min(count, offset + limit))
            ],
        }

    def import_project(self, path):
        source = self._path(path)
        if not source.is_file() or source.suffix.lower() != ".zprj":
            raise ValueError("Expected a ZPRJ file")
        options = self._option(
            "ImportZPRJOption",
            {
                "bAppend": False,
                "bLoadGarment": True,
                "bLoadAvatar": True,
            },
        )
        if self._host("import_api", "ImportZprj")(str(source), options) is not True:
            raise RuntimeError("Native project import failed")
        return self.get_status()

    def create_rectangle(self, width_mm, height_mm):
        for value in (width_mm, height_mm):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 1 <= value <= 10000
            ):
                raise ValueError("Rectangle dimensions must be finite, 1..10000 mm")
        before = self._host("pattern_api", "GetPatternCount")()
        index = self._host("pattern_api", "CreatePatternWithPoints")(
            [
                (0.0, 0.0, 0),
                (float(width_mm), 0.0, 0),
                (float(width_mm), float(height_mm), 0),
                (0.0, float(height_mm), 0),
            ]
        )
        after = self._host("pattern_api", "GetPatternCount")()
        if type(index) is not int or index < 0 or after != before + 1:
            raise RuntimeError("Pattern creation readback failed; inspect scene before retry")
        return {"pattern_index": index, "pattern_count": after, "unit": "mm"}

    def simulate_steps(self, steps=1):
        if type(steps) is not int or not 1 <= steps <= 30:
            raise ValueError("steps must be an integer in 1..30")
        if self._host("utility_api", "Simulate")(steps) is not True:
            raise RuntimeError("Native simulation failed; inspect scene before retry")
        return {"completed_steps": steps, "native_interrupt_supported": False}

    def inspect_artifact(self, path):
        source = self._path(path)
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError("Artifact must be a nonempty regular file")
        digest = hashlib.sha256()
        with source.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return {"path": str(source), "bytes": source.stat().st_size, "sha256": digest.hexdigest()}

    def save_project(self, path):
        target = self._path(path, exists=False)
        if target.suffix.lower() != ".zprj" or target.exists() or not target.parent.is_dir():
            raise ValueError("Choose a new ZPRJ path in an existing directory")
        result = self._host("export_api", "ExportZPrj")(str(target), False)
        if not result or Path(result).resolve() != target:
            raise RuntimeError("Native save did not return the requested path")
        return self.inspect_artifact(str(target))

    def export_garment(self, directory, format="obj", scale=1.0):
        methods = {"obj": "ExportOBJ", "fbx": "ExportFBX", "abc": "ExportAlembic"}
        if format not in methods:
            raise ValueError("Unsupported export format")
        if (
            isinstance(scale, bool)
            or not isinstance(scale, (int, float))
            or not math.isfinite(scale)
            or not 0 < scale <= 1000
        ):
            raise ValueError("scale must be finite in (0,1000]")
        target = self._path(directory)
        if not target.is_dir() or any(target.iterdir()):
            raise ValueError("Export requires an empty existing output directory")
        options = self._option(
            "ImportExportOption",
            {
                "bExportGarment": True,
                "bExportAvatar": False,
                "bSingleObject": True,
                "bSaveInZip": False,
                "bExportAnimation": format == "abc",
                "scale": float(scale),
            },
        )
        primary = target / ("garment." + format)
        paths = self._host("export_api", methods[format])(str(primary), options)
        if not isinstance(paths, (list, tuple)) or not paths or len(paths) > 256:
            raise RuntimeError("Export did not return a bounded artifact list")
        resolved = [self._path(path) for path in paths]
        if primary not in resolved or any(target not in path.parents for path in resolved):
            raise RuntimeError("Export paths differ from the requested output directory")
        return {
            "format": format,
            "scale": scale,
            "animation": "offline_cache" if format == "abc" else "static_mesh",
            "engine_import_verified": False,
            "artifacts": [self.inspect_artifact(str(path)) for path in resolved],
        }
