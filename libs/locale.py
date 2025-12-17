import json
from pathlib import Path
from functools import lru_cache
from typing import Dict
from difflib import SequenceMatcher


class LocaleManager:
    __slots__ = ('_mods', '_ui', '_status', '_notifications', '_errors', '_categories', '_empty_state', '_lang', '_cache')
    
    def __init__(self, locales_path: Path, language: str = "en"):
        self._mods: Dict = {}
        self._ui: Dict = {}
        self._status: Dict = {}
        self._notifications: Dict = {}
        self._errors: Dict = {}
        self._categories: Dict = {}
        self._empty_state: Dict = {}
        self._lang = language
        self._cache: Dict = {}
        self._load(locales_path)
    
    def _load(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            with path.open('r', encoding='utf-8') as f:
                data = json.load(f)
            self._mods = data.get("mods", {})
            self._ui = data.get("ui", {})
            self._status = data.get("status", {})
            self._notifications = data.get("notifications", {})
            self._errors = data.get("errors", {})
            self._categories = data.get("categories", {})
            self._empty_state = data.get("empty_state", {})
            self._build_cache()
        except Exception as e:
            print(f"Error loading locales: {e}")
    
    def _build_cache(self) -> None:
        self._cache.clear()
        for section in [self._ui, self._status, self._notifications, self._errors, self._empty_state]:
            for key, translations in section.items():
                self._cache[key] = translations.get(self._lang, translations.get("en", key))
    
    def set_language(self, lang: str) -> None:
        if lang != self._lang:
            self._lang = lang
            self._build_cache()
            self.get_mod_name.cache_clear()
            self.get_category_name.cache_clear()
    
    def _normalize(self, text: str) -> str:
        return text.lower().replace("_", " ").replace("-", " ").replace(":", "").strip()
    
    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()
    
    @lru_cache(maxsize=256)
    def get_mod_name(self, filename: str) -> str:
        filename_norm = self._normalize(filename)
        best_match = None
        best_score = 0.0
        
        for code, info in self._mods.items():
            if code.lower() in filename_norm:
                name = info.get(self._lang, info.get("en", ""))
                return name.replace("_", " ") if name else self.t("unknown_mod")
            
            en_name = self._normalize(info.get("en", ""))
            if en_name:
                score = self._similarity(filename_norm, en_name)
                if score > best_score and score >= 0.75:
                    best_score = score
                    best_match = info
                if en_name in filename_norm and score > 0.6:
                    best_score = max(best_score, score)
                    best_match = info
            
            pl_name = self._normalize(info.get("pl", ""))
            if pl_name:
                score = self._similarity(filename_norm, pl_name)
                if score > best_score and score >= 0.75:
                    best_score = score
                    best_match = info
                if pl_name in filename_norm and score > 0.6:
                    best_score = max(best_score, score)
                    best_match = info
        
        if best_match:
            name = best_match.get(self._lang, best_match.get("en", ""))
            return name.replace("_", " ") if name else self.t("unknown_mod")
        return self.t("unknown_mod")
    
    @lru_cache(maxsize=256)
    def get_mod_category(self, filename: str) -> str:
        filename_norm = self._normalize(filename)
        
        for code, info in self._mods.items():
            if code.lower() in filename_norm:
                return code[:2]
            
            en_name = self._normalize(info.get("en", ""))
            pl_name = self._normalize(info.get("pl", ""))
            
            if en_name and (en_name in filename_norm or self._similarity(filename_norm, en_name) >= 0.75):
                return code[:2]
            if pl_name and (pl_name in filename_norm or self._similarity(filename_norm, pl_name) >= 0.75):
                return code[:2]
        return 'OTHER'
    
    @lru_cache(maxsize=64)
    def get_category_name(self, category: str) -> str:
        return self._categories.get(category, {}).get(self._lang, category)
    
    def t(self, key: str, *args) -> str:
        text = self._cache.get(key, key)
        if args:
            return text.format(*args)
        return text
    
    @property
    def language(self) -> str:
        return self._lang
