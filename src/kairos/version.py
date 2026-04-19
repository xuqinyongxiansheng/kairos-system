"""
版本号单一事实来源（SSOT）
所有模块从此文件读取版本号，禁止各自硬编码
"""

import os

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

def _read_version_from_pyproject() -> str:
    _pyproject_paths = [
        os.path.join(os.path.dirname(__file__), "pyproject.toml"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "pyproject.toml"),
    ]
    for path in _pyproject_paths:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    data = tomllib.load(f)
                return data.get("project", {}).get("version", "4.0.0")
            except Exception:
                pass
    return "4.0.0"

__version__ = os.environ.get("GEMMA4_VERSION", _read_version_from_pyproject())
VERSION = __version__
SYSTEM_NAME = "Kairos System"
SYSTEM_CODENAME = "KAIROS-001"
