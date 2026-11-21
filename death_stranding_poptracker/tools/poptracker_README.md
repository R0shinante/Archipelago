# Death Stranding — Archipelago PopTracker pack

Pack [PopTracker](https://github.com/black-sliver/PopTracker/releases) pour le monde **Death Stranding** d'Archipelago. / PopTracker pack for the Archipelago **Death Stranding** world.

## Installation (FR)

1. Installe PopTracker, puis place ce dossier (ou le `.zip`, sans le décompresser) dans son dossier `packs/` (par ex. `Documents\PopTracker\packs`).
2. Lance PopTracker → *Open Pack* → « Death Stranding (Archipelago) ».
3. Autotracking : clique sur le « AP » gris en haut, saisis l'adresse du serveur, **le nom de ton slot** et le mot de passe éventuel. Les objets reçus et les commandes cochées se mettent à jour tout seuls.

## Install (EN)

1. Install PopTracker and drop this folder (or the `.zip`, unextracted) into its `packs/` folder.
2. Start PopTracker → *Open Pack* → "Death Stranding (Archipelago)".
3. Autotracking: click the grey "AP" at the top, enter the server address, **your slot name** and the password if any.

## Ce que le pack affiche / What it shows

- **Carte « Orders »** : les 70 commandes principales rangées par épisode (+ une case Victoire). Vert = accessible d'après la logique de génération, rouge = pas encore (il manque un objet « Episode N Access »), case grisée/cochée = check envoyé. Les numéros suivis d'une `*` sont des commandes **optionnelles** (jamais d'objet de progression dessus). Clic droit = marquer comme fait à la main (la case devient sombre) ; l'autotracking le fait tout seul. Pour **défaire** une case cochée par erreur : bouton **SYNC** (section Progress), qui remet toutes les cases dans l'état du serveur (hors connexion : tout décoché). Les commandes épinglées s'affichent dans le panneau sous la carte.
- **Accès d'épisode** (14), **équipement**, **matériaux/fournitures** et **pièges** : s'allument ou se comptent à la réception.
- **Progress** : objectif (épisode 14 ou 12, lu dans le slot), **mode libre** (à activer à la main : affiche tout en accessible, utile quand l'option *Retenir les checks selon les accès d'épisode* est désactivée, car le jeu n'est jamais verrouillé), et les compteurs « cochés / total » des commandes principales et des paliers (likes, progression, standard, bot) selon les options du slot.
- Les checks de paliers (likes, progression des commandes, commandes standard, bots) sont comptés par les compteurs ; ils n'ont pas de case sur la carte car ils sont toujours accessibles.

## Limites connues / Known limits

- Le pack reflète les checks **reçus par le serveur**. Avec l'option *Retenir les checks selon les accès d'épisode*, une commande déjà faite en jeu mais retenue reste rouge (non cochée) jusqu'à l'arrivée de l'objet « Episode N Access » ; `/ds_held` dans le client liste ces commandes. (Validé le 21/11 : à la connexion 3/70 cochées, 12/70 après réception des épisodes 2 à 7.)
- La case Victoire n'est pas autotrackée (l'événement de victoire n'a pas d'identifiant de lieu) ; elle indique seulement si l'objectif est atteignable.
- Le pack suit la **logique de génération** (accès d'épisode) ; si l'option de retenue est désactivée, active le « mode libre ».
- Pack testé en simulation puis en réel le 21/11 (connexion AP, objets, compteurs, cases cochées, bouton « Tout accessible » ; une reconnexion sans fermer PopTracker restitue le même état, car le serveur renvoie les mêmes objets et checks).

## Régénération / Regeneration

Tout est produit par `tools/make_poptracker.py` à partir des données du monde (`PYTHONPATH=<Archipelago> python3 tools/make_poptracker.py`). Ne modifie pas `scripts/mapping.lua` à la main.
