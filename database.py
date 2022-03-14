import datetime
import pickle
import os.path
from typing import List, Dict
from seat_typing import Result, Players



class Database:
    def __init__(self):
        self.pending_matches: Dict[Players, List[datetime.datetime]] = {}

        self.matches: Dict[Players, List[Result]] = {}

        self.flat_matches : List[Result]= []

    def add_match(self, players: Players,
            start: datetime.datetime,
            verbose: bool = False) -> bool:

        players = tuple(sorted(p.lower() for p in players)) #type: ignore

        if players in self.matches:
            for match in self.matches[players]:
                if abs(match.start_time - start) < datetime.timedelta(minutes=10):
                    if verbose:
                        print('adjacent match')
                    return False

        if players in self.pending_matches:
            for pending_match in self.pending_matches[players]:
                if abs(pending_match - start) < datetime.timedelta(minutes=10):
                    if verbose:
                        print('adjacent pending match')
                    return False
            self.pending_matches[players].append(start)
        else:
            self.pending_matches[players] = [start]

        return True

    def add_results(self, #pylint: disable=too-many-arguments
            players: Players,
            end: datetime.datetime,
            games: int,
            division: str,
            verbose: bool = False) -> bool:

        players = tuple(sorted(p.lower() for p in players)) #type: ignore

        if players not in self.pending_matches or not self.pending_matches[players]:
            if verbose:
                print(f"No pending match between {players}")
            return False

        pending_matches = [match for match in self.pending_matches[players]
            if end - match < datetime.timedelta(hours=6) and end > match]

        if not pending_matches:
            print(f'Found no suitable pending matches between {players}')
            return False

        pending_matches.sort(reverse=True)

        start_time = pending_matches[0]
        self.pending_matches[players].remove(start_time)

        delta = end - start_time
        duration = int(delta.total_seconds())

        if players not in self.matches:
            self.matches[players] = []
        else:
            for match in self.matches[players]:
                if abs(match.start_time - start_time) < datetime.timedelta(minutes=10):
                    print(f'About to add duplicate match between {players} at {start_time}!')
                    return False

        avg = duration/games
        if avg < 300 or avg > 7200:
            print(f'Extreme average {avg} in {games}, skipping match between {players}')

        result = Result(players, start_time, duration, games, division)
        self.matches[players].append(result)
        self.flat_matches.append(result)
        if verbose:
            print(f'Added match between {players}')
        return True

    def print_matches(self, data: str = 'all') -> None:
        if data in ('all', 'matches'):
            for matchup_lists in self.matches.values():
                for match in matchup_lists:
                    print(match)
        if data in ('all', 'pending'):
            for players, time in self.pending_matches.items():
                print(players, time)

    def export_matches(self, filename='matches.csv') -> None:
        with open(filename, 'w', encoding='utf-8') as file:
            for matchup_lists in self.matches.values():
                for match in matchup_lists:
                    file.write(str(match) + '\n')

    def save(self, data: str = 'all') -> None:
        if data in ('all', 'pending'):
            with open('pending_matches.pickle', 'wb') as file:
                pickle.dump(self.pending_matches, file)
        if data in ('all', 'matches'):
            with open('matches.pickle', 'wb') as file:
                pickle.dump(self.matches, file)
            with open('flat_matches.pickle', 'wb') as file:
                pickle.dump(self.flat_matches, file)

    def load(self, data: str = 'all') -> None:
        if data in ('all', 'pending'):
            with open('pending_matches.pickle', 'rb') as file:
                self.pending_matches = pickle.load(file)
        if data in ('all', 'matches'):
            if os.path.isfile('flat_matches.pickle'):
                with open('flat_matches.pickle', 'rb') as file:
                    self.flat_matches = pickle.load(file)
            with open('matches.pickle', 'rb') as file:
                self.matches = pickle.load(file)

    def wipe(self, data: str = 'all') -> None:
        if data in ('all', 'pending'):
            self.pending_matches = {}
        if data in ('all', 'matches'):
            self.matches = {}

database = Database()
