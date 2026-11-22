# Death Stranding (Director's Cut, PC/Steam) — Archipelago APWorld

[🇫🇷 Français](README.md) · 🇬🇧 English

[Archipelago](https://archipelago.gg) world and client for **Death Stranding Director's Cut** (PC, Steam).
Unofficial project, not affiliated with Kojima Productions, 505 Games or the Archipelago team.

> ⚠️ **Beta.** Use it **offline**, in **single player**, on a **dedicated save**.
> The client reads and writes the game's memory: never use it online, and back up your saves before you start.

## Contents

1. [What the mod does](#what-the-mod-does)
2. [Installation](#installation)
3. [Configuration (YAML)](#configuration-yaml)
4. [Starting a game](#starting-a-game)
5. [Tracking with PopTracker](#tracking-with-poptracker-optional)
6. [Client commands](#client-commands)
7. [Troubleshooting](#troubleshooting)
8. [Known limitations](#known-limitations)

## What the mod does

- **Checks:** the 70 main orders (no. 1 to 70), detected automatically from the game's memory. Optionally: milestones for likes, order steps, standard orders and bot orders.
- **Received items, applied in game by the client:** Chiral Crystals, materials (a facility's stock), likes, one-shot effects (healing, fatigue, boots, stamina, cryptobiotes…), traps, and a **compensation** for equipment (see [the guide](docs/setup_en.md)).
- **DeathLink:** sending and receiving Sam's death.
- **Victory:** complete the last order of the goal episode (14, or 12 depending on the `goal` option).
- **"Episode N Access" items:** they shape the generation logic and, with `episode_gating`, hold back the checks of an episode until its access is received. The game itself is **never locked**: nothing stops you from playing the story without having received them.

What is **not** done: locking episodes in game, unlocking real equipment, per-order checks for standard or optional orders.

### How reliable is order detection?

| Level | Orders | Detail |
|---|---|---|
| ✅ Validated in game | 2 to 12, 14 to 16, 18 to 30, 32 to 36, 38 to 44, 46 to 55, 58 to 65, 67 to 70 | The game creates a key of its own when the order ends: detection on delivery, and catch-up when the client starts |
| 🟡 Not replayed yet | 13, 17, 31, 37, 45, 56, 57, 66 | Same mechanism (keys read from the game files). If one is reported too early, too late or never: `/check <location>` and, if you can, a `/ds_debug on` then `/ds_counters watch on` capture in an issue |
| ⚪ Through the save title | 1 | Seen a few seconds after the game's checkpoint, or found by inference |

In addition, the client reads the title of each checkpoint ("Order completed: No. N …") and **infers** that mandatory orders of earlier episodes are done when the title shows a later episode. Optional orders are never inferred. Technical details are in [`death_stranding_research/RECHERCHE_compteurs_commandes.md`](https://github.com/R0shinante/Archipelago/blob/death-stranding/death_stranding_research/RECHERCHE_compteurs_commandes.md) (on the repository branch, outside the APWorld; in French).

## Installation

| Item | Detail |
|---|---|
| System | **Windows**, Death Stranding Director's Cut (Steam), preferably **in French** (see [Other languages](#other-languages)) |
| Archipelago | **0.6.x**, preferably **from source** (<https://github.com/ArchipelagoMW/Archipelago>) |
| Python | **3.12 or 3.13** if you use the sources (on Windows: 3.12.10 or newer; 3.10, 3.11 and 3.14 do not work) |
| pymem | Python library that lets the client access the game's memory |

1. **APWorld**, one of the two methods only (otherwise the world is loaded twice):
   - from a release: put `death_stranding.apworld` in Archipelago's `custom_worlds` folder;
   - from this repository: copy the `death_stranding` folder into Archipelago's `worlds` folder.
2. **pymem** (replace `3.12` with your Python version):
   ```
   py -3.12 -m pip install pymem
   ```
   With the official Archipelago installer, install `pymem` in the Python that runs the client; the sources are recommended for this world.

## Configuration (YAML)

1. In the Archipelago Launcher, click **Generate Template Options**.
2. Open `Death Stranding.yaml`, check `game: Death Stranding` and set your `name:`.
3. Adjust the options, then put the file in the `Players` folder.

| Option | Values | Default | Role |
|---|---|---|---|
| `goal` | `finish_episode_14`, `finish_episode_12` | `finish_episode_14` | Victory condition |
| `trap_percentage` | 0 to 100 | 15 | Share of filler turned into traps |
| `episode_gating` | `false`, `true` | `false` | Holds back the checks of episode N until "Episode 1 Access" to "Episode N Access" are received (`/ds_held` lists held checks) |
| `starting_episodes` | 0 to 5 | 0 | "Episode N Access" items given at the start (random, episode 1 included) |
| `death_link` | true / false | false | DeathLink |
| `likes_checks` / `likes_step` | 0 to 50 / 100 to 10000 | 0 / 1000 | Number of likes checks (0 = disabled) / likes per milestone |
| `order_checks` / `order_step` | 0 to 100 / 1 to 50 | 0 / 3 | Order-progress checks / steps per milestone |
| `standard_checks` / `standard_step` | 0 to 100 / 1 to 50 | 0 / 3 | Standard orders delivered checks / orders per milestone |
| `bot_checks` / `bot_step` | 0 to 100 / 1 to 50 | 0 / 3 | Bot orders delivered checks / orders per milestone |

**Milestones** (likes, steps, standard, bot) are counted **since the slot's first connection** (the baseline is set then) and need no save. `/ds_likes`, `/ds_orders`, `/ds_standard` and `/ds_bot` show progress, `/ds_..._rebase` resets the baseline. Likes received through "Likes Pack" items do not count.

- **Order progress:** counts completed objective steps, all types combined (standard deliveries, bots, objectives of a main order); returned lost cargo is not counted.
- **Standard orders:** the game's exact counter. They only exist in game after no. 9.
- **Bot orders:** counter derived from two internal game counters; the check arrives about 90 s after the delivery. They only exist from about no. 24, and the counter this calculation relies on is missing from some saves: `/ds_bot` then says "unavailable for now" and no bot milestone goes out (the rest works). If this persists after several bot deliveries, set `bot_checks` to 0. Returned lost cargo counts like a bot delivery.

Once the YAML is ready: Launcher → **Generate** (the `AP_xxxxxxxx.zip` appears in `output`), then **Host**, and note the address (default `localhost:38281`).

> **Redo this for every new APWorld version:** a game generated with an older version may contain locations the server does not know (the client reports "Location … does not exist in the hosted game").

## Starting a game

1. Start Death Stranding **offline** and load your dedicated save.
2. In the Launcher, open **Death Stranding Client** and connect: `/connect localhost:38281`.
3. **Check memory access:** `/ds_status` must show your Chiral Crystals quantities.
4. **Wait for the first search to finish:** the log shows "Main orders: memory reading active …" (about a minute the first time, a few seconds afterwards).
5. **Play.** Complete a main order: the client sends the check and the server hands out the items, which appear in the client console.

When the client starts, orders already completed whose end key is present in the loaded game are caught up at once. For the others, `/check <location name>` sends the check by hand.

### Other languages

Title reading has only been validated on the game in **French**. By default the client recognises likely wordings in other languages (English, German, Spanish, Italian, Portuguese, Dutch, Polish, Czech, Turkish, Swedish, Russian, Japanese, Chinese, Korean), but these are **guesses**. "In progress" / "incomplete" states are never taken for a completion.

To check: save in game (accept or complete an order), then type `/ds_titles` (about 1 minute). The client lists the latest titles read with "COMPLETED" or "not completed". If a completed order is marked "not completed", add a fragment of the status word (no accents, lowercase) to `memory_map.json` (a copy of `memory_map.default.json` in Archipelago's user folder):

```
"saves": { "completed_words": ["accompli"] }
```

If `/ds_titles` finds no title, open an issue with a screenshot of the title shown in the game's load menu.

## Tracking with PopTracker (optional)

A [PopTracker](https://github.com/black-sliver/PopTracker/releases) pack is provided (`death_stranding_poptracker_vX.Y.Z.zip` from the release, or the `death_stranding_poptracker/pack` folder of the repository): the 70 orders by episode, episode accesses, received items, the slot's goal and counters.

1. Put the zip **without extracting it** in PopTracker's `packs` folder, then *Open Pack* → "Death Stranding (Archipelago)".
2. Click the grey "AP", enter the server, **your slot name** and the password: tracking is automatic (the game is not read).

Right-click a box to tick the order by hand. **SYNC** puts the boxes back to the server's state, **ALL** shows everything as reachable (useful without `episode_gating`). The Victory box is not autotracked.

## Client commands

Common commands:

| Command | Role |
|---|---|
| `/connect <address:port>` | Connect to the server |
| `/ds_status` | Quantities read from memory (tests access to the game) |
| `/locations` | Lists the world's locations (orders) |
| `/check <name>` | Sends a check by hand |
| `/ds_held` | Checks held back by `episode_gating` |
| `/ds_likes`, `/ds_orders`, `/ds_standard`, `/ds_bot` | Milestone progress; `/ds_likes_rebase`, `/ds_orders_rebase`, `/ds_standard_rebase`, `/ds_bot_rebase` reset the baseline |
| `/ds_items` | Items received / applied in game |
| `/ds_stock [facility]` | Material stocks of a facility |
| `/ds_stock_mode random\|target`, `/ds_stock_target <facility>`, `/ds_stock_pool Name1; Name2` | Where received materials go (random by default) |
| `/ds_titles` | Language diagnostic: checkpoint titles read from memory |
| `/ds_debug on\|off` | Enables, for the current session, the test and diagnostic commands below (disabled at every client start) |

<details>
<summary>Test and diagnostic commands (after <code>/ds_debug on</code>)</summary>

All of these are **disabled by default**: they answer "Debug command disabled" until `/ds_debug on` is typed. The ones that write to the game are for testing only.

| Command | Role |
|---|---|
| `/ds_give <resource> <n>`, `/ds_likes_give <npc\|players> <n>`, `/ds_stock_give <material> <n>` | Writes a quantity into the game |
| `/ds_effect [name]` | Applies a trap or an item effect (no name: list) |
| `/ds_hp`, `/ds_kill` | Sam's health; sets it to 0 |
| `/ds_items_reset <n>` | Resets the applied-items index |
| `/ds_counters snap\|diff\|save [name]\|watch [on\|off]\|scan\|partial` | Read-only: snapshots the game's named counters, shows changes, writes `DeathStranding_counters[_name].json`, or (`watch`) prints every change continuously; `scan` restarts the table search, `partial` describes a rejected candidate table |
| `/ds_memdiff snap [inventory\|player\|all\|@0xOFFSET] [hex size]` then `/ds_memdiff diff` (`ptrs` lists nearby zones) | Read-only: snapshot of a game memory zone then list of changed words |
| `/ds_memdump [inventory\|player\|@0xOFFSET] <hex offset> <hex length>` | Read-only: raw bytes of a zone |

</details>

## Troubleshooting

| Symptom | What to do |
|---|---|
| "Location … does not exist in the hosted game" | Regenerate the game with the latest APWorld version |
| `/ds_status` shows nothing | The game must be running with the save loaded. Offsets may change after a game update (`memory_map.default.json`) |
| A completed main order is not detected | Wait for the "memory reading active" line at startup; the check goes out within seconds of the game's save. Otherwise: `/check <exact location name>` (the client suggests the likely command when it reports a main or special order end that "could not be identified") |
| "no save title in memory for now" | Normal until the game has written a checkpoint; the client retries by itself |
| Counters (standard, bot) stay silent | The client looks for their table in memory as soon as you are in game (up to a few minutes). Wait for loading to finish, then `/ds_debug on` and `/ds_counters scan`. If "table not found" persists, attach the output of `/ds_counters partial` to an issue |
| "Counter 'total' missing from the table…" / `/ds_bot` unavailable | Normal on some saves (see "Bot orders"); only bot milestones are affected |
| An effect or trap is not applied | It waits until Sam is readable (not during loading or menus). Test: `/ds_debug on` then `/ds_effect <name>` |

## Known limitations

- **No in-game locking.** Episode accesses do not stop you from playing; `episode_gating` only holds back the sending of checks (they survive a client restart, `/check` sends them regardless of the hold).
- **Equipment is compensated, not unlocked.** Writing memory cannot create or unlock equipment (each piece is tied to live game objects): it gives a one-shot effect or materials ([table](docs/setup_en.md)). Effects never permanently change the game's balance. This compensation is still to be confirmed in game.
- **Optional orders.** 19 of the 70 orders are optional (6, 10-13, 15, 17, 25, 26, 29, 31, 35, 37, 40, 42, 45, 56, 57, 66: construction tutorials, pizzas…). They are checks, but generation never places a progression item on them.
- **Victory.** Validated in game for no. 70 (episode 14 goal, 30 s to 1 min after the save that follows the credits) and no. 68 (episode 12 goal). With `episode_gating`, it waits for the accesses to every episode up to the goal. If it does not go out: `/check <location name>`.
- **Unidentified order.** If the game wrote no checkpoint before the next order and it has no known end key (no. 1, and the 🟡 orders not replayed), the client reports it with the likely order and the `/check` to type.
- **Client closed during an order.** It is caught up at launch if its end key is in the loaded game or if the titles prove it; otherwise `/check`. As a safeguard nothing is inferred if the title's episode is more than one ahead of your most advanced known order (another save, client started mid-game).
- **Other languages**: unverified guesses (see above).
- **Memory offsets.** They come from a community cheat table (only the addresses are used, not the file) and from personal measurements. They may break with every game update.

## License

MIT. Death Stranding is a trademark of Kojima Productions. This project is neither endorsed by nor affiliated with them.
