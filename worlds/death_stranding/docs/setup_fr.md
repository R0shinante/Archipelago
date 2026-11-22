# Guide de configuration - Death Stranding Director's Cut (PC)

> **Bêta.** À jouer **hors ligne**, en **solo**, sur une **sauvegarde dédiée**. Le client lit et écrit la mémoire du jeu.

## Prérequis
- Archipelago 0.6.x (de préférence lancé depuis les sources : Python 3.12 ou 3.13) et `pip install pymem`
- Death Stranding Director's Cut (Steam), de préférence en français (voir le README, « Autres langues »)

## Génération
1. Génère ton YAML via le Launcher (« Generate Template Options »), `game: Death Stranding`, et règle les options (tableau complet dans le README).
2. Place `death_stranding.apworld` dans `custom_worlds`, puis Generate et Host.

## Premier lancement du client
1. Lance le jeu et charge ta sauvegarde dédiée, puis ouvre « Death Stranding Client » et connecte-toi : `/connect adresse:port`.
2. **Accès à la mémoire :** `/ds_status` doit afficher tes quantités.
3. **Commandes principales :** attends la ligne « Main orders: memory reading active … » (environ une minute la première fois, quelques secondes ensuite). Terminer une commande principale envoie alors son check.

Si un check ne part pas, `/check <nom exact du lieu>` l'envoie à la main. `/locations` liste les noms des lieux.

## Paliers optionnels
Réglés dans le YAML : `likes_checks` / `likes_step`, `order_checks` / `order_step`, `standard_checks` / `standard_step` et `bot_checks` / `bot_step`. Ils se comptent depuis la première connexion du slot et ne demandent aucune sauvegarde. `/ds_likes`, `/ds_orders`, `/ds_standard` et `/ds_bot` affichent la progression.

## Objets reçus et effets
Les effets sont ponctuels et ne modifient jamais durablement l'équilibre du jeu. Un effet attend que Sam soit lisible (ni chargement ni menu).

### Pièges
Aucun ne peut tuer Sam.

| Objet | Effet |
|---|---|
| Injury Trap | −30 % de la vie maximale (plancher : 10 %) |
| Fatigue Trap | +3000 de fatigue (maximum 10000) |
| Boot Wear Trap | −40 % de durabilité des bottes (plancher : 5 %) |
| Rust Trap | −1500 d'état de la combinaison (minimum 0) |
| Pickpocket Trap | −50 cristaux chiraux du sac à dos (minimum 0) |

La part de pièges se règle dans le YAML (`trap_percentage`).

### Objets utiles
| Objet | Effet |
|---|---|
| Blood Bag | +40 % de la vie maximale (plafonné) |
| Energy Drink | −3000 de fatigue (minimum 0) |
| Repair Spray | +50 % de durabilité des bottes et +1500 d'état de la combinaison (plafonnés) |
| Boot Upgrade | bottes réparées à 100 % de durabilité |
| Power Skeleton | stamina remplie |
| Speed Skeleton | −2000 de fatigue (minimum 0) |
| Cryptobiote Pack | +5 cryptobiotes dans le sac à dos |
| D-Cryptobiote Pack | +3 cryptobiotes D dans le sac à dos |
| Sandalweed Bundle | +5 sandalweed dans le sac à dos |
| Chiral Crystals | +100 cristaux chiraux dans le sac à dos |
| Likes Pack | +500 likes |

### Équipements (compensation)
Écrire la mémoire ne permet pas de débloquer un équipement dans le jeu (chaque pièce est liée à des objets vivants du jeu) : le recevoir donne donc une compensation. Cette partie reste à confirmer en jeu.

| Objet | Compensation |
|---|---|
| Cargo Skeleton | stamina remplie + −1000 de fatigue |
| Hematic Grenade Pack | +40 % de la vie maximale (comme une Blood Bag) |
| Trike | +100 métaux |
| Truck | +50 alliages spéciaux |
| Road Paver | +100 céramiques |
| Zipline Anchor Set | +50 métaux |
| Ladder Set | +50 résines |
| Climbing Anchor Set | +50 céramiques |
| Assault Rifle | +100 produits chimiques |
| Bola Gun | +100 cristaux chiraux dans le sac à dos |

### Matériaux
Les résines, métaux, céramiques, produits chimiques et alliages sont stockés **par installation** dans le jeu, pas dans le sac à dos. Chaque objet « matériau » reçu est crédité au stock d'**une installation tirée au hasard** parmi les 39 (tirage reproductible ; la ligne « Item applied » du journal indique laquelle). `/ds_stock_mode target` désactive le hasard et crédite toujours l'installation choisie avec `/ds_stock_target <installation>` ; `/ds_stock_pool Nom1; Nom2` limite le tirage à certaines installations (`/ds_stock_pool all` pour tout reprendre). `/ds_stock` affiche les 6 valeurs d'une installation (`/ds_stock Port Knot City` pour une autre) : ouvre d'abord son menu en jeu pour comparer.

### « Episode N Access »
Ils n'agissent pas dans le jeu lui-même. Ils structurent la logique de génération et, avec `episode_gating`, retiennent les checks d'un épisode tant que son accès n'est pas reçu.

## DeathLink
Active `death_link` dans le YAML puis régénère. Le client lit la vie de Sam : quand elle tombe à 0, il prévient les autres joueurs ; à la réception d'un DeathLink, il met la vie de Sam à 0 (dès qu'elle est lisible). Une mort provoquée par un DeathLink n'est pas renvoyée (20 s) et une mort envoyée bloque les envois pendant 30 s.

## Commandes de test et de diagnostic
Elles sont désactivées par défaut. `/ds_debug on` les active pour la session (`/ds_give`, `/ds_effect`, `/ds_likes_give`, `/ds_stock_give`, `/ds_kill`, `/ds_hp`, `/ds_items_reset`, `/ds_counters`, `/ds_memdiff`, `/ds_memdump`) ; les valeurs sont dans `memory_map.default.json` (sections `traps`, `boosts`, `item_grants`). Pour tester un effet : `/ds_debug on` puis `/ds_effect Blood Bag`.

## Suivi avec PopTracker (optionnel)
Un pack PopTracker (carte des 70 commandes, objets reçus, compteurs, autotracking Archipelago) est disponible dans la release (`death_stranding_poptracker_vX.Y.Z.zip`). Place-le sans le décompresser dans le dossier `packs` de PopTracker, ouvre-le, clique sur le « AP » gris et saisis serveur, **nom du slot** et mot de passe. Voir le README.

## Limites connues
Voir le README, section « Limites connues ».
