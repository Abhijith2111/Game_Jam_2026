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
    HEAL_AMOUNT,
    HUD_WIDTH,
    GRID_SIZE,
    TILE_SIZE,
    PLAYER_COLORS,
    COMBAT_RANGE,
    HEAL_RANGE,
)
from src.models import Ship


def _format_match_elapsed(seconds: float) -> str:
    total = int(max(0.0, seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


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

    def draw_space_background_fullscreen(self, screen_width: int, screen_height: int) -> None:
        # Tile the prebuilt starfield to cover the entire window.
        for y in range(0, screen_height, self.grid_px):
            for x in range(0, screen_width, self.grid_px):
                self.screen.blit(self.star_bg, (x, y))

        # Subtle dark overlay for menu text readability.
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 35))
        self.screen.blit(overlay, (0, 0))

    def _draw_health_bar(self, *, x: int, y: int, w: int, h: int, hp: int, max_hp: int) -> None:
        # Color-coded HP bar (green -> red).
        ratio = 0.0 if max_hp <= 0 else hp / max_hp
        ratio = max(0.0, min(1.0, ratio))

        track_rect = pygame.Rect(x, y, w, h)
        border_radius = max(1, min(10, h // 5))
        pygame.draw.rect(self.screen, (20, 20, 25), track_rect, border_radius=border_radius)

        if ratio <= 0:
            return

        fill_w = max(1, int(w * ratio))
        fill_rect = pygame.Rect(x, y, fill_w, h)

        r = int(255 * (1.0 - ratio))
        g = int(255 * ratio)
        b = 70
        pygame.draw.rect(self.screen, (r, g, b), fill_rect, border_radius=border_radius)

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
        # When `TILE_SIZE` is scaled (e.g. 10x), a lot of the ship art/padding used
        # to rely on hard-coded pixel offsets. This scale factor keeps those
        # offsets proportional.
        scale = max(1, TILE_SIZE // 20)

        # Valid destination squares for movement selection
        for (x, y, dist) in valid_destinations:
            px, py = self.grid_to_px(x, y)
            pad = 1 * scale
            rect = pygame.Rect(px + pad, py + pad, TILE_SIZE - 2 * pad, TILE_SIZE - 2 * pad)
            if movement_max_steps is not None and dist == movement_max_steps:
                pygame.draw.rect(self.screen, (255, 220, 60), rect, 3)
            elif dist == 0:
                pygame.draw.rect(self.screen, (120, 255, 160), rect, 3)
            else:
                pygame.draw.rect(self.screen, (80, 220, 255), rect, 1)

        # Action target highlights
        for t in in_action_targets:
            px, py = self.grid_to_px(t.x, t.y)
            pad = 1 * scale
            rect = pygame.Rect(px + pad, py + pad, TILE_SIZE - 2 * pad, TILE_SIZE - 2 * pad)
            pygame.draw.rect(self.screen, (255, 80, 80), rect, 3)

        for t in in_action_friendly_targets:
            px, py = self.grid_to_px(t.x, t.y)
            pad = 1 * scale
            rect = pygame.Rect(px + pad, py + pad, TILE_SIZE - 2 * pad, TILE_SIZE - 2 * pad)
            pygame.draw.rect(self.screen, (80, 255, 150), rect, 3)

        # Ships
        for s in ships:
            if s.hp <= 0:
                continue
            color = PLAYER_COLORS.get(s.owner_id, COLOR_PLAYER0)
            px, py = self.grid_to_px(s.x, s.y)
            ship_pad = 2 * scale
            rect = pygame.Rect(px + ship_pad, py + ship_pad, TILE_SIZE - 2 * ship_pad, TILE_SIZE - 2 * ship_pad)

            cx = px + TILE_SIZE // 2
            cy = py + TILE_SIZE // 2

            # Galaga-style procedural art (no sprite assets).
            if s.ship_type == "healer":
                edge = 3 * scale
                core_top = 5 * scale
                core_span = 10 * scale
                ant_w = 2 * scale
                ant_h = 5 * scale

                # Diamond hull
                points = [
                    (cx, py + edge),
                    (px + TILE_SIZE - edge, cy),
                    (cx, py + TILE_SIZE - edge),
                    (px + edge, cy),
                ]
                pygame.draw.polygon(self.screen, color, points)
                # Cross core
                arm_w = max(2, TILE_SIZE // 6)
                pygame.draw.rect(
                    self.screen,
                    (255, 255, 255),
                    (cx - arm_w // 2, py + core_top, arm_w, TILE_SIZE - core_span),
                )
                pygame.draw.rect(
                    self.screen,
                    (255, 255, 255),
                    (px + core_top, cy - arm_w // 2, TILE_SIZE - core_span, arm_w),
                )
                # Antenna
                pygame.draw.rect(
                    self.screen,
                    (255, 255, 255),
                    (cx - (ant_w // 2), py, ant_w, ant_h),
                )
                pygame.draw.circle(self.screen, (255, 240, 180), (cx, py + scale), 2 * scale)
            elif s.ship_type == "tank":
                base_pad_x = 4 * scale
                base_pad_y = 9 * scale
                base_w_pad = 8 * scale
                base_h_pad = 7 * scale

                turret_x = 3 * scale
                turret_y = 3 * scale
                turret_sz = 6 * scale

                # Bulky hull + turret
                base = pygame.Rect(px + base_pad_x, py + base_pad_y, TILE_SIZE - base_w_pad, TILE_SIZE - base_h_pad)
                pygame.draw.rect(self.screen, color, base, border_radius=3)
                turret = pygame.Rect(cx - turret_x, py + turret_y, turret_sz, turret_sz)
                pygame.draw.rect(self.screen, color, turret, border_radius=2)
                # Barrel
                barrel_w = max(1, 2 * scale)
                pygame.draw.line(self.screen, (255, 255, 255), (cx, py + base_pad_y), (cx, py + 13 * scale), barrel_w)
                # Windows
                pygame.draw.circle(self.screen, (255, 255, 255), (cx - 4 * scale, cy + 3 * scale), 2 * scale)
                pygame.draw.circle(self.screen, (255, 255, 255), (cx + 4 * scale, cy + 3 * scale), 2 * scale)
            else:
                edge = 3 * scale
                tip_pad = 4 * scale
                wing_x_pad = 2 * scale
                wing_y_pad = 9 * scale
                wing_w = 5 * scale
                wing_h = 3 * scale

                # Fighter triangle
                pts = [
                    (cx, py + edge),
                    (px + edge, py + TILE_SIZE - tip_pad),
                    (px + TILE_SIZE - tip_pad, py + TILE_SIZE - tip_pad),
                ]
                pygame.draw.polygon(self.screen, color, pts)
                # Wings
                pygame.draw.rect(
                    self.screen, (255, 255, 255), (px + wing_x_pad, py + TILE_SIZE - wing_y_pad, wing_w, wing_h)
                )
                pygame.draw.rect(
                    self.screen, (255, 255, 255), (px + TILE_SIZE - 7 * scale, py + TILE_SIZE - wing_y_pad, wing_w, wing_h)
                )
                # Engine glow
                pygame.draw.circle(
                    self.screen, (255, 240, 180), (cx, py + TILE_SIZE - 6 * scale), 2 * scale
                )

            # Health bar above the ship (color-coded; no numeric text).
            bar_pad_x = 4 * scale
            bar_h = max(3 * scale, TILE_SIZE // 10)
            self._draw_health_bar(
                x=px + 2 * scale,
                y=py + 1 * scale,
                w=TILE_SIZE - bar_pad_x,
                h=bar_h,
                hp=s.hp,
                max_hp=s.max_hp,
            )

            is_selected = s.id in set(selected_ship_ids)
            if is_selected and (active_ship_id is None or s.id != active_ship_id):
                pygame.draw.rect(self.screen, (150, 100, 255), rect, max(1, 2 * scale), border_radius=3)

            if active_ship_id is not None and s.id == active_ship_id:
                pygame.draw.rect(self.screen, (255, 220, 60), rect, max(1, 2 * scale))

    def draw_pickups(self, pickups: Sequence[object], *, active: bool = True) -> None:
        scale = max(1, TILE_SIZE // 20)
        # pickups are `Pickup` models; we draw active ones.
        for p in pickups:
            if not getattr(p, "active", False):
                continue
            px, py = self.grid_to_px(p.x, p.y)
            cx = px + TILE_SIZE // 2
            cy = py + TILE_SIZE // 2
            glow_r = max(3 * scale, TILE_SIZE // 3)
            pygame.draw.circle(self.screen, (*COLOR_PICKUP,), (cx, cy), glow_r)
            # Medkit cross
            arm = max(2 * scale, TILE_SIZE // 6)
            pad = 2 * scale
            pygame.draw.rect(
                self.screen,
                (255, 255, 255),
                (cx - arm // 2, cy - glow_r + pad, arm, glow_r * 2 - 2 * pad),
            )
            pygame.draw.rect(
                self.screen,
                (255, 255, 255),
                (cx - glow_r + pad, cy - arm // 2, glow_r * 2 - 2 * pad, arm),
            )
            # Outer border
            pygame.draw.circle(self.screen, COLOR_PICKUP, (cx, cy), glow_r, max(1, 2 * scale))

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
        elapsed_seconds: float,
    ) -> None:
        hud_x = GRID_SIZE * TILE_SIZE
        hud = pygame.Rect(hud_x, 0, HUD_WIDTH, GRID_SIZE * TILE_SIZE)
        pygame.draw.rect(self.screen, (10, 10, 14), hud, 0)
        pygame.draw.line(self.screen, COLOR_GRID, (hud_x, 0), (hud_x, hud.height), 2)

        title = "Galactic Warfare Survival"
        self.screen.blit(self.font.render(title, True, COLOR_TEXT), (hud_x + 14, 14))

        owner_label = "Player (You)" if turn_owner_id == 0 else f"AI {turn_owner_id}"
        self.screen.blit(self.small_font.render(f"Turn: {owner_label}", True, COLOR_TEXT), (hud_x + 14, 42))
        self.screen.blit(self.small_font.render(f"Move up to: {dice_roll}", True, COLOR_TEXT), (hud_x + 14, 68))
        dice_size = max(34, min(52, int(TILE_SIZE * 1.5)))
        self._draw_dice_icon(dice_roll, hud_x + HUD_WIDTH - 70, 58, size=dice_size)

        self.screen.blit(self.small_font.render(f"Phase: {current_phase}", True, COLOR_TEXT), (hud_x + 14, 94))
        time_str = _format_match_elapsed(elapsed_seconds)
        self.screen.blit(
            self.small_font.render(f"Time: {time_str}", True, COLOR_TEXT),
            (hud_x + 14, 120),
        )

        # Alive ships per owner
        y = 166
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

            self.screen.blit(
                self.small_font.render(f"Damage: {active_ship.damage}", True, COLOR_TEXT),
                (hud_x + 14, y),
            )
            y += 20
            self.screen.blit(
                self.small_font.render(f"Max HP: {active_ship.max_hp}", True, COLOR_TEXT),
                (hud_x + 14, y),
            )
            y += 20
            if active_ship.ship_type == "healer":
                self.screen.blit(
                    self.small_font.render(f"Heal: {HEAL_AMOUNT}", True, COLOR_TEXT),
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

