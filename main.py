import os
from dotenv import load_dotenv
import requests as rq
import sys
import json
import smtplib
import time


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

        self.league_id = league_id
        self.league_name = ''
        self.missing_participants_id = []
        self.new_participants_id = []
        self.missing_participants_obj = []
        self.new_participants_obj = []
        self.response_results = []
        self.league_url = f'https://fantasy.premierleague.com/api/leagues-classic/{self.league_id}/standings/'

        if sys.platform == "darwin":
            current_subdir = os.getenv('MAC')
        else:
            current_subdir = os.getenv('LINUX')

        self.email = os.getenv('EMAIL')
        self.app_pw = os.getenv('APP_PW')
        self.current_dir = os.path.expanduser('~') + current_subdir
        self.participant_path = self.current_dir + f'participants_{league_id}.json'

        if os.path.exists(self.participant_path):
            with open(self.participant_path, 'r') as file:
                self.current_participants_json = json.load(file)
        else:
            with open(self.participant_path, 'w') as file:
                json.dump([], file)
                self.current_participants_json = []

    def fetch(self):
        has_more = True
        i = 1

        while has_more:
            if i == 800:
                has_more = False

            response_raw = rq.get(self.league_url + f'?page_new_entries={i}&page_standings=1&phase=1')
            response = response_raw.json()

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

        response_entries = [entry['entry'] for entry in self.response_results]
        missing_entries = [entry for entry in self.current_participants_json if entry['entry'] not in response_entries]
        new_entries = [entry for entry in self.response_results
                       if not any(d['entry'] == entry['entry'] for d in self.current_participants_json)]

        for entry in missing_entries:
            self.missing_participants_id.append(entry['entry'])

        for entry in new_entries:
            self.new_participants_id.append(entry['entry'])

        if len(self.missing_participants_id) > 0 or len(self.new_participants_id) > 0:
            self.missing_participants_obj = [Participant(entry) for entry in self.missing_participants_id]
            self.new_participants_obj = [Participant(entry) for entry in self.new_participants_id]

            with open(self.participant_path, 'w') as file:
                self.send_email()
                json.dump(self.response_results, file)

    def send_email(self):
        missing_list = [f'{player.id}, ' \
                        f'{player.team_name}, ' \
                        f'{player.first_name},' \
                        f'{player.last_name}, ' \
                        f'{player.country}'
                        for player in self.missing_participants_obj]

        new_list = [f'{player.id}, ' \
                    f'{player.team_name}, ' \
                    f'{player.first_name}, ' \
                    f'{player.last_name}, ' \
                    f'{player.country}'
                    for player in self.new_participants_obj]

        message = 'Subject: Change in league {}\n\nThe following {} ' \
                  'has left the league:{}\nThe following {} has joined ' \
                  'the league:{}'.format(self.league_name,
                                         len(self.missing_participants_id),
                                         missing_list,
                                         len(self.new_participants_id),
                                         new_list
                                         )

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
    fpl.fetch()
    fpl.compare()
