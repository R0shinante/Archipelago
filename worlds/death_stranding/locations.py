from BaseClasses import Location
from .data import BASE_ID, MAIN_ORDERS, location_name


class DeathStrandingLocation(Location):
    game = "Death Stranding"


def _build_location_table() -> dict[str, tuple[int, int]]:
    """nom -> (id, episode). id = BASE_ID + numero de commande (stable)."""
    return {location_name(no, name): (BASE_ID + no, ep) for no, name, ep in sorted(MAIN_ORDERS)}


location_table = _build_location_table()
location_name_to_id = {name: data[0] for name, data in location_table.items()}
