# Death Stranding (Director's Cut, PC/Steam) — APWorld Archipelago

🇫🇷 Français · [🇬🇧 English](README.en.md)

Monde et client [Archipelago](https://archipelago.gg) pour **Death Stranding Director's Cut** (PC, Steam).
Projet non officiel, sans lien avec Kojima Productions, 505 Games ni l'équipe d'Archipelago.

> ⚠️ **Bêta.** À utiliser **hors ligne**, en **solo**, sur une **sauvegarde dédiée**.
> Le client lit et écrit la mémoire du jeu : ne l'utilisez jamais en ligne, et faites une copie de vos sauvegardes avant de commencer.

## Sommaire

1. [Ce que fait le mod](#ce-que-fait-le-mod)
2. [Installation](#installation)
3. [Configuration (YAML)](#configuration-yaml)
4. [Lancer une partie](#lancer-une-partie)
5. [Suivi avec PopTracker](#suivi-avec-poptracker-optionnel)
6. [Commandes du client](#commandes-du-client)
7. [Dépannage](#dépannage)
8. [Limites connues](#limites-connues)

## Ce que fait le mod

- **Checks :** les 70 commandes principales (n°1 à 70), détectées automatiquement dans la mémoire du jeu. En option : paliers de likes, d'étapes de commande, de commandes standard et de commandes de bot.
- **Objets reçus, appliqués en jeu par le client :** cristaux chiraux, matériaux (stock d'une installation), likes, effets ponctuels (soins, fatigue, bottes, stamina, cryptobiotes…), pièges, et une **compensation** pour les équipements (voir [le guide](docs/setup_fr.md)).
- **DeathLink :** envoi et réception de la mort de Sam.
- **Victoire :** terminer la dernière commande de l'épisode but (14, ou 12 selon l'option `goal`).
- **Objets « Episode N Access » :** ils structurent la logique de génération et, avec `episode_gating`, retiennent l'envoi des checks d'un épisode tant que l'accès n'est pas reçu. Le jeu lui-même **n'est jamais verrouillé** : rien n'empêche de jouer l'histoire sans les avoir reçus.

Ce qui n'est **pas** fait : verrouiller les épisodes en jeu, débloquer de vrais équipements, checks par commande standard ou optionnelle.

### Fiabilité de la détection des commandes

| Niveau | Commandes | Détail |
|---|---|---|
| ✅ Validées en jeu | 2 à 12, 14 à 16, 18 à 30, 32 à 36, 38 à 44, 46 à 55, 58 à 65, 67 à 70 | Le jeu crée une clé propre à la fin de la commande : détection à la livraison, et rattrapage au lancement du client |
| 🟡 Pas encore rejouées | 13, 17, 31, 37, 45, 56, 57, 66 | Même mécanisme (clés lues dans les fichiers du jeu). Si l'une est signalée trop tôt, trop tard ou jamais : `/check <lieu>` et, si possible, un relevé `/ds_debug on` puis `/ds_counters watch on` dans une issue |
| ⚪ Par le titre de sauvegarde | 1 | Vue quelques secondes après le point de contrôle du jeu, ou retrouvée par déduction |

En complément, le client lit le titre de chaque point de contrôle (« Commande terminée : nº N … ») et **déduit** la fin des commandes obligatoires des épisodes précédents quand le titre montre un épisode plus avancé. Les commandes optionnelles ne sont jamais déduites. Le détail technique est dans [`death_stranding_research/RECHERCHE_compteurs_commandes.md`](https://github.com/R0shinante/Archipelago/blob/death-stranding/death_stranding_research/RECHERCHE_compteurs_commandes.md) (sur la branche du dépôt, hors de l'APWorld).

## Installation

| Élément | Détail |
|---|---|
| Système | **Windows**, Death Stranding Director's Cut (Steam), de préférence **en français** (voir [Autres langues](#autres-langues)) |
| Archipelago | **0.6.x**, de préférence **depuis les sources** (<https://github.com/ArchipelagoMW/Archipelago>) |
| Python | **3.12 ou 3.13** si vous utilisez les sources (sous Windows : 3.12.10 ou plus récent ; 3.10, 3.11 et 3.14 ne conviennent pas) |
| pymem | Bibliothèque Python qui permet au client d'accéder à la mémoire du jeu |

1. **APWorld**, une seule des deux méthodes (sinon le monde est chargé deux fois) :
   - depuis une release : placez `death_stranding.apworld` dans le dossier `custom_worlds` d'Archipelago ;
   - depuis ce dépôt : copiez le dossier `death_stranding` dans le dossier `worlds` d'Archipelago.
2. **pymem** (remplacez `3.12` par votre version de Python) :
   ```
   py -3.12 -m pip install pymem
   ```
   Avec l'installateur officiel d'Archipelago, installez `pymem` dans le Python qui lance le client ; les sources sont recommandées pour ce monde.

## Configuration (YAML)

1. Dans le Launcher d'Archipelago, cliquez sur **Generate Template Options**.
2. Ouvrez `Death Stranding.yaml`, vérifiez `game: Death Stranding` et renseignez votre `name:`.
3. Réglez les options, puis placez le fichier dans le dossier `Players`.

| Option | Valeurs | Défaut | Rôle |
|---|---|---|---|
| `goal` | `finish_episode_14`, `finish_episode_12` | `finish_episode_14` | Condition de victoire |
| `trap_percentage` | 0 à 100 | 15 | Part du remplissage transformée en pièges |
| `episode_gating` | `false`, `true` | `false` | Retient l'envoi des checks d'un épisode N tant que « Episode 1 Access » à « Episode N Access » ne sont pas reçus (`/ds_held` liste les checks retenus) |
| `starting_episodes` | 0 à 5 | 0 | Objets « Episode N Access » donnés au départ (tirés au hasard, épisode 1 compris) |
| `death_link` | vrai / faux | faux | DeathLink |
| `likes_checks` / `likes_step` | 0 à 50 / 100 à 10000 | 0 / 1000 | Nombre de checks de likes (0 = désactivé) / likes par palier |
| `order_checks` / `order_step` | 0 à 100 / 1 à 50 | 0 / 3 | Checks de progression des commandes / étapes par palier |
| `standard_checks` / `standard_step` | 0 à 100 / 1 à 50 | 0 / 3 | Checks de commandes standard livrées / commandes par palier |
| `bot_checks` / `bot_step` | 0 à 100 / 1 à 50 | 0 / 3 | Checks de commandes de bot livrées / commandes par palier |

**Les paliers** (likes, étapes, standard, bot) se comptent **depuis la première connexion** du slot (la base est fixée à ce moment-là) et ne demandent aucune sauvegarde. `/ds_likes`, `/ds_orders`, `/ds_standard` et `/ds_bot` affichent la progression, `/ds_..._rebase` refixe la base. Les likes reçus par des objets « Likes Pack » ne comptent pas.

- **Progression des commandes :** compte les étapes d'objectif accomplies, tous types confondus (livraisons standard, bots, objectifs d'une commande principale) ; pas les marchandises perdues rendues.
- **Commandes standard :** compteur exact du jeu. Elles n'existent en jeu qu'après la n°9.
- **Commandes de bot :** compteur déduit de deux compteurs internes du jeu ; le check arrive environ 90 s après la livraison. Elles n'existent qu'à partir de la n°24 environ, et le compteur dont dépend ce calcul manque dans certaines sauvegardes : `/ds_bot` dit alors « unavailable for now » et aucun palier de bot ne part (le reste fonctionne). Si cela persiste après plusieurs livraisons de bot, mettez `bot_checks` à 0. Une marchandise perdue rendue compte comme une livraison de bot.

Une fois le YAML prêt : Launcher → **Generate** (le zip `AP_xxxxxxxx.zip` apparaît dans `output`), puis **Host**, et notez l'adresse (par défaut `localhost:38281`).

> **À refaire à chaque nouvelle version de l'APWorld :** une partie générée avec une version plus ancienne peut contenir des lieux inconnus du serveur (le client le signale par « Le lieu … n'existe pas dans la partie hébergée »).

## Lancer une partie

1. Lancez Death Stranding **hors ligne** et chargez votre sauvegarde dédiée.
2. Dans le Launcher, ouvrez **Death Stranding Client** et connectez-vous : `/connect localhost:38281`.
3. **Vérifiez l'accès à la mémoire :** `/ds_status` doit afficher vos quantités de cristaux chiraux.
4. **Attendez la fin de la première recherche :** le journal affiche « Main orders: memory reading active … » (environ une minute la première fois, quelques secondes ensuite).
5. **Jouez.** Terminez une commande principale : le client envoie le check et le serveur distribue les objets, qui s'affichent dans la console du client.

Au lancement du client, les commandes déjà terminées dont la clé de fin est présente dans la partie chargée sont rattrapées d'un coup. Pour les autres, `/check <nom du lieu>` envoie le check à la main.

### Autres langues

La lecture des titres n'a été validée que sur le jeu en **français**. Le client reconnaît par défaut des formulations probables dans d'autres langues (anglais, allemand, espagnol, italien, portugais, néerlandais, polonais, tchèque, turc, suédois, russe, japonais, chinois, coréen), mais ce sont des **suppositions**. Les états « en cours » / « incomplet » ne sont jamais pris pour une fin.

Pour vérifier : faites un enregistrement en jeu (acceptez ou terminez une commande), puis tapez `/ds_titles` (environ 1 minute). Le client liste les derniers titres lus avec « COMPLETED » ou « not completed ». Si une commande terminée est notée « not completed », ajoutez un fragment du mot d'état (sans accents, en minuscules) dans `memory_map.json` (copie de `memory_map.default.json` dans le dossier utilisateur d'Archipelago) :

```
"saves": { "completed_words": ["accompli"] }
```

Si `/ds_titles` ne trouve aucun titre, ouvrez une issue avec une capture du titre affiché dans le menu de chargement du jeu.

## Suivi avec PopTracker (optionnel)

Un pack [PopTracker](https://github.com/black-sliver/PopTracker/releases) est fourni (`death_stranding_poptracker_vX.Y.Z.zip` de la release, ou dossier `death_stranding_poptracker/pack` du dépôt) : les 70 commandes par épisode, les accès d'épisode, les objets reçus, l'objectif du slot et les compteurs.

1. Placez le zip **sans le décompresser** dans le dossier `packs` de PopTracker, puis *Open Pack* → « Death Stranding (Archipelago) ».
2. Cliquez sur le « AP » gris, saisissez le serveur, **le nom de votre slot** et le mot de passe : le suivi est automatique (aucune lecture du jeu).

Clic droit sur une case : coche la commande à la main. **SYNC** remet les cases dans l'état du serveur, **ALL** affiche tout en accessible (utile sans `episode_gating`). La case Victoire n'est pas autotrackée.

## Commandes du client

Les commandes courantes :

| Commande | Rôle |
|---|---|
| `/connect <adresse:port>` | Se connecter au serveur |
| `/ds_status` | Quantités lues en mémoire (test de l'accès au jeu) |
| `/locations` | Liste les lieux (commandes) du monde |
| `/check <nom>` | Envoie un check manuellement |
| `/ds_held` | Checks retenus par `episode_gating` |
| `/ds_likes`, `/ds_orders`, `/ds_standard`, `/ds_bot` | Progression des paliers ; `/ds_likes_rebase`, `/ds_orders_rebase`, `/ds_standard_rebase`, `/ds_bot_rebase` refixent la base |
| `/ds_items` | Objets reçus / appliqués en jeu |
| `/ds_stock [installation]` | Stocks de matériaux d'une installation |
| `/ds_stock_mode random\|target`, `/ds_stock_target <installation>`, `/ds_stock_pool Nom1; Nom2` | Où vont les matériaux reçus (au hasard par défaut) |
| `/ds_titles` | Diagnostic des langues : titres de points de contrôle lus en mémoire |
| `/ds_debug on\|off` | Active, pour la session en cours, les commandes de test et de diagnostic ci-dessous (désactivées à chaque lancement du client) |

<details>
<summary>Commandes de test et de diagnostic (après <code>/ds_debug on</code>)</summary>

Toutes ces commandes sont **désactivées par défaut** : elles répondent « Debug command disabled » tant que `/ds_debug on` n'a pas été tapé. Celles qui écrivent dans le jeu sont à réserver aux tests.

| Commande | Rôle |
|---|---|
| `/ds_give <ressource> <n>`, `/ds_likes_give <npc\|players> <n>`, `/ds_stock_give <matériau> <n>` | Écrit une quantité dans le jeu |
| `/ds_effect [nom]` | Applique un piège ou un effet d'objet (sans nom : liste) |
| `/ds_hp`, `/ds_kill` | Vie de Sam ; mise à 0 |
| `/ds_items_reset <n>` | Recale l'index des objets appliqués |
| `/ds_counters snap\|diff\|save [nom]\|watch [on\|off]\|scan\|partial` | Lecture seule : photographie les compteurs nommés du jeu, affiche les changements, écrit `DeathStranding_counters[_nom].json`, ou (`watch`) affiche chaque changement en continu ; `scan` relance la recherche de la table, `partial` décrit une table candidate rejetée |
| `/ds_memdiff snap [inventory\|player\|all\|@0xDÉCALAGE] [taille hex]` puis `/ds_memdiff diff` (`ptrs` liste les zones voisines) | Lecture seule : photo d'une zone de la mémoire du jeu puis liste des mots modifiés |
| `/ds_memdump [inventory\|player\|@0xDÉCALAGE] <décalage hex> <longueur hex>` | Lecture seule : octets bruts d'une zone |

</details>

## Dépannage

| Symptôme | Que faire |
|---|---|
| « Le lieu … n'existe pas dans la partie hébergée » | Régénérez la partie avec la dernière version de l'APWorld |
| `/ds_status` n'affiche rien | Le jeu doit être lancé et la sauvegarde chargée. Les offsets peuvent changer après une mise à jour du jeu (`memory_map.default.json`) |
| Une commande principale terminée n'est pas détectée | Attendez la ligne « memory reading active » au démarrage ; le check part dans les secondes qui suivent la sauvegarde du jeu. Sinon : `/check <nom exact du lieu>` (le client suggère la commande probable quand il signale qu'une fin de commande « could not be identified ») |
| « no save title in memory for now » | Normal tant que le jeu n'a pas écrit de point de contrôle ; le client réessaie tout seul |
| Les compteurs (standard, bot) restent muets | Le client cherche leur table en mémoire dès l'entrée en jeu (jusqu'à quelques minutes). Attendez la fin du chargement, puis `/ds_debug on` et `/ds_counters scan`. Si « table not found » persiste, joignez la sortie de `/ds_counters partial` à une issue |
| « Counter "total" missing from the table… » / `/ds_bot` « unavailable for now » | Normal sur certaines sauvegardes (voir « Commandes de bot ») ; seuls les paliers de bot sont concernés |
| Un effet ou un piège ne s'applique pas | Il attend que Sam soit lisible (ni chargement ni menu). Test : `/ds_debug on` puis `/ds_effect <nom>` |

## Limites connues

- **Aucun verrouillage en jeu.** Les accès d'épisode n'empêchent pas de jouer ; `episode_gating` ne fait que retenir l'envoi des checks (ils survivent à un redémarrage du client, `/check` les envoie sans tenir compte de la retenue).
- **Équipements compensés, pas débloqués.** Écrire la mémoire ne permet pas de créer ni de débloquer un équipement (chaque pièce est liée à des objets vivants du jeu) : ils donnent un effet ponctuel ou des matériaux ([table](docs/setup_fr.md)). Les effets ne modifient jamais durablement l'équilibre du jeu. Cette compensation reste à confirmer en jeu.
- **Commandes optionnelles.** 19 des 70 commandes sont optionnelles (6, 10-13, 15, 17, 25, 26, 29, 31, 35, 37, 40, 42, 45, 56, 57, 66 : tutoriels de construction, pizzas…). Ce sont des checks, mais la génération n'y place jamais d'objet de progression.
- **Victoire.** Validée en jeu pour la n°70 (objectif épisode 14, 30 s à 1 min après la sauvegarde qui suit le générique) et la n°68 (objectif épisode 12). Avec `episode_gating`, elle attend les accès à tous les épisodes jusqu'au but. Si elle ne part pas : `/check <nom du lieu>`.
- **Commande non identifiée.** Si le jeu n'a pas écrit de point de contrôle avant la commande suivante et qu'elle n'a pas de clé de fin connue (n°1, et les commandes 🟡 non rejouées), le client le signale avec la commande probable et le `/check` à taper.
- **Client fermé pendant une commande.** Elle est rattrapée au lancement si sa clé de fin est dans la partie chargée ou si les titres la prouvent ; sinon `/check`. Par prudence, rien n'est déduit si l'épisode du titre dépasse de plus d'un celui de votre commande la plus avancée connue (autre sauvegarde, client lancé en cours de partie).
- **Autres langues** : suppositions non vérifiées (voir plus haut).
- **Offsets mémoire.** Ils viennent d'une table de triche communautaire (seules les adresses sont reprises, pas le fichier) et de relevés personnels. Ils peuvent casser à chaque mise à jour du jeu.

## Licence

MIT. Death Stranding est une marque de Kojima Productions. Ce projet n'est ni approuvé ni affilié.
