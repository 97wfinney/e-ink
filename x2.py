#!/usr/bin/env python3

import sys
import os
import json
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure paths
thisdir = os.path.dirname(os.path.realpath(__file__))

picdir = os.path.join(thisdir, 'pic')   
libdir = os.path.join(thisdir, 'lib')   


if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd3in52

# -------------------------------------------------------------------------
# Utility functions from your text-based script
# (Used for My Team Analysis and gameweek calculations)
# -------------------------------------------------------------------------

def calculate_gw_average(mini_league_data, gw):
    total_points = 0
    count = 0
    for manager in mini_league_data['standings']['results']:
        if 'history' in manager and 'current' in manager['history']:
            if len(manager['history']['current']) > (gw - 1):
                total_points += manager['history']['current'][gw - 1]['points']
                count += 1
    return total_points / count if count else 0

# -------------------------------------------------------------------------
# The main FPLAnalyzer class
# -------------------------------------------------------------------------
class FPLAnalyzer:
    def __init__(self):
        self.player_data = None
        self.league_data = None
        self.current_gw = None
        self.current_gw_event = None
        self.player_id_to_name = {}
        self.player_id_to_points = {}
        self.player_id_to_position = {}
        self.teams_by_id = {}

    def load_data(self):
        # Load the JSON data
        with open('player_data.json', 'r') as f:
            self.player_data = json.load(f)
        with open('league_data.json', 'r') as f:
            self.league_data = json.load(f)

        # Identify the current gameweek
        self.current_gw_event = next(
            (ev for ev in self.player_data['events'] if ev.get("is_current")), 
            None
        )
        if not self.current_gw_event:
            raise ValueError("No current gameweek found in player_data.json")
        self.current_gw = self.current_gw_event['id']

        # Build lookups
        players = self.player_data.get('elements', [])
        self.player_id_to_name = {p['id']: p['web_name'] for p in players}
        self.player_id_to_points = {p['id']: p['event_points'] for p in players}
        self.player_id_to_position = {p['id']: p['element_type'] for p in players}
        self.teams_by_id = {t['id']: t for t in self.player_data.get('teams', [])}

    def get_chip_usage(self):
        if not self.current_gw_event or 'chip_plays' not in self.current_gw_event:
            return []
        return self.current_gw_event['chip_plays']

    def get_form_players(self):
        players = self.player_data.get('elements', [])
        return sorted(
            players,
            key=lambda x: float(x['form']),
            reverse=True
        )[:5]

    def get_most_transferred(self):
        players = self.player_data.get('elements', [])
        return sorted(
            players,
            key=lambda x: x['transfers_in_event'],
            reverse=True
        )[:5]

    def get_team_strengths(self):
        teams = self.player_data.get('teams', [])
        return sorted(
            teams,
            key=lambda x: x['strength_overall_home'] + x['strength_overall_away'],
            reverse=True
        )[:5]

    def analyze_fixtures(self):
        """Return next-gw fixture data with basic attack strength calculations."""
        fixtures = self.player_data.get('fixtures_next_gw', [])
        analyzed_fixtures = []
        for fixture in fixtures:
            home_team = self.teams_by_id.get(fixture['team_h'])
            away_team = self.teams_by_id.get(fixture['team_a'])
            if home_team and away_team:
                home_attack = home_team['strength_attack_home']
                away_defence = away_team['strength_defence_away']
                home_strength = home_attack / away_defence if away_defence else 0

                away_attack = away_team['strength_attack_away']
                home_defence = home_team['strength_defence_home']
                away_strength = away_attack / home_defence if home_defence else 0

                analyzed_fixtures.append({
                    'home_team': home_team['name'],
                    'away_team': away_team['name'],
                    'home_strength': home_strength,
                    'away_strength': away_strength
                })
        # Split into pages of 2 fixtures each
        fixture_pages = [analyzed_fixtures[i:i + 2] for i in range(0, len(analyzed_fixtures), 2)]
        return fixture_pages

    def get_mini_league_standings(self):
        """Return a list of manager data from the mini-league standings."""
        return self.league_data.get('standings', {}).get('results', [])

    def get_manager_details(self, manager_data):
        """Build a quick dictionary for a single manager's current-gw data."""
        gw_data = manager_data.get('gameweek_data', {}).get(str(self.current_gw), {})
        entry_history = gw_data.get('entry_history', {})
        picks = gw_data.get('picks', [])

        # Captain
        captain_pick = next((p for p in picks if p.get('is_captain')), None)
        captain_id = captain_pick['element'] if captain_pick else None
        captain_multiplier = captain_pick['multiplier'] if captain_pick else 1
        captain_name = self.player_id_to_name.get(captain_id, 'Unknown')
        captain_points = self.player_id_to_points.get(captain_id, 0) * captain_multiplier

        # Top scorer in picks
        if picks:
            top_scorer_id = max(picks, key=lambda x: self.player_id_to_points.get(x['element'], 0))['element']
            top_scorer_points = self.player_id_to_points.get(top_scorer_id, 0)
            top_scorer_name = self.player_id_to_name.get(top_scorer_id, 'Unknown')
        else:
            top_scorer_name, top_scorer_points = 'Unknown', 0

        # Formation
        starting_players = [p for p in picks if p['position'] <= 11]
        formation = "{}-{}-{}".format(
            sum(1 for pick in starting_players if self.player_id_to_position.get(pick['element'], 0) == 2),
            sum(1 for pick in starting_players if self.player_id_to_position.get(pick['element'], 0) == 3),
            sum(1 for pick in starting_players if self.player_id_to_position.get(pick['element'], 0) == 4)
        )

        return {
            'points': entry_history.get('points', 0),
            'captain_name': captain_name,
            'captain_points': captain_points,
            'transfers': entry_history.get('event_transfers', 0),
            'team_value': entry_history.get('value', 0) / 10,
            'bank': entry_history.get('bank', 0) / 10,
            'top_scorer_name': top_scorer_name,
            'top_scorer_points': top_scorer_points,
            'formation': formation,
            'chip_used': gw_data.get('active_chip', 'None'),
            'rank_movement': manager_data.get('rank_sort', 0) - manager_data.get('last_rank', 0),
            'manager_name': manager_data['entry_name'],
            'total_points': manager_data['total']
        }

    # ---------------------------------------------------------------------
    # "My Team Analysis" logic for "404error.log"
    # Returns a dict with the data to display. If not found, returns None.
    # ---------------------------------------------------------------------
    def get_my_team_analysis(self):
        my_team_name = "404error.log"
        standings = self.get_mini_league_standings()
        my_team = next((m for m in standings if m['entry_name'] == my_team_name), None)
        if not my_team:
            return None

        # Basic data
        my_points = my_team['total']
        leader = max(standings, key=lambda x: x['total']) if standings else None
        leader_points = leader['total'] if leader else 0

        total_all = sum(m['total'] for m in standings)
        avg_points_total = total_all / len(standings) if standings else 0

        # Position
        sorted_by_points = sorted(standings, key=lambda x: x['total'], reverse=True)
        position = next(i for i, m in enumerate(sorted_by_points, start=1) if m['entry_name'] == my_team_name)

        # Weekly analysis
        gw_avg = calculate_gw_average(self.league_data, self.current_gw)
        gw_data = my_team.get('gameweek_data', {}).get(str(self.current_gw), {})
        picks = gw_data.get('picks', [])
        entry_history = gw_data.get('entry_history', {})
        my_gw_points = entry_history.get('points', 0)

        # Captaincy Analysis
        captain_pick = next((p for p in picks if p.get('is_captain')), None)
        captain_points = 0
        if captain_pick:
            c_id = captain_pick['element']
            c_mult = captain_pick['multiplier']
            captain_points = self.player_id_to_points.get(c_id, 0) * c_mult

        if picks:
            # highest raw points in starting XI
            starters = [p for p in picks if p['position'] <= 11]
            best_player = max(starters, key=lambda x: self.player_id_to_points.get(x['element'], 0), default=None)
            best_player_points = self.player_id_to_points.get(best_player['element'], 0) if best_player else 0
        else:
            best_player_points = 0

        best_possible_captain_points = best_player_points * 2
        captain_success_rate = 0.0
        if best_possible_captain_points > 0:
            captain_success_rate = (captain_points / best_possible_captain_points) * 100

        return {
            'my_team_name': my_team_name,
            'my_points': my_points,
            'leader_points': leader_points,
            'avg_points_total': avg_points_total,
            'position': position,
            'num_teams': len(standings),
            'my_gw_points': my_gw_points,
            'league_gw_average': gw_avg,
            'captain_points': captain_points,
            'best_possible_captain_points': best_possible_captain_points,
            'captain_success_rate': captain_success_rate
        }

