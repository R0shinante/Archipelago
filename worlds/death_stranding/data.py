"""Donnees statiques du monde Death Stranding.

Les checks sont les commandes PRINCIPALES numerotees du jeu (le numero est celui affiche dans le titre
des sauvegardes : « Commande terminee : n° 59 ... »). Liste d'apres la page
https://samurai-gamers.com/death-stranding/delivery-order-list/ (50 commandes de son tableau principal).
Cette page se contredit par endroits (la n°17 n'apparait nulle part, les commandes optionnelles partagent la
meme numerotation) : a verifier en jouant. La n°66 (episode 10, Die-Hardman) est une commande
OPTIONNELLE (non necessaire a l'histoire) : « (URGENT) Fresh Pizza Delivery: Peter Englert » (nom confirme en jeu le 19/11).

Les identifiants de lieux sont stables : BASE_ID + numero de commande.
"""

BASE_ID = 7_770_000

# Episode 0 = prologue (toujours accessible).
EPISODE_TITLES: dict[int, str] = {
    0: "Prologue - Porter", 1: "Episode 1 - Bridget", 2: "Episode 2 - Amelie", 3: "Episode 3 - Fragile",
    4: "Episode 4 - Unger", 5: "Episode 5 - Mama", 6: "Episode 6 - Deadman", 7: "Episode 7 - Clifford",
    8: "Episode 8 - Heartman", 9: "Episode 9 - Higgs", 10: "Episode 10 - Die-Hardman",
    11: "Episode 11 - Clifford Unger", 12: "Episode 12 - Bridges", 13: "Episode 13 - Sam Strand",
    14: "Episode 14 - Lou",
}

# (numero de commande, nom anglais, episode)
MAIN_ORDERS: list[tuple[int, str, int]] = [
    (1, "Smart Drug Delivery", 0),
    (2, "Morphine Delivery: Isolation Ward", 1),
    (3, "Cremation: President's Body", 1),
    (4, "Smart Drug Delivery: Waystation West of Capital Knot City", 2),
    (5, "Rare Metal Delivery: Distribution Center West of Capital Knot City", 2),
    (7, "Recovery: Chiral Printer Interface", 2),
    (8, "Collection: Chiral Crystals", 2),
    (9, "Power Supply Unit Delivery: Wind Farm", 2),
    (14, "Aid Package Delivery: Port Knot City", 2),
    (16, "Elimination: BT", 2),
    (18, "Aid Package Delivery: Lake Knot City", 3),
    (19, "Evo-devo Unit Delivery: Engineer", 3),
    (20, "Prescription Medicine Delivery: Elder", 3),
    (21, "Gun Parts and Anti-BT Weapon Delivery: Craftsman", 3),
    (22, "Recovery: Toolbox", 3),
    (23, "Retrieval: System Server", 3),
    (24, "Prototype Bot Delivery: Distribution Center South of Lake Knot City", 3),
    (27, "Chiralium Gauge Delivery: Weather Station", 3),
    (28, "Wheat Seed Delivery: Timefall Farmers", 3),
    (30, "Old Component Delivery: Junk Dealer", 3),
    (32, "Collection: Old Components", 3),
    (33, "Hourglass Delivery: Chiral Artist", 3),
    (34, "Chiral Artist Delivery: Junk Dealer", 3),
    (38, "Emergency Provisions Delivery: South Knot City", 3),
    (39, "Escape the Battlefield", 4),
    (41, "Building Materials Delivery: Waystation North of Mountain Knot City", 5),
    (43, "Blood Delivery: Distribution Center North of Mountain Knot City", 5),
    (44, "Antimatter Bomb Delivery: Mountain Knot City", 5),
    (46, "Mama Delivery: Mountain Knot City", 5),
    (47, "High-bounce Spring Delivery: Roboticist", 6),
    (48, "Medicine Sample Delivery: Doctor", 6),
    (49, "Antibiotic Delivery: Mountaineer", 6),
    (50, "Medical Device Delivery: Mountaineer", 6),
    (51, "Photograph Delivery: Photographer", 6),
    (52, "Retrieval: Camera", 6),
    (53, "Stone Fragment Delivery: Spiritualist", 6),
    (54, "Escape the Battlefield", 7),
    (55, "Corpse Delivery: Heartman's Lab", 7),
    (58, "Anti-chiralium Medication Delivery: Geologist", 8),
    (59, "Antimatter Bomb Delivery: Paleontologist", 8),
    (60, "Recovery: Ammonites", 8),
    (61, "Tar Extraction Device & Ammonite Delivery: Evo-devo Biologist", 8),
    (62, "Repair: Chiral Relay", 8),
    (63, "Network Activation Key Delivery: Edge Knot City", 9),
    (64, "Elimination: BT", 9),
    (65, "Elimination: Higgs", 9),
    (66, "Fresh Pizza Delivery: Peter Englert", 10),
    (67, "Escape the Battlefield", 11),
    (68, "Cryptobiote Delivery: Capital Knot City Isolation Ward", 12),
    (69, "Go to Her Beach", 13),
    (70, "Cremation: BB", 14),
]


