import os

import discord
from discord import option
from discord.ext import commands

from config import bot_settings
from database import Database
from main import MyBot
from cogs.draft import Draft
from PIL import Image


class Admin(commands.Cog):

    admin = discord.SlashCommandGroup(
        name="admin",
        description="Admin tools.",
        guild_ids=bot_settings.debug_servers,
    )

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Admin extension loaded.")

    @admin.command(
        name="clear",
        description="Clear private messages sent to you by this bot.",
    )
    @option(
        "amount",
        description="Insert the amount of messages you want to delete.",
        min_value=1,
        max_value=100,
    )
    @commands.is_owner()
    async def admin_clear(
        self,
        context: discord.ApplicationContext,
        amount: int,
    ) -> None:
        # Defer the response, to have more time for responding.
        await context.defer(ephemeral=True)

        # Gain access to private messages between user and bot.
        channel = context.author.dm_channel
        if channel is None:
            channel = await context.author.create_dm()

        # Delete up to `amount` private messages between user and bot.
        index = 0
        async for message in channel.history(limit=int(amount)):
            if message.author == self.bot.user:
                await message.delete()
                index += 1

        content = f"{index} private messages received by this bot cleared."
        await context.respond(content, ephemeral=True)
        print(content)

    @staticmethod
    def get_cog_choices() -> list[str]:
        cog_choices = []
        for cog in os.listdir("./cogs"):
            if cog.endswith(".py"):
                cog_choices.append(cog[:-3].capitalize())
        return cog_choices

    @admin.command(
        name="load",
        description="Load an extension.",
    )
    @option(
        "extension",
        description="Select an extension.",
        choices=get_cog_choices(),
    )
    @commands.is_owner()
    async def admin_load(
        self,
        context: discord.ApplicationContext,
        extension: str,
    ) -> None:
        extension = extension.lower()

        try:
            self.bot.load_extension(f"cogs.{extension}")
        except discord.ExtensionNotFound:
            event = "not active."
        else:
            event = "loaded"

        content = f"{extension.capitalize()} extension {event}."
        await context.respond(content, ephemeral=True)
        print(content)

    @admin.command(
        name="reload",
        description="Reload an extension.",
    )
    @option(
        "extension",
        description="Select an extension.",
        choices=get_cog_choices(),
    )
    @commands.is_owner()
    async def admin_reload(
        self,
        context: discord.ApplicationContext,
        extension: str,
    ) -> None:
        extension = extension.lower()
        try:
            self.bot.unload_extension(f"cogs.{extension}")
            self.bot.load_extension(f"cogs.{extension}")
        except discord.ExtensionNotFound:
            event = "not active"
        except discord.ExtensionAlreadyLoaded:
            event = "already loaded"
        else:
            event = "reloaded"

        content = f"{extension.capitalize()} extension {event}."
        await context.respond(content, ephemeral=True)
        print(content)

    @admin.command(
        name="resize",
        description="Resize images.",
    )
    @option(
        "source",
        description="Choose a source folder by writing its path (eg. `./images/source`).",
    )
    @option(
        "extension",
        description='Choose a file extension (eg. `(".png")`).',
    )
    @option(
        "size",
        description="Choose the new size (eg. `100` for 100 x 100).",
    )
    @option(
        "destination",
        description="Choose a destination folder by writing its path (eg. `./images/destination`).",
    )
    @commands.is_owner()
    async def admin_resize(
        self,
        context: discord.ApplicationContext,
        source: str,
        extension: str,
        size: int,
        destination: str,
    ) -> None:
        for file in os.listdir(source):
            if file.lower().endswith(extension):
                path = f"{source}/{file}"
                with Image.open(path) as image:
                    image.thumbnail((size, size), Image.LANCZOS)
                    name = file.split(".")[0]
                    image.save(f"{destination}/{name}.png", "PNG")

        content = f"All `{extension}` images in `{source}` resized and saved in `{destination}`."
        await context.respond(content, ephemeral=True)
        print(content)

    @admin.command(
        name="unload",
        description="Unload an extension.",
    )
    @option(
        "extension",
        description="Select an extension.",
        choices=get_cog_choices(),
    )
    @commands.is_owner()
    async def admin_unload(
        self,
        context: discord.ApplicationContext,
        extension: str,
    ) -> None:
        extension = extension.lower()
        try:
            self.bot.unload_extension(f"cogs.{extension}")
        except discord.ExtensionNotFound:
            event = "not found"
        else:
            event = "unloaded"

        content = f"{extension.capitalize()} extension {event}."
        await context.respond(content, ephemeral=True)
        print(content)

    @admin.command(
        name="draft",
        description="Create draft layouts.",
    )
    @commands.is_owner()
    async def admin_draft(
        self,
        context: discord.ApplicationContext,
    ) -> None:
        # Size values for Hero borders.
        border_modifier = 5
        border_width = Draft.portrait_size[0] + border_modifier * 2
        border_height = Draft.portrait_size[1] + border_modifier * 2
        border_size = (border_width, border_height)

        async def draw_square(size: tuple) -> tuple[Image.Image, Image.Image]:
            portrait = Image.open("./draft/slots/none.png").convert("RGBA").resize(size)
            path = f"./draft/layouts/{layout.lower()}/layout-empty.png"
            image = Image.open(path).convert("RGBA")
            return portrait, image

        for layout in list(Draft.layouts.keys()):
            # Load smaller black squares.
            portrait, image = await draw_square(Draft.portrait_size)

            # Create internal grid.
            slot = 0
            while slot < 16:
                image.paste(portrait, Draft.layouts[layout][slot], portrait)
                path = f"./draft/layouts/{layout.lower()}/layout-internal.png"
                image.save(path, format="PNG")
                slot += 1

            # Prepare bigger black squares.
            portrait, image = await draw_square(border_size)

            # Create external grid.
            slot = 0
            while slot < 16:
                x = Draft.layouts[layout][slot][0] - border_modifier
                y = Draft.layouts[layout][slot][1] - border_modifier
                coordinates = (x, y)
                image.paste(portrait, coordinates, portrait)
                path = f"./draft/layouts/{layout.lower()}/layout-external.png"
                image.save(path, format="PNG")
                slot += 1

        content = "Draft layouts crafted."
        await context.respond(content, ephemeral=True)
        print(content)

    @admin.command(
        name="update",
        description="Update data in the database.",
    )
    @option(
        "table",
        description="Select a table to update.",
        choices=["Tooltips"],
    )
    @commands.is_owner()
    async def admin_update(
        self,
        context: discord.ApplicationContext,
        table: str,
    ) -> None:
        if table == "Tooltips":
            await Database.update_tooltips_and_keywords()

        content = f"{table} data updated."
        await context.respond(content, ephemeral=True)


def setup(bot: MyBot) -> None:
    bot.add_cog(Admin(bot))
