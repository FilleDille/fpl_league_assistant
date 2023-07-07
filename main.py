import os
from dotenv import load_dotenv
import requests as rq
import sys
import json
import smtplib


class FPL:
    def __init__(self, league_id: str):
        load_dotenv()

        self.league_id = league_id
        self.league_name = ''
        self.missing_participants = []
        self.new_participants = []
        self.response = None
        self.response_results = None
        self.participants = 0
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
        response_raw = rq.get(self.league_url)
        self.response = response_raw.json()
        self.response_results = self.response['new_entries']['results']
        self.participants = len(self.response)
        self.league_name = self.response['league']['name']

    def compare(self):
        self.missing_participants = []
        self.new_participants = []

        response_entries = [entry['entry'] for entry in self.response_results]
        missing_entries = [entry for entry in self.current_participants_json if entry['entry'] not in response_entries]
        new_entries = [entry for entry in self.response_results
                       if not any(d['entry'] == entry['entry'] for d in self.current_participants_json)]

        for entry in missing_entries:
            self.missing_participants.append(entry['entry'])

        for entry in new_entries:
            self.new_participants.append(entry['entry'])

        if len(self.missing_participants) > 0 or len(self.new_participants) > 0:
            with open(self.participant_path, 'w') as file:
                json.dump(self.response_results, file)

    def send_email(self):
        message = 'Subject: Change in league {}\n\nThe following {} ' \
                  'has left the league:{}\nThe following {} has joined ' \
                  'the league:{}'.format(self.league_name,
                                         len(self.missing_participants),
                                         self.missing_participants,
                                         len(self.new_participants),
                                         self.new_participants
                                         )

        try:
            s = smtplib.SMTP('smtp.gmail.com', 587)
            s.starttls()
            s.login(self.email, self.app_pw)
            s.sendmail(self.email, self.email, message)
            s.quit()

            return True

        except Exception as e:
            print(e)

            return False


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('No league id provided')
        sys.exit()

    fpl = FPL(sys.argv[1])
    fpl.fetch()
    fpl.compare()
