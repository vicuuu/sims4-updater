import json
import sys
from pathlib import Path
from functools import lru_cache


def get_locales_path() -> Path:
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        if (exe_dir / "locales.json").exists():
            return exe_dir / "locales.json"
        return Path(sys._MEIPASS) / "locales.json"
    else:
        return Path(__file__).parent.parent / "locales.json"


LOCALES_FILE = get_locales_path()


class LocaleManager:
    __slots__ = ('mods', 'ui_texts', 'language', '_cache')
    
    def __init__(self, language: str = "pl"):
        self.mods: dict = {}
        self.ui_texts: dict = {}
        self.language = language
        self._cache: dict = {}
        self._load_locales()
    
    def _load_locales(self) -> None:
        if not LOCALES_FILE.exists():
            return
        
        try:
            with LOCALES_FILE.open('r', encoding='utf-8') as f:
                data = json.load(f)
            self.mods = data.get("mods", {})
            self.ui_texts = data.get("ui", {})
            self._build_cache()
        except (json.JSONDecodeError, IOError) as e:
            print(f"locales.json: {e}")
    
    def _build_cache(self) -> None:
        self._cache.clear()
        for key, translations in self.ui_texts.items():
            self._cache[key] = translations.get(self.language) or translations.get("en", key)
    
    def get_mod_name(self, filename: str) -> str:
        for code, info in self.mods.items():
            if code in filename:
                name = info.get(self.language) or info.get("en", "")
                return name.replace("_", " ") if name else self._cache.get("unknown_mod", "Unknown mod")
        return self._cache.get("unknown_mod", "Unknown mod")
    
    def t(self, key: str) -> str:
        if key in self._cache:
            return self._cache[key]
        
        translations = self.ui_texts.get(key)
        if translations:
            result = translations.get(self.language) or translations.get("en", key)
            self._cache[key] = result
            return result
        return key


locale_mgr = LocaleManager(language="en")