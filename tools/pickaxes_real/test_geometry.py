import sys, bpy, bmesh
sys.path.insert(0, "/home/user/Steal/tools/pickaxes_real")
import geometry as G
bpy.ops.wm.read_factory_settings(use_empty=True)
bm = bmesh.new()
G.build_handle(bm, mat=0); G.build_head(bm, mat=1); G.build_collar(bm, mat=2); G.build_rivets(bm, mat=2); G.build_wedge(bm, mat=3)
G.build_helix(bm, 0.06, 0.36, 36, 0.0042, 4)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
print("verts", len(bm.verts), "faces", len(bm.faces))
me = bpy.data.meshes.new("t"); bm.to_mesh(me); ob = bpy.data.objects.new("t", me); bpy.context.scene.collection.objects.link(ob)
print("dims", tuple(round(x,3) for x in ob.dimensions))
