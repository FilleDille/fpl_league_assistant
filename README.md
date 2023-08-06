# fpl_league_assistant - a Fantasy Premier League League Monitoring Script

## Description

This script is designed to monitor a Fantasy Premier League (FPL) league and send email notifications when any participant joins or leaves the league since the last check. It also provides options to fetch and display information about the league.

The script is currently under build up with only basic features available. New features will be added during the season.

## Setup

1. Make sure you have Python installed on your system.
2. Install required dependencies by running:

    ```pip install dotenv requests smtplib```

## How to Use

1. Clone or download the script from GitHub.
2. Create a .env file in the same directory as the script and add the following variables:
    ```
    EMAIL=your_email@gmail.com
    APP_PW=your_app_password
    MAC=your_mac_subdirectory_path
    LINUX=your_linux_subdirectory_path
    ```
   
    Replace your_email@gmail.com with your Gmail address, and your_app_password with the App Password generated for your Gmail account to use SMTP (this is required for sending emails).

3. Obtain the league ID for your Fantasy Premier League from the official FPL website.
4. Run the script using the following command:
    ```
    python script_name.py <league_id>
   ```
    Replace script_name.py with the actual name of the Python script file, and <league_id> with the ID of your Fantasy Premier League.
   
## Options

* Fetch and Monitor: By running the script with just the league ID, it fetches the participants' information in the league and saves it in a JSON file (participants_<league_id>.json). It then compares the current participants with the previous ones, sending an email if there are any new joiners or if some participants have left since the last check.
* Dump: By running the script with two arguments (league ID and dump), it displays the current participants' information in the league as stored in the JSON file.
* Stats: By running the script with two arguments (league ID and stats), it displays statistics about the participating countries in the league, including the number of participants from each country and their percentage in the league.

## Note

* The script uses Gmail's SMTP server to send notification emails. Make sure to provide valid email credentials in the .env file to enable email notifications.
* The script will create or update a JSON file (participants_<league_id>.json) in the user's specified subdirectory path (MAC for macOS and LINUX for Linux) to store the participants' information for comparison in future runs.

## Example Usage

1. To fetch and monitor a Fantasy Premier League with league ID 12345:
    ```
    python script_name.py 12345
    ```
2. To display the current participants in the league with league ID 12345:
    ```
    python script_name.py 12345 dump
   ```
3. To display statistics about the participating countries in the league with league ID 12345:
    ```
    python script_name.py 12345 stats
   ```