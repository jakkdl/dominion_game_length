"""Command class system inspired by incnone's necrobot.
"""
from __future__ import annotations

import itertools
import datetime
#import asyncio
from enum import Enum, auto
import typing
from typing import Optional, List, Any, Sequence
from dataclasses import dataclass

import discord  # type: ignore

import seat_strings
import seat_typing
from seat_typing import GameState
from database import database

#if typing.TYPE_CHECKING:
#    # pylint: disable=cyclic-import
#    import discord_game
#    from discord_game import DiscordGame
#    GameDict = typing.Dict[discord.TextChannel, DiscordGame]
## from player_game import Findable, Player, Proposal


OPTIONAL_STR = "Brackets around an argument means that it's optional."
REVEAL_TIME = 5


class CommandException(seat_typing.SeatException):
    def __init__(self, command: typing.Union[CommandType, CommandMessage],
                 message: str):
        super().__init__('Error running `{}`: {}'.format(
            command, message))


class ArgType:
    def __init__(self, arg_type: type,
                 optional: bool = False,
                 defaultvalue: Any = None,
                 name: Optional[str] = None) -> None:
        self.arg_type: type = arg_type
        self.optional: bool = optional
        self.defaultvalue: Any = defaultvalue
        self.name = name

    def __str__(self) -> str:
        if self.name is not None:
            name: str = self.name
        else:
            name = self.arg_type.__name__

        if self.optional:
            return '[{}]'.format(name)
        return name

    def convert(self, arg: str, **kwargs: Any) -> Any:
        if arg == '' and self.optional:
            return self.defaultvalue

        if issubclass(self.arg_type, seat_typing.Findable):
            return self.arg_type.find(arg, **kwargs)

        # Gives "Too many arguments for "object" without cast
        return typing.cast(type, self.arg_type)(arg)


class CommandMessage:
    """Wrapper for discord.message"""
    def __init__(self, message: discord.message,
                 channel: seat_typing.SeatChannel,
                 author: seat_typing.DiscordUser) -> None:
        self._message = message

        self.author: seat_typing.DiscordUser = author
        self.channel = channel
        self.command: str = message.content.split(' ')[0][1:]
        self.args: List[Any] = message.content.split(' ')[1:]

    def __str__(self) -> str:
        return self.command

    def convert_arguments(self,
                          arg_types: Sequence[ArgType],
                          **kwargs: Any,
                          ) -> typing.List[typing.Any]:
        if len(self.args) > len(arg_types):
            raise CommandException(self, 'Too many arguments.')

        if len(self.args) < len([x for x in arg_types if not x.optional]):
            raise CommandException(self, 'Too few arguments.')

        new_args: List[Any] = []
        for arg, arg_type in itertools.zip_longest(
                self.args, arg_types, fillvalue=''):
            try:
                new_args.append(arg_type.convert(arg, **kwargs))

            except ValueError as exception:
                raise CommandException(self, 'Invalid type for argument {}. '
                                       'Not convertible to {}'.format(
                                           arg, arg_type)) from exception
        return new_args


def format_list_with_conjunction_and_comma(sequence: typing.Iterable[Any],
                                           conjunction: str) -> str:
    if not sequence:
        raise NotImplementedError('Empty list.')

    res = ''
    str_sequence = list(map(str, sequence))

    for seq in str_sequence[:-2]:
        res += seq + ', '

    if len(str_sequence) > 1:
        res += '{} {} '.format(str_sequence[-2], conjunction)

    return res + str_sequence[-1]


@dataclass
class Requirements:
    public_only: bool = False
    private_only: bool = False
    admin_only: bool = False
    not_active_player: bool = False

    # implies game_only
    valid_game_states: typing.Iterable[GameState] = GameState
    player_only: bool = False

    def human_readable(self) -> List[str]:
        result = []
        if self.public_only:
            result.append('in a public channel')
        if self.private_only:
            result.append('in a private channel')
        if self.admin_only:
            result.append("you're an admin")
        if self.not_active_player:
            result.append("you're not a player in an active game")
        if self.player_only:
            result.append('there is a valid game')
        if self.player_only:
            result.append("you're a player in that game")
        if self.valid_game_states != GameState:
            result.append(
                'the game is {}.'.format(
                    format_list_with_conjunction_and_comma(
                        self.valid_game_states, 'or')))
        return result


class CommandTag(Enum):
    INFO = auto()
    MANAGEMENT = auto()
    GAMEPLAY = auto()
    OPTIONS = auto()
    REALLIFE = auto()
    ADMIN = auto()


