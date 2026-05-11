import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any


class Config:
    _instance = None
    _config: Dict[str, Any] = {}
    _user_settings: Dict[str, Any] = {}
    _settings_path: Path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            self._resolve_env_vars()
        
        self._settings_path = Path(__file__).parent.parent.parent / "user_settings.json"
        self._load_user_settings()

    def _load_user_settings(self):
        if self._settings_path.exists():
            with open(self._settings_path, "r", encoding="utf-8") as f:
                self._user_settings = json.load(f)
        else:
            self._user_settings = {}

    def save_user_settings(self, settings: Dict[str, Any]):
        self._user_settings = settings
        with open(self._settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    def get_user_settings(self) -> Dict[str, Any]:
        return self._user_settings.copy()

    def _resolve_env_vars(self):
        def resolve_value(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.environ.get(env_var, "")
            return value

        def resolve_dict(d):
            for key, value in d.items():
                if isinstance(value, dict):
                    resolve_dict(value)
                elif isinstance(value, list):
                    d[key] = [resolve_value(v) for v in value]
                else:
                    d[key] = resolve_value(value)

        resolve_dict(self._config)

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    @property
    def llm(self):
        return self._config.get("llm", {})

    @property
    def storage(self):
        return self._config.get("storage", {})

    @property
    def server(self):
        return self._config.get("server", {})
