from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pygame

from src.config import (
    COLOR_BG,
    COLOR_GRID,
    COLOR_PICKUP,
    COLOR_SAFE_ZONE,
    COLOR_STORM_OVERLAY,
    COLOR_TEXT,
    COLOR_PLAYER0,
    HUD_WIDTH,
    GRID_SIZE,
    TILE_SIZE,
    PLAYER_COLORS,
    COMBAT_RANGE,
    HEAL_RANGE,
)
from src.models import Ship


@dataclass(frozen=True)
class UIButtonHint:
    label: str
    key: str


class UI:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont(None, 32)
        self.small_font = pygame.font.SysFont(None, 22)

        self.grid_px = GRID_SIZE * TILE_SIZE
        self._build_starfield()

    def _build_starfield(self) -> None:
        self.star_bg = pygame.Surface((self.grid_px, self.grid_px))
        self.star_bg.fill(COLOR_BG)

        rng = random.Random(1337)
        star_count = (self.grid_px * self.grid_px) // 3000
        star_count = max(250, min(1500, star_count))
        for _ in range(star_count):
            x = rng.randrange(0, self.grid_px)
            y = rng.randrange(0, self.grid_px)
            r = rng.choice([1, 1, 2])
            col = rng.choice(
                [(200, 210, 255), (255, 255, 255), (180, 255, 240), (255, 210, 140)]
            )
            pygame.draw.circle(self.star_bg, col, (x, y), r)

        # Nebula blobs (simple placeholder)
        for _ in range(6):
            cx = rng.randrange(0, self.grid_px)
            cy = rng.randrange(0, self.grid_px)
            radius = rng.randrange(max(10, self.grid_px // 8), max(11, self.grid_px // 4))
            col = rng.choice([(40, 80, 180), (80, 40, 160), (40, 160, 140)])
            blob = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(blob, (*col, 40), (radius, radius), radius)
            self.star_bg.blit(blob, (cx - radius, cy - radius))

    def grid_to_px(self, x: int, y: int) -> Tuple[int, int]:
        return x * TILE_SIZE, y * TILE_SIZE

    def draw_grid(self) -> None:
        self.screen.blit(self.star_bg, (0, 0))
        # Draw grid overlay.
        for i in range(GRID_SIZE + 1):
            px = i * TILE_SIZE
            pygame.draw.line(self.screen, COLOR_GRID, (px, 0), (px, self.grid_px), 1)
            pygame.draw.line(self.screen, COLOR_GRID, (0, px), (self.grid_px, px), 1)

    def draw_safe_zone(self, safe_radius: int, storm_active: bool) -> None:
        # Chebyshev distance => axis-aligned square of tiles.
        cx = GRID_SIZE // 2
        cy = GRID_SIZE // 2
        left = (cx - safe_radius) * TILE_SIZE
        right = (cx + safe_radius + 1) * TILE_SIZE
        top = (cy - safe_radius) * TILE_SIZE
        bottom = (cy + safe_radius + 1) * TILE_SIZE

        overlay = pygame.Surface((self.grid_px, self.grid_px), pygame.SRCALPHA)
        alpha = 70 if not storm_active else 95
        pygame.draw.rect(
            overlay,
            (*COLOR_SAFE_ZONE, alpha),
            pygame.Rect(left, top, right - left, bottom - top),
            width=0,
            border_radius=0,
        )
        self.screen.blit(overlay, (0, 0))

        pygame.draw.rect(
            self.screen,
            COLOR_SAFE_ZONE,
            pygame.Rect(left, top, right - left, bottom - top),
            2,
        )

    def draw_storm_overlay(self, storm_active: bool) -> None:
        if not storm_active:
            return
        overlay = pygame.Surface((self.grid_px, self.grid_px), pygame.SRCALPHA)
        pygame.draw.rect(
            overlay,
            (*COLOR_STORM_OVERLAY, 25),
            pygame.Rect(0, 0, self.grid_px, self.grid_px),
        )
        self.screen.blit(overlay, (0, 0))

    def draw_ships(
        self,
        ships: Sequence[Ship],
        *,
        active_ship_id: Optional[int] = None,
        selected_ship_ids: Sequence[int] = (),
        valid_destinations: Sequence[Tuple[int, int, int]] = (),
        movement_max_steps: Optional[int] = None,
        in_action_targets: Sequence[Ship] = (),
        in_action_friendly_targets: Sequence[Ship] = (),
    ) -> None:
        # Valid destination squares for movement selection
        for (x, y, dist) in valid_destinations:
            px, py = self.grid_to_px(x, y)
            rect = pygame.Rect(px + 1, py + 1, TILE_SIZE - 2, TILE_SIZE - 2)
            if movement_max_steps is not None and dist == movement_max_steps:
                pygame.draw.rect(self.screen, (255, 220, 60), rect, 3)
            elif dist == 0:
                pygame.draw.rect(self.screen, (120, 255, 160), rect, 3)
            else:
                pygame.draw.rect(self.screen, (80, 220, 255), rect, 1)

        # Action target highlights
        for t in in_action_targets:
            px, py = self.grid_to_px(t.x, t.y)
            rect = pygame.Rect(px + 1, py + 1, TILE_SIZE - 2, TILE_SIZE - 2)
            pygame.draw.rect(self.screen, (255, 80, 80), rect, 3)

        for t in in_action_friendly_targets:
            px, py = self.grid_to_px(t.x, t.y)
            rect = pygame.Rect(px + 1, py + 1, TILE_SIZE - 2, TILE_SIZE - 2)
            pygame.draw.rect(self.screen, (80, 255, 150), rect, 3)

        # Ships
        for s in ships:
            if s.hp <= 0:
                continue
            color = PLAYER_COLORS.get(s.owner_id, COLOR_PLAYER0)
            px, py = self.grid_to_px(s.x, s.y)
            rect = pygame.Rect(px + 2, py + 2, TILE_SIZE - 4, TILE_SIZE - 4)

            cx = px + TILE_SIZE // 2
            cy = py + TILE_SIZE // 2

            # Galaga-style procedural art (no sprite assets).
            if s.ship_type == "healer":
                # Diamond hull
                points = [
                    (cx, py + 3),
                    (px + TILE_SIZE - 3, cy),
                    (cx, py + TILE_SIZE - 3),
                    (px + 3, cy),
                ]
                pygame.draw.polygon(self.screen, color, points)
                # Cross core
                arm_w = max(2, TILE_SIZE // 6)
                pygame.draw.rect(
                    self.screen,
                    (255, 255, 255),
                    (cx - arm_w // 2, py + 5, arm_w, TILE_SIZE - 10),
                )
                pygame.draw.rect(
                    self.screen,
                    (255, 255, 255),
                    (px + 5, cy - arm_w // 2, TILE_SIZE - 10, arm_w),
                )
                # Antenna
                pygame.draw.rect(self.screen, (255, 255, 255), (cx - 1, py + 0, 2, 5))
                pygame.draw.circle(self.screen, (255, 240, 180), (cx, py + 1), 2)
            elif s.ship_type == "tank":
                # Bulky hull + turret
                base = pygame.Rect(px + 4, py + 9, TILE_SIZE - 8, TILE_SIZE - 7)
                pygame.draw.rect(self.screen, color, base, border_radius=3)
                turret = pygame.Rect(cx - 3, py + 3, 6, 6)
                pygame.draw.rect(self.screen, color, turret, border_radius=2)
                # Barrel
                pygame.draw.line(self.screen, (255, 255, 255), (cx, py + 9), (cx, py + 13), 2)
                # Windows
                pygame.draw.circle(self.screen, (255, 255, 255), (cx - 4, cy + 3), 2)
                pygame.draw.circle(self.screen, (255, 255, 255), (cx + 4, cy + 3), 2)
            else:
                # Fighter triangle
                pts = [
                    (cx, py + 3),
                    (px + 3, py + TILE_SIZE - 4),
                    (px + TILE_SIZE - 4, py + TILE_SIZE - 4),
                ]
                pygame.draw.polygon(self.screen, color, pts)
                # Wings
                pygame.draw.rect(
                    self.screen, (255, 255, 255), (px + 2, py + TILE_SIZE - 9, 5, 3)
                )
                pygame.draw.rect(
                    self.screen, (255, 255, 255), (px + TILE_SIZE - 7, py + TILE_SIZE - 9, 5, 3)
                )
                # Engine glow
                pygame.draw.circle(self.screen, (255, 240, 180), (cx, py + TILE_SIZE - 6), 2)

            is_selected = s.id in set(selected_ship_ids)
            if is_selected and (active_ship_id is None or s.id != active_ship_id):
                pygame.draw.rect(self.screen, (150, 100, 255), rect, 2, border_radius=3)

            if active_ship_id is not None and s.id == active_ship_id:
                pygame.draw.rect(self.screen, (255, 220, 60), rect, 2)

    def draw_pickups(self, pickups: Sequence[object], *, active: bool = True) -> None:
        # pickups are `Pickup` models; we draw active ones.
        for p in pickups:
            if not getattr(p, "active", False):
                continue
            px, py = self.grid_to_px(p.x, p.y)
            cx = px + TILE_SIZE // 2
            cy = py + TILE_SIZE // 2
            glow_r = max(3, TILE_SIZE // 3)
            pygame.draw.circle(self.screen, (*COLOR_PICKUP,), (cx, cy), glow_r)
            # Medkit cross
            arm = max(2, TILE_SIZE // 6)
            pygame.draw.rect(self.screen, (255, 255, 255), (cx - arm // 2, cy - glow_r + 2, arm, glow_r * 2 - 4))
            pygame.draw.rect(self.screen, (255, 255, 255), (cx - glow_r + 2, cy - arm // 2, glow_r * 2 - 4, arm))
            # Outer border
            pygame.draw.circle(self.screen, COLOR_PICKUP, (cx, cy), glow_r, 2)

    def _draw_dice_icon(self, value: int, x: int, y: int, size: int = 46) -> None:
        # Simple procedural “dice image” for the HUD.
        rect = pygame.Rect(x, y, size, size)
        pygame.draw.rect(self.screen, (245, 245, 245), rect, border_radius=8)
        pygame.draw.rect(self.screen, (20, 20, 20), rect, width=2, border_radius=8)

        pip_r = max(3, size // 10)
        cx = x + size // 2
        cy = y + size // 2
        step = size // 3

        pip_positions = {
            1: [(0, 0)],
            2: [(-1, -1), (1, 1)],
            3: [(-1, -1), (0, 0), (1, 1)],
            4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
            5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
            6: [(-1, -1), (0, -1), (1, -1), (-1, 1), (0, 1), (1, 1)],
        }.get(value, [(0, 0)])

        for ox, oy in pip_positions:
            px = cx + ox * step // 2
            py = cy + oy * step // 2
            pygame.draw.circle(self.screen, (30, 30, 30), (px, py), pip_r)

    def draw_hud(
        self,
        *,
        turn_owner_id: int,
        current_phase: str,
        dice_roll: int,
        alive_counts: Dict[int, int],
        num_opponents: int,
        active_ship: Optional[Ship],
        healing_cooldown_for_active: Optional[int],
    ) -> None:
        hud_x = GRID_SIZE * TILE_SIZE
        hud = pygame.Rect(hud_x, 0, HUD_WIDTH, GRID_SIZE * TILE_SIZE)
        pygame.draw.rect(self.screen, (10, 10, 14), hud, 0)
        pygame.draw.line(self.screen, COLOR_GRID, (hud_x, 0), (hud_x, hud.height), 2)

        title = "Space Grid TBS"
        self.screen.blit(self.font.render(title, True, COLOR_TEXT), (hud_x + 14, 14))

        owner_label = "Player (You)" if turn_owner_id == 0 else f"AI {turn_owner_id}"
        self.screen.blit(self.small_font.render(f"Turn: {owner_label}", True, COLOR_TEXT), (hud_x + 14, 42))
        self.screen.blit(self.small_font.render(f"Move up to: {dice_roll}", True, COLOR_TEXT), (hud_x + 14, 68))
        self._draw_dice_icon(dice_roll, hud_x + HUD_WIDTH - 70, 58, size=52)

        self.screen.blit(self.small_font.render(f"Phase: {current_phase}", True, COLOR_TEXT), (hud_x + 14, 94))

        # Alive ships per owner
        y = 140
        self.screen.blit(self.small_font.render("Ships alive:", True, COLOR_TEXT), (hud_x + 14, y))
        y += 22
        for pid in range(0, 1 + num_opponents):
            cnt = alive_counts.get(pid, 0)
            label = "You" if pid == 0 else f"AI {pid}"
            self.screen.blit(self.small_font.render(f"{label}: {cnt}", True, COLOR_TEXT), (hud_x + 14, y))
            y += 20

        y += 10
        if active_ship is None or active_ship.hp <= 0:
            self.screen.blit(self.small_font.render("Active ship: None", True, COLOR_TEXT), (hud_x + 14, y))
        else:
            self.screen.blit(self.small_font.render(f"Active: {active_ship.name}", True, COLOR_TEXT), (hud_x + 14, y))
            y += 22
            self.screen.blit(
                self.small_font.render(f"HP: {active_ship.hp}/{active_ship.max_hp}", True, COLOR_TEXT),
                (hud_x + 14, y),
            )
            y += 20

            if healing_cooldown_for_active is not None:
                self.screen.blit(
                    self.small_font.render(f"Heal CD: {healing_cooldown_for_active}", True, COLOR_TEXT),
                    (hud_x + 14, y),
                )
                y += 20

        # Controls
        y = hud.height - 120
        self.screen.blit(self.small_font.render("Controls:", True, COLOR_TEXT), (hud_x + 14, y))
        y += 22
        self.screen.blit(self.small_font.render("Click ship: select ship", True, COLOR_TEXT), (hud_x + 14, y))
        y += 20
        self.screen.blit(self.small_font.render("Click tile: move", True, COLOR_TEXT), (hud_x + 14, y))
        y += 20
        self.screen.blit(self.small_font.render("Click target: attack/heal", True, COLOR_TEXT), (hud_x + 14, y))
        y += 20
        if current_phase == "action_choice":
            self.screen.blit(self.small_font.render("Space: skip action and end turn", True, COLOR_TEXT), (hud_x + 14, y))
        else:
            self.screen.blit(self.small_font.render("Space: end turn", True, COLOR_TEXT), (hud_x + 14, y))

