import asyncio
import os

# py -m pip install py-cord
# py -m pip install --upgrade py-cord
import discord

from config import bot_settings
import database


class MyBot(discord.Bot):
    def __init__(
        self,
        activity: discord.Activity,
    ):
        self.admin: discord.User | None = None
        super().__init__(activity=activity)

    async def my_fetch_user(
        self,
        user_id: int,
    ) -> discord.User | None:
        try:
            user = await self.fetch_user(user_id)
        except (
            discord.NotFound,
            discord.HTTPException,
        ):
            user = None
        return user

    async def my_is_owner(
        self,
        user_id: int,
    ) -> bool:
        user = await self.my_fetch_user(user_id)
        is_owner = await self.is_owner(user) if user is not None else False
        return is_owner


# Configure the activity that will be shown for the bot's user.
activity = discord.Activity(
    name="Heroes of the Storm",
    type=discord.ActivityType.playing,
)

# Configure the bot.
bot = MyBot(activity=activity)


def load_extensions() -> None:
    # Load all cogs/extensions.
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            bot.load_extension(f"cogs.{file[:-3]}")


@bot.event
async def on_connect() -> None:
    bot_name = bot.user.name if bot.user is not None else "Bot"

    # Due to overriding `on_connect()`, we need to call `sync_commands()`.
    if bot.auto_sync_commands:

        # Check if the debug bot, set in `config.ini`, is being used.
        if (
            bot.user is not None
            and bot_settings.debug_bot is not None
            and bot.user.id == bot_settings.debug_bot
        ):
            debug_servers = bot_settings.debug_servers
            print("Debug mode: Slash Commands are registered instantly.")
        else:
            debug_servers = None
            print("Release mode: Slash Commands may take up to an hour to register.")

        try:
            await bot.sync_commands(guild_ids=debug_servers)
        except discord.errors.Forbidden:
            print("No access to some servers listed in the configuration file.")

    print(f"{bot_name} connected.")


@bot.event
async def on_ready() -> None:
    app = await bot.application_info()

    # Check if the bot has a team and store ownership data accordingly.
    if app.team:
        bot.owner_ids = {member.id for member in app.team.members}
    else:
        bot.owner_id = app.owner.id

    # Store the data of the main bot's owner for later usage.
    bot.admin = await bot.fetch_user(app.owner.id)

    # Print the username of the bot, to show which account is being used.
    bot_name = bot.user.name if bot.user is not None else "Bot"
    print(f"{bot_name} ready.")


def main() -> None:
    # Print a welcome message, to notifiy the file is running.
    print("Rise and shine, sleepy head!")

    # Start a loop usable to run asyncronous functions.
    loop = asyncio.new_event_loop()

    # Connect to and load the database.
    loop.run_until_complete(database.main())

    # Load all cogs/extensions.
    load_extensions()

    # Run the bot by using the token stored in the ".env" file.
    bot.run(bot_settings.discord_bot_token)


if __name__ == "__main__":
    main()
