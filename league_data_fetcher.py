import pandas as pd
import requests as rq
import json
import time
from functools import reduce

class Fetcher:
    position_dict: dict = {1: 'GOAL', 2: 'DEF', 3: 'MID', 4: 'FWD'}

    def __init__(self, time_sleep: float, league_id: int, gameweek: int):
        self.participants_dict: dict = {}
        self.pick_dict: dict = {}
        self.player_dict: dict = {}
        self.team_dict: dict = {}

        self.time_sleep = time_sleep
        self.league_id = league_id
        self.gw = gameweek
        self.counter = 1

        url_bootstrap = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        url_league = f'https://fantasy.premierleague.com/api/leagues-classic/{self.league_id}/standings/'


        self.bootstrap: json = rq.get(url_bootstrap).json()
        self.df_teams = pd.DataFrame(self.bootstrap['teams'])
        self.df_players = pd.DataFrame(self.bootstrap['elements'])
        self.df_all = pd.merge(self.df_teams, self.df_players, left_on='id', right_on='team')

        self.league_response: json = rq.get(url_league).json()  # add new entries, as well as team names
        self.participants_json = self.league_response['standings']['results']

        print('Fetching league entries')

        for p in self.league_response['standings']['results']:
            entry = p['entry']
            participant_url = f'https://fantasy.premierleague.com/api/entry/{entry}/event/{self.gw}/picks/'

            participant_response: json = rq.get(participant_url).json()
            self.pick_dict[entry] = participant_response['picks']
            entry_picks = [player['element'] for player in participant_response['picks']]
            self.participants_dict[entry] = entry_picks

            print(f'Entry #{self.counter} saved, sleeping for {self.time_sleep} s')
            time.sleep(self.time_sleep)
            self.counter += 1

        self.entry_element_tuple = [(key, value) for key, values in self.participants_dict.items() for value in values]

        self.df_melted_players = pd.DataFrame(self.entry_element_tuple, columns=['entry', 'player'])
        self.df_groupby = self.df_melted_players.groupby('player').count().sort_values('entry', ascending=False)
        self.df_groupby['unique'] = 1 - (self.df_groupby['entry'] - 1) / (len(self.participants_dict) - 1)
        self.df_unique = self.df_melted_players.merge(self.df_groupby.drop('entry', axis=1), on='player', how='left')

        self.counter = 1

        for p in self.df_groupby.reset_index()['player']:
            self.player_dict[p] = Player(self, p)
            print(f'Player #{self.counter} created, sleeping for {self.time_sleep} s')
            time.sleep(self.time_sleep)
            self.counter += 1

        self.counter = 1

        for k, v in self.participants_dict.items():
            self.team_dict[k] = Team(self, k)
            print(f'Team #{self.counter} created, sleeping for {self.time_sleep} s')
            time.sleep(self.time_sleep)
            self.counter += 1

        print('Fetching complete')


