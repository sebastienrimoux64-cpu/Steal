# Pioches réalistes (non voxel) – Blender

8 pioches modélisées en haute qualité (~10–13 k faces chacune), matériaux procéduraux Cycles :
bois, cuivre (patine), fer (rouille légère), or, diamant (cristal facetté translucide),
uranium vert (lumineux), rubis rouge, lapis-lazuli (veines + éclats dorés).

- `Pickaxes_Realistic_All.blend` : les 8 pioches alignées, éclairage studio + caméra.
- `Pickaxe_<Matière>_Realistic.blend` : une pioche par fichier (scène studio prête à rendre).
- `Previews/` : rendus.

Ouvrir dans Blender 4.x/5.x, moteur **Cycles** (matériaux à base de nœuds, verre/cristal inclus).
Les matériaux procéduraux ne s'exportent pas tels quels en FBX/GLB (il faudrait les « baker »).
Régénérer : `python tools/pickaxes_real/make_real_pickaxes.py` puis `combine.py`.
