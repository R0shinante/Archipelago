from BaseClasses import Location
from .data import BASE_ID, MAIN_ORDERS, location_name


class DeathStrandingLocation(Location):
    game = "Death Stranding"


def _build_location_table() -> dict[str, tuple[int, int]]:
    """nom -> (id, episode). id = BASE_ID + numero de commande (stable)."""
    return {location_name(no, name): (BASE_ID + no, ep) for no, name, ep in sorted(MAIN_ORDERS)}


location_table = _build_location_table()

# Paliers de likes (optionnels) : id = LIKES_BASE_ID + n. Le palier n correspond a n * likes_step likes (option).
LIKES_BASE_ID = 7_771_000
MAX_LIKES_CHECKS = 50


def likes_location_name(n: int) -> str:
    return f"Likes Milestone {n}"


likes_location_table = {likes_location_name(n): LIKES_BASE_ID + n for n in range(1, MAX_LIKES_CHECKS + 1)}

# Paliers de progression des commandes (optionnels) : id = ORDER_PROGRESS_BASE_ID + n (palier n = n * order_step etapes de commande).
ORDER_PROGRESS_BASE_ID = 7_772_000
MAX_ORDER_CHECKS = 100


def order_progress_location_name(n: int) -> str:
    return f"Order Progress {n}"


order_progress_location_table = {order_progress_location_name(n): ORDER_PROGRESS_BASE_ID + n for n in range(1, MAX_ORDER_CHECKS + 1)}
# Paliers de commandes standard livrees (optionnels) : id = STANDARD_ORDER_BASE_ID + n (palier n = n * standard_step livraisons standard).
STANDARD_ORDER_BASE_ID = 7_773_000
MAX_STANDARD_CHECKS = 100


def standard_order_location_name(n: int) -> str:
    return f"Standard Orders {n}"


standard_order_location_table = {standard_order_location_name(n): STANDARD_ORDER_BASE_ID + n for n in range(1, MAX_STANDARD_CHECKS + 1)}
location_name_to_id = {**{name: data[0] for name, data in location_table.items()}, **likes_location_table, **order_progress_location_table,
                       **standard_order_location_table}
