from dataclasses import fields
import inspect
import re

import discord
from discord.ext import commands

from config import authors, bot_settings
from main import MyBot
from tools.misc import Misc


class Help(commands.Cog):

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.add_view(self.HelpView(self.bot, self))
        print("Help extension loaded.")

    class HelpView(discord.ui.View):
        def __init__(
            self,
            bot: MyBot,
            outer,
        ) -> None:
            self.bot: MyBot = bot
            self.outer: Help = outer
            super().__init__(timeout=None)

        @discord.ui.button(
            label="Utility",
            custom_id="Help¦Utility",
            style=discord.ButtonStyle.blurple,
            disabled=True,
        )
        async def utility(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            await self.on_interaction(button, interaction)

        @discord.ui.button(
            label="Draft",
            custom_id="Help¦Draft",
            style=discord.ButtonStyle.blurple,
        )
        async def draft(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            await self.on_interaction(button, interaction)

        @discord.ui.button(
            label="Creative",
            custom_id="Help¦Creative",
            style=discord.ButtonStyle.blurple,
        )
        async def creative(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            await self.on_interaction(button, interaction)

        @discord.ui.button(
            label="Matchup",
            custom_id="Help¦Matchup",
            style=discord.ButtonStyle.blurple,
        )
        async def matchup(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            await self.on_interaction(button, interaction)

        async def on_interaction(
            self, button: discord.ui.Button, interaction: discord.Interaction
        ) -> None:
            page = button.label

            self.enable_all_items()
            button.disabled = True

            servers = len(interaction.client.guilds)
            embed = await self.outer.craft_embed(servers=servers, page=page)
            await interaction.response.edit_message(embed=embed, view=self)

            event = f"{page} selected."
            Misc.send_log(interaction, event)

    async def craft_embed(
        self,
        servers: int,
        page: str | None = None,
    ) -> discord.Embed:
        servers_label = "server" if servers == 1 else "servers"

        pages = {
            "Utility": [
                "/build <hero>",
                "/convert <code>",
                "/guide [category] [title]",
                "/timings [map] [category] [format]",
                "/tooltip [options]",
            ],
            "Draft": [
                "/draft start <opponent> [coin]",
                "/draft hero <hero>",
                "/draft undo",
                "/draft quit",
            ],
            "Creative": [
                "/artwork",
                "/joke",
                "/spray <hero>",
                "/quiz [category]",
            ],
            "Matchup": [
                "/matchup list <your_hero>",
                "/matchup tips <your_hero> <enemy_hero>",
                "/matchup permission",
                "/matchup edit",
            ],
        }

        page_names = list(pages)
        if page is None:
            page = page_names[0]

        title = f"Help Menu ({page_names.index(page) + 1}/{len(page_names)})"
        description = inspect.cleandoc(
            f"""
            Discord bot designed for Heroes of the Storm players!
            • Ask for assistance in the [Snowball Discord Bot]({bot_settings.official_server}) server.
            • Donate for 24/7 hosting on the [Tips of the Storm]({bot_settings.web_page}) page.
        """
        )

        inline = False
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue(),
        )

        for entry in pages[page]:
            # Split the string into full command name and options.
            results = re.search(r"(\w+ *\w*) *(.+)?", entry)

            assert results is not None
            results = results.groups()

            name, options = [result.strip() if result else result for result in results]

            command = self.bot.get_application_command(name)
            assert command is not None and isinstance(command, discord.SlashCommand)
            syntax = f"{command.mention} {options}" if options else command.mention

            embed.add_field(
                name=syntax,
                value=command.description,
                inline=inline,
            )

        embed.set_author(**authors["Elitesparkle"])
        embed.set_footer(
            text=f"{servers} {servers_label}",
            icon_url="https://icon-library.com/images/discord-icon-white/discord-icon-white-1.jpg",
        )

        return embed

    @commands.slash_command(
        name="help",
        description="Get a list of commands available.",
    )
    async def help(
        self,
        context: discord.ApplicationContext,
    ) -> None:
        servers = len(self.bot.guilds)
        embed = await self.craft_embed(servers)

        event = "Help menu shared."
        view = self.HelpView(self.bot, self)

        await context.respond(embed=embed, view=view)
        Misc.send_log(context, event)


def setup(bot: MyBot) -> None:
    bot.add_cog(Help(bot))
