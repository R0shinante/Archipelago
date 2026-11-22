# Setup guide - Death Stranding Director's Cut (PC)

> **Beta.** Play **offline**, in **single player**, on a **dedicated save**. The client reads and writes the game's memory.

## Requirements
- Archipelago 0.6.x (preferably run from source: Python 3.12 or 3.13) and `pip install pymem`
- Death Stranding Director's Cut (Steam), preferably in French (see the README, "Other languages")

## Generating a game
1. Generate your YAML from the Launcher ("Generate Template Options"), `game: Death Stranding`, and set your options (see the README for the full table).
2. Put `death_stranding.apworld` in `custom_worlds`, then Generate and Host.

## First launch of the client
1. Start the game and load your dedicated save, then open "Death Stranding Client" and connect: `/connect address:port`.
2. **Memory access:** `/ds_status` must show your quantities.
3. **Main orders:** wait for the log line "Main orders: memory reading active …" (about a minute the first time, a few seconds afterwards). Completing a main order then sends its check.

If a check does not go out, `/check <exact location name>` sends it by hand. `/locations` lists the location names.

## Optional milestone checks
Set in the YAML: `likes_checks` / `likes_step`, `order_checks` / `order_step`, `standard_checks` / `standard_step` and `bot_checks` / `bot_step`. They are counted since the slot's first connection and need no save. `/ds_likes`, `/ds_orders`, `/ds_standard` and `/ds_bot` show the progress.

## Received items and effects
Effects are one-shot and never change the game's balance permanently. An effect waits until Sam is readable (not during loading or menus).

### Traps
They never kill Sam.

| Item | Effect |
|---|---|
| Injury Trap | -30% of max health (floor: 10%) |
| Fatigue Trap | +3000 fatigue (max 10000) |
| Boot Wear Trap | -40% boot durability (floor: 5%) |
| Rust Trap | -1500 suit condition (min 0) |
| Pickpocket Trap | -50 Chiral Crystals from the backpack (min 0) |

The share of traps is set in the YAML (`trap_percentage`).

### Useful items
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
| Chiral Crystals | +100 chiral crystals in the backpack |
| Likes Pack | +500 likes |

### Equipment (compensation)
Equipment cannot be unlocked in the game by writing memory (each piece is tied to live game objects), so receiving it gives a compensation instead. This part is still to be confirmed in game.

| Item | Compensation |
|---|---|
| Cargo Skeleton | stamina refilled + -1000 fatigue |
| Hematic Grenade Pack | +40% of max health (like a Blood Bag) |
| Trike | +100 metals |
| Truck | +50 special alloys |
| Road Paver | +100 ceramics |
| Zipline Anchor Set | +50 metals |
| Ladder Set | +50 resins |
| Climbing Anchor Set | +50 ceramics |
| Assault Rifle | +100 chemicals |
| Bola Gun | +100 chiral crystals in the backpack |

### Materials
Resins, metals, ceramics, chemicals and special alloys are stored **per facility** in the game, not in the backpack. Each received material item is credited to the stock of **one facility drawn at random** among the 39 (reproducible draw; the "Item applied" log line says which). `/ds_stock_mode target` turns the randomness off and always credits the facility chosen with `/ds_stock_target <facility>`; `/ds_stock_pool Name1; Name2` limits the draw to some facilities (`/ds_stock_pool all` to take them all again). `/ds_stock` shows the six values of a facility (`/ds_stock Port Knot City` for another one): open the facility's menu in game first to compare.

### "Episode N Access"
They do nothing in the game itself. They shape the generation logic and, with `episode_gating`, hold back the checks of an episode until its access is received.

## DeathLink
Enable `death_link` in the YAML and regenerate. The client reads Sam's health: when it drops to 0 it warns the other players, and when a DeathLink is received it sets Sam's health to 0 (as soon as it is readable). A death caused by a DeathLink is not sent back (20 s) and a sent death blocks sending for 30 s.

## Test and diagnostic commands
They are off by default. `/ds_debug on` enables them for the session (`/ds_give`, `/ds_effect`, `/ds_likes_give`, `/ds_stock_give`, `/ds_kill`, `/ds_hp`, `/ds_items_reset`, `/ds_counters`, `/ds_memdiff`, `/ds_memdump`); the values live in `memory_map.default.json` (sections `traps`, `boosts`, `item_grants`). Test an effect with `/ds_debug on` then `/ds_effect Blood Bag`.

## Tracking with PopTracker (optional)
A PopTracker pack (map of the 70 orders, received items, counters, Archipelago autotracking) is available in the release (`death_stranding_poptracker_vX.Y.Z.zip`). Put it in PopTracker's `packs` folder without extracting it, open it, click the grey "AP" and enter server, **slot name** and password. See the README.

## Known limitations
See the README, section "Known limitations".
