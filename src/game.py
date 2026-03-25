from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

import pygame

from src.config import (
    DICE_MAX,
    DICE_MIN,
    GRID_SIZE,
    PICKUP_SPAWN_COUNT,
    SHIP_HEALER,
    SHIP_NORMAL,
    SHIP_TANK,
    SHIP_STATS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    FPS,
    TILE_SIZE,
    DICE_MIN,
    DICE_MAX,
    COMBAT_RANGE,
    HEAL_RANGE,
    HEAL_COOLDOWN_TURNS,
    HEAL_AMOUNT,
    HEAL_RANGE,
    STORM_START_TURNS,
    SAFE_ZONE_MIN_RADIUS,
)
from src.models import Pickup, Ship, create_ship
from src.systems import (
    AIChoice,
    AIController,
    CombatSystem,
    GridManager,
    HazardSystem,
    PickupManager,
    TurnManager,
    DIRS_8,
)
from src.ui import UI


PHASE_MENU = "menu"
PHASE_SELECT_SHIP = "select_ship"
PHASE_SELECT_DEST = "select_destination"
PHASE_ACTION = "action_choice"
PHASE_GAME_OVER = "game_over"


@dataclass
class PendingHumanAction:
    action_type: Optional[str] = None  # "attack" | "heal" | None
    target_id: Optional[int] = None


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Space Grid TBS (Galaga-style TBS)")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.ui = UI(self.screen)

        self.rng = random.Random()

        self.state = PHASE_MENU
        self.num_opponents = 1

        # Core systems
        self.grid_manager = GridManager(grid_size=GRID_SIZE)
        self.turn_manager = TurnManager(dice_min=DICE_MIN, dice_max=DICE_MAX)
        self.combat = CombatSystem()
        self.hazard = HazardSystem(grid_size=GRID_SIZE)
        self.pickups = PickupManager(spawn_count=PICKUP_SPAWN_COUNT)

        # Game data
        self.ships: List[Ship] = []
        self.pickup_list: List[Pickup] = []
        self.active_owner_id: int = 0  # 0=human, 1..N=AIs
        self.active_ship_id: Optional[int] = None
        self.dice_roll: int = 1
        self.phase: str = PHASE_SELECT_SHIP

        # Destination tiles currently highlighted for movement selection.
        # value = shortest steps from the active ship to that tile (0..dice_roll).
        self.valid_destinations: Dict[Tuple[int, int], int] = {}
        self.in_range_attack_targets: List[Ship] = []
        self.in_range_heal_targets: List[Ship] = []
        self.pending_human_action = PendingHumanAction()

        self.ai: Optional[AIController] = None

        # Human-only multi-ship selection state (AI still moves one ship per turn).
        self.human_selected_ship_ids: List[int] = []
        self.human_processed_ship_ids: Set[int] = set()

        self.game_start_ticks_ms: int = pygame.time.get_ticks()

        self._running = True

    def reset_game(self) -> None:
        self.ships = []
        self.pickup_list = []
        self.active_owner_id = 0
        self.active_ship_id = None
        self.dice_roll = self.turn_manager.roll_dice()
        self.turn_manager.global_turn_index = 0
        self.game_start_ticks_ms = pygame.time.get_ticks()

        self.valid_destinations = {}
        self.in_range_attack_targets = []
        self.in_range_heal_targets = []
        self.pending_human_action = PendingHumanAction()

        self.human_selected_ship_ids = []
        self.human_processed_ship_ids = set()

        self.ai = AIController(num_opponents=self.num_opponents)

        self._spawn_fleets()
        self.pickup_list = self.pickups.spawn_initial(
            rng=self.rng, grid_manager=self.grid_manager, ships=self.ships
        )

        self.phase = PHASE_SELECT_SHIP
        self.state = "playing"

        # Decrement cooldown at start of the first owner's turn
        self._decrement_cooldowns_for_owner(self.active_owner_id)

    def _elapsed_seconds_since_game_start(self) -> float:
        return (pygame.time.get_ticks() - self.game_start_ticks_ms) / 1000.0

    def _spawn_fleets(self) -> None:
        # Ship IDs are global across the entire match.
        ship_id = 1

        # Up to 4 players: 0=human, 1..3=AIs
        player_regions: Dict[int, Tuple[int, int]] = {
            0: (5, GRID_SIZE - 5 - 2),
            1: (5, 5),
            2: (GRID_SIZE - 8, 5),
            3: (GRID_SIZE - 8, GRID_SIZE - 5 - 2),
        }

        offsets = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)]

        for owner_id in range(0, 1 + self.num_opponents):
            origin_x, origin_y = player_regions.get(owner_id, (5, 5))
            # Two of each type.
            types = [SHIP_HEALER, SHIP_HEALER, SHIP_TANK, SHIP_TANK, SHIP_NORMAL, SHIP_NORMAL]
            for i, (ox, oy) in enumerate(offsets):
                ship_type = types[i]
                x = origin_x + ox
                y = origin_y + oy
                self.ships.append(create_ship(ship_id, owner_id, ship_type, x, y))
                ship_id += 1

    def _alive_owner_ids(self) -> List[int]:
        alive: Dict[int, int] = {}
        for s in self.ships:
            if s.hp <= 0:
                continue
            alive[s.owner_id] = alive.get(s.owner_id, 0) + 1
        return sorted(alive.keys())

    def _alive_counts(self) -> Dict[int, int]:
        out: Dict[int, int] = {}
        for s in self.ships:
            if s.hp <= 0:
                continue
            out[s.owner_id] = out.get(s.owner_id, 0) + 1
        return out

    def _get_ship(self, ship_id: int) -> Optional[Ship]:
        for s in self.ships:
            if s.id == ship_id and s.hp > 0:
                return s
        return None

    def _get_ships_of_owner(self, owner_id: int) -> List[Ship]:
        return [s for s in self.ships if s.hp > 0 and s.owner_id == owner_id]

    def _decrement_cooldowns_for_owner(self, owner_id: int) -> None:
        for s in self.ships:
            if s.owner_id != owner_id:
                continue
            if s.heal_cooldown_remaining > 0:
                s.heal_cooldown_remaining -= 1

    def _owner_turn_cycle_count(self) -> int:
        return 1 + self.num_opponents

    def _advance_to_next_owner(self) -> None:
        self.active_owner_id = (self.active_owner_id + 1) % self._owner_turn_cycle_count()
        self.active_ship_id = None
        self.valid_destinations = {}
        self.in_range_attack_targets = []
        self.in_range_heal_targets = []
        self.pending_human_action = PendingHumanAction()
        self.phase = PHASE_SELECT_SHIP
        # Each owner turn begins with exactly one dice roll.
        self.dice_roll = self.turn_manager.roll_dice()

        # Clear human multi-ship state for the next owner.
        self.human_selected_ship_ids = []
        self.human_processed_ship_ids = set()

        self._decrement_cooldowns_for_owner(self.active_owner_id)

    def _end_turn(self) -> None:
        # Global turn advances after each player's turn.
        self.turn_manager.advance_global_turn()
        elapsed_seconds = self._elapsed_seconds_since_game_start()

        # Update pickups (respawn after 5 global turns).
        self.pickups.update(
            self.pickup_list,
            rng=self.rng,
            grid_manager=self.grid_manager,
            ships=self.ships,
        )

        # Apply hazard damage at end of turn.
        killed = self.hazard.apply_end_turn_damage(
            self.ships,
            self.turn_manager.global_turn_index,
            elapsed_seconds,
        )
        # (ships are already hp<=0 so occupancy will update automatically)

        # Check win condition
        alive_owner_ids = self._alive_owner_ids()
        if len(alive_owner_ids) <= 1:
            self.state = PHASE_GAME_OVER
            self.phase = PHASE_GAME_OVER
            return

        self._advance_to_next_owner()

    def _ship_can_attack(self, attacker: Ship) -> bool:
        enemies = [s for s in self.ships if s.hp > 0 and s.owner_id != attacker.owner_id]
        for e in enemies:
            if max(abs(attacker.x - e.x), abs(attacker.y - e.y)) <= COMBAT_RANGE:
                return True
        return False

    def _compute_human_action_targets(self, ship: Ship) -> Tuple[List[Ship], List[Ship]]:
        enemies = []
        friends = []
        for s in self.ships:
            if s.hp <= 0:
                continue
            if s.id == ship.id:
                continue
            dist = max(abs(ship.x - s.x), abs(ship.y - s.y))
            if dist <= COMBAT_RANGE and s.owner_id != ship.owner_id:
                enemies.append(s)
            if dist <= HEAL_RANGE and s.owner_id == ship.owner_id:
                friends.append(s)
        return enemies, friends

    def _try_move_active_ship(self, dest: Tuple[int, int]) -> bool:
        ship = self._get_ship(self.active_ship_id) if self.active_ship_id is not None else None
        if ship is None:
            return False

        # Movement rule: destination must be reachable within <= dice_roll steps.
        if dest not in self.valid_destinations:
            return False

        # Apply movement
        ship.x, ship.y = dest

        # Resolve pickup collection
        self.pickups.try_collect(ship, self.pickup_list)

        return True

    def _human_select_destinations_for_active_ship(self) -> Dict[Tuple[int, int], int]:
        ship = self._get_ship(self.active_ship_id) if self.active_ship_id is not None else None
        if ship is None:
            return {}
        occupancy = self.grid_manager.build_occupancy(self.ships)
        return self.grid_manager.directional_destinations(ship, occupancy, max_steps=self.dice_roll)

    def _human_can_process_ship(self, ship: Ship) -> bool:
        # Processed ships can't be moved/acted again in this owner turn.
        return ship.hp > 0 and ship.id not in self.human_processed_ship_ids and ship.owner_id == self.active_owner_id

    def _human_queue_ship(self, ship: Ship) -> None:
        if not self._human_can_process_ship(ship):
            return
        if ship.id not in self.human_selected_ship_ids:
            self.human_selected_ship_ids.append(ship.id)
        self.active_ship_id = ship.id
        self.valid_destinations = self._human_select_destinations_for_active_ship()
        self.phase = PHASE_SELECT_DEST

    def _human_mark_active_processed_and_advance(self) -> None:
        if self.active_ship_id is not None:
            self.human_processed_ship_ids.add(self.active_ship_id)

        self.in_range_attack_targets = []
        self.in_range_heal_targets = []

        # Move to the most recently queued ship that hasn't been processed yet.
        next_ship_id = None
        for sid in reversed(self.human_selected_ship_ids):
            if sid not in self.human_processed_ship_ids:
                next_ship_id = sid
                break

        if next_ship_id is None:
            # Nothing left to process in this queue.
            self.active_ship_id = None
            self.valid_destinations = {}
            self._end_turn()
            return

        self.active_ship_id = next_ship_id
        self.valid_destinations = self._human_select_destinations_for_active_ship()
        self.phase = PHASE_SELECT_DEST

    def _human_skip_current_action(self) -> None:
        # Skip attack/heal for the active ship, then continue queue processing.
        self._human_mark_active_processed_and_advance()

    def _handle_human_input(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            # Skip action (if in action phase) OR end the turn (if in selection/move phase).
            self._end_turn()
            return

        if event.type != pygame.MOUSEBUTTONDOWN:
            return

        mx, my = event.pos
        if mx >= GRID_SIZE * TILE_SIZE:
            return
        grid_x = mx // TILE_SIZE
        grid_y = my // TILE_SIZE

        clicked_ship: Optional[Ship] = None
        for s in self._get_ships_of_owner(self.active_owner_id):
            if s.x == grid_x and s.y == grid_y:
                clicked_ship = s
                break

        if self.phase == PHASE_SELECT_SHIP:
            # Clicking any of your ships selects it as the only active ship.
            if clicked_ship is not None:
                self.active_ship_id = clicked_ship.id
                self.in_range_attack_targets = []
                self.in_range_heal_targets = []
                self.valid_destinations = self._human_select_destinations_for_active_ship()
                self.phase = PHASE_SELECT_DEST
            return

        if self.phase == PHASE_SELECT_DEST:
            # Allow retargeting the active ship (click another ship), but never move multiple ships.
            if clicked_ship is not None:
                self.active_ship_id = clicked_ship.id
                self.valid_destinations = self._human_select_destinations_for_active_ship()
                self.in_range_attack_targets = []
                self.in_range_heal_targets = []
                return

            if (grid_x, grid_y) in self.valid_destinations:
                moved = self._try_move_active_ship((grid_x, grid_y))
                if not moved:
                    return

                ship = self._get_ship(self.active_ship_id)
                if ship is not None:
                    enemies, friends = self._compute_human_action_targets(ship)
                    self.in_range_attack_targets = enemies
                    self.in_range_heal_targets = [
                        f
                        for f in friends
                        if ship.ship_type == SHIP_HEALER
                        and f.hp < f.max_hp
                        and ship.heal_cooldown_remaining <= 0
                    ]
                self.phase = PHASE_ACTION
            return

        if self.phase == PHASE_ACTION:
            ship = self._get_ship(self.active_ship_id)
            if ship is None:
                return

            # Try attack or heal based on what is highlighted.
            clicked_target = None
            for t in self.in_range_attack_targets + self.in_range_heal_targets:
                if t.x == grid_x and t.y == grid_y:
                    clicked_target = t
                    break
            if clicked_target is None:
                return

            if clicked_target in self.in_range_attack_targets:
                if self._ship_can_attack(ship):
                    self.combat.perform_attack(ship, clicked_target)
                    self._end_turn()
            elif clicked_target in self.in_range_heal_targets:
                self.combat.perform_heal(ship, clicked_target)
                self._end_turn()

    def _ai_take_turn(self) -> None:
        assert self.ai is not None
        owner_id = self.active_owner_id
        dice_roll = self.dice_roll
        elapsed_seconds = self._elapsed_seconds_since_game_start()

        choice = self.ai.choose_turn(
            owner_id=owner_id,
            ships=self.ships,
            grid_manager=self.grid_manager,
            pickups=self.pickup_list,
            hazard=self.hazard,
            global_turn_index=self.turn_manager.global_turn_index,
            elapsed_seconds_since_game_start=elapsed_seconds,
            dice_roll=dice_roll,
        )

        ship = self._get_ship(choice.ship_id)
        if ship is None:
            self._end_turn()
            return

        # Validate move (should already be valid from AI, but verify reachability).
        occupancy = self.grid_manager.build_occupancy(self.ships)
        dest = choice.moved_to
        allowed = self.grid_manager.directional_destinations(ship, occupancy, max_steps=dice_roll)
        if dest not in allowed:
            self._end_turn()
            return
        ship.x, ship.y = dest

        # Collect pickup
        self.pickups.try_collect(ship, self.pickup_list)

        # Resolve action
        if choice.action_type == "attack" and choice.target_id is not None:
            target = self._get_ship(choice.target_id)
            if target is not None:
                dist = max(abs(ship.x - target.x), abs(ship.y - target.y))
                if dist <= COMBAT_RANGE:
                    self.combat.perform_attack(ship, target)
        elif choice.action_type == "heal" and choice.heal_target_id is not None:
            target = self._get_ship(choice.heal_target_id)
            if target is not None and ship.ship_type == SHIP_HEALER:
                self.combat.perform_heal(ship, target)

        self._end_turn()

    def _start_player_turn(self) -> None:
        # Roll dice for each turn.
        self.dice_roll = self.turn_manager.roll_dice()
        self.active_ship_id = None
        self.valid_destinations = {}
        self.in_range_attack_targets = []
        self.in_range_heal_targets = []
        self.phase = PHASE_SELECT_SHIP

        # Cooldown ticks at start of owner's turn.
        self._decrement_cooldowns_for_owner(self.active_owner_id)

    def run(self) -> None:
        self.clock.tick(FPS)
        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    break

                if self.state == PHASE_MENU:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_1:
                            self.num_opponents = 1
                            self.reset_game()
                        elif event.key == pygame.K_2:
                            self.num_opponents = 2
                            self.reset_game()
                        elif event.key == pygame.K_3:
                            self.num_opponents = 3
                            self.reset_game()
                elif self.state == "playing":
                    if self.active_owner_id == 0:
                        self._handle_human_input(event)
                elif self.state == PHASE_GAME_OVER:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                        self.state = PHASE_MENU

            # AI takes turns automatically when it's an AI owner's turn.
            if self.state == "playing" and self.active_owner_id != 0:
                # AI acts once per update frame to keep logic simple.
                if self.phase == PHASE_SELECT_SHIP:
                    self._ai_take_turn()

            # Rendering
            self._render()
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

    def _render(self) -> None:
        if self.state == PHASE_MENU:
            self.screen.fill((7, 10, 20))
            title_font = pygame.font.SysFont(None, 38)
            title = "Space Grid TBS"
            self.screen.blit(title_font.render(title, True, (230, 235, 255)), (60, 60))

            desc_font = pygame.font.SysFont(None, 28)
            desc = "Select AI opponents (1-3). You are Player 0."
            self.screen.blit(desc_font.render(desc, True, (220, 230, 255)), (60, 120))

            y = 180
            self.screen.blit(desc_font.render("Press 1: 1 AI", True, (220, 230, 255)), (60, y))
            self.screen.blit(desc_font.render("Press 2: 2 AI", True, (220, 230, 255)), (60, y + 30))
            self.screen.blit(desc_font.render("Press 3: 3 AI", True, (220, 230, 255)), (60, y + 60))
            self.screen.blit(desc_font.render("Movement: click ship then click destination tile.", True, (220, 230, 255)), (60, y + 120))
            self.screen.blit(desc_font.render("Action: click an enemy to attack or a friend to heal (healers only).", True, (220, 230, 255)), (60, y + 150))
            return

        # playing / game over
        self.ui.draw_grid()

        elapsed_seconds = self._elapsed_seconds_since_game_start()
        safe_r = self.hazard.safe_radius(self.turn_manager.global_turn_index, elapsed_seconds)
        storm_active = self.turn_manager.global_turn_index >= STORM_START_TURNS
        self.ui.draw_safe_zone(safe_r, storm_active=storm_active)
        self.ui.draw_storm_overlay(storm_active=storm_active)
        self.ui.draw_pickups(self.pickup_list)

        active_ship = self._get_ship(self.active_ship_id) if self.active_ship_id is not None else None

        self.ui.draw_ships(
            self.ships,
            active_ship_id=self.active_ship_id,
            selected_ship_ids=[self.active_ship_id] if self.active_owner_id == 0 and self.active_ship_id is not None else (),
            valid_destinations=[
                (x, y, dist) for (x, y), dist in self.valid_destinations.items()
            ]
            if self.phase == PHASE_SELECT_DEST
            else (),
            in_action_targets=self.in_range_attack_targets if self.phase == PHASE_ACTION else (),
            in_action_friendly_targets=self.in_range_heal_targets if self.phase == PHASE_ACTION else (),
            movement_max_steps=self.dice_roll if self.phase == PHASE_SELECT_DEST else None,
        )

        alive_counts = self._alive_counts()
        self.ui.draw_hud(
            turn_owner_id=self.active_owner_id,
            current_phase=self.phase if self.state == "playing" else "game_over",
            dice_roll=self.dice_roll,
            alive_counts=alive_counts,
            num_opponents=self.num_opponents,
            active_ship=active_ship,
            healing_cooldown_for_active=active_ship.heal_cooldown_remaining if active_ship and active_ship.ship_type == SHIP_HEALER else None,
        )

        if self.state == PHASE_GAME_OVER:
            winner_ids = self._alive_owner_ids()
            winner_text = "Draw" if not winner_ids else ("You win!" if winner_ids[0] == 0 else f"AI {winner_ids[0]} wins!")
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.screen.blit(overlay, (0, 0))
            big_font = pygame.font.SysFont(None, 52)
            self.screen.blit(big_font.render(winner_text, True, (255, 255, 255)), (80, 220))
            small_font = pygame.font.SysFont(None, 22)
            self.screen.blit(small_font.render("Press R to return to menu.", True, (230, 235, 255)), (80, 320))