# -------------------------------------------------------------------------
# The FPLDisplay class for the e-ink rendering
# -------------------------------------------------------------------------
class FPLDisplay:
    def __init__(self):
        self.epd = epd3in52.EPD()
        self.epd.init()

        self.font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
        self.font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)
        self.font16 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 16)
        self.font14 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 14)
        self.font12 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 12)

        # e-Paper dimensions
        self.width = self.epd.height
        self.height = self.epd.width

    def create_page(self):
        return Image.new('1', (self.width, self.height), 255)

    def display_page(self, image):
        self.epd.display(self.epd.getbuffer(image))
        self.epd.lut_GC()
        self.epd.refresh()

    def clear(self):
        self.epd.Clear()

    def sleep(self):
        self.epd.sleep()

    def draw_title(self, draw, text):
        draw.text((10, 5), text, font=self.font24, fill=0)
        draw.line((10, 35, self.width - 10, 35), fill=0)

    # ---------------------------------------------------------------------
    # Basic Insights Page
    # ---------------------------------------------------------------------
    def create_basic_insights_page(self, analyzer):
        image = self.create_page()
        draw = ImageDraw.Draw(image)

        self.draw_title(draw, f"GW{analyzer.current_gw} Insights")

        y = 45
        event = analyzer.current_gw_event
        stats = [
            f"Average: {event['average_entry_score']}",
            f"Highest: {event['highest_score']}",
            f"Most Cap: {analyzer.player_id_to_name.get(event['most_captained'])}",
            f"Most Trans: {analyzer.player_id_to_name.get(event['most_transferred_in'])}",
            f"Top Player: {analyzer.player_id_to_name.get(event.get('top_element'))} "
            f"({event.get('top_element_info', {}).get('points', 0)})"
        ]

        for stat in stats:
            draw.text((10, y), stat, font=self.font18, fill=0)
            y += 25

        return image

    # ---------------------------------------------------------------------
    # Chips Page
    # ---------------------------------------------------------------------
    def create_chips_page(self, analyzer):
        image = self.create_page()
        draw = ImageDraw.Draw(image)

        self.draw_title(draw, "Chips Used")

        y = 45
        for chip in analyzer.get_chip_usage():
            text = f"{chip['chip_name']}: {chip['num_played']}"
            draw.text((10, y), text, font=self.font18, fill=0)
            y += 25

        return image

    # ---------------------------------------------------------------------
    # Top Form Players
    # ---------------------------------------------------------------------
    def create_form_page(self, analyzer):
        image = self.create_page()
        draw = ImageDraw.Draw(image)

        self.draw_title(draw, "Top Form Players")

        y = 45
        for player in analyzer.get_form_players():
            team_name = analyzer.teams_by_id.get(player['team'], {}).get('name', '?')
            line = f"{player['web_name']} ({team_name}): {player['form']}"
            draw.text((10, y), line, font=self.font16, fill=0)
            y += 25

        return image

    # ---------------------------------------------------------------------
    # Most Transferred In Page
    # ---------------------------------------------------------------------
    def create_transfers_page(self, analyzer):
        image = self.create_page()
        draw = ImageDraw.Draw(image)

        self.draw_title(draw, "Most Transferred In")

        y = 45
        for player in analyzer.get_most_transferred():
            team_name = analyzer.teams_by_id.get(player['team'], {}).get('name', '?')
            line = f"{player['web_name']} ({team_name}): {player['transfers_in_event']}"
            draw.text((10, y), line, font=self.font16, fill=0)
            y += 25

        return image

    # ---------------------------------------------------------------------
    # Team Strengths Page
    # ---------------------------------------------------------------------
    def create_team_strength_page(self, analyzer):
        image = self.create_page()
        draw = ImageDraw.Draw(image)

        self.draw_title(draw, "Team Strength")

        y = 45
        for t in analyzer.get_team_strengths():
            strength = t['strength_overall_home'] + t['strength_overall_away']
            line = f"{t['name']}: {strength}"
            draw.text((10, y), line, font=self.font18, fill=0)
            y += 25

        return image

    # ---------------------------------------------------------------------
    # Single Manager Analysis Page (One page per team)
    # ---------------------------------------------------------------------
    def create_manager_page(self, manager_details):
        """
        Create a page showing data for exactly one manager from the mini league.
        manager_details is a dict from analyzer.get_manager_details(...)
        """
        image = self.create_page()
        draw = ImageDraw.Draw(image)

        # Manager name at top
        self.draw_title(draw, f"Manager: {manager_details['manager_name']}")

        y = 45
        lines = [
            f"Points: {manager_details['points']}",
            f"Captain: {manager_details['captain_name']} "
            f"({manager_details['captain_points']})",
            f"Transfers: {manager_details['transfers']}",
            f"Team Value: {manager_details['team_value']:.1f}",
            f"Top Scorer: {manager_details['top_scorer_name']} "
            f"({manager_details['top_scorer_points']})",
            f"Formation: {manager_details['formation']}",
            f"Chip: {manager_details['chip_used']}",
            f"Rank Move: {manager_details['rank_movement']}",
            f"Total Points: {manager_details['total_points']}"
        ]

        for line in lines:
            draw.text((10, y), line, font=self.font16, fill=0)
            y += 22

        return image

    # ---------------------------------------------------------------------
    # Fixtures Pages
    # ---------------------------------------------------------------------
    def create_fixtures_pages(self, analyzer):
        fixture_pages = analyzer.analyze_fixtures()
        rendered_pages = []
        next_gw = analyzer.current_gw + 1

        for i, chunk in enumerate(fixture_pages):
            image = self.create_page()
            draw = ImageDraw.Draw(image)
            self.draw_title(draw, f"GW{next_gw} Fixtures ({i+1}/{len(fixture_pages)})")

            y = 45
            for fixture in chunk:
                # Show fixture teams
                line1 = f"{fixture['home_team']} (H) vs"
                line2 = f"{fixture['away_team']} (A)"
                draw.text((10, y), line1, font=self.font16, fill=0)
                y += 20
                draw.text((10, y), line2, font=self.font16, fill=0)
                y += 25

                # Attack strengths
                home_str = f"{fixture['home_team']} Atk: {fixture['home_strength']:.2f}"
                away_str = f"{fixture['away_team']} Atk: {fixture['away_strength']:.2f}"
                draw.text((20, y), home_str, font=self.font14, fill=0)
                y += 20
                draw.text((20, y), away_str, font=self.font14, fill=0)
                y += 35

            rendered_pages.append(image)

        return rendered_pages

    # ---------------------------------------------------------------------
    # "My Team Analysis" Page for 404error.log
    # ---------------------------------------------------------------------
    def create_my_team_page(self, analyzer):
        """
        If 404error.log is found, display the analysis on a single page.
        Otherwise show a note that the team wasn't found.
        """
        analysis = analyzer.get_my_team_analysis()
        image = self.create_page()
        draw = ImageDraw.Draw(image)

        self.draw_title(draw, "My Team Analysis")

        y = 45
        if not analysis:
            # Team not found
            lines = [
                "404error.log not found",
                "in this league."
            ]
            for line in lines:
                draw.text((10, y), line, font=self.font16, fill=0)
                y += 25
            return image

        # If found, display the data
        lines = [
            f"Team: {analysis['my_team_name']}",
            f"Total Points: {analysis['my_points']}",
            f"League Pos: {analysis['position']} of {analysis['num_teams']}",
            f"Leader Diff: {analysis['leader_points'] - analysis['my_points']}",
            f"vs. Average: {analysis['my_points'] - analysis['avg_points_total']:+.1f}",
            "",
            "Weekly Analysis:",
            f"  This GW's Pts: {analysis['my_gw_points']}",
            f"  League GW Avg: {analysis['league_gw_average']:.1f}",
            f"  vs. GW Avg: {(analysis['my_gw_points'] - analysis['league_gw_average']):+.1f}",
            "",
            "Captaincy Analysis:",
            f"  Actual Captain: {analysis['captain_points']}",
            f"  Best Captain: {analysis['best_possible_captain_points']}",
            f"  Success Rate: {analysis['captain_success_rate']:.1f}%",
        ]

        for line in lines:
            draw.text((10, y), line, font=self.font16, fill=0)
            y += 22

        return image

