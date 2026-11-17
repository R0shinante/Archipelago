<!-- death-stranding-fork -->
> ## Death Stranding (Director's Cut, PC) : fork experimental
> Cette branche ajoute un monde **Death Stranding** pour Archipelago : [**README (francais)**](worlds/death_stranding/README.md) | [**README (English)**](worlds/death_stranding/README.en.md).
> This branch adds a **Death Stranding** world for Archipelago: see the [English README](worlds/death_stranding/README.en.md) or the [French README](worlds/death_stranding/README.md).
> Projet non officiel, alpha : a utiliser hors ligne, en solo, sur une sauvegarde dediee. / Unofficial alpha: offline, solo, dedicated save only.
# Death Stranding (Director's Cut, PC/Steam) — APWorld Archipelago

Monde et client [Archipelago](https://archipelago.gg) expérimentaux pour **Death Stranding Director's Cut** (PC, Steam).
Projet non officiel, sans lien avec Kojima Productions, 505 Games ni l'équipe d'Archipelago.

> ⚠️ **Alpha.** À utiliser **hors ligne**, en **solo**, sur une **sauvegarde dédiée aux tests**.
> Le client lit et écrit la mémoire du jeu : ne l'utilisez jamais en ligne et faites une copie de vos sauvegardes avant de commencer.

## Fonctionnalités

| | État |
|---|---|
| Checks : commandes principales (51), détectées automatiquement | ✅ |
| Objets « Episode N Access » (déblocage des épisodes) | ✅ |
| Cristaux chiraux appliqués en jeu | ✅ |
| Autres ressources (métaux, céramiques…) | ❌ |
| Pièges, DeathLink (mort du joueur) | ❌ |
| Commandes standard / optionnelles comme checks | ❌ |

Les checks sont identifiés par `7 770 000 + numéro de commande`. Le client détecte une commande terminée grâce au **titre des
sauvegardes de checkpoint** (« Commande terminée : nº N … »), qu'il déchiffre avec un outil tiers.

## Prérequis

- **Windows** et Death Stranding Director's Cut (Steam), en français par défaut (voir « Autres langues »)
- **Archipelago 0.6.x**, lancé depuis les sources ou l'installateur officiel (<https://github.com/ArchipelagoMW/Archipelago/releases>)
- **Python 3.12 ou 3.13** si vous lancez Archipelago depuis les sources (Python 3.10 et 3.11 ne conviennent pas)
- **pymem**, pour que le client accède à la mémoire du jeu
- **DeathStrandingSaveDataResigner** (version en ligne de commande), pour déchiffrer les sauvegardes :
  <https://github.com/mi5hmash/DeathStrandingSaveDataResigner> (onglet *Releases*, fichier
  `death-stranding-savedata-resigner-cli`). Cet outil est un projet tiers, il n'est pas inclus ici.
  Le client ne travaille que sur une **copie temporaire** de vos checkpoints : vos sauvegardes ne sont jamais modifiées.

## Installation pas à pas

### 1. Installer l'APWorld
- **Depuis une release :** téléchargez `death_stranding.apworld` et placez-le dans le dossier `custom_worlds` d'Archipelago.
- **Depuis ce dépôt :** copiez le dossier `worlds/death_stranding` dans le dossier `worlds` d'Archipelago (installation depuis les sources).

Évitez d'avoir les deux à la fois, sinon le monde est chargé deux fois.

### 2. Installer pymem
Dans une invite de commandes (adaptez `-3.12` à votre version de Python) :

```
py -3.12 -m pip install pymem
```

