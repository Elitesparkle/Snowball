import secrets
from unidecode import unidecode

from database import database_connection
from tools.misc import Misc


class Hero:

    @staticmethod
    async def catalog(role: str | None = None) -> list[str]:
        if role == "Offlaner":
            non_bruisers = [
                "Arthas",
                "Blaze",
                "E.T.C.",
                "Illidan",
                "Johanna",
                "Murky",
                "Qhira",
                "Samuro",
                "The Butcher",
                "The Lost Vikings",
                "Valeera",
                "Zeratul",
            ]

            heroes = await Hero.catalog("Bruiser") + non_bruisers
            heroes.sort()
        else:
            query = """
                SELECT Name
                FROM Heroes
                WHERE 1 = 1
            """
            values = ()
            if role is not None:
                query += " AND Role = ?"
                values += (role,)
            query += " ORDER BY Name"
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)
                results = await cursor.fetchall()

            heroes = [hero for result in results for hero in result]

        return heroes

    @staticmethod
    async def random(except_hero: str | None = None) -> str:
        heroes = await Hero.catalog()

        if except_hero:
            heroes.remove(except_hero)

        hero = secrets.choice(heroes)
        return hero

    @staticmethod
    async def get_id(hero_name: str) -> int | None:
        query = """
            SELECT HeroID
            FROM Heroes
            WHERE Name = ?
        """
        values = (hero_name,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        assert results is not None
        try:
            hero_id = int(results[0])
        except TypeError:
            hero_id = None

        return hero_id

    @staticmethod
    async def get_name(hero_id: int) -> str | None:
        query = """
            SELECT Name
            FROM Heroes
            WHERE HeroID = ?
        """
        values = (hero_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        assert results is not None
        return results[0]

    @staticmethod
    async def get_acronym(hero_name: str) -> str:
        query = """
            SELECT Acronym
            FROM Heroes
            WHERE Name = ?
        """
        values = (hero_name,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        assert results is not None
        acronym = results[0]
        return acronym

    @staticmethod
    async def fix_name(hero_name: str) -> str:
        try:
            fix_name = Misc.alpha_unidecode_lower(hero_name)
        except AttributeError:
            fix_name = ""
            return fix_name

        query = """
            SELECT Name
            FROM Heroes
            WHERE Acronym = UPPER(?)
                OR REPLACE(
                    REPLACE(
                        REPLACE(
                            REPLACE(
                                REPLACE(Name, ".", ""),
                            "ú", "u"),
                        "-", ""),
                    "'", ""),
                " ", "") LIKE ?
            ORDER BY
                INSTR(Name, ?),
                Name
        """
        values = (
            fix_name,
            f"%{fix_name}%",
            fix_name,
        )
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        if results is not None:
            fix_name = results[0]
        else:
            fix_name = ""
        return fix_name

    @staticmethod
    def get_code(
        hero_name: str,
        company: str,
    ) -> str | None:
        hero_code = unidecode(hero_name)

        if company is not None:
            if company == "Blizzard":
                hero_code = "".join(
                    filter(
                        str.isalpha,
                        hero_code.replace("Cho", "Cho'Gall").replace(
                            "The Lost Vikings", "Lost Vikings"
                        ),
                    )
                )
            elif company == "Icy Veins":
                hero_code = (
                    hero_code.replace("Kel'Thuzad", "Kel Thuzad")
                    .replace(". ", "-")
                    .replace(".", "-", 2)
                    .replace(".", "")
                    .replace("'", "")
                    .replace(" ", "-")
                )
            elif company == "Psionic Storm":
                hero_code = (
                    hero_code.replace("'", "").replace(".", "").replace(" ", "-")
                )
            hero_code = hero_code.lower()
        else:
            hero_code = None
            print("Company not valid.")

        return hero_code
