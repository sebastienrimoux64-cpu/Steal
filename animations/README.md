# Animations « idle » R6 — une par personnage

Chaque fichier est **votre rig R6IKFIX, inchangé** (mêmes objets, mêmes contraintes, mêmes parties du corps entières),
avec **une seule action** ajoutée sur l'armature de contrôle `Armature`. L'armature `__Rig` suit par ses contraintes,
comme d'habitude. Rien n'est coupé : seuls les os de contrôle bougent.

| Fichier | Personnage | Durée | Esprit |
|---|---|---|---|
| `Idle_Tanjiro.blend` | Tanjiro | 6 s | **Modeste** : posture droite, mains jointes devant, tête légèrement baissée, petite révérence polie, regard attentif sur le côté |
| `Idle_Nezuko.blend`  | Nezuko  | 4 s | **Timide** : épaules rentrées, bras serrés contre la poitrine, tête baissée et penchée, genoux qui se touchent, coups d'œil furtifs puis regard détourné, un pied qui se frotte |
| `Idle_Inosuke.blend` | Inosuke | 2 s | **Excité, sauvage** : rebond permanent, torse penché en avant façon bête, tête qui claque d'un côté à l'autre, bras écartés en griffes, coups de poing dans le vide, piétinements |
| `Idle_Muzan.blend`   | Muzan   | 8 s | **Froid, arrogant** : presque immobile, menton levé, épaules en arrière, une main devant à la taille, respiration très lente, regard qui balaie, puis inclinaison de tête menaçante |
| `Idle_Gon.blend`      | Gon      | 4 s  | **Joyeux, énergique, curieux** : petits rebonds sur la pointe des pieds, bras qui se balancent, tête qui regarde partout, poing levé de joie |
| `Idle_Killua.blend`   | Killua   | 6 s  | **Cool, nonchalant, félin** : mains dans les poches, affalé sur une jambe, pied qui tape, tête penchée, regard félin soudain, étirement de nuque |
| `Idle_Kurapika.blend` | Kurapika | 6 s  | **Sérieux, maître de lui, en alerte** : très droit, bras collés, poing droit avancé, balayage lent du regard, éclair de tension contenue |
| `Idle_Leorio.blend`   | Leorio   | 5 s  | **Fier, fanfaron, soupe au lait** : poings sur les hanches, torse bombé, menton levé, gros éclat de rire, rajuste ses lunettes |
| `Idle_Meruem.blend`   | Meruem   | 10 s | **Roi souverain, puissant et curieux** : torse bombé, respiration lente et profonde, pose pensive, tête qui s'incline |
| `Idle_Hisoka.blend`   | Hisoka   | 6 s  | **Joueur, dérangeant, séducteur** : balancement de hanches, main à la hanche, carte près du menton claquée d'un geste vif, tête penchée, petit rire |

Aperçus (vue 3/4 + vue de côté, couleurs de test seulement) : `previews/Idle_<Nom>.gif`.

## Techniques (une action par fichier)

| Fichier | Technique | Durée | Contenu |
|---|---|---|---|
| `Jutsu_Katon_GoukakyuuNoJutsu.blend` | **Katon : Grande boule de feu** (Uchiha) | 4,4 s | Position prête (jambes écartées, fléchies) → **6 mains rapides** (Serpent, Bélier, Singe, Sanglier, Cheval, Tigre) → **grande inspiration** (buste en arrière, tête levée) → **souffle explosif** (buste projeté en avant, mains devant la bouche, recul du pied droit) → maintien du jet → retour à la position prête. Début = fin : s'enchaîne ou boucle. |

L'aperçu `previews/Jutsu_Katon_GoukakyuuNoJutsu.gif` montre une boule de feu **ajoutée uniquement dans l'aperçu** pour visualiser le timing ;
le `.blend` ne contient que l'animation du personnage (les effets de feu ne s'exportent pas avec les os).
Le souffle part à `t = 2,40 s` (image 144 à 60 fps).

## Détails techniques
- 60 images/seconde (comme votre fichier), image de début 0. Les animations **bouclent parfaitement** (dernière image = première).
- Os animés : `Torso`, `Head`, `LeftUpperArm`, `RightUpperArm`, `LeftLeg-IKTarget`, `RightLeg-IKTarget`.
  Les pieds restent posés grâce à l'IK (on ne déplace que les cibles). `MasterControl` n'est pas touché.
- Dans votre rig, `Head` copie la rotation de `MasterControl` : la tête garde donc son orientation quand le torse penche.
  Les rotations de tête sont réglées en tenant compte de ça.
- **Pas de vibration** : plus aucun tremblement rapide. Les jambes IK de votre rig sont exactement tendues au repos, donc le moindre mouvement
  vertical du torse (même 1-2 cm) plie le genou de 10 à 20° d'un coup : les idles calmes ne bougent donc jamais le torse en hauteur
  (la respiration passe par l'inclinaison du torse et des bras), et les idles « accroupis » (Gon, Inosuke, Katon) restent toujours fléchis.
  `tools/anim/jitter_check.py` mesure la part de mouvement rapide (> 3 Hz) de chaque animation.
- Action : `Idle_<Nom>` ou `Jutsu_<Nom>` (sur `Armature`). Pour l'exporter vers Roblox, utilisez votre exporteur habituel comme pour une action normale.

## Ajouter un personnage
Tout est dans `tools/anim/r6_idles.py` : une fonction `pose(t)` par personnage (posture, rythme, tics), puis une ligne dans
le registre `CHARACTERS`. Ensuite :
```
python tools/anim/r6_idles.py tools/anim/source/R6IKFIX.blend animations           # tous
python tools/anim/r6_idles.py tools/anim/source/R6IKFIX.blend animations Tanjiro   # un seul
python tools/anim/preview.py animations/Idle_Tanjiro.blend animations/previews/Idle_Tanjiro.gif 10 260   # aperçu GIF
python tools/anim/r6_jutsu.py tools/anim/source/R6IKFIX.blend animations                  # techniques (Katon...)
python tools/anim/jitter_check.py animations/Idle_Tanjiro.blend                              # mesure des vibrations
```
(nécessite le module Python `bpy` : `pip install bpy`.)
