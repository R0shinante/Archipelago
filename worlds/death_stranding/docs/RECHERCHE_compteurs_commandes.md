# Recherche : compteurs de commandes en mémoire (Death Stranding Director's Cut)

Notes de recherche, destinées aux développeurs. Ce fichier n'est pas livré dans l'`.apworld`.
Tout ce qui suit a été observé sur Steam, hors ligne, sauvegarde de test. Les adresses d'objets (tas)
changent à chaque lancement du jeu ; seules les adresses relatives au module `ds.exe` sont stables.

## Objectif

Détecter en direct, sans lire les sauvegardes, la progression des commandes (principales, standard, bots)
et idéalement les totaux de l'onglet « Commandes » (Honoré, Sam, Standard, Bot, types).

## Résultat utile : le compteur d'étapes

- Racine statique : `[ds.exe+0x7BFA148]` (pointeur global vers un objet de tas).
- `+0x168` (int32) et `+0x114` (int32) augmentent de 1 à chaque étape. Ils survivent au rechargement d'une
  sauvegarde et au redémarrage du jeu. C'est la base de « Order Progress » (`order_progress` dans `memory_map.default.json`).
- Compte : livraison standard, commande de bot, acceptation et objectifs intermédiaires d'une commande principale,
  fin de commande principale.
- Ne compte pas : livraison de marchandise perdue.
- `+0x10C` / `+0x110` : copie de `+0x114` avec une étape de retard (pas un compteur indépendant).

## Ce que c'est vraiment

L'instruction qui écrit `+0x168` est `ds.exe+2E5B026` (`mov [rbx],ecx`), à l'intérieur d'une petite fonction
`push_back` sur un tableau d'entiers :

- `[rbx]` = taille (`+0x168`), `+0x16C` = capacité, `+0x170` = pointeur des données ;
- `call ds.exe+1941A80` assure la capacité et renvoie les données ; `[données + taille*4] = edi` ; taille++.

Ce tableau est la **liste des emplacements libres** d'un pool de 192 objets (pile `191, 190, … 64`, puis l'indice
libéré est poussé : 63, 59, 58, 57, 56…). Les objets sont dans le bloc pointé par `+0x150` de la racine, à raison de
336 octets (`0x150`) par emplacement. Un emplacement libre contient `-1` à `+0x14`. Un emplacement occupé contient un
numéro à `+0x14` (238, 242, 244, 246…), deux références à `+0x20` / `+0x24` dans la plage 201–239 et trois flottants à
`+0x130` à `+0x148` qui ressemblent à des coordonnées. Ce sont probablement des objets d'objectif / repères.