# -------------------------------------------------------------------------
# Main script logic
# -------------------------------------------------------------------------
def main():
    try:
        analyzer = FPLAnalyzer()
        analyzer.load_data()
        logger.info("Data loaded successfully")

        fpl_display = FPLDisplay()
        logger.info("Display initialized")

        # Build the pages we want to cycle
        pages = []

        # 1) Basic insights
        pages.append(fpl_display.create_basic_insights_page(analyzer))

        # 2) Chips
        pages.append(fpl_display.create_chips_page(analyzer))

        # 3) Top form
        pages.append(fpl_display.create_form_page(analyzer))

        # 4) Most transferred in
        pages.append(fpl_display.create_transfers_page(analyzer))

        # 5) Team strengths
        pages.append(fpl_display.create_team_strength_page(analyzer))

        # 6) One page per mini-league manager
        standings = analyzer.get_mini_league_standings()
        for manager_data in standings:
            md = analyzer.get_manager_details(manager_data)
            pages.append(fpl_display.create_manager_page(md))

        # 7) "My Team Analysis" page
        pages.append(fpl_display.create_my_team_page(analyzer))

        # 8) Fixture pages
        fixture_pages = fpl_display.create_fixtures_pages(analyzer)
        pages.extend(fixture_pages)

        # Now cycle through pages
        while True:
            for page in pages:
                fpl_display.clear()
                fpl_display.display_page(page)
                time.sleep(60)  # Show each page for 60 seconds

    except KeyboardInterrupt:
        logger.info("Ctrl+C pressed. Exiting...")
        fpl_display.clear()
        fpl_display.sleep()
        sys.exit()

    except Exception as e:
        logger.error(f"Error: {e}")
        # In case of error, clear and sleep
        fpl_display.clear()
        fpl_display.sleep()
        sys.exit()

if __name__ == "__main__":
    main()