def location_name(number: int, name: str) -> str:
    return f"Order {number} - {name}"


# episode -> noms de lieux, tries par numero de commande
EPISODES: dict[int, list[str]] = {}
for _no, _name, _ep in sorted(MAIN_ORDERS):
    EPISODES.setdefault(_ep, []).append(location_name(_no, _name))

ORDER_TO_LOCATION: dict[int, str] = {no: location_name(no, name) for no, name, _ in MAIN_ORDERS}

# Objets d'equipement/utilite (classification: useful)
USEFUL_ITEMS: dict[str, int] = {
    "Power Skeleton": 1,
    "Speed Skeleton": 1,
    "Cargo Skeleton": 1,
    "Trike": 1,
    "Truck": 1,
    "Road Paver": 1,
    "Zipline Anchor Set": 1,
    "Ladder Set": 2,
    "Climbing Anchor Set": 2,
    "Assault Rifle": 1,
    "Hematic Grenade Pack": 2,
    "Bola Gun": 1,
    "Boot Upgrade": 2,
}

# Objets de remplissage
FILLER_ITEMS: dict[str, int] = {
    "Chiral Crystals": 50,
    "Metals": 20,
    "Ceramics": 20,
    "Resins": 20,
    "Blood Bag": 25,
    "Energy Drink": 20,
    "Repair Spray": 15,
}

# Pieges
# Les 3 premiers remplacent les anciens pieges (Timefall / BT Spawn / Cargo Drop) qui n'avaient aucun effet en jeu.
TRAP_ITEMS: dict[str, int] = {
    "Injury Trap": 20,        # -30 % de vie (ne tue jamais : plancher a 10 %)
    "Fatigue Trap": 25,       # +3000 de fatigue
    "Boot Wear Trap": 20,     # -40 % de durabilite des bottes
}

# Ajoutes apres les pieges pour ne pas decaler les IDs d'objets existants
EXTRA_FILLER_ITEMS: dict[str, int] = {
    "Chemicals": 20,
    "Special Alloys": 10,
}

# Pieges ajoutes apres les objets existants (IDs stables)
EXTRA_TRAP_ITEMS: dict[str, int] = {
    "Rust Trap": 20,          # -1500 d'etat de la combinaison (rouille)
    "Pickpocket Trap": 15,    # -50 cristaux chiraux du sac a dos
}

# Objets de sac a dos ajoutes en dernier (IDs stables)
EXTRA_FILLER2_ITEMS: dict[str, int] = {
    "Cryptobiote Pack": 10,     # +5 cryptobiotes
    "D-Cryptobiote Pack": 5,    # +3 cryptobiotes D
}

# Ajoute en dernier (IDs stables)
EXTRA_FILLER3_ITEMS: dict[str, int] = {
    "Sandalweed Bundle": 10,    # +5 sandalweed
}

# Ajoute en dernier (IDs stables)
EXTRA_FILLER4_ITEMS: dict[str, int] = {
    "Likes Pack": 10,           # +500 likes
}
