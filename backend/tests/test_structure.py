"""Keep the agreed boundaries enforceable when future features are added."""

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PACKAGES = ("api", "services", "integrations", "runtime", "core")
OLD_MODULES = {"portal", "app", "cli", "sync", "config", "db", "security", "errors", "constants"}


def modules():
    roots = list(BACKEND.glob("*.py"))
    for folder in PACKAGES:
        roots.extend((BACKEND / folder).rglob("*.py"))
    result = {}
    for path in roots:
        parts = path.relative_to(BACKEND).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        result[".".join(parts)] = path
    return result


def test_database_access_stays_in_services_and_database_adapters():
    for name, path in modules().items():
        if name.startswith("services.") or name in {"core.db", "integrations.cpamp"}:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"execute", "executemany", "executescript"}, str(path)


def test_import_directions_and_cycles():
    paths = modules()
    edges = {name: set() for name in paths}
    forbidden = {
        "core": {"api", "services", "integrations", "runtime", "server", "fastapi", "starlette"},
        "services": {"api", "runtime", "server", "fastapi", "starlette"},
        "integrations": {"api", "services", "runtime", "server", "fastapi", "starlette"},
        "api": {"runtime", "server"},
    }
    for name, path in paths.items():
        for node in ast.walk(ast.parse(path.read_text())):
            imports = []
            if isinstance(node, ast.Import):
                imports = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0, f"Use absolute imports from backend root: {path}"
                imports = [node.module or ""] + [
                    f"{node.module}.{item.name}" for item in node.names
                ]
            for target in imports:
                first = target.split(".")[0]
                assert first not in OLD_MODULES | {"backend"}, (name, target)
                assert first not in forbidden.get(name.split(".")[0], set()), (name, target)
                # Importing a submodule also runs its parent package initializers.
                parts = target.split(".")
                for index in range(1, len(parts) + 1):
                    dependency = ".".join(parts[:index])
                    if dependency in paths:
                        edges[name].add(dependency)

    visited = set()

    def visit(name, stack):
        assert name not in stack, " -> ".join([*stack, name])
        if name in visited:
            return
        for target in edges[name]:
            visit(target, [*stack, name])
        visited.add(name)

    for name in paths:
        visit(name, [])
