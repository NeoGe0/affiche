import ast
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent / "affiche"

LOWER_LAYERS = ("app", "external", "config")

def _python_files(package: str):
    return sorted((BACKEND_ROOT / package).rglob("*.py"))

def _imported_modules(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module, node.lineno

@pytest.mark.parametrize("package", LOWER_LAYERS)
def test_lower_layers_do_not_import_the_api_layer(package):
    offenders = [
        f"{path.relative_to(BACKEND_ROOT.parent)}:{line} imports {module}"
        for path in _python_files(package)
        for module, line in _imported_modules(path)
        if module == "affiche.api" or module.startswith("affiche.api.")
    ]

    assert offenders == [], (
        "the app layer must not depend on the API layer:\n  " + "\n  ".join(offenders))

def test_the_scan_would_actually_catch_an_upward_import(tmp_path):
    offender = tmp_path / "bad.py"
    offender.write_text("from affiche.api.schemas.media_server import MediaServerLibrary\n")

    found = [m for m, _ in _imported_modules(offender) if m.startswith("affiche.api")]

    assert found == ["affiche.api.schemas.media_server"]

@pytest.mark.parametrize("module", [
    "affiche.app.asynch.auto_pickup",
    "affiche.app.asynch.library_tasks",
    "affiche.app.asynch.auto_sync_scheduler",
    "affiche.app.mediaserver.service.media_server_service",
])
def test_app_modules_import_in_a_fresh_interpreter(module, tmp_path):
    import os
    import subprocess
    import sys

    script = (
        f"import importlib, sys;"
        f"importlib.import_module({module!r});"
        f"api = [m for m in sys.modules if m.startswith('affiche.api')];"
        f"print(len(api));"
        f"sys.exit(0 if not api else 1)"
    )
    env = {**os.environ, "CONFIG_DIR": str(tmp_path)}

    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                            cwd=str(BACKEND_ROOT.parent), env=env)

    assert result.returncode == 0, (
        f"importing {module} on its own failed or pulled in the API layer:\n"
        f"{result.stdout}\n{result.stderr[-1500:]}")