Conséquence : le compteur est **générique** (objets d'objectif libérés), il ne contient ni type de commande ni numéro.
La libération et la création suivante se font dans le même emplacement, donc on lit le contenu de l'objet suivant,
pas de celui qui vient de finir.

## Chaînes d'appelants observées (breakpoint sur `ds.exe+2E5B026`)

| Événement | Chaîne (du plus proche au plus lointain) |
|---|---|
| Livraison standard ; acceptation d'une commande principale | `2E8100E`, `2E80DF4`, `3415A2E`, `341AAB6`, `33C4023`, `2E10EA4`, `263E963`, `263C296`… |
| Étape validée d'une commande principale | `2E8100E`, `2E88135`, `2E82DDA`, `2E10AB3`, `263EA4A`, `263C296`… |
| Livraison / fin d'une commande principale | `2E881E8`, `2E82DDA`, `2E10AB3`, `263EA4A`, `263C296`… |

Les chemins diffèrent entre commandes principales et standard, mais le client (lecture mémoire seule) ne peut pas
observer quel chemin s'exécute. Poser un hook de code est hors périmètre (risque de plantage).

## Table de statistiques (découverte du 17/11) : compteur Standard exact

Trouvé par scans « All » dans Cheat Engine (valeur exacte à chaque étape, case Hex décochée), puis
« Find out what writes » (instruction `ds.exe+3413ECE`, `mov [rax+rcx*8+08],ebp`, `RCX` = clé, `RAX` = table, `RBX` = objet).

- Chemin stable (vérifié après redémarrage du jeu) : `[[ds.exe+0x7BE6318]+0xC88]` = table. Trois autres chemins
  mènent à la même table : `7BE6A30 -> +0xC88`, `57A26B8 -> +0x258`, `57A26C0 -> +0x58`.
- Format : 40 entrées de 16 octets `(clé int32, état int32, valeur int32, remplissage)` sur 0x280 octets.
  État `0x701` = clé enregistrée sans valeur ; `0x702` = valeur présente.
- Clés avec valeur observées (sauvegarde de test) : 17, 23, 38, 43, 48, 49, 50, 62.

| Clé | Livraison standard | Marchandise perdue | Livraison finale principale | Bot |
|---|---|---|---|---|
| **17** | +1 | 0 | 0 | 0 |
| 48 | +6 | +1 | +5 | 0 |
| 49 | +78 | +2 | +63 | 0 |
| 50 | +1 | 0 | +2 | 0 |
| 23 (=7), 38, 43, 62 | 0 | 0 | 0 | 0 |

- **Clé 17 = commandes standard livrées** (exact, en direct, sans ouvrir l'onglet). 48 ≈ colis livrés, 49 ≈ poids livré.
- Acceptation et étape intermédiaire d'une commande principale : aucun changement dans la table.
- La clé 23 valait 7 comme le total de bots, mais n'a pas bougé quand le total est passé à 8 : coïncidence.
- Onglet : Honoré = Sam + Standard + Bot + 1 sur toutes nos mesures (93 = 49+36+7+1, 94, 95). Honoré est donc une somme calculée.

## Totaux Sam et Bot : pas de valeur stockée (historique, voir « Table de compteurs nommés »)

- Sam (commandes principales, 49 → 52) : scans Cheat Engine « All » décimaux sur trois livraisons, 0 résultat.
- Bot (7 → 12) : scans sur cinq livraisons. À 12, il ne reste que 4 flottants qui dérivent (7,54 → 11,72, retenus par l'arrondi « extreme »), plus aucun entier : pas de compteur stocké. Avant cela, à 11, il restait ~85 adresses, dont ~70 dans un tableau d'objets de 0x12C0 octets
  (copies d'affichage). Les candidats isolés (`21E504FC75C`, `21E50F78A98`, `5126D1BBCA0`, `5129E18D780`) n'ont aucune
  racine statique (`/ds_chain` : « atteignable que par un pointeur temporaire »).
- `/ds_readscan` sur `[ds.exe+0x7BE6318]` (64 Ko) : seulement des faux positifs (zones de descripteurs et de hachages).
- Conclusion de l'époque : Sam et Bot ne sont pas stockés sous forme de valeurs. **Corrigée plus bas** : ils sont dérivés de compteurs nommés, Sam = `nobot − standard`, Bot = `total − nobot − repair` (à une constante près).

## Qui lit la table de statistiques ? (17/11, fin de session)

- « Find out what accesses » sur la valeur de la clé 17 : seules deux instructions apparaissent.
  - `ds.exe+3413ECE` (`mov [rax+rcx*8+08],ebp`) : l'écriture, à chaque livraison standard, et rien d'autre à la livraison.
  - `VCRUNTIME140._NLG_Return2+4FA` (`mov ecx,[rdx]` / `mov [rax],ecx` / `ret`, copie de 4 octets) : uniquement lors d'une **sauvegarde**
    (ouverture d'un terminal de livraison qui déclenche une sauvegarde automatique). La destination est un tableau d'enregistrements de
    0x34 octets (clé, 1, …, valeur) : c'est le tampon de sérialisation de la sauvegarde.
- Ouvrir l'onglet Commandes ne déclenche aucun accès à la table (point d'arrêt de données « Break on access » sans effet).
- Donc l'onglet affiche une valeur copiée ailleurs ou calculée ; aucun scan de texte UTF-16 (« 37 ») n'a trouvé de copie.

## Pistes écartées

- Totaux de l'onglet (Honoré/Sam/Standard/Bot/types) comme entiers en mémoire : introuvables par valeur exacte
  (int16/32/64), par pointeurs globaux à un saut, par scan du module, par clusters sur tout le processus
  (bruit : compteurs de références et tables d'index séquentielles), ni par différence de pages (~10,9 Go, ~75 s
  par instantané).
- Objet `[ds.exe+0x7AE80B0]` : cache d'interface avec des constantes (51, 7, 109, 89, 26, 30) et des valeurs
  (49/35/12/12) constantes d'une sauvegarde à l'autre : ce ne sont pas des compteurs.
- Champs de l'objet racine `+0x198=51`, `+0x178=45`, `+0xA0=95`, `+0xB0=5`, `+0x10C=212` : constantes, sans lien avec l'onglet.
- Bloc `+0x180` (`0x453148F4200`) : table d'enregistrements `(A, B, drapeau, n)` statique (ids 102–107, 201–239,
  500–590), inchangée par une livraison. Les tables `1..191` et `191..64` sont des tables d'index d'allocateur.
- Dernière commande terminée en clair (322 / 286) : aucun mot dans les pages modifiées par une livraison.

## Détection par la sauvegarde (historique ; le client lit désormais le titre directement en mémoire)

Le client lit l'en-tête des sauvegardes (voir `savewatch.py`). La mention « Commande n°X terminée » apparaît au
moment de la sauvegarde (ouverture du terminal avant livraison), et nomme la commande **précédemment** terminée.

## Table de compteurs nommés (trouvée en décompressant les sauvegardes)

Les sauvegardes ne sont pas indéchiffrables : la section 3 d'un checkpoint (après l'en-tête de 8 octets et l'identifiant Steam préfixé par sa longueur)
est un flux **Oodle Kraken** découpé en blocs de 256 Ko. La décompression donne un tampon d'environ 12 Mio (48 blocs ; 47 pour certaines sauvegardes,
avec 6 octets de fin à ignorer) qui contient l'état du jeu en clair. Outil : `tools/save_counters.py` (nécessite `pip install pyooz`).

Dans ce tampon, une table de ~250 compteurs nommés : enregistrements de 20 octets (clé de 16 octets, valeur int32). En comparant des sauvegardes
avant/après une livraison de chaque type :

| Événement | clé `02738f31…` (« nobot ») | clé `27c0565a…` (« total ») |
|---|---|---|
| Livraison standard | +1 | +1 |
| Livraison de bot | inchangé | +1 |
| Commande principale | +1 | +1 |

D'où : `bot = total - nobot` et `main = nobot - standard` (compteur standard exact, clé 17). Les valeurs absolues portent une constante inconnue ; seuls les écarts comptent.

**En mémoire**, cette table est une table de hachage ouverte de 512 cases de 24 octets : `hash u32 | clé 16 octets | valeur int32`, case = `hash & 0x1FF`
(hash de `nobot` : `0xC1BA5649`, de `total` : `0xE5344AB7`). Des cases « anciennes » avec la même clé et un hash à 0 contiennent des valeurs périmées : il faut exiger
la clé **et** le hash. Chaîne statique vérifiée : `[[[[ds.exe+0x7BFCFC0]+0xFB8]+0xDD0]+0x0]` = base de la table (autres chaînes : `0x7C18670 -> 0x1BB8 -> 0xDD0 -> 0x0`,
`0x7C19940 -> 0x4F8 -> 0xDD0 -> 0x0`). L'écriture se fait en `ds.exe+1B06C59` (`mov [rax+rcx*8+14],edx`, RAX = base, RCX = 3 × case).

Méthode qui a marché : décompression des sauvegardes comme oracle → recherche des clés de 16 octets en mémoire (octets, Cheat Engine) → « Find out what writes »
sur la valeur → `/ds_chain` sur la base de la table. Les scans de texte (ASCII/UTF-16) et de valeurs numériques n'avaient rien donné.

Limites : marchandises perdues et demandes d'équipement non testées ; les trois compteurs sont écrits séparément (le client exige deux lectures identiques).

## Reprise éventuelle

### Piste ouverte : le reste de la table de compteurs nommés

La table contient ~250 compteurs, dont le client n'en utilise que trois (`nobot`, `total`, `repair`). Les autres n'ont jamais été comparés en direct : seules deux paires de sauvegardes (avant / après une livraison de chaque type, avant / après la 62) l'ont été, et la plupart des types de commandes principales (récupération, collecte, élimination, crémation, retrait…) n'ont pas été testés isolément. Si le jeu tient un compteur par catégorie (comme pour la réparation), on pourrait reconnaître la catégorie d'une commande principale sans le titre du point de contrôle, donc sans être gêné par un bot actif.

Outil prévu pour l'explorer sans Cheat Engine ni déchiffrement : `/ds_counters snap` (photo de toute la table), faire l'événement à tester, attendre la sauvegarde (environ une minute), `/ds_counters diff` (clés qui ont changé, avec leur valeur avant / après) ; `/ds_counters save` écrit `DeathStranding_counters.json`. Protocole conseillé : une seule action par photo, et noter son type (ex. « commande 60, récupération »). Une clé qui monte de +1 à chaque commande d'une même catégorie et jamais autrement est candidate pour un nouveau compteur dans `memory_map.default.json`.

### Autres pistes non explorées

- Liste officielle des commandes (numéros, noms, épisodes) : les textes du jeu sont dans les archives `data/*.bin`, lisibles avec Decima Workshop (ShadelessFox, prend en charge Death Stranding et sa Director's Cut) ou Decima-Explorer (Jayveer). Elle permettrait de vérifier la liste actuelle (numéros absents, n°66) au lieu de se fier à une page communautaire.
- Retenir les checks côté client tant que l'objet « Episode N Access » n'est pas reçu (`location_to_episode` est déjà dans les données de partie) : ne bloque pas le jeu, mais rend la logique effective.
- Noms de commandes standard / optionnelles : leurs titres (n°345, 553…) sont lisibles en mémoire comme ceux des commandes principales.

Retrouver le nom de la commande livrée (identité) reste ouvert : les compteurs ci-dessus ne donnent que des totaux par type.

### La réparation (commande n°62) n'est pas une commande de bot

La commande 62 (« Réparation : relais chiral ») fait monter le compteur « total » (`27c0565a…`) sans faire monter « nobot » (`02738f31…`) : `total - nobot` la prenait pour une livraison de bot.

**Premier essai (abandonné) :** une paire de sauvegardes avant / après la 62 montrait `55a57fec…` à +1 ; en direct, ce compteur **ne bouge pas** (588 pendant au moins 5 minutes après la livraison). Les autres sauvegardes ont des valeurs très différentes (596, 597), il s'agit sans doute d'une statistique sans rapport.

**Piste retenue :** la clé `7f91306c7bdd4aa780f44df4068b3495` (valeur 1, et `f496b86a3afa3f29ad6f18bc97c8045c` à 0) **n'existe dans aucune des 9 sauvegardes d'avant la 62** et existe dans les 3 sauvegardes d'après ; elle apparaît aussi **en direct** dans la table en mémoire à la livraison (relevé `/ds_counters snap` / `diff`, 5 minutes après, avec une commande de bot active). Le client la lit comme compteur facultatif « repair » (absente = 0) : `bot = total - nobot - repair + 1000`, et la 62 est reconnue quand `repair` passe de 0 à 1 avec `total` en hausse et `nobot` inchangé.

Autres relevés utiles (paires de sauvegardes) :

| Événement | Compteurs qui changent |
|---|---|
| Livraison de bot | `total` +1, **rien d'autre** |
| Commande standard | `nobot` +1, `total` +1, `9ee48407…` |
| Commande principale 60 / 61 | `nobot` +1, `total` +1, plusieurs autres (`9ee48407…`, `34c1624b…`, `1f63d23f…`), quelques clés apparaissent / disparaissent avec une valeur 0 ou 1 |
| Commande 62 | `total` +1 (pas `nobot`), likes +1000 (`26adb4df…`), `9ee48407…` +11, `34c1624b…` +22, clés `7f91306c…` (=1) et `f496b86a…` (=0) créées |

**Validé en jeu (TEST #28, 62 livrée avec une commande de bot en cours) :** la clé `7f91306c…` apparaît **36 à 40 s après** la hausse de `total` (trois relevés : 40 s, 36 s, 38 s), car le jeu écrit ses compteurs en plusieurs temps. Le client mémorise donc l'instant de la hausse de `total` et celui de l'apparition de la clé, et reconnaît la 62 quand les deux tombent dans une fenêtre de 300 s (`repair_progress`, relevés bruts, sans exiger de valeur stable). La confirmation de palier de bot (45 relevés, environ 90 s) laisse une marge au-dessus de ce décalage ; si le décalage dépassait un jour ~90 s, le faux palier de bot pourrait revenir.

Piste ouverte : une livraison de bot ne change que `total`, donc « `total` monte seul » suffirait à la reconnaître sans clé spécifique, à confirmer en direct avec `/ds_counters`.

## Commande 70 (Cremation: BB, fin du jeu), relevé du 18/11

Deux essais avec la même sauvegarde (70 en cours) : le total monte de 1 à la crémation (`70 -> 71`) sans que `nobot` bouge, comme pour la 62, et le client prend cette hausse pour une livraison de bot (palier de bot environ 90 s plus tard). La clé « repair » ne bouge pas.

`/ds_counters diff` pris au début du générique (après le palier de bot) : 7 compteurs changent.

| Clé | Changement |
|---|---|
| `27c0565a…` (total) | 70 -> 71 |
| `26adb4df…` (likes) | +101 000 (1 358 095 -> 1 459 095) |
| `9ee48407…` | 102 -> 103 (+1) |
| `63353f3a…` | absente -> 6605 |
| `8da0f66b…` | 1 -> 0 |
| `88a3ea04…`, `cd8735b9…` | absentes -> 0 |

Piste : `9ee48407…` monte pour toute commande qui n'est pas un bot (standard, principales 60 / 61, 62 : +11, 70 : +1), pas pour une livraison de bot (paires de sauvegardes). Il pourrait servir à écarter ces hausses du total sans clé propre à chaque commande. Non implémenté : il faudrait absorber la hausse dans la base du palier de bot (persistée) sans la compter deux fois avec la clé « repair » de la 62, et vérifier que `9ee48407…` ne bouge pas en jeu ordinaire. À retenter si la 68 (objectif épisode 12) montre le même défaut. `63353f3a…` (6605) apparaît à la fin : signification inconnue (peut-être un compteur de fin de partie).

Détection de la 70 : par la sauvegarde avec l'outil de déchiffrement, et par la mémoire seule (outil désactivé) : titre lu 30 s à 1 min après la sauvegarde qui suit le générique (les zones de titres sont perdues pendant la fin : recherches complètes répétées jusqu'à retrouver le titre).