Si vous utilisez l'installateur officiel d'Archipelago, installez `pymem` dans le Python qui lance le client
(les sources d'Archipelago sont recommandées pour ce monde).

### 3. Préparer le YAML
1. Dans le Launcher d'Archipelago, cliquez sur **Generate Template Options**.
2. Ouvrez `Death Stranding.yaml`, vérifiez `game: Death Stranding` et renseignez votre `name:`.
3. Placez-le dans le dossier `Players`.

Options : objectif (`finish_episode_14` ou `finish_episode_12`), pourcentage de pièges, épisodes de départ, DeathLink.

### 4. Générer et héberger la partie
1. Launcher → **Generate**. Le fichier `AP_xxxxxxxx.zip` apparaît dans `output`.
2. Launcher → **Host**, puis choisissez ce zip. Notez l'adresse (par défaut `localhost:38281`).

> **À refaire à chaque nouvelle version de l'APWorld :** une partie générée avec une version plus ancienne peut contenir
> des lieux inconnus du serveur. Le client l'indique par un avertissement « Le lieu … n'existe pas dans la partie hébergée ».

### 5. Premier lancement du client
1. Lancez Death Stranding **hors ligne**, chargez votre sauvegarde dédiée.
2. Dans le Launcher d'Archipelago, ouvrez **Death Stranding Client** et connectez-vous : `/connect localhost:38281`.
3. Vérifiez l'accès à la mémoire : `/ds_status` doit afficher vos quantités de cristaux chiraux.
   Test d'écriture : `/ds_give Chiral Crystals 10`.

### 6. Configurer la détection des sauvegardes
1. Téléchargez et décompressez l'outil de déchiffrement, par exemple dans `C:\Games`.
2. Indiquez son emplacement au client (une seule fois) :
   ```
   /ds_resigner C:\Games\death-stranding-savedata-resigner-cli.exe
   ```
3. Si le dossier des sauvegardes n'est pas trouvé automatiquement :
   ```
   /ds_saves_dir C:\Users\<vous>\AppData\Local\KojimaProductions\DeathStrandingDC\<identifiant Steam>
   ```
   C'est le dossier qui contient les sous-dossiers `quicksave…`, `checkpoint…`, chacun avec un `checkpoint.dat`.
4. Vérifiez toute la chaîne : `/ds_selftest` déchiffre le dernier checkpoint et affiche son titre, par exemple
   `Commande terminée : nº 61 « … »`.

### 7. Jouer
Terminez une commande principale : le jeu écrit un checkpoint, le client lit le titre, envoie le check, et le serveur
distribue les objets. Les objets reçus s'affichent dans la console du client.

## Commandes du client

| Commande | Rôle |
|---|---|
| `/locations` | Liste les lieux (commandes) du monde |
| `/check <nom>` | Envoie un check manuellement |
| `/ds_status` | Quantités lues en mémoire |
| `/ds_give <ressource> <quantité>` | Test d'écriture en mémoire |
| `/ds_resigner <exe>` | Chemin de l'outil de déchiffrement |
| `/ds_saves_dir <dossier>` | Dossier des sauvegardes |
| `/ds_saves` | État de la surveillance (checkpoints vus, commandes détectées) |
| `/ds_selftest` | Teste le déchiffrement et la lecture du titre |
| `/ds_catchup` | Traite aussi les checkpoints déjà présents (avec prudence) |

## Dépannage

- **« Le lieu … n'existe pas dans la partie hébergée »** : régénérez la partie avec la dernière version de l'APWorld.
- **`/ds_status` n'affiche rien :** le jeu doit être lancé et la sauvegarde chargée. Les offsets peuvent changer après une mise à jour
  du jeu : ils sont dans `memory_map.default.json` (copiez-le en `memory_map.json` dans le dossier utilisateur d'Archipelago pour les modifier).
- **« Fichier introuvable » avec `/ds_resigner` :** vérifiez le chemin complet jusqu'au `.exe`. Les antislashs sont acceptés tels quels.
- **Code retour étrange du déchiffrement** (par exemple `3762504530`) : l'outil plante à sa sortie, c'est sans conséquence tant que
  `/ds_selftest` affiche un titre.
- **Rien n'est détecté :** lancez `/ds_selftest`, puis `/ds_saves`. Les modifications ne comptent qu'après le démarrage du client.

## Autres langues

Le titre des sauvegardes dépend de la langue du jeu. Si votre jeu n'est pas en français, ajustez `saves.completed_words` dans
`memory_map.json` (mots signifiant « terminée »). Les titres de commandes sont lus dans la langue du jeu, seul le numéro compte.

## Limites connues

- Seules les 51 commandes principales de la liste sont des checks. La liste vient de guides communautaires et peut contenir des erreurs
  (n°17 absente, n°66 au nom approximatif).
- Les objets reçus n'ont d'effet en jeu que pour les cristaux chiraux (+100) ; les autres sont seulement affichés.
- Les offsets mémoire proviennent d'une table de triche communautaire (seules les adresses sont reprises, pas le fichier) et de relevés personnels.
  Ils peuvent casser à chaque mise à jour du jeu.

## Tests

```
SKIP_REQUIREMENTS_UPDATE=1 python tests/test_memory.py
SKIP_REQUIREMENTS_UPDATE=1 python tests/test_savewatch.py
```

(Dans le dépôt autonome ; ces tests ne sont pas inclus dans la branche du fork.)

## Licence

MIT. Death Stranding est une marque de Kojima Productions. Ce projet n'est ni approuvé ni affilié.
