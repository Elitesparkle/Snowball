import discord
from discord.ext import commands

from config import bot_settings
from tools.misc import Misc


class Error(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Error extension loaded.")

    @commands.Cog.listener()
    async def on_application_command_error(
        self, context: discord.ApplicationContext, error: discord.DiscordException
    ) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            cooldown_display = Misc.display_time(int(error.retry_after) + 1)
            content = f"Warning! Command on cooldown for {cooldown_display}."
            await context.respond(content=content, ephemeral=True)
            Misc.send_log(context, "Cooldown.")
        elif isinstance(error, commands.NotOwner):
            content = "Forbidden! Only bot's owners can use this command."
            await context.respond(content=content, ephemeral=True)
            Misc.send_log(context, "Not owner.")
        elif isinstance(error, discord.Forbidden):
            content = "Warning! Snowball doesn't have permissions for that."
            await context.respond(content=content, ephemeral=True)
            Misc.send_log(context, "Forbidden.")
        else:
            content = f"Error! Please, join the official [Snowball Discord Bot]({bot_settings.official_server}) server for support."
            await context.respond(content=content, ephemeral=True)
            Misc.send_log(context, "Error.")
            raise error


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Error(bot))
