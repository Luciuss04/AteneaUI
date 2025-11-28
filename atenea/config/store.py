import os
import json
from threading import RLock

BASE_DIR = os.path.join(os.getcwd(), "data")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LICENSE_PATH = os.path.join(BASE_DIR, "licenses.json")

_lock = RLock()

def _ensure_dir():
    if not os.path.isdir(BASE_DIR):
        os.makedirs(BASE_DIR, exist_ok=True)

def read_json(path: str):
    _ensure_dir()
    if not os.path.isfile(path):
        return {}
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

def write_json(path: str, data: dict):
    _ensure_dir()
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
