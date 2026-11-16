from typing import Any

from BaseClasses import Item, ItemClassification, Region, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.LauncherComponents import Component, Type, components, launch_subprocess

from .data import EPISODE_TITLES, EPISODES, EXTRA_FILLER_ITEMS, EXTRA_FILLER2_ITEMS, EXTRA_FILLER3_ITEMS, EXTRA_FILLER4_ITEMS, EXTRA_TRAP_ITEMS, FILLER_ITEMS, TRAP_ITEMS, USEFUL_ITEMS
from .items import DeathStrandingItem, item_name_to_id, item_table
from .locations import (DeathStrandingLocation, likes_location_name, likes_location_table, location_name_to_id, location_table,
                        order_progress_location_name, order_progress_location_table)
from .options import DeathStrandingOptions


def _launch_client(*args: str) -> None:
    from .client import launch
    launch_subprocess(launch, name="DeathStrandingClient", args=args)


components.append(Component("Death Stranding Client", func=_launch_client,
                            component_type=Type.CLIENT, game_name="Death Stranding"))


class DeathStrandingWeb(WebWorld):
    theme = "partyTime"
    tutorials = [Tutorial(
        "Guide de configuration",
        "Comment configurer Death Stranding Director's Cut (PC) avec Archipelago.",
        "Français",
        "setup_fr.md",
        "setup/fr",
        ["Roshinante"],
    ), Tutorial(
        "Setup guide",
        "How to set up Death Stranding Director's Cut (PC) with Archipelago.",
        "English",
        "setup_en.md",
        "setup/en",
        ["Roshinante"],
    )]


class DeathStrandingWorld(World):
    """
    Death Stranding : livre des colis à travers une Amérique dévastée et reconnecte-la.
    Chaque livraison principale est un check ; les épisodes sont verrouillés par des items.
    """
    game = "Death Stranding"
    web = DeathStrandingWeb()
    options_dataclass = DeathStrandingOptions
    options: DeathStrandingOptions

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id

    def create_item(self, name: str) -> Item:
        code, cls = item_table[name]
        return DeathStrandingItem(name, cls, code, self.player)

    def generate_early(self) -> None:
        n = self.options.starting_episodes.value
        candidates = [f"Episode {e} Access" for e in sorted(EPISODES) if e != 0]
        self.random.shuffle(candidates)
        self.starting_items = candidates[:n]
        self.goal_episode = 14 if self.options.goal == 0 else 12

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)
        previous = menu
        for ep in sorted(EPISODES):
            if ep > self.goal_episode:
                break
            region = Region(EPISODE_TITLES[ep], self.player, self.multiworld)
            for loc_name in EPISODES[ep]:
                code, _ = location_table[loc_name]
                region.locations.append(DeathStrandingLocation(self.player, loc_name, code, region))
            self.multiworld.regions.append(region)
            if ep == 0:
                previous.connect(region, "Debut -> Prologue")
            else:
                item_name = f"Episode {ep} Access"
                previous.connect(
                    region, f"Episode {ep - 1} -> Episode {ep}",
                    lambda state, n=item_name: state.has(n, self.player),
                )
            previous = region
        if self.options.likes_checks.value > 0:
            likes_region = Region("Likes", self.player, self.multiworld)
            for n in range(1, self.options.likes_checks.value + 1):
                name = likes_location_name(n)
                likes_region.locations.append(DeathStrandingLocation(self.player, name, likes_location_table[name], likes_region))
            self.multiworld.regions.append(likes_region)
            menu.connect(likes_region, "Menu -> Likes")
        if self.options.order_checks.value > 0:
            order_region = Region("Order Progress", self.player, self.multiworld)
            for n in range(1, self.options.order_checks.value + 1):
                name = order_progress_location_name(n)
                order_region.locations.append(DeathStrandingLocation(self.player, name, order_progress_location_table[name], order_region))
            self.multiworld.regions.append(order_region)
            menu.connect(order_region, "Menu -> Order Progress")
        # Événement de victoire
        victory = DeathStrandingLocation(self.player, "Victoire", None, previous)
        victory.place_locked_item(DeathStrandingItem("Victoire", ItemClassification.progression, None, self.player))
        previous.locations.append(victory)
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victoire", self.player)

    def create_items(self) -> None:
        pool: list[Item] = []
        for ep in sorted(EPISODES):
            if ep == 0 or ep > self.goal_episode:
                continue
            name = f"Episode {ep} Access"
            if name in self.starting_items:
                self.multiworld.push_precollected(self.create_item(name))
            else:
                pool.append(self.create_item(name))

        total_locations = len([l for l in self.multiworld.get_unfilled_locations(self.player)])
        remaining = total_locations - len(pool)

        for name, qty in USEFUL_ITEMS.items():
            for _ in range(qty):
                if remaining <= 0:
                    break
                pool.append(self.create_item(name))
                remaining -= 1

        filler_names = [n for d in (FILLER_ITEMS, EXTRA_FILLER_ITEMS, EXTRA_FILLER2_ITEMS, EXTRA_FILLER3_ITEMS, EXTRA_FILLER4_ITEMS) for n, q in d.items() for _ in range(q)]
        trap_names = [n for d in (TRAP_ITEMS, EXTRA_TRAP_ITEMS) for n, q in d.items() for _ in range(q)]
        trap_count = int(remaining * self.options.trap_percentage.value / 100)
        for _ in range(max(remaining, 0)):
            if trap_count > 0:
                pool.append(self.create_item(self.random.choice(trap_names)))
                trap_count -= 1
            else:
                pool.append(self.create_item(self.random.choice(filler_names)))

        self.multiworld.itempool += pool

    def get_filler_item_name(self) -> str:
        return self.random.choice(list(FILLER_ITEMS))

    def fill_slot_data(self) -> dict[str, Any]:
        return {
            "goal_episode": self.goal_episode,
            "death_link": bool(self.options.death_link.value),
            "likes_checks": self.options.likes_checks.value,
            "likes_step": self.options.likes_step.value,
            "order_checks": self.options.order_checks.value,
            "order_step": self.options.order_step.value,
            "location_to_episode": {str(code): ep for code, ep in
                                    (location_table[n] for n in location_table)},
        }
