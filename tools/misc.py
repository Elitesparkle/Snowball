import discord
from unidecode import unidecode  # pip install unidecode


class Misc:

    @staticmethod
    def display_time(
        seconds: int,
        granularity: int = 2,
    ) -> str:
        intervals = (
            ("weeks", 604800),
            ("days", 86400),
            ("hours", 3600),
            ("minutes", 60),
            ("seconds", 1),
        )

        result = []
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip("s")
                result.append(f"{value} {name}")

        time = ", ".join(result[:granularity])
        return time

    @staticmethod
    def alpha_unidecode_lower(string: str) -> str:
        # Process the string:
        # 1. Remove non-alphanumeric characters.
        # 2. Convert from Unicode to ASCII equivalent.
        # 3. Convert from uppercase to lowercase.
        return unidecode("".join(filter(str.isalpha, string))).lower()

    @staticmethod
    def send_log(
        context: discord.ApplicationContext | discord.Interaction,
        event: str,
    ) -> None:
        if context.guild is None:
            channel_info = f"private messages with {context.user}"
        else:
            guild_name = unidecode(context.guild.name)
            channel_name = (
                unidecode(context.channel.name)
                if isinstance(context.channel, discord.abc.GuildChannel)
                else ""
            )
            channel_info = f"{guild_name} ({context.guild_id}) \
                #{channel_name} ({context.channel_id})"

        log = f"{event[:-1]} in {channel_info}."
        print(log)

    @staticmethod
    def decapitalize(string: str):
        return string[:1].lower() + string[1:]
