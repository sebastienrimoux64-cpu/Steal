# Katanas réalistes (non voxel) – Blender

4 katanas détaillés (~11 700 faces) : bois (bokken), fer (acier avec hamon ondulé modélisé), or, diamant (lame cristal facetée).
Lame à arête (shinogi) et kissaki, habaki, tsuba avec seppa, manche (tsuka) avec tsuka-ito en rubans, fuchi et kashira.

- `Katanas_Realistic_All.blend` : les 4 ensemble, éclairage studio + caméra.
- `Katana_<Matière>_Realistic.blend` : un katana par fichier (studio inclus).
- `Previews/` : rendus.

Ouvrir dans Blender avec le moteur **Cycles** (matériaux procéduraux ; non exportables tels quels en FBX/GLB sans baking).
Régénérer : `python tools/katanas/make_real_katanas.py` puis `python tools/katanas/combine_katanas.py`.
