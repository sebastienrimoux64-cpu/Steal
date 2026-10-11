=====================================================================
  HOME BUILDER KIT  v1.0   —   Pack d'assets 3D "Maison" modulaire
=====================================================================
89 assets low-poly propres, à l'échelle réelle (mètres), prêts pour
Blender, Unity, Unreal, Godot, ou tout moteur lisant FBX / glTF.
Éléments de construction modulaires + mobilier + déco + extérieur.

---------------------------------------------------------------------
CONTENU DU PACK
---------------------------------------------------------------------
HomeBuilderKit_Library.blend   Tous les assets rangés par catégories
                               (Blender 4.2+). Marqués comme "Assets" :
                               ils apparaissent dans l'Asset Browser.
Showcase_House.blend           La maison de démonstration assemblée
                               avec les pièces du pack (modifiable).
Scenes/Showroom.blend / .glb   Le SHOWROOM : les 89 assets alignés par
                               catégorie, sur socles, avec étiquettes.
Scenes/Example_Place.blend/.glb  La scène d'EXEMPLE : maison + jardin
                               (extérieur), maison en coupe (intérieur),
                               salon / salle à manger / cuisine.
Scenes/Renders/                Images des deux scènes (vues larges + détails)
Viewer/index.html              Visualiseur 3D web autonome (voir ci-dessous)
Individual_Assets/FBX/<cat>/   Un fichier .fbx par asset
Individual_Assets/GLB/<cat>/   Un fichier .glb par asset (glTF binaire)
Previews/                      Images de présentation
ASSET_LIST.csv                 Liste : dimensions, triangles, matériaux
LICENSE.txt                    Licence d'utilisation

---------------------------------------------------------------------
SCÈNES DE PRÉSENTATION & VISUALISEUR WEB
---------------------------------------------------------------------
Les fichiers Scenes/*.glb sont prévus pour la prévisualisation 3D sur
un site web (glTF binaire, léger : Showroom ~7 Mo, Example_Place ~2 Mo).
Viewer/index.html les affiche avec <model-viewer> (Google, licence
Apache 2.0, fichier model-viewer.min.js inclus) : rotation, zoom, boutons
de points de vue (vue d'ensemble, une par catégorie / une par zone).
Pour tester en local, servez le dossier du pack, par exemple :
    python -m http.server 8000     (puis ouvrir /Viewer/index.html)
(les navigateurs bloquent le chargement de .glb depuis file://)
Hébergement : copiez les dossiers Viewer/ et Scenes/ côte à côte sur votre
site, ou intégrez la balise <model-viewer src="Scenes/Showroom.glb"> dans
votre page. ?scene=place ouvre directement la scène d'exemple.

---------------------------------------------------------------------
CATÉGORIES (89 assets)
---------------------------------------------------------------------
01 Structure        12   Murs modulaires 2 m (plein, porte, fenêtre,
                         arche, briques, bardage), poteau d'angle...
02 Sols & toits     11   Parquet, carrelage, plafond, fondation, toit
                         (tuiles / ardoise), faîtage, pignon, cheminée,
                         lucarne
03 Portes & fenêtres 9   Portes, cadre, fenêtres, volets, escaliers,
                         garde-corps
04 Salon            13   Canapés, fauteuil, chaises, tables, TV,
                         bibliothèque, buffet, cheminée
05 Chambre           7   Lits, table de nuit, armoire, commode, bureau
06 Cuisine           8   Meubles bas/hauts, évier, cuisinière, hotte,
                         réfrigérateur
07 Salle de bain     4   Baignoire, WC, lavabo, armoire à miroir
08 Éclairage & déco 19   Lampes, luminaires, tapis, cadres, miroirs,
                         plantes, rideaux, horloge...
09 Extérieur         6   Clôture, portillon, colonne, boîte aux lettres,
                         banc, dalle de chemin

---------------------------------------------------------------------
CONVENTIONS TECHNIQUES
---------------------------------------------------------------------
* Unité : 1 unité = 1 mètre. Axe Z vers le haut (FBX : Y-up à l'import
  automatique dans Unity/Unreal, glTF : Y-up standard).
* Grille modulaire : 2 m. Murs : 2 m de large, 2,8 m de haut,
  0,20 m d'épaisseur. Planchers : dalles de 2 m x 2 m.
* Pivot : au sol, au centre de la pièce (murs : centre bas de l'épaisseur).
  Objets muraux : pivot en bas au centre, face vers -Y.
* Orientation : l'avant des meubles regarde vers -Y. L'extérieur
  des murs est du côté -Y.
* Matériaux : PBR unis (Principled BSDF) — base color, roughness,
  metallic ; pas de texture externe à gérer. Verre = alpha 25 %.
  Les ampoules utilisent une émission.
* UV : projection cubique en mètres (densité de texels constante),
  prêts à recevoir vos propres textures tileables.
* Maillages propres : arêtes chanfreinées, ombrage lissé par angle,
  aucune face coplanaire (pas de z-fighting), 81 000 triangles pour
  les 89 assets (moyenne ~900 par asset).

---------------------------------------------------------------------
ASSEMBLER UNE MAISON (exemple : 6 m x 8 m)
---------------------------------------------------------------------
1. Posez des "Foundation_2m" et "Floor_Wood_2m" sur la grille de 2 m.
2. Placez les murs le long des lignes de grille : "Wall_*" avec
   rotation 0° (mur sud), 180° (nord), -90° (ouest), +90° (est).
   Mettez un "Wall_Corner_Post" à chaque angle.
3. Insérez portes et fenêtres : "Door_Frame_1m" + "Door_Front",
   "Window_Casement_*" (posée à Z = 0,9 m dans "Wall_Window_*").
4. Toit : "Roof_Slope_Tile_2m" (égout au pivot, pente 35°, portée 3 m)
   sur chaque module, "Roof_Ridge_2m" au faîtage,
   "Roof_Gable_Triangle_6m" aux deux pignons.
5. Meublez avec les catégories 04 à 08. Ouvrez Showcase_House.blend
   pour un exemple complet.

---------------------------------------------------------------------
UTILISATION DANS BLENDER
---------------------------------------------------------------------
* Ouvrez HomeBuilderKit_Library.blend, ou ajoutez le dossier du pack
  comme bibliothèque d'assets (Préférences > Chemins des fichiers >
  Bibliothèques d'assets) puis glissez-déposez depuis l'Asset Browser.
* Pour un seul objet : File > Import > FBX / glTF, ou
  File > Link/Append depuis HomeBuilderKit_Library.blend.

---------------------------------------------------------------------
COMPATIBILITÉ
---------------------------------------------------------------------
Blender 4.2+ (testé 5.2), Unity, Unreal Engine, Godot 4, et tout
logiciel lisant FBX ou glTF 2.0.

Support : voir la page du produit.
