import json

import discord

from database import database_connection
from tools.hero import Hero
from tools.map import Map
from tools.misc import Misc


class MatchupsException(Exception):
    pass


class Autocomplete:

    @staticmethod
    async def guide_types(context: discord.AutocompleteContext):
        input = Misc.alpha_unidecode_lower(context.value)

        choices = ["Gameplay", "Map", "Reddit", "Tier List", "Tips of the Storm"]

        return [
            choice for choice in choices if input in Misc.alpha_unidecode_lower(choice)
        ]

    @staticmethod
    async def guides(context: discord.AutocompleteContext):
        input = Misc.alpha_unidecode_lower(context.value)

        type = context.options["type"]

        gameplay_guides = [
            "Debug Mode Guide",
            "Holdable Abilities",
            "Hotkeys Advanced Guide",
            "Ragnaros's Lava Wave Timings",
            "Medivh's Portal Mastery",
            "Observer and Replay Interface Guide",
            "Opening Moves",
            "Spell Power and Damage Modifier",
            "Chen's Wandering Keg",
        ]

        map_guides = [
            "Hanamura Temple Map Guide",
            "Garden of Terror Map Guide",
            "Warhead Junction Map Guide",
        ]

        reddit_guides = [
            "New Player Guide",
            "Veteran Player Guide",
            "Returning Player Guide",
        ]

        global_tierlists = [
            "Quick Match Tier List",
            "General Tier List",
            "Master Tier List",
            "ARAM Tier List",
        ]

        tierlists = global_tierlists + [
            f"{map} Tier List" for map in await Map.catalog()
        ]

        with open("data/misc/tips-of-the-storm.json", "r", encoding="utf-8") as file:
            external_tips = json.load(file)

        tips = list(external_tips.keys())

        if type == "Gameplay":
            choices = gameplay_guides
        elif type == "Map":
            choices = map_guides
        elif type == "Tier List":
            choices = tierlists
        elif type == "Tips of the Storm":
            choices = tips
        elif type == "Reddit":
            choices = reddit_guides
        else:
            choices = gameplay_guides + map_guides + tierlists + tips

        choices.sort()

        return [
            choice for choice in choices if input in Misc.alpha_unidecode_lower(choice)
        ]

    @staticmethod
    async def heroes(context: discord.AutocompleteContext) -> list[str]:
        input = Misc.alpha_unidecode_lower(context.value)

        command_name = context.command.qualified_name
        if command_name.startswith("matchup"):

            async def available_matchups(
                field: str | None = None, hero: str | None = None
            ) -> list[str]:
                if hero is None:
                    query = """
                        SELECT Name,
                            COUNT (*) AS Amount
                        FROM (
                            SELECT Name
                            FROM Matchups
                                INNER JOIN Heroes ON Heroes.HeroID = Matchups.YourHeroID
                            GROUP BY YourHeroID, EnemyHeroID
                        ) AS HeroMatchups
                        GROUP BY Name
                        HAVING Amount > 0
                    """
                    if field == "enemy_hero":
                        query = query.replace(
                            "Matchups.YourHeroID", "Matchups.EnemyHeroID"
                        )
                    async with database_connection.cursor() as cursor:
                        await cursor.execute(query)
                        results = await cursor.fetchall()
                else:
                    query = """
                        SELECT Name,
                            COUNT (*) AS Amount
                        FROM (
                            SELECT Name
                            FROM Matchups
                                INNER JOIN Heroes ON Heroes.HeroID = Matchups.YourHeroID
                            GROUP BY YourHeroID, EnemyHeroID
                            HAVING EnemyHeroID = (
                                SELECT HeroID
                                FROM Heroes
                                WHERE Name = ?
                            )
                        ) AS HeroMatchups
                        GROUP BY Name
                        HAVING Amount > 0
                    """
                    if field == "enemy_hero":
                        query = query.replace(
                            "Matchups.YourHeroID", "Matchups.EnemyHeroID"
                        )
                        query = query.replace("HAVING EnemyHeroID", "HAVING YourHeroID")
                    values = (hero,)
                    async with database_connection.cursor() as cursor:
                        await cursor.execute(query, values)
                        results = await cursor.fetchall()

                try:
                    choices, _ = zip(*results)
                except ValueError:
                    choices = []
                else:
                    choices = list(choices)

                return choices

            if command_name == "matchup list":
                choices = await available_matchups()
            elif command_name == "matchup tips":
                if context.focused.name == "your_hero":
                    enemy_hero = context.options["enemy_hero"]

                    choices = await available_matchups(
                        field="your_hero", hero=enemy_hero
                    )

                    # Remove the selected Hero from choices.
                    if enemy_hero in choices:
                        choices.remove(enemy_hero)
                elif context.focused.name == "enemy_hero":
                    your_hero = context.options["your_hero"]

                    choices = await available_matchups(
                        field="enemy_hero", hero=your_hero
                    )

                    # Remove the selected Hero from choices.
                    if your_hero in choices:
                        choices.remove(your_hero)
                else:
                    raise MatchupsException
            else:
                your_hero = context.options["your_hero"]
                enemy_hero = context.options["enemy_hero"]

                choices = await Hero.catalog("Offlaner")

                # Remove the selected Hero from choices.
                if your_hero in choices:
                    choices.remove(your_hero)

                # Remove the selected Hero from choices.
                if enemy_hero in choices:
                    choices.remove(enemy_hero)
        else:
            choices = await Hero.catalog()

        return [
            choice
            for choice in choices
            if input in Misc.alpha_unidecode_lower(choice)
            or input.upper() == await Hero.get_acronym(choice)
        ]

    @staticmethod
    async def maps(context: discord.AutocompleteContext):
        input = Misc.alpha_unidecode_lower(context.value)

        timing = context.options["timing"]

        # Check if a single Timing has been selected
        if timing not in ["All Timings", "Objective Timings", "Offlane Timings"]:
            choices = ["All (Quick Match)", "All (Storm League)", "All (Custom Game)"]
            choices += await Map.catalog()

        # Check if multiple Timings have been selected
        else:
            choices = await Map.catalog()

        return [
            choice for choice in choices if input in Misc.alpha_unidecode_lower(choice)
        ]

    @staticmethod
    async def timings(context: discord.AutocompleteContext):
        input = Misc.alpha_unidecode_lower(context.value)

        map = context.options["map"]

        # Check if no Maps have been selected
        if map is None:
            choices = [
                "All Timings",
                "Objective Spawn",
                "Objective Respawn",
                "Objective Timings",
                "Offlane Timings",
                "Lava Wave Timings",
                "Minions Crash",
                "Rotation Time",
            ]

        # Check if all Maps have been selected
        elif "All" in map:
            choices = [
                "Objective Spawn",
                "Objective Respawn",
                "Lava Wave Timings",
                "Minions Crash",
                "Rotation Time",
            ]

        # Check if a single Map has been selected
        else:
            choices = [
                "All Timings",
                "Objective Timings",
                "Offlane Timings",
                "Lava Wave Timings",
                "Minions Crash",
                "Rotation Time",
            ]

        return [
            choice for choice in choices if input in Misc.alpha_unidecode_lower(choice)
        ]
