import re
import secrets

from database import database_connection
from tools.misc import Misc


class Map:

    @staticmethod
    async def catalog(game_mode: str | None = "Custom Game") -> list[str]:
        query = """
            SELECT Name
            FROM Maps
            WHERE ? = 1
            ORDER BY Name
        """

        if game_mode in [
            "Quick Match",
            "Storm League",
        ]:
            # Replace the placeholder in the query with the name of the selected column.
            query = query.replace("?", game_mode.replace(" ", ""))
        else:
            query = query.replace("WHERE ? = 1", "")

        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
            results = await cursor.fetchall()

        maps = [map for result in results for map in result]
        return maps

    # Convert "S seconds" into "M:SS minutes".
    @staticmethod
    def format_timing(
        timing: str,
        format: str,
    ) -> str:
        if format == "Minutes":
            values_in_seconds = re.findall("[0-9]+", timing)
            values_in_minutes = [
                f"{int(value) // 60}:{(int(value) % 60):02}"
                for value in values_in_seconds
                if int(value) > 2
            ]
            for value_in_seconds, value_in_minutes in zip(
                values_in_seconds, values_in_minutes
            ):
                timing = timing.replace(value_in_seconds, value_in_minutes)
            timing = timing.replace("seconds", "minutes")
        return timing

    @staticmethod
    async def random(game_mode: str | None) -> str:
        maps = await Map.catalog(game_mode)
        map = secrets.choice(maps)
        return map

    @staticmethod
    async def fix_name(map_name: str) -> str | None:
        fixed_name = None
        try:
            fixed_name = Misc.alpha_unidecode_lower(map_name)
        except AttributeError:
            fixed_name = None
            return fixed_name

        query = """
            SELECT Name
            FROM Maps
            WHERE REPLACE(
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
            f"%{fixed_name}%",
            fixed_name,
        )
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        fixed_name = results[0] if results else None
        return fixed_name