class CommandType():
    def __init__(self,
                 command_name: str,
                 *command_names: str,
                 requirements: Requirements = Requirements(),
                 args: Sequence[ArgType] = (),
                 help_text: str = 'This command has no help text.',
                 tag: CommandTag
                 ) -> None:
        self.command_name_list = (command_name,) + command_names
        self.requirements = requirements
        self.args = args
        self.help_text = help_text
        self.tag = tag

    def __str__(self) -> str:
        return str(self.command_name)

    @property
    def command_name(self) -> str:
        return self.command_name_list[0]

    @property
    def help(self) -> str:
        return '```{name}\n{arg_format}\n{help_text}```'.format(
            name=self.command_name,
            arg_format=self.arg_format,
            help_text=self.help_text)

    @property
    def arg_format(self) -> str:
        return '!{}{}'.format(
            self.command_name,
            ''.join(' '+str(arg) for arg in self.args))

    @property
    def player_only(self) -> bool:
        return self.requirements.player_only

    def _validate_channel(self,
                          channel: seat_typing.SeatChannel) -> None:
        # channel can also be group dm
        if self.requirements.public_only and not channel.is_public:
            raise CommandException(self, 'Not a public channel.')
        if (self.requirements.private_only and not channel.is_dm):
            raise CommandException(self, 'Not a private channel.')

    def matches(self, key: str) -> bool:
        return key in self.command_name_list

    async def execute(self, command: CommandMessage) -> None:
        if self.requirements.admin_only and not command.author.is_admin:
            raise CommandException(self,
                                   'Called by non-admin {}'.format(
                                       command.author.display_name))

        self._validate_channel(command.channel)

        await self._do_execute(command)
        return


    def _validate_game_state(self, state: GameState) -> None:
        if state not in self.requirements.valid_game_states:
            raise CommandException(self, 'Invalid game state.')

    async def _do_execute(self, command: CommandMessage) -> None:
        raise NotImplementedError(
            '{}: Called do_execute in the abstract '
            'base class.'.format(command.command))



# General commands
class Help(CommandType):
    def __init__(self,
                 command_dict: typing.Dict[str, typing.List[CommandType]]
                 ) -> None:

        help_text = (
            'DM a help text, optionally for a specified command.\n'
            'Some commands are callable by several different aliases, these '
            'will all be listed when running help on either of them (for '
            'example, this command is also known as `info`).\n'
            'In the "Usage" line some parameters may be written with '
            'brackets. This means they are optional and can be left out. '
            'The help text will often explain what is the difference between '
            'specifying the parameter and not.\n'
        )
        args = (ArgType(str, optional=True, name='command'),)
        super().__init__('help', 'info',
                         args=args,
                         help_text=help_text,
                         tag=CommandTag.INFO)
        self.command_dict = command_dict

    async def _do_execute(self, command: CommandMessage) -> None:
        user_channel = await seat_typing.SeatChannel.from_user(command.author)
        if not command.channel.is_dm:
            await command.channel.send('Help text sent via DM.')

        key: Optional[str] = command.convert_arguments(self.args)[0]

        print('{} called help {}'.format(command.author, key))

        if not key:
            await user_channel.send(seat_strings.HELP_HELP)
            return

        key = key.lower().lstrip('!').rstrip('.')

        if key not in self.command_dict:
            raise CommandException(
                self, 'Cannot find help for unknown command `{}`.'.format(
                    command.args[0]))

        full_text = ''

        if len(self.command_dict[key]) > 1:
            full_text = 'Found {} commands matching {}.\n'.format(
                len(self.command_dict[key]), key)

        for help_cmd in self.command_dict[key]:
            full_text += 'Help for `{}`:\n'.format(
                '`, `'.join(str(cmd) for cmd in help_cmd.command_name_list))

            full_text += '  {}\n'.format(
                help_cmd.help_text.replace('\n', '\n  '))

            full_text += '  Usage: `{}`\n'.format(help_cmd.arg_format)
            reqs_readable = help_cmd.requirements.human_readable()
            if reqs_readable:
                full_text += '  Can only be run if {}\n'.format(
                    format_list_with_conjunction_and_comma(
                        reqs_readable, 'and'))

        await user_channel.send(full_text)



class Commands(CommandType):
    def __init__(self, commands: Sequence[CommandType]) -> None:
        self.commands = commands
        help_text = 'Print list of available commands'
        requirements = Requirements(private_only=True)
        # TODO: Split into Commands, GameCommands,
        # AdminCommands (PlayerCommands?)
        super().__init__('commands', 'command',
                         help_text=help_text,
                         requirements=requirements,
                         tag=CommandTag.INFO)

    async def _do_execute(self, command: CommandMessage) -> None:
        await command.author.send(
            ' '.join('`!' + str(x) + '`' for x in self.commands))
        # TODO do it like rules


class Source(CommandType):
    def __init__(self) -> None:
        help_text = 'Prints the URL to the source code.'
        super().__init__('source', 'sourcecode', 'code',
                         help_text=help_text,
                         tag=CommandTag.INFO)

    async def _do_execute(self, command: CommandMessage) -> None:
        await command.channel.send(
            'https://github.com/h00701350103/seat_exchange')

