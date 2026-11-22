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

Limites : marchandises perdues testées 2 fois le 18/11 (comptées comme livraisons de bot, voir plus bas) ; demandes d'équipement non testables en jeu hors ligne (elles supposent la connexion en ligne) ; les trois compteurs sont écrits séparément (le client exige deux lectures identiques).

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
| Commande standard | `nobot` +1, `total` +1, `9ee48407…` **-28** (baisse), `cb920241…` apparaît (=1), `4c615b8a…` disparaît |
| Commande principale 60 | `nobot` +1, `total` +1, `1f63d23f…` +2, `e39be3a6…` **1 -> 0**, `1ce82f7a…` et `4c615b8a…` apparaissent (=0) ; `9ee48407…` inchangé |
| Commande principale 61 | `nobot` +1, `total` +1, `34c1624b…` +6, `9ee48407…` +2, `a63a89d0…` +2, `6e891c1e…` **1 -> 0**, `4374086b…` apparaît (=0), `37d16dcf…` disparaît |
| Commande 62 | `total` +1 (pas `nobot`), likes +1000 (`26adb4df…`), `9ee48407…` +11, `34c1624b…` +22, clés `7f91306c…` (=1) et `f496b86a…` (=0) créées |

**Validé en jeu (TEST #28, 62 livrée avec une commande de bot en cours) :** la clé `7f91306c…` apparaît **36 à 40 s après** la hausse de `total` (trois relevés : 40 s, 36 s, 38 s ; **quatrième relevé le 18/11 à 23 h 41 : 98 s ; cinquième le 19/11 à 13 h 48 : 124 s**, voir plus bas), car le jeu écrit ses compteurs en plusieurs temps. Le client mémorise donc l'instant de la hausse de `total` et celui de l'apparition de la clé, et reconnaît la 62 quand les deux tombent dans une fenêtre de 300 s (`repair_progress`, relevés bruts, sans exiger de valeur stable). La confirmation de palier de bot (45 relevés, environ 90 s) laisse une marge au-dessus de ce décalage ; si le décalage dépassait un jour ~90 s, le faux palier de bot pourrait revenir.

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

Correction (18/11) : `9ee48407…` n'est **pas** un marqueur fiable de « commande non-bot terminée » : il baisse de 28 à une commande standard et ne bouge pas à la 60. Voir la section « Classement des compteurs » plus bas : `26adb4df…` (+1000 à la 62, +101 000 à la 70) et les clés « drapeau » 1 -> 0 / créées à 0 sont de meilleurs candidats, avec très peu d'exemples (2 événements spéciaux, 1 livraison de bot).

Détection de la 70 : par la sauvegarde avec l'outil de déchiffrement, et par la mémoire seule (outil désactivé) : titre lu 30 s à 1 min après la sauvegarde qui suit le générique (les zones de titres sont perdues pendant la fin : recherches complètes répétées jusqu'à retrouver le titre).

## Classement des compteurs (paires de sauvegardes + relevés en direct), 18/11

