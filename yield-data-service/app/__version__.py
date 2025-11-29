"""
Версія EarnAggregator Data Service.

Версія читається з кореневого файлу VERSION для централізованого управління.
"""

from pathlib import Path

# Шлях до кореневого VERSION файлу
# Спробуємо кілька можливих шляхів для підтримки різних середовищ
_ROOT_DIR = Path(__file__).parent.parent.parent
_VERSION_FILE = _ROOT_DIR / "VERSION"

# Якщо файл не знайдено, спробуємо шлях відносно /app (для Docker)
if not _VERSION_FILE.exists():
    _VERSION_FILE = Path("/app/VERSION")


def get_version() -> str:
    """
    Отримати версію проекту з файлу VERSION.
    
    Returns:
        str: Версія проекту (наприклад, "1.0.0")
    """
    try:
        if _VERSION_FILE.exists():
            version = _VERSION_FILE.read_text().strip()
            return version
        else:
            # Fallback якщо файл не знайдено
            return "1.0.0"
    except Exception:
        # Fallback при помилці читання
        return "1.0.0"


# Версія для імпорту
__version__ = get_version()
<<<<<<< HEAD

=======
>>>>>>> 838651ea112ede6673d9ce4f82e973a4b448a2f6
