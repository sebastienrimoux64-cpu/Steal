# Steal — Les 9 bijū en Parts Roblox

Les 9 démons à queues de Naruto, **entièrement construits en Parts cubiques** et **rigés en Motor6D** :

| # | Bijū | Forme | Particularités |
|---|------|-------|----------------|
| 1 | Shukaku | tanuki de sable | bandes bleues, touffes de sable |
| 2 | Matatabi | chat | flammes bleues Neon |
| 3 | Isobu | tortue | carapace à pointes |
| 4 | Son Goku | singe rouge | crinière blanche, cornes |
| 5 | Kokuo | cheval-dauphin | corne frontale, crinière rouge |
| 6 | Saiken | limace | antennes, queues translucides |
| 7 | Chomei | scarabée | corne, ailes mobiles |
| 8 | Gyūki | taureau-pieuvre | cornes, 8 tentacules |
| 9 | Kurama | renard | 9 queues, marques noires |

Chaque modèle contient : `Root` (PrimaryPart invisible), `Body`, `Neck`, `Head`, `Jaw`,
`Ear*`, 4 pattes (`Upper` / `Lower` / `Paw` / griffes), des queues segmentées
(`TailN_K`, chaque segment est un Motor6D enfant du précédent) et un
`AnimationController` prêt pour l'éditeur d'animations.

## Installation

### Avec Rojo
`rojo serve` puis connectez Studio (le fichier `default.project.json` est fourni).

### Sans Rojo (copier-coller)
1. `ReplicatedStorage` → dossier **Bijuu** contenant 2 ModuleScripts : `BijuuBuilder` et `BijuuAnimator` (contenu de `src/shared/`).
2. `ServerScriptService` → un **Script** avec `src/server/BuildBijuu.server.lua`.
3. `StarterPlayerScripts` → un **LocalScript** avec `src/client/AnimateBijuu.client.lua`.
4. Lancez Play : les 9 bijū apparaissent alignés dans `Workspace.Bijuu`.

### Un seul bijū, depuis la barre de commande de Studio
```lua
local B = require(game.ReplicatedStorage.Bijuu.BijuuBuilder)
B.build("Kurama", CFrame.new(0, 0, 0), workspace)
```
Noms valides : `Shukaku Matatabi Isobu SonGoku Kokuo Saiken Chomei Gyuki Kurama`.

## Animation
`BijuuAnimator` (côté client) gère respiration, queues, tête, mâchoire, marche et ailes.
Attributs du modèle : `Walking`, `Roar`, `Flying` (booléens).
Pour des animations personnalisées, utilisez l'éditeur d'animations Roblox sur les Motor6D.

## Personnaliser
Chaque bijū est une table dans `SPECS` (`BijuuBuilder.lua`) : tailles, couleurs, nombre de
queues, et une fonction `extras` pour les détails (cornes, carapace, ailes...).
