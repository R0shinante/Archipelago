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
Chemicals / Special Alloys reçus sont donc crédités au stock d'**une installation** (par défaut : Capitol Knot City).
- `/ds_stock` affiche les 6 valeurs de cette installation (`/ds_stock Port Knot City` pour une autre) ; ouvrez d'abord le menu de
  l'installation en jeu pour comparer.
- `/ds_stock_target <installation>` change l'installation créditée (enregistré), `/ds_stock_give Metals 50` teste l'écriture.
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
- Les pièges, DeathLink et les autres ressources ne sont pas encore branchés.
