# Guide de configuration - Death Stranding Director's Cut (PC)

## Prérequis
- Archipelago 0.6.x (lancé depuis les sources : Python 3.12 ou 3.13) et `pip install pymem`
- Death Stranding Director's Cut (Steam), jouée **hors ligne** sur une **sauvegarde dédiée**

## Génération
1. Génère ton YAML via le Launcher (« Generate Template Options »), `game: Death Stranding`.
2. Place `death_stranding.apworld` dans `custom_worlds`, puis Generate et Host.

## Premier lancement du client
1. Lance le jeu et charge ta sauvegarde, puis ouvre « Death Stranding Client » et connecte-toi : `/connect adresse:port`.
2. **Inventaire :** `/ds_status` doit afficher les quantités ; test d'écriture (après `/ds_debug on`) : `/ds_give Chiral Crystals 10`.
3. **Commandes principales :** attends la ligne « Commandes principales : lecture en mémoire active … » (environ une minute la première fois, quelques secondes ensuite). Terminer une commande principale envoie alors son check.

## Matériaux (résines, métaux, céramiques, produits chimiques, alliages)
Dans le jeu, ces matériaux sont stockés **par installation**, pas dans le sac à dos. Les objets Resins / Metals / Ceramics /
Chemicals / Special Alloys reçus sont donc crédités au stock d'**une installation**, tirée **au hasard** parmi les 39 pour chaque objet
(tirage reproductible, le message « Objet appliqué » indique laquelle). `/ds_stock_mode target` désactive le hasard et crédite toujours
l'installation choisie avec `/ds_stock_target` ; `/ds_stock_pool Nom1; Nom2` limite le tirage à certaines installations (`/ds_stock_pool all` pour tout reprendre).
- `/ds_stock` affiche les 6 valeurs de cette installation (`/ds_stock Port Knot City` pour une autre) ; ouvrez d'abord le menu de
  l'installation en jeu pour comparer.
- `/ds_stock_target <installation>` choisit l'installation du mode `target` (enregistré), `/ds_stock_give Metals 50` (après `/ds_debug on`) teste l'écriture sur cette installation.
- Les offsets viennent d'une table communautaire (jeu v1.004) ; si `/ds_stock` répond « Stocks introuvables » alors que le jeu est chargé,
  ils ne correspondent pas à votre version.

## Paliers optionnels (likes, étapes de commande, commandes standard)
Réglés dans le YAML : `likes_checks` / `likes_step` (likes gagnés depuis la première connexion, `/ds_likes`), `order_checks` / `order_step` (étapes d'objectifs accomplies,
tous types confondus, `/ds_orders`) et `standard_checks` / `standard_step` (commandes standard livrées, compteur exact du jeu, `/ds_standard`). Idem pour les commandes de bot (`bot_checks` / `bot_step`, `/ds_bot`). Aucun ne demande de sauvegarde.

## Comment les checks sont détectés
À chaque checkpoint, le jeu écrit « Commande terminée : nº N … » dans le titre de la sauvegarde. Le client lit ce titre directement dans la mémoire du jeu
et envoie le check « Order N - … » correspondant (la plupart des commandes sont même reconnues tout de suite, par une clé que le jeu crée à leur fin). Seules les commandes terminées **après** le démarrage du client comptent.
Si ton jeu n'est pas en français (les autres langues sont des suppositions, pas encore vérifiées en jeu), tape `/ds_titles` après un enregistrement pour voir ce que lit le client, et ajoute si besoin les mots manquants dans `saves.completed_words` de `memory_map.json`.

### Déchiffrement des sauvegardes (optionnel)
En secours, ou pour une autre langue : l'outil [DeathStrandingSaveDataResigner](https://github.com/mi5hmash/DeathStrandingSaveDataResigner) (version ligne de commande)
lit les checkpoints sur une copie temporaire (tes sauvegardes ne sont jamais modifiées). `/ds_resigner <chemin de l'exe>`, puis `/ds_selftest` ;
`/ds_saves_dir <dossier>` si le dossier n'est pas trouvé, `/ds_resigner off` / `on` pour le désactiver / réactiver, `/ds_catchup` pour traiter les checkpoints déjà présents.

