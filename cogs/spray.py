import discord
from discord import option
from discord.ext import commands

from main import MyBot
from tools.autocomplete import Autocomplete
from tools.hero import Hero
from tools.misc import Misc


class Spray(commands.Cog):

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Spray extension loaded.")

    @commands.slash_command(
        name="spray",
        description="Use a Spray made by Carbot Animations.",
    )
    @option(
        "hero",
        description="Select a Hero.",
        autocomplete=Autocomplete.heroes,
    )
    async def spray_use(
        self,
        context: discord.ApplicationContext,
        hero: str = None,
    ) -> None:
        if hero is None:
            hero = await Hero.random()
        else:
            hero = await Hero.fix_name(hero)

        if hero is None:
            event = "Hero not valid."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            return

        hero_code = Hero.get_code(hero, "Blizzard")
        filename = f"storm_lootspray_static_carbots_{hero_code}.png"
        path = f"./images/sprays/{filename}"
        file = discord.File(path, filename=filename)

        try:
            await context.respond(file=file)
        except discord.errors.DiscordServerError:
            event = "Discord error."
            content = f"{event} Please, try again later."
            await context.respond(content, ephemeral=True)
        else:
            event = "Spray used."

        Misc.send_log(context, event)


def setup(bot: MyBot) -> None:
    bot.add_cog(Spray(bot))
