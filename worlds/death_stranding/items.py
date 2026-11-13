from BaseClasses import Item, ItemClassification
from .data import BASE_ID, EPISODES, USEFUL_ITEMS, FILLER_ITEMS, TRAP_ITEMS


class DeathStrandingItem(Item):
    game = "Death Stranding"


def _build_item_table() -> dict[str, tuple[int, ItemClassification]]:
    table: dict[str, tuple[int, ItemClassification]] = {}
    code = BASE_ID
    # Deblocage des episodes 1..14 (le prologue, episode 0, est libre)
    for ep in sorted(EPISODES):
        if ep == 0:
            continue
        table[f"Episode {ep} Access"] = (code, ItemClassification.progression)
        code += 1
    for name in USEFUL_ITEMS:
        table[name] = (code, ItemClassification.useful)
        code += 1
    for name in FILLER_ITEMS:
        table[name] = (code, ItemClassification.filler)
        code += 1
    for name in TRAP_ITEMS:
        table[name] = (code, ItemClassification.trap)
        code += 1
    return table


item_table = _build_item_table()
item_name_to_id = {name: data[0] for name, data in item_table.items()}
