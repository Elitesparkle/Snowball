import re

import discord
from discord import option
from discord.ext import commands

from config import authors
from main import MyBot
from tools.autocomplete import Autocomplete
from tools.hero import Hero
from tools.misc import Misc


class Build(commands.Cog):

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Build extension loaded.")

    @staticmethod
    async def build_conversion(
        context: discord.ApplicationContext,
        code: str | None = None,
    ) -> None:
        if code is None:
            event = "Build Code not present."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            return

        build_search = re.search(r"\[T\d{7}\,[úa-z\s\.\-\'A-Z]+]", code)
        if build_search is None:
            event = "Build Code not valid."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            return

        build_code = build_search.group(0)  # Extract "[T<Build>,<Hero>]"

        hero = build_code[10:-1]
        hero = await Hero.fix_name(hero)

        if hero is None:
            event = "Hero not valid."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            return

        # Psionic Storm Talent Builder
        build = "-".join(list(build_code[2:9])).replace("0", "x")
        hero_code = Hero.get_code(hero, "Psionic Storm")
        link = f"https://psionic-storm.com/en/talent-calculator/{hero_code}/#talents={build}"

        hero_code = Hero.get_code(hero, "Blizzard")
        filename = f"{hero_code}.png"
        path = f"./images/heroes/{filename}"
        file = discord.File(path, filename)

        build_code = build_code.replace(build_code[10:-1], hero)
        title = f"{hero} Talent Calculator {build_code}"
        description = f"Check this {hero} Build via Talent Calculator and easily share it with your friends."
        embed = discord.Embed(
            title=title,
            url=link,
            description=description,
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=f"attachment://{filename}")
        embed.set_author(**authors["Psionic Storm"])

        event = f"{hero} Talent Calculator shared."

        await context.respond(file=file, embed=embed)
        Misc.send_log(context, event=event)

    @commands.slash_command(
        name="build",
        description="Get a link to a Build.",
    )
    @option(
        "hero",
        description="Select a Hero.",
        autocomplete=Autocomplete.heroes,
    )
    async def share_build(
        self,
        context: discord.ApplicationContext,
        hero: str,
    ) -> None:
        hero = await Hero.fix_name(hero)

        if hero is None:
            event = "Hero not valid."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            return

        hero_code = Hero.get_code(hero, "Icy Veins")
        link = f"https://www.icy-veins.com/heroes/{hero_code}-build-guide"

        title = f"{hero} Build Guide"
        description = f"The ultimate guide to playing {hero} in Heroes of the Storm: talent builds, playstyle, matchups, maps, etc."

        hero_code = Hero.get_code(hero, "Blizzard")
        filename = "thumbnail.png"
        path = f"./images/heroes/{hero_code}.png"
        file = discord.File(path, filename)

        embed = discord.Embed(
            title=title,
            url=link,
            description=description,
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=f"attachment://{filename}")
        embed.set_author(**authors["Icy Veins"])

        event = f"{hero} Build Guide shared."

        await context.respond(file=file, embed=embed)
        Misc.send_log(context, event=event)

    @commands.slash_command(
        name="convert",
        description="Convert an in-game Build Code into a link to a Build.",
    )
    @option(
        "code",
        description="Insert a valid in-game Build Code.",
        required=True,
    )
    async def convert_build_code(
        self,
        context: discord.ApplicationContext,
        code: str,
    ) -> None:
        await self.build_conversion(context, code)


def setup(bot: MyBot) -> None:
    bot.add_cog(Build(bot))