Données : 12 sauvegardes déchiffrées (5 paires avant / après utiles : principale 60, principale 61, standard, bot, 62 ; plus une paire de deux sauvegardes d'après la 62, sans aucune différence) et deux relevés `/ds_counters diff` en direct (62 avec bot actif ; 70). Les sauvegardes contiennent 248 à 255 clés (258 au total), la mémoire 293. **231 clés sur 258 ne changent jamais entre les 12 sauvegardes**, 16 varient, 11 sont partielles : la table est presque statique, donc un journal de changements (`/ds_counters watch`) reste lisible.

| Événement | Clés qui changent (valeur) | Statut |
|---|---|---|
| Livraison de bot | `total` +1, rien d'autre (aucun changement différé non plus) | vérifié : 1 paire de sauvegardes + 3 livraisons en direct (`/ds_counters watch`, 18/11 22 h : 12 min de silence entre deux livraisons) |
| Marchandise perdue rendue (2 essais, 18/11 23 h) | `total` +1 seul (`nobot` inchangé : **indiscernable d'une livraison de bot par ces deux compteurs**). Autour : `8da0f66b…` 1 -> 0 en sortant d'une zone de livraison puis 0 -> 1 en y entrant (observé par le joueur, y compris sans livraison : 23:08:50 / 23:08:55) ; `d18f523f…` +1 (essai 1) puis +10 en 90 s (essai 2) ; essai 2 : `da70c6fc…` +1 et `55a57fec…` +1 (non vus à l'essai 1). | vérifié sur 2 essais en direct ; **aucune clé spécifique trouvée** (voir ci-dessous) |
| Commande standard | `nobot` +1, `total` +1, `9ee48407…` -28, `cb920241…` créée (1), `4c615b8a…` disparue | vérifié (1 paire de sauvegardes + 3 relevés en direct des seuls compteurs bruts, 18/11 23 h ; voir chronologie ci-dessous) |
| Principale 60 | `nobot` +1, `total` +1, `1f63d23f…` +2, `e39be3a6…` 1 -> 0, `1ce82f7a…` / `4c615b8a…` créées (0) | vérifié (1 paire) |
| Principale 61 | `nobot` +1, `total` +1, `34c1624b…` +6, `9ee48407…` +2, `a63a89d0…` +2, `6e891c1e…` 1 -> 0, `4374086b…` créée (0), `37d16dcf…` disparue | vérifié (1 paire) |
| 62 (spéciale) | `total` +1 seul (pas `nobot`), `26adb4df…` +1000, `1f63d23f…` +2, `34c1624b…` +22, `9ee48407…` +11, `7f91306c…` créée (1), `f496b86a…` créée (0) | vérifié (1 paire + relevé en direct) |
| 70 (spéciale, fin) | `total` +1 seul, `26adb4df…` +101 000, `9ee48407…` +1, `8da0f66b…` 1 -> 0, `63353f3a…` créée (6605), `88a3ea04…` et `cd8735b9…` créées (0) | vérifié (2 essais en jeu, 1 relevé) |

Rôles probables (**hypothèses**) :
- `26adb4df…` : cumul de likes / récompenses (850 095 vers la 62, 1 358 095 vers la 70) ; monte aux commandes spéciales observées (62, 70) et ne bouge pas aux paires standard, 60, 61, bot ; mais il vaut 845 095 dans 9 sauvegardes, 850 095 juste avant la 62 et 851 095 après : un autre événement non identifié (+5000, entre la fin de la 61 et le début de la 62) le fait monter aussi. Il n'est donc pas exclusif aux commandes spéciales.
- Clés « drapeau » `e39be3a6…` (60), `6e891c1e…` (61), `8da0f66b…` (70) : **hypothèse d'un drapeau par commande principale très affaiblie**. Le relevé en direct du 18/11 (voyage rapide, 22 h 24) montre `8da0f66b…` qui passe de 1 à 0 puis revient à 1 en 5 s : c'est un état de jeu (chargement, cinématique), pas un drapeau de commande ; son 1 -> 0 à la 70 (générique) s'explique ainsi. Les deux autres, relevées entre deux sauvegardes, peuvent être de même nature. À ne pas utiliser pour détecter des commandes.
- `9ee48407…` n'est pas un compteur de commandes : il baisse de 3 sans aucune commande (voyage rapide) en même temps que `0fe77991…`, `c580f851…` et `f56d0510…` (216 -> 213 pour les quatre) ; probablement une quantité d'objets / de cargaison.
- `63353f3a…` apparaît (5600 ; 6605 à la 70) au moment d'un point de contrôle (voyage rapide : même seconde que la lecture du titre de la 61) : lié à la sauvegarde, pas à une commande (hypothèse).
- `37d16dcf…` apparaît / disparaît selon l'état du jeu (créée à 0 au voyage rapide ; disparue à la 61) : bruit.

Règle possible pour écarter les hausses du total qui ne sont pas des livraisons de bot (**non implémentée**, à valider en jeu ; les 4 livraisons de bot observées ne touchent QUE `total`, alors que la 62 et la 70 touchent aussi `26adb4df…`, seule clé commune qui ne soit pas du bruit d'état) : « `total` monte seul et `26adb4df…` monte d'au moins 1000 dans les 120 s » = commande spéciale (le +5000 inexpliqué ci-dessus montre que la règle peut se tromper si cet événement tombe dans la même fenêtre). Il faudrait aussi retrancher cette hausse de la base du palier de bot (valeur enregistrée sur disque) sans la compter deux fois avec la clé « repair » de la 62 (qui apparaît vers 40 s : n'absorber qu'après ~75 s si elle n'est pas apparue), et vérifier sur plusieurs livraisons de bot, une marchandise perdue et une demande d'équipement que `26adb4df…` ne bouge pas.

## Numéros de commandes principales : ce que montre la table Cheat Engine publique (source secondaire, 18/11)

La table communautaire jointe (`DeathStrandingDC_Update37_for_v1.004…CT`) contient un pas-à-pas par épisode qui cite des numéros de commandes. **Les 19 numéros manquants de la liste du projet y figurent tous** (existence confirmée ; noms exacts à relever en jeu) :
- épisode 2 : 6, 10, 11 (depuis le Wind Farm), 12 et 13 (depuis le centre de distribution Ouest de Capital Knot City), 15 (depuis Capital Knot City), 17 (Ludens Fan) ;
- épisode 3 : 25, 26, 29 (Weather Station), 31, 35 (Junk Dealer), 36 (récupération sur des MULE), 37 (livraison au Cosplayer) ;
- épisode 4 : 40 (livraison à Peter Englert) ; épisode 5 : 42, 45 (Peter Englert) ; épisode 7 : 56 (Mountain Knot City) ; épisode 8 : 57 (Peter Englert).
La table cite aussi des numéros 71 à 85 (par exemple 72, 74, 77 « Director's Cut Episode Quest », 78, 79, 80 à 85) et des « Standard Order » à partir de 100. Les commandes < 100 hors liste sont déjà signalées une fois dans le journal du client.

Effets en jeu des objets : la même table liste des pointeurs pour le poids transporté, les munitions, la durabilité des bottes, la batterie des véhicules et les matériaux des installations, mais son auteur note encore « find a way to spawn items » en objectif non résolu ; « Infinite Equipment/Weapon Use » et « Max Carrying Weight » sont de simples interrupteurs d'un script injecté (code patché), pas des valeurs à écrire. Aucune structure publique d'inventaire ou de déblocage d'équipement n'est donc connue.

## Optimisation possible : recherche complète des titres en boucle

Quand le client ne trouve aucun titre en mémoire (menus, fin du jeu), il relance une recherche complète au plus toutes les 60 s, mais chacune dure déjà environ 55 s : environ 90 % du temps à lire ~10 Go de mémoire (relevé du 18/11 : une douzaine de recherches d'affilée pendant la fin du jeu). Piste : attendre au moins trois fois la durée de la dernière recherche entre deux essais quand aucune zone n'est connue. Contre-partie : la détection d'un titre sans compteur de livraison peut prendre quelques minutes de plus. Non appliqué.

### Marchandise perdue : ce que les deux essais du 18/11 (23 h) montrent
- `total` +1 seul, `nobot` inchangé, dans les deux essais : le client la compte comme une livraison de bot (palier à ~90 s). **À confirmer par la ligne « Palier de commandes de bot atteint » du journal.** Comportement conservé : un check de trop est moins grave qu'un check manquant.
- `8da0f66b…` = **indicateur de présence dans une zone de livraison** (observation du joueur : 0 quand il sort de la zone, 1 quand il y rentre). Cela explique ses bascules au voyage rapide, au chargement, et aux deux essais. Ce n'est pas un marqueur de commande.
- `d18f523f…` = **compteur d'activité du joueur** (+1 une fois à l'essai 1, +10 en 90 s à l'essai 2) : identique avant/après dans les 12 sauvegardes pour chaque commande (bot 218/218, standard 218/218, principale 220/220, 62 : 207/207 et 208/208). Comme il bouge avec l'activité du joueur, une règle « `d18f523f…` a monté, donc marchandise perdue » classerait à tort en marchandise perdue une vraie livraison de bot quand le joueur ramasse des objets en même temps : **piste abandonnée, non implémentée**.
- `da70c6fc…` (+1 à 23:06:45) et `55a57fec…` (+1 à 23:07:00) : inexpliqués, un seul exemple, absents de l'essai 1. Dans les sauvegardes, `55a57fec…` passe de 588 à 589 dans la seconde paire de la commande 62 ; les deux clés bougent lentement entre sauvegardes.
- Essai 2 (bot en parallèle) : une seule hausse du total (60 -> 61, 23:07:11) ; l'heure de fin de la livraison de bot n'est pas connue, ce qui laisse deux lectures (marchandise perdue = +1 et bot pas encore terminé, ou l'inverse).

### Chronologie d'une livraison standard (4 relevés en direct, 18/11, 23 h 22-23 h 29, autre sauvegarde)
Quatre livraisons (échantillon, standard fragile ×2, standard ordinaire) ont toutes la même signature : `nobot` +1, `total` +1, `standard` (clé 17) +1. Le jeu écrit ces trois compteurs **séparément**, toujours dans le même ordre (heures du joueur entre parenthèses) :

| Livraison | `total` +1 (début de la cinématique) | `standard` +1 (fin de l'écran de résultat) | `nobot` +1 (sortie de l'écran de résultat) |
|---|---|---|---|
| Échantillon | 23:22:22 | 23:22:50 (+28 s) | 23:23:12 (+22 s) |
| Standard fragile | 23:25:06 | 23:25:38 (+32 s) | 23:26:02 (+24 s) |
| Standard | 23:28:04 | 23:28:30 (+26 s) | 23:28:56 (+26 s) |
| Standard fragile (suivi `watch` actif) | 23:33:43 | 23:34:03 (+20 s) | 23:35:14 (+71 s : stats lues sans se presser) |

- Le `total` a donc **50 à 91 s d'avance** sur `nobot` : pendant ce temps le « bot » calculé (`total` - `nobot` - `repair` + 1000) est trop haut de 1. Ces délais dépendent du rythme du joueur sur l'écran de résultat : les trois premiers relevés sont faits en appuyant vite, le quatrième avec 71 s passées sur l'écran des statistiques.
- Le client n'en fait pas un faux palier de bot : le relevé qu'il juge stable est le triplet (`standard`, `main`, `bot`) ; il change à chaque écriture (`total` +1 -> `bot` +1 ; `standard` +1 -> `standard` +1 et `main` -1 ; `nobot` +1 -> `main` +1 et `bot` -1), et une livraison de bot exige 90 s sans aucun changement. Plus longue période stable observée : **72 s** (quatrième livraison, entre `standard` +1 et `nobot` +1), soit **18 s de marge seulement** (les trois premiers relevés : 32 s au plus). Un faux palier de bot arrive si le joueur reste plus de 90 s sur une seule de ces étapes (stats lues longuement, pause, absence) et coûte un check de bot en trop.
- Valeurs de fin identiques à celles du début : `main` = `nobot` - `standard` inchangé (19 -> 19), `bot` = `total` - `nobot` inchangé (1 -> 1). Aucun faux palier.
- Le suivi des autres clés (`/ds_counters watch`) n'était pas actif : seules les quatre valeurs brutes sont connues pour ces trois livraisons.
- Une ligne « Commande n°336 terminée (hors liste des checks : ignorée) » est apparue une seule fois (vers 23:23:40, probablement l'échantillon) : les numéros de commandes standard sont lisibles par titre, mais pas à chaque livraison (1 sur 3).

#### Quatrième livraison (23:33-23:35, `watch` actif) : autres clés
| Heure | Changement |
|---|---|
| 23:33:38 | `9ee48407…` 208 -> 227 (+19), 5 s avant la fin de livraison : quantité d'objets (la ligne « -28 » de la paire de sauvegardes standard n'est pas un marqueur de commande non plus : ses valeurs vont de 210 à 250 selon les sauvegardes) |
| 23:33:43 (début de la cinématique) | `total` +1, **`4c615b8a…` 0 -> 1**, `63353f3a…` créée (5600 : point de contrôle) |
| 23:33:54 | `8da0f66b…` 1 -> 0 (sorti de la zone de livraison), `f3ec6d76…` créée (1 ; présente aussi dans les 4 sauvegardes de la 62, absente des autres) |
| 23:34:03 (fin de livraison, écran de statistiques) | `standard` +1 |
| 23:35:14 (sortie de l'écran) | `nobot` +1, **`4c615b8a…` 1 -> 0**, `6e843d6f…` 98 -> 99 (vaut 100 dans les 12 sauvegardes : probablement un compteur plafonné à 100, donc inutilisable) |

- **`4c615b8a…` vaut 1 exactement pendant la période où `total` a de l'avance sur `nobot`** (de la cinématique à la sortie de l'écran de résultat). Dans les 12 sauvegardes elle ne vaut jamais 1 (0 ou absente), comme on s'y attend d'un état transitoire. Elle n'a **pas bougé** pendant les 3 livraisons de bot du test A, ni pendant les 2 marchandises perdues (suivi actif). **Règle implémentée le 19/11 (`bot_hold_step`, non validée en jeu ; 1 seul exemple, délai de sécurité de 300 s)** : tant que `4c615b8a…` vaut 1, ne pas confirmer de livraison de bot (puis exiger de nouveau 90 s de stabilité après sa retombée à 0, plus un délai maximal de sécurité pour ne pas rester bloqué si la clé restait à 1). Elle supprimerait le risque de faux palier de bot sur les commandes standard, quel que soit le temps passé sur l'écran de résultat. À confirmer sur une commande principale et une autre commande standard ; ne couvre pas les commandes spéciales (62, 70) ni les marchandises perdues.

### Commande 62 en direct avec `watch` (18/11, 23:37-23:41, autre sauvegarde)
Heures du joueur : acceptée vers 23:39 ; fin de livraison lancée 23:39:59 ; sortie de l'écran de résultat 23:41:04 ; « fin complète, après dialogues et sauvegarde » 23:41:41.

| Heure | Changement |
|---|---|
| 23:37:54 - 23:38:04 | `c580f851…`, `f56d0510…` puis `9ee48407…` +12 (quantités d'objets) |
| 23:38:19 | **`26adb4df…` 845 095 -> 850 095 (+5000)**, environ 1 min avant l'acceptation notée par le joueur (à préciser : même saut que dans la paire de sauvegardes « avant 62 ») |
| 23:39:19 | `63353f3a…` 5600 -> 5900 (+300), `fc3d06f4…` 1 -> 2 |
| 23:39:34 / 23:39:59 | `c580f851…` puis `9ee48407…` +11 (quantités d'objets, déjà vu en +11 dans la paire de la 62) |
| **23:40:03-04** | **`total` +1 seul (`nobot` reste 50), `26adb4df…` +1000 (850 095 -> 851 095), `f496b86a…` créée (0)**, tous dans le même relevé |
| 23:41:04 | `37d16dcf…` 0 -> 2 (sortie de l'écran de résultat) |
| 23:41:29 | `34c1624b…` +22 (comme dans la paire de la 62) |
| **23:41:41** | **`reparation` 0 -> 1** (clé `7f91306c…`) : « Commande terminée détectée (compteur) : Order 62 », check envoyé |

- Détection de la 62 par la clé « repair » : correcte, le check est parti. En fin de séquence `bot` (`total` - `nobot` - `repair`) est revenu à sa valeur de départ.
- **Délai entre `total` et la clé « repair » : 98 s** (23:40:03 -> 23:41:41), contre 36 à 40 s aux trois relevés précédents. La clé est écrite à la fin des dialogues et de la sauvegarde, donc le délai dépend du rythme du joueur. Il reste sous la fenêtre `REPAIR_WINDOW` (300 s), mais **dépasse les 90 s de confirmation d'une livraison de bot** : pendant ces 97 s, `bot` est trop haut de 1 sans changement du triplet (`standard`, `main`, `bot`) jugé stable. D'après le code, un palier de bot en trop est alors possible si le compteur de bot de la sauvegarde dépasse la base. Le journal ne le montre pas : aucune ligne « Palier » n'apparaît, ce qui est attendu si le compteur de bot de cette sauvegarde (1001) reste sous la base fixée sur la sauvegarde principale. **Non démontré en jeu.**
- Marqueurs de commande spéciale vus dans le relevé de la hausse du `total` : `26adb4df…` +1000 (+101 000 à la 70) et une clé créée à 0 (`f496b86a…` ; à la 70 : `88a3ea04…` et `cd8735b9…`). Aucun des 4 bots, 2 marchandises perdues et 4 livraisons standard observés en direct ne les montre. `4c615b8a…` n'a pas bougé pendant la 62 (elle ne couvre que les commandes standard).
- **Règle implémentée le 19/11 (`bot_hold_step`, non validée en jeu)** : si `26adb4df…` monte d'au moins 1000 dans les ~10 s autour d'une hausse de `total` seul, retenir toute confirmation de bot pendant `REPAIR_WINDOW` (300 s) ou jusqu'à l'apparition de la clé « repair ». Ne fait que retarder (jamais de check perdu) ; pour la 70 (pas de clé « repair »), le palier de bot est alors confirmé au bout de 300 s, sans conséquence pour l'objectif 14.

### Commande principale 61 en direct (19/11, 23:57-23:59, autre sauvegarde, `watch` actif)
Heures du joueur : début de la livraison (cinématique) 23:57:41 ; sortie de l'écran de résultat 23:58:20 ; fin complète et sauvegarde 23:59:10.

| Heure | Changement |
|---|---|
| 23:57:36 | `9ee48407…` +2, `37d16dcf…` créée (0), `8573c7fa…` 1 -> 0 |
| **23:57:41** | **`total` +1 seul (`nobot` reste 46)**, `4374086b…` créée (0), `6e891c1e…` 1 -> 0, `a63a89d0…` +2, `63353f3a…` créée (5600) |
| 23:57:56 | `8da0f66b…` 1 -> 0 (sortie de la zone de livraison) |
| **23:58:20-21** | **`nobot` +1**, `37d16dcf…` 0 -> 3, `6e843d6f…` 95 -> 96 ; `standard` inchangé (28) |
| 23:58:46 | `34c1624b…` 612 -> 611 (-1) |

- La signature de la 61 de la paire de sauvegardes est retrouvée en direct : `4374086b…` créée, `6e891c1e…` 1 -> 0, `a63a89d0…` +2, `9ee48407…` +2. `34c1624b…` ne l'est pas (+6 dans la paire, -1 ici) : ce n'est pas un marqueur.
- `total` a **40 s d'avance** sur `nobot` (pas d'étape `standard` entre les deux pour une commande principale) : bien sous les 90 s de confirmation du bot. Aucune retenue automatique pour les commandes principales ordinaires : ni `26adb4df…` ni `4c615b8a…` ne bougent.
- **Hypothèse « un drapeau 1 -> 0 par commande principale » de nouveau plausible** : `6e891c1e…` passe de 1 à 0 à la livraison de la 61 (deux fois : paire de sauvegardes et direct), `e39be3a6…` à la 60 (une fois). L'abandon du 18/11 reposait sur `8da0f66b…` (indicateur de zone de livraison) et `9ee48407…` (quantité d'objets), qui n'en étaient pas : il ne reste que ces deux clés. Piste : lire ces drapeaux pour détecter une commande terminée sans chercher son titre en mémoire ; exige une livraison de chaque commande pour établir la correspondance clé / numéro.

### Commande 62 avec la retenue du bot (19/11, 13:46-13:48, `watch` actif, dialogues et cinématiques non passés) : validation en jeu
Contexte : nouvelle multiworld, bases : bot 1001 (paliers 0/3), standard 36, likes 28 551 ; commande 62 déjà acceptée, une commande de bot en cours en parallèle (pas livrée pendant le relevé).

| Heure | Changement |
|---|---|
| 13:46:26 | début de la livraison ; `9ee48407…` +11, `37d16dcf…` créée (0) ; palier de likes 1 atteint (+1000 likes de la livraison) |
| **13:46:28-31** | **`total` +1 seul (`nobot` reste 56), `26adb4df…` +1000, `f496b86a…` créée (0)** ; journal : « Livraison de bot : confirmation retenue » |
| 13:47:01 | `37d16dcf…` 0 -> 2 (sortie de l'écran de résultat) |
| 13:47:51 | `34c1624b…` +22 |
| **13:48:31-32** | **`reparation` 0 -> 1** (**124 s après le total**) : « Commande terminée détectée (compteur) : Order 62 », check envoyé |

- **Validé : aucun faux palier de bot.** Avec l'ancienne règle, le triplet jugé stable restait identique de 13:46:28 à 13:48:31 (123 s > 90 s) et un « Palier de commandes de bot atteint : 1 » serait apparu vers 13:47:58 (base 1001, 0/3 paliers atteints : cas idéal pour le voir). Le journal n'en contient aucun.
- Troisième observation de `26adb4df…` +1000 dans le même relevé que la hausse du total à la 62 (avec `f496b86a…` créée à 0).
- Délais total -> clé « repair » observés : 40, 36, 38, 98 et **124 s** : ils dépendent des dialogues, la fenêtre de 90 s ne pouvait pas convenir.
- **Reste à valider** : que le bot en parallèle soit bien compté quand il se termine après la retenue (palier 1 attendu).

### Commande « de bot » récupérée au terminal, après la 62 (19/11, 13:57, `watch` actif) : comportement différent des 3 bots du test A
Heures du joueur : petit message d'arrivée du bot 13:57:22 ; récupération de la commande au terminal de livraison 13:57:44.

| Heure | Changement |
|---|---|
| 13:57:22 (message) | aucun changement de compteur |
| **13:57:44** (récupération au terminal) | `total` +1 (`nobot` reste 56, `repair` = 1, `standard` reste 36) |
| **13:57:56** | **`nobot` +1** (`total` reste 59) |

- Le jeu n'écrit donc **rien au message d'arrivée** : le compteur bouge à la récupération au terminal.
- Mais ici `nobot` suit `total` 12 s plus tard, sans `standard` : signature d'une commande principale ordinaire (comme la 61 : `total` puis `nobot`), pas celle des 3 bots du test A (`total` seul). Résultat net : bot (`total` - `nobot` - `repair` + 1000) = 1001 avant, 1002 pendant 12 s, 1001 après : **aucun palier de bot**, ce que le joueur constate (« pas de check de bot en la finissant »). La retenue n'est pas intervenue (ni `26adb4df…` ni `4c615b8a…` ne bougent).
- Précisions du joueur : la commande confiée au bot était la **n°345, une livraison standard fragile** (appareils de mesure portables dernier cri) ; les 3 bots du test A étaient, à son souvenir, des commandes standard (fragiles ou non : inconnu). À 13:57:56, il a très probablement quitté le terminal de livraison et une sauvegarde s'est déclenchée.
- La séquence (`total` puis `nobot`, `standard` inchangé) est celle d'une commande principale (61), sans les clés propres à une commande principale (aucune clé créée ni drapeau 1 -> 0 dans le relevé). **Hypothèses non tranchées (1 seul exemple)** : (a) une commande **fragile** confiée à un bot fait aussi monter `nobot` ; (b) `nobot` monte à la sortie du terminal ou à la sauvegarde qui suit une récupération, ce qui n'aurait pas été le cas des bots du test A. À départager avec deux bots (une commande fragile, une non fragile), en notant l'heure de récupération et de sortie du terminal. Conséquence possible : une livraison de bot fragile ne compte pas comme livraison de bot (net 0). **Les deux hypothèses sont réfutées par les deux bots suivants (voir plus bas).**

### Deux bots de 15 min, standard non fragile puis fragile (19/11, 14:06-14:42, `watch` actif, nouvelle apworld avec retenue)
Sauvegarde chargée à 14:06:49 (`nobot` 51, `total` 52, `standard` 32, bases du client : bot 1001, standard 36).

| Bot | Heures du joueur | Compteurs | Palier |
|---|---|---|---|
| Standard non fragile | récupération 14:23:19 ; écran de livraison fermé 14:23:35 ; menu fermé 14:23:55 | `total` +1 seul (`nobot` reste 51) ; `4c615b8a…` créée à **0** (14:23:35, fermeture de l'écran) | « Palier de commandes de bot atteint : 1 » à 14:24:50 (91 s après le total), check reçu |
| Standard fragile | récupération 14:40:21 ; écran fermé 14:40:34 ; menu fermé 14:40:51 | `total` +1 seul (`nobot` reste 51) | « Palier ... : 2 » à 14:41:51 (90 s après le total), check reçu |

- **Les deux bots sont comptés normalement** : `total` +1 seul, aucune hausse de `nobot` (ni à la sortie du terminal, ni à la sauvegarde), palier 90 s plus tard. Les hypothèses du 13:57 (une commande fragile fait monter `nobot` ; `nobot` monte à la sortie du terminal) sont donc **réfutées**. La commande n°345 du 13:57 (`nobot` +1 douze secondes après le `total`) reste **un cas isolé inexpliqué** (5 bots normaux observés contre 1 anormal, tous des commandes standard) ; il suivait la 62 dans la même sauvegarde.
- La retenue n'est pas intervenue (aucun saut de `26adb4df…`, `4c615b8a…` jamais à 1) : un bot ne retarde pas plus que les 90 s habituelles. `4c615b8a…` apparaît à 0 à la première livraison de la sauvegarde (écran de livraison fermé) ; elle ne passe à 1 que pendant la finalisation d'une commande standard faite à la main.
- Le message d'arrivée du bot (13:57:22 la veille) n'écrit rien ; le compteur n'est écrit qu'à la récupération au terminal.
- Objets : « Episode 1 Access » (palier 1) et « Pickpocket Trap » (palier 2, -50 cristaux chiraux) appliqués. « Commande n°492 terminée » vue dans le journal (numéros de commandes standard vus : 336, 492).

### Commande standard n°452 avec écran de résultat laissé ouvert : validation de la retenue `4c615b8a…` (19/11, 14:44-14:48)
Heures du joueur : acceptation 14:44:55 ; arrivée au point de livraison 14:45:41 ; début de la livraison (cinématique) 14:46:06 ; écran de résultat fermé 14:48:20 ; terminal fermé 14:48:40. Bases du client : bot 1001 (paliers 2/3 atteints), standard 36 ; la sauvegarde est à 32.

| Heure | Changement |
|---|---|
| **14:46:07-11** | **`total` +1** (`nobot` reste 51), **`4c615b8a…` 0 -> 1** ; journal : « Livraison de bot : confirmation retenue » |
| 14:46:16 | `8da0f66b…` 1 -> 0, `dca14f7f…` 1 -> 0 (clé nouvelle, inexpliquée) |
| 14:46:25 | `standard` +1 (32 -> 33), 18 s après le total |
| **14:48:21** | **`nobot` +1, `4c615b8a…` 1 -> 0** (sortie de l'écran de résultat) |
| 14:48:41 | `8da0f66b…` 0 -> 1 (retour dans la zone) |

- **Validé : aucun faux palier de bot.** Le triplet (`standard`, `main`, `bot`) est resté identique **116 s** (14:46:25 -> 14:48:21), donc plus que les 90 s : sans la retenue, un « Palier de commandes de bot atteint : 3 » (3 paliers dans la seed, 2 déjà atteints) serait apparu vers 14:47:55. Le journal n'en contient aucun. Le `total` avait **134 s d'avance** sur `nobot`.
- Deuxième observation de `4c615b8a…` : 0 -> 1 à la cinématique (au même relevé que le `total`), 1 -> 0 à la sortie de l'écran, avec `nobot` +1.
- Aucun check de commande standard n'a été envoyé : normal, la sauvegarde est à 32 (puis 33) et la base du client à 36 (gain = 0). Il faudrait `/ds_standard_rebase` sur cette sauvegarde, ou dépasser 36 livraisons.

### Journal du test `episode_gating` (19/11, 14:56-15:00) : relevés annexes
- **Standard livrée à la main (14:56:29-46)** : `total` +1 avec `4c615b8a…` 0 -> 1 (retenue du bot engagée), `standard` +1 à 14:56:41 (palier de commandes standard 1 atteint, check envoyé), `nobot` +1 avec `4c615b8a…` 1 -> 0 à 14:56:46 (17 s après le total, 6e843d6f… 98 -> 99). Troisième observation du drapeau 0 -> 1 -> 0 sur une commande standard.
- **Commande 62 (14:58:48)** : `total` +1 avec `26adb4df…` +1000 et `f496b86a…` créée (retenue engagée), clé « repair » 34 s plus tard (14:59:22), palier de likes 1 (+1000 likes). Quatrième observation de `26adb4df…` +1000 avec le total à la 62. `26adb4df…` avait fait +5000 à 14:57:37, soit 71 s avant la hausse du total (3e observation de ce saut avant la 62 : 104 s à la première, 71 s ici).
- Les paliers de likes et de commandes standard sont réaffichés à la reconnexion au serveur (sans conséquence).


## Course 63 → 69 avec `watch` actif (19/11, 15:58-16:46, apworld 0.3.0 publiée, `episode_gating` actif, bot 1003, paliers 0/3)
Heures du joueur : 63 livrée 15:59:01 (sortie de l'écran de résultat 15:59:27, fin complète 15:59:58) ; 64 (boss, Higgs retenant Amélie) battue 16:06:00 ; 65 (combat de Higgs sur la grève) terminée 16:19:29 ; 67 : étape 1 validée 16:30:01, Cliff vaincu 16:34:06, écran de résultat 16:34:32-51 ; 68 livrée 16:40:24, écran 16:40:53 ; chapitre 13 à 16:43:10 (69 active dès les cinématiques).

| Commande | Compteurs au moment de la fin | `nobot` ? | Clés créées (absent → valeur) avec le `total` |
|---|---|---|---|
| 63 (livraison) | `total` 51→52 (15:59:01) | **+2** (15:59:27) | `63353f3a…` (6000), `d9574e65…` (0) ; `37d16dcf…` (0) 8 s avant |
| 64 (boss) | `total` 52→53 (16:06:00) | non | `4e96248a…` (0, puis 1 à la sortie de l'écran, 16:06:34) |
| 65 (Higgs) | `total` 53→54 (16:19:29) + `26adb4df…` **+103 000** | non | `d4a6a0e4…` (0) |
| 67 (Cliff) | `total` 54→55 (16:34:32) | non | `6f178569…` (1) ; 9 clés modifiées au même relevé |
| 68 (livraison spéciale) | `total` 55→56 (16:40:24) + `26adb4df…` **+202 000** | non | `6134f3c4…`, `81118171…`, `d32463f3…` (0) |

- **Les fins de commande qui ne sont pas des livraisons classiques ne font monter que `total`** : le « bot » calculé (`total` − `nobot` − `repair` + 1000) monte de 1. Résultat avec l'ancienne règle : **3 faux paliers de bot** (65 à 16:24:30, soit la retenue de 300 s après le saut de likes ; 67 vers 16:36, ~90 s après, aucun marqueur ; 68 vers 16:45:30, fin de la retenue). La 64 est masquée parce que le `nobot` +2 de la 63 avait fait descendre le « bot » de 1.
- **Signature commune à toutes les fins de commande observées (60, 61, 62, 63, 64, 65, 67, 68) : une clé est créée dans le même relevé que la hausse du `total`.** Aucune des 4 livraisons de bot, 2 marchandises perdues, ni des 2 bots de 14:23-14:40 n'a ce comportement (`4c615b8a…` est créée 16 s plus tard à la fermeture de l'écran : exclue). `26adb4df…` (likes cumulés) saute aux commandes spéciales 62 (+1000), 65 (+103 000), 68 (+202 000), 70 (+101 000) ; la clé « repair » n'existe qu'à la 62. À 16:27:10 (écran de stats de fin d'épisode) les likes montent de 101 000 **sans** hausse du `total`.
- **Détection par la mémoire (titres)** : 64 vue à 16:09:04 (177 s après la fin ; enregistrement en entrant dans la chambre à 16:08:19), 65 à 16:21:55 (148 s, au rechargement après les cinématiques), 67 à 16:38:17 (225 s, enregistrement au terminal). **La 63 n'a jamais été vue** (aucun enregistrement entre sa fin et la fin de la 64 ; le titre ne garde que la dernière commande) et **la 68 non plus** (aucun enregistrement avant 16:46). Une rafale de 90 s après le compteur ne suffit donc pas ; le build TEST garde la cadence continue 6 min.
- Victoire (objectif épisode 12) : non partie, la 68 n'étant pas détectée, et, `episode_gating` étant actif, elle serait retenue sans les accès 1 à 12 (la victoire ignore les checks retenus).
- **63 confirmée manquée** (le joueur avait régénéré la partie avant la course : aucun envoi antérieur). **La 66 existe dans le jeu mais n'est pas obligatoire pour l'histoire** (confirmé par le joueur) : le lieu reste valide, mais la commande doit être faite à la main ; nom et épisode exacts à relever quand elle sera faite. L'écran de stats de 16:27:10 est annoncé « fin épisode 11 » par le joueur, avant la 67 : l'épisode de la 67 est peut-être 12 (la table le met en 11 ; `episode_gating` a retenu la 67 derrière les accès 1 à 11).
- Autres clés observées : `f7020f19…` 1→2→3 aux étapes de la 65 (0 au rechargement), `6c91fa26…` +1 à chaque fin de séquence, `12f07528…` / `607f7aec…` (paire qui oscille, 0↔7), `8da0f66b…` (drapeau de zone de livraison, 1↔0), `c580f851…` / `f56d0510…` / `9ee48407…` (quantités d'objets, variables avec les ressources).

### Piste : reconnaître la 68 (et les autres fins spéciales) sans titre (19/11, 1 seul échantillon, NON implémenté)
- Outil `tools/analyse_console.py` (hors apworld) : pour chaque hausse du `total` d'une console `watch`, liste les clés créées et les changements à ±10 s ; avec plusieurs consoles, compte les clés communes.
- Sauts de `26adb4df…` aux fins spéciales : 62 +1000, 65 +103 000, 68 +202 000, 70 +101 000 ; et **+101 000 à l'écran de stats de fin d'épisode (16:27:10) sans hausse du `total`**. Hypothèse : 101 000 = bonus de fin d'épisode (65 = 101 000 + 2000 ? 68 = 2 × 101 000 ?) ; à vérifier sur d'autres épisodes.
- `96814946…` : 1 → 4 à la fin de la 67, 4 → 1 à la fin de la 68 (même relevé que le `total`) ; `fd9d5e11…` : -1 → 2 → -1 autour de la 67. Seuls les relevés d'une 2e course 67 / 68 diront si c'est une empreinte stable ou un état propre à cette partie.
- Aucun identifiant du numéro de commande n'a été trouvé dans la table (`63353f3a…` : 5600 à la 61, 6000 à la 63, 6200 / 6300 / 6400 aux débuts des 65 / 67 et à l'acceptation de la 68, mais aucun changement à l'arrivée de la 69 : pas un compteur « une commande = +100 »). Tant qu'aucune empreinte n'est confirmée, la 68 reste identifiée par titre (au prochain enregistrement) ou, à défaut, par l'avertissement « fin de commande non identifiée » du build TEST puis `/check`.

## 2e course 63 → 68 avec le paquet TEST (19/11, 17:12-17:49, mêmes saves de départ, joueur skippant la plupart des cinématiques)
- **Les clés créées à la fin de chaque commande sont IDENTIQUES à celles de la 1re course et propres à chaque commande** (analyse avec `tools/analyse_console.py` sur les deux consoles) : 63 `d9574e65…`, 64 `4e96248a…`, 65 `d4a6a0e4…` (+ `26adb4df…` +103 000), 67 `6f178569…` (créée 5 s après le total ; + `96814946…` 1→4, `fd9d5e11…` 2→-1), 68 `6134f3c4…` + `81118171…` + `d32463f3…` (+ `26adb4df…` +202 000, `96814946…` 4→1). Avec 61 (`4374086b…`), 62 (`f496b86a…`, 3 relevés) et 70 (`88a3ea04…` + `cd8735b9…`) : **table clé → commande** utilisable pour identifier la fin d'une commande tout de suite, sans titre (`ORDER_MARKER_KEYS` dans le build TEST). 60 : `1ce82f7a…` (GUID complet non relevé).
- **Validé : plus de faux palier de bot** — la hausse de la 65 a été écartée à 17:36:28 (« base 1003 → 1004 », fin de la retenue de 300 s) ; aucun palier sur 64 (masquée par le creux de la 63), 65, 67. Pour la 68 la retenue court jusqu'à 17:52:39 (console arrêtée avant).
- Titres lus **77 s (63), ~48 s (64), ~117 s (65), ~61 s (67)** après la fin de la commande ; la 63 a cette fois été vue (enregistrement avant la 64). Le 1er avertissement « fin non identifiée » (Order 62 probablement manquée) était un **faux positif** : tolérance de 90 s trop longue (la signature de la 63, vieille de 77 s lors de la lecture du titre, était restée en attente). Tolérance ramenée à 15 s.
- 68 : aucun titre avant la fin de la console (comme la 1re course) ; la victoire (objectif 12) ne peut pas partir tant que la 68 n'est pas identifiée, d'où les marqueurs. Les accès 1 à 12 ont été envoyés (console serveur) : « Check libéré » pour 63, 64, 65, 67 immédiatement.
- Écrans de stats : fin ép. 10 à 17:36:03 (début de la 67 à 17:36:53 : la 67 est dans l'épisode **11**, comme dans la table), fin ép. 11 à 17:43:33, la 68 dans l'épisode 12, chapitre 13 à 17:48:24.

## Relevés des 20-21/11 : table de compteurs sur sauvegarde neuve / avancée, drapeaux de fin des commandes 2 à 10
- **La table est créée paresseusement** : 128 cases sur partie neuve / commande 10, 256 puis 512 cases au fil du jeu (n°36, avant la 68). Les clés sont créées par le jeu à la demande (absent → 0 → valeur) et diffèrent selon l'historique de la partie. Cases de 24 octets `<hash u32><clé 16 o><valeur int32>`, comme avant.
- **`total` (hash 0xE5344AB7) est paresseux** : absent de la sauvegarde de la n°36 malgré 2 bots livrés (cause non élucidée) ; présent sur la sauvegarde entre les n°61 et 62. `bot = total − nobot − repair + 1000` n'a de sens que si `total` existe.
- **Piège du test de placement** `(s − (h & (n−1))) % n < 64` : sans effet pour n ≤ 64, donc une fenêtre d'une table plus grande était acceptée comme « petite table » ; corrigé en essayant les capacités de la plus grande à la plus petite (base réelle trouvée d'abord). Bases réelles alignées sur la taille de la table (256/512 cases).
- **Clés de fin de commande (création absent → 0 à la livraison, persistantes)** : n°2 `f9db6f96…`, 3 `640537e9…`, 4 `19af8d70…`, 5 `1ed9b421…`, 6 `1f0fa331…`, 7 `424c79d1…`, 8 `d55e2356…`, 9 `89e67a16…`, 10 `0f772386…`. Présence = commande terminée (rattrapage au lancement validé sur la n°36). Exception n°3 : valeur 1 pendant la cinématique, 0 à l'écran de résultat.
- **`6e843d6f…`** : +1 à la sortie de l'écran de résultat de chaque commande sauf la n°6. **`nobot`** : +1 pour les n°3, 4, 5, 9 et les commandes standard, pas pour les n°2, 7, 8. `4c615b8a…` = drapeau de livraison ; `63353f3a…` est créée au lancement d'un bot (valeur 5600 / 2405 selon la sauvegarde, pas une distance).
- **Récupération de bot** : sur la sauvegarde entre les n°61 et 62 (commande de bot n°337, 661 m, ~10 min) : `total` 49→50, `6e843d6f…` 97→98, création de `4c615b8a…` ; palier de bot n°1 reçu 1 à 2 min après. Sur la sauvegarde de la n°36, seule `6e843d6f…` +1 (pas de `total`).
- Première commande standard (partie neuve, n°133) : base standard 0 (compteur absent), palier 1 reçu. Les commandes standard n'apparaissent qu'après la n°9, les bots vers la n°24.
- Relevés manquants : clés des n°1 et 11 à 60 (`/ds_counters watch on` pendant une course, noter les heures de livraison).

## Origine des clés de fin de commande : lecture dans les fichiers du jeu (21/11, copie du jeu de l'auteur, extraite avec Decima Explorer)
- **Les clés des commandes sont des UUID de version 3** (hachage MD5 d'un nom : demi-octet de version = 3, variante = 10) ; les clés `4c615b8a…`, `26adb4df…`, `6f178569…` sont de version 4 (aléatoires). Ce n'est pas une suite devinable : un nom + un espace de noms inconnus (les essais MD5 / SHA-1 / SHA-256 avec les noms et chemins des fichiers n'ont rien donné).
- **On les retrouve telles quelles dans `ds/mission/main_sub_mission/<mission>/<mission>.core`** (16 octets, ordre direct) : motif `01 <clé 16 o> 02 <cible 16 o> <longueur><hash> "localized/sentences/ds_ui/ds_mission/simpletext"`. La clé est l'identifiant d'une **phrase d'objectif** de la mission ; la cible (UUID v4) est le texte, dans `localized/sentences/ds_ui/ds_mission/simpletext.core` (une entrée par phrase : UUID, longueur u16, texte dans chaque langue). La clé créée à la fin d'une commande est celle de son **dernier objectif** (n°2 « Deliver morphine to the Bridges isolation ward. », n°3 « Return to the Capital Knot City Distribution Center. », n°6 « Build a postbox… », n°7 « Make a delivery to the distribution center… », n°14 « Deliver all four containers of aid. », n°15 « Recycle chiral crystals… », n°61 « Deliver a container of ammonites… »).
- **Missions à plusieurs objectifs** (n°15, relevé du 21/11 21:16-21:19) : chaque étape intermédiaire valide sa propre clé (absent → 1 à la validation de l'étape), toutes repassent à 0 à la validation finale, et la clé de l'objectif final est créée absent → 0 à cet instant. L'**ordre des objectifs dans les fichiers n'est pas fiable** (dans l'ordre du déroulement pour la n°15, inversé pour d'autres) : l'objectif final est déduit du texte (ramasser / récupérer, puis livrer).
- **Numéro de mission ≠ numéro de commande** : correspondance établie par le texte des objectifs (n°1 = 00010, 2 = 00020, 3 = 00030, 4 = 00050, 5 = 00060, 6 = 00065, 7 = 00070, 8 = 00075, 9 = 00080, 10 = 00085, 11 = 00090…, 15 = 00127, 16 = 00130, 17 = 00125, 37 = 00205…). `ds/mission/system/mission_list.core` : 65 missions classées par numéro puis 5 « tutoriels » en queue (00175, 00065, 00085, 00165, 00127 = n°31, 6, 10, 25, 15), 5 pizzas (00700 à 00740 ; la n°26 = 00700 a été vérifiée le 21/11 21:39:43, la clé créée à la livraison est celle de 00700) et 6 missions de puces (00910 à 00960). Aucune table `mission_*` du dossier `system` ne donne le numéro de commande ni l'ordre des objectifs.
- Le client branche ces clés dans `DECIMA_ORDER_FLAGS` (46 commandes de 11 à 66) ; les commandes aux objectifs ambigus (1, 29, 38, 39, 46, 54, 69) restent détectées par les titres. Validées en jeu : 14, 15, 26 (en plus de 2-10 et 61-70).

## Relevé de 103 sauvegardes et validation des commandes 38 et 39 (21/11)

**Méthode.** `tools/scan_saves.py` (déchiffrement par l'outil tiers, décompression de la section 3 du point de contrôle, lecture de la table de compteurs de 20 octets par entrée) a été lancé sur deux jeux de sauvegardes de la même partie (54 + 49 relevés, de 0 à 26 h de jeu). Pour chaque sauvegarde, le titre (« Commande terminée/en cours : nº N ») a été confronté à la présence des clés de fin de commande.

**Résultats.**
- Aucun faux positif réel et aucune absence réelle. Les 8 écarts apparents viennent du titre : il désigne la dernière commande *sélectionnée*, pas la progression (la 8 peut être faite avant la 7, la 58 pendant que la 59 est « en cours »).
- Présence de la clé après la fin de la commande, confirmée dans 24 à 38 sauvegardes pour 12, 14, 16, 18 à 24, 26 à 28, 30, 32 à 36, 41, 43, 44, 47 à 53, 55, 58 à 60 ; dans 18, 6, 3, 3, 3, 2 et 1 pour 61, 62, 63, 64, 65, 67 et 68. Jamais rencontrées (toutes optionnelles) : 13, 17, 37, 40, 42, 45, 56, 57, 66 ; la 70 n'est jamais terminée dans ces sauvegardes.
- Toutes les clés de fin connues valent **0** une fois la commande faite (aucune valeur non nulle sur 103 sauvegardes) ; une étape intermédiaire est à 1 jusqu'à la validation finale. Le client exige donc la valeur 0.
- Trou d'échantillonnage : aucune sauvegarde entre la n°32 (9 h 57) et la n°59 (18 h 34).
- Le compteur « total » est absent jusqu'à la n°32 et présent à 18 h 34 (valeur proche du compteur « sans bot »).

**Commande 38 (relevé en direct 22:30 → 22:34).** À la livraison (22:33:34), `a42c2ea3…` est créée à 0 : c'est la clé de fin. `7a2fe706…` et `6cdcc269…` sont des étapes (absentes → 3 à 22:32:14, puis 3 → 0 à la fin). Le compteur « total » est créé au même instant (absent → 2).

**Commande 39 (22:36 → 22:43).** Aucune clé n'est créée à la validation finale. Les deux objectifs textuels passent à 1 quand ils sont terminés (`d812327c…` à 22:38:30, `ccecd94d…` à 22:42:25) et retombent à 0 à l'écran de résultat (22:43:00) ; « total » passe de 2 à 3. La clé retenue est la dernière étape, `ccecd94d…`, avec la valeur 0 exigée.

**À confirmer.** n°46 (clé lue dans les fichiers, absente à la 32 et présente à la 59, jamais rejouée), n°54 (même structure que la 39 : probablement pas de clé de fin créée), n°29, n°69, n°1.

## Relevé en direct du 22/11 (commandes 40 à 46) : six clés confirmées

Partie reprise après la n°39, `/ds_counters watch on`, 6 livraisons enchaînées. Chaque clé câblée a été créée **absent → 0 à la livraison** (à quelques secondes) :
| Commande | Livraison | Clé créée | Remarque |
|---|---|---|---|
| 42 (Collection : minerais rares) | 09:50:08 | `92a68b85…` | objectif final déduit du texte (« Deliver all four containers ») ; l'étape « Collect » (`71080414…`) passe à 1 à 09:49:05 puis à 0 à la validation : la déduction « collecter, puis livrer » est confirmée |
| 40 (pizza) | 09:52:22 | `c5ab7558…` | confirme l'attribution de la 2ᵉ mission de pizza (00710) à la n°40 : ordre croissant, comme pour la n°26 (00700) |
| 41 | 09:54:45 | `4d3f85fa…` | |
| 43 | 09:57:53 | `5d85d97d…` | |
| 44 | 10:00:54 | `6e43dedf…` | |
| 46 | 10:04:03 | `86f3dd70…` | mission à un seul objectif |

Le compteur « total » augmente de 1 à chaque livraison (3 → 9). Le compteur « sans bot » augmente de 1 à la sortie de l'écran de résultat pour les livraisons ordinaires (40, 41, 43, 44) mais **pas** pour la 42 (collecte) ni la 46 (histoire). Aucun faux palier de bot sur ces six commandes. Le client testé n'avait pas encore les clés 11 et suivantes (détection « mémoire » ou « déduite » à la place) : la détection par titre a bien pris le relais pour 39 à 44 ; la 46 n'avait pas été détectée avant le plantage du jeu (le titre n'avait pas été réécrit).

Restent à rejouer : 45 (pizza, attribution 00720 par déduction, désormais appuyée par 26 et 40), 54, 29, 69.


## Relevé en direct du 22/11 (commandes 47 à 55, chapitre 6) : neuf clés confirmées, 54 câblée

Partie reprise juste avant la 46 (apworld du 21/11 18:32, donc sans les clés 47+ : tout est passé par les titres / la mémoire). Chaque livraison crée une clé **absent → 0 avec la hausse du total** (même schéma que 40–46) :

| Commande | Clé de fin | Heure | Étapes intermédiaires (1 → 0) |
|---|---|---|---|
| 47 | `c7f7cec2ba103bab8a61ed6f6c0ab7ab` | 10:33:23 | |
| 48 | `9da69a44d1ca34dea1423a3289e401a5` | 10:30:01 | |
| 49 | `7835eba730e2301ea5ec740ac4408031` | 10:35:54 | |
| 50 | `59bdb53f4fd7312fab7e833db15c54eb` | 10:38:26 | `bebf662f…` |
| 51 | `6abeef8c6fd333c4888a5a5b32f49571` | 10:41:12 | |
| 52 | `df117a304f79332d8c6deca7e83af8d0` | 10:44:48 | `f4361f5f…` |
| 53 | `1e0a0125c9203b98bdc1d22b55869fec` | 10:49:34 | |
| 55 | `a7832327bf0d3e4aabaf815b00f3f8d4` | 11:04:12 | |

Ces clés sont exactement celles lues dans les fichiers du jeu le 21/11.

**Commande 54 (« Escape the Battlefield », 2e du nom)** : comme la 39, aucune clé n'est créée à la fin. Quatre étapes passent à 1 au fil de la mission (`86dfa5bf…` 10:54:11, `4833c9b4…` 10:56:16, `435bd75c…` 10:57:16, `27e3ca68…` 11:00:16), puis les quatre retombent à 0 ensemble à 11:00:46 (hausse du total). On surveille la dernière (`27e3ca6834203342b0a8f246bac84642`, « Vaincre l'homme mystérieux ») avec la règle « valeur 0 ».

**Pourquoi 48/49/52/53 n'étaient pas « déduites »** : la déduction par titre (`implied_completed`) ne couvre que les commandes d'épisodes strictement antérieurs (et les chaînes 2→3, 54→55, 63→64→65). Les 47 à 53 sont du même épisode : la 50 ne prouve pas la 48. Elles n'étaient donc connues que par les clés (absentes de l'apworld testé) ; à l'arrivée du titre de la 55 (épisode suivant), 48, 49, 52, 53 et 54 ont été déduites d'un coup (11:03). Avec les clés de la v0.4.3, chacune est reconnue à la livraison.

**Bot crédité à tort (10:25)** : « Palier de commandes de bot atteint : 1 » est apparu ~90 s après le lancement du client (stabilité de 45 relevés), sans aucune hausse du total entre-temps. La base du bot est mémorisée dans la progression du slot, pas dans la sauvegarde du jeu : en rechargeant une sauvegarde différente, `bot = total − nobot − repair + 1000` (973) dépassait la base mémorisée (972). Correctif v0.4.3 : la base est recalée sur la sauvegarde chargée au lancement du client et dès que `total` diminue (rechargement d'une sauvegarde plus ancienne).

Constat associé : la 46 augmente `total` sans que `nobot` suive (les autres commandes font +1 total puis +1 nobot à la sortie de l'écran de résultat) ; la hausse est écartée par `bot_absorb` après la fenêtre de retenue.

## Relevé du 22/11 15:06-15:27 (commande 69, fin du jeu) et rattrapage au lancement sur sauvegarde avancée

**Commande 69** : aucune clé créée à la fin (comme 39 et 54). Étape 1 « Trouver Amélie » : `b724c5f6ef2537b48fa48f5a5dd3bbdf` absent → 1 (15:06:40) ; étape 2 : `9bf7a4f853cc38cf8409d12a2d7a3b28` absent → 1 (15:07:20). Les deux restent à 1 pendant la cinématique finale, les crédits (15:17:10) et la reprise après l'écran titre (15:24:00), puis passent à 0 à l'ouverture de l'écran de résultat (15:25:58, total 56 → 57). Câblée : dernière étape, valeur 0 exigée. Après cet écran de résultat, `63353f3a…` apparaît à 6400 et `f56d0510…` à 102 (non exploités).

**Rattrapage au lancement** (table lue à froid sur la sauvegarde de fin de jeu) : détectées par clé, à 0 : 2–10, 12, 14–16, 18–28, 30, 32–36, 38, 39, 41, 43, 44, 46–55, 58, 59, 60. Une clé de fin de commande retrouvée à 0 sur une vraie sauvegarde avancée confirme la clé : passent donc de « lues dans les fichiers » à « validées » les n°12, 16, 18–25, 27, 28, 30, 32–36, 58–60. Non détectées : 11, 13, 17, 31, 37, 45, 56, 57, 66 (commandes facultatives non faites sur cette sauvegarde, ou clé à revoir : à confirmer). Les 61–65, 67, 68, 70 ne sont pas rattrapées au lancement : leurs clés (`ORDER_MARKER_KEYS`) ne sont utilisées qu'à la création, avec la hausse du total.

**Remarque DeathLink** : « DeathLink: Sending death » est parti à 15:25:35, 23 s avant l'écran de résultat de la 69 (séquence de fin / reprise après les crédits) : à vérifier, possible fausse mort pendant la séquence finale.

## Commande 1 (22/11, 15:37) : table introuvable avant la 1re livraison
Rejouée en direct, client connecté dès la cinématique d'ouverture : « table introuvable » à chaque tentative (signatures `nobot` / `total` vues 0 fois) tant que la 1re commande n'est pas terminée. À la fin, la commande est retrouvée **par la mémoire (titre de sauvegarde)** : « Commande terminée détectée (mémoire) : Order 1 ». Décision : pas de clé pour la n°1 (la clé candidate `9c25f335…`, présente à 0 sur les 103 sauvegardes, n'est pas câblée).

## Relevé du 22/11 16:02-16:12 (commandes 27, 29, 28 ; sauvegarde de début de partie)

- **27** (livraison 16:03:10) : `46609eff…` absent → 0 à la livraison ✔ (clé inchangée). **28** (livraison 16:10:30) : `45d9222a…` absent → 0 ✔. Les deux étaient « lues dans les fichiers » : validées. Jouées dans l'ordre 27, 29, 28 : chaque commande est reconnue indépendamment.
- **11** : retrouvée à 0 au lancement (sauvegarde après la 11) ✔ validée.
- **29 (Construction : Safe House)** : aucune clé créée à 0. Étape 1 (« Build a safe house ») : `d4715a80835a34f6b8bf2a162bb230f0` absent → 1 (16:07:33). À la livraison (16:08:58) : `4ac395687f4f3036b3c27106174717d9` (« Upgrade the safe house ») absent → 1 ; à la sortie de l'écran de résultat (16:09:19) les deux passent à 0. Câblée : `4ac39568…`, valeur 0 exigée. Cette commande ne fait pas monter `nobot` (contrairement aux commandes ordinaires) : sur une sauvegarde où `total` existe, sa hausse relève de la retenue des fins spéciales.
- Table de début de partie : `total` absent (bot indisponible), comme attendu.
- Titre de la 28 vu avant sa livraison : déduction (1, 2–5, 7–9, 14, 16) ; le titre désigne la dernière commande *sélectionnée*, pas la progression.
