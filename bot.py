import os
import discord
from discord.ext import commands
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

class AteneaBot(commands.Bot):
    async def setup_hook(self):
        if not discord.opus.is_loaded():
            try:
                base = os.path.dirname(discord.__file__)
                x64 = os.path.join(base, "bin", "libopus-0.x64.dll")
                x86 = os.path.join(base, "bin", "libopus-0.x86.dll")
                lib = x64 if os.path.exists(x64) else x86
                if os.path.exists(lib):
                    discord.opus.load_opus(lib)
            except Exception:
                pass
        cid = os.getenv("SPOTIFY_CLIENT_ID")
        csec = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.spotify_client = None
        if cid and csec:
            auth = SpotifyClientCredentials(client_id=cid, client_secret=csec)
            self.spotify_client = Spotify(auth_manager=auth)
        from atenea.config.manager import ConfigManager
        from atenea.license.manager import LicenseManager
        self.config_manager = ConfigManager()
        self.license_manager = LicenseManager(trial_days=7)
        await self.load_extension("atenea.commands.music")
        await self.load_extension("atenea.commands.license")
        await self.load_extension("atenea.commands.config")
        self._announced = set()

    async def on_ready(self):
        await self.tree.sync()
        print(f"Conectado como {self.user}")
        for g in self.guilds:
            if g.id in self._announced:
                continue
            ch = None
            cid = self.config_manager.get(g.id, "music_channel_id", None)
            if cid:
                ch = g.get_channel(int(cid))
            if not ch:
                name = self.config_manager.get(g.id, "music_channel_name", None)
                if name:
                    for c in g.text_channels:
                        if c.name.lower() == str(name).lower():
                            ch = c
                            break
            if not ch:
                for c in g.text_channels:
                    if c.permissions_for(g.me).send_messages:
                        if c.name.lower() in ("musica", "música", "music"):
                            ch = c
                            break
                if not ch and g.text_channels:
                    c = g.text_channels[0]
                    if c.permissions_for(g.me).send_messages:
                        ch = c
            if not ch:
                continue
            cmds = self.tree.get_commands()
            emb = discord.Embed(title="Comandos disponibles", color=0x00AEEF)
            for c in cmds:
                desc = c.description or ""
                emb.add_field(name=f"/{c.name}", value=desc or " ", inline=False)
            pasos = "1) Únete a un canal de voz\n" \
                    "2) /join para conectar el bot\n" \
                    "3) /play <búsqueda o URL>\n" \
                    "4) /volume 80 para ajustar volumen\n" \
                    "5) /queue, /skip, /stop para gestionar la reproducción"
            emb.add_field(name="Primeros pasos", value=pasos, inline=False)
            try:
                await ch.send(embed=emb)
                self._announced.add(g.id)
            except Exception:
                pass
            try:
                bot_id = self.user.id
                perms = 3147776
                url = f"https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot%20applications.commands&permissions={perms}"
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Invitar bot", style=discord.ButtonStyle.link, url=url))
                await ch.send(view=view)
            except Exception:
                pass

def main():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = AteneaBot(command_prefix="!", intents=intents)
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Falta DISCORD_TOKEN")
        return
    bot.run(token)

if __name__ == "__main__":
    main()
