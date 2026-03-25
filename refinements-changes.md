# Refinements & Running Log

## Design decisions (early)
- Movement model for MVP: a dice turn moves in a single chosen direction (8-direction straight-line) for exactly `dice` tiles.
  - Rationale: keeps movement validation deterministic and UI interaction simple for an MVP.
- Range metric for “within 3 tiles”: Chebyshev distance (matches 8-direction geometry).
- Storm / safe zone model: safe zone is a Chebyshev-radius square around the board center; radius shrinks over global turns after the storm starts.
- Healing cooldown: cooldown counts down at the start of the healer's owner turn (so it lasts 2 owner-turns).

## Scope shifts
- Turn action: during human action phase, the player selects exactly one action (attack or heal) after moving.
  - Rationale: simplifies UX and avoids handling multi-action turns in the MVP.

## Implementation log
- Implemented core loop, fleet spawning, dice roll per owner turn, movement validation, pickups, combat, healing, storm damage, win condition, and AI decision-making.

## Notes / Known gaps (possible follow-ups)
- UI can be expanded for more explicit “end turn / action done” feedback.
- AI scoring can be tuned after playtesting (weights, target selection, pickup seeking, safe-zone urgency).

