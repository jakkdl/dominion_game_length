#!env/bin/python3
import pickle
import pprint
from typing import List

from seat_typing import Result

def load_data(filename):
    with open(filename, 'rb') as file:
        return pickle.load(file)

def load_matches() -> List[Result]:
    return sum(load_data('matches.pickle').values(), [])

def format_duration(duration: float, decimal_seconds = False) -> str:
    hours = int(duration // 3600)
    minutes = int((duration % 3600 ) // 60)

    if decimal_seconds:
        seconds = duration % 60
    else:
        seconds = round(duration % 60)

    if duration > 3600:
        return f'{hours}h{minutes:02}m'
    if duration > 60:
        return f'{minutes}m{seconds:02}s'
    return f'{seconds}s'

def format_basic_stats(source: str, time: int, games: int):
    return f'{source}: {format_duration(time/games)} across {games} games'

def player_stats(player: str, matches) -> str:
    def comparator(result: Result):
        return player in map(lambda x: x.lower(), result.players)

    filtered = tuple(filter(comparator, matches))
    time = sum((m.duration for m in filtered))
    games = sum((m.game_count for m in filtered))

    pprint.pprint(filtered)

    return format_basic_stats(player, time, games)

def main(matches : List[Result]):

    total_time = sum((m.duration for m in matches))
    total_games = sum((m.game_count for m in matches))

    print(f'Total games: {total_games}')
    print(f'Total average: {format_duration(total_time/total_games)}')

    print('Averages by tier:')
    for tier in (chr(x) for x in range(65, 75)):
        time = sum((m.duration for m in matches if tier in m.division))
        games = sum((m.game_count for m in matches if tier in m.division))
        print('\t', format_basic_stats(tier, time, games))

    print('Average by game count:')
    for count in range(1, 7):
        time = sum((m.duration for m in matches if m.game_count == count))
        games = sum((m.game_count for m in matches if m.game_count == count))
        if not games:
            continue
        print('\t', format_basic_stats(str(count), time, games))

def mainmain():
    matches = load_matches()
    main(matches)
    print(player_stats('jakkdl', matches))

if __name__ == '__main__':
    mainmain()
