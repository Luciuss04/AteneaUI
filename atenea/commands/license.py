import os
import time
import hmac
from hashlib import sha256
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands

class License(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="license_status", description="Ver estado de la licencia")
    async def license_status(self, interaction: discord.Interaction):
        lm = getattr(self.bot, "license_manager", None)
        lm.ensure_trial_started(interaction.guild.id)
        s = lm.status(interaction.guild.id)
        rem = s.get("remaining", 0)
        mins = rem // 60
        hrs = rem // 3600
        days = rem // 86400
        title = "Licencia activa" if s.get("active") else "Prueba"
        desc = f"Quedan {days}d {hrs%24}h {mins%60}m"
        emb = discord.Embed(title=title, description=desc)
        await interaction.response.send_message(embed=emb, ephemeral=True)

    @app_commands.command(name="license_activate", description="Activar licencia con clave")
    @app_commands.describe(key="Clave de licencia")
    async def license_activate(self, interaction: discord.Interaction, key: str):
        lm = getattr(self.bot, "license_manager", None)
        ok = lm.activate(interaction.guild.id, key)
        if ok:
            await interaction.response.send_message("Licencia activada", ephemeral=True)
        else:
            await interaction.response.send_message("Clave inválida o secreto no configurado", ephemeral=True)

    @app_commands.command(name="license_generate", description="Generar licencia para un servidor")
    @app_commands.describe(days="Días de validez", guild_id="ID del servidor (opcional)")
    async def license_generate(self, interaction: discord.Interaction, days: app_commands.Range[int, 1, 365], guild_id: Optional[int] = None):
        if interaction.user.id != 443479189597716480:
            await interaction.response.send_message("No autorizado", ephemeral=True)
            return
        secret = os.getenv("LICENSE_SECRET")
        if not secret:
            await interaction.response.send_message("Configura LICENSE_SECRET", ephemeral=True)
            return
        gid = guild_id or (interaction.guild.id if interaction.guild else None)
        if not gid:
            await interaction.response.send_message("Proporciona guild_id cuando ejecutes el comando fuera de un servidor", ephemeral=True)
            return
        expires_at = int(time.time()) + days * 86400
        msg = f"{gid}:{expires_at}".encode()
        sig = hmac.new(secret.encode(), msg, sha256).hexdigest()
        key = f"{gid}:{expires_at}:{sig}"
        await interaction.response.send_message(key, ephemeral=True)

async def setup(bot):
    await bot.add_cog(License(bot))
