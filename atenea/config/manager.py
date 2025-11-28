from .store import read_json, write_json, CONFIG_PATH

class ConfigManager:
    def __init__(self):
        self._data = read_json(CONFIG_PATH)

    def get(self, guild_id: int, key: str, default=None):
        g = self._data.get(str(guild_id), {})
        return g.get(key, default)

    def set(self, guild_id: int, key: str, value):
        gid = str(guild_id)
        g = self._data.get(gid, {})
        g[key] = value
        self._data[gid] = g
        write_json(CONFIG_PATH, self._data)

    def all(self, guild_id: int):
        return self._data.get(str(guild_id), {})
