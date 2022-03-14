#!env/bin/python3
import pickle
import statistics
#import pprint
from typing import List,Dict

import numpy #type: ignore
from matplotlib import pyplot

from seat_typing import Result, Players

CACHED_AVERAGES = {}
def load_data(filename: str) -> Dict[Players, List[Result]]:
    with open(filename, 'rb') as file:
        return pickle.load(file) #type: ignore

def load_matches() -> List[Result]:
    return sum(load_data('matches.pickle').values(), [])

def format_duration(duration: float, decimal_seconds: bool = False) -> str:
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

def format_basic_stats(source: str, time: int, games: int) -> str:
    if games == 0:
        return f'No games found for {source}.'
    return f'{source}: {format_duration(time/games)} across {games} games'


def average(player: str, matches: List[Result]) -> float:
    if player in CACHED_AVERAGES:
        return CACHED_AVERAGES[player]

    filtered = tuple(filter(lambda x: x.contains(player), matches))
    time = sum((m.duration for m in filtered))
    games = sum((m.game_count for m in filtered))
    if games == 0:
        print(f'no games found for {player}')
    avg = time/games
    CACHED_AVERAGES[player] = avg
    return avg

def adaptability(player: str, matches: List[Result]) -> float:
    def opponent(players: Players) -> str:
        if player.lower() == players[0].lower():
            return players[1]
        return players[0]

    filtered = filter(lambda x: x.contains(player), matches)

    duration_diff = []
    avg_diff = []
    avg = average(player, matches)

    for match in filtered:
        duration_diff.append(match.duration / match.game_count / avg)
        oppo = opponent(match.players)
        avg_diff.append(average(oppo, matches) / avg)

    #print(','.join(map(str, map(round, duration_diff))))
    #print(','.join(map(str, map(round, avg_diff))))

    return numpy.polyfit(duration_diff, avg_diff, 1)[0] # type: ignore

def player_stats(player: str, matches: List[Result]) -> str: #pylint: disable=too-many-locals
    def opponent(players: Players) -> str:
        if player.lower() == players[0].lower():
            return players[1]
        return players[0]


    filtered = sorted(filter(lambda x: x.contains(player), matches), key=lambda x:x.start_time)

    time = sum((m.duration for m in filtered))
    games = sum((m.game_count for m in filtered))
    averages = tuple(m.duration / m.game_count for m in filtered)

    res = f'Stats for {player}\n'
    res += 'WARNING: Noisy, incomplete and likely even incorrect data!\n'

    opponents = []
    res += 'Average game times\n'
    for match in filtered:
        oppo = opponent(match.players)
        opponents.append(oppo)
        res += (f'\t{format_duration(match.duration/match.game_count):6} '
                f'in {match.game_count} vs {oppo}\n')

    res += format_basic_stats('Total', time, games) + '\n'

    weighted_matches: List[float] = sum(
            ([m.duration/m.game_count]*m.game_count for m in filtered), [])
    res += f'stdev: {statistics.stdev(weighted_matches)/60:.2}m\n'

    trend : float= numpy.polyfit(range(len(filtered)), averages, 1)[0] # type: ignore
    res += f'Trend: {trend:.2f}s\n'

    # Adaptability

    res += f'Adaptability: {adaptability(player, matches):.4f}\n'

    return res

def player_stdev(player, matches: List[Result]) -> float:

    filtered = filter(lambda x: x.contains(player), matches)
    weighted_matches: List[float] = sum(
            ([m.duration/m.game_count]*m.game_count for m in filtered), [])
    return statistics.stdev(weighted_matches)

def big_stats(matches : List[Result]):
    big_dict = {}
    for match in matches:
        for player in match.players:
            if player not in big_dict:
                big_dict[player] = [match]
            else:
                big_dict[player].append(match)

    sorted_players = sorted(big_dict.keys(), key=lambda x: len(big_dict[x]), reverse=True)

    for player in sorted_players[:20]:
        print(f'{player:17}, {format_duration(average(player, matches))}, '
                f'{adaptability(player, matches):.4f}, '
                f'{len(big_dict[player]):2}, '
                f'{player_stdev(player, matches)/60:.2f}')

def main(matches : List[Result]) -> None:

    total_time = sum((m.duration for m in matches))
    total_games = sum((m.game_count for m in matches))

    print(f'Total games: {total_games}')
    print(f'Total average: {format_duration(total_time/total_games)}')

    weighted_matches: List[float] = sum(
            ([m.duration/m.game_count]*m.game_count for m in matches), [])
    print(f'stdev: {statistics.stdev(weighted_matches)/60:.2f}m')

    match = max(matches, key=lambda x: x.duration)
    print(f'Longest match: {format_duration(match.duration)} across {match.game_count}')

    match = min(matches, key=lambda x: x.duration)
    print(f'Shortest match: {format_duration(match.duration)} across {match.game_count}')

    match = max(matches, key=lambda x: x.duration / x.game_count)
    print(format_basic_stats('Longest average', match.duration, match.game_count))

    match = min(matches, key=lambda x: x.duration / x.game_count)
    print(format_basic_stats('Shortest average', match.duration, match.game_count))

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

def big_correlation(matches: List[Result]) -> None:
    player_averages = []
    durations = []
    for match in matches:
        if match.game_count < 3:
            continue
        if match.duration / match.game_count > 5000:
            continue
        avg = sum((average(p, matches) for p in match.players))/2
        if avg > 2500:
            continue
        player_averages.append(avg)
        durations.append(match.duration / match.game_count)

    polyfit = numpy.polyfit(player_averages, durations, 1) # type: ignore
    print(polyfit)
    min_avg = min(player_averages)
    max_avg = max(player_averages)
    x_axis = numpy.linspace(min_avg, max_avg, 100)
    y_axis = x_axis*polyfit[0] + polyfit[1]

    _fig, axes = pyplot.subplots()
    axes.scatter(player_averages, durations, s=8, c='000000')
    axes.plot(x_axis, y_axis)

    axes.set_title(f'Game length as a function of players average game length. n={len(durations)}')
    axes.set_xlabel('average game duration for the two players')
    axes.set_ylabel('average game duration in the match')
    pyplot.xlim(700, 2000)
    pyplot.ylim(0, 3000)
    pyplot.show()

    #print(polyfit)
    #with open('big_correlation.csv', 'w', encoding='utf-8') as file:
    #    for avg, duration in zip(player_averages, durations):
    #        file.write(f'{avg},{duration}\n')

def mainmain() -> None:
    matches = load_matches()
    main(matches)
    #print()
    #print(player_stats('jakkdl', matches))
    #print()
    #print(player_stats('nasmith99', matches))
    #print()
    #print(player_stats('aku chi', matches))
    big_stats(matches)
    big_correlation(matches)

if __name__ == '__main__':
    mainmain()
