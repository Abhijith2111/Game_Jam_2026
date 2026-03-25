from __future__ import annotations

# -----------------------------
# Board / rendering
# -----------------------------
GRID_SIZE = 25
TILE_SIZE = 20
HUD_WIDTH = 420
SCREEN_WIDTH = GRID_SIZE * TILE_SIZE + HUD_WIDTH
SCREEN_HEIGHT = GRID_SIZE * TILE_SIZE
FPS = 60

# -----------------------------
# Dice / turns
# -----------------------------
DICE_MIN = 1
DICE_MAX = 6

# -----------------------------
# Ship types / stats
# -----------------------------
SHIP_HEALER = "healer"
SHIP_TANK = "tank"
SHIP_NORMAL = "normal"

SHIP_STATS = {
    SHIP_HEALER: {"max_hp": 70, "damage": 1},
    SHIP_TANK: {"max_hp": 120, "damage": 5},
    SHIP_NORMAL: {"max_hp": 80, "damage": 3},
}

HEAL_RANGE = 3
HEAL_AMOUNT = 10
HEAL_COOLDOWN_TURNS = 2

COMBAT_RANGE = 3

# -----------------------------
# Pickups
# -----------------------------
PICKUP_HEAL = 20
PICKUP_RESPAWN_TURNS = 5
PICKUP_SPAWN_COUNT = 2

# -----------------------------
# Hazard system
# -----------------------------
STORM_START_TURNS = 8  # global turn count
SAFE_ZONE_SHRINK_INTERVAL = 2
SAFE_ZONE_SHRINK_AMOUNT = 2
SAFE_ZONE_MIN_RADIUS = 0
HAZARD_DAMAGE = 10

# -----------------------------
# Colors (placeholders)
# -----------------------------
COLOR_BG = (7, 10, 20)
COLOR_GRID = (24, 30, 55)
COLOR_TEXT = (230, 235, 255)
COLOR_SAFE_ZONE = (55, 160, 255)
COLOR_STORM_OVERLAY = (255, 120, 40)
COLOR_PICKUP = (255, 240, 110)

COLOR_PLAYER0 = (60, 230, 120)  # human
COLOR_AI1 = (255, 90, 90)
COLOR_AI2 = (120, 150, 255)
COLOR_AI3 = (205, 120, 255)

PLAYER_COLORS = {
    0: COLOR_PLAYER0,
    1: COLOR_AI1,
    2: COLOR_AI2,
    3: COLOR_AI3,
}

