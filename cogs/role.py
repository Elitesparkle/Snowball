import discord
from discord import option
from discord.ext import commands

from main import MyBot
from tools.hero import Hero
from tools.misc import Misc


class Role(commands.Cog):

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Role extension loaded.")

    roles = [
        "Tank",
        "Bruiser",
        "Melee Assassin",
        "Ranged Assassin",
        "Support",
        "Healer",
    ]

    @commands.slash_command(
        name="role",
        description="Get a list of Heroes from a given Role.",
    )
    @option(
        "role",
        description="Select a Role.",
        choices=roles,
    )
    async def role(
        self,
        context: discord.ApplicationContext,
        role: str,
    ) -> None:
        heroes = await Hero.catalog(role)

        if role in [
            "Tank",
            "Melee Assassin",
        ]:
            heroes.append("Varian")
            heroes.sort()
        elif role == "Bruiser":
            heroes.append("Blaze")
            heroes.sort()

        heroes = ", ".join(heroes)
        event = f"{role}s listed."
        content = f"**{role}:** {heroes}"

        await context.respond(content)
        Misc.send_log(context, event)


def setup(bot: MyBot) -> None:
    bot.add_cog(Role(bot))
