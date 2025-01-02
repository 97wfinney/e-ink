# E-Ink FPL Display

This repository contains two main Python scripts and supporting folders to fetch Fantasy Premier League (FPL) data and display it on a Waveshare 3.52-inch E-Ink screen connected to a Raspberry Pi.

---

## Contents

- **`data_setup.py`**  
  - Fetches FPL data via the official [Fantasy Premier League API](https://fantasy.premierleague.com/).
  - The mini-league ID is **hard-coded** as `405323` (change `LEAGUE_ID` in the script to suit your own league).
  - Stores the bootstrap data and mini-league data into local JSON files:  
    - `player_data.json`  
    - `league_data.json`

- **`main.py`**  
  - Loads the fetched JSON data.
  - Uses **Waveshare E-Paper** libraries (in the `lib` folder) to render pages on the e-ink display.
  - Cycles through multiple pages, including:
    1. **Basic Insights** (average score, highest score, etc.)
    2. **Chips Used** (who used Bench Boost, Triple Captain, etc.)
    3. **Top Form Players**
    4. **Most Transferred In**
    5. **Team Strengths** (from FPL’s `strength_overall_home` and `strength_overall_away`)
    6. **Mini-League Manager Analysis** (one page per manager, showing captain, transfers, points)
    7. **“My Team” Analysis** specifically for the team named `404error.log`
    8. **Upcoming Fixture Pages** for the next gameweek

- **`lib/`**  
  - Python libraries for the Waveshare EPD module (e.g. `waveshare_epd` directory).
  - Provides `epd3in52` and related functionality.

- **`pic/`**  
  - Contains fonts or any image assets needed for the display (e.g. `Font.ttc`, other images).

---

## Requirements

- **Python 3** on your Raspberry Pi.
- **PIL** (Pillow), SMBus, and other dependencies for the Waveshare display:
  ```bash
  sudo apt-get update
  sudo apt-get install python3-pil python3-smbus```

- The Waveshare 3.52-inch e-paper display itself, wired to the Pi’s GPIO.
- lib folder should contain the waveshare_epd modules. If not, you may need to install them system-wide or copy them from the original Waveshare repo.

---
## Usage
### Data Setup (fetch FPL data)
Run data_setup.py to fetch the latest FPL bootstrap, next gameweek fixtures, and mini-league standings.
Outputs player_data.json and league_data.json in the local directory.
### Main
Then run main.py to load those JSON files and cycle through various pages on the e-ink display.
It will continuously loop, showing each page for ~60 seconds.

 ## Example
 ```bash
python3 data_setup.py
python3 main.py
```


## Work in Progress
This is still under development. The e-ink layout, fonts, and detailed visuals may evolve over time.
You can tweak the scripts to change:
- The mini-league ID in data_setup.py (currently 405323).
- The display update intervals.
- “My Team Analysis” to match your actual team name.


## Contributing

Feel free to open issues or submit pull requests if you have ideas for improvements or additional pages for the display!

## Enjoy tracking your FPL mini-league on a Waveshare E-Ink display!
