import discord
from discord.ext import commands

from config import bot_settings
from main import MyBot
from tools.misc import Misc


class Error(commands.Cog):

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Error extension loaded.")

    @commands.Cog.listener()
    async def on_application_command_error(
        self,
        context: discord.ApplicationContext,
        error: discord.DiscordException,
    ) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            cooldown_display = Misc.display_time(int(error.retry_after) + 1)
            event = "Cooldown."
            content = f"Warning! Command on cooldown for {cooldown_display}."
        elif isinstance(error, commands.NotOwner):
            event = "Not owner."
            content = "Forbidden! Only bot's owners can use this command."
        elif isinstance(error, discord.Forbidden):
            event = "Forbidden."
            content = "Warning! Snowball doesn't have permissions for that."
        else:
            event = "Error!"
            content = f"{event} Please, join the official [Snowball Discord Bot]({bot_settings.official_server}) server for support."
            raise error

        await context.respond(content, ephemeral=True)
        Misc.send_log(context, event)


def setup(bot: MyBot) -> None:
    bot.add_cog(Error(bot))
