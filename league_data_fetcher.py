import pandas as pd
import requests as rq
import json
import time


class Fetcher:
    position_dict: dict = {1: 'GOAL', 2: 'DEF', 3: 'MID', 4: 'FWD'}

    def __init__(self, time_sleep: float, league_id: int, gw: int):
        self.pick_dict: dict = {}
        self.chip_dict: dict = {}
        self.entry_dict: dict = {}
        self.player_dict: dict = {}
        self.record_list: list = []
        self.player_set: set = set()
        self.gw: int = gw
        self.time_sleep: float = time_sleep
        self.league_id: int = league_id

        url_bootstrap = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        url_league = f'https://fantasy.premierleague.com/api/leagues-classic/{self.league_id}/standings/'

        self.bootstrap: json = rq.get(url_bootstrap).json()
        self.df_all = pd.merge(pd.DataFrame(self.bootstrap['teams']), pd.DataFrame(self.bootstrap['elements']), left_on='id', right_on='team')
        self.team_dict = {x['id']: x['name'] for x in self.bootstrap['teams']}

        has_more: bool = True
        counter: int = 1
        x: int = 1
        more_old_entries: bool = True
        response_results: list = []
        gw_index_list: list = list(range(1, self.gw + 1))

        while has_more:
            league_response_raw: json = rq.get(url_league + f'?page_new_entries=1&page_standings={x}&phase=1')
            print(f'Status code: {league_response_raw.status_code}')
            league_response: json = league_response_raw.json()

            if len(league_response['standings']['results']) == 0:
                more_old_entries = False
            else:
                response_results = response_results + league_response['standings']['results']
                x += 1

            if not more_old_entries:
                has_more = False

            print(f'Page #{x - 1} saved, sleeping for {self.time_sleep} s')
            time.sleep(self.time_sleep)

        print('Fetching league entries')

        for entry_summary in response_results:
            entry = entry_summary['entry']
            self.entry_dict[entry] = {}
            self.pick_dict[entry] = {}
            self.chip_dict[entry] = {}

            for i in gw_index_list:
                entry_url = f'https://fantasy.premierleague.com/api/entry/{entry}/event/{i}/picks/'

                if not (entry_response := fetch_participant(entry_url, self.time_sleep)):
                    continue

                self.pick_dict[entry][i] = entry_response['picks']
                self.chip_dict[entry][i] = entry_response['active_chip']
                self.player_set.update([player['element'] for player in entry_response['picks']])
                self.entry_dict[entry][i] = entry_response['entry_history']

                print(f'Entry #{counter} saved, sleeping for {self.time_sleep} s')
                time.sleep(self.time_sleep)
                counter += 1

        counter = 1

        for player in self.player_set:
            self.player_dict[player] = Player(self, player)
            print(f'Player #{counter} created, sleeping for {self.time_sleep} s')
            time.sleep(self.time_sleep)
            counter += 1

        counter = 1
        entry_set = set(self.entry_dict.keys())

        for entry in entry_set:
            for i in gw_index_list:
                record_status = "failed"

                try:
                    temp_entry_dict = self.entry_dict[entry][i]
                    temp_pick_dict = self.pick_dict[entry][i]
                    temp_chip_dict = self.chip_dict[entry][i]
                except Exception as e:
                    print(e)
                    print(f'Record #{counter} for team {entry} gw {i} {record_status}, sleeping for {self.time_sleep} s')
                    time.sleep(self.time_sleep)
                    counter += 1
                    continue

                temp_record = Record(self, entry, temp_entry_dict, temp_pick_dict, temp_chip_dict, i)

                if temp_record.successful:
                    self.record_list.append(temp_record)
                    record_status = "created"

                print(f'Record #{counter} for team {entry} gw {i} {record_status}, sleeping for {self.time_sleep} s')
                time.sleep(self.time_sleep)
                counter += 1

        print('Fetching complete')

        print('Creating a DataFrames')

        dict_list = [
            {
                'gw': record.gw,
                'entry': record.entry,
                'first_name': record.first_name,
                'second_name': record.second_name,
                'team_name': record.team_name,
                'favourite_team': record.favourite_team,
                'country': record.country,
                'points': record.points,
                'total_points': record.total_points,
                'points_on_bench': record.points_on_bench,
                'value': record.value,
                'value_ex_bank': record.value_ex_bank,
                'bank': record.bank,
                'event_transfers': record.event_transfers,
                'event_transfers_cost': record.event_transfers_cost,
                'rank': record.rank,
                'chip': record.chip,
                'def_count': record.def_count,
                'mid_count': record.mid_count,
                'fwd_count': record.fwd_count,
                'captain_entry': record.captain_entry,
                'captain_name': record.captain_name,
                'captain_position': record.captain_position,
                'captain_points': record.captain_points,
                'minutes': record.minutes,
                'was_home': record.was_home,
                'assists': record.assists,
                'goals_scored': record.goals_scored,
                'clean_sheets': record.clean_sheets,
                'goals_conceded': record.goals_conceded,
                'own_goals': record.own_goals,
                'penalties_saved': record.penalties_saved,
                'penalties_missed': record.penalties_missed,
                'yellow_cards': record.yellow_cards,
                'red_cards': record.red_cards,
                'saves': record.saves,
                'bonus': record.bonus,
                'bps': record.bps,
                'influence': record.influence,
                'creativity': record.creativity,
                'threat': record.threat,
                'ict_index': record.ict_index,
                'starts': record.starts,
                'expected_goals': record.expected_goals,
                'expected_assists': record.expected_assists,
                'expected_goal_involvements': record.expected_goal_involvements,
                'expected_goals_conceded': record.expected_goals_conceded
            }
            for record in self.record_list
        ]

        self.df = pd.DataFrame(dict_list)

        self.df['acc_points_on_bench'] = self.df.groupby('entry')['points_on_bench'].cumsum()
        self.df['acc_event_transfers'] = self.df.groupby('entry')['event_transfers'].cumsum()
        self.df['acc_event_transfers_cost'] = self.df.groupby('entry')['event_transfers_cost'].cumsum()
        self.df['mean_def_count'] = self.df.groupby('entry')['def_count'].cumsum() / self.df['gw']
        self.df['mean_mid_count'] = self.df.groupby('entry')['mid_count'].cumsum() / self.df['gw']
        self.df['mean_fwd_count'] = self.df.groupby('entry')['fwd_count'].cumsum() / self.df['gw']
        self.df['acc_captain_points'] = self.df.groupby('entry')['captain_points'].cumsum()
        self.df['acc_minutes'] = self.df.groupby('entry')['minutes'].cumsum()
        self.df['acc_was_home'] = self.df.groupby('entry')['was_home'].cumsum()
        self.df['acc_assists'] = self.df.groupby('entry')['assists'].cumsum()
        self.df['acc_goals_scored'] = self.df.groupby('entry')['goals_scored'].cumsum()
        self.df['acc_clean_sheets'] = self.df.groupby('entry')['clean_sheets'].cumsum()
        self.df['acc_goals_conceded'] = self.df.groupby('entry')['goals_conceded'].cumsum()
        self.df['acc_own_goals'] = self.df.groupby('entry')['own_goals'].cumsum()
        self.df['acc_penalties_saved'] = self.df.groupby('entry')['penalties_saved'].cumsum()
        self.df['acc_penalties_missed'] = self.df.groupby('entry')['penalties_missed'].cumsum()
        self.df['acc_yellow_cards'] = self.df.groupby('entry')['yellow_cards'].cumsum()
        self.df['acc_red_cards'] = self.df.groupby('entry')['red_cards'].cumsum()
        self.df['acc_saves'] = self.df.groupby('entry')['saves'].cumsum()
        self.df['acc_bonus'] = self.df.groupby('entry')['bonus'].cumsum()
        self.df['acc_bps'] = self.df.groupby('entry')['bps'].cumsum()
        self.df['acc_influence'] = self.df.groupby('entry')['influence'].cumsum()
        self.df['acc_creativity'] = self.df.groupby('entry')['creativity'].cumsum()
        self.df['acc_threat'] = self.df.groupby('entry')['threat'].cumsum()
        self.df['acc_ict_index'] = self.df.groupby('entry')['ict_index'].cumsum()
        self.df['acc_starts'] = self.df.groupby('entry')['starts'].cumsum()
        self.df['acc_expected_goals'] = self.df.groupby('entry')['expected_goals'].cumsum()
        self.df['acc_expected_assists'] = self.df.groupby('entry')['expected_assists'].cumsum()
        self.df['acc_expected_goal_involvements'] = self.df.groupby('entry')['expected_goal_involvements'].cumsum()
        self.df['acc_expected_goals_conceded'] = self.df.groupby('entry')['expected_goals_conceded'].cumsum()

        self.df['acc_goals_luck'] = self.df['acc_goals_scored'] - self.df['acc_expected_goals']
        self.df['acc_assists_luck'] = self.df['acc_assists'] - self.df['acc_expected_assists']
        self.df['acc_goals_conceded_luck'] = self.df['acc_goals_conceded'] - self.df['acc_expected_goals_conceded']
        self.df['acc_goal_involvements_luck'] = self.df['acc_goals_scored'] + self.df['acc_assists'] - self.df['acc_expected_goal_involvements']

        self.df_last = self.df.copy(True)
        self.df_last = self.df_last[self.df_last['gw'] == self.df['gw'].max()]
        self.df_last['league_rank'] = self.df_last['total_points'].rank(ascending=False, method='min')
        self.df_last.sort_values(by='league_rank', ascending=True, inplace=True)

        print('DataFrames complete')


