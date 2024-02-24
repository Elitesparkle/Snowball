from dataclasses import dataclass
import json

import configparser
import os
import pathlib

import dotenv  # pip install python-dotenv

# Load the author values from the "author.json" file.
with open("author.json", "r", encoding="utf-8") as file:
    authors = json.load(file)

# Load the environment variables from the ".env" file.
dotenv.load_dotenv()

# Load the configuration values from the "config.ini" file.
root = os.path.abspath(os.curdir)
path = pathlib.Path(root.replace(os.sep, "/") + "/config.ini")
config = configparser.ConfigParser()
config.read(path)


@dataclass
class BotSettings:
    debug_bot: int | None
    debug_servers: list[int]
    discord_bot_token: str
    official_server: str
    web_page: str


debug_bots = list(map(int, config["Debug Bot"].values()))

bot_settings = BotSettings(
    debug_bots[0] if len(debug_bots) > 0 else None,
    list(map(int, config["Debug Servers"].values())),
    str(os.getenv("DISCORD_BOT_TOKEN")),
    *list(map(str, config["Bot Resources"].values()))
)


@dataclass
class AIBuildSettings:
    allowed_servers: list[int]


ai_build_settings = AIBuildSettings(list(map(int, config["AI Servers"].values())))


@dataclass
class DraftSettings:
    actions_history: bool
    expiration_frequency: int
    expiration_notification: bool
    expiration_time: int
    alternative_layout_servers: list[int]
    self_drafters: list[int]


draft_settings = DraftSettings(
    config.getboolean("Draft Settings", "Actions_History"),
    3600 * int(config.get("Draft Settings", "Expiration_Frequency")),
    config.getboolean("Draft Settings", "Expiration_Notification"),
    3600 * int(config.get("Draft Settings", "Expiration_Time")),
    list(map(int, config["Odd Servers"].values())),
    list(map(int, config["Self Drafters"].values())),
)


@dataclass
class QuizSettings:
    offset_value: int


quiz_settings = QuizSettings(int(os.getenv("QUIZ_OFFSET_VALUE", "0")))