## Limites connues
- Les 70 commandes principales (n°1 à 70) sont des checks. 19 sont optionnelles (Fandom « Story : No » + pizza n°66 : 6, 10-13, 15, 17, 25, 26, 29, 31, 35, 37, 40, 42, 45, 56, 57, 66) : la génération n'y place jamais d'objet de progression. La n°1 et les commandes de type tutoriel (6, 10, 15, 25, 29) ne sont pas vérifiées en jeu : `/check <lieu>` si l'une n'est pas détectée.
- Les objets « Episode N Access » ne verrouillent rien en jeu : ils n'existent que dans la logique de génération. La victoire (dernière commande de l'épisode but) est validée en jeu pour la n°70 (objectif épisode 14) et la n°68 (objectif épisode 12) ;
  `/check <nom du lieu>` envoie un check à la main si elle ne part pas. Avec `episode_gating`, la victoire attend les accès à tous les épisodes jusqu'au but.
- Objets reçus : les cristaux chiraux (+100), les matériaux (stock d'une installation), les pièges et les effets ponctuels listés plus bas agissent en jeu ; le reste de l'équipement est affiché seulement.
- Pièges, effets des objets et crédit des matériaux : validés en jeu. DeathLink aussi (envoi et réception).

## DeathLink
Activez l'option `death_link` dans le YAML, puis régénérez la partie. Le client lit la vie de Sam en mémoire :
- quand elle tombe à 0, il prévient les autres joueurs ;
- quand un DeathLink est reçu, il met la vie de Sam à 0 (dès qu'elle est lisible : pas pendant un chargement ou un menu).
Une mort provoquée par un DeathLink n'est pas renvoyée (20 s de répit), et une mort envoyée bloque les envois pendant 30 s.
Validé en jeu. En cas de doute, testez à la main : `/ds_hp` doit afficher la vie, puis `/ds_debug on` et `/ds_kill` doivent tuer Sam.

## Pièges
Les pièges sont des objets du multimonde qui modifient l'état de Sam en mémoire. Aucun ne peut tuer Sam.
| Objet | Effet |
|---|---|
| Injury Trap | −30 % de la vie maximale (plancher : 10 %) |
| Fatigue Trap | +3000 de fatigue (maximum 10000) |
| Boot Wear Trap | −40 % de durabilité des bottes (plancher : 5 %) |
| Rust Trap | −1500 d'état de la combinaison (rouille, minimum 0) |
| Pickpocket Trap | −50 cristaux chiraux du sac à dos (minimum 0) |

Un piège attend que Sam soit lisible (pas pendant un chargement ou un menu). Après `/ds_debug on`, `/ds_trap` liste les pièges et en applique un à la
main pour tester. Les valeurs sont dans `memory_map.default.json` (section `traps`). Le pourcentage de pièges se règle dans le YAML.

## Objets utiles avec effet
| Objet | Effet |
|---|---|
| Blood Bag | +40 % de la vie maximale (plafonné) |
| Energy Drink | −3000 de fatigue (minimum 0) |
| Repair Spray | +50 % de durabilité des bottes et +1500 d'état de la combinaison (plafonnés) |
| Boot Upgrade | bottes réparées à 100 % de leur durabilité maximale (effet ponctuel, aucun bonus permanent) |
| Power Skeleton | stamina remplie (effet ponctuel) |
| Speed Skeleton | −2000 de fatigue (minimum 0, effet ponctuel) |
| Cryptobiote Pack | +5 cryptobiotes dans le sac à dos |
| D-Cryptobiote Pack | +3 cryptobiotes D dans le sac à dos |
| Sandalweed Bundle | +5 sandalweed dans le sac à dos |

Les autres objets d'équipement (Cargo Skeleton, Trike, Truck, Road Paver, ancrages, échelles, armes, grenades) n'ont **pas d'effet en jeu pour l'instant** : ils sont reçus mais n'agissent pas.

Même mécanique que les pièges : l'effet attend que Sam soit lisible. `/ds_debug on` puis `/ds_effect Blood Bag` permet de tester.
Les valeurs sont dans `memory_map.default.json` (sections `boosts` et `item_grants`).

## Suivi avec PopTracker (optionnel)

Un pack PopTracker (carte des 70 commandes, objets reçus, compteurs, autotracking Archipelago) est disponible dans la release (`death_stranding_poptracker_vX.Y.Z.zip`). Placez-le sans le décompresser dans le dossier `packs` de PopTracker, ouvrez-le, cliquez sur le « AP » gris et saisissez serveur, **nom du slot** et mot de passe. Voir le README, section « Suivi avec PopTracker ».
