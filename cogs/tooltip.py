import asyncio
import re

import discord
from discord import option
from discord.ext import commands
from unidecode import unidecode

from database import database_connection
from main import MyBot
from tools.autocomplete import Autocomplete
from tools.hero import Hero
from tools.misc import Misc


class Tooltip(commands.Cog):

    busy_channels = []
    stop_searching = []

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Tooltip extension loaded.")

    @staticmethod
    def format_description(
        description: str,
        hero: str,
        name: str,
    ) -> str:
        # https://qwerty.dev/whitespace/
        quest_icon = " !"
        reward_icon = "?"

        # Align icons.
        quest_icon = "\N{HAIR SPACE}" + quest_icon + "\N{HAIR SPACE}"

        # Format exceptions.
        if hero == "Alexstrasza":
            description = description.replace(
                "Dragonqueen: Cast", "**Dragonqueen:** Cast"
            )
            description = description.replace(
                "Dragonqueen: Range", "**Dragonqueen:** Range"
            )
        if hero == "Deathwing":
            if name == "Form Switch":
                description = description.replace(
                    "Incinerate", "**Destroyer:** Incinerate"
                )
                description = description.replace(
                    "Lava Burst", "**World Breaker:** Lava Burst"
                )
            elif name in ["Dragon Soul", "Heat Wave", "Ruination"]:
                description = description.replace("Destroyer:", "**Destroyer:**")
                description = description.replace(
                    "World Breaker:", "**World Breaker:**"
                )
        elif hero == "D.Va":
            description = description.replace("Mech Mode:", "**Mech Mode:**")
            description = description.replace("Pilot Mode:", "**Pilot Mode:**")
        elif hero == "Greymane":
            if name == "Curse of the Worgen":
                description = description.replace("While Human,", "**Human:**")
                description = description.replace("While Worgen,", "**Worgen:**")
        elif hero == "Ragnaros":
            description = description.replace(
                "Molten Core: Range", "**Molten Core:** Range"
            )
        elif hero == "Sgt. Hammer":
            description = description.replace("Siege Mode:", "**Siege Mode:**")

        # Highlight keywords and add icons.
        description = description.replace("Gambit:", "**Gambit:**")
        description = description.replace("Quest:", f"**{quest_icon} Quest:**")
        description = description.replace("Reward:", f"**{reward_icon} Reward:**")
        description = description.replace("Active:", "**Active:**")
        description = description.replace("Passive:", "**Passive:**")
        description = description.replace("Vector Targeting ", "**Vector Targeting**  ")

        # Aeparate paragraphs.
        description = description.replace("  ", "\n")

        # Make bold a title having a new line character at the end, even with [hotkey] at the end.
        pattern = r"(?m)(?<=\n^)([^\*\s]\w+.+\w+)(\s\[\w+\])?$"
        description = re.sub(pattern, r"__**\g<1>**__\g<2>", description)

        return description

    hotkeys = [
        "Q",
        "W",
        "E",
        "R",
        "D",
        "Z",
        "1",
    ]
    levels = [
        0,
        1,
        4,
        7,
        10,
        13,
        16,
        20,
    ]

    # Warning! To change Keywords, update the function in the Database cog too.
    keywords = [
        "Cleanse",
        "Block",
        "Spell Shield",
        "Armor",
        "Armor Reduction",
        "Physical Armor",
        "Physical Armor Reduction",
        "Spell Armor",
        "Spell Armor Reduction",
        "Healing Reduction",
    ]

    resources = [
        "Brew",
        "Energy",
        "Fury",
        "Mana",
        "Scrap",
    ]

    slots = [
        "Active",
        "Basic",
        "Heroic",
        "Mount",
        "Passive",
        "Trait",
        "Q Talent",
        "W Talent",
        "E Talent",
        "Z Talent",
    ]

    @commands.slash_command(
        name="tooltip",
        description="Search for tooltips or cancel the current search.",
    )
    @option(
        "amount",
        description="Select the maximum amount of tooltips to print in chat.",
        min_value=1,
        default=None,
    )
    @option(
        "cooldown",
        description="Insert a cooldown value.",
        default=None,
    )
    @option(
        "cost",
        description="Insert a cost value.",
        min_value=0,
        max_value=222,
        default=None,
    )
    @option(
        "description",
        description="Insert part of the description of a tooltip.",
        default=None,
    )
    @option(
        "hero",
        description="Select a Hero.",
        autocomplete=Autocomplete.heroes,
        default=None,
    )
    @option(
        "hotkey",
        description="Select an hotkey.",
        default=None,
        choices=hotkeys,
    )
    @option(
        "keyword",
        description="Select a keyword.",
        default=None,
        choices=keywords,
    )
    @option(
        "level",
        description="Select a level.",
        default=None,
        choices=levels,
    )
    @option(
        "resource",
        description="Select a resource.",
        default=None,
        choices=resources,
    )
    @option(
        "slot",
        description="Select a slot.",
        default=None,
        choices=slots,
    )
    @option(
        "title",
        description="Insert the name of an Ability or Talent, or part of it.",
        default=None,
    )
    async def tooltip(
        self,
        context: discord.ApplicationContext,
        amount: int,
        cooldown: int,
        cost: int,
        description: str,
        hero: str,
        hotkey: str,
        keyword: str,
        level: int,
        resource: str,
        slot: str,
        title: str,
    ) -> None:
        if context.channel_id in self.busy_channels:
            self.stop_searching.append(context.channel_id)

            # Add delay to avoid having tooltips after the abort message.
            await asyncio.sleep(1)

            event = "Search aborted."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            self.busy_channels.remove(context.channel_id)
        else:
            query = """
                SELECT Tooltips.TooltipID,
                    Title,
                    Cooldown,
                    Cost,
                    Description,
                    Hotkey,
                    Icon,
                    Level,
                    Resource,
                    Slot,
                    Unit,
                    (
                        SELECT Name
                        FROM Heroes
                        WHERE Heroes.HeroID = Tooltips.HeroID
                    ) AS Hero
                FROM Tooltips
                LEFT JOIN Keywords USING (TooltipID)
                WHERE 1 = 1
            """
            values = ()

            if cooldown is not None:
                if cooldown < 1:
                    query += " AND Tooltips.Cooldown IS NULL"
                else:
                    query += " AND Tooltips.Cooldown = ?"
                    values += (cooldown,)

            if cost is not None:
                if cost < 1:
                    query += " AND Tooltips.Cost IS NULL"
                else:
                    query += " AND Tooltips.Cost = ?"
                    values += (cost,)

            if description is not None:
                description = unidecode(description)

                query += " AND Tooltips.Description LIKE ?"
                values += (f"%{description}%",)

            if hero is not None:
                hero = await Hero.fix_name(hero)

                query += " AND Hero = ?"
                values += (hero,)

            if hotkey is not None:
                query += " AND Tooltips.Hotkey = ?"
                values += (hotkey,)

            if keyword is not None:
                query += " AND Keywords.Name = ?"
                values += (keyword,)

            if level is not None:
                if level < 1:
                    query += " AND Tooltips.Level IS NULL"
                else:
                    query += " AND Tooltips.Level = ?"
                    values += (level,)

            if resource is not None:
                query += " AND Tooltips.Resource = ?"
                values += (resource,)

            if slot is not None:
                slot = slot.replace(" Talent", "")

                query += " AND Tooltips.Slot = ?"
                values += (slot,)

            if title is not None:
                title = unidecode(title)

                query += " AND Tooltips.Title LIKE ?"
                values += (f"%{title}%",)

            # Remove duplicates and fix order.
            query += """
                GROUP BY Tooltips.TooltipID
                ORDER BY Tooltips.rowid
            """

            if not "AND" in query:
                event = "Invalid input."
                content = f"{event} Select at least one option besides `amount`."

                await context.respond(content, ephemeral=True)
                Misc.send_log(context, event)

                return

            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)
                results = await cursor.fetchall()
            results = list(results)

            if context.channel_id in self.busy_channels:
                event = "Another search going on."
                content = "Another search going on in this channel. Use `/search quit` to abort it."

                await context.respond(content, ephemeral=True)
                Misc.send_log(context, event)

                return

            self.busy_channels.append(context.channel_id)

            event = "Search started."
            Misc.send_log(context, event)

            tooltips = []
            total = 0
            followup = False
            interrupted = False

            for index, result in enumerate(results):
                if context.channel_id in self.stop_searching:
                    self.stop_searching.remove(context.channel_id)
                    return

                if index == amount:
                    interrupted = True
                    break

                (
                    _,
                    name,
                    cooldown,
                    cost,
                    description,
                    hotkey,
                    icon,
                    level,
                    resource,
                    slot,
                    unit,
                    hero,
                ) = result

                rows = []
                total += 1

                emote_name = Hero.get_code(hero, "Snowball")
                emote_id = await Hero.get_emote_id(hero)
                emote = f"<:{emote_name}:{emote_id}>"

                # Abilities
                if level is None:
                    form = await Hero.fix_name(unit)
                    subcategory = "Baseline" if form == hero else "Special"
                    rows.append(f"{emote} {hero} ‒ {subcategory}")

                # Talents
                else:
                    if hero == "Chromie" and level > 3:
                        level -= 2
                    rows.append(f"{emote} {hero} ‒ Level {level}")

                if hotkey is None:
                    rows.append(f"**__{name}__**")
                else:
                    rows.append(f"**__{name}__** [{hotkey}]")

                if cost is not None:
                    if name == "Life Tap":
                        resource = "(+4% per level) " + resource

                    if cost != 1 and resource == "Scrap":
                        resource += "s"

                    rows.append(f"**Cost:** {cost} {resource}")

                if cooldown is not None:
                    label = "second"
                    if cooldown != 1:
                        label += "s"

                    rows.append(f"**Cooldown:** {cooldown:g} {label}")

                description = Tooltip.format_description(description, hero, name)
                rows.append(description)

                embed = discord.Embed(
                    color=discord.Color.blue(),
                    description="\n".join(rows),
                )

                # Link to images in the public repository.
                thumbnail_url = f"https://raw.githubusercontent.com/Elitesparkle/Snowball/main/images/talents/{icon}"
                embed.set_thumbnail(url=thumbnail_url)
                tooltips.append(embed)

                if (
                    len(tooltips) == 10
                    or index == len(results) - 1
                    or (amount and index == amount - 1)
                ):
                    await context.respond(embeds=tooltips)
                    followup = True if not followup else False
                    tooltips = []

                    if index < len(results) - 1:
                        # Add dynamic delay to work around Discord API limitations.
                        await asyncio.sleep(index * 0.1 * len(self.busy_channels))

            event = "Search completed."
            content = f"{context.author.mention}, search completed."

            if not interrupted:
                total_label = "tooltip" if total == 1 else "tooltips"
                content += f"\nA total of {total} {total_label} has been found."
            else:
                amount_label = "tooltip" if amount == 1 else "tooltips"
                content += (
                    f"\nDue to the search being limited at {amount} {amount_label}, some are missing."
                    "\nTo see more results, set a custom value for the `amount` field."
                )

            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            self.busy_channels.remove(context.channel_id)


def setup(bot: MyBot) -> None:
    bot.add_cog(Tooltip(bot))
