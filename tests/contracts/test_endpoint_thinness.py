import ast
from pathlib import Path


def test_project_json_views_do_not_import_mechanics_or_solver_internals():
    tree = ast.parse(Path('projects/views.py').read_text())
    modules = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    modules.extend(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)

    assert all(not module.startswith(('numpy', 'mechanics.', 'idealization.')) for module in modules)
