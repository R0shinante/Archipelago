# Death Stranding (Director's Cut, PC/Steam) — APWorld Archipelago

🇫🇷 Français · [🇬🇧 English](README.en.md)

Monde et client [Archipelago](https://archipelago.gg) expérimentaux pour **Death Stranding Director's Cut** (PC, Steam).
Projet non officiel, sans lien avec Kojima Productions, 505 Games ni l'équipe d'Archipelago.

> ⚠️ **Alpha.** À utiliser **hors ligne**, en **solo**, sur une **sauvegarde dédiée aux tests**.
> Le client lit et écrit la mémoire du jeu : ne l'utilisez jamais en ligne, et faites une copie de vos sauvegardes avant de commencer.

## Sommaire

1. [Ce que fait le mod](#ce-que-fait-le-mod)
2. [Installation](#installation)
3. [Configuration (YAML)](#configuration-yaml)
4. [Lancer une partie](#lancer-une-partie)
5. [Commandes du client](#commandes-du-client)
6. [Dépannage](#dépannage)
7. [Limites connues](#limites-connues)

## Ce que fait le mod

Les **70 commandes principales** (n°1 à 70) sont des checks. Des objets « Episode N Access » structurent la logique de génération (un épisode n'est « atteignable » qu'une fois
son objet reçu), mais **le jeu lui-même n'est pas verrouillé** : rien n'empêche de jouer l'histoire sans les avoir reçus (voir [Limites connues](#limites-connues)).
Les autres objets du multimonde (cristaux, matériaux, équipement, pièges) sont appliqués en jeu par le client, qui accède à la mémoire du jeu.

| Fonction | État |
|---|---|
| Checks : commandes principales (70), détectées automatiquement | ✅ |
| Objets « Episode N Access » dans la logique de génération (régions d'épisodes) | ✅ reçus et affichés, mais **sans effet en jeu** |
| Verrouillage réel des épisodes en jeu (empêcher de jouer un épisode sans l'objet) | ❌ pas possible pour l'instant |
| Cristaux chiraux appliqués en jeu | ✅ |
| DeathLink (envoi et réception de la mort du joueur) | ✅ validé en jeu |
| Paliers de likes comme checks (`likes_checks` / `likes_step`, jusqu'à 50) | ✅ validé en jeu |
| Paliers de progression des commandes comme checks (`order_checks` / `order_step`, jusqu'à 100, sans sauvegarde) | ✅ validé en jeu : compte les étapes de commande, tous types confondus |
| Paliers de commandes standard livrées comme checks (`standard_checks` / `standard_step`, jusqu'à 100, sans sauvegarde) | ✅ validé en jeu : compteur exact du jeu (clé 17 de la table de statistiques) |
| Effets ponctuels : Blood Bag, Energy Drink, Repair Spray, Boot Upgrade, Power Skeleton, Speed Skeleton, Cryptobiote Pack, D-Cryptobiote Pack, Sandalweed Bundle | ✅ validé en jeu |
| Objet « Likes Pack » (+500 likes) | ✅ validé en jeu |
| Matériaux (résines, métaux, céramiques, chimiques, alliages) crédités au stock d'une installation | ✅ validé en jeu |
| Pièges : Injury, Fatigue, Boot Wear, Rust, Pickpocket | ✅ validé en jeu |
| Paliers de commandes de bot livrées comme checks (`bot_checks` / `bot_step`, jusqu'à 100, sans sauvegarde) | ✅ validé en jeu : déduit de compteurs internes du jeu ; le check arrive environ 90 s après la livraison |
| Détection des commandes principales terminées en lisant la mémoire du jeu (sans outil ni déchiffrement) | ✅ validé en jeu (français) ; le déchiffrement des sauvegardes reste disponible en option |
| Rattrapage des commandes déjà terminées quand le client se lance ou qu'une commande n'apparaît pas dans le titre | ✅ validé en jeu : clés de fin de commande validées sur les n°2 à 10, 14, 15, 26 et 61 à 70 ; les autres : voir « Couverture de la détection immédiate » (clés lues dans les fichiers du jeu ou déduction par les titres de sauvegarde) |
| Checks nominatifs par commande standard / optionnelle | ❌ |

Les checks sont identifiés par `7 770 000 + numéro de commande`. Le client détecte une commande principale terminée en lisant, **directement dans la mémoire du jeu**,
le titre du point de contrôle (« Commande terminée : nº N … ») : aucun outil supplémentaire n'est nécessaire. Pour les commandes dont le jeu crée une clé propre à la fin (voir « Couverture de la détection immédiate » ci-dessous), le client les reconnaît **tout de suite**, sans attendre le prochain enregistrement du jeu (« Commande terminée détectée (marqueur) »). Au lancement du client, les commandes dont la clé est déjà présente (voir le tableau ci-dessous) sont rattrapées d'un coup, y compris celles que le titre de sauvegarde ne montre jamais (n°6, 8…). La première recherche prend environ une minute ; le client
mémorise ensuite la zone de mémoire utilisée et la fouille en premier aux lancements suivants (quelques secondes). Si le jeu déplace ses données (autre sauvegarde,
redémarrage), la recherche complète reprend toute seule. Le déchiffrement des sauvegardes reste disponible en option, en secours ([voir plus bas](#déchiffrement-des-sauvegardes-optionnel)).

### Couverture de la détection immédiate

| Niveau | Commandes | Comment le client les voit |
|---|---|---|
| ✅ Validées en jeu | 2 à 10, 14, 15, 26, 61 à 65, 67, 68 et 70 | Clé de fin de commande créée par le jeu : détection à la livraison, et rattrapage au lancement du client |
| 🟡 Clés lues dans les fichiers du jeu, pas encore rejouées | 11 à 13, 16 à 25, 27, 28, 30 à 37, 40 à 45, 47 à 53, 55 à 60 et 66 | Même mécanisme ; si une commande est signalée trop tôt, trop tard ou jamais, merci de le signaler avec un relevé `/ds_counters watch on` |
| ⚪ Par les titres de sauvegarde seulement | 1, 29, 38, 39, 46, 54 et 69 | Lecture du titre du point de contrôle (quelques secondes après la sauvegarde du jeu) et déduction ; `/check <lieu>` en dernier recours |

La clé de fin d'une commande est l'identifiant de la phrase de son **objectif final** (par exemple « Deliver all four containers of aid. » pour la n°14). Les clés des autres commandes ont été lues dans les fichiers de mission de la copie du jeu de l'auteur (rien du jeu n'est livré avec l'APWorld) et recoupées avec les clés relevées en jeu. Les commandes à plusieurs objectifs ont leur clé d'objectif final déduite du texte (ramasser, puis livrer) ; celles dont l'objectif final reste ambigu sont dans la dernière ligne.

## Installation

### Ce qu'il vous faut

| Élément | Détail |
|---|---|
| Système | **Windows**, avec Death Stranding Director's Cut (Steam), en français (voir [Autres langues](#autres-langues)) |
| Archipelago | **0.6.x**, de préférence **depuis les sources** (<https://github.com/ArchipelagoMW/Archipelago>) |
| Python | **3.12 ou 3.13** si vous utilisez les sources (sous Windows : 3.12.10 ou plus récent ; 3.10, 3.11 et 3.14 ne conviennent pas) |
| pymem | Bibliothèque Python qui permet au client d'accéder à la mémoire du jeu |

### Étape 1 — Installer l'APWorld

Choisissez **une seule** des deux méthodes (sinon le monde est chargé deux fois) :

- **Depuis une release (le plus simple) :** téléchargez `death_stranding.apworld` et placez-le dans le dossier `custom_worlds` d'Archipelago.
- **Depuis ce dépôt :** copiez le dossier `death_stranding` dans le dossier `worlds` d'Archipelago.

### Étape 2 — Installer pymem

Dans une invite de commandes (remplacez `3.12` par votre version de Python) :

```
py -3.12 -m pip install pymem
```

Avec l'installateur officiel d'Archipelago, installez `pymem` dans le Python qui lance le client ; les sources sont recommandées pour ce monde.

## Configuration (YAML)

1. Dans le Launcher d'Archipelago, cliquez sur **Generate Template Options**.
2. Ouvrez `Death Stranding.yaml`, vérifiez `game: Death Stranding` et renseignez votre `name:`.
3. Réglez les options ci-dessous, puis placez le fichier dans le dossier `Players`.

| Option | Valeurs | Défaut | Rôle |
|---|---|---|---|
| `goal` | `finish_episode_14`, `finish_episode_12` | `finish_episode_14` | Condition de victoire |
| `trap_percentage` | 0 à 100 | 15 | Part du remplissage transformée en pièges |
| `episode_gating` | `false`, `true` | `false` | Retient l'envoi des checks de commandes principales tant que les objets « Episode 1 Access » à « Episode N Access » ne sont pas reçus (voir plus bas) |
| `starting_episodes` | 0 à 5 | 0 | Nombre d'objets « Episode N Access » donnés au départ (épisodes tirés au hasard, épisode 1 compris ; logique de génération seulement) |
| `death_link` | vrai / faux | faux | DeathLink (voir ci-dessous) |
| `likes_checks` | 0 à 50 | 0 | Nombre de checks de likes (0 = désactivé) |
| `likes_step` | 100 à 10000 | 1000 | Likes à gagner par palier |
| `order_checks` | 0 à 100 | 0 | Nombre de checks de progression des commandes (0 = désactivé) |
| `order_step` | 1 à 50 | 3 | Étapes de commande par palier |
| `standard_checks` | 0 à 100 | 0 | Nombre de checks de commandes standard livrées (0 = désactivé) |
| `standard_step` | 1 à 50 | 3 | Commandes standard à livrer par palier |
| `bot_checks` | 0 à 100 | 0 | Nombre de checks de commandes de bot livrées (0 = désactivé) |
| `bot_step` | 1 à 50 | 3 | Commandes de bot à livrer par palier |

**Likes.** Le check « Likes Milestone N » se débloque quand vous gagnez N × `likes_step` likes **depuis la première connexion** (la base est fixée à ce moment-là).
Les likes reçus par des objets « Likes Pack » ne comptent pas. `/ds_likes` affiche la progression.

**Progression des commandes.** Le check « Order Progress N » se débloque quand le compteur d'étapes de commande gagne N × `order_step` **depuis la première connexion**.
Ce compteur monte à chaque étape d'objectif accomplie : livraison de commande standard, commande de bot, acceptation et objectifs intermédiaires d'une commande principale.
Il mesure des étapes, tous types confondus, et ne compte pas les livraisons de marchandise perdue. Il fonctionne en direct, sans sauvegarde, client connecté.
`/ds_orders` affiche la progression, `/ds_orders_rebase` refixe la base.

**Commandes standard.** Le check « Standard Orders N » se débloque quand vous avez livré N × `standard_step` commandes standard **depuis la première connexion**. C'est le compteur exact du jeu, lu en direct, sans sauvegarde : les commandes principales, les commandes de bot et les marchandises perdues ne comptent pas. Les commandes standard ne sont accessibles en jeu qu'après la livraison de la n°9 (relevé) : aucun palier avant. `/ds_standard` affiche la progression, `/ds_standard_rebase` refixe la base.

**Commandes de bot.** Le check « Bot Orders N » se débloque après N × `bot_step` livraisons de bot **depuis la première connexion**, sans sauvegarde. Le compteur est déduit de deux compteurs internes du jeu (total et hors bot), qui ne sont pas écrits au même moment : le client attend environ 90 s sans changement avant de valider, pour éviter les faux positifs pendant une livraison, et retient la validation tant qu'une commande standard (écran de résultat) est en cours de finalisation. Une fin de commande principale ou spéciale (le jeu ne fait alors monter que le compteur total) est reconnue à la clé que le jeu crée au même moment ou à un saut de likes : la confirmation est retenue 5 minutes, puis la hausse est écartée de la base du bot (journal : « Fin de commande principale ou spéciale reconnue dans les compteurs »). **Limites connues :** le jeu n'écrit pas de compteur distinct pour les marchandises perdues rendues, qui augmentent le compteur de bot comme une livraison de bot et comptent donc dans ces paliers (relevé sur deux livraisons) ; un vrai bot récupéré à 10 s d'une création de clé sans rapport peut, plus rarement, être écarté à tort. Les demandes d'équipement ne sont pas testées (elles exigent d'être en ligne). `/ds_bot` affiche la progression, `/ds_bot_rebase` refixe la base. Les commandes principales ne sont pas concernées : elles ont leurs checks nominatifs. **Disponibilité :** les commandes de bot n'existent en jeu qu'à partir de la n°24 environ, et le compteur « total » dont dépend ce calcul n'existe pas dans la table de toutes les sauvegardes (relevé : absent sur une sauvegarde à la n°36, présent sur une autre à la n°61). Tant qu'il manque, `/ds_bot` indique « indisponibles pour l'instant », aucun palier de bot ne part et le reste du client fonctionne normalement ; quand il apparaît, la base est fixée après environ 90 s de valeurs stables. Si `/ds_bot` reste indisponible sur ta partie après plusieurs livraisons de bot, mets `bot_checks` à 0 : ces checks ne se débloqueront pas.

**DeathLink.** Le client lit la vie de Sam : à 0, il prévient les autres joueurs ; à la réception d'un DeathLink, il met la vie de Sam à 0
(dès qu'elle est lisible, donc pas pendant un chargement ou un menu). Une mort reçue n'est pas renvoyée (20 s de répit) et une mort envoyée bloque
les envois 30 s.

Une fois le YAML prêt : Launcher → **Generate**, le fichier `AP_xxxxxxxx.zip` apparaît dans `output` ; Launcher → **Host**, choisissez ce zip et notez
l'adresse (par défaut `localhost:38281`).

> **À refaire à chaque nouvelle version de l'APWorld :** une partie générée avec une version plus ancienne peut contenir des lieux inconnus du serveur.
> Le client le signale par « Le lieu … n'existe pas dans la partie hébergée ».

## Lancer une partie

1. Lancez Death Stranding **hors ligne** et chargez votre sauvegarde dédiée.
2. Dans le Launcher d'Archipelago, ouvrez **Death Stranding Client** et connectez-vous : `/connect localhost:38281`.
3. **Vérifiez l'accès à la mémoire :** `/ds_status` doit afficher vos quantités de cristaux chiraux. Test d'écriture (après `/ds_debug on`) : `/ds_give Chiral Crystals 10`.
4. **Attendez la fin de la première recherche :** le log affiche « Commandes principales : lecture en mémoire active … » (environ une minute la première fois, quelques secondes ensuite).
5. **Jouez.** Terminez une commande principale : le client lit son titre en mémoire, envoie le check et le serveur distribue les objets.
   Les objets reçus s'affichent dans la console du client. Seules les commandes terminées **après** le démarrage du client comptent.

### Déchiffrement des sauvegardes (optionnel)

Inutile en temps normal. Il sert de secours, ou si votre jeu n'est pas en français. Le client utilise alors l'outil tiers
[DeathStrandingSaveDataResigner](https://github.com/mi5hmash/DeathStrandingSaveDataResigner) (version en ligne de commande, onglet *Releases*, non inclus ici) sur une **copie
temporaire** de vos checkpoints : vos sauvegardes ne sont jamais modifiées.
```
/ds_resigner C:\Games\death-stranding-savedata-resigner-cli.exe
/ds_selftest
```
`/ds_selftest` déchiffre le dernier checkpoint et affiche son titre. Si le dossier des sauvegardes n'est pas trouvé automatiquement :
`/ds_saves_dir C:\Users\<vous>\AppData\Local\KojimaProductions\DeathStrandingDC\<identifiant Steam>` (le dossier qui contient les sous-dossiers `checkpoint…`).
`/ds_resigner off` désactive le déchiffrement, `/ds_resigner on` le réactive, `/ds_catchup` traite aussi les checkpoints déjà présents (avec prudence).

### Autres langues

La lecture en mémoire n'a été validée que sur le jeu en **français**. Le client reconnaît par défaut, **sans réglage**, des formulations probables dans d'autres langues
(anglais « Order Completed : No. 12 … », allemand, espagnol, italien, portugais, néerlandais, polonais, tchèque, turc, suédois, russe, japonais, chinois, coréen), mais ce sont des **suppositions** :
le format exact n'est pas confirmé en jeu. Les états « en cours » / « incomplet » ne sont jamais pris pour une fin de commande.

Pour vérifier avec ton jeu : fais un enregistrement (accepte ou termine une commande), puis tape **`/ds_titles`** (~1 minute). Le client affiche les derniers titres de points de contrôle lus en mémoire,
avec « TERMINEE » / « pas terminee » pour chacun. Si une commande terminée est notée « pas terminee », ajoute un fragment du mot de l'état dans `saves.completed_words` de `memory_map.json`
(copiez `memory_map.default.json` en `memory_map.json` dans le dossier utilisateur d'Archipelago, c'est le même fichier qui sert à modifier les offsets). Ces mots **s'ajoutent** aux mots par défaut :
```
"saves": { "completed_words": ["accompli"] }
```
Un fragment de mot suffit (sans accents, en minuscules). Si `/ds_titles` ne trouve aucun titre, ouvre une issue GitHub avec une capture du titre affiché dans le menu de chargement du jeu : le format de ta langue sera ajouté.
En cas de doute, utilisez le déchiffrement des sauvegardes.

## Commandes du client

<details>
<summary>Afficher la liste</summary>

| Commande | Rôle |
|---|---|
| `/locations` | Liste les lieux (commandes) du monde |
| `/check <nom>` | Envoie un check manuellement |
| `/ds_status` | Quantités lues en mémoire |
| `/ds_debug on\|off` | Active ou coupe, pour la session en cours, les commandes de test qui **écrivent dans le jeu** (`/ds_give`, `/ds_effect`, `/ds_trap`, `/ds_likes_give`, `/ds_stock_give`, `/ds_kill`). Coupées à chaque lancement du client |
| `/ds_give <ressource> <quantité>` | Test (après `/ds_debug on`) : écriture en mémoire (sac à dos) |
| `/ds_effect [nom]` | Test (après `/ds_debug on`) d'un piège ou d'un effet d'objet (sans nom : liste) ; `/ds_trap` est un alias |
| `/ds_likes` | Likes lus en mémoire (PNJ / joueurs / total) |
| `/ds_likes_give <npc\|players> <n>` | Test (après `/ds_debug on`) : écriture d'un compteur de likes |
| `/ds_likes_rebase` | Refixe la base des paliers de likes |
| `/ds_orders` | Compteur d'étapes de commande et progression des paliers |
| `/ds_orders_rebase` | Refixe la base des paliers de progression des commandes |
| `/ds_standard` | Commandes standard livrées (compteur du jeu) et progression des paliers |
| `/ds_standard_rebase` | Refixe la base des paliers de commandes standard |
| `/ds_bot` | Commandes de bot livrées (compteur en direct) et progression des paliers |
| `/ds_bot_rebase` | Refixe la base des paliers de commandes de bot |
| `/ds_counters snap\|diff\|save [nom]\|watch [on\|off]\|scan\|partial` | Diagnostic (lecture seule) : photographie tous les compteurs nommés du jeu, affiche ceux qui ont changé depuis la photo, les écrit dans `DeathStranding_counters[_nom].json`, ou (`watch`) écrit en continu chaque changement dans la console (à couper après le test) ; `scan` relance tout de suite la recherche de la table ; `partial` décrit la table candidate rejetée (`DeathStranding_counters_partial.json`) |
| `/ds_held` | Liste les checks retenus par l'option `episode_gating`, en attente d'un objet « Episode N Access » |
| `/ds_hp` | Vie du joueur lue en mémoire (test) |
| `/ds_kill` | Test (après `/ds_debug on`) : met la vie de Sam à 0 |
| `/ds_items` | Objets reçus / appliqués en jeu (diagnostic) |
| `/ds_items_reset <n>` | Recale l'index des objets appliqués |
| `/ds_stock [installation]` | Stocks de matériaux d'une installation |
| `/ds_stock_mode random\|target` | Répartition des matériaux : installation au hasard (défaut) ou choisie |
| `/ds_stock_pool Nom1; Nom2` | Limite le tirage au hasard à certaines installations (`all` = toutes) |
| `/ds_stock_target <installation>` | Installation créditée en mode `target` |
| `/ds_stock_give <matériau> <quantité>` | Test (après `/ds_debug on`) : écriture d'un stock |
| `/ds_resigner <exe>` | (optionnel) Chemin de l'outil de déchiffrement. `/ds_resigner off` / `on` : désactive / réactive le déchiffrement |
| `/ds_saves_dir <dossier>` | (optionnel) Dossier des sauvegardes |
| `/ds_saves` | (optionnel) État du déchiffrement (checkpoints vus, commandes détectées) |
| `/ds_selftest` | (optionnel) Teste le déchiffrement et la lecture du titre |
| `/ds_titles` | Diagnostic des langues : liste les titres de points de contrôle lus en mémoire et dit s'ils sont reconnus comme « terminée » |
| `/ds_catchup` | (optionnel) Traite aussi les checkpoints déjà présents (avec prudence) |

</details>

## Dépannage

| Symptôme | Que faire |
|---|---|
| « Le lieu … n'existe pas dans la partie hébergée » | Régénérez la partie avec la dernière version de l'APWorld |
| `/ds_status` n'affiche rien | Le jeu doit être lancé et la sauvegarde chargée. Les offsets peuvent changer après une mise à jour du jeu (voir `memory_map.default.json`) |
| Une commande principale terminée n'est pas détectée | Attendez la ligne « lecture en mémoire active » au démarrage ; le check part dans les secondes qui suivent la sauvegarde du jeu. Seules les commandes terminées après le démarrage du client comptent. En dernier recours, configurez le déchiffrement des sauvegardes (voir plus haut) |
| « aucun titre de sauvegarde en mémoire pour l'instant » | Normal tant que le jeu n'a pas écrit de point de contrôle ; le client réessaie (toutes les 1 à 10 minutes au repos, en continu pendant 6 minutes après chaque livraison) |
| Les compteurs de commandes (standard, bot) restent muets | Le client cherche la table en mémoire dès l'entrée en jeu (jusqu'à quelques minutes, réessais espacés) après un redémarrage du jeu ou un changement de sauvegarde. Attends la fin du chargement, puis `/ds_counters scan` relance la recherche immédiatement ; `/ds_bot` indique l'état. Si « table introuvable » persiste, `/ds_counters partial` décrit ce qui a été vu : envoie la console avec une issue |
| « Compteur « total » absent de la table… » / `/ds_bot` : indisponibles | Normal sur certaines sauvegardes : le jeu ne crée ce compteur que plus tard. Seuls les paliers de bot sont concernés (voir « Commandes de bot ») |
| Un effet ou piège ne s'applique pas | Il attend que Sam soit lisible (pas pendant un chargement ou un menu). Testez avec `/ds_debug on` puis `/ds_effect <nom>` |

## Limites connues

- Les objets « Episode N Access » **ne verrouillent rien en jeu** : ils n'existent que dans la logique de génération. Le joueur peut jouer l'histoire dans l'ordre sans les avoir
  reçus, et les checks partent dès que la commande est terminée. Avec l'option `episode_gating`, le client **retient l'envoi** des checks de commandes principales : une commande de l'épisode N n'est envoyée qu'une fois les objets « Episode 1 Access » à « Episode N Access » reçus (même règle que la génération). La commande se termine normalement dans le jeu et son check part dès que l'objet arrive ; les checks retenus survivent à un redémarrage du client (`/ds_held` les liste). Les checks de likes, de progression, de commandes standard et de bot ne sont jamais retenus, et `/check <lieu>` envoie un check sans tenir compte de la retenue. Le jeu lui-même n'est pas verrouillé ;
  bloquer l'accès aux épisodes en jeu n'est pas possible pour l'instant.
- Les 70 commandes principales (n°1 à 70) sont des checks. Liste d'après le wiki Fandom et Neoseeker. 19 sont optionnelles (marquées « Story : No » sur Fandom, plus la n°66) : n°6, 10-13, 15, 17, 25, 26, 29, 31, 35, 37, 40, 42, 45, 56, 57, 66
  (tutoriels de construction, livraisons de pizza « Fresh Pizza Delivery: Peter Englert »…). Ce sont des checks, mais la génération n'y place jamais d'objet de progression. Les tutoriels n°6, 10 et 15 et la pizza n°26 sont validés en jeu (clé de fin de commande) ; la n°1 est vue par le titre ou la déduction ; les tutoriels n°25 et 29 et les pizzas n°40, 45, 57 et 66 ne sont pas encore vérifiés en jeu : si l'une n'est pas détectée, `/check <nom exact du lieu>`. Quand le client voit se terminer une commande
  de numéro inférieur à 100 qui n'est pas dans la liste, il l'indique une fois dans le journal : merci de la signaler avec son nom et son épisode.
- La victoire (dernière commande de l'épisode but : n°70, ou n°68 avec l'objectif épisode 12) est validée en jeu pour la n°70 (objectif épisode 14), 30 s à 1 min après la sauvegarde qui suit le générique, et pour la n°68 (objectif épisode 12), reconnue par ses clés marqueurs dès le début de la cinématique de fin de livraison. Avec `episode_gating`, la victoire attend les objets « Episode 1 Access » à « Episode N Access ». Si la victoire ne part pas, `/check <nom du lieu>` envoie le check à la main.
- Une commande principale peut ne pas être identifiée si le jeu n'a pas écrit de point de contrôle avant la suivante et si elle n'a pas de clé marqueur connue (c'est le cas des commandes de la dernière ligne du tableau de couverture). Le client le signale alors (« fin de commande non identifiée ») avec la commande probable et la commande `/check` à taper.
- Une commande principale terminée pendant que le client n'était pas lancé n'est pas rattrapée (la mémoire ne garde que le dernier point de contrôle), sauf avec le déchiffrement optionnel et `/ds_catchup`. Exceptions : les commandes dont la clé de fin est connue (tableau de couverture) et celles que la déduction par les titres prouve. `/check <nom du lieu>` permet de l'envoyer à la main.
- Le titre de sauvegarde ne garde que la dernière commande : une commande terminée puis suivie d'une autre avant l'enregistrement n'y apparaît jamais. Le client **déduit** alors sa fin quand le titre montre une commande d'un épisode plus avancé (n'importe quel état, même « en cours ») : toutes les commandes « Story : Yes » des épisodes précédents sont considérées terminées, ainsi que, dans les épisodes strictement séquentiels (n°2→3, 54→55, 63→64→65), les précédentes de la chaîne. Les commandes optionnelles ne sont jamais déduites. Par prudence, rien n'est déduit si l'épisode du titre dépasse de plus d'un celui de ta commande la plus avancée connue (autre sauvegarde, client lancé en cours de partie) : utilise alors `/check`. Le journal indique « Commande terminee deduite ».
- Pour les objets reçus : seuls les cristaux chiraux, les matériaux, les pièges et les effets ponctuels listés ci-dessus agissent en jeu. Les autres équipements
  (Cargo Skeleton, véhicules, ancrages, échelles, armes, grenades…) sont reçus mais **n'ont pas d'effet pour l'instant**. Les effets ne modifient jamais durablement l'équilibre du jeu.
- Les offsets mémoire proviennent d'une table de triche communautaire (seules les adresses sont reprises, pas le fichier) et de relevés personnels.
  Ils peuvent casser à chaque mise à jour du jeu.
- Le détail des recherches sur les compteurs de commandes est dans [`death_stranding_research/RECHERCHE_compteurs_commandes.md`](https://github.com/R0shinante/Archipelago/blob/death-stranding/death_stranding_research/RECHERCHE_compteurs_commandes.md) (sur la branche du dépôt, hors de l'APWorld).

## Tests

```
SKIP_REQUIREMENTS_UPDATE=1 python tests/test_memory.py
SKIP_REQUIREMENTS_UPDATE=1 python tests/test_savewatch.py
```

(Dans le dépôt autonome ; ces tests ne sont pas inclus dans la branche du fork.)

## Licence

MIT. Death Stranding est une marque de Kojima Productions. Ce projet n'est ni approuvé ni affilié.
