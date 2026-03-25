# Space Grid TBS

A 2D top-down, turn-based strategy game inspired by classic arcade visuals (Galaga-like space feel), played on a board-game-style grid map.

## Overview
- 1 human player vs 1–3 AI opponents (selected from the main menu).
- Each player controls 6 ships:
  - 2 Healing ships
  - 2 Tank ships
  - 2 Normal ships
- The goal is to be the last player with ships remaining alive.

## Gameplay (MVP)
- Each owner turn:
  - A dice is rolled (default `1–6`).
  - Choose exactly one ship and move it `dice` tiles (8-direction, straight-line move).
  - Collect health pickups on landing.
  - If possible, take one action (attack or heal).
  - Apply asteroid storm damage if outside the safe zone.

## Controls
- Main menu:
  - Press `1`, `2`, or `3` to choose number of AI opponents.
- In-game (human turn):
  - Click your ship: selects active ship.
  - Click a highlighted tile: moves active ship.
  - Click an enemy ship: attack (if in range).
  - Click a friendly ship: heal (if active ship is a healer and heal cooldown is ready).
  - Press `Space`: end turn (during the action phase).
- Game over:
  - Press `R` to return to the menu.

## Requirements
- Python 3.x
- `pygame`

## Installation
```bash
pip install -r requirements.txt
```

## Run
```bash
python main.py
```

## Credits
- Game built with Python + Pygame.

## Note on AI Tools Used
- Development assistance was guided with AI support in `Cursor IDE` and `ChatGPT/OpenAI` for planning and implementation help.

