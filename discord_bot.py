#!env/bin/python3
# pragma pylint: disable=missing-docstring
from typing import Dict, List
import datetime

import discord  # type: ignore

import discord_commands as commands

from seat_typing import SeatException, SeatChannel, DiscordUser


class DiscordBotException(SeatException):
    pass


class DiscordBot(discord.Client):  # type: ignore
    def __init__(self) -> None:
        super().__init__()

        self.command_list: List[commands.CommandType] = []
        self.command_dict: Dict[str, List[commands.CommandType]] = {}

        self._initialize_commands()

    def _initialize_commands(self) -> None:
        self.command_list += [
            # General info
            commands.Help(self.command_dict),
            commands.Commands(self.command_list),
            commands.Source(),

            commands.PlayerStats(),
            commands.PrintMatches(),
            commands.Pickle(),

            commands.Update(self),
            commands.Shutdown(self),
        ]

        for command in self.command_list:
            for command_name in command.command_name_list:
                if command_name not in self.command_dict:
                    self.command_dict[command_name] = [command]
                else:
                    self.command_dict[command_name].append(command)

    async def on_ready(self) -> None:
        print(f'Logged in as {self.user} at {datetime.datetime.now()}')
        # for guild in self.guilds:
        #     for channel in guild.channels:
        #         if channel.name == 'testing':
        #             await channel.send('Seat Exchange Bot v0.1')

    async def on_message(self, message: discord.message) -> None:
        """
        If message from:
            admin, run command. (update, etc)
            user, run usercommand (help, query user, graphs?)
            DomBot in #matches, check if "Starting Now" - log division, players, time.
            League Results in #results, if we find a matching start,
                log players, division, duration, game count.

        """
        async def run_command(command_list: List[commands.CommandType],
                              command_message: commands.CommandMessage
                              ) -> None:
            errors = []
            for matching_command in command_list:
                try:
                    await matching_command.execute(command_message)
                    return
                except SeatException as error:
                    errors.append(error)
            print(errors)
            await command_message.channel.send(
                '\n'.join(str(x) for x in errors))

        if message.author == self.user:
            return

        if isinstance(message.channel, discord.channel.TextChannel):
            if message.channel.name == 'matches':
                commands.parse_matches_message(message)
                return
            if message.channel.name == 'results':
                commands.parse_results_message(message)
                return

        if not message.channel.type == discord.ChannelType.private:
            return

        if not message.content.startswith('!'):
            return

        command = message.content.split(' ')[0][1:]
        channel = SeatChannel(message.channel)
        user = DiscordUser(message.author)

        # parameters = message.content.split(' ')[1:]
        command_message = commands.CommandMessage(
            message, channel, user)

        if command in self.command_dict:
            await run_command(self.command_dict[command], command_message)

def _main() -> None:
    with open('discord_token', encoding='utf-8') as file:
        token = file.read().strip()

    bot = DiscordBot()
    bot.run(token)


if __name__ == '__main__':
    _main()