def parse_matches_message(message: discord.message, verbose: bool = False) -> int:
    if verbose:
        print(f'parsing matches message: {message.id}')
    if str(message.author) != 'Upcoming Matches#0000':
        if verbose:
            print('wrong author')
        return 0
    embed = message.embeds[0]
    if embed.title != 'Starting Now':
        if verbose:
            print('wrong title')
        return 0

    added = 0
    for field in embed.fields:
        if 'League' not in field.name:
            if verbose:
                print('not a league game')
            continue
        if field.name.split(':')[0].split(' ')[0] != 'League':
            if verbose:
                print('not a league game')
            continue

        timestamp = message.created_at + datetime.timedelta(minutes=1)

        try:
            players = tuple(field.name.split(':')[1].strip().split(' vs. '))
            players = typing.cast(typing.Tuple[str, str], players)
        except IndexError:
            print(f'Failed to parse {field.name}')
            continue

        if database.add_match(players, timestamp, verbose):
            added += 1
    return added

def parse_results_message(message: discord.message, verbose: bool = False) -> bool:
    if verbose:
        print(f'parsing results message: {message.id}')
    if str(message.author) != 'League Results#0000':
        return False
    embed = message.embeds[0]
    division = embed.title.split(' ')[-1]
    timestamp = message.created_at

    try:
        ppb = embed.fields[0].name.split(' - ')
        ppbs = [pp.strip().split(' ') for pp in ppb]

        games = int(float(ppbs[0][-1]) + float(ppbs[1][0]))
        players = ' '.join(ppbs[0][:-1]), ' '.join(ppbs[1][1:])

        return database.add_results(players, timestamp, games, division)
    except ValueError:
        print(f'failed to parse {embed.fields[0].name}')
    return False

class Update(CommandType):
    def __init__(self, client: discord.Client):
        help_text = ('Goes through the specified date range and adds all matches to the database.')
        requirements = Requirements(admin_only=True)
        args = (ArgType(int, optional=True, name='after'),
                ArgType(int, optional=True, name='before'),
                ArgType(str, optional=True, name='verbosity',
                    defaultvalue='quiet'),
                )
        super().__init__('update',
                         args=args,
                         requirements=requirements,
                         help_text=help_text,
                         tag=CommandTag.ADMIN)
        self.client = client

    async def _do_execute(self, command: CommandMessage) -> None:
        after_utc: Optional[int]
        before_utc: Optional[int]
        after: datetime.datetime
        before: datetime.datetime
        verbosity : str


        after_utc, before_utc, verbosity = command.convert_arguments(
            self.args)

        verbose = verbosity == 'verbose'

        if not after_utc:
            after = datetime.datetime.now() - datetime.timedelta(days=1)
        else:
            after = datetime.datetime.fromtimestamp(after_utc)
        if not before_utc:
            before = datetime.datetime.now()
        else:
            before = datetime.datetime.fromtimestamp(before_utc)

        matches_parsed, results_parsed = 0, 0

        for guild in self.client.guilds:
            for channel in guild.channels:
                if channel.name == 'matches':
                    async for message in channel.history(
                            after=after,
                            before=before,
                            limit=None):
                        if parse_matches_message(message, verbose):
                            matches_parsed += 1
                if channel.name == 'results':
                    async for message in channel.history(
                            after=after,
                            before=before,
                            limit=None):
                        if parse_results_message(message, verbose):
                            results_parsed += 1
        await command.author.send(f'added {matches_parsed} matches and {results_parsed} results')


class PrintMatches(CommandType):
    def __init__(self):
        requirements = Requirements(admin_only=True)
        args = (ArgType(str, optional=True, name='target', defaultvalue='tty'),
                ArgType(str, name='data', optional=True, defaultvalue='all'),
                )
        super().__init__('printmatches', 'print',
                         requirements=requirements,
                         args=args,
                         tag=CommandTag.ADMIN)

    async def _do_execute(self, command: CommandMessage) -> None:
        target : str
        data : str
        target, data = command.convert_arguments(self.args)

        if target == 'tty':
            database.print_matches(data)
            await command.author.send('printed to tty')
        elif target == 'file':
            database.export_matches()
            await command.author.send('printed to file')
        else:
            await command.author.send(f'invalid printing target: {target}')

class Pickle(CommandType):
    def __init__(self):
        requirements = Requirements(admin_only=True)
        args = (
                ArgType(str, name='action'),
                ArgType(str, name='data', optional=True, defaultvalue='all'),
                )
        super().__init__('pickle',
                         requirements=requirements,
                         args=args,
                         tag=CommandTag.ADMIN)

    async def _do_execute(self, command: CommandMessage) -> None:
        action : str
        data : str

        action, data = command.convert_arguments(
            self.args)

        if action == 'load':
            database.load(data)
        elif action == 'save':
            database.save(data)
        elif action == 'wipe':
            database.wipe(data)
        else:
            await command.author.send(f'invalid action: {action}')
            return

        await command.author.send(f'executed {action} on {data}')



# Admin commands
class Shutdown(CommandType):
    def __init__(self, client: discord.Client):
        help_text = ('Turns off the bot.')
        requirements = Requirements(admin_only=True)
        super().__init__('shutdown', 'forcequit',
                         requirements=requirements,
                         help_text=help_text,
                         tag=CommandTag.ADMIN)
        self.client = client

    async def _do_execute(self, command: CommandMessage) -> None:
        await command.channel.wait_send('Shutting down.')
        await self.client.close()
