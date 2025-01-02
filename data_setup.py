#!/usr/bin/env python3

import json
import requests
import os
from datetime import datetime

BASE_URL = "https://fantasy.premierleague.com/api/"
LEAGUE_ID = 405323  # Fixed mini-league ID

def fetch_data(url):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch data from {url}. Status code: {response.status_code}")
        return None
    return response.json()

def fetch_bootstrap_data():
    """Fetch the entire bootstrap-static dataset (teams, players, events)."""
    url = BASE_URL + "bootstrap-static/"
    return fetch_data(url)

def fetch_fixtures(gw):
    """Fetch the fixtures for a given gameweek."""
    url = BASE_URL + "fixtures/"
    all_fixtures = fetch_data(url)
    if not all_fixtures:
        return []
    return [f for f in all_fixtures if f["event"] == gw]

def fetch_league_data(league_id):
    """Fetch the standings for a given mini-league."""
    url = BASE_URL + f"leagues-classic/{league_id}/standings/"
    return fetch_data(url)

def fetch_manager_data(team_id):
    url = BASE_URL + f"entry/{team_id}/"
    return fetch_data(url)

def fetch_manager_transfers(team_id):
    url = BASE_URL + f"entry/{team_id}/transfers/"
    return fetch_data(url)

def fetch_manager_history(team_id):
    url = BASE_URL + f"entry/{team_id}/history/"
    return fetch_data(url)

def fetch_gameweek_data_for_team(team_id, gameweek):
    url = BASE_URL + f"entry/{team_id}/event/{gameweek}/picks/"
    return fetch_data(url)

def get_current_gameweek(bootstrap_data):
    """Return the integer 'id' of the current gameweek."""
    for event in bootstrap_data.get('events', []):
        if event.get('is_current'):
            return event['id']
    return None

def retrieve_mini_league_data(league_id, gameweek):
    league_data = fetch_league_data(league_id)
    if not league_data or 'standings' not in league_data:
        return None

    for entry in league_data['standings']['results']:
        team_id = entry['entry']
        entry['manager_details'] = fetch_manager_data(team_id)
        entry['transfers'] = fetch_manager_transfers(team_id)
        entry['history'] = fetch_manager_history(team_id)

        gw_str = str(gameweek)
        entry['gameweek_data'] = {}
        entry['gameweek_data'][gw_str] = fetch_gameweek_data_for_team(team_id, gw_str)

    return league_data

def save_to_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def main():
    """
    Script 1 (fetch_and_save):
    - Fetch bootstrap data and identify current_gw
    - Fetch next_gw fixtures and embed in the bootstrap data under "fixtures_next_gw"
    - Fetch mini-league data for the current_gw
    - Save to player_data.json and league_data.json
    - Overwrite these files each time
    """
    os.makedirs(".", exist_ok=True)  # Ensure current directory is available
    # 1) Fetch bootstrap data
    bootstrap_data = fetch_bootstrap_data()
    if not bootstrap_data:
        print("Error: Could not fetch bootstrap data.")
        return

    current_gw = get_current_gameweek(bootstrap_data)
    if not current_gw:
        print("Error: Could not determine current gameweek.")
        return

    # 2) Also fetch fixtures for next_gw
    next_gw = current_gw + 1
    next_gw_fixtures = fetch_fixtures(next_gw)
    # Store them in the bootstrap data
    bootstrap_data["fixtures_next_gw"] = next_gw_fixtures

    # 3) Fetch mini-league data for current_gw
    mini_league_data = retrieve_mini_league_data(LEAGUE_ID, current_gw)
    if not mini_league_data:
        print("Error: Could not fetch mini-league data.")
        return

    # 4) Overwrite JSON files
    player_data_file = "player_data.json"
    league_data_file = "league_data.json"

    save_to_json(bootstrap_data, player_data_file)
    save_to_json(mini_league_data, league_data_file)

    print(f"Bootstrap data (plus fixtures_next_gw) saved to {player_data_file}")
    print(f"Mini-league data (current GW = {current_gw}) saved to {league_data_file}")
    print(f"\nDone! Current gameweek is GW{current_gw}, next is GW{next_gw}.")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