class Player:
    def __init__(self, fetcher_instance: Fetcher, element: int):
        self.player_history: dict = {}

        filtered_df = fetcher_instance.df_all[fetcher_instance.df_all['id_y'] == element]
        self.team_name = filtered_df['name'].iloc[0]
        self.first_name = filtered_df['first_name'].iloc[0]
        self.second_name = filtered_df['second_name'].iloc[0]
        self.position = fetcher_instance.position_dict[int(filtered_df['element_type'].iloc[0])]

        player_url = f'https://fantasy.premierleague.com/api/element-summary/{element}/'
        player_response_raw = rq.get(player_url)
        player_response: json = player_response_raw.json()

        print(f'Status code: {player_response_raw.status_code}')

        if len(player_response['history']) == 0:
            return

        for gw in player_response['history']:
            self.player_history[gw['round']] = gw


class Record:
    def __init__(self, fetcher_instance: Fetcher, entry: int, entry_dict: dict, pick_list: list, chip: str, gw: int):
        self.successful: bool = True
        manager_url = f'https://fantasy.premierleague.com/api/entry/{entry}/'
        self.fetcher_instance = fetcher_instance

        if not (manager_response := fetch_participant(manager_url, fetcher_instance.time_sleep)):
            self.successful = False
            return

        try:
            captain_dict = list(filter(lambda p: p['multiplier'] in (2, 3), pick_list))[0]
            captain_multiplier = captain_dict['multiplier']
            player_dict_captain: Player = fetcher_instance.player_dict[captain_dict['element']]
            self.players_played_list: list = [x['element'] for x in list(filter(lambda p: p['multiplier'] != 0, pick_list))]

            self.gw: int = gw
            self.entry: int = entry
            self.first_name: str = manager_response['player_first_name']
            self.second_name: str = manager_response['player_last_name']
            self.team_name: str = manager_response['name']

            if (favourite_team_id := manager_response['favourite_team']) is None:
                self.favourite_team = None
            else:
                self.favourite_team = fetcher_instance.team_dict[favourite_team_id]

            self.country: str = manager_response['player_region_name']
            self.points: int = entry_dict['points']
            self.total_points: int = entry_dict['total_points']
            self.points_on_bench: int = entry_dict['points_on_bench']
            self.value: int = entry_dict['value']
            self.value_ex_bank: int = int(entry_dict['value']) - (entry_dict['bank'])
            self.bank: int = entry_dict['bank']
            self.event_transfers: int = entry_dict['event_transfers']
            self.event_transfers_cost: int = entry_dict['event_transfers_cost']
            self.rank: int = entry_dict['rank']
            self.chip: str = chip
            self.def_count = sum([1 if fetcher_instance.player_dict[x].position == 'DEF' else 0 for x in
                                  self.players_played_list])
            self.mid_count = sum([1 if fetcher_instance.player_dict[x].position == 'MID' else 0 for x in
                                  self.players_played_list])
            self.fwd_count = sum([1 if fetcher_instance.player_dict[x].position == 'FWD' else 0 for x in
                                  self.players_played_list])
            self.captain_entry: int = captain_dict['element']
            self.captain_name: str = player_dict_captain.first_name + ' ' + player_dict_captain.second_name
            self.captain_position: str = player_dict_captain.position
            self.captain_points: int = player_dict_captain.player_history[gw]['total_points'] * captain_multiplier

            self.minutes: int = self.aggregate('minutes', 'sum', gw)
            self.was_home: int = self.aggregate('was_home', 'sum', gw)
            self.assists: int = self.aggregate('assists', 'sum', gw)
            self.goals_scored: int = self.aggregate('goals_scored', 'sum', gw)
            self.clean_sheets: int = self.aggregate('clean_sheets', 'sum', gw)
            self.goals_conceded: int = self.aggregate('goals_conceded', 'sum', gw)
            self.own_goals: int = self.aggregate('own_goals', 'sum', gw)
            self.penalties_saved: int = self.aggregate('penalties_saved', 'sum', gw)
            self.penalties_missed: int = self.aggregate('penalties_missed', 'sum', gw)
            self.yellow_cards: int = self.aggregate('yellow_cards', 'sum', gw)
            self.red_cards: int = self.aggregate('red_cards', 'sum', gw)
            self.saves: int = self.aggregate('saves', 'sum', gw)
            self.bonus: int = self.aggregate('bonus', 'sum', gw)
            self.bps: int = self.aggregate('bps', 'sum', gw)
            self.influence: float = self.aggregate('influence', 'sum', gw)
            self.creativity: float = self.aggregate('creativity', 'sum', gw)
            self.threat: float = self.aggregate('threat', 'sum', gw)
            self.ict_index: float = self.aggregate('ict_index', 'sum', gw)
            self.starts: int = self.aggregate('starts', 'sum', gw)
            self.expected_goals: float = self.aggregate('expected_goals', 'sum', gw)
            self.expected_assists: float = self.aggregate('expected_assists', 'sum', gw)
            self.expected_goal_involvements: float = self.aggregate('expected_goal_involvements', 'sum', gw)
            self.expected_goals_conceded: float = self.aggregate('expected_goals_conceded', 'sum', gw)
        except Exception as e:
            print(e)
            self.successful = False

    def aggregate(self, attribute_name: str, agg: str, gw: int):
        try:
            attribute_values = [
                round(float(y), 2) if isinstance(y, str) else int(y)
                for x in self.players_played_list
                for y in [self.fetcher_instance.player_dict[x].player_history[gw][attribute_name] if gw in self.fetcher_instance.player_dict[x].player_history else None]
                if y is not None
            ]

            sum_attributes = sum(attribute_values)
            max_attributes = max(attribute_values)
            min_attributes = min(attribute_values)

            if agg == 'sum':
                return sum_attributes

            if agg == 'mean':
                return round(sum_attributes / len(attribute_values), 1) if len(attribute_values) > 0 else 0

            if agg == 'median':
                attribute_values.sort()
                return round(attribute_values[int(len(attribute_values) / 2 - 1)], 1) if \
                    len(attribute_values) % 2 == 1 else \
                    sum(attribute_values[int(len(attribute_values) // 2 - 1):int(len(attribute_values) // 2 + 1)]) / 2

            if agg == 'max':
                return max_attributes

            if agg == 'min':
                return min_attributes

            raise Exception(f"Unrecognized aggregation function: '{agg}'")
        except Exception as e:
            raise AttributeError(e)


def fetch_participant(entry_url, time_sleep):
    counter: int = 1
    continue_flag: bool = False
    retry_flag: bool = False

    entry_response_raw = rq.get(entry_url)
    entry_response: json = entry_response_raw.json()
    print(f'Status code: {entry_response_raw.status_code}')

    while not continue_flag:
        if entry_response_raw.status_code == 200:
            continue_flag = True
            continue

        if retry_flag:
            print(f'Entry #{counter} not available, sleeping for {time_sleep} s and continuing')
            time.sleep(time_sleep)
            return False

        print(f'Entry #{counter} failed to fetch, sleeping for 5 s and retrying')
        time.sleep(5)
        participant_response_raw = rq.get(entry_url)
        entry_response: json = participant_response_raw.json()
        print(f'Status code: {participant_response_raw.status_code}')
        retry_flag = True

    return entry_response
