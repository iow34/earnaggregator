import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LocalizationManager:
    """
    Centralized localization manager for the Telegram bot.
    Loads JSON translation files and provides methods to retrieve localized texts.
    """

    DEFAULT_LANG = "ua"
    FALLBACK_LANG = "en"

    def __init__(self):
        self._texts: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._base_dir = os.path.dirname(__file__)
        self._texts_dir = os.path.join(self._base_dir, "texts")
        self._load_texts()

    def _load_texts(self):
        """Loads all JSON files from the texts directory."""
        if not os.path.exists(self._texts_dir):
            logger.error(f"Localization texts directory not found: {self._texts_dir}")
            return

        for filename in os.listdir(self._texts_dir):
            if filename.endswith(".json"):
                category = filename[:-5]  # remove .json extension
                file_path = os.path.join(self._texts_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self._texts[category] = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load localization file {filename}: {e}")

    def get_text(self, key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
        """
        Retrieve a localized text by key.

        Args:
            key: The key in format 'category.subkey' (e.g., 'ui.menu.main.welcome').
                 If the key is simple (e.g. 'menu.main.welcome'), it tries to find it across loaded categories
                 or expects the category to be implicit if possible (though explicit category is better).
                 The plan implies structure like ui.json containing "ua": {"menu.main.welcome": ...}.
                 So the key usage in code might be just "menu.main.welcome" and we need to find which file it is in,
                 OR the key implies the file.
                 Looking at the plan:
                 File: ui.json -> Key: menu.main.welcome
                 File: messages.json -> Key: loading.main_menu

                 The keys seem unique enough. I will search through all loaded categories for the key.
            lang: The target language code ('ua', 'ru', 'en').
            **kwargs: Arguments for string formatting.

        Returns:
            Localized string or the key itself if not found.
        """

        # Helper to find key in any category
        def find_key_in_dict(text_dict: Dict, k: str) -> Optional[str]:
            return text_dict.get(k)

        # Strategy: Iterate over all categories to find the key in the specified language
        # This assumes keys are unique across files or we don't care about collisions.
        # Given the plan, keys look namespaced (menu.*, loading.*, error.*).

        value = None

        # 1. Try target language
        for category_data in self._texts.values():
            if lang in category_data:
                value = find_key_in_dict(category_data[lang], key)
                if value is not None:
                    break

        # 2. Fallback to DEFAULT_LANG (ua)
        if value is None and lang != self.DEFAULT_LANG:
            for category_data in self._texts.values():
                if self.DEFAULT_LANG in category_data:
                    value = find_key_in_dict(category_data[self.DEFAULT_LANG], key)
                    if value is not None:
                        break

        # 3. Fallback to FALLBACK_LANG (en)
        if value is None and lang != self.FALLBACK_LANG and self.FALLBACK_LANG != self.DEFAULT_LANG:
            for category_data in self._texts.values():
                if self.FALLBACK_LANG in category_data:
                    value = find_key_in_dict(category_data[self.FALLBACK_LANG], key)
                    if value is not None:
                        break

        if value is None:
            logger.warning(f"Missing translation for key: {key} in lang: {lang}")
            return key

        try:
            return value.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing format key {e} for text: {value}")
            return value

    def get_menu_text(self, key: str, lang: str = DEFAULT_LANG) -> str:
        """Wrapper for menu texts."""
        return self.get_text(key, lang)

    def get_error_text(self, key: str, lang: str = DEFAULT_LANG) -> str:
        """Wrapper for error texts."""
        return self.get_text(key, lang)