class Player:
    def __init__(self, fetcher_instance: Fetcher, element: int):
        self.player_history: list = []

        filtered_df = fetcher_instance.df_all[fetcher_instance.df_all['id_y'] == element]
        self.team_name = filtered_df['name'].iloc[0]
        self.first_name = filtered_df['first_name'].iloc[0]
        self.second_name = filtered_df['second_name'].iloc[0]
        self.position = fetcher_instance.position_dict[int(filtered_df['element_type'].iloc[0])]
        self.xp = float(filtered_df['ep_this'].iloc[0])

        player_url = f'https://fantasy.premierleague.com/api/element-summary/{element}/'
        player_response: json = rq.get(player_url).json()

        for gw in player_response['history']:
            self.player_history.append(gw)

        gw_summary = player_response['history'][fetcher_instance.gw - 1]

        self.opponent_team = int(gw_summary['opponent_team'])
        self.total_points = int(gw_summary['total_points'])
        self.was_home = int(gw_summary['was_home'])
        self.team_h_score = int(gw_summary['team_h_score'])
        self.team_a_score = int(gw_summary['team_a_score'])
        self.minutes = int(gw_summary['minutes'])
        self.goals_scored = int(gw_summary['goals_scored'])
        self.assists = int(gw_summary['assists'])
        self.clean_sheets = int(gw_summary['clean_sheets'])
        self.goals_conceded = int(gw_summary['goals_conceded'])
        self.own_goals = int(gw_summary['own_goals'])
        self.penalties_saved = int(gw_summary['penalties_saved'])
        self.penalties_missed = int(gw_summary['penalties_missed'])
        self.yellow_cards = int(gw_summary['yellow_cards'])
        self.red_cards = int(gw_summary['red_cards'])
        self.saves = int(gw_summary['saves'])
        self.bonus = int(gw_summary['bonus'])
        self.bps = int(player_response['history'][-1]['bps'])
        self.influence = float(gw_summary['influence'])
        self.creativity = float(gw_summary['creativity'])
        self.threat = float(gw_summary['threat'])
        self.ict_index = float(gw_summary['ict_index'])
        self.starts = int(gw_summary['starts'])
        self.expected_goals = float(gw_summary['expected_goals'])
        self.expected_assists = float(gw_summary['expected_assists'])
        self.expected_goal_involvements = float(gw_summary['expected_goal_involvements'])
        self.expected_goals_conceded = float(gw_summary['expected_goals_conceded'])
        self.value = int(gw_summary['value'])
        self.uniqueness = fetcher_instance.df_unique[fetcher_instance.df_unique['player'] == element]['unique'].iloc[0]


class Team:
    def __init__(self, fetcher_instance: Fetcher, entry: int):
        manager_url = f'https://fantasy.premierleague.com/api/entry/{entry}/'
        manager_response: json = rq.get(manager_url).json()

        self.entry: int = entry
        self.df_unique = fetcher_instance.df_unique[fetcher_instance.df_unique['entry'] == entry]
        self.player_list: list = [p for p in self.df_unique['player']]
        self.player_dict: dict = {p: fetcher_instance.player_dict[p] for p in self.player_list}
        self.first_name: str = manager_response['player_first_name']
        self.second_name: str = manager_response['player_last_name']
        self.country: str = manager_response['player_region_name']
        self.picks: dict = {x['element']: x['multiplier'] for x in fetcher_instance.pick_dict[entry]}
        self.uniqueness: float = round(
            sum([
                self.player_dict[k].uniqueness if v in (1, 0)
                else
                v * self.player_dict[k].uniqueness
                for k, v in self.picks.items()]) / len(self.player_dict),
            3
        )


        if manager_response['favourite_team'] is None:
            self.favourite_team = None
        else:
            self.favourite_team = fetcher_instance.df_teams[fetcher_instance.df_teams['id'] == manager_response['favourite_team']]['name'].iloc[0]

    def aggregate(self, attribute_name: str, agg: str):
        try:
            if agg == 'sum':
                return sum([getattr(player[1], attribute_name) for player in self.player_dict.items()])

            if agg == 'mean':
                attribute_values = [getattr(player[1], attribute_name) for player in self.player_dict.items()]
                total = sum(attribute_values)
                return round(total / len(attribute_values), 1) if len(attribute_values) > 0 else 0

            if agg == 'median':
                attribute_values = [getattr(player[1], attribute_name) for player in self.player_dict.items()]
                attribute_values.sort()
                return round(attribute_values[int(len(attribute_values) / 2 - 1)], 1) if \
                    len(attribute_values) % 2 == 1 else \
                    sum(attribute_values[int(len(attribute_values) // 2 - 1):int(len(attribute_values) // 2 + 1)]) / 2

            if agg == 'max':
                return max([getattr(player[1], attribute_name) for player in self.player_dict.items()])

            if agg == 'min':
                return min([getattr(player[1], attribute_name) for player in self.player_dict.items()])

            raise ValueError(f"Unrecognized aggregation function: '{agg}'")
        except Exception as e:
            raise AttributeError(e)