import time

import discord
from discord import option
from discord.ext import commands
from discord.utils import escape_mentions, remove_markdown

from database import database_connection
from main import MyBot
from tools.autocomplete import Autocomplete
from tools.hero import Hero
from tools.misc import Misc


class Matchup(commands.Cog):

    matchup = discord.SlashCommandGroup(
        name="matchup",
        description="Matchup information.",
    )

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.add_view(self.HeroView(self.bot))
        self.bot.add_view(self.TipsView(self.bot))
        self.bot.add_view(self.PermissionView(self.bot))
        self.bot.add_view(self.NotificationView(self.bot))

        print("Matchup extension loaded.")

    @staticmethod
    def get_color(win_chance) -> discord.Color:
        if win_chance == "Favored":
            color = discord.Color.green()
        elif win_chance == "Unfavored":
            color = discord.Color.red()
        else:
            color = discord.Color.yellow()
        return color

    @staticmethod
    async def get_tips(
        your_hero: str,
        enemy_hero: str,
    ) -> tuple[discord.Embed, discord.File]:
        your_hero_id = await Hero.get_id(your_hero)
        enemy_hero_id = await Hero.get_id(enemy_hero)

        query = """
            SELECT MatchupID,
                WinChance,
                Notes
            FROM Matchups
            WHERE YourHeroID = ?
                AND EnemyHeroID = ?
            ORDER BY Time DESC
        """
        values = (
            your_hero_id,
            enemy_hero_id,
        )
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        hero_code = Hero.get_code(your_hero, "Blizzard")
        filename = f"{hero_code}.png"
        path = f"./images/heroes/{filename}"
        file = discord.File(path, filename=filename)

        if results is None:
            embed = discord.Embed(
                title=f"{your_hero} vs {enemy_hero}",
                description="No information available.",
                color=discord.Color.blue(),
            )
            embed.set_thumbnail(url=f"attachment://{filename}")

            return embed, file

        matchup_id, win_chance, notes = results

        query = """
            SELECT Text
            FROM MatchupTips
            WHERE MatchupID = ?
        """
        values = (matchup_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchall()

        tips = [value for result in results for value in result][0:4]

        win_chance = (
            "Favored" if win_chance > 0 else "Unfavored" if win_chance < 0 else "Even"
        )

        embed = discord.Embed(
            title=f"{your_hero} vs {enemy_hero}",
            description=f"{your_hero} is {win_chance.lower()} against {enemy_hero}.",
            color=Matchup.get_color(win_chance),
        )

        for index, tip in enumerate(tips):
            if tip and not tip.isspace():
                tip = escape_mentions(tip)
                tip = remove_markdown(tip)

                embed.add_field(
                    name=f"Tip {index + 1}",
                    value=tip,
                    inline=False,
                )

        if notes and not notes.isspace():
            notes = escape_mentions(notes)
            notes = remove_markdown(notes)

            embed.add_field(
                name="Notes",
                value=notes,
                inline=False,
            )

        embed.set_thumbnail(url=f"attachment://{filename}")

        return embed, file

    class TipsView(discord.ui.View):
        def __init__(
            self,
            bot: MyBot,
        ) -> None:
            self.bot: MyBot = bot
            super().__init__(timeout=None)

        @discord.ui.button(
            label="Switch",
            custom_id="Matchup¦SwitchHero",
            style=discord.ButtonStyle.blurple,
        )
        async def switch_callback(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            assert interaction.message is not None
            embed_title = interaction.message.embeds[0].title

            assert isinstance(embed_title, str)
            enemy_hero, your_hero = embed_title.split(" vs ")

            embed, file = await Matchup.get_tips(your_hero, enemy_hero)
            await interaction.response.edit_message(
                embeds=[embed],
                file=file,
                view=Matchup.TipsView(self.bot),
            )

    @staticmethod
    def list_matchups(
        embed: discord.Embed,
        name: str,
        matchups: list[str],
    ) -> discord.Embed:
        if len(matchups) == 0:
            value = "-"
        else:
            matchups.sort()
            value = "• " + "\n• ".join(matchups)

        embed.add_field(
            name=name,
            value=value,
            inline=True,
        )
        return embed

    @staticmethod
    async def get_matchups(
        your_hero: str,
        show_missing: bool = False,
    ) -> tuple[discord.Embed, discord.File]:
        your_hero_id = await Hero.get_id(your_hero)

        query = """
            SELECT EnemyHeroID,
                WinChance
            FROM Matchups
            WHERE YourHeroID = ?
            GROUP BY EnemyHeroID
            HAVING Time = MAX(Time)
        """
        values = (your_hero_id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchall()

        favored_matchups = []
        even_matchups = []
        unfavored_matchups = []

        for result in results:
            enemy_hero_id, win_chance = result
            enemy_hero = await Hero.get_name(enemy_hero_id)

            if win_chance > 0:
                favored_matchups.append(enemy_hero)
            elif win_chance < 0:
                unfavored_matchups.append(enemy_hero)
            else:
                even_matchups.append(enemy_hero)

        embed = discord.Embed(
            title=f"{your_hero} Matchups",
            description="Chance to win against other Heroes.",
            color=discord.Color.blue(),
        )

        if show_missing:
            offlaners = await Hero.catalog("Offlaner")
            offlaners.remove(your_hero)

            missing_matchups = [
                hero
                for hero in offlaners
                if hero not in favored_matchups + even_matchups + unfavored_matchups
            ]

            embed.title = str(embed.title) + " (2/2)"
            embed = Matchup.list_matchups(embed, "Missing", missing_matchups)
        else:
            embed.title = str(embed.title) + " (1/2)"
            embed = Matchup.list_matchups(embed, "Favored", favored_matchups)
            embed = Matchup.list_matchups(embed, "Even", even_matchups)
            embed = Matchup.list_matchups(embed, "Unfavored", unfavored_matchups)

        hero_code = Hero.get_code(your_hero, "Blizzard")
        filename = f"{hero_code}.png"
        path = f"./images/heroes/{filename}"
        file = discord.File(path, filename=filename)

        embed.set_thumbnail(url=f"attachment://{filename}")

        return embed, file

    class NotificationView(discord.ui.View):
        def __init__(
            self,
            bot: MyBot,
        ) -> None:
            self.bot: MyBot = bot
            super().__init__(timeout=None)

        @discord.ui.button(
            label="Accept",
            custom_id="Matchup¦AcceptTips",
            style=discord.ButtonStyle.blurple,
        )
        async def accept_callback(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            button.style = discord.ButtonStyle.green
            button.disabled = True

            other_button = self.children[1]
            assert isinstance(other_button, discord.Button)
            other_button.style = discord.ButtonStyle.blurple
            other_button.disabled = False

            await interaction.response.edit_message(view=self)

        @discord.ui.button(
            label="Decline",
            custom_id="Matchup¦DeclineTips",
            style=discord.ButtonStyle.blurple,
        )
        async def decline_callback(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            button.style = discord.ButtonStyle.red
            button.disabled = True

            other_button = self.children[0]
            assert isinstance(other_button, discord.Button)
            other_button.style = discord.ButtonStyle.blurple
            other_button.disabled = True

            await interaction.response.edit_message(view=self)

            assert interaction.message is not None
            embed_title = interaction.message.embeds[0].title

            assert isinstance(embed_title, str)
            your_hero, enemy_hero = embed_title.split(" vs ")

            your_hero_id = await Hero.get_id(your_hero)
            enemy_hero_id = await Hero.get_id(enemy_hero)

            user_id = interaction.message.raw_mentions[0]
            timestamp = int(interaction.message.created_at.timestamp())

            query = """
                DELETE FROM Matchups
                WHERE UserID = ?
                    AND YourHeroID = ?
                    AND EnemyHeroID = ?
                    AND Time BETWEEN ? AND ?
                """
            values = (
                user_id,
                your_hero_id,
                enemy_hero_id,
                timestamp - 1,
                timestamp + 1,
            )
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)

    class MatchupModal(discord.ui.Modal):
        def __init__(
            self,
            bot: MyBot,
            your_hero: str,
            enemy_hero: str,
            win_chance: int,
            texts: list[str],
            *args,
            **kwargs,
        ) -> None:
            self.bot: MyBot = bot
            self.your_hero: str = your_hero
            self.enemy_hero: str = enemy_hero
            self.win_chance: int = win_chance
            super().__init__(*args, **kwargs)

            tips = texts[0:4]
            for index, tip in enumerate(tips):
                if tip is None:
                    tip = ""

                self.add_item(
                    discord.ui.InputText(
                        label=f"Tip {index + 1}",
                        style=discord.InputTextStyle.short,
                        max_length=128,
                        value=tip,
                        required=(index < 1),
                    )
                )

            notes = texts[-1]
            if notes is None:
                notes = ""

            self.add_item(
                discord.ui.InputText(
                    label="Notes",
                    style=discord.InputTextStyle.short,
                    max_length=128,
                    value=notes,
                    required=False,
                )
            )

        async def callback(
            self,
            interaction: discord.Interaction,
        ) -> None:
            assert interaction.user is not None
            user_id = interaction.user.id

            your_hero_id = await Hero.get_id(self.your_hero)
            enemy_hero_id = await Hero.get_id(self.enemy_hero)

            notes = self.children[-1].value

            query = """
                INSERT INTO Matchups (
                    UserID,
                    YourHeroID,
                    EnemyHeroID,
                    WinChance,
                    Time,
                    Notes
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """
            values = (
                user_id,
                your_hero_id,
                enemy_hero_id,
                self.win_chance,
                time.time(),
                notes,
            )
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)

            await database_connection.commit()

            query = """
                SELECT MatchupID
                FROM Matchups
                WHERE UserID = ?
                    AND YourHeroID = ?
                    AND EnemyHeroID = ?
                ORDER BY Time DESC
            """
            values = (
                user_id,
                your_hero_id,
                enemy_hero_id,
            )
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)
                results = await cursor.fetchone()

            assert results is not None
            matchup_id = results[0]

            tips = []
            for child in self.children[0:4]:
                tips.append(child.value)

            for tip in tips:
                if tip == "":
                    continue

                query = """
                    INSERT INTO MatchupTips (
                        MatchupID,
                        Text
                    )
                    VALUES (?, ?)
                """
                values = (
                    matchup_id,
                    tip,
                )
                async with database_connection.cursor() as cursor:
                    await cursor.execute(query, values)

            await database_connection.commit()

            embed, file = await Matchup.get_tips(self.your_hero, self.enemy_hero)
            await interaction.response.send_message(
                content=f"Matchup updated.",
                embeds=[embed],
                file=file,
                ephemeral=True,
            )

            content = f"Matchup updated by {interaction.user.mention}."
            embed, file = await Matchup.get_tips(self.your_hero, self.enemy_hero)

            admin = self.bot.admin
            if not admin:
                event = "Admin not found."

                await interaction.response.send_message(content=event, ephemeral=True)
                Misc.send_log(interaction, event)

                return

            await admin.send(
                content=content,
                embeds=[embed],
                file=file,
                view=Matchup.NotificationView(self.bot),
            )

    class PermissionView(discord.ui.View):
        def __init__(
            self,
            bot: MyBot,
        ) -> None:
            self.bot: MyBot = bot
            super().__init__(timeout=None)

        @discord.ui.button(
            label="Accept",
            custom_id="Matchup¦AcceptPermissionRequest",
            style=discord.ButtonStyle.blurple,
        )
        @commands.is_owner()
        async def accept_callback(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            await self.on_interaction(button, interaction)

        @discord.ui.button(
            label="Decline",
            custom_id="Matchup¦DeclinePermissionRequest",
            style=discord.ButtonStyle.blurple,
        )
        @commands.is_owner()
        async def decline_callback(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            await self.on_interaction(button, interaction)

        async def on_interaction(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            assert interaction.message is not None
            user_id = interaction.message.raw_mentions[0]

            button.disabled = True
            if button.custom_id == "Matchup¦AcceptPermissionRequest":
                permission = 1
                action = "granted"
                button.style = discord.ButtonStyle.green
                other_button = self.children[1]
            else:
                permission = 0
                action = "denied"
                button.style = discord.ButtonStyle.red
                other_button = self.children[0]

            assert isinstance(other_button, discord.Button)
            other_button.style = discord.ButtonStyle.blurple
            other_button.disabled = False

            await interaction.response.edit_message(view=self)

            query = """
                UPDATE Users
                SET Permission = ?
                WHERE UserID = ?
            """
            values = (
                permission,
                user_id,
            )
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)

            await database_connection.commit()

            user = await self.bot.my_fetch_user(user_id)
            if user is not None and not self.bot.my_is_owner(user_id):
                content = f"Matchups permission {action}."
                await user.send(content)

    @matchup.command(
        name="permission",
        description="Ask for permission to edit matchups.",
    )
    async def matchup_permission(
        self,
        context: discord.ApplicationContext,
    ) -> None:
        if await self.bot.my_is_owner(context.author.id):
            bot_name = self.bot.user.name if self.bot.user is not None else "Bot"
            content = f"{bot_name}'s owners don't have to ask for permission to edit matchups."
            await context.respond(content, ephemeral=True)
            return

        query = """
            SELECT *
            FROM Users
            WHERE UserID = ?
        """
        values = (context.author.id,)
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        if results is not None:
            content = "You cannot ask again for permission to edit matchups."
            await context.respond(content, ephemeral=True)
            return

        permission = 0

        query = """
            INSERT INTO Users (
                UserID,
                Permission
            )
            VALUES (?, ?)
        """
        values = (
            context.author.id,
            permission,
        )
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)

        await database_connection.commit()

        content = f"{context.user.mention} would like to contribute to matchups."
        timestamp = int(context.user.created_at.timestamp())

        embed = discord.Embed(
            title=context.user,
            description=f"Discord member since: <t:{timestamp}:D>",
            color=discord.Color.blue(),
        )
        assert context.user.avatar is not None
        embed.set_thumbnail(url=context.user.avatar.url)

        for index, guild in enumerate(context.user.mutual_guilds):
            if index >= 25:
                break

            embed.add_field(
                name=f"Guild {index + 1}",
                value=guild.name,
                inline=False,
            )

        admin = self.bot.admin
        view = Matchup.PermissionView(self.bot)
        if admin:
            await admin.send(
                content=content,
                embeds=[embed],
                view=view,
            )
        else:
            event = "Admin not found."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            return

        assert self.bot.user is not None

        event = "Matchups permission asked."
        content = f"{event} Your request will be reviewed and then you will receive a private message from {self.bot.user.mention}."

        await context.respond(content, ephemeral=True)
        Misc.send_log(context, event)

    class HeroView(discord.ui.View):
        def __init__(
            self,
            bot: MyBot,
        ) -> None:
            self.bot: MyBot = bot
            super().__init__(timeout=None)

        @discord.ui.button(
            label="Available",
            custom_id="Matchup¦Available",
            style=discord.ButtonStyle.blurple,
            disabled=True,
        )
        async def available_callback(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            await self.on_interaction(button, interaction)

        @discord.ui.button(
            label="Missing",
            custom_id="Matchup¦Missing",
            style=discord.ButtonStyle.blurple,
        )
        async def missing_callback(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            await self.on_interaction(button, interaction)

        async def on_interaction(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            assert interaction.message is not None
            embed_title = interaction.message.embeds[0].title

            assert isinstance(embed_title, str)
            your_hero = embed_title.split(" Matchups")[0]

            show_missing = button.custom_id == "Matchup¦Missing"
            embed, _ = await Matchup.get_matchups(your_hero, show_missing)

            self.enable_all_items()
            button.disabled = True

            await interaction.response.edit_message(embeds=[embed], view=self)

    @matchup.command(
        name="list",
        description="View the matchups available for a given Hero.",
    )
    @option(
        "your_hero",
        description="Select your Hero.",
        autocomplete=Autocomplete.heroes,
    )
    async def matchup_list(
        self,
        context: discord.ApplicationContext,
        your_hero: str,
    ) -> None:
        command = self.bot.get_application_command("matchup tips")

        your_hero = await Hero.fix_name(your_hero)
        embed, _ = await Matchup.get_matchups(your_hero)

        assert command is not None and isinstance(command, discord.SlashCommand)
        command_description = Misc.decapitalize(command.description)

        event = "Matchup List shared."
        content = f"Use **{command.mention} <your_hero> <enemy_hero>** to {command_description}"
        view = Matchup.HeroView(self.bot)

        await context.respond(
            content,
            embeds=[embed],
            view=view,
        )
        Misc.send_log(context, event)

    @matchup.command(
        name="tips",
        description="View the tips for a specific matchup.",
    )
    @option(
        "your_hero",
        description="Select your Hero.",
        autocomplete=Autocomplete.heroes,
    )
    @option(
        "enemy_hero",
        description="Select the enemy Hero.",
        autocomplete=Autocomplete.heroes,
    )
    async def matchup_tips(
        self,
        context: discord.ApplicationContext,
        your_hero: str,
        enemy_hero: str,
    ) -> None:
        command = self.bot.get_application_command("matchup list")

        your_hero = await Hero.fix_name(your_hero)
        enemy_hero = await Hero.fix_name(enemy_hero)

        offlaners = await Hero.catalog("Offlaner")
        are_both_offlaners = your_hero not in offlaners or enemy_hero not in offlaners
        is_not_mirror = your_hero == enemy_hero

        if are_both_offlaners or is_not_mirror:
            event = "Matchup not valid."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            return

        embed, file = await Matchup.get_tips(your_hero, enemy_hero)

        assert command is not None and isinstance(command, discord.SlashCommand)
        command_description = Misc.decapitalize(command.description)

        event = "Matchup Tips shared."
        content = f"Use **{command.mention}** to {command_description}"
        view = Matchup.TipsView(self.bot)

        await context.respond(
            content,
            embeds=[embed],
            file=file,
            view=view,
        )
        Misc.send_log(context, event)

    @matchup.command(
        name="edit",
        description="Edit the information about matchups.",
    )
    @option(
        "your_hero",
        description="Select your Hero.",
        autocomplete=Autocomplete.heroes,
    )
    @option(
        "enemy_hero",
        description="Select the enemy Hero.",
        autocomplete=Autocomplete.heroes,
    )
    @option(
        "win_chance",
        description="Select the expected chance to win.",
        choices=[
            discord.OptionChoice("Favored", 1),
            discord.OptionChoice("Even", 0),
            discord.OptionChoice("Unfavored", -1),
        ],
        default=None,
    )
    async def matchup_edit(
        self,
        context: discord.ApplicationContext,
        your_hero: str,
        enemy_hero: str,
        win_chance: int,
    ) -> None:
        your_hero = await Hero.fix_name(your_hero)
        enemy_hero = await Hero.fix_name(enemy_hero)

        if await self.bot.my_is_owner(context.author.id):
            query = """
                SELECT *
                FROM Users
                WHERE UserID = ?
            """
            values = (context.author.id,)
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)
                results = await cursor.fetchone()

            permission = 1
            if results is not None:
                query = """
                    UPDATE Users
                    SET Permission = ?
                    WHERE UserID = ?
                """
                values = (
                    permission,
                    context.author.id,
                )
            else:
                query = """
                    INSERT INTO Users (
                        UserID,
                        Permission
                    )
                    VALUES (?, ?)
                """
                values = (
                    context.author.id,
                    permission,
                )
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)

            await database_connection.commit()

        query = """
            SELECT UserID
            FROM Users
            WHERE Permission = 1
        """
        async with database_connection.cursor() as cursor:
            await cursor.execute(query)
            results = await cursor.fetchall()

        contributors = [contributor for result in results for contributor in result]
        no_permission = context.author.id not in contributors

        if no_permission:
            command = self.bot.get_application_command("matchup permission")
            assert command is not None and isinstance(command, discord.SlashCommand)

            event = "No matchup permissions."
            content = f"Forbidden. Please, use {command.mention} to ask for permission."

            await context.respond(content, ephemeral=True)
            Misc.send_log(context, event)

            return

        offlaners = await Hero.catalog("Offlaner")
        are_both_offlaners = your_hero not in offlaners or enemy_hero not in offlaners
        is_not_mirror = your_hero == enemy_hero

        if are_both_offlaners or is_not_mirror:
            event = "Matchup not valid."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            return

        your_hero_id = await Hero.get_id(your_hero)
        enemy_hero_id = await Hero.get_id(enemy_hero)

        query = """
            SELECT MatchupID, WinChance, Notes
            FROM Matchups
            WHERE YourHeroID = ?
                AND EnemyHeroID = ?
            ORDER BY Time DESC
        """
        values = (
            your_hero_id,
            enemy_hero_id,
        )
        async with database_connection.cursor() as cursor:
            await cursor.execute(query, values)
            results = await cursor.fetchone()

        if results is None:
            texts = [""] * 5

            if win_chance is None:
                event = "Win chance missing."
                content = "Please, insert a win chance when adding a new matchup."

                await context.respond(content, ephemeral=True)
                Misc.send_log(context, event)

                return
        else:
            matchup_id, previous_win_chance, notes = results
            if win_chance is None:
                win_chance = previous_win_chance

            query = """
                SELECT Text
                FROM MatchupTips
                WHERE MatchupID = ?
            """
            values = (matchup_id,)
            async with database_connection.cursor() as cursor:
                await cursor.execute(query, values)
                results = await cursor.fetchall()

            tips = [text for result in results for text in result]

            texts = []
            for index in range(4):
                try:
                    texts.append(tips[index])
                except IndexError:
                    texts.append("")
            texts.append(notes)

        modal = self.MatchupModal(
            bot=self.bot,
            your_hero=your_hero,
            enemy_hero=enemy_hero,
            win_chance=win_chance,
            texts=texts,
            title=f"{your_hero} vs {enemy_hero}",
        )
        await context.send_modal(modal)


def setup(bot: MyBot) -> None:
    bot.add_cog(Matchup(bot))
