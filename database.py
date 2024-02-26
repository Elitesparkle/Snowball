import asyncio
import json
import os
import re

import aiosqlite  # python -m pip install aiosqlite


class Database:

    @staticmethod
    async def create_heroes() -> None:
        query = """
            CREATE TABLE IF NOT EXISTS Heroes (
                HeroID INTEGER,
                Name TEXT,
                Role TEXT,
                Acronym TEXT,
                PRIMARY KEY (HeroID)
            )
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
        print("Heroes table created.")

    @staticmethod
    async def create_maps() -> None:
        query = """
            CREATE TABLE IF NOT EXISTS Maps (
                MapID INTEGER,
                Name TEXT,
                QuickMatch INTEGER,
                StormLeague INTEGER,
                PRIMARY KEY (MapID)
            )
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
        print("Maps table created.")

    @staticmethod
    async def create_drafts() -> None:
        query = """
            CREATE TABLE IF NOT EXISTS Drafts (
                ChannelID INTEGER,
                MessageID INTEGER,
                Image BLOB,
                Layout TEXT,
                Map TEXT,
                Time INTEGER,
                PRIMARY KEY (ChannelID)
            )"""
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
        print("Drafts table created.")

    @staticmethod
    async def create_teams() -> None:
        query = """
            CREATE TABLE IF NOT EXISTS Teams (
                TeamID INTEGER,
                UserID INTEGER,
                ChannelID INTEGER,
                PRIMARY KEY (TeamID),
                FOREIGN KEY (ChannelID)
                    REFERENCES Drafts (ChannelID)
                        ON DELETE CASCADE
            )
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
        print("Teams table created.")

    @staticmethod
    async def create_selections() -> None:
        query = """
            CREATE TABLE IF NOT EXISTS Selections (
                SelectionID INTEGER,
                ChannelID INTEGER,
                HeroID INTEGER,
                PRIMARY KEY (SelectionID),
                FOREIGN KEY (ChannelID)
                    REFERENCES Drafts (ChannelID)
                        ON DELETE CASCADE,
                FOREIGN KEY (HeroID)
                    REFERENCES Heroes (HeroID)
                        ON DELETE CASCADE
            )
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
        print("Selections table created.")

    @staticmethod
    async def create_tooltips() -> None:
        query = """
            CREATE TABLE IF NOT EXISTS Tooltips (
                TooltipID TEXT,
                Title TEXT,
                Cooldown FLOAT,
                Cost INTEGER,
                Description TEXT,
                Hotkey TEXT,
                Icon TEXT,
                Level INTEGER,
                Resource TEXT,
                Type TEXT,
                Unit TEXT,
                HeroID INTEGER,
                PRIMARY KEY (TooltipID),
                FOREIGN KEY (HeroID)
                    REFERENCES Heroes (HeroID)
                        ON DELETE CASCADE
            )
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
        print("Tooltips table created.")

    @staticmethod
    async def create_keywords() -> None:
        query = """
            CREATE TABLE IF NOT EXISTS Keywords (
                KeywordID INTEGER,
                Name TEXT,
                TooltipID INTEGER,
                PRIMARY KEY (KeywordID),
                FOREIGN KEY (TooltipID)
                    REFERENCES Tooltips (TooltipID)
                        ON DELETE CASCADE
            )
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
        print("Keywords table created.")

    @staticmethod
    async def create_matchups() -> None:
        query = """
            CREATE TABLE IF NOT EXISTS Matchups (
                MatchupID INTEGER,
                UserID TEXT,
                YourHeroID TEXT,
                EnemyHeroID TEXT,
                WinChance INTEGER,
                Time INTEGER,
                Notes TEXT,
                PRIMARY KEY (MatchupID),
                FOREIGN KEY (YourHeroID)
                    REFERENCES Heroes (HeroID)
                        ON DELETE CASCADE,
                FOREIGN KEY (EnemyHeroID)
                    REFERENCES Heroes (HeroID)
                        ON DELETE CASCADE,
                FOREIGN KEY (UserID)
                    REFERENCES Users (UserID)
                        ON DELETE CASCADE
            )
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
        print("Matchups table created.")

    @staticmethod
    async def create_matchup_tips() -> None:
        query = """
            CREATE TABLE IF NOT EXISTS MatchupTips (
                MatchupTipID INTEGER,
                Text TEXT,
                MatchupID INTEGER,
                PRIMARY KEY (MatchupTipID),
                FOREIGN KEY (MatchupID)
                    REFERENCES Matchups (MatchupID)
                        ON DELETE CASCADE
            )
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
        print("Matchup Tips table created.")

    @staticmethod
    async def create_matchup_contributors() -> None:
        query = """
            CREATE TABLE IF NOT EXISTS Users (
                UserID INTEGER,
                Permission INTEGER,
                PRIMARY KEY (UserID)
            )
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
        print("Matchup Contributors table created.")

    @staticmethod
    async def insert_heroes() -> None:
        query = """
            SELECT COUNT(*)
            FROM Heroes
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
            results = await cursor.fetchone()
            assert results is not None
        rows = results[0]

        if rows > 0:
            print("Heroes data present.")
        else:
            for file in os.listdir("./data/heroes/"):
                if file.endswith(".json"):
                    with open(
                        f"./data/heroes/{file}",
                        "r",
                        encoding="utf-8",
                    ) as file:
                        data: dict = json.load(file)

                    assert isinstance(data, dict)
                    id = data.get("id")
                    name = data.get("name")
                    role = data.get("expandedRole")

                    with open(
                        "./data/misc/acronyms.json",
                        "r",
                        encoding="utf-8",
                    ) as file:
                        data = json.load(file)
                    acronym = data.get(name)

                    query = """
                        INSERT INTO Heroes (
                            HeroID,
                            Name,
                            Role,
                            Acronym
                        )
                        VALUES (?, ?, ?, ?)
                    """
                    values = (
                        id,
                        name,
                        role,
                        acronym,
                    )
                    async with database_connection.cursor() as cursor:
                        await cursor.execute(query, values)

            await database_connection.commit()
            print("Heroes data added.")

    @staticmethod
    def fix_description(
        description: str,
        hero: str,
        title: str,
    ) -> str:
        # To customize tooltips.
        with open(
            f"./data/misc/corrections.json",
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        try:
            corrections = data[hero][title]
        except KeyError:
            # No corrections needed according to the data.
            ...
        else:
            for correction in corrections:
                if correction[0] is None:
                    # Append a string to the description.
                    description += correction[1]
                elif correction[1] is None:
                    # Prepend a string to the description.
                    description = correction[0] + description
                elif correction[0] == "":
                    # Create a new description.
                    description = correction[1]
                else:
                    # Remove a substring from the description.
                    description = description.replace(correction[0], correction[1])

        # To split the text into paragraphs.
        labels = [
            "Dragonqueen: Breath of Life",
            "Dragonqueen: Preservation",
            "Dragonqueen: Wing Buffet",
            "Breath of Fire",
            "Keg Smash",
            "Destroyer: Incinerate",
            "World Breaker: Lava Burst",
            "Destroyer: Onslaught",
            "World Breaker: Earth Shatter",
            "Worgen: Razor Swipe",
            "Worgen: Disengage",
            "Human: Gilnean Cocktail",
            "Human: Darkflight",
            "Molten Core: Molten Swing",
            "Molten Core: Meteor Shower",
            "Molten Core: Explosive Rune",
            "Unstealth: Sinister Strike",
            "Stealth: Ambush",
            "Unstealth: Blade Flurry",
            "Stealth: Cheap Shot",
            "Unstealth: Eviscerate",
            "Stealth: Garrote",
            "Medivac Dropship",
            "Reinforcements",
        ]
        for label in labels:
            label = f"  {label} "
            description = description.replace(label, f"{label} ")

        # To fix inconsistencies.
        old_strings = [
            "   ",
            "Repeatable Quest:",
            "  Unlimited range.",
            "After reaching level",
            "After reaching Level",
        ]
        new_strings = [
            "  ",
            "Quest:",
            " Unilimited range.",
            "After reaching Level",
            "Quest: After reaching Level",
        ]
        for old_string, new_string in zip(old_strings, new_strings):
            description = description.replace(old_string, new_string)

        # To split paragraphs near keywords.
        keywords = ["Active", "Passive", "Quest", "Reward"]
        for keyword in keywords:
            description = description.replace(f". {keyword}:", f".  {keyword}:")

        # To remove leading and trailing space or new line characters.
        description = description.strip(" \n")

        # To add a period at the end when missing.
        if not (description.endswith(".") or description.endswith("!")):
            description += "."

        return description

    @staticmethod
    async def update_tooltips_and_keywords():
        resources = {
            "Chen": "Brew",
            "Deathwing": "Energy",
            "Lt. Morales": "Energy",
            "Sonya": "Fury",
            "Valeera": "Energy",
            "Zarya": "Energy",
        }

        query = "DELETE FROM Tooltips"
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)

        query = "DELETE FROM Keywords"
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)

        for file in os.listdir("./data/heroes/"):
            if not file.endswith(".json"):
                continue

            with open(
                f"./data/heroes/{file}",
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            hero_id = int(data.get("id"))
            hero_code = data.get("hyperlinkId")
            hero = data.get("name")

            # Abilities
            for unit in data["abilities"]:
                for ability in data["abilities"][unit]:
                    is_new = True
                    level = None

                    code = ability.get("abilityId")
                    if code in [
                        "Alexstrasza|R4",
                        "LostVikings|Q1",
                        "LostVikings|Q2",
                        "LostVikings|W1",
                        "LostVikings|W2",
                        "LostVikings|E1",
                        "Ragnaros|R3",
                    ]:
                        continue

                    name = ability.get("name")

                    try:
                        cooldown = float(ability.get("cooldown"))
                    except TypeError:
                        cooldown = None

                    description = ability.get("description")
                    description = Database.fix_description(description, hero, name)

                    hotkey = ability.get("hotkey")

                    if name == "Nordic Attack Squad":
                        hotkey = None

                    icon = ability.get("icon")

                    try:
                        cost = float(ability.get("manaCost"))
                        resource = (
                            resources.get(hero) if hero in list(resources) else "Mana"
                        )
                    except TypeError:
                        cost = None
                        resource = None

                    if code == "Guldan|D1":
                        cost = 222
                        resource = "Health"
                    elif code == "Gazlowe|Q1":
                        resource = "Scrap"
                    elif code == "Samuro|21":
                        icon = "storm_ui_ingame_heroselect_btn_samuro.png"
                    elif code == "LostVikings|41":
                        name = "Select All"
                        description = "Issue orders to Olaf, Baleog, and Erik."
                    elif code == "LtMorales|Q1":
                        cooldown = 1
                    elif code == "Stitches|D1":
                        description = description.replace(
                            "Vile Gas Hitting", "Vile Gas  Hitting"
                        )

                    type = ability.get("type").capitalize()
                    if type == "Heroic":
                        for tier in [4, 10]:
                            for talent in data["talents"][str(tier)]:
                                title = talent.get("name")
                                if name == title:
                                    is_new = False
                                    continue
                    elif type == "Activable":
                        type = "Active"
                    elif type == "Subunit":
                        type = "Special"
                    elif type == "Trait" and "Activate to" in description:
                        hotkey = "D"

                    if is_new:
                        query = """
                            INSERT INTO Tooltips (
                                TooltipID,
                                Title,
                                Cooldown,
                                Cost,
                                Description,
                                Hotkey,
                                Icon,
                                Level,
                                Resource,
                                Type,
                                Unit,
                                HeroID
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        values = (
                            code,
                            name,
                            cooldown,
                            cost,
                            description,
                            hotkey,
                            icon,
                            level,
                            resource,
                            type,
                            unit,
                            hero_id,
                        )
                        async with database_connection.cursor() as cursor:
                            await cursor.execute(query, values)
                        await Database.insert_keyword(code, description)

            # Missing from data, being added manually.
            if hero == "Samuro":
                code = "Samuro|D1"
                name = "Image Transmission"
                cooldown = 14
                cost = None
                description = "Activate to switch places with a target Mirror Image, removing most negative effects from Samuro and the Mirror Image.  Advancing Strikes  Basic Attacks against enemy Heroes increase Samuro's Movement Speed by 25% for 2 seconds."
                hotkey = "D"
                icon = "storm_ui_icon_samuro_flowingstrikes.png"
                type = "Trait"
                unit = "Samuro"
                hero_id = 58

                query = """
                    INSERT OR REPLACE INTO Tooltips (
                        TooltipID,
                        Title,
                        Cooldown,
                        Cost,
                        Description,
                        Hotkey,
                        Icon,
                        Level,
                        Resource,
                        Type,
                        Unit,
                        HeroID
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                values = (
                    code,
                    name,
                    cooldown,
                    cost,
                    description,
                    hotkey,
                    icon,
                    level,
                    resource,
                    type,
                    unit,
                    hero_id,
                )
                async with database_connection.cursor() as cursor:
                    await cursor.execute(query, values)
                await Database.insert_keyword(code, description)

            # Talents
            for level in [1, 4, 7, 10, 13, 16, 20]:
                for talent in data["talents"][str(level)]:
                    cost = None
                    cooldown = None
                    unit = None
                    resource = None

                    # Replace generic terms to handle Talents with the same ID across different Heroes.
                    assert isinstance(talent, dict)
                    talent_id = talent.get("tooltipId")

                    assert talent_id is not None and isinstance(talent_id, str)
                    code = talent_id.replace("Generic", hero_code).replace(
                        "Nexus", f"{hero_code}Nexus"
                    )
                    name = talent.get("name")
                    assert name is not None

                    description = talent.get("description")
                    assert description is not None

                    if level == 20 and code in [
                        "AlarakCounterStrike2ndHeroic",
                        "AlarakDeadlyCharge",
                    ]:
                        if name == "Deadly Charge":
                            code += "2ndHeroic"
                            description += (
                                " This ability will take over Alarak's Trait button."
                            )

                        for ability in data["abilities"]["Alarak"]:
                            assert isinstance(ability, dict)

                            title = ability.get("name")
                            if name == title:
                                cost = ability.get("manaCost")
                                if cost is not None:
                                    cost = float(cost)
                                    resource = (
                                        resources.get(hero)
                                        if hero in list(resources)
                                        else "Mana"
                                    )

                    description = Database.fix_description(description, hero, name)

                    try:
                        cooldown = talent.get("cooldown")
                        assert cooldown is not None
                        cooldown = float(cooldown)
                    except TypeError:
                        expressions = [
                            r"This effect has a(.+?)second cooldown.",
                            r"This effect can only happen once every(.+?)seconds.",
                            r"This can only occur every(.+?)seconds.",
                            r"Can only trigger once every(.+?)seconds.",
                            r"Every(.+?)seconds, ",
                            r"Additionally, every(.+?)seconds, ",
                            r"Can only occur once every(.+?)seconds",
                            r"every(.+?)seconds.",
                        ]
                        for expression in expressions:
                            if match := re.search(expression, description):
                                try:
                                    cooldown = float(match.group(1))

                                    # To ignore periodic effects that match some expressions.
                                    if cooldown < 5 or name in [
                                        "Evolutionary Link",
                                        "Fortified Bunker",
                                    ]:
                                        cooldown = None

                                    break
                                except ValueError:
                                    cooldown = None
                            else:
                                cooldown = None

                    type = talent.get("type")
                    assert isinstance(type, str)
                    type = type.capitalize()

                    hotkey = talent.get("hotkey")

                    if level in [4, 10]:
                        if type == "Heroic" and hero not in [
                            "Deathwing",
                            "Tracer",
                        ]:
                            hotkey = "R"
                            for ability in data["abilities"][hero_code]:
                                assert isinstance(ability, dict)

                                title = ability.get("name")
                                if name == title:
                                    cost = ability.get("manaCost")
                                    if cost is not None:
                                        cost = float(cost)
                                        resource = (
                                            resources.get(hero)
                                            if hero in list(resources)
                                            else "Mana"
                                        )

                    if hotkey is None:
                        if hero == "The Lost Vikings":
                            if name in [
                                "Spin To Win!",
                                "Norse Force!",
                            ]:
                                hotkey = "Q"
                            elif name == "Jump!":
                                hotkey = "W"
                            elif name == "Viking Bribery":
                                hotkey = "E"
                        elif hero == "Tassadar":
                            if name == "Oracle":
                                hotkey = "D"
                                type = "Trait"

                        trait_tests = [
                            "Activate",
                            "Cancel",
                            "can be activated to",
                            "Stop channeling",
                            "can activate",
                        ]

                        active_tests = [
                            "Can be toggled",
                            "can activate",
                            "Activate to",
                        ]

                        if name == "Rite of Rak'Shir":
                            hotkey = "1"
                            type = "Active"
                        elif name == "Seasoned Soldier":
                            hotkey = None
                            type = "Passive"
                        elif name == "Legion of Beetles":
                            hotkey = "1"
                            type = "Active"
                        elif type == "Trait" and any(
                            string in description for string in trait_tests
                        ):
                            hotkey = "D"
                        elif (type == "Active" and name != "Amani Hide") or any(
                            string in description for string in active_tests
                        ):
                            hotkey = "1"
                    else:
                        if hero == "The Lost Vikings":
                            if name == "Nordic Attack Squad":
                                hotkey = None

                    icon = talent.get("icon")

                    query = """
                        INSERT OR REPLACE INTO Tooltips (
                            TooltipID,
                            Title,
                            Cooldown,
                            Cost,
                            Description,
                            Hotkey,
                            Icon,
                            Level,
                            Resource,
                            Type,
                            Unit,
                            HeroID
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    values = (
                        code,
                        name,
                        cooldown,
                        cost,
                        description,
                        hotkey,
                        icon,
                        level,
                        resource,
                        type,
                        unit,
                        hero_id,
                    )
                    async with database_connection.cursor() as cursor:
                        await cursor.execute(query, values)

                    await Database.insert_keyword(code, description)

        await database_connection.commit()
        print("Tooltips data updated.")

    # To change Keywords, update the list in the Search cog too.
    @staticmethod
    async def insert_keyword(
        code: str,
        description: str,
    ) -> None:
        keywords = []

        if "Armor" in description:
            match = re.search("lose(.+?)Armor", description)
            if match is not None:
                match = match.group(1)
                flag = len(match) < 6
            else:
                flag = False
                if "0 Armor" in description or "5 Armor" in description:
                    keywords.append("Armor")

            checks = [
                "Armor reduc",
                "Armor is reduced",
                "lowers a Hero's Armor",
                "lowers enemy Hero Armor",
                "lowering their Armor",
                "reduce their Armor",
                "reduces their Armor",
                "reduce the Armor",
                "reduces the Armor",
                "reduces the target's Armor",
                "reducing their Armor",
                "their Armor lowered",
            ]
            if any(string in description for string in checks) or flag:
                keywords.append("Armor Reduction")

            if "Physical Armor" in description:
                if "0 Physical A" in description or "5 Physical A" in description:
                    keywords.append("Physical Armor")

                checks = [
                    "decrease the Physical A",
                    "reduce their Physical A",
                    "reduces Physical A",
                ]
                if any(string in description for string in checks):
                    keywords.append("Physical Armor Reduction")

                if "Physical Armor against" in description:
                    keywords.append("Block")

            if "Spell Armor" in description:
                if "0 Spell A" in description or "5 Spell A" in description:
                    keywords.append("Spell Armor")

                if "toggled to allow" in description:
                    keywords.append("Spell Shield")

                checks = [
                    "reduces their Spell A",
                    "their Spell Armor reduced",
                ]
                if any(string in description for string in checks):
                    keywords.append("Spell Armor Reduction")

        checks = [
            "allied Heroes are Unstoppable",
            "allies below Johanna are Unstoppable",
            "them Unstoppable",
            "ally Unstoppable",
            "allies Unstoppable",
            "both gain Unstoppable",
            "removes Roots",
            "removes Stuns",
            "remove all Stuns",
            "remove all damage over time and disabling effects",
            "remove all disabling effects",
            "remove all Slows",
            "removes all Slows",
        ]
        if (
            any(string in description for string in checks)
            and code != "BarbarianHurricaneWhirlwindTalent"
        ):
            keywords.append("Cleanse")

        checks = [
            "reduce heal",
            "reducing all healing received",
            "reduce the healing received",
            "reduce their healing received",
            "reduce enemy healing received",
            "reduces healing received",
            "reduced heal",
            "less healing",
        ]
        if any(string in description for string in checks):
            keywords.append("Healing Reduction")

        for keyword in keywords:
            query = """
                INSERT INTO Keywords (
                    TooltipID,
                    Name
                )
                VALUES (?, ?)
            """
            values = (
                code,
                keyword,
            )
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)

    async def insert_maps(self) -> None:
        query = """
            SELECT COUNT(*)
            FROM Maps
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
            results = await cursor.fetchone()
            assert results is not None
        rows = results[0]

        if rows > 0:
            print("Maps data present.")
        else:
            maps = [
                "Alterac Pass",
                "Battlefield of Eternity",
                "Blackheart's Bay",
                "Braxis Holdout",
                "Cursed Hollow",
                "Dragon Shire",
                "Garden of Terror",
                "Hanamura Temple",
                "Haunted Mines",
                "Infernal Shrines",
                "Sky Temple",
                "Tomb of the Spider Queen",
                "Towers of Doom",
                "Volskaya Foundry",
                "Warhead Junction",
            ]

            quick_match_bans = [
                "Haunted Mines",
            ]

            storm_league_bans = [
                "Blackheart's Bay",
                "Haunted Mines",
                "Volskaya Foundry",
            ]

            for map in maps:
                quick_match = map not in quick_match_bans
                storm_league = map not in storm_league_bans

                query = """
                    INSERT INTO Maps (
                        Name,
                        QuickMatch,
                        StormLeague
                    )
                    VALUES (?, ?, ?)
                """
                values = (
                    map,
                    quick_match,
                    storm_league,
                )
                async with database_connection.cursor() as cursor:
                    await cursor.execute(query, values)

            await database_connection.commit()
            print("Maps data added.")

    async def load_database(self) -> None:
        print("Database loading...")

        query = "PRAGMA foreign_keys = ON;"
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)

        if not is_file:
            await self.create_heroes()
            await self.insert_heroes()

            await self.create_tooltips()
            await self.create_keywords()
            await self.update_tooltips_and_keywords()

            await self.create_maps()
            await self.insert_maps()

            await self.create_drafts()
            await self.create_teams()
            await self.create_selections()

            await self.create_matchups()
            await self.create_matchup_contributors()
            await self.create_matchup_tips()

        print("Database ready.")


async def main() -> None:
    path = "./main.db"

    # Check if the database exists and store the value for later usage.
    global is_file
    is_file = os.path.isfile(path)

    # Connect to the database.
    global database_connection
    database_connection = await aiosqlite.connect(path)

    # Create tables and insert data into the database.
    database = Database()

    # Load the database.
    await database.load_database()


if __name__ == "__main__":
    asyncio.run(main())
