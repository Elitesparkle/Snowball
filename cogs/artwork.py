import os
import random

import discord
from discord.ext import commands

from tools.misc import Misc


class Artwork(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.folder = "./images/artworks"
        self.images = [file for file in os.listdir(self.folder) if file.endswith("png")]
        print("Artwork extension loaded.")

    @commands.slash_command(name="artwork", description="Get a random artwork.")
    async def random_artwork(self, context: discord.ApplicationContext) -> None:
        # To give enough time for uploading bigger images.
        await context.defer()

        filename = random.choice(self.images)
        path = f"{self.folder}/{filename}"
        file = discord.File(path, filename)
        await context.respond(file=file)
        event = "Artwork shared."
        Misc.send_log(context, event)


def setup(bot) -> None:
    bot.add_cog(Artwork(bot))
