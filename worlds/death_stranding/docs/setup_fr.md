# Guide de configuration - Death Stranding Director's Cut (PC)

## Prérequis
- Archipelago 0.6.x (lancé depuis les sources : Python 3.12 ou 3.13) et `pip install pymem`
- Death Stranding Director's Cut (Steam), jouée **hors ligne** sur une **sauvegarde dédiée**
- L'outil DeathStrandingSaveDataResigner (version ligne de commande, `death-stranding-savedata-resigner-cli.exe`) :
  le client s'en sert pour déchiffrer les checkpoints (copie temporaire, tes sauvegardes ne sont jamais modifiées)

## Génération
1. Génère ton YAML via le Launcher (« Generate Template Options »), `game: Death Stranding`.
2. Place `death_stranding.apworld` dans `custom_worlds`, puis Generate et Host.

## Premier lancement du client
1. Lance le jeu et charge ta sauvegarde, puis ouvre « Death Stranding Client » et connecte-toi : `/connect adresse:port`.
2. **Inventaire :** `/ds_status` doit afficher les quantités ; test d'écriture : `/ds_give Chiral Crystals 10`.
3. **Sauvegardes :**
   - `/ds_resigner C:\chemin\death-stranding-savedata-resigner-cli.exe` (une seule fois)
   - `/ds_saves_dir <dossier>` seulement si le dossier n'est pas trouvé automatiquement
     (c'est celui qui contient les sous-dossiers de checkpoints, ex. `...\KojimaProductions\DeathStrandingDC\<ton identifiant>`)
   - `/ds_selftest` déchiffre le dernier checkpoint et affiche son titre : c'est la vérification de toute la chaîne.
   - `/ds_saves` affiche l'état (checkpoints vus, commandes terminées détectées).

## Matériaux (résines, métaux, céramiques, produits chimiques, alliages)
Dans le jeu, ces matériaux sont stockés **par installation**, pas dans le sac à dos. Les objets Resins / Metals / Ceramics /
Chemicals / Special Alloys reçus sont donc crédités au stock d'**une installation**, tirée **au hasard** parmi les 39 pour chaque objet
(tirage reproductible, le message « Objet appliqué » indique laquelle). `/ds_stock_mode target` désactive le hasard et crédite toujours
l'installation choisie avec `/ds_stock_target` ; `/ds_stock_pool Nom1; Nom2` limite le tirage à certaines installations (`/ds_stock_pool all` pour tout reprendre).
- `/ds_stock` affiche les 6 valeurs de cette installation (`/ds_stock Port Knot City` pour une autre) ; ouvrez d'abord le menu de
  l'installation en jeu pour comparer.
- `/ds_stock_target <installation>` choisit l'installation du mode `target` (enregistré), `/ds_stock_give Metals 50` teste l'écriture sur cette installation.
- Les offsets viennent d'une table communautaire (jeu v1.004) ; si `/ds_stock` répond « Stocks introuvables » alors que le jeu est chargé,
  ils ne correspondent pas à votre version.

## Comment les checks sont détectés
À chaque checkpoint, le jeu écrit « Commande terminée : nº N … » dans le titre de la sauvegarde. Le client lit ce
numéro et envoie le check « Order N - … » correspondant. Seules les modifications **après** le démarrage du client
comptent ; `/ds_catchup` traite aussi les checkpoints déjà présents (à utiliser avec prudence).
Si ton jeu n'est pas en français, ajuste `saves.completed_words` dans `memory_map.json`.

## Limites connues
- Seules les commandes principales de la liste sont des checks (51). La liste vient d'une page communautaire
  et peut contenir des erreurs (n°17 absente, n°66 au nom approximatif).
- Les objets reçus n'ont d'effet en jeu que pour les Chiral Crystals (+100, sac à dos) et les matériaux (stock d'une installation) ; le reste est affiché seulement.
- DeathLink, pièges et effets des objets : expérimentaux, voir plus bas.

## DeathLink (expérimental)
Activez l'option `death_link` dans le YAML, puis régénérez la partie. Le client lit la vie de Sam en mémoire :
- quand elle tombe à 0, il prévient les autres joueurs ;
- quand un DeathLink est reçu, il met la vie de Sam à 0 (dès qu'elle est lisible : pas pendant un chargement ou un menu).
Une mort provoquée par un DeathLink n'est pas renvoyée (20 s de répit), et une mort envoyée bloque les envois pendant 30 s.
**Avant de l'activer**, testez à la main : `/ds_hp` doit afficher la vie, puis `/ds_kill` doit tuer Sam. Si la vie affichée est
juste mais que Sam ne meurt pas, signalez-le : la mort passera alors par une autre valeur (conscience).

## Pièges (expérimental)
Les pièges sont des objets du multimonde qui modifient l'état de Sam en mémoire. Aucun ne peut tuer Sam.
| Objet | Effet |
|---|---|
| Injury Trap | −30 % de la vie maximale (plancher : 10 %) |
| Fatigue Trap | +3000 de fatigue (maximum 10000) |
| Boot Wear Trap | −40 % de durabilité des bottes (plancher : 5 %) |
| Rust Trap | −1500 d'état de la combinaison (rouille, minimum 0) |
| Pickpocket Trap | −50 cristaux chiraux du sac à dos (minimum 0) |

Un piège attend que Sam soit lisible (pas pendant un chargement ou un menu). `/ds_trap` liste les pièges et en applique un à la
main pour tester. Les valeurs sont dans `memory_map.default.json` (section `traps`). Le pourcentage de pièges se règle dans le YAML.

## Objets utiles avec effet (expérimental)
| Objet | Effet |
|---|---|
| Blood Bag | +40 % de la vie maximale (plafonné) |
| Energy Drink | −3000 de fatigue (minimum 0) |
| Repair Spray | +50 % de durabilité des bottes et +1500 d'état de la combinaison (plafonnés) |
| Cryptobiote Pack | +5 cryptobiotes dans le sac à dos |
| D-Cryptobiote Pack | +3 cryptobiotes D dans le sac à dos |
| Sandalweed Bundle | +5 sandalweed dans le sac à dos |

Même mécanique que les pièges : l'effet attend que Sam soit lisible. `/ds_effect Blood Bag` permet de tester.
Les valeurs sont dans `memory_map.default.json` (sections `boosts` et `item_grants`).

### Localiser une valeur du sac à dos (aide)
`/ds_find <quantité> <maximum>` cherche, dans l'objet d'inventaire, un compteur de la forme (quantité, maximum à +4). Exemple : avec 12 sandalweed
sur un maximum de 99, `/ds_find 12 99` liste les décalages trouvés ; recommencez avec une autre quantité pour ne garder que le décalage commun.
(La sandalweed est à +0x388C, trouvée ainsi.)

### Chercher l'objet des likes (aide, expérimental)
Les compteurs de likes sont des entiers de 8 octets dans un objet que les tables communautaires ne localisent que par injection de code.
`/ds_findlikes <likes reçus des PNJ> <likes reçus d'autres joueurs>` (valeurs exactes du menu, +0x18 et +0x20 dans l'objet) explore, en lecture
seule, les objets voisins de la chaîne connue (20 s maximum). `/ds_findobj 0x18=<valeur> 0x20=<valeur>` est la version générale (décalages imposés) ; `/ds_findval <valeur> ...` cherche ces entiers (4 ou 8 octets)
à n'importe quel décalage et classe en premier les objets qui en contiennent le plus.

### Recherche complète avec `/ds_trace` (aide, expérimental)
`/ds_trace 0x18=25390 0x20=1741` cherche l'objet dans **toute** la mémoire du jeu (lecture seule, 1 à 3 minutes, `ds.exe` doit être chargé
et le menu ne doit pas changer), puis remonte les pointeurs jusqu'à une racine statique du module. Elle affiche des chaînes de la forme
`ds.exe+0x… -> +0x… -> +0x…`. Cette commande nécessite `numpy` : `py -3.12 -m pip install numpy`.
