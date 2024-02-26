import json
import random
import secrets

import discord
from discord import option
from discord.ext import commands

from config import quiz_settings
from main import MyBot
from tools.hero import Hero
from tools.misc import Misc


class Quiz(commands.Cog):

    categories = [
        "Talent → Hero",
        "Ability → Cooldown",
    ]

    questions = [
        "Who has a Talent named `{talent}`?",
        "What is the cooldown of `{ability}`?",
    ]

    tiers = [
        1,
        4,
        7,
        10,
        13,
        16,
        20,
    ]

    def __init__(
        self,
        bot: MyBot,
    ) -> None:
        self.bot: MyBot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.add_view(self.QuizView(self.bot))
        print("Draft extension loaded.")

    class QuizView(discord.ui.View):
        def __init__(
            self,
            bot: MyBot,
        ) -> None:
            self.bot: MyBot = bot
            super().__init__(timeout=None)

        @discord.ui.button(
            custom_id="Quiz¦Option A",
            style=discord.ButtonStyle.blurple,
        )
        async def option_a(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            self.disable_all_items()
            await self.on_interaction(button, interaction)

            event = f"{button.label} selected."
            Misc.send_log(interaction, event)

        @discord.ui.button(
            custom_id="Quiz¦Option B",
            style=discord.ButtonStyle.blurple,
        )
        async def option_b(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            self.disable_all_items()
            await self.on_interaction(button, interaction)

            event = f"{button.label} selected."
            Misc.send_log(interaction, event)

        @discord.ui.button(
            custom_id="Quiz¦Option C",
            style=discord.ButtonStyle.blurple,
        )
        async def option_c(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:
            self.disable_all_items()
            await self.on_interaction(button, interaction)

            event = f"{button.label} selected."
            Misc.send_log(interaction, event)

        async def on_interaction(
            self,
            button: discord.ui.Button,
            interaction: discord.Interaction,
        ) -> None:

            # Check if it's a URL button.
            if button.custom_id is None:
                return

            split = button.custom_id.split("¦")
            answers = split[1].split("|")
            selection_id = int(split[2]) - quiz_settings.offset_value
            solution_id = int(split[3]) - quiz_settings.offset_value * 2

            encoded_solution = str(solution_id + quiz_settings.offset_value * 2)
            for child in self.children:
                index = self.children.index(child)
                encoded_index = str(index + quiz_settings.offset_value)

                if isinstance(child, discord.ui.Button):
                    if index == selection_id:
                        if selection_id == solution_id:
                            child.style = discord.ButtonStyle.green
                        else:
                            child.style = discord.ButtonStyle.red
                    else:
                        child.style = discord.ButtonStyle.blurple

                    child.label = str(answers[index])
                    child.custom_id = f"Quiz¦{answers[0]}|{answers[1]}|{answers[2]}¦{encoded_index}¦{encoded_solution}"

            await interaction.response.edit_message(view=self)

    @commands.slash_command(
        name="quiz",
        description="Get a random question to test your game knowledge.",
    )
    @option(
        "category",
        description="Select a type of question.",
        default=None,
        choices=categories,
    )
    async def quiz(
        self,
        context: discord.ApplicationContext,
        category: str,
    ) -> None:
        # If a category has not been selected, randomly choose one.
        if category is None:
            question_id = secrets.randbelow(len(self.questions))
        else:
            question_id = self.categories.index(category)

        if question_id == 0:
            hero = await Hero.random()
            solution = hero

            try:
                hero = await Hero.fix_name(hero)
            except TypeError:
                event = "Hero not valid."
                print(event)
                return

            hero_code = Hero.get_code(hero, "Blizzard")
            with open(
                f"./data/heroes/{hero_code}.json",
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            tier = self.tiers[secrets.randbelow(7)]
            talent = random.choice(data["talents"][str(tier)])
            assert isinstance(talent, dict)

            name = talent.get("name")
            content = self.questions[question_id].format(talent=name)

            heroes = await Hero.catalog()
            heroes.remove(hero)
            random.shuffle(heroes)

            answers = []
            for entry in heroes:
                try:
                    hero = await Hero.fix_name(hero)
                except TypeError:
                    event = "Hero not valid."
                    print(event)
                    return

                hero_code = Hero.get_code(hero, "Blizzard")
                with open(
                    f"./data/heroes/{hero_code}.json",
                    "r",
                    encoding="utf-8",
                ) as file:
                    data = json.load(file)
                assert isinstance(data, dict)

                talents = data.get("talents")
                assert talents is not None

                for tier in talents:
                    for talent in tier:
                        if talent == name:
                            break

                answers.append(entry)
                if len(answers) == 2:
                    break

            answers.append(solution)
            random.shuffle(answers)
            solution_id = answers.index(solution)

        elif question_id == 1:
            while True:
                hero = await Hero.random()

                try:
                    hero = await Hero.fix_name(hero)
                except TypeError:
                    event = "Hero not valid."
                    print(event)
                    return

                hero_code = Hero.get_code(hero, "Blizzard")
                with open(
                    f"./data/heroes/{hero_code}.json",
                    "r",
                    encoding="utf-8",
                ) as file:
                    data = json.load(file)
                assert isinstance(data, dict)

                hero_code = data.get("hyperlinkId")
                ability = random.choice(data["abilities"][hero_code])

                assert isinstance(ability, dict)
                ability_name = ability.get("name")
                cooldown = ability.get("cooldown")

                if cooldown is not None:
                    cooldown = int(cooldown)
                    break

            content = self.questions[question_id].format(
                ability=ability_name,
                hero=hero_code,
            )

            answers = []
            answers.append(cooldown)
            layout = secrets.randbelow(3)

            if cooldown >= 80:
                delta = 10
            elif cooldown >= 20:
                delta = 5
            else:
                delta = 1

            answers.append(cooldown + delta)
            if layout == 0:
                answers.append(cooldown + delta * 2)
            elif layout == 1:
                answers.append(cooldown - delta * 2)
            elif layout == 2:
                answers.append(cooldown - delta)

            random.shuffle(answers)
            solution_id = answers.index(cooldown)

        view = self.QuizView(self.bot)
        encoded_solution = str(solution_id + quiz_settings.offset_value * 2)
        for child in view.children:
            index = view.children.index(child)
            encoded_index = str(index + quiz_settings.offset_value)

            if isinstance(child, discord.ui.Button):
                child.label = str(answers[index])
                child.custom_id = f"Quiz¦{answers[0]}|{answers[1]}|{answers[2]}¦{encoded_index}¦{encoded_solution}"

        await context.respond(content, view=view)


def setup(bot: MyBot) -> None:
    bot.add_cog(Quiz(bot))
