import random

import discord
from discord.ext import commands

from tools.misc import Misc


class Joke(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Joke extension loaded.")

    @commands.slash_command(name="joke", description="Get a random joke.")
    async def random_joke(self, context: discord.ApplicationContext) -> None:
        with open("./data/misc/jokes.txt", "r", encoding="utf-8") as file:
            data = list(file)

        event = "Joke shared."
        Misc.send_log(context, event)

        content = random.choice(data)
        await context.respond(content)


def setup(bot) -> None:
    bot.add_cog(Joke(bot))
