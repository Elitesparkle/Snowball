import json

import discord
from discord import option
from discord.ext import commands

from main import MyBot
from tools.autocomplete import Autocomplete
from tools.map import Map
from tools.misc import Misc


class Timing(commands.Cog):

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Timing extension loaded.")

    @commands.slash_command(
        name="timings",
        description="View timings for Maps.",
    )
    @option(
        "map",
        description="Select a Map.",
        autocomplete=Autocomplete.maps,
    )
    @option(
        "timing",
        description="Select the timing you are looking for.",
        autocomplete=Autocomplete.timings,
        default=None,
    )
    @option(
        "format",
        description="Select a Hero.",
        choices=["Minutes", "Seconds"],
        default="Minutes",
    )
    async def timings(
        self,
        context: discord.ApplicationContext,
        map: str,
        timing: str,
        format: str,
    ) -> None:
        if "All" in map:
            if timing == "Lava Wave Timings":
                description = "+1 second every 4 minutes"
            else:
                description = None

                if timing is None:
                    timing = "Objective Respawn"

            embed = discord.Embed(
                title=timing,
                description=description,
                color=discord.Color.blue(),
            )

            with open(
                "./data/misc/maps.json",
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            maps = await Map.catalog(map[5:-1])
            for map in maps:
                if "Objective" in timing:
                    value = Map.format_timing(data[map][timing], format)
                else:
                    value = data[map][timing]

                if not "?" in value:
                    embed.add_field(
                        name=map,
                        value=value,
                        inline=False,
                    )

            await context.respond(embed=embed)
        else:
            if timing is None:
                timing = "All Timings"

            embed = discord.Embed(
                title=map,
                color=discord.Color.blue(),
            )

            with open(
                "./data/misc/maps.json",
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            if timing in [
                "All Timings",
                "Objective Spawn",
                "Objective Timings",
            ]:

                try:
                    value = Map.format_timing(data[map]["Objective Spawn"], format)
                except KeyError:
                    event = "Map not found."
                    content = f"{event} Select an option from the list."

                    await context.respond(content, ephemeral=True)
                    Misc.send_log(context, event)

                    return

                embed.add_field(
                    name="Objective Spawn",
                    value=value,
                    inline=False,
                )

            if timing in [
                "All Timings",
                "Objective Respawn",
                "Objective Timings",
            ]:
                value = Map.format_timing(data[map]["Objective Respawn"], format)
                embed.add_field(
                    name="Objective Respawn",
                    value=value,
                    inline=False,
                )

            if timing in [
                "All Timings",
                "Lava Wave Timings",
                "Offlane Timings",
            ]:
                value = data[map]["Lava Wave Timings"]
                embed.add_field(
                    name="Lava Wave Timings",
                    value=f"{value}\n+1 second every 4 minutes",
                    inline=False,
                )

            if timing in [
                "All Timings",
                "Minions Crash",
                "Offlane Timings",
            ]:
                value = data[map]["Minions Crash"]
                embed.add_field(
                    name="Minions Crash",
                    value=value,
                    inline=False,
                )

            if timing in [
                "All Timings",
                "Rotation Time",
                "Offlane Timings",
            ]:
                value = data[map]["Rotation Time"]
                embed.add_field(
                    name="Rotation Time",
                    value=value,
                    inline=False,
                )

            map_code = map.lower().replace(" ", "-").replace("'", "")
            filename = f"{map_code}-map-preview.png"
            path = f"./images/minimaps/{filename}"
            file = discord.File(path, filename)
            embed.set_image(url=f"attachment://{filename}")
            await context.respond(file=file, embed=embed)

        event = "Timings shared."
        Misc.send_log(context, event)


def setup(bot: MyBot) -> None:
    bot.add_cog(Timing(bot))
