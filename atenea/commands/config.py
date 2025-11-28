import discord
from discord.ext import commands
from discord import app_commands

ALLOWED_KEYS = {"restrict_volume", "restrict_clear", "restrict_invite", "spotify_max_items", "default_volume", "music_channel_id", "music_channel_name"}

class Config(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="config_set", description="Establecer configuración del servidor")
    @app_commands.describe(key="Clave", value="Valor")
    async def config_set(self, interaction: discord.Interaction, key: str, value: str):
        cm = getattr(self.bot, "config_manager", None)
        if key not in ALLOWED_KEYS:
            await interaction.response.send_message("Clave no permitida", ephemeral=True)
            return
        if key.startswith("restrict_"):
            v = value.lower() in ("true", "1", "yes", "on")
        elif key == "spotify_max_items":
            try:
                v = max(1, min(50, int(value)))
            except Exception:
                await interaction.response.send_message("Valor inválido", ephemeral=True)
                return
        elif key == "default_volume":
            try:
                fv = float(value)
                v = max(0.0, min(2.0, fv))
            except Exception:
                await interaction.response.send_message("Valor inválido", ephemeral=True)
                return
        elif key == "music_channel_id":
            try:
                v = int(value)
            except Exception:
                await interaction.response.send_message("Valor inválido", ephemeral=True)
                return
        elif key == "music_channel_name":
            v = value
        else:
            v = value
        cm.set(interaction.guild.id, key, v)
        await interaction.response.send_message("Configuración actualizada", ephemeral=True)

    @app_commands.command(name="config_get", description="Ver configuración del servidor")
    @app_commands.describe(key="Clave")
    async def config_get(self, interaction: discord.Interaction, key: str):
        cm = getattr(self.bot, "config_manager", None)
        val = cm.get(interaction.guild.id, key, None)
        await interaction.response.send_message(f"{key} = {val}", ephemeral=True)

    @app_commands.command(name="config_show", description="Mostrar configuración completa")
    async def config_show(self, interaction: discord.Interaction):
        cm = getattr(self.bot, "config_manager", None)
        data = cm.all(interaction.guild.id)
        emb = discord.Embed(title="Configuración")
        for k, v in data.items():
            emb.add_field(name=k, value=str(v), inline=False)
        await interaction.response.send_message(embed=emb, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Config(bot))
