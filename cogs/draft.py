import asyncio
import base64
import os
import secrets
import time

import discord
from discord import option
from discord.ext import commands, tasks
from PIL import Image, ImageEnhance  # py -m pip install --upgrade Pillow

from config import draft_settings
from database import database_connection
from main import MyBot
from tools.hero import Hero
from tools.autocomplete import Autocomplete
from tools.map import Map
from tools.misc import Misc


class Draft(commands.Cog):

    draft = discord.SlashCommandGroup(
        name="draft",
        description="Draft simulation.",
    )

    # Channels that are currently busy executing another draft command.
    busy_channels = []

    # Values used to check whose turn is while drafting.
    turns = [
        0,
        1,
        0,
        1,
        0,
        1,
        1,
        0,
        0,
        1,
        0,
        1,
        1,
        0,
        0,
        1,
    ]

    # Values used to check when it's turn to ban.
    next_bans = [
        0,
        1,
        2,
        3,
        4,
        10,
        11,
    ]
    previous_bans = [
        0,
        1,
        2,
        3,
        9,
        10,
    ]

    # Coordinates used for placing Heroes in draft slots.
    layouts = {
        "Horizontal": [
            (120, 50),
            (120, 520),
            (260, 50),
            (260, 520),
            (50, 190),
            (50, 380),
            (190, 380),
            (190, 190),
            (330, 190),
            (540, 520),
            (540, 50),
            (330, 380),
            (470, 380),
            (470, 190),
            (610, 190),
            (610, 380),
        ],
        "Vertical": [
            (120, 50),
            (450, 50),
            (120, 190),
            (450, 190),
            (120, 330),
            (380, 330),
            (520, 330),
            (50, 470),
            (190, 470),
            (450, 470),
            (120, 610),
            (380, 610),
            (520, 610),
            (50, 750),
            (190, 750),
            (450, 750),
        ],
    }

    countdowns = [40, 24]  # Countdowns for first ban and other turns.

    # Size values for Hero portraits.
    portrait_size = (90, 90)

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot
        self.expiration.start()

    def cog_unload(self) -> None:
        self.expiration.cancel()

    @staticmethod
    def is_ready(channel_id: int | None) -> bool:
        if channel_id in Draft.busy_channels:
            Draft.ready_up(channel_id)
            ready = False
        else:
            Draft.busy_channels.append(channel_id)
            ready = True
        return ready

    @staticmethod
    def ready_up(channel_id: int | None) -> None:
        try:
            Draft.busy_channels.remove(channel_id)
        except ValueError:
            event = f"Channel {channel_id} already available."
            print(event)

    @staticmethod
    async def get_drafting_players(
        bot: MyBot,
        channel_id: int | None,
    ) -> list[discord.User]:
        query = """
            SELECT UserID
            FROM Teams
            WHERE ChannelID = ?
        """
        values = (channel_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchall()

        drafting_players = [
            await bot.fetch_user(drafting_player)
            for result in results
            for drafting_player in result
        ]
        return drafting_players

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.add_view(self.CoinView(self.bot))
        print("Draft extension loaded.")

    class CoinView(discord.ui.View):
        def __init__(
            self,
            bot: MyBot,
        ) -> None:
            self.bot: MyBot = bot
            super().__init__(timeout=None)

        @discord.ui.button(
            label="First Pick",
            custom_id="Draft¦Pick",
            style=discord.ButtonStyle.blurple,
        )
        async def first_pick(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            await self.on_interaction(button, interaction)

        @discord.ui.button(
            label="Map Choice",
            custom_id="Draft¦Map",
            style=discord.ButtonStyle.blurple,
        )
        async def map_choice(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            await self.on_interaction(button, interaction)

        @discord.ui.button(
            label="Ask Opponent",
            custom_id="Draft¦Ask",
            style=discord.ButtonStyle.blurple,
        )
        async def ask_opponent(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            button.disabled = True
            await self.on_interaction(button, interaction)

        async def on_interaction(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            channel_id = interaction.channel_id
            button_id = str(button.custom_id)
            response = interaction.response
            players = await Draft.get_drafting_players(self.bot, channel_id)

            try:
                your_turn = interaction.user == players[0]
            except IndexError:
                command = self.bot.get_application_command("draft start")
                assert command is not None and isinstance(command, discord.SlashCommand)

                event = "Draft corrupted."
                content = f"{event} Use {command.mention} to begin a new draft."

                await response.send_message(content, ephemeral=True)
                Misc.send_log(interaction, event)

                Draft.ready_up(interaction.channel_id)
                return

            assert interaction.user is not None
            is_owner = await self.bot.my_is_owner(interaction.user.id)
            if your_turn or is_owner:
                ready = Draft.is_ready(channel_id)
                if not ready:
                    return

                if "Ask" in button_id:
                    event = "Ask opponent."

                    players[0], players[1] = players[1], players[0]
                    if interaction.message is not None:
                        await interaction.message.delete()

                    player = players[0].mention
                    content = f"{player}, your opponent passed. What do you prefer?"
                    interaction = await response.send_message(content, view=self)
                else:
                    if "Pick" in button_id:
                        event = "First pick."

                        if interaction.message is not None:
                            await interaction.message.delete()

                    elif "Map" in button_id:
                        event = "Map choice."

                        players[0], players[1] = players[1], players[0]
                        if interaction.message is not None:
                            await interaction.message.delete()

                    command = self.bot.get_application_command("draft map")
                    assert command is not None and isinstance(
                        command, discord.SlashCommand
                    )

                    player = players[1].mention
                    content = f"{player}, use {command.mention} to select a Map."
                    interaction = await response.send_message(content)

                message = await interaction.original_response()
                Misc.send_log(interaction, event)

                query = """
                    UPDATE Drafts
                    SET MessageID = ?
                    WHERE ChannelID = ?
                """
                values = (
                    message.id,
                    channel_id,
                )
                async with database_connection.cursor() as cursor:
                    await cursor.execute(query, values)

                query = """
                    DELETE FROM Teams
                    WHERE ChannelID = ?
                """
                values = (channel_id,)
                async with database_connection.cursor() as cursor:
                    await cursor.execute(query, values)

                for player in players:
                    query = """
                        INSERT INTO Teams (
                            UserID,
                            ChannelID
                        )
                        VALUES (?, ?)
                    """
                    values = (
                        player.id,
                        channel_id,
                    )
                    async with database_connection.cursor() as cursor:
                        await cursor.execute(query, values)

                await database_connection.commit()
                Draft.ready_up(channel_id)

    @staticmethod
    def craft_embed(
        color_id: int,
        map: str,
        players: list,
        channel_id: int,
    ) -> discord.Embed:
        # https://gist.github.com/Soheab/d9cf3f40e34037cfa544f464fc7d919e
        colors = [
            discord.Color.dark_blue(),  # Blue Team
            discord.Color.dark_red(),  # Red Team
            discord.Color.dark_purple(),  # Bans
            discord.Color.blue(),  # Draft Over
        ]

        title = "Draft Simulation"
        embed = discord.Embed(
            title=title,
            color=colors[color_id],
            description=map,
        )
        embed.add_field(
            name="Blue Team",
            value=players[0].name.capitalize(),
            inline=True,
        )
        embed.add_field(
            name="Red Team",
            value=players[1].name.capitalize(),
            inline=True,
        )
        embed.set_image(url=f"attachment://{channel_id}.png")
        return embed

    def delete_image(
        self,
        path: str,
    ) -> None:
        try:
            os.remove(path)
        except FileNotFoundError:
            event = f"File {path} already deleted."
            print(event)
        except OSError:
            event = f"File {path} not accessible."
            print(event)

    async def delete_message(
        self,
        channel_id: int | None,
        message_id: int,
    ) -> None:
        assert channel_id is not None
        channel = self.bot.get_channel(channel_id)
        try:
            message = [discord.Object(id=message_id)]
            if isinstance(
                channel,
                (
                    discord.TextChannel,
                    discord.Thread,
                    discord.VoiceChannel,
                ),
            ):
                await channel.delete_messages(message)
        except AttributeError:
            event = f"Channel {channel_id} not accessible."
            print(event)
        except discord.errors.NotFound:
            event = f"Message {message_id} not found."
            print(event)
        except discord.errors.Forbidden:
            event = f"Message {message_id} not accessible."
            print(event)

    @tasks.loop(seconds=draft_settings.expiration_frequency)
    async def expiration(self) -> None:
        query = """
            SELECT ChannelID,
                MessageID,
                (
                    SELECT COUNT (*)
                    FROM Selections
                    WHERE Selections.ChannelID = Drafts.ChannelID
                ) AS Slot
            FROM Drafts
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
            total = await cursor.fetchall()

        total = list(total)

        query = """
            SELECT ChannelID,
                MessageID,
                (
                    SELECT COUNT (*)
                    FROM Selections
                    WHERE Selections.ChannelID = Drafts.ChannelID
                ) AS Slot
            FROM Drafts
            WHERE ? > Time + ?
        """
        values = (
            time.time(),
            draft_settings.expiration_time,
        )
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchall()

        results = list(results)

        for result in results:
            channel_id, message_id, slot = result

            # Delete the message only if the draft is being aborted due to being incomplete.
            if slot < 1:
                await self.delete_message(channel_id, message_id)

                days = draft_settings.expiration_time // 86400  # 1 day
                content = f"Draft expired after {days} days of inactivity."

                if draft_settings.expiration_notification and slot < 16:
                    # Notify that the draft has expired due to inactivity.
                    try:
                        channel = self.bot.get_channel(channel_id)
                        if isinstance(
                            channel,
                            (
                                discord.TextChannel,
                                discord.Thread,
                                discord.VoiceChannel,
                            ),
                        ):
                            await channel.send(content)
                    except (
                        AttributeError,
                        discord.errors.Forbidden,
                    ):
                        event = f"Channel {channel_id} not accessible."
                        print(event)

                event = f"Draft {channel_id} expired."
                print(event)

            query = """
                DELETE FROM Drafts
                WHERE ChannelID = ?
            """
            values = (channel_id,)
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)

        await database_connection.commit()
        print(f"{len(results)}/{len(total)} drafts expired.")

    async def draft_countdown(
        self,
        context: discord.ApplicationContext,
        message: discord.Message,
        seconds: int,
    ) -> None:
        icon_url = "https://www.iconsdb.com/icons/preview/white/clock-xxl.png"

        try:
            embed = message.embeds[0]
        except AttributeError:
            return

        embed.set_image(url=f"attachment://{context.channel_id}.png")

        for amount in range(seconds, -1, -1):
            if amount == 10:
                icon_url = "https://www.iconsdb.com/icons/preview/orange/clock-xxl.png"

            if amount > 0:
                embed.set_footer(
                    text=f"{amount} seconds",
                    icon_url=icon_url,
                )
            else:
                embed.set_footer(text=discord.Embed.Empty)

            try:
                await message.edit(embeds=[embed])
            except discord.errors.NotFound:
                return

            await asyncio.sleep(1)

    @expiration.before_loop
    async def before_expiration(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(4)

    layout_choices = list(layouts.keys())

    @draft.command(
        name="start",
        description="Start a draft simulation.",
    )
    @option(
        "opponent",
        discord.SlashCommandOptionType.user,
        description="Choose an opponent.",
    )
    @option(
        "coin",
        description="Select who should win the coin toss.",
        default="Random",
        choices=[
            "Me",
            "Opponent",
            "Random",
        ],
    )
    async def draft_start(
        self,
        context: discord.ApplicationContext,
        opponent: discord.User,
        coin: str,
    ) -> None:
        ready = Draft.is_ready(context.channel_id)
        if not ready:
            return

        query = """
            SELECT (
                    SELECT COUNT (*)
                    FROM Selections
                    WHERE Selections.ChannelID = Drafts.ChannelID
                ) AS Slot
            FROM Drafts
            WHERE ChannelID = ?
        """
        values = (context.channel_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        # Check if another draft is going on.
        if results is not None:
            slot = results[0]
            # Check if there are picks remaining.
            if slot < 16:
                command = self.bot.get_application_command("draft quit")
                assert command is not None and isinstance(command, discord.SlashCommand)

                event = "Another draft going on."
                content = f"{event[-1]} in this channel. Use {command.mention} first."

                await context.respond(content=content, ephemeral=True)
                Misc.send_log(context, event)

                Draft.ready_up(context.channel_id)
                return

        # Check if the selected opponent is valid.
        self_target = context.author == opponent
        is_owner = await self.bot.my_is_owner(context.author.id)
        is_allowed = context.author.id in draft_settings.self_drafters
        if self_target and not is_owner and not is_allowed:
            event = "You can't draft against yourself."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        result = '"won"'
        if coin == "Opponent":
            random = 0
        elif coin == "Me":
            random = 1
        else:
            result = "won"
            random = secrets.randbelow(2)

        players: list[discord.Member | discord.User] = (
            [opponent, context.author] if random == 0 else [context.author, opponent]
        )

        event = "Draft started."
        content = f"{event[-1]}: {players[0].mention} against {players[1].mention}."

        await context.respond(
            content=content,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        Misc.send_log(context, event)

        player = players[0].mention
        content = f"{player}, you {result} the coin toss. What do you prefer?"
        view = self.CoinView(self.bot)

        message = await context.respond(content, view=view)

        query = """
            INSERT OR REPLACE INTO Drafts (
                ChannelID,
                MessageID,
                Image,
                Layout,
                Map,
                Time
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """
        values = (
            context.channel_id,
            message.id,
            None,
            None,
            None,
            time.time(),
        )
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)

        for player in players:
            query = """
                INSERT INTO Teams (
                    UserID,
                    ChannelID
                )
                VALUES (?, ?)
            """
            values = (
                player.id,
                context.channel_id,
            )
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)

        await database_connection.commit()
        Draft.ready_up(context.channel_id)

    map_choices = [
        "Random (Quick Match)",
        "Random (Storm League)",
        "Random (Custom Game)",
    ]
    loop = asyncio.get_event_loop()
    map_choices += loop.run_until_complete(Map.catalog())
    del loop

    @draft.command(
        name="map",
        description="Select a Map for the current draft simulation.",
    )
    @option(
        "map",
        description="Select a Map.",
        choices=map_choices,
    )
    @option(
        "layout",
        description="Select a layout, else use the default layout for this server.",
        default=None,
        choices=layout_choices,
    )
    async def draft_map(
        self,
        context: discord.ApplicationContext,
        map: str,
        layout: str,
    ) -> None:
        ready = Draft.is_ready(context.channel_id)
        if not ready:
            return

        query = """
            SELECT MessageID,
                Image
            FROM Drafts
            WHERE ChannelID = ?
        """
        values = (context.channel_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        # Check if another draft is going on.
        if results is None:
            command = self.bot.get_application_command("draft start")
            assert command is not None and isinstance(command, discord.SlashCommand)

            event = "No draft going on."
            content = f"{event} Use {command.mention} to begin a new draft."

            await context.respond(content=content, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        message_id, image = results

        if image is not None:
            command = self.bot.get_application_command("draft hero")
            assert command is not None and isinstance(command, discord.SlashCommand)

            event = "Map already selected."
            content = content = f"{event} Use {command.mention} to continue the draft."

            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        # Choose a random Map, excluding banned ones.
        if "Random" in map:
            game_mode = map[8:-1]
            map_pool = await Map.catalog(game_mode)
            map = secrets.choice(map_pool)

        # Check if the server has a custom default layout.
        if layout is None:
            layout = (
                "Horizontal"
                if context.guild_id in draft_settings.alternative_layout_servers
                else "Vertical"
            )

        slot = 0
        try:
            portrait = Image.open("./draft/slots/next.png")
        except OSError:
            Draft.ready_up(context.channel_id)
            raise
        else:
            portrait = portrait.resize(self.portrait_size)
            map_code = map.lower().replace(" ", "-").replace("'", "")
            image = Image.open(f"./draft/layouts/{layout.lower()}/{map_code}.png")
            image.paste(portrait, self.layouts[layout][slot])
            path = f"./draft/{context.channel_id}.png"
            image.save(path)

        players = await Draft.get_drafting_players(self.bot, context.channel_id)

        # Check whose turn is.
        map_chooser = context.author == players[0]
        is_owner = await self.bot.my_is_owner(context.author.id)
        is_allowed = context.author.id in draft_settings.self_drafters
        if map_chooser and not is_owner and not is_allowed:
            event = "Not your turn."
            content = f"No, it's {players[1].mention}'s turn!"

            await context.respond(
                content,
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        filename = f"{context.channel_id}.png"
        file = discord.File(path, filename)

        assert context.channel_id is not None
        embed = Draft.craft_embed(
            color_id=2,
            map=map,
            players=players,
            channel_id=context.channel_id,
        )

        command = self.bot.get_application_command("draft hero")
        assert command is not None and isinstance(command, discord.SlashCommand)

        try:
            content = f"{players[0].mention}, use {command.mention} to ban a Hero."
            interaction = await context.respond(
                content,
                embed=embed,
                file=file,
            )
        except discord.errors.DiscordServerError:
            event = "Discord error."
            content = f"{event} Try again later."

            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        assert isinstance(interaction, discord.Interaction)
        message = await interaction.original_response()
        await self.delete_message(context.channel_id, message_id)

        # Encode the image, from PNG to BLOB.
        with open(path, "rb") as file:
            data = file.read()
        image = base64.b64encode(data)

        # Delete image from disk.
        self.delete_image(path)

        query = """
            UPDATE Drafts
            SET MessageID = ?,
                Image = ?,
                Layout = ?,
                Map = ?
            WHERE ChannelID = ?
        """
        values = (
            message.id,
            image,
            layout,
            map,
            context.channel_id,
        )
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)

        await database_connection.commit()
        Draft.ready_up(context.channel_id)
        await self.draft_countdown(context, message, self.countdowns[0])

    @draft.command(
        name="hero",
        description="Pick or ban a Hero for the current draft simulation.",
    )
    @option(
        "hero",
        description="Select a Hero.",
        autocomplete=Autocomplete.heroes,
    )
    async def draft_hero(
        self,
        context: discord.ApplicationContext,
        hero: str,
    ) -> None:
        ready = Draft.is_ready(context.channel_id)
        if not ready:
            return

        query = """
            SELECT MessageID,
                Image,
                Layout,
                Map
            FROM Drafts
            WHERE ChannelID = ?
        """
        values = (context.channel_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        # Check if another draft is going on.
        if results is None:
            command = self.bot.get_application_command("draft start")
            assert command is not None and isinstance(command, discord.SlashCommand)

            event = "No draft going on."
            content = f"{event} Use {command.mention} to begin a new draft."

            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        message_id, image, layout, map = results

        # Check if another draft is going on.
        if map is None:
            event = "Map missing."
            content = "Map not selected yet."

            Misc.send_log(context, event)
            await context.respond(content, ephemeral=True)

            Draft.ready_up(context.channel_id)
            return

        query = """
            SELECT Name
            FROM Heroes
            INNER JOIN Selections
            ON Heroes.HeroID = Selections.HeroID
            WHERE ChannelID = ?
        """
        values = (context.channel_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchall()

        # Extract all Heroes that have been already used.
        heroes = [hero for result in results for hero in result]
        slot = len(heroes)

        # Check if there are picks remaining.
        if slot == 16:
            command = self.bot.get_application_command("draft start")
            assert command is not None and isinstance(command, discord.SlashCommand)

            event = "No picks remaining."
            content = f"{event} Use {command.mention} to begin a new draft."

            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        players = await Draft.get_drafting_players(self.bot, context.channel_id)

        # Check whose turn is.
        next = self.turns[slot]
        self_target = context.author != players[next]
        is_owner = await self.bot.my_is_owner(context.author.id)
        is_allowed = context.author.id in draft_settings.self_drafters
        if self_target and not is_owner and not is_allowed:
            event = "Not your turn."
            content = f"No, it's {players[next].mention}'s turn!"

            await context.respond(
                content,
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        # Get the exact name of the selected Hero.
        hero = await Hero.fix_name(hero)
        if hero is None:
            event = "Hero not valid."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        # Check if the selected Hero has been already used.
        if hero in heroes:
            index = heroes.index(hero)

            move = "banned" if index in self.previous_bans else "picked"
            verb = "have" if hero == "The Lost Vikings" else "has"

            event = "Hero not available."
            content = f"{hero} {verb} already been {move} before."

            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        file = Hero.get_code(hero, "Blizzard")
        portrait = Image.open(f"./images/heroes/{file}.png")
        portrait = portrait.resize(self.portrait_size)
        if slot < 4 or slot == 9 or slot == 10:
            enhancer = ImageEnhance.Brightness(portrait)
            portrait = enhancer.enhance(0.60)

        path = f"./draft/{context.channel_id}.png"

        # Decode the image, from BLOB to PNG.
        data = base64.b64decode(image)
        with open(path, "wb") as file:
            file.write(data)

        image = Image.open(path)
        image.paste(portrait, self.layouts[layout][slot])

        move = "banned" if slot in self.previous_bans else "picked"
        verb = "have" if hero == "The Lost Vikings" else "has"

        event = f"Turn {slot + 1}: {hero} {move}."

        if draft_settings.actions_history:
            await context.respond(content=event)
        Misc.send_log(context, event)

        if slot < 15:
            next = self.turns[slot + 1]

            if slot + 1 in self.previous_bans:
                move = "ban"
                color_id = 2
            else:
                move = "pick"
                color_id = next

            portrait = Image.open("./draft/slots/next.png")
            portrait = portrait.resize(self.portrait_size)
            image.paste(portrait, self.layouts[layout][slot + 1])

            command = self.bot.get_application_command("draft hero")
            assert command is not None and isinstance(command, discord.SlashCommand)

            next_player = players[next].mention
            content = f"{next_player}, use {command.mention} to {move} a Hero."

            allowed_mentions = discord.AllowedMentions.all()
        else:
            color_id = 3
            content = f"Draft over on {map}: {players[0].mention} against {players[1].mention}."
            allowed_mentions = discord.AllowedMentions.none()

        image.save(path)

        filename = f"{context.channel_id}.png"
        file = discord.File(path, filename)

        assert context.channel_id is not None
        embed = Draft.craft_embed(
            color_id=color_id,
            map=map,
            players=players,
            channel_id=context.channel_id,
        )

        try:
            await context.respond(
                file=file,
                embed=embed,
                content=content,
                allowed_mentions=allowed_mentions,
            )
        except discord.errors.DiscordServerError:
            event = "Discord error."
            content = f"{event} Try again later."
            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)
            return

        message = await context.interaction.original_response()
        await self.delete_message(context.channel_id, message_id)

        # Encode the image, from PNG to BLOB.
        with open(path, "rb") as file:
            data = file.read()
        image = base64.b64encode(data)

        # Delete image from disk.
        self.delete_image(path)

        slot += 1

        # Save changes in the database.
        query = """
            UPDATE Drafts
            SET MessageID = ?,
                Image = ?,
                Time = ?
            WHERE ChannelID = ?
        """
        values = (
            message.id,
            image,
            time.time(),
            context.channel_id,
        )
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)

        hero_id = await Hero.get_id(hero)

        query = """
            INSERT INTO Selections (
                ChannelID,
                HeroID
            )
            VALUES (?, ?)
        """
        values = (
            context.channel_id,
            hero_id,
        )
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)

        await database_connection.commit()
        Draft.ready_up(context.channel_id)
        if slot < 16:
            await self.draft_countdown(context, message, self.countdowns[1])

    @draft.command(
        name="undo",
        description="Undo your previous move for the current draft simulation.",
    )
    async def draft_undo(
        self,
        context: discord.ApplicationContext,
    ) -> None:
        ready = Draft.is_ready(context.channel_id)
        if not ready:
            return

        query = """
            SELECT MessageID,
                Image,
                Layout,
                Map
            FROM Drafts
            WHERE ChannelID = ?
        """
        values = (context.channel_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        # Check if another draft is going on.
        if results is None:
            command = self.bot.get_application_command("draft start")
            assert command is not None and isinstance(command, discord.SlashCommand)

            event = "No draft going on."
            content = f"{event} Use {command.mention} to begin a new draft."

            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        message_id, image, layout, map = results

        query = """
            SELECT COUNT (Selections.SelectionID) as Slot,
                Heroes.Name
            FROM Heroes
            INNER JOIN Selections
            ON Heroes.HeroID = Selections.HeroID
            WHERE Selections.ChannelID = ?
        """
        values = (context.channel_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        assert results is not None
        slot, hero = results

        # Check if there are moves to undo.
        if slot == 0:
            command = self.bot.get_application_command("draft start")
            assert command is not None and isinstance(command, discord.SlashCommand)

            event = "No moves to undo."
            content = f"{event} Use {command.mention} to begin a new draft."

            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        players = await Draft.get_drafting_players(self.bot, context.channel_id)

        # Check whose turn was.
        previous = self.turns[slot - 1]
        self_target = context.author != players[previous]
        is_owner = await self.bot.my_is_owner(context.author.id)
        is_allowed = context.author.id in draft_settings.self_drafters
        if self_target and not is_owner and not is_allowed:
            event = "Not your turn."
            content = "You can only undo your own moves."

            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        path = f"./draft/{context.channel_id}.png"

        # Decode the image, from BLOB to PNG.
        data = base64.b64decode(image)
        with open(path, "wb") as file:
            file.write(data)

        image = Image.open(path)

        if slot < 16:
            portrait = Image.open("./draft/slots/none.png")
            portrait = portrait.resize(self.portrait_size)
            image.paste(portrait, self.layouts[layout][slot])

        move = "banned" if slot in self.next_bans else "picked"
        event = f"Turn {slot - 1}: {hero} un{move}."
        content = event

        if draft_settings.actions_history:
            await context.respond(content)
        Misc.send_log(context, event)

        if slot in self.next_bans:
            move = "ban"
            color_id = 2
        else:
            move = "pick"
            color_id = previous

        portrait = Image.open("./draft/slots/next.png")
        portrait = portrait.resize(self.portrait_size)
        slot -= 1
        image.paste(portrait, self.layouts[layout][slot])
        image.save(path)

        command = self.bot.get_application_command("draft hero")
        assert command is not None and isinstance(command, discord.SlashCommand)

        filename = f"{context.channel_id}.png"
        file = discord.File(path, filename)

        assert context.channel_id is not None
        embed = Draft.craft_embed(
            color_id=color_id,
            map=map,
            players=players,
            channel_id=context.channel_id,
        )

        try:
            previous_player = players[previous]
            assert isinstance(previous_player, discord.User)

            previous_player = previous_player.mention
            content = f"{previous_player}, use {command.mention} to {move} a Hero."
            await context.respond(
                content,
                embed=embed,
                file=file,
            )
        except discord.errors.DiscordServerError:
            event = "Discord error."
            content = f"{content} Try again later."
            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            return

        message = await context.interaction.original_response()
        await self.delete_message(context.channel_id, message_id)

        # Encode the image, from PNG to BLOB.
        with open(path, "rb") as file:
            data = file.read()
        image = base64.b64encode(data)

        # Delete image from disk.
        self.delete_image(path)

        # Save changes in the database.
        query = """
            UPDATE Drafts
            SET MessageID = ?,
                Image = ?,
                Time = ?
            WHERE ChannelID = ?
        """
        values = (
            message.id,
            image,
            time.time(),
            context.channel_id,
        )
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)

        query = """
            DELETE FROM Selections
            WHERE SelectionID = (
                SELECT SelectionID
                FROM Selections
                WHERE ChannelID = ?
                ORDER BY SelectionID DESC LIMIT 1
            )
        """
        values = (context.channel_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)

        await database_connection.commit()
        Draft.ready_up(context.channel_id)

    @draft.command(
        name="quit",
        description="Quit the current draft simulation.",
    )
    async def draft_quit(
        self,
        context: discord.ApplicationContext,
    ) -> None:
        ready = Draft.is_ready(context.channel_id)
        if not ready:
            return

        query = """
            SELECT MessageID,
                (
                    SELECT COUNT (*)
                    FROM Selections
                    WHERE Selections.ChannelID = Drafts.ChannelID
                ) AS Slot
            FROM Drafts
            WHERE ChannelID = ?
        """
        values = (context.channel_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        # Check if another draft is going on.
        if results is None:
            command = self.bot.get_application_command("draft start")
            assert command is not None and isinstance(command, discord.SlashCommand)

            event = "No draft going on."
            content = f"{event} Use {command.mention} to begin a new draft."

            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            Draft.ready_up(context.channel_id)
            return

        message_id, slot = results

        query = """
            DELETE FROM Drafts
            WHERE ChannelID = ?
        """
        values = (context.channel_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)

        if slot > 15:
            event = "Draft finalized."
        else:
            if slot < 1:
                await self.delete_message(context.channel_id, message_id)
            event = "Draft aborted."

        await context.respond(content=event)
        Misc.send_log(context, event)

        await database_connection.commit()
        Draft.ready_up(context.channel_id)


def setup(bot: MyBot) -> None:
    bot.add_cog(Draft(bot))
