"""防止純計算核心因新增模組而偷偷依賴網頁框架。"""
import ast
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_mechanics_imports_without_django_setup():
    # 新行程排除 pytest 已載入的 plugin；攔截任何直接或間接 Django import。
    code = '''
import sys, importlib.abc, importlib, pkgutil
class BlockDjango(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "django" or fullname.startswith("django."):
            raise AssertionError("mechanics must not import Django")
sys.meta_path.insert(0, BlockDjango())
import mechanics
for module in pkgutil.walk_packages(mechanics.__path__, "mechanics."):
    importlib.import_module(module.name)
assert "django" not in sys.modules
'''
    env = {k: v for k, v in os.environ.items() if k != 'DJANGO_SETTINGS_MODULE'}
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env,
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_mechanics_source_has_no_django_imports():
    paths = list((ROOT / 'mechanics').rglob('*.py'))
    assert paths, 'mechanics package is missing'
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or '']
            assert not any(n == 'django' or n.startswith('django.') for n in names), path
