import discord
from discord.ext import commands

from cogs.build import Build
from tools.misc import Misc


class Context(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Context extension loaded.")

    @commands.message_command(
        name="Delete Message",
        description="Delete a message sent by Snowball. Draft-related messages are protected.",
    )
    async def delete_message(
        self, context: discord.ApplicationContext, message: discord.Message
    ) -> None:
        bot_user = self.bot.user
        bot_name = bot_user.name if bot_user is not None else "Bot"

        if message.author == bot_user:
            if "draft" in message.content.lower():
                content = "Draft-related messages cannot be deleted."
            else:
                if context.guild is None:
                    # Gain access to private messages.
                    channel = context.author.dm_channel
                    if channel is None:
                        await context.author.create_dm()
                try:
                    await message.delete()
                except discord.Forbidden:
                    content = "Warning! Snowball doesn't have permissions for that."
                    Misc.send_log(context, "Forbidden.")
                else:
                    content = f"{bot_name}'s message deleted."
                    Misc.send_log(context, content)
        else:
            content = f"You can only delete {bot_name}'s messages."
            Misc.send_log(context, "Denied.")

        await context.respond(content, ephemeral=True)

    @commands.message_command(
        name="Convert Build Code",
        description="Convert an in-game Build Code into a link to a Build.",
    )
    async def convert_build_code(
        self, context: discord.ApplicationContext, message: discord.Message
    ) -> None:
        code = message.content
        await Build.build_conversion(context, code)


def setup(bot) -> None:
    bot.add_cog(Context(bot))
