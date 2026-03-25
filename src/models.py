from __future__ import annotations

from dataclasses import dataclass

from src.config import (
    SHIP_HEALER,
    SHIP_NORMAL,
    SHIP_STATS,
    SHIP_TANK,
)


@dataclass
class Ship:
    id: int
    owner_id: int  # 0=human, 1..N=AIs
    ship_type: str
    x: int
    y: int

    hp: int
    max_hp: int
    damage: int

    heal_cooldown_remaining: int = 0

    @property
    def name(self) -> str:
        if self.ship_type == SHIP_HEALER:
            return "Healing"
        if self.ship_type == SHIP_TANK:
            return "Tank"
        if self.ship_type == SHIP_NORMAL:
            return "Normal"
        return self.ship_type


@dataclass
class Pickup:
    id: int
    x: int
    y: int

    active: bool = True
    respawn_timer: int = 0  # counts down when inactive


def create_ship(ship_id: int, owner_id: int, ship_type: str, x: int, y: int) -> Ship:
    stats = SHIP_STATS[ship_type]
    return Ship(
        id=ship_id,
        owner_id=owner_id,
        ship_type=ship_type,
        x=x,
        y=y,
        hp=stats["max_hp"],
        max_hp=stats["max_hp"],
        damage=stats["damage"],
        heal_cooldown_remaining=0,
    )

