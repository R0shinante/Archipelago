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

Les **51 commandes principales** sont des checks. Les épisodes sont verrouillés derrière des objets « Episode N Access ». Les autres
objets du multimonde (cristaux, matériaux, équipement, pièges) sont appliqués en jeu par le client, qui accède à la mémoire du jeu.

| Fonction | État |
|---|---|
| Checks : commandes principales (51), détectées automatiquement | ✅ |
| Objets « Episode N Access » (déblocage des épisodes) | ✅ |
| Cristaux chiraux appliqués en jeu | ✅ |
| DeathLink (envoi et réception de la mort du joueur) | ✅ validé en jeu |
| Paliers de likes comme checks (`likes_checks` / `likes_step`, jusqu'à 50) | ✅ validé en jeu |
| Paliers de progression des commandes comme checks (`order_checks` / `order_step`, jusqu'à 100, sans sauvegarde) | 🔧 en cours : compte les étapes de commande, pas encore les totaux par type |
| Paliers de commandes standard livrées comme checks (`standard_checks` / `standard_step`, jusqu'à 100, sans sauvegarde) | 🧪 à valider en jeu : compteur exact du jeu (clé 17 de la table de statistiques) |
| Effets ponctuels : Blood Bag, Energy Drink, Repair Spray, Boot Upgrade, Power Skeleton, Speed Skeleton, Cryptobiote Pack, D-Cryptobiote Pack, Sandalweed Bundle | ✅ validé en jeu |
| Objet « Likes Pack » (+500 likes) | 🧪 à valider en jeu |
| Matériaux (résines, métaux, céramiques, chimiques, alliages) crédités au stock d'une installation | 🧪 à valider en jeu |
| Pièges : Injury, Fatigue, Boot Wear, Rust, Pickpocket | 🧪 à valider en jeu |
| Checks nominatifs par commande standard / optionnelle ; paliers en direct pour les commandes principales ou de bot seules | ❌ : aucun compteur lisible en direct n'a été trouvé (voir `docs/RECHERCHE_compteurs_commandes.md`) |

Les checks sont identifiés par `7 770 000 + numéro de commande`. Le client détecte une commande principale terminée grâce au **titre des
sauvegardes de checkpoint** (« Commande terminée : nº N … »), qu'il déchiffre avec un outil tiers.

## Installation

### Ce qu'il vous faut

| Élément | Détail |
|---|---|
| Système | **Windows**, avec Death Stranding Director's Cut (Steam), en français par défaut (voir [Autres langues](#autres-langues)) |
| Archipelago | **0.6.x**, de préférence **depuis les sources** (<https://github.com/ArchipelagoMW/Archipelago>) |
| Python | **3.12 ou 3.13** si vous utilisez les sources (3.10 et 3.11 ne conviennent pas) |
| pymem | Bibliothèque Python qui permet au client d'accéder à la mémoire du jeu |
| Outil de déchiffrement | [DeathStrandingSaveDataResigner](https://github.com/mi5hmash/DeathStrandingSaveDataResigner), version en ligne de commande (`death-stranding-savedata-resigner-cli.exe`, onglet *Releases*). Projet tiers, non inclus ici. Le client ne travaille que sur une **copie temporaire** de vos checkpoints : vos sauvegardes ne sont jamais modifiées. |

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

### Étape 3 — Préparer l'outil de déchiffrement

1. Téléchargez et décompressez l'outil, par exemple dans `C:\Games`.
2. Notez le chemin complet de l'exécutable : vous le donnerez au client à l'étape « Lancer une partie ».

## Configuration (YAML)

1. Dans le Launcher d'Archipelago, cliquez sur **Generate Template Options**.
2. Ouvrez `Death Stranding.yaml`, vérifiez `game: Death Stranding` et renseignez votre `name:`.
3. Réglez les options ci-dessous, puis placez le fichier dans le dossier `Players`.

| Option | Valeurs | Défaut | Rôle |
|---|---|---|---|
| `goal` | `finish_episode_14`, `finish_episode_12` | `finish_episode_14` | Condition de victoire |
| `trap_percentage` | 0 à 100 | 15 | Part du remplissage transformée en pièges |
| `starting_episodes` | 0 à 5 | 0 | Épisodes débloqués au départ en plus de l'épisode 1 |
| `death_link` | vrai / faux | faux | DeathLink (voir ci-dessous) |
| `likes_checks` | 0 à 50 | 0 | Nombre de checks de likes (0 = désactivé) |
| `likes_step` | 100 à 10000 | 1000 | Likes à gagner par palier |
| `order_checks` | 0 à 100 | 0 | Nombre de checks de progression des commandes (0 = désactivé) |
| `order_step` | 1 à 50 | 3 | Étapes de commande par palier |
| `standard_checks` | 0 à 100 | 0 | Nombre de checks de commandes standard livrées (0 = désactivé) |
| `standard_step` | 1 à 50 | 3 | Commandes standard à livrer par palier |

**Likes.** Le check « Likes Milestone N » se débloque quand vous gagnez N × `likes_step` likes **depuis la première connexion** (la base est fixée à ce moment-là).
Les likes reçus par des objets « Likes Pack » ne comptent pas. `/ds_likes` affiche la progression.

**Progression des commandes.** Le check « Order Progress N » se débloque quand le compteur d'étapes de commande gagne N × `order_step` **depuis la première connexion**.
Ce compteur monte à chaque étape d'objectif accomplie : livraison de commande standard, commande de bot, acceptation et objectifs intermédiaires d'une commande principale.
Il mesure des étapes, tous types confondus, et ne compte pas les livraisons de marchandise perdue. Il fonctionne en direct, sans sauvegarde, client connecté.
`/ds_orders` affiche la progression, `/ds_orders_rebase` refixe la base.

**Commandes standard.** Le check « Standard Orders N » se débloque quand vous avez livré N × `standard_step` commandes standard **depuis la première connexion**. C'est le compteur exact du jeu, lu en direct, sans sauvegarde : les commandes principales, les commandes de bot et les marchandises perdues ne comptent pas. `/ds_standard` affiche la progression, `/ds_standard_rebase` refixe la base.

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
3. **Vérifiez l'accès à la mémoire :** `/ds_status` doit afficher vos quantités de cristaux chiraux. Test d'écriture : `/ds_give Chiral Crystals 10`.
4. **Configurez la détection des sauvegardes** (une seule fois) :
   ```
   /ds_resigner C:\Games\death-stranding-savedata-resigner-cli.exe
   ```
   Si le dossier des sauvegardes n'est pas trouvé automatiquement :
   ```
   /ds_saves_dir C:\Users\<vous>\AppData\Local\KojimaProductions\DeathStrandingDC\<identifiant Steam>
   ```
   C'est le dossier qui contient les sous-dossiers `quicksave…` et `checkpoint…`, chacun avec un `checkpoint.dat`.
5. **Vérifiez toute la chaîne :** `/ds_selftest` déchiffre le dernier checkpoint et affiche son titre, par exemple `Commande terminée : nº 61 « … »`.
6. **Jouez.** Terminez une commande principale : le jeu écrit un checkpoint, le client lit le titre, envoie le check et le serveur distribue les objets.
   Les objets reçus s'affichent dans la console du client. Seules les commandes terminées **après** le démarrage du client comptent ; `/ds_catchup` traite aussi
   les checkpoints déjà présents (avec prudence).

### Autres langues

Le titre des sauvegardes dépend de la langue du jeu. Si votre jeu n'est pas en français, ajustez `saves.completed_words` dans `memory_map.json`
(mots signifiant « terminée »). Pour modifier les offsets, copiez `memory_map.default.json` en `memory_map.json` dans le dossier utilisateur d'Archipelago.

## Commandes du client

<details>
<summary>Afficher la liste</summary>

| Commande | Rôle |
|---|---|
| `/locations` | Liste les lieux (commandes) du monde |
| `/check <nom>` | Envoie un check manuellement |
| `/ds_status` | Quantités lues en mémoire |
| `/ds_give <ressource> <quantité>` | Test d'écriture en mémoire (sac à dos) |
| `/ds_effect [nom]` | Test d'un piège ou d'un effet d'objet (sans nom : liste) ; `/ds_trap` est un alias |
| `/ds_likes` | Likes lus en mémoire (PNJ / joueurs / total) |
| `/ds_likes_give <npc\|players> <n>` | Test d'écriture d'un compteur de likes |
| `/ds_likes_rebase` | Refixe la base des paliers de likes |
| `/ds_orders` | Compteur d'étapes de commande et progression des paliers |
| `/ds_orders_rebase` | Refixe la base des paliers de progression des commandes |
| `/ds_standard` | Commandes standard livrées (compteur du jeu) et progression des paliers |
| `/ds_standard_rebase` | Refixe la base des paliers de commandes standard |
| `/ds_hp` | Vie du joueur lue en mémoire (test) |
| `/ds_kill` | Test : met la vie de Sam à 0 |
| `/ds_items` | Objets reçus / appliqués en jeu (diagnostic) |
| `/ds_items_reset <n>` | Recale l'index des objets appliqués |
| `/ds_stock [installation]` | Stocks de matériaux d'une installation |
| `/ds_stock_mode random\|target` | Répartition des matériaux : installation au hasard (défaut) ou choisie |
| `/ds_stock_pool Nom1; Nom2` | Limite le tirage au hasard à certaines installations (`all` = toutes) |
| `/ds_stock_target <installation>` | Installation créditée en mode `target` |
| `/ds_stock_give <matériau> <quantité>` | Test d'écriture d'un stock |
| `/ds_resigner <exe>` | Chemin de l'outil de déchiffrement |
| `/ds_saves_dir <dossier>` | Dossier des sauvegardes |
| `/ds_saves` | État de la surveillance (checkpoints vus, commandes détectées) |
| `/ds_selftest` | Teste le déchiffrement et la lecture du titre |
| `/ds_catchup` | Traite aussi les checkpoints déjà présents (avec prudence) |

</details>

## Dépannage

| Symptôme | Que faire |
|---|---|
| « Le lieu … n'existe pas dans la partie hébergée » | Régénérez la partie avec la dernière version de l'APWorld |
| `/ds_status` n'affiche rien | Le jeu doit être lancé et la sauvegarde chargée. Les offsets peuvent changer après une mise à jour du jeu (voir `memory_map.default.json`) |
| « Fichier introuvable » avec `/ds_resigner` | Vérifiez le chemin complet jusqu'au `.exe` (les antislashs sont acceptés tels quels) |
| Code retour étrange du déchiffrement (ex. `3762504530`) | L'outil plante à sa sortie : sans conséquence tant que `/ds_selftest` affiche un titre |
| Rien n'est détecté | Lancez `/ds_selftest`, puis `/ds_saves`. Seules les modifications faites après le démarrage du client comptent |
| Un effet ou piège ne s'applique pas | Il attend que Sam soit lisible (pas pendant un chargement ou un menu). Testez avec `/ds_effect <nom>` |

## Limites connues

- Seules les 51 commandes principales de la liste sont des checks. La liste vient de guides communautaires et peut contenir des erreurs (n°17 absente, n°66 au nom approximatif).
- Pour les objets reçus : seuls les cristaux chiraux, les matériaux, les pièges et les effets ponctuels listés ci-dessus agissent en jeu. Les autres équipements
  (Cargo Skeleton, véhicules, ancrages, échelles, armes, grenades…) sont reçus mais **n'ont pas d'effet pour l'instant**. Les effets ne modifient jamais durablement l'équilibre du jeu.
- Les offsets mémoire proviennent d'une table de triche communautaire (seules les adresses sont reprises, pas le fichier) et de relevés personnels.
  Ils peuvent casser à chaque mise à jour du jeu.
- Le détail des recherches sur les compteurs de commandes est dans [`docs/RECHERCHE_compteurs_commandes.md`](docs/RECHERCHE_compteurs_commandes.md).

## Tests

```
SKIP_REQUIREMENTS_UPDATE=1 python tests/test_memory.py
SKIP_REQUIREMENTS_UPDATE=1 python tests/test_savewatch.py
```

(Dans le dépôt autonome ; ces tests ne sont pas inclus dans la branche du fork.)

## Licence

MIT. Death Stranding est une marque de Kojima Productions. Ce projet n'est ni approuvé ni affilié.
