from pathlib import Path


_ROOT_DIR = Path(__file__).parent.parent.parent
_VERSION_FILE = _ROOT_DIR / "VERSION"


if not _VERSION_FILE.exists():
    _VERSION_FILE = Path("/app/VERSION")


def get_version() -> str:
    try:
        if _VERSION_FILE.exists():
            version = _VERSION_FILE.read_text().strip()
            return version
        else:
            return "1.0.0"
    except Exception:
        return "1.0.0"


__version__ = get_version()
