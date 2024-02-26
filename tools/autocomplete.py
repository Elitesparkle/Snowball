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

        guide_types = [
            "Gameplay",
            "Map",
            "Reddit",
            "Tier List",
            "Tips of the Storm",
        ]

        return [
            guide_type
            for guide_type in guide_types
            if input in Misc.alpha_unidecode_lower(guide_type)
        ]

    @staticmethod
    async def guides(context: discord.AutocompleteContext):
        input = Misc.alpha_unidecode_lower(context.value)

        category = context.options["category"]

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

        map_tierlists = [f"{map} Tier List" for map in await Map.catalog()]
        tierlists = global_tierlists + map_tierlists

        with open("data/misc/tips-of-the-storm.json", "r", encoding="utf-8") as file:
            external_tips = json.load(file)
        tips = list(external_tips.keys())

        if category == "Gameplay":
            guides = gameplay_guides
        elif category == "Map":
            guides = map_guides
        elif category == "Tier List":
            guides = tierlists
        elif category == "Tips of the Storm":
            guides = tips
        elif category == "Reddit":
            guides = reddit_guides
        else:
            guides = gameplay_guides + map_guides + tierlists + tips
        guides.sort()

        return [guide for guide in guides if input in Misc.alpha_unidecode_lower(guide)]

    @staticmethod
    async def available_matchups(
        field: str | None = None,
        hero: str | None = None,
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
                query = query.replace("Matchups.YourHeroID", "Matchups.EnemyHeroID")
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
                query = query.replace("Matchups.YourHeroID", "Matchups.EnemyHeroID")
                query = query.replace("HAVING EnemyHeroID", "HAVING YourHeroID")
            values = (hero,)
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)
                results = await cursor.fetchall()

        try:
            matchups, _ = zip(*results)
        except ValueError:
            matchups = []
        else:
            matchups = list(matchups)

        return matchups

    @staticmethod
    async def heroes(context: discord.AutocompleteContext) -> list[str]:
        input = Misc.alpha_unidecode_lower(context.value)

        command_name = context.command.qualified_name
        if command_name.startswith("matchup"):
            if command_name == "matchup list":
                heroes = await Autocomplete.available_matchups()
            elif command_name == "matchup tips":
                if context.focused.name == "your_hero":
                    enemy_hero = context.options["enemy_hero"]

                    heroes = await Autocomplete.available_matchups(
                        field="your_hero", hero=enemy_hero
                    )

                    # Remove the selected Hero from choices.
                    if enemy_hero in heroes:
                        heroes.remove(enemy_hero)
                elif context.focused.name == "enemy_hero":
                    your_hero = context.options["your_hero"]

                    heroes = await Autocomplete.available_matchups(
                        field="enemy_hero", hero=your_hero
                    )

                    # Remove the selected Hero from choices.
                    if your_hero in heroes:
                        heroes.remove(your_hero)
                else:
                    raise MatchupsException
            else:
                your_hero = context.options["your_hero"]
                enemy_hero = context.options["enemy_hero"]

                heroes = await Hero.catalog("Offlaner")

                # Remove the selected Hero from choices.
                if your_hero in heroes:
                    heroes.remove(your_hero)

                # Remove the selected Hero from choices.
                if enemy_hero in heroes:
                    heroes.remove(enemy_hero)
        else:
            heroes = await Hero.catalog()

        return [
            hero
            for hero in heroes
            if input in Misc.alpha_unidecode_lower(hero)
            or input.upper() == await Hero.get_acronym(hero)
        ]

    @staticmethod
    async def maps(context: discord.AutocompleteContext):
        input = Misc.alpha_unidecode_lower(context.value)

        # Check if multiple Timings have been selected.
        timing = context.options["timing"]
        if timing in [
            "All Timings",
            "Objective Timings",
            "Offlane Timings",
        ]:
            maps = await Map.catalog()

        # Check if a single Timing has been selected.
        else:
            maps = [
                "All (Quick Match)",
                "All (Storm League)",
                "All (Custom Game)",
            ]
            maps += await Map.catalog()

        return [map for map in maps if input in Misc.alpha_unidecode_lower(map)]

    @staticmethod
    async def timings(context: discord.AutocompleteContext):
        input = Misc.alpha_unidecode_lower(context.value)

        # Check if no Maps have been selected.
        map = context.options["map"]
        if map is None:
            map_timings = [
                "All Timings",
                "Objective Spawn",
                "Objective Respawn",
                "Objective Timings",
                "Offlane Timings",
                "Lava Wave Timings",
                "Minions Crash",
                "Rotation Time",
            ]

        # Check if all Maps have been selected.
        elif "All" in map:
            map_timings = [
                "Objective Spawn",
                "Objective Respawn",
                "Lava Wave Timings",
                "Minions Crash",
                "Rotation Time",
            ]

        # Check if a single Map has been selected.
        else:
            map_timings = [
                "All Timings",
                "Objective Timings",
                "Offlane Timings",
                "Lava Wave Timings",
                "Minions Crash",
                "Rotation Time",
            ]

        return [
            map_timing
            for map_timing in map_timings
            if input in Misc.alpha_unidecode_lower(map_timing)
        ]
