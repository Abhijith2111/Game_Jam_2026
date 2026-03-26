## Development Plan

### Goals
- Create a working MVP of a 2D top-down, turn-based strategy game on a `50x50` grid.
- Player vs 1–3 AI opponents.
- Each player controls 6 ships: 2 Healing, 2 Tank, 2 Normal.
- Win condition: last player with ships remaining.

### Ship Rules (MVP)
- Healing Ship
  - HP: 70
  - Damage: 1
  - Ability: heal a friendly ship within 3 tiles, heals 10 HP
  - Cooldown: 2 turns
- Tank Ship
  - HP: 120
  - Damage: 5
- Normal Ship
  - HP: 80
  - Damage: 3

### Turn Flow (MVP)
- Roll a dice each owner turn (default `1–6`).
- Select exactly one ship.
- Move it exactly that many tiles (8-direction, straight-line move in one chosen direction).
- Resolve pickup collection on landing.
- Resolve one action (attack or heal) when available.
- Apply asteroid storm damage (if outside the safe zone).

```mermaid
flowchart TD
  A[Start Owner Turn] --> B[Roll Dice 1-6]
  B --> C[Select Active Ship]
  C --> D[Move Exactly Dice Tiles (8-dir straight line)]
  D --> E[Resolve Pickup on Landing]
  E --> F[Resolve Combat/Heal Action]
  F --> G[End-of-Turn Hazard Damage]
  G --> H[Win Check]
  H -->|Game over| I[Stop]
  H -->|Next Owner| A
```

### System Milestones
1. Core loop + board + dice movement
   - Grid + movement validation
   - Range-3 combat + destruction + win condition
2. Healing + pickups
   - Healing cooldown and heal range
   - Health pickups spawn, despawn on collect, respawn after 5 turns
3. Hazard system (asteroid storm)
   - Safe zone shrinking over time
   - Damage when outside safe zone
4. AI + UI polish
   - AI chooses ship, moves strategically, and decides between attack/heal/positioning
   - Difficulty scaling for 1–3 opponents
   - HUD: dice roll, turn info, selected ship HP

### AI Approach (MVP)
- Enumerate candidate moves (each ship, each of 8 straight directions for `dice` steps).
- Score candidate outcomes using weighted priorities:
  - attack enemies within range (range = 3)
  - heal allies when possible (healer + cooldown ready)
  - seek health pickups when low HP
  - seek safe zone during storm
- Choose the highest-scoring move; add slight randomness to avoid loops.
- Difficulty scaling: increase attack/heal weights as the number of AI opponents increases.

### Task List
- Scaffold Python/Pygame project (entrypoint, game loop, module structure)
- Implement GridManager, TurnManager, dice-based movement, range-3 combat, win condition
- Implement Healing cooldown + healing, pickup spawn/collect/respawn
- Implement asteroid storm safe-zone shrink + outside damage
- Implement AIController (ship selection + movement + action choice)
- Implement UI HUD and interaction highlights
- Documentation + GitHub connection

### AI Tools Used
- Development assistance was guided with AI support in `Cursor IDE` and `ChatGPT/OpenAI` for planning and implementation help.

### Reflection on AI Use
The AI excelled at turning my prompts into a functioning MVP quickly—especially in scaffolding the 2D top-down, turn-based structure, wiring up the core loop, and iterating until the game became playable.

At the same time, it limited my scope in a helpful way: it steered the project toward a simpler 2D approach to reduce complexity and avoid overloading the AI with requirements that were too large for the timeframe.

It also changed my creative/technical process by taking on a lot of the execution work (writing and updating code, handling integration steps, and pushing updates to GitHub), so my role shifted more toward reviewing, guiding, and validating behavior.

I was transparent about my use of AI throughout the game jam process, and I credited the AI tools as part of the development workflow.

