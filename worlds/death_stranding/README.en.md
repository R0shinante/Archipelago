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
5. [Client commands](#client-commands)
6. [Troubleshooting](#troubleshooting)
7. [Known limitations](#known-limitations)

## What it does

The **51 main orders** are the checks. Episodes are locked behind "Episode N Access" items. The other multiworld items (crystals, materials,
equipment, traps) are applied in game by the client, which accesses the game's memory.

| Feature | Status |
|---|---|
| Checks: main orders (51), detected automatically | ✅ |
| "Episode N Access" items (episode unlocks) | ✅ |
| Chiral Crystals applied in game | ✅ |
| DeathLink (sending and receiving the player's death) | ✅ validated in game |
| Likes milestones as checks (`likes_checks` / `likes_step`, up to 50) | ✅ validated in game |
| Order progress milestones as checks (`order_checks` / `order_step`, up to 100, no save needed) | ✅ validated in game: counts order steps, all order types combined |
| Standard orders delivered milestones as checks (`standard_checks` / `standard_step`, up to 100, no save needed) | ✅ validated in game: the game's exact counter (key 17 of the statistics table) |
| One-shot effects: Blood Bag, Energy Drink, Repair Spray, Boot Upgrade, Power Skeleton, Speed Skeleton, Cryptobiote Pack, D-Cryptobiote Pack, Sandalweed Bundle | ✅ validated in game |
| "Likes Pack" item (+500 likes) | 🧪 to be validated in game |
| Materials (resins, metals, ceramics, chemicals, special alloys) credited to a facility's stock | 🧪 to be validated in game |
| Traps: Injury, Fatigue, Boot Wear, Rust, Pickpocket | 🧪 to be validated in game |
| Bot orders delivered milestones as checks (`bot_checks` / `bot_step`, up to 100, no save needed) | ✅ validated in game: derived from internal game counters; the check arrives about 90 s after the delivery |
| Detection of completed main orders by reading the game's memory (no decryption tool) | ✅ validated on a few orders, French game; save decryption remains available as a fallback |
| Named checks per standard / optional order | ❌ |

Checks are identified by `7,770,000 + order number`. The client detects a completed main order from the **title of the checkpoint saves**
("Order completed: No. N …"). It reads it directly from the game's memory (French game); if you also configure the decryption tool below, it reads it from the saves as well, as a fallback (`/ds_resigner off` disables decryption). At startup the memory search scans about 10 GB in a minute, then watches a small area and redoes a full search every 4 minutes, or as soon as a main-order delivery is counted.

## Installation

### What you need

| Item | Details |
|---|---|
| System | **Windows**, with Death Stranding Director's Cut (Steam). The game is expected in French by default (see [Other languages](#other-languages)) |
| Archipelago | **0.6.x**, preferably **from source** (<https://github.com/ArchipelagoMW/Archipelago>) |
| Python | **3.12 or 3.13** when running from source (3.10 and 3.11 will not work) |
| pymem | Python library that lets the client access the game's memory |
| Decryption tool | [DeathStrandingSaveDataResigner](https://github.com/mi5hmash/DeathStrandingSaveDataResigner), command-line version (`death-stranding-savedata-resigner-cli.exe`, *Releases* tab). Third-party project, not included here. The client only works on a **temporary copy** of your checkpoints: your saves are never modified. |

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

### Step 3 — Prepare the decryption tool

1. Download and unzip the tool, for example into `C:\Games`.
2. Note the full path to the executable: you will give it to the client in the "Starting a game" section.

## Configuration (YAML)

1. In the Archipelago Launcher, click **Generate Template Options**.
2. Open `Death Stranding.yaml`, check `game: Death Stranding` and fill in your `name:`.
3. Set the options below, then put the file in the `Players` folder.

| Option | Values | Default | Purpose |
|---|---|---|---|
| `goal` | `finish_episode_14`, `finish_episode_12` | `finish_episode_14` | Victory condition |
| `trap_percentage` | 0 to 100 | 15 | Share of filler items turned into traps |
| `starting_episodes` | 0 to 5 | 0 | Episodes unlocked at the start, in addition to episode 1 |
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

**Standard orders.** The "Standard Orders N" check unlocks when you have delivered N × `standard_step` standard orders **since your first connection**. This is the game's exact counter, read live with no save needed: main orders, bot orders and lost-cargo deliveries do not count. `/ds_standard` shows the progress and `/ds_standard_rebase` resets the baseline.

**Bot orders.** The "Bot Orders N" check unlocks after N × `bot_step` bot deliveries **since your first connection**, with no save needed. The counter is derived from two internal game counters (total and non-bot) that are not written at the same moment: the client waits about 90 s without change before confirming, to avoid false positives during a delivery. Lost-cargo deliveries and equipment requests have not been tested. `/ds_bot` shows the progress and `/ds_bot_rebase` resets the baseline. Main orders are not affected: they have their named checks.

**DeathLink.** The client reads Sam's health: at 0 it notifies the other players; when a DeathLink is received it sets Sam's health to 0
(as soon as it is readable, so not during a loading screen or a menu). A received death is not sent back (20 s grace) and a sent death blocks further sends for 30 s.

Once the YAML is ready: Launcher → **Generate**, the `AP_xxxxxxxx.zip` file appears in `output`; Launcher → **Host**, pick that zip and note the
address (`localhost:38281` by default).

> **Redo this with every new APWorld version:** a game generated with an older version may contain locations the server does not know.
> The client reports it with a "Location … does not exist in the hosted game" warning (the client messages are in French).

## Starting a game

1. Launch Death Stranding **offline** and load your dedicated save.
2. In the Archipelago Launcher, open **Death Stranding Client** and connect: `/connect localhost:38281`.
3. **Check memory access:** `/ds_status` should show your Chiral Crystal amounts. Write test: `/ds_give Chiral Crystals 10`.
4. **Set up save detection** (once):
   ```
   /ds_resigner C:\Games\death-stranding-savedata-resigner-cli.exe
   ```
   If the saves folder is not found automatically:
   ```
   /ds_saves_dir C:\Users\<you>\AppData\Local\KojimaProductions\DeathStrandingDC\<Steam ID>
   ```
   This is the folder containing the `quicksave…` and `checkpoint…` subfolders, each with a `checkpoint.dat`.
5. **Check the whole chain:** `/ds_selftest` decrypts the latest checkpoint and shows its title, for example `Commande terminée : nº 61 « … »`.
6. **Play.** Complete a main order: the game writes a checkpoint, the client reads the title, sends the check, and the server hands out items.
   Received items are shown in the client console. Only orders completed **after** the client starts count; `/ds_catchup` also processes
   checkpoints that already exist (use with care).

### Other languages

The save title depends on the game language. If your game is not in French, adjust `saves.completed_words` in `memory_map.json`
(words meaning "completed"). To change the memory offsets, copy `memory_map.default.json` to `memory_map.json` in Archipelago's user folder.

## Client commands

<details>
<summary>Show the list</summary>

| Command | Purpose |
|---|---|
| `/locations` | Lists the world's locations (orders) |
| `/check <name>` | Sends a check manually |
| `/ds_status` | Amounts read from memory |
| `/ds_give <resource> <amount>` | Memory write test (backpack) |
| `/ds_effect [name]` | Tests a trap or item effect (no name: list); `/ds_trap` is an alias |
| `/ds_likes` | Likes read from memory (NPC / players / total) |
| `/ds_likes_give <npc\|players> <n>` | Write test for a likes counter |
| `/ds_likes_rebase` | Resets the likes milestone baseline |
| `/ds_orders` | Order-step counter and milestone progress |
| `/ds_orders_rebase` | Resets the order-progress baseline |
| `/ds_standard` | Standard orders delivered (game counter) and milestone progress |
| `/ds_standard_rebase` | Resets the standard-orders baseline |
| `/ds_bot` | Bot orders delivered (live counter) and milestone progress |
| `/ds_bot_rebase` | Resets the bot-orders baseline |
| `/ds_hp` | Player health read from memory (test) |
| `/ds_kill` | Test: sets Sam's health to 0 |
| `/ds_items` | Items received / applied in game (diagnostics) |
| `/ds_items_reset <n>` | Resets the applied-items index |
| `/ds_stock [facility]` | Material stocks of a facility |
| `/ds_stock_mode random\|target` | Material distribution: random facility (default) or chosen one |
| `/ds_stock_pool Name1; Name2` | Limits the random draw to some facilities (`all` = all of them) |
| `/ds_stock_target <facility>` | Facility credited in `target` mode |
| `/ds_stock_give <material> <amount>` | Write test for a stock |
| `/ds_resigner <exe>` | Path of the decryption tool (optional). `/ds_resigner off` / `on` disables / re-enables decryption |
| `/ds_saves_dir <folder>` | Saves folder |
| `/ds_saves` | Watcher status (checkpoints seen, orders detected) |
| `/ds_selftest` | Tests decryption and title reading |
| `/ds_catchup` | Also processes checkpoints that already exist (use with care) |

</details>

## Troubleshooting

| Symptom | What to do |
|---|---|
| "Location … does not exist in the hosted game" (shown in French) | Regenerate the game with the latest APWorld version |
| `/ds_status` shows nothing | The game must be running with your save loaded. Offsets may change after a game update (see `memory_map.default.json`) |
| "File not found" with `/ds_resigner` | Check the full path to the `.exe` (backslashes are accepted as typed) |
| Odd decryption return code (e.g. `3762504530`) | The tool crashes on exit: harmless as long as `/ds_selftest` shows a title |
| Nothing is detected | Run `/ds_selftest`, then `/ds_saves`. Only changes made after the client starts count |
| An effect or trap does not apply | It waits until Sam is readable (not during a loading screen or menu). Test with `/ds_effect <name>` |

## Known limitations

- Only the 51 main orders on the list are checks. The list comes from community guides and may contain mistakes (order 17 missing, order 66 with an approximate name).
- For received items: only Chiral Crystals, materials, traps and the one-shot effects listed above act in game. Other equipment
  (Cargo Skeleton, vehicles, anchors, ladders, weapons, grenades…) is received but **has no effect for now**. Effects never permanently change the game's balance.
- Memory offsets come from a community cheat table (only the addresses are used, not the file) and from personal measurements.
  They may break with any game update.
- The research on the order counters is documented in [`docs/RECHERCHE_compteurs_commandes.md`](docs/RECHERCHE_compteurs_commandes.md) (in French).

## Tests

```
SKIP_REQUIREMENTS_UPDATE=1 python tests/test_memory.py
SKIP_REQUIREMENTS_UPDATE=1 python tests/test_savewatch.py
```

(In the standalone repository; these tests are not included in the fork branch.)

## License

MIT. Death Stranding is a trademark of Kojima Productions. This project is neither endorsed by nor affiliated with them.
