from __future__ import annotations

# -----------------------------
# Board / rendering
# -----------------------------
GRID_SIZE = 25
TILE_SIZE = 30
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
    SHIP_HEALER: {"max_hp": 60, "damage": 11},
    SHIP_TANK: {"max_hp": 110, "damage": 15},
    SHIP_NORMAL: {"max_hp": 70, "damage": 13},
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
STORM_FIRST_SHRINK_SECONDS = 60  # 1 minute
STORM_SUBSEQUENT_SHRINK_SECONDS = 60  # 1 minute
SAFE_ZONE_SHRINK_INTERVAL = 2
SAFE_ZONE_SHRINK_AMOUNT = 2
SAFE_ZONE_MIN_RADIUS = 0
HAZARD_DAMAGE = 10

# -----------------------------
# AI retreat behavior
# -----------------------------
AI_RETREAT_HP_THRESHOLD = 0.25  # retreat when HP% <= 25%
AI_RETREAT_DISTANCE_WEIGHT = 70  # how strongly AI prefers increasing distance

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

