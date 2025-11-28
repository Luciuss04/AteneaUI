import time
import hmac
import os
from hashlib import sha256
from ..config.store import read_json, write_json, LICENSE_PATH

class LicenseManager:
    def __init__(self, trial_days: int = 7):
        self._data = read_json(LICENSE_PATH)
        self.trial_days = trial_days

    def _now(self):
        return int(time.time())

    def ensure_trial_started(self, guild_id: int):
        gid = str(guild_id)
        g = self._data.get(gid, {})
        if not g.get("trial_start"):
            g["trial_start"] = self._now()
            g["active"] = False
            g["expires_at"] = None
            self._data[gid] = g
            write_json(LICENSE_PATH, self._data)

    def status(self, guild_id: int):
        gid = str(guild_id)
        g = self._data.get(gid, {})
        trial_start = g.get("trial_start")
        active = bool(g.get("active"))
        expires_at = g.get("expires_at")
        if trial_start is None:
            return {"active": False, "trial": True, "remaining": self.trial_days * 86400}
        if active and expires_at:
            remaining = max(0, expires_at - self._now())
            return {"active": True, "trial": False, "remaining": remaining}
        trial_end = trial_start + self.trial_days * 86400
        remaining = max(0, trial_end - self._now())
        return {"active": False, "trial": True, "remaining": remaining}

    def is_allowed(self, guild_id: int):
        s = self.status(guild_id)
        if s["active"]:
            return True
        return s["remaining"] > 0

    def activate(self, guild_id: int, key: str):
        try:
            parts = key.split(":")
            gid_str, exp_str, sig = parts[0], parts[1], parts[2]
            if gid_str != str(guild_id):
                return False
            secret = os.getenv("LICENSE_SECRET")
            if not secret:
                return False
            msg = f"{gid_str}:{exp_str}".encode()
            expected = hmac.new(secret.encode(), msg, sha256).hexdigest()
            if not hmac.compare_digest(expected, sig):
                return False
            expires_at = int(exp_str)
            gid = str(guild_id)
            g = self._data.get(gid, {})
            g["active"] = True
            g["expires_at"] = expires_at
            self._data[gid] = g
            write_json(LICENSE_PATH, self._data)
            return True
        except Exception:
            return False
