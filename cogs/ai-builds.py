import json
import os
import re
import shutil
import xml.dom.minidom as minidom
import zipfile

import discord
from discord.ext import commands

from config import ai_build_settings
from main import MyBot
from tools.hero import Hero
from tools.misc import Misc


class AIBuilds(commands.Cog):

    ai = discord.SlashCommandGroup(
        name="ai",
        description="AI configuration for offline games.",
        guild_ids=ai_build_settings.allowed_servers,
    )

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("AI Build extension loaded.")

    @staticmethod
    async def fix_build_code(
        context: discord.ApplicationContext,
        build_code: str,
    ) -> str | None:
        build_search = re.search(
            r"\[T\d{7}\,[úa-z\s\.\-\']+]",
            build_code,
            re.IGNORECASE,
        )

        if build_search is None:
            event = "Build Code not valid."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            return

        build_code = build_search.group(0)  # Extract "[T<Build>,<Hero>]"

        hero = build_code[10:-1]
        hero = await Hero.fix_name(hero)

        if hero is None:
            event = "Hero not valid."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            return

        return build_code.replace(build_code[10:-1], hero)

    @staticmethod
    async def craft_xml(
        context: discord.ApplicationContext,
        build_code: str,
        player_id: int,
    ) -> tuple[str, str] | None:

        hero = build_code[10:-1]
        hero_code = Hero.get_code(hero, "Blizzard")
        file = f"{hero_code}.json"
        with open(
            f"./data/heroes/{file}",
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        selected_sorts = [int(number) for number in build_code[2:9]]
        selected_talents = []

        tiers = [
            "1",
            "4",
            "7",
            "10",
            "13",
            "16",
            "20",
        ]
        for index, tier in enumerate(tiers):
            for talent in data["talents"][tier]:
                if talent["sort"] == selected_sorts[index]:
                    selected_talents.append(talent["talentTreeId"])

        talents_count = len(selected_talents)
        if talents_count != 7:
            if talents_count < 7:
                event = "Not enough Talents selected."
            else:
                event = "Too many Talents selected."

            await context.respond(content=event, ephemeral=True)
            Misc.send_log(context, event)

            return

        internal_hero_id = data["cHeroId"]

        indentation = "    " * 3
        talents = [
            f"""<TalentsArray index="{talent_index}" value="{selected_talents[talent_index]}" />"""
            for talent_index in range(7)
        ]
        talents_block = f"\n{indentation}".join(talents)

        text = f"""
            <?xml version="1.0" encoding="us-ascii"?>
                <Catalog>
                    <CButton id="Player{player_id}Hero">
                        <Icon value="{internal_hero_id}" />
                    </CButton>
                    <CHero id="{internal_hero_id}">
                        <TalentAIBuildsArray index="0" ChanceToPick="100">
                            {talents_block}
                        </TalentAIBuildsArray>
                        <TalentAIBuildsArray index="1" ChanceToPick="0" />
                        <TalentAIBuildsArray index="2" ChanceToPick="0" />
                        <TalentAIBuildsArray index="3" ChanceToPick="0" />
                        <TalentAIBuildsArray index="4" ChanceToPick="0" />
                        <TalentAIBuildsArray index="5" ChanceToPick="0" />
                    </CHero>
                </Catalog>
            """.strip()

        # Remove leading and trailing whitespace for each line.
        text = "".join([line.strip() for line in text.splitlines()])

        # Indent XML.
        dom = minidom.parseString(text)
        xml = dom.toprettyxml(
            indent=" " * 4,
            encoding="us-ascii",
        ).decode("us-ascii")
        return xml, hero

    class AIBuildsModal(discord.ui.Modal):
        def __init__(
            self,
            context: discord.ApplicationContext,
            *args,
            **kwargs,
        ) -> None:
            super().__init__(*args, **kwargs)
            self.context: discord.ApplicationContext = context

            self.add_item(
                discord.ui.InputText(
                    label=f"Build Codes",
                    value="1. [T1231231,Abathur]\n[T1231231,TLV]\n10. [T1231231,Zera]",
                    style=discord.InputTextStyle.long,
                    max_length=288,
                    required=True,
                )
            )

        async def callback(
            self,
            interaction: discord.Interaction,
        ) -> None:
            input_string = self.children[0].value

            assert input_string is not None
            input_rows = input_string.split("\n")

            assert interaction.user is not None
            folder = f"./temp/{interaction.user.id}/"

            try:
                os.makedirs(folder)
            except FileExistsError:
                shutil.rmtree(folder)
                os.makedirs(folder)

            for file in os.listdir(folder):
                if file.endswith(".xml"):
                    os.remove(folder + file)

            embed = discord.Embed(
                title="AI Builds",
                description="Builds for AI players in offline games.\nMaps for using them can be found [here](https://github.com/spazzo966/HeroesAITalentBuilds).",
                color=discord.Color.blue(),
            )

            for index, input_row in enumerate(input_rows[:10], start=1):
                player_id, build_code = input_row.split(". ")
                try:
                    player_id = int(player_id)
                except ValueError:
                    player_id = index
                    build_code = input_row
                else:
                    if player_id not in range(1, 11):
                        player_id = index

                build_code = await AIBuilds.fix_build_code(self.context, build_code)

                assert build_code is not None
                craft = await AIBuilds.craft_xml(self.context, build_code, player_id)
                if craft is None:
                    return

                xml, hero = craft

                build = "-".join(list(build_code[2:9])).replace("0", "x")
                hero_code = Hero.get_code(hero, "Psionic Storm")
                link = f"https://psionic-storm.com/en/talent-calculator/{hero_code}/#talents={build}"

                team = "Red Team" if int(player_id) > 5 else "Blue Team"
                embed.add_field(
                    name=f"Player {player_id} ({team})",
                    value=f"[{build_code}]({link})",
                    inline=False,
                )

                filename = f"Player{player_id}Data.xml"
                with open(
                    f"{folder}/{filename}",
                    "w",
                    encoding="us-ascii",
                ) as file:
                    file.write(xml)

                event = f"AI Build for {hero} created."
                Misc.send_log(self.context, event=event)

            if len(input_rows) > 1:

                def zipdir(path, ziph):
                    for root, _, files in os.walk(path):
                        for file in files:
                            ziph.write(
                                os.path.join(root, file),
                                os.path.relpath(
                                    os.path.join(root, file), os.path.join(path, "..")
                                ),
                            )

                filename = f"{interaction.user.id}.zip"
                path = f"./temp/{filename}"
                with zipfile.ZipFile(
                    path,
                    "w",
                    zipfile.ZIP_DEFLATED,
                ) as zipf:
                    zipdir(folder, zipf)

                file = discord.File(path, "AIBuilds.zip")

                # Delete temporary files and folders.
                shutil.rmtree(folder)
            else:
                xml_file = None
                for file in os.listdir(folder):
                    if file.endswith(".xml"):
                        path = folder + file
                        xml_file = discord.File(path, filename)
                        break

            assert xml_file is not None
            await interaction.response.send_message(embed=embed, file=xml_file)

            # Delete temporary files after being sent.
            os.remove(path)

    @ai.command(
        name="builds",
        description="Create new Builds for AI.",
    )
    async def ai_builds(
        self,
        context: discord.ApplicationContext,
    ) -> None:
        modal = self.AIBuildsModal(context=context, title="AI Builds")
        await context.send_modal(modal)


def setup(bot: MyBot) -> None:
    bot.add_cog(AIBuilds(bot))
