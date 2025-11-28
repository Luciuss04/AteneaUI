import asyncio
from collections import deque
import random
import discord
from .youtube import ffmpeg_before

class MusicPlayer:
    def __init__(self):
        self.queue = deque()
        self.current = None
        self.playing = False
        self.lock = asyncio.Lock()
        self.volume = 1.0

    async def add(self, item):
        self.queue.append(item)

    def _play_next(self, vc, bot):
        if self.queue:
            item = self.queue.popleft()
            self.current = item
            try:
                base = discord.FFmpegPCMAudio(item["url"], executable="ffmpeg", before_options=ffmpeg_before, options="-vn")
                source = discord.PCMVolumeTransformer(base, volume=self.volume)
                vc.play(
                    source,
                    after=lambda e: bot.loop.call_soon_threadsafe(
                        self._after_play if not e else self._handle_error, vc, bot, e
                    ),
                )
            except Exception as e:
                print(f"[ERROR] FFmpeg/Playback: {e}")
                self.current = None
                self.playing = False
        else:
            self.current = None
            self.playing = False

    def _after_play(self, vc, bot):
        self._play_next(vc, bot)

    def _handle_error(self, vc, bot, error):
        print(f"[ERROR] Playback callback: {error}")
        self._play_next(vc, bot)

    def set_volume(self, vc, vol: float):
        self.volume = max(0.0, min(vol, 2.0))
        if vc and vc.source and hasattr(vc.source, "volume"):
            vc.source.volume = self.volume

    def remove_at(self, index: int):
        if index < 0 or index >= len(self.queue):
            return None
        lst = list(self.queue)
        item = lst.pop(index)
        self.queue = deque(lst)
        return item

    def shuffle(self):
        lst = list(self.queue)
        random.shuffle(lst)
        self.queue = deque(lst)

    def clear(self):
        self.queue.clear()

players = {}

def get_player(guild_id):
    if guild_id not in players:
        players[guild_id] = MusicPlayer()
    return players[guild_id]
