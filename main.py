import os
from dotenv import load_dotenv
import requests as rq
import sys
import json
import smtplib
import time
from functools import reduce


class Participant:
    def __init__(self, player_id):
        self.player_url = f'https://fantasy.premierleague.com/api/entry/{player_id}/'
        response_raw = rq.get(self.player_url)
        self.response = response_raw.json()
        self.id = player_id

        try:
            self.team_name = self.response['name']

        except Exception as e:
            self.team_name = e

        try:
            self.first_name = self.response['player_first_name']

        except Exception as e:
            self.first_name = e

        try:
            self.last_name = self.response['player_last_name']

        except Exception as e:
            self.last_name = e

        try:
            self.country = self.response['player_region_name']

        except Exception as e:
            self.country = e


class FPL:
    def __init__(self, league_id: str):
        load_dotenv()

        self.league_id: str = league_id
        self.league_name: str = ''
        self.missing_participants_id: list = []
        self.new_participants_id: list = []
        self.all_participants_id: list = []
        self.missing_participants_obj: dict = {}
        self.new_participants_obj: dict = {}
        self.all_participants_obj: dict = {}
        self.response_results: list = []
        self.league_url: str = f'https://fantasy.premierleague.com/api/leagues-classic/{self.league_id}/standings/'

        if sys.platform == "darwin":
            current_subdir: str = os.getenv('MAC')
        else:
            current_subdir: str = os.getenv('LINUX')

        self.email: str = os.getenv('EMAIL')
        self.app_pw: str = os.getenv('APP_PW')
        self.current_dir: str = os.path.expanduser('~') + current_subdir
        self.participant_path: str = self.current_dir + f'participants_{league_id}.json'

        if os.path.exists(self.participant_path):
            with open(self.participant_path, 'r') as file:
                self.current_participants_json: list = json.load(file)
        else:
            with open(self.participant_path, 'w') as file:
                json.dump([], file)
                self.current_participants_json: list = []

    def __str__(self):
        return self.current_participants_json.__str__()

    def __len__(self):
        return len(self.current_participants_json)

    def fetch(self):
        has_more: bool = True
        i: int = 1

        while has_more:
            if i == 800:
                has_more = False

            response_raw = rq.get(self.league_url + f'?page_new_entries={i}&page_standings=1&phase=1')
            response: json = response_raw.json()

            if self.league_name == '':
                self.league_name = response['league']['name']

            if len(response['new_entries']['results']) == 0:
                has_more = False
            else:
                self.response_results = self.response_results + response['new_entries']['results']

            time.sleep(0.1)
            i += 1


    def compare(self):
        self.missing_participants_id = []
        self.new_participants_id = []

        self.all_participants_id = [entry['entry'] for entry in self.response_results]
        missing_entries = [entry for entry in self.current_participants_json if entry['entry'] not in self.all_participants_id]
        new_entries = [entry for entry in self.response_results
                       if not any(d['entry'] == entry['entry'] for d in self.current_participants_json)]

        for entry in missing_entries:
            self.missing_participants_id.append(entry['entry'])

        for entry in new_entries:
            self.new_participants_id.append(entry['entry'])

        if len(self.missing_participants_id) > 0 or len(self.new_participants_id) > 0:
            self.missing_participants_obj = {entry: Participant(entry) for entry in self.missing_participants_id}
            self.new_participants_obj = {entry: Participant(entry) for entry in self.new_participants_id}
            self.all_participants_obj = {entry: Participant(entry) for entry in self.all_participants_id}

            for participant in self.response_results:
                participant['country'] = self.all_participants_obj[participant['entry']].country

            with open(self.participant_path, 'w') as file:
                self.send_email()
                json.dump(self.response_results, file)

    def stats(self):
        def count_countries(dictionary, parameter):
            if 'country' in dictionary and dictionary['country'] == parameter:
                return 1
            return 0

        unique_countries = set([x['country'] for x in self.current_participants_json])
        num_unique_countries = len(unique_countries)
        num_participants = len(self.current_participants_json)
        print(f'Participating countries ({num_unique_countries}): {unique_countries}')

        print(f'Whereas:')

        for country in unique_countries:
            num_in_country = sum(map(lambda d: count_countries(d, country), self.current_participants_json))
            print(f'\t{country}: {num_in_country} ({round(num_in_country / num_participants * 100, 1)} %)')

        print(f'\n\tTotal: {num_participants}')

    def send_email(self):
        missing_list = [f'{player.id}, ' \
                        f'{player.team_name}, ' \
                        f'{player.first_name},' \
                        f'{player.last_name}, ' \
                        f'{player.country}'
                        for player in self.missing_participants_obj.values()]

        new_list = [f'{player.id}, ' \
                    f'{player.team_name}, ' \
                    f'{player.first_name}, ' \
                    f'{player.last_name}, ' \
                    f'{player.country}'
                    for player in self.new_participants_obj.values()]

        message = 'Subject: Change in league {}\n\nThe following {} ' \
                  'has left the league:{}\nThe following {} has joined ' \
                  'the league:{}'.format(self.league_name,
                                         len(self.missing_participants_id),
                                         missing_list,
                                         len(self.new_participants_id),
                                         new_list
                                         ).encode('utf-8')

        try:
            s = smtplib.SMTP('smtp.gmail.com', 587)
            s.starttls()
            s.login(self.email, self.app_pw)
            s.sendmail(self.email, self.email, message)
            s.quit()

        except Exception as e:
            print(e)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('No league id provided')
        sys.exit()

    fpl = FPL(sys.argv[1])

    if len(sys.argv) == 2:
        fpl.fetch()
        fpl.compare()

    if len(sys.argv) == 3:
        if sys.argv[2] == 'dump':
            print(fpl)

        if sys.argv[2] == 'stats':
            fpl.stats()
