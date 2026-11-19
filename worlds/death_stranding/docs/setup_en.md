# Setup guide - Death Stranding Director's Cut (PC)

## Requirements
- Archipelago 0.6.x (run from source: Python 3.12 or 3.13) and `pip install pymem`
- Death Stranding Director's Cut (Steam), played **offline** on a **dedicated save**

## Generating a game
1. Generate your YAML from the Launcher ("Generate Template Options"), `game: Death Stranding`.
2. Put `death_stranding.apworld` in `custom_worlds`, then Generate and Host.
3. Options: `goal`, `trap_percentage`, `starting_episodes`, `episode_gating`, `death_link`, `likes_checks` / `likes_step`, `order_checks` / `order_step`, `standard_checks` / `standard_step`, `bot_checks` / `bot_step`.
   "Episode N Access" items only shape the generation logic: they do not lock the game.

## First client launch
1. Start the game and load your save, then open "Death Stranding Client" and connect: `/connect address:port`.
2. **Inventory:** `/ds_status` should show the amounts; write test (after `/ds_debug on`): `/ds_give Chiral Crystals 10`.
3. **Main orders:** wait for the "Commandes principales : lecture en memoire active …" line (about a minute the first time, a few seconds afterwards). Completing a main order then sends its check.

## How checks are detected
At every checkpoint the game writes "Commande terminée : nº N ..." (French) in the save title. The client reads that title directly from the game's memory and sends
the matching "Order N - ..." check (orders 61 to 65, 67, 68 and 70 are even recognised immediately, by a key the game creates at their end). Only orders completed **after** the client starts count.
If your game is not in French, adjust `saves.completed_words` in `memory_map.json`.

### Save decryption (optional)
As a fallback, or for another language: the third-party tool [DeathStrandingSaveDataResigner](https://github.com/mi5hmash/DeathStrandingSaveDataResigner) (command-line version)
reads the checkpoints on a temporary copy (your saves are never modified). `/ds_resigner <path to the exe>`, then `/ds_selftest`;
`/ds_saves_dir <folder>` if the folder is not found, `/ds_resigner off` / `on` to disable / re-enable it, `/ds_catchup` to process checkpoints that already exist.

## Optional checks
- **Likes milestones:** `likes_checks` checks, one every `likes_step` likes earned since the first connection. `/ds_likes` shows progress.
- **Order progress:** `order_checks` checks, one every `order_step` completed order steps since the first connection. The counter goes up on
  standard deliveries, bot orders, and acceptance and intermediate objectives of main orders (not lost-cargo deliveries). No save needed. `/ds_orders` shows progress.

- **Standard orders:** `standard_checks` checks, one every `standard_step` standard orders delivered since the first connection (the game's exact counter). `/ds_standard` shows progress.
- **Bot orders:** `bot_checks` / `bot_step`, counted live since the first connection (derived from internal game counters). `/ds_bot` shows progress.

## Materials
In game, resins, metals, ceramics, chemicals and special alloys are stored **per facility**, not in the backpack. Received items are credited to the stock of
**one random facility** out of 39 (reproducible; the "applied item" message says which). `/ds_stock_mode target` credits the facility chosen with
`/ds_stock_target`; `/ds_stock_pool Name1; Name2` limits the random draw. `/ds_stock` shows the six values of a facility.

## DeathLink
Enable `death_link` in the YAML and regenerate. The client sends a DeathLink when Sam's health reaches 0 and sets it to 0 when one is received
(once readable: not during loading or menus). A received death is not sent back (20 s) and a sent death blocks sends for 30 s. Validated in game.
Test by hand first: `/ds_hp` shows health, `/ds_debug on` then `/ds_kill` kills Sam.

## Traps
None can kill Sam.
| Item | Effect |
|---|---|
| Injury Trap | -30% of max health (floor: 10%) |
| Fatigue Trap | +3000 fatigue (max 10000) |
| Boot Wear Trap | -40% boot durability (floor: 5%) |
| Rust Trap | -1500 suit condition (min 0) |
| Pickpocket Trap | -50 Chiral Crystals from the backpack (min 0) |

## Useful items with effects
One-shot effects only, nothing permanent.
| Item | Effect |
|---|---|
| Blood Bag | +40% of max health (capped) |
| Energy Drink | -3000 fatigue (min 0) |
| Repair Spray | +50% boot durability and +1500 suit condition (capped) |
| Boot Upgrade | boots repaired to 100% durability |
| Power Skeleton | stamina refilled |
| Speed Skeleton | -2000 fatigue (min 0) |
| Cryptobiote Pack | +5 cryptobiotes in the backpack |
| D-Cryptobiote Pack | +3 D-cryptobiotes in the backpack |
| Sandalweed Bundle | +5 sandalweed in the backpack |

Other equipment items (Cargo Skeleton, Trike, Truck, Road Paver, anchors, ladders, weapons, grenades) have **no in-game effect for now**.
Effects wait until Sam is readable. Test with `/ds_debug on` then `/ds_effect Blood Bag`. Values live in `memory_map.default.json` (sections `traps`, `boosts`, `item_grants`).

## Known limitations
- Only the 51 main orders on the list are checks; the list comes from a community page and may contain mistakes (order 66 is optional (“Fresh Pizza Delivery: Peter Englert”); numbers 6, 10-13, 15, 17, 25, 26, 29, 31, 35-37, 40, 42, 45, 56, 57 are missing).
- "Episode N Access" items lock nothing in game. Victory (last order of the goal episode) is validated in game for No. 70 (episode 14 goal) and No. 68 (episode 12 goal); `/check <location name>` sends a check by hand if it does not go out. With `episode_gating`, victory waits for the access items of every episode up to the goal.
- Memory offsets come from a community table (game v1.004); if `/ds_status` finds nothing while the game is loaded, they do not match your version.
