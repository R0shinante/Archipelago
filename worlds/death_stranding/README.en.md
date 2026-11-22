# Death Stranding (Director's Cut, PC/Steam) — Archipelago APWorld

[🇫🇷 Français](README.md) · 🇬🇧 English

Experimental [Archipelago](https://archipelago.gg) world and client for **Death Stranding Director's Cut** (PC, Steam).
Unofficial project, not affiliated with Kojima Productions, 505 Games or the Archipelago team.

> ⚠️ **Alpha.** Use it **offline**, in **single player**, on a **dedicated test save**.
> The client reads and writes the game's memory: never use it online, and back up your saves before you start.

## Contents

1. [What it does](#what-it-does)
2. [Installation](#installation)
3. [Configuration (YAML)](#configuration-yaml)
4. [Starting a game](#starting-a-game)
5. [Tracking with PopTracker (optional)](#tracking-with-poptracker-optional)
6. [Client commands](#client-commands)
7. [Troubleshooting](#troubleshooting)
8. [Known limitations](#known-limitations)

## What it does

The **70 main orders** (no. 1 to 70) are the checks. "Episode N Access" items shape the generation logic (an episode is only "reachable" once its item is received), but **the game itself is not locked**:
nothing stops you from playing the story without having received them (see [Known limitations](#known-limitations)). The other multiworld items (crystals, materials,
equipment, traps) are applied in game by the client, which accesses the game's memory.

| Feature | Status |
|---|---|
| Checks: main orders (70), detected automatically | ✅ |
| "Episode N Access" items in the generation logic (episode regions) | ✅ received and displayed, but **no effect in game** |
| Real in-game episode locking (preventing play of an episode without its item) | ❌ not possible for now |
| Chiral Crystals applied in game | ✅ |
| DeathLink (sending and receiving the player's death) | ✅ validated in game |
| Likes milestones as checks (`likes_checks` / `likes_step`, up to 50) | ✅ validated in game |
| Order progress milestones as checks (`order_checks` / `order_step`, up to 100, no save needed) | ✅ validated in game: counts order steps, all order types combined |
| Standard orders delivered milestones as checks (`standard_checks` / `standard_step`, up to 100, no save needed) | ✅ validated in game: the game's exact counter (key 17 of the statistics table) |
| One-shot effects: Blood Bag, Energy Drink, Repair Spray, Boot Upgrade, Power Skeleton, Speed Skeleton, Cryptobiote Pack, D-Cryptobiote Pack, Sandalweed Bundle | ✅ validated in game |
| "Likes Pack" item (+500 likes) | ✅ validated in game |
| Materials (resins, metals, ceramics, chemicals, special alloys) credited to a facility's stock | ✅ validated in game |
| Traps: Injury, Fatigue, Boot Wear, Rust, Pickpocket | ✅ validated in game |
| Bot orders delivered milestones as checks (`bot_checks` / `bot_step`, up to 100, no save needed) | ✅ validated in game: derived from internal game counters; the check arrives about 90 s after the delivery |
| Detection of completed main orders by reading the game's memory (no tool, no decryption) | ✅ validated in game (French); save decryption remains available as an option |
| Catching up orders already completed when the client starts, or that never show in the save title | ✅ validated in game: end-of-order keys validated on no. 2 to 10, 14, 15, 26, 38 to 44, 46 and 61 to 70; the others: see “Coverage of the immediate detection” (keys read from the game files, or inference from save titles) |
| Named checks per standard / optional order | ❌ |

Checks are identified by `7,770,000 + order number`. The client detects a completed main order by reading, **directly from the game's memory**, the checkpoint title
("Order completed: No. N …"): no extra tool is needed. For the orders whose end the game marks with a key of its own (see “Coverage of the immediate detection” below), the client recognises them **immediately**, without waiting for the next game save ("Order completion detected (marker)"). When the client starts, orders whose key is already present (see the table below) are caught up at once, including those the save title never shows (no. 6, 8…). The first search takes about a minute; the client then remembers the memory area it used and searches it first on later
launches (a few seconds). If the game moves its data (another save, a restart), the full search resumes by itself. Save decryption remains available as an option, as a fallback
([see below](#save-decryption-optional)).

### Coverage of the immediate detection

| Level | Orders | How the client sees them |
|---|---|---|
| ✅ Validated in game | 2 to 12, 14 to 16, 18 to 30, 32 to 36, 38 to 44, 46 to 55, 58 to 65, 67 to 70 | End-of-order key created by the game: detected on delivery, and caught up when the client starts |
| 🟡 Keys read from the game files, not replayed yet | 13, 17, 31, 37, 45, 56, 57 and 66 | Same mechanism; if an order is reported too early, too late or never, please report it with a `/ds_counters watch on` capture |
| ⚪ Save titles only | 1 | The checkpoint title is read (a few seconds after the game saves) and orders are inferred; `/check <location>` as a last resort |

An order's end key is the identifier of the sentence of its **final objective** (for example "Deliver all four containers of aid." for no. 14). The keys of the other orders were read from the mission files of the author's own copy of the game (nothing from the game ships with the APWorld) and cross-checked against the keys measured in game. For orders with several objectives the final-objective key is inferred from the text (collect, then deliver); those whose final objective remains ambiguous are in the last row. The client requires the key to be **0**: an intermediate step stays at 1 until the final validation, and no. 39 does not even create a key at the end (its last step is what falls back from 1 to 0).

## Installation

### What you need

| Item | Details |
|---|---|
| System | **Windows**, with Death Stranding Director's Cut (Steam). The game is expected in French (see [Other languages](#other-languages)) |
| Archipelago | **0.6.x**, preferably **from source** (<https://github.com/ArchipelagoMW/Archipelago>) |
| Python | **3.12 or 3.13** when running from source (on Windows: 3.12.10 or newer; 3.10, 3.11 and 3.14 will not work) |
| pymem | Python library that lets the client access the game's memory |

### Step 1 — Install the APWorld

Pick **one** of the two methods (otherwise the world is loaded twice):

- **From a release (easiest):** download `death_stranding.apworld` and put it in Archipelago's `custom_worlds` folder.
- **From this repository:** copy the `death_stranding` folder into Archipelago's `worlds` folder.

### Step 2 — Install pymem

In a command prompt (replace `3.12` with your Python version):

```
py -3.12 -m pip install pymem
```

With the official Archipelago installer, install `pymem` into the Python that runs the client; running from source is recommended for this world.

## Configuration (YAML)

1. In the Archipelago Launcher, click **Generate Template Options**.
2. Open `Death Stranding.yaml`, check `game: Death Stranding` and fill in your `name:`.
3. Set the options below, then put the file in the `Players` folder.

| Option | Values | Default | Purpose |
|---|---|---|---|
| `goal` | `finish_episode_14`, `finish_episode_12` | `finish_episode_14` | Victory condition |
| `trap_percentage` | 0 to 100 | 15 | Share of filler items turned into traps |
| `episode_gating` | `false`, `true` | `false` | Holds main-order checks until the items "Episode 1 Access" to "Episode N Access" are received (see below) |
| `starting_episodes` | 0 to 5 | 0 | Number of "Episode N Access" items given at the start (random episodes, episode 1 included; generation logic only) |
| `death_link` | true / false | false | DeathLink (see below) |
| `likes_checks` | 0 to 50 | 0 | Number of likes checks (0 = disabled) |
| `likes_step` | 100 to 10000 | 1000 | Likes to earn per milestone |
| `order_checks` | 0 to 100 | 0 | Number of order-progress checks (0 = disabled) |
| `order_step` | 1 to 50 | 3 | Order steps per milestone |
| `standard_checks` | 0 to 100 | 0 | Number of standard-orders-delivered checks (0 = disabled) |
| `standard_step` | 1 to 50 | 3 | Standard orders to deliver per milestone |
| `bot_checks` | 0 to 100 | 0 | Number of bot-orders-delivered checks (0 = disabled) |
| `bot_step` | 1 to 50 | 3 | Bot orders to deliver per milestone |

**Likes.** The "Likes Milestone N" check unlocks when you earn N × `likes_step` likes **since your first connection** (the baseline is fixed at that moment).
Likes received through "Likes Pack" items do not count. `/ds_likes` shows your progress.

**Order progress.** The "Order Progress N" check unlocks when the order-step counter rises by N × `order_step` **since your first connection**.
The counter goes up on every completed objective step: standard order delivery, bot order, and acceptance and intermediate objectives of a main order.
It measures steps, all types combined, and does not count lost-cargo deliveries. It works live, with no save needed, while the client is connected.
`/ds_orders` shows the progress and `/ds_orders_rebase` resets the baseline.

**Standard orders.** The "Standard Orders N" check unlocks when you have delivered N × `standard_step` standard orders **since your first connection**. This is the game's exact counter, read live with no save needed: main orders, bot orders and lost-cargo deliveries do not count. Standard orders only become available in game after the delivery of no. 9 (observed): no milestone before that. `/ds_standard` shows the progress and `/ds_standard_rebase` resets the baseline.

**Bot orders.** The "Bot Orders N" check unlocks after N × `bot_step` bot deliveries **since your first connection**, with no save needed. The counter is derived from two internal game counters (total and non-bot) that are not written at the same moment: the client waits about 90 s without change before confirming, to avoid false positives during a delivery, and holds the confirmation while a standard order (results screen) is being finalised. The end of a main or special order (the game then raises only the total counter) is recognised by the key the game creates at the same moment, or by a likes jump: the confirmation is held for 5 minutes, then the increase is dropped from the bot baseline (log: "Fin de commande principale ou speciale reconnue dans les compteurs"). **Known limitations:** the game keeps no separate counter for returned lost cargo, which raises the bot counter like a bot delivery and therefore counts towards these milestones (seen on two deliveries); a real bot collected within 10 s of an unrelated key creation may, more rarely, be dropped by mistake. Equipment requests have not been tested (they need the game to be online). `/ds_bot` shows the progress and `/ds_bot_rebase` resets the baseline. Main orders are not affected: they have their named checks. **Availability:** bot orders only exist in game from about no. 24, and the "total" counter this calculation relies on is not in the table of every save (observed: absent on a save at no. 36, created on delivery of no. 38 on the tested game, present on another save at no. 61). While it is missing, `/ds_bot` says "unavailable for now", no bot milestone goes out and the rest of the client works normally; once it appears, the baseline is set after about 90 s of stable values. If `/ds_bot` stays unavailable on your game after several bot deliveries, set `bot_checks` to 0: those checks will not unlock.

**DeathLink.** The client reads Sam's health: at 0 it notifies the other players; when a DeathLink is received it sets Sam's health to 0
(as soon as it is readable, so not during a loading screen or a menu). A received death is not sent back (20 s grace) and a sent death blocks further sends for 30 s.

Once the YAML is ready: Launcher → **Generate**, the `AP_xxxxxxxx.zip` file appears in `output`; Launcher → **Host**, pick that zip and note the
address (`localhost:38281` by default).

> **Redo this with every new APWorld version:** a game generated with an older version may contain locations the server does not know.
> The client reports it with a "Location … does not exist in the hosted game" warning (the client messages are in French).

## Starting a game

1. Launch Death Stranding **offline** and load your dedicated save.
2. In the Archipelago Launcher, open **Death Stranding Client** and connect: `/connect localhost:38281`.
3. **Check memory access:** `/ds_status` should show your Chiral Crystal amounts. Write test (after `/ds_debug on`): `/ds_give Chiral Crystals 10`.
4. **Wait for the first search to finish:** the log shows "Commandes principales : lecture en memoire active …" (about a minute the first time, a few seconds afterwards).
5. **Play.** Complete a main order: the client reads its title from memory, sends the check, and the server hands out items.
   Received items are shown in the client console. Only orders completed **after** the client starts count.

### Save decryption (optional)

Not needed normally. It serves as a fallback, or if your game is not in French. The client then uses the third-party tool
[DeathStrandingSaveDataResigner](https://github.com/mi5hmash/DeathStrandingSaveDataResigner) (command-line version, *Releases* tab, not included here) on a **temporary copy**
of your checkpoints: your saves are never modified.
```
/ds_resigner C:\Games\death-stranding-savedata-resigner-cli.exe
/ds_selftest
```
`/ds_selftest` decrypts the latest checkpoint and shows its title. If the saves folder is not found automatically:
`/ds_saves_dir C:\Users\<you>\AppData\Local\KojimaProductions\DeathStrandingDC\<Steam ID>` (the folder containing the `checkpoint…` subfolders).
`/ds_resigner off` disables decryption, `/ds_resigner on` re-enables it, `/ds_catchup` also processes checkpoints that already exist (use with care).

### Other languages

Memory reading has only been validated on the **French** game. By default, with **no setup**, the client recognises likely wordings in other languages
(English "Order Completed : No. 12 ...", German, Spanish, Italian, Portuguese, Dutch, Polish, Czech, Turkish, Swedish, Russian, Japanese, Chinese, Korean), but these are **guesses**:
the exact format is not confirmed in game. "In progress" / "incomplete" states are never taken for a completed order.

To check with your game: make a save (accept or finish an order), then type **`/ds_titles`** (~1 minute). The client prints the latest checkpoint titles read from memory,
each marked "TERMINEE" (completed) or "pas terminee" (not completed). If a completed order is marked "pas terminee", add a fragment of the state word to `saves.completed_words` in `memory_map.json`
(copy `memory_map.default.json` to `memory_map.json` in Archipelago's user folder; the same file is used to change the memory offsets). These words are **added** to the defaults:
```
"saves": { "completed_words": ["accompli"] }
```
A word fragment is enough (no accents, lowercase). If `/ds_titles` finds no title, send a screenshot of the title shown in the game's load menu (GitHub issue) and your language's format will be added.
If in doubt, use save decryption.

## Tracking with PopTracker (optional)

A [PopTracker](https://github.com/black-sliver/PopTracker/releases) pack is provided (`death_stranding_poptracker_vX.Y.Z.zip` in the release, or the `death_stranding_poptracker/pack` folder of the repository). It shows the 70 orders by episode (green: reachable according to the generation logic, red: an "Episode N Access" item is missing, dark: check sent), episode access, equipment, materials and traps received, the slot's goal, and "checked / total" counters (main orders, likes, order-progress, standard-order and bot-order milestones).

1. Put the zip **unextracted** in PopTracker's `packs` folder, then *Open Pack* → "Death Stranding (Archipelago)".
2. Click the grey "AP", enter the server, **your slot name** and the password: tracking is automatic (the game is never read).

Right click on a square marks the order as done by hand; the **SYNC** button (*Progress* section) puts every square back to the server's state. The **ALL** button shows everything as reachable (useful without `episode_gating`, since the game is never locked). With `episode_gating`, an order that is done but held back (`/ds_held`) stays red until its episode item arrives. The Victory square is not autotracked. Validated in game on 21/11 (connection, items, counters, checked squares, SYNC, ALL). The pack is regenerated by `death_stranding_poptracker/tools/make_poptracker.py`.

## Client commands

<details>
<summary>Show the list</summary>

| Command | Purpose |
|---|---|
| `/locations` | Lists the world's locations (orders) |
| `/check <name>` | Sends a check manually |
| `/ds_status` | Amounts read from memory |
| `/ds_debug on\|off` | Turns on or off, for the current session, the test commands that **write to the game** (`/ds_give`, `/ds_effect`, `/ds_trap`, `/ds_likes_give`, `/ds_stock_give`, `/ds_kill`). Off at every client start |
| `/ds_give <resource> <amount>` | Test (after `/ds_debug on`): memory write (backpack) |
| `/ds_effect [name]` | Test (after `/ds_debug on`) of a trap or item effect (no name: list); `/ds_trap` is an alias |
| `/ds_likes` | Likes read from memory (NPC / players / total) |
| `/ds_likes_give <npc\|players> <n>` | Test (after `/ds_debug on`): write a likes counter |
| `/ds_likes_rebase` | Resets the likes milestone baseline |
| `/ds_orders` | Order-step counter and milestone progress |
| `/ds_orders_rebase` | Resets the order-progress baseline |
| `/ds_standard` | Standard orders delivered (game counter) and milestone progress |
| `/ds_standard_rebase` | Resets the standard-orders baseline |
| `/ds_bot` | Bot orders delivered (live counter) and milestone progress |
| `/ds_bot_rebase` | Resets the bot-orders baseline |
| `/ds_counters snap\|diff\|save [name]\|watch [on\|off]\|scan\|partial` | Diagnostics (read-only): snapshots every named game counter, shows those that changed since the snapshot, writes them to `DeathStranding_counters[_name].json`, or (`watch`) prints every change to the console as it happens (turn it off after testing); `scan` restarts the table search immediately; `partial` describes the rejected candidate table (`DeathStranding_counters_partial.json`) |
| `/ds_held` | Lists the checks held by the `episode_gating` option, waiting for an "Episode N Access" item |
| `/ds_hp` | Player health read from memory (test) |
| `/ds_kill` | Test (after `/ds_debug on`): sets Sam's health to 0 |
| `/ds_items` | Items received / applied in game (diagnostics) |
| `/ds_items_reset <n>` | Resets the applied-items index |
| `/ds_stock [facility]` | Material stocks of a facility |
| `/ds_stock_mode random\|target` | Material distribution: random facility (default) or chosen one |
| `/ds_stock_pool Name1; Name2` | Limits the random draw to some facilities (`all` = all of them) |
| `/ds_stock_target <facility>` | Facility credited in `target` mode |
| `/ds_stock_give <material> <amount>` | Test (after `/ds_debug on`): write a stock |
| `/ds_resigner <exe>` | (optional) Path of the decryption tool. `/ds_resigner off` / `on` disables / re-enables decryption |
| `/ds_saves_dir <folder>` | (optional) Saves folder |
| `/ds_saves` | (optional) Decryption status (checkpoints seen, orders detected) |
| `/ds_selftest` | (optional) Tests decryption and title reading |
| `/ds_titles` | Language diagnostic: lists the checkpoint titles read from memory and whether they are recognised as completed |
| `/ds_catchup` | (optional) Also processes checkpoints that already exist (use with care) |

</details>

## Troubleshooting

| Symptom | What to do |
|---|---|
| "Location … does not exist in the hosted game" (shown in French) | Regenerate the game with the latest APWorld version |
| `/ds_status` shows nothing | The game must be running with your save loaded. Offsets may change after a game update (see `memory_map.default.json`) |
| A completed main order is not detected | Wait for the "lecture en memoire active" line at startup; the check goes out within seconds of the game writing its checkpoint. Only orders completed after the client starts count. As a last resort, set up save decryption (see above) |
| "aucun titre de sauvegarde en memoire pour l'instant" | Normal until the game has written a checkpoint; the client retries (every 1 to 10 minutes when idle, continuously for 6 minutes after each delivery) |
| Order counters (standard, bot) stay silent | The client searches memory for the table as soon as you are in game (up to a few minutes, retries spaced out) after a game restart or a change of save. Wait for the save to finish loading, then `/ds_counters scan` restarts the search immediately; `/ds_bot` shows the state. If "table introuvable" persists, `/ds_counters partial` describes what was seen: send the console with an issue |
| "Compteur « total » absent de la table…" / `/ds_bot`: unavailable | Normal on some saves: the game only creates this counter later (observed in game: on delivery of no. 38 on the tested game). Only the bot milestones are affected (see "Bot orders") |
| An effect or trap does not apply | It waits until Sam is readable (not during a loading screen or menu). Test with `/ds_debug on` then `/ds_effect <name>` |

## Known limitations

- "Episode N Access" items **lock nothing in game**: they only exist in the generation logic. You can play the story in order without having received them, and checks go out
  as soon as the order is completed. With the `episode_gating` option the client **holds back sending** main-order checks: an order of episode N is only sent once "Episode 1 Access" to "Episode N Access" are received (same rule as generation). The order completes normally in game and its check goes out as soon as the item arrives; held checks survive a client restart (`/ds_held` lists them). Likes, order progress, standard order and bot order checks are never held, and `/check <location>` sends a check regardless of the hold. The game itself is not locked.
- The 70 main orders (no. 1 to 70) are the checks. List from the Fandom wiki and Neoseeker. 19 are optional (marked “Story: No” on Fandom, plus no. 66): no. 6, 10-13, 15, 17, 25, 26, 29, 31, 35, 37, 40, 42, 45, 56, 57, 66
  (construction tutorials, “Fresh Pizza Delivery: Peter Englert”…). They are checks, but generation never places a progression item on them. The tutorials no. 6, 10 and 15 and pizza no. 26 are validated in game (end-of-order key); order 1 is seen through the title or inference; the tutorials no. 25 and 29 and the pizzas no. 40, 45, 57 and 66 have not been verified in game yet: if one is not detected, use `/check <exact location name>`. When the client sees an order numbered below 100
  complete that is not on the list, it says so once in the log: please report it with its name and episode.
- Victory (last order of the goal episode: No. 70, or No. 68 with the episode 12 goal) is validated in game for No. 70 (episode 14 goal), 30 s to 1 min after the save that follows the credits, and for No. 68 (episode 12 goal), recognised by its marker keys as soon as the end-of-delivery cinematic starts. With `episode_gating`, victory waits for the "Episode 1 Access" to "Episode N Access" items. If victory does not go out, `/check <location name>` sends the check by hand.
- A main order may go unidentified if the game wrote no checkpoint before the next one and it has no known marker key (this is the case of the orders in the last row of the coverage table). The client then warns ("unidentified order end") with the likely order and the `/check` command to type.
- A main order completed while the client was not running is not caught up (memory only keeps the latest checkpoint), except with the optional decryption and `/ds_catchup`. Exceptions: orders whose end key is known (coverage table) and those proven by the inference from save titles. `/check <location name>` sends it by hand.
- The save title only keeps the latest order: an order completed and then followed by another before the save never shows up there. The client therefore **infers** its completion when the title shows an order from a later episode (any state, even "in progress"): every "Story: Yes" order of earlier episodes is considered completed, as are the earlier orders of strictly sequential chains (no. 2→3, 54→55, 63→64→65). Optional orders are never inferred. As a safeguard nothing is inferred if the title's episode is more than one episode beyond your most advanced known order (another save, client started mid-game): use `/check` then. The log says "Commande terminee deduite".
- For received items: only Chiral Crystals, materials, traps and the one-shot effects listed above act in game. Other equipment
  (Cargo Skeleton, vehicles, anchors, ladders, weapons, grenades…) is received but **has no effect for now**. Effects never permanently change the game's balance.
- Memory offsets come from a community cheat table (only the addresses are used, not the file) and from personal measurements.
  They may break with any game update.
- The research on the order counters is documented in [`death_stranding_research/RECHERCHE_compteurs_commandes.md`](https://github.com/R0shinante/Archipelago/blob/death-stranding/death_stranding_research/RECHERCHE_compteurs_commandes.md) (in French, on the repository branch, outside the APWorld).

## Tests

```
SKIP_REQUIREMENTS_UPDATE=1 python tests/test_memory.py
SKIP_REQUIREMENTS_UPDATE=1 python tests/test_savewatch.py
```

(In the standalone repository; these tests are not included in the fork branch.)

## License

MIT. Death Stranding is a trademark of Kojima Productions. This project is neither endorsed by nor affiliated with them.
