from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from src.config import (
    COMBAT_RANGE,
    DICE_MAX,
    DICE_MIN,
    GRID_SIZE,
    HAZARD_DAMAGE,
    HEAL_COOLDOWN_TURNS,
    HEAL_AMOUNT,
    HEAL_RANGE,
    PICKUP_HEAL,
    PICKUP_RESPAWN_TURNS,
    PICKUP_SPAWN_COUNT,
    SHIP_HEALER,
    SAFE_ZONE_MIN_RADIUS,
    SAFE_ZONE_SHRINK_AMOUNT,
    SAFE_ZONE_SHRINK_INTERVAL,
    STORM_START_TURNS,
)
from src.models import Pickup, Ship


DIRS_8: List[Tuple[int, int]] = [
    (-1, -1),
    (0, -1),
    (1, -1),
    (-1, 0),
    (1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
]


def chebyshev_dist(x1: int, y1: int, x2: int, y2: int) -> int:
    return max(abs(x1 - x2), abs(y1 - y2))


def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


class GridManager:
    def __init__(self, grid_size: int = GRID_SIZE):
        self.grid_size = grid_size

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.grid_size and 0 <= y < self.grid_size

    def build_occupancy(self, ships: Sequence[Ship]) -> Dict[Tuple[int, int], int]:
        occ: Dict[Tuple[int, int], int] = {}
        for s in ships:
            if s.hp > 0:
                occ[(s.x, s.y)] = s.id
        return occ

    def is_tile_free(
        self, x: int, y: int, occupancy: Dict[Tuple[int, int], int]
    ) -> bool:
        return (x, y) not in occupancy

    def straight_move_destination(
        self, x: int, y: int, dir_xy: Tuple[int, int], steps: int
    ) -> Tuple[int, int]:
        dx, dy = dir_xy
        return x + dx * steps, y + dy * steps

    def validate_straight_move(
        self,
        ship: Ship,
        dir_xy: Tuple[int, int],
        steps: int,
        occupancy: Dict[Tuple[int, int], int],
    ) -> Optional[Tuple[int, int]]:
        """
        Board-game style movement:
        - choose a single direction for the whole dice move
        - move exactly `steps` tiles in a straight line
        - intermediate tiles must be empty
        """
        if steps <= 0:
            return (ship.x, ship.y)

        dest_x, dest_y = self.straight_move_destination(ship.x, ship.y, dir_xy, steps)
        if not self.in_bounds(dest_x, dest_y):
            return None

        dx, dy = dir_xy
        for k in range(1, steps + 1):
            tx = ship.x + dx * k
            ty = ship.y + dy * k
            if not self.in_bounds(tx, ty):
                return None
            if (tx, ty) in occupancy and (tx, ty) != (ship.x, ship.y):
                return None
        return (dest_x, dest_y)

    def ships_in_cheb_range(
        self,
        src: Ship,
        ships: Sequence[Ship],
        *,
        owner_filter: Optional[int] = None,
        range_tiles: int = COMBAT_RANGE,
    ) -> List[Ship]:
        out: List[Ship] = []
        for s in ships:
            if s.id == src.id or s.hp <= 0:
                continue
            if owner_filter is not None and s.owner_id != owner_filter:
                continue
            if chebyshev_dist(src.x, src.y, s.x, s.y) <= range_tiles:
                out.append(s)
        return out


class TurnManager:
    def __init__(self, dice_min: int = DICE_MIN, dice_max: int = DICE_MAX):
        self.dice_min = dice_min
        self.dice_max = dice_max
        self.dice_roll = 1
        self.global_turn_index = 0

    def roll_dice(self) -> int:
        self.dice_roll = random.randint(self.dice_min, self.dice_max)
        return self.dice_roll

    def advance_global_turn(self) -> int:
        self.global_turn_index += 1
        return self.global_turn_index


class CombatSystem:
    def attack_damage(self, attacker: Ship) -> int:
        # damage is fixed by ship type
        return attacker.damage

    def perform_attack(
        self, attacker: Ship, target: Ship
    ) -> Tuple[int, bool]:
        dmg = self.attack_damage(attacker)
        target.hp -= dmg
        killed = target.hp <= 0
        return dmg, killed

    def can_heal(self, healer: Ship) -> bool:
        return healer.ship_type == SHIP_HEALER and healer.heal_cooldown_remaining <= 0

    def perform_heal(self, healer: Ship, target: Ship) -> bool:
        """
        Healing only:
        - healer must be a Healing Ship
        - cooldown ready
        - target in range
        """
        if healer.ship_type != SHIP_HEALER:
            return False
        if healer.heal_cooldown_remaining > 0:
            return False
        if healer.owner_id != target.owner_id:
            return False
        if chebyshev_dist(healer.x, healer.y, target.x, target.y) > HEAL_RANGE:
            return False

        target.hp = clamp(target.hp + HEAL_AMOUNT, 0, target.max_hp)
        healer.heal_cooldown_remaining = HEAL_COOLDOWN_TURNS
        return True


class PickupManager:
    def __init__(self, spawn_count: int = PICKUP_SPAWN_COUNT, respawn_turns: int = PICKUP_RESPAWN_TURNS):
        self.spawn_count = spawn_count
        self.respawn_turns = respawn_turns

    def _random_empty_tile(
        self,
        *,
        rng: random.Random,
        grid_manager: GridManager,
        ships: Sequence[Ship],
        pickups: Sequence[Pickup],
    ) -> Optional[Tuple[int, int]]:
        occupancy = grid_manager.build_occupancy(ships)
        pickup_tiles = {(p.x, p.y) for p in pickups if p.active}

        # brute-force attempts; grid is small enough for this.
        for _ in range(2000):
            x = rng.randrange(grid_manager.grid_size)
            y = rng.randrange(grid_manager.grid_size)
            if (x, y) in occupancy:
                continue
            if (x, y) in pickup_tiles:
                continue
            return x, y
        return None

    def spawn_initial(
        self,
        *,
        rng: random.Random,
        grid_manager: GridManager,
        ships: Sequence[Ship],
    ) -> List[Pickup]:
        pickups: List[Pickup] = []
        next_id = 1
        for _ in range(self.spawn_count):
            tile = self._random_empty_tile(
                rng=rng, grid_manager=grid_manager, ships=ships, pickups=pickups
            )
            if tile is None:
                break
            x, y = tile
            pickups.append(Pickup(id=next_id, x=x, y=y, active=True, respawn_timer=0))
            next_id += 1
        return pickups

    def try_collect(self, ship: Ship, pickups: List[Pickup]) -> bool:
        for p in pickups:
            if p.active and p.x == ship.x and p.y == ship.y:
                ship.hp = clamp(ship.hp + PICKUP_HEAL, 0, ship.max_hp)
                p.active = False
                p.respawn_timer = self.respawn_turns
                return True
        return False

    def update(self, pickups: List[Pickup], *, rng: random.Random, grid_manager: GridManager, ships: Sequence[Ship]) -> None:
        """
        Respawn inactive pickups after `respawn_turns` global turns.
        Keep the overall pickup count at `spawn_count` by respawning each collected pickup.
        """
        for p in pickups:
            if p.active:
                continue
            p.respawn_timer -= 1
            if p.respawn_timer <= 0:
                tile = self._random_empty_tile(
                    rng=rng, grid_manager=grid_manager, ships=ships, pickups=pickups
                )
                if tile is None:
                    # If we can't find a tile, just wait and try again next tick.
                    p.respawn_timer = 1
                    continue
                p.x, p.y = tile
                p.active = True
                p.respawn_timer = 0


class HazardSystem:
    def __init__(self, grid_size: int = GRID_SIZE):
        self.grid_size = grid_size
        self.cx = grid_size // 2
        self.cy = grid_size // 2

        self.max_radius = max(self.cx, self.cy)

    def safe_radius(self, global_turn_index: int) -> int:
        if global_turn_index < STORM_START_TURNS:
            return self.max_radius
        shrinks = (global_turn_index - STORM_START_TURNS) // SAFE_ZONE_SHRINK_INTERVAL
        radius = self.max_radius - shrinks * SAFE_ZONE_SHRINK_AMOUNT
        return max(SAFE_ZONE_MIN_RADIUS, radius)

    def is_ship_in_safe_zone(self, ship: Ship, global_turn_index: int) -> bool:
        r = self.safe_radius(global_turn_index)
        return chebyshev_dist(ship.x, ship.y, self.cx, self.cy) <= r

    def apply_end_turn_damage(self, ships: Sequence[Ship], global_turn_index: int) -> List[int]:
        killed_ids: List[int] = []
        for s in ships:
            if s.hp <= 0:
                continue
            if not self.is_ship_in_safe_zone(s, global_turn_index):
                s.hp -= HAZARD_DAMAGE
                if s.hp <= 0:
                    killed_ids.append(s.id)
        return killed_ids


@dataclass
class AIChoice:
    ship_id: int
    move_dir: Tuple[int, int]
    moved_to: Tuple[int, int]
    action_type: str  # "attack" | "heal" | "none"
    target_id: Optional[int] = None
    heal_target_id: Optional[int] = None


class AIController:
    def __init__(self, *, num_opponents: int):
        self.num_opponents = num_opponents
        self.difficulty = 1.0 + 0.35 * max(0, num_opponents - 1)

        self.rng = random.Random()

    def choose_turn(
        self,
        *,
        owner_id: int,
        ships: Sequence[Ship],
        grid_manager: GridManager,
        pickups: Sequence[Pickup],
        hazard: HazardSystem,
        global_turn_index: int,
        dice_roll: int,
    ) -> AIChoice:
        occupancy = grid_manager.build_occupancy(ships)
        my_ships = [s for s in ships if s.owner_id == owner_id and s.hp > 0]
        if not my_ships:
            # Shouldn't happen; fallback.
            s0 = min(ships, key=lambda s: s.id)
            return AIChoice(ship_id=s0.id, move_dir=(0, 0), moved_to=(s0.x, s0.y), action_type="none")

        enemy_ships = [s for s in ships if s.owner_id != owner_id and s.hp > 0]
        pickup_tiles = [(p.x, p.y) for p in pickups if p.active]
        storm_active = global_turn_index >= STORM_START_TURNS
        safe_r = hazard.safe_radius(global_turn_index)

        attack_weight = 55 * self.difficulty
        heal_weight = 35 * self.difficulty
        pickup_weight = 18
        storm_weight = 30 * self.difficulty

        best: Optional[AIChoice] = None
        best_score = -1e18

        # Enumerate candidates: move straight in one of 8 directions.
        for ship in my_ships:
            for dir_xy in DIRS_8:
                dest = grid_manager.validate_straight_move(ship, dir_xy, dice_roll, occupancy)
                if dest is None:
                    continue

                sx, sy = dest

                # Predict "in range" after moving.
                enemies_in_range = [
                    e
                    for e in enemy_ships
                    if chebyshev_dist(sx, sy, e.x, e.y) <= COMBAT_RANGE
                ]
                friends_in_range = [
                    f
                    for f in my_ships
                    if chebyshev_dist(sx, sy, f.x, f.y) <= HEAL_RANGE
                ]
                heal_ready = ship.ship_type == SHIP_HEALER and ship.heal_cooldown_remaining <= 0

                # Evaluate best attack option
                best_attack = None
                if enemies_in_range:
                    # Prefer finishing low HP targets
                    best_target = min(enemies_in_range, key=lambda t: t.hp)
                    dmg = ship.damage
                    kill_bonus = 1000 if best_target.hp - dmg <= 0 else 0
                    best_attack = (
                        attack_weight * dmg + kill_bonus - best_target.hp * 0.1,
                        best_target.id,
                    )

                # Evaluate best heal option
                best_heal = None
                if heal_ready:
                    candidates = [f for f in friends_in_range if f.hp < f.max_hp]
                    if candidates:
                        best_target = max(candidates, key=lambda t: (t.max_hp - t.hp))
                        missing = best_target.max_hp - best_target.hp
                        kill_prevent_bonus = 0
                        best_heal = (
                            heal_weight * HEAL_AMOUNT + missing * 0.5 + kill_prevent_bonus,
                            best_target.id,
                        )

                # Evaluate movement shaping: pickups and safe zone during storm
                pickup_score = 0.0
                if pickup_tiles:
                    nearest = min(pickup_tiles, key=lambda xy: chebyshev_dist(sx, sy, xy[0], xy[1]))
                    dist_to_pickup = chebyshev_dist(sx, sy, nearest[0], nearest[1])
                    # Only strongly seek pickups if the ship is low-ish.
                    if ship.hp / ship.max_hp < 0.55:
                        pickup_score = pickup_weight * (10 - dist_to_pickup)

                storm_score = 0.0
                if storm_active:
                    # Prefer landing inside / closer to safe zone.
                    outside = max(0, chebyshev_dist(sx, sy, hazard.cx, hazard.cy) - safe_r)
                    storm_score = storm_weight * (-outside)

                # Combine: prioritize attack > heal > positioning
                move_base = pickup_score + storm_score
                action_score = move_base
                action_type = "none"
                target_id = None
                heal_target_id = None

                # Choose the better between attack and heal if available.
                if best_attack and best_heal:
                    if best_attack[0] >= best_heal[0]:
                        action_score = best_attack[0] + move_base * 0.25
                        action_type = "attack"
                        target_id = best_attack[1]
                    else:
                        action_score = best_heal[0] + move_base * 0.25
                        action_type = "heal"
                        heal_target_id = best_heal[1]
                elif best_attack:
                    action_score = best_attack[0] + move_base * 0.25
                    action_type = "attack"
                    target_id = best_attack[1]
                elif best_heal:
                    action_score = best_heal[0] + move_base * 0.25
                    action_type = "heal"
                    heal_target_id = best_heal[1]

                # Small randomness to avoid deterministic loops
                action_score += self.rng.uniform(-5, 5)

                if action_score > best_score:
                    best_score = action_score
                    best = AIChoice(
                        ship_id=ship.id,
                        move_dir=dir_xy,
                        moved_to=(sx, sy),
                        action_type=action_type,
                        target_id=target_id,
                        heal_target_id=heal_target_id,
                    )

        if best is None:
            # If no move is valid, stay and do best available action.
            ship = my_ships[0]
            enemies_in_range = grid_manager.ships_in_cheb_range(ship, ships, owner_filter=None, range_tiles=COMBAT_RANGE)
            enemies_in_range = [e for e in enemies_in_range if e.owner_id != owner_id]
            if enemies_in_range:
                target = min(enemies_in_range, key=lambda t: t.hp)
                return AIChoice(ship_id=ship.id, move_dir=(0, 0), moved_to=(ship.x, ship.y), action_type="attack", target_id=target.id)

            if ship.ship_type == SHIP_HEALER and ship.heal_cooldown_remaining <= 0:
                friend_candidates = [f for f in my_ships if chebyshev_dist(ship.x, ship.y, f.x, f.y) <= HEAL_RANGE and f.hp < f.max_hp]
                if friend_candidates:
                    target = max(friend_candidates, key=lambda t: t.max_hp - t.hp)
                    return AIChoice(ship_id=ship.id, move_dir=(0, 0), moved_to=(ship.x, ship.y), action_type="heal", heal_target_id=target.id)

            return AIChoice(ship_id=ship.id, move_dir=(0, 0), moved_to=(ship.x, ship.y), action_type="none")

        return best

