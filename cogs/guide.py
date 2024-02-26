import json

from bs4 import BeautifulSoup  # pip install beautifulsoup4
import discord
from discord import option
from discord.ext import commands
import requests  # pip install requests

from config import authors
from main import MyBot
from tools.autocomplete import Autocomplete
from tools.map import Map
from tools.misc import Misc


class NoDescription(Exception):
    pass


class Guide(commands.Cog):

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Guide extension loaded.")

    @commands.slash_command(
        name="guide",
        description="Get a link to a guide.",
    )
    @option(
        "category",
        description="Select a category.",
        autocomplete=Autocomplete.categories,
    )
    @option(
        "title",
        description="Select a title.",
        autocomplete=Autocomplete.guides,
    )
    async def guide(
        self,
        context: discord.ApplicationContext,
        category: str,
        title: str,
    ) -> None:
        thumbnail_url = "https://mir-s3-cdn-cf.behance.net/project_modules/fs/4cf28827382215.563643d0ae125.jpg"

        if category == "Tips of the Storm":
            author = "Elitesparkle"

            with open(
                "data/misc/tips-of-the-storm.json",
                "r",
                encoding="utf-8",
            ) as file:
                guide = json.load(file)
            description, link = guide[title]
        elif category == "Reddit":
            author = "Elitesparkle"

            proficiency = title.split(" ")[0].lower()
            description = f"A compendium of useful resources for {proficiency} players."

            proficiency = "advanced" if proficiency == "veteran" else proficiency
            link = f"https://old.reddit.com/r/heroesofthestorm/wiki/{proficiency}playerguide"
        else:
            author = "Icy Veins"

            removes = [
                " Map Guide",
                " Tier List",
                "Chen's ",
                "Medivh's ",
                "Ragnaros's ",
            ]
            code = title
            for remove in removes:
                code = code.replace(remove, "")
            code = code.replace(" ", "-").replace("'", "").lower()

            if category == "Gameplay":
                link = f"https://www.icy-veins.com/heroes/{code}"
            else:
                if category == "Map":
                    link = f"https://www.icy-veins.com/heroes/{code}-introduction"
                    thumbnail_url = f"https://static.icy-veins.com/images/heroes/background-images/map-{code}.jpg"
                elif category == "Tier List":
                    link = f"https://www.icy-veins.com/heroes/heroes-of-the-storm-{code}-tier-list"

                    if title.replace(" Tier List", "") in await Map.catalog():
                        thumbnail_url = f"https://static.icy-veins.com/images/heroes/background-images/map-{code}.jpg"

            # Get the meta description for the selected page.
            response = requests.get(link)
            soup = BeautifulSoup(
                markup=response.text,
                features="html.parser",
            )
            metas: list[BeautifulSoup] = soup.find_all("meta")
            descriptions = [
                meta.attrs["content"]
                for meta in metas
                if "name" in meta.attrs and meta.attrs["name"] == "description"
            ]

            try:
                description = descriptions[0]
            except IndexError:
                raise NoDescription

            if description == "":
                raise NoDescription

        embed = discord.Embed(
            title=title,
            url=link,
            description=description,
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=thumbnail_url)
        embed.set_author(**authors[author])

        event = f"{title} shared."
        await context.respond(embed=embed)
        Misc.send_log(context, event)


def setup(bot: MyBot) -> None:
    bot.add_cog(Guide(bot))
