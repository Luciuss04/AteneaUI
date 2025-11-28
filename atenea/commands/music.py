import shutil
import discord
from discord.ext import commands
from discord import app_commands
from ..music.youtube import ytdl_search, ytdl_suggest
from ..music.spotify import is_spotify_url, resolve_spotify_items
from ..music.player import get_player
from ..utils import fmt_duration
from ..config.manager import ConfigManager
from ..license.manager import LicenseManager

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot, spotify_client):
        self.bot = bot
        self.spotify_client = spotify_client
        self.config = getattr(bot, "config_manager", None) or ConfigManager()
        self.license = getattr(bot, "license_manager", None) or LicenseManager()

    async def ensure_voice_interaction(self, interaction: discord.Interaction):
        user = interaction.user
        if hasattr(user, "voice") and user.voice and user.voice.channel:
            channel = user.voice.channel
            vc = interaction.guild.voice_client if interaction.guild else None
            if vc and vc.channel == channel:
                return vc
            if vc:
                await vc.move_to(channel)
                return vc
            return await channel.connect()
        if interaction.response.is_done():
            await interaction.followup.send("Debes estar en un canal de voz", ephemeral=True)
        else:
            await interaction.response.send_message("Debes estar en un canal de voz", ephemeral=True)
        return None

    @app_commands.command(name="join", description="Unirse al canal de voz")
    async def join(self, interaction: discord.Interaction):
        vc = await self.ensure_voice_interaction(interaction)
        if vc:
            await interaction.response.send_message(f"Unido a {vc.channel.name}")

    @app_commands.command(name="leave", description="Salir del canal de voz")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("Desconectado")
        else:
            await interaction.response.send_message("No estoy en un canal de voz", ephemeral=True)

    @app_commands.command(name="play", description="Reproducir música desde YouTube o Spotify")
    @app_commands.describe(query="URL o búsqueda")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.send_message("Procesando...", ephemeral=True)
        if not shutil.which("ffmpeg"):
            await interaction.followup.send("FFmpeg no está instalado en el sistema.", ephemeral=True)
            return
        self.license.ensure_trial_started(interaction.guild.id)
        if not self.license.is_allowed(interaction.guild.id):
            await interaction.followup.send("Licencia expirada. Usa /license_activate.", ephemeral=True)
            return
        vc = await self.ensure_voice_interaction(interaction)
        if not vc:
            return
        player = get_player(interaction.guild.id)
        dv = self.config.get(interaction.guild.id, "default_volume", 1.0)
        try:
            player.set_volume(vc, float(dv))
        except Exception:
            pass
        added_titles = []
        async with player.lock:
            if is_spotify_url(query):
                if not self.spotify_client:
                    await interaction.followup.send("Configura SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET", ephemeral=True)
                    return
                searches = resolve_spotify_items(self.spotify_client, query)
                if not searches:
                    await interaction.followup.send("No se pudo resolver el enlace de Spotify", ephemeral=True)
                    return
                for s in searches:
                    item = ytdl_search(s)
                    await player.add(item)
                    added_titles.append(item["title"])
            else:
                item = ytdl_search(query)
                await player.add(item)
                added_titles.append(item["title"])
            if not player.playing and not vc.is_playing():
                player.playing = True
                player._play_next(vc, self.bot)
        if len(added_titles) == 1:
            item = get_player(interaction.guild.id).current or ytdl_search(query)
            emb = discord.Embed(title=added_titles[0], url=item.get("webpage_url"), description=f"Duración: {fmt_duration(item.get('duration'))}")
            if item.get("thumbnail"):
                emb.set_thumbnail(url=item["thumbnail"])
            await interaction.followup.send(content="Añadido a la cola", embed=emb)
        else:
            await interaction.followup.send(f"Añadidas {len(added_titles)} canciones")

    @play.autocomplete("query")
    async def play_autocomplete(self, interaction: discord.Interaction, current: str):
        if not current:
            return []
        if is_spotify_url(current):
            return [app_commands.Choice(name="Enlace de Spotify detectado", value=current)]
        suggestions = ytdl_suggest(current)
        choices = []
        for s in suggestions[:10]:
            name = s["title"]
            chan = s.get("channel")
            dur = fmt_duration(s.get("duration"))
            label = f"{name} • {chan or 'YouTube'} • {dur}"
            choices.append(app_commands.Choice(name=label[:100], value=s["webpage_url"]))
        return choices

    @app_commands.command(name="skip", description="Saltar la canción actual")
    async def skip(self, interaction: discord.Interaction):
        self.license.ensure_trial_started(interaction.guild.id)
        if not self.license.is_allowed(interaction.guild.id):
            await interaction.response.send_message("Licencia expirada", ephemeral=True)
            return
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("Saltado")
        else:
            await interaction.response.send_message("No hay reproducción", ephemeral=True)

    @app_commands.command(name="pause", description="Pausar la reproducción")
    async def pause(self, interaction: discord.Interaction):
        self.license.ensure_trial_started(interaction.guild.id)
        if not self.license.is_allowed(interaction.guild.id):
            await interaction.response.send_message("Licencia expirada", ephemeral=True)
            return
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("Pausado")
        else:
            await interaction.response.send_message("No hay reproducción", ephemeral=True)

    @app_commands.command(name="resume", description="Reanudar la reproducción")
    async def resume(self, interaction: discord.Interaction):
        self.license.ensure_trial_started(interaction.guild.id)
        if not self.license.is_allowed(interaction.guild.id):
            await interaction.response.send_message("Licencia expirada", ephemeral=True)
            return
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("Reanudado")
        else:
            await interaction.response.send_message("No está pausado", ephemeral=True)

    @app_commands.command(name="stop", description="Detener y vaciar la cola")
    async def stop(self, interaction: discord.Interaction):
        self.license.ensure_trial_started(interaction.guild.id)
        if not self.license.is_allowed(interaction.guild.id):
            await interaction.response.send_message("Licencia expirada", ephemeral=True)
            return
        vc = interaction.guild.voice_client if interaction.guild else None
        player = get_player(interaction.guild.id)
        player.queue.clear()
        player.playing = False
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
        await interaction.response.send_message("Detenido y cola vaciada")

    @app_commands.command(name="now", description="Ver la canción actual")
    async def now(self, interaction: discord.Interaction):
        self.license.ensure_trial_started(interaction.guild.id)
        if not self.license.is_allowed(interaction.guild.id):
            await interaction.response.send_message("Licencia expirada", ephemeral=True)
            return
        player = get_player(interaction.guild.id)
        if player.current:
            item = player.current
            emb = discord.Embed(title=item["title"], url=item.get("webpage_url"), description=f"Duración: {fmt_duration(item.get('duration'))}")
            if item.get("thumbnail"):
                emb.set_thumbnail(url=item["thumbnail"])
            await interaction.response.send_message(embed=emb)
        else:
            await interaction.response.send_message("Nada en reproducción", ephemeral=True)

    @app_commands.command(name="queue", description="Ver la cola de reproducción")
    async def queue(self, interaction: discord.Interaction):
        self.license.ensure_trial_started(interaction.guild.id)
        if not self.license.is_allowed(interaction.guild.id):
            await interaction.response.send_message("Licencia expirada", ephemeral=True)
            return
        player = get_player(interaction.guild.id)
        if not player.queue:
            await interaction.response.send_message("Cola vacía", ephemeral=True)
            return
        emb = self.build_queue_embed(player, page=0)
        view = QueueView(self, interaction.guild.id)
        await interaction.response.send_message(embed=emb, view=view)

    @app_commands.command(name="volume", description="Ajustar volumen (0-200)")
    @app_commands.describe(value="Valor de volumen 0-200")
    async def volume(self, interaction: discord.Interaction, value: app_commands.Range[int, 0, 200]):
        self.license.ensure_trial_started(interaction.guild.id)
        if not self.license.is_allowed(interaction.guild.id):
            await interaction.response.send_message("Licencia expirada", ephemeral=True)
            return
        if self.config.get(interaction.guild.id, "restrict_volume", False):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("Solo administradores pueden usar este comando", ephemeral=True)
                return
        vc = interaction.guild.voice_client if interaction.guild else None
        player = get_player(interaction.guild.id)
        vol = float(value) / 100.0
        player.set_volume(vc, vol)
        self.config.set(interaction.guild.id, "default_volume", vol)
        await interaction.response.send_message(f"Volumen establecido a {value}%")

    @app_commands.command(name="volume_default", description="Ver el volumen por defecto del servidor")
    async def volume_default(self, interaction: discord.Interaction):
        dv = self.config.get(interaction.guild.id, "default_volume", 1.0)
        pct = int(round(float(dv) * 100))
        await interaction.response.send_message(f"Volumen por defecto: {pct}%", ephemeral=True)

    @app_commands.command(name="help", description="Mostrar ayuda de comandos")
    async def help(self, interaction: discord.Interaction):
        cmds = self.bot.tree.get_commands()
        emb = discord.Embed(title="Comandos disponibles", color=0x00AEEF)
        for c in cmds:
            emb.add_field(name=f"/{c.name}", value=c.description or " ", inline=False)
        pasos = "1) Únete a un canal de voz\n" \
                "2) /join para conectar el bot\n" \
                "3) /play <búsqueda o URL>\n" \
                "4) /volume 80 para ajustar volumen\n" \
                "5) /queue, /skip, /stop para gestionar la reproducción"
        emb.add_field(name="Primeros pasos", value=pasos, inline=False)
        extras = "Spotify: /play con enlace de Spotify (requiere SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET)\n" \
                 "Licencia: /license_status y /license_activate <clave>"
        emb.add_field(name="Extras", value=extras, inline=False)
        perms = getattr(interaction.user, "guild_permissions", None)
        if perms and (perms.administrator or perms.manage_guild):
            try:
                bot_id = self.bot.user.id
                url = f"https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot%20applications.commands&permissions=3147776"
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Invitar bot", style=discord.ButtonStyle.link, url=url))
                await interaction.response.send_message(embed=emb, view=view, ephemeral=True)
                return
            except Exception:
                pass
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @app_commands.command(name="remove", description="Eliminar de la cola por índice (1-n)")
    @app_commands.describe(index="Índice en la cola (1-n)")
    async def remove(self, interaction: discord.Interaction, index: app_commands.Range[int, 1, 1000]):
        self.license.ensure_trial_started(interaction.guild.id)
        if not self.license.is_allowed(interaction.guild.id):
            await interaction.response.send_message("Licencia expirada", ephemeral=True)
            return
        player = get_player(interaction.guild.id)
        removed = player.remove_at(index - 1)
        if removed:
            await interaction.response.send_message(f"Eliminado: {removed['title']}")
        else:
            await interaction.response.send_message("Índice inválido", ephemeral=True)

    @app_commands.command(name="shuffle", description="Mezclar la cola")
    async def shuffle(self, interaction: discord.Interaction):
        self.license.ensure_trial_started(interaction.guild.id)
        if not self.license.is_allowed(interaction.guild.id):
            await interaction.response.send_message("Licencia expirada", ephemeral=True)
            return
        player = get_player(interaction.guild.id)
        player.shuffle()
        await interaction.response.send_message("Cola mezclada")

    @app_commands.command(name="clear", description="Vaciar la cola")
    async def clear(self, interaction: discord.Interaction):
        self.license.ensure_trial_started(interaction.guild.id)
        if not self.license.is_allowed(interaction.guild.id):
            await interaction.response.send_message("Licencia expirada", ephemeral=True)
            return
        if self.config.get(interaction.guild.id, "restrict_clear", False):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("Solo administradores pueden usar este comando", ephemeral=True)
                return
        player = get_player(interaction.guild.id)
        player.clear()
        await interaction.response.send_message("Cola vaciada")

    @app_commands.command(name="invite", description="Obtener enlace de invitación del bot")
    async def invite(self, interaction: discord.Interaction):
        if self.config.get(interaction.guild.id, "restrict_invite", False):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("Solo administradores pueden usar este comando", ephemeral=True)
                return
        bot_id = self.bot.user.id
        perms = 3147776
        url = f"https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot%20applications.commands&permissions={perms}"
        view = InviteConfirmView(self.bot, interaction.user.id, url)
        await interaction.response.send_message("Pulsa Confirmar para obtener el enlace", ephemeral=True, view=view)

    def build_queue_embed(self, player, page: int, per_page: int = 10):
        total = len(player.queue)
        start = page * per_page
        end = min(start + per_page, total)
        emb = discord.Embed(title="Cola de reproducción", description=f"Total: {total}")
        for idx, item in enumerate(list(player.queue)[start:end], start=start + 1):
            dur = fmt_duration(item.get("duration"))
            emb.add_field(name=f"{idx}. {item['title']}", value=f"{dur}", inline=False)
        return emb

class QueueView(discord.ui.View):
    def __init__(self, cog: Music, guild_id: int, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.guild_id = guild_id
        self.page = 0
        self.per_page = 10

    async def update_message(self, interaction: discord.Interaction):
        player = get_player(self.guild_id)
        emb = self.cog.build_queue_embed(player, self.page, self.per_page)
        await interaction.response.edit_message(embed=emb, view=self)

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await self.update_message(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = get_player(self.guild_id)
        max_page = max(0, (len(player.queue) - 1) // self.per_page)
        if self.page < max_page:
            self.page += 1
        await self.update_message(interaction)

class InviteConfirmView(discord.ui.View):
    def __init__(self, bot: commands.Bot, user_id: int, url: str, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.user_id = user_id
        self.url = url

    async def ensure_user(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Esta confirmación no es para ti", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.ensure_user(interaction):
            return
        await interaction.response.edit_message(content=f"Invítame con: {self.url}", view=None)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.ensure_user(interaction):
            return
        await interaction.response.edit_message(content="Cancelado", view=None)


async def setup(bot):
    spotify_client = getattr(bot, "spotify_client", None)
    await bot.add_cog(Music(bot, spotify_client))
