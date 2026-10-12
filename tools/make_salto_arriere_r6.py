"""Salto arrière (backflip) physique pour le personnage R6 (style Roblox).

Usage :
    python tools/make_salto_arriere_r6.py ENTREE.blend SORTIE.blend   # construit le .blend
    python tools/make_salto_arriere_r6.py --sim                       # simulation seule + diagnostics

La physique est réellement simulée (modèle 2D dans le plan sagittal, personnage = 6 solides
avec les vraies proportions de masse d'un humain) :
  * poussée : pieds collés au sol, accroupissement équilibré (le centre de masse reste au-dessus
    des pieds), extension des jambes et lancer des bras ;
  * vol : le centre de masse suit une parabole exacte (g = 28 u/s², le personnage mesure 5 u = 1,75 m) ;
    le moment cinétique total est conservé : la vitesse de rotation dépend du moment d'inertie
    calculé à chaque instant, donc la rotation accélère en position groupée et ralentit à l'ouverture ;
  * réception : les pieds se posent, le corps encaisse l'impact (décélération du centre de masse) puis se redresse.
La vitesse de rotation au décollage est calculée (bissection) pour que le personnage retombe
sur ses pieds, à peu près à la verticale, après exactement un tour.

Pour pouvoir fléchir les genoux, les jambes du R6 sont coupées en deux (cuisse / mollet) ; les
rigs d'origine (`Armature`, `__Rig`) restent dans le fichier mais ne sont plus utilisés.
"""
import math
import sys

FPS = 60
F_START, F_END = 1, 240
G = 28.0                     # gravité en unités/s² (1 u = 0,35 m)

# --------------------------------------------------------------- calendrier (s)
T_B = 1.10                   # fond de l'accroupissement
T_PUSH = 0.20                # durée de la poussée
T_TO_NOM = T_B + T_PUSH      # fin nominale de la poussée (le vrai décollage est calculé)
THETA_TO = -15.0             # inclinaison du buste au décollage (deg, <0 = vers l'arrière)
K_EXT = 1.5                  # vivacité de l'extension des jambes
T_TOEOFF, TOEOFF_H = 0.12, 0.35     # durée et hauteur du soulevé des talons
VZ_TO = 8.5                  # vitesse verticale du centre de masse au décollage (u/s)
LAMBDA_TD = 22.0             # inclinaison avant du buste au toucher (deg) : 360 - 338 de rotation
T_LAND_BOTTOM = 0.18         # fond de la réception, après le toucher
T_LAND_STAND = 0.65          # fin du redressement

# --------------------------------------------------------- modèle du corps (y, z)
# fractions de masse humaines : tronc 50 %, tête 8 %, bras 2×5 %, cuisses 2×10 %, mollets 2×6 %
M_TORSO, M_HEAD, M_ARM, M_THIGH, M_SHANK = 0.50, 0.08, 0.05, 0.10, 0.06
HIP = (0.0, -1.1)            # relatif au centre du torse
SHOULDER = (0.0, 0.6)
NECK = (0.0, 1.0)
HEAD_OFF = (0.0, 0.5)
ARM_OFF = (0.0, -0.6)
THIGH_LEN, THIGH_OFF = 0.9, (0.0, -0.4)
SHANK_LEN, SHANK_OFF = 1.0, (0.0, -0.5)
KNEE_Z = 1.0                 # hauteur du genou au repos (monde)


def rad(d):
    return math.radians(d)


def rot(a, v):
    c, s = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def hermite(wps, t):
    """Interpolation d'Hermite cubique ; wps = [(t, valeur, pente), ...] triés."""
    if t <= wps[0][0]:
        return wps[0][1]
    if t >= wps[-1][0]:
        return wps[-1][1]
    for i in range(len(wps) - 1):
        t0, v0, m0 = wps[i]
        t1, v1, m1 = wps[i + 1]
        if t <= t1:
            h = t1 - t0
            u = (t - t0) / h
            return ((2 * u**3 - 3 * u**2 + 1) * v0 + (u**3 - 2 * u**2 + u) * h * m0
                    + (-2 * u**3 + 3 * u**2) * v1 + (u**3 - u**2) * h * m1)


# pose p = (th, kn, ar, hd) : cuisse (rel. torse), flexion du genou, bras, tête  (rad)
def segments(p):
    th, kn, ar, hd = p
    sa = th + kn
    knee = add(HIP, rot(th, (0.0, -THIGH_LEN)))
    return [  # (masse, cy, cz, angle, ly, lz)
        (M_TORSO, 0.0, 0.0, 0.0, 1.0, 2.0),
        (M_HEAD, *add(NECK, rot(hd, HEAD_OFF)), hd, 1.2, 1.2),
        (2 * M_ARM, *add(SHOULDER, rot(ar, ARM_OFF)), ar, 1.0, 2.0),
        (2 * M_THIGH, *add(HIP, rot(th, THIGH_OFF)), th, 1.0, 1.0),
        (2 * M_SHANK, *add(knee, rot(sa, SHANK_OFF)), sa, 1.0, 1.0),
    ]


def com_of(segs):
    return (sum(s[0] * s[1] for s in segs), sum(s[0] * s[2] for s in segs))


def inertia_of(segs, com):
    return sum(s[0] * (s[4] ** 2 + s[5] ** 2) / 12 + s[0] * ((s[1] - com[0]) ** 2 + (s[2] - com[1]) ** 2)
               for s in segs)


def corners_of(segs):
    pts = []
    for m, cy, cz, ang, ly, lz in segs:
        for sy in (-ly / 2, ly / 2):
            for sz in (-lz / 2, lz / 2):
                r = rot(ang, (sy, sz))
                pts.append((cy + r[0], cz + r[1]))
    return pts


def foot_of(p):
    th, kn = p[0], p[1]
    knee = add(HIP, rot(th, (0.0, -THIGH_LEN)))
    return add(knee, rot(th + kn, (0.0, -SHANK_LEN)))


def h_rel(pose_fn, t, h=1 / 2400):
    """Moment cinétique des membres par rapport au torse (relatif au centre de masse)."""
    s0, sm, s1 = segments(pose_fn(t - h)), segments(pose_fn(t)), segments(pose_fn(t + h))
    c0, cm, c1 = com_of(s0), com_of(sm), com_of(s1)
    tot = 0.0
    for a, b, m in zip(s0, s1, sm):
        ry, rz = m[1] - cm[0], m[2] - cm[1]
        vy = ((b[1] - c1[0]) - (a[1] - c0[0])) / (2 * h)
        vz = ((b[2] - c1[1]) - (a[2] - c0[1])) / (2 * h)
        inert = m[0] * (m[4] ** 2 + m[5] ** 2) / 12
        tot += m[0] * (ry * vz - rz * vy) + inert * (b[3] - a[3]) / (2 * h)
    return tot


# ---------------------------------------------------------- phase 1 : sol (poussée)
def ground1(t, w_to, k=1.0):
    """Angles (theta, phi cuisse monde, psi mollet monde, bras, tête) avant le décollage."""
    tb, tto = T_B, T_TO_NOM
    th = hermite([(0, 0, 0), (0.5, 0, 0), (tb, rad(34), 0), (tto, rad(THETA_TO), w_to)], t)
    phi = hermite([(0, 0, 0), (0.5, 0, 0), (tb, rad(-85), 0), (tto, 0, rad(500) * k)], t)
    psi = hermite([(0, 0, 0), (0.5, 0, 0), (tb, rad(32), 0), (tto, 0, rad(-80) * k)], t)
    ar = hermite([(0, 0, 0), (0.5, 0, 0), (tb, rad(62), 0), (tto, rad(-150), rad(-600))], t)
    hd = hermite([(0, 0, 0), (0.5, 0, 0), (tb, rad(-22), 0), (tto, rad(-12), 0)], t)
    breath = rad(2) * math.sin(2 * math.pi * 0.8 * t) * (1 - smooth(0.3, 0.5, t))
    return th, phi, psi, ar + breath, hd + breath * 0.5


def relative(theta, phi, psi, ar, hd):
    return (phi - theta, psi - phi, ar, hd)


def root_from_pin(theta, p, psi_world, y_pin, lift=0.0):
    """Position du centre du torse quand le pied (centre de la semelle) est collé en y_pin.
    La semelle repose sur son arête la plus basse (z = 0)."""
    fr = rot(theta, foot_of(p))
    return (y_pin - fr[0], 0.5 * abs(math.sin(psi_world)) + lift - fr[1])


def com_world(P, theta, p):
    cl = com_of(segments(p))
    r = rot(theta, cl)
    return (P[0] + r[0], P[1] + r[1])


def ground_state(t, w_to, y_pin=0.0, k=1.0):
    th, phi, psi, ar, hd = ground1(t, w_to, k)
    p = relative(th, phi, psi, ar, hd)
    # toe-off : les talons se soulèvent dans les derniers instants de la poussée
    u = max(0.0, min(1.0, (t - (T_TO_NOM - T_TOEOFF)) / T_TOEOFF))
    P = root_from_pin(th, p, psi, y_pin, TOEOFF_H * u * u)
    return th, P, p


# -------------------------------------------------------------------- phase 2 : vol
def flight_pose_fn(p0):
    th0, kn0, ar0, hd0 = p0
    wps = {
        "th": [(0, th0, 0), (0.10, th0, 0), (0.28, rad(-100), 0), (0.46, rad(-100), 0),
               (0.66, rad(-55), 0), (2.0, rad(-55), 0)],
        "kn": [(0, kn0, 0), (0.10, kn0, 0), (0.28, rad(115), 0), (0.46, rad(115), 0),
               (0.66, rad(30), 0), (2.0, rad(30), 0)],
        "ar": [(0, ar0, 0), (0.10, ar0 + rad(25), 0), (0.28, rad(-75), 0), (0.46, rad(-75), 0),
               (0.66, rad(-30), 0), (2.0, rad(-30), 0)],
        "hd": [(0, hd0, 0), (0.10, hd0, 0), (0.28, rad(18), 0), (0.46, rad(18), 0),
               (0.66, rad(-15), 0), (2.0, rad(-15), 0)],
    }

    def pose(tau):
        return tuple(hermite(wps[k], tau) for k in ("th", "kn", "ar", "hd"))
    return pose


def find_takeoff(w_to, k):
    """Instant où le sol cesse de pousser : accélération verticale du centre de masse = -g
    (au-delà, la cinématique demanderait au sol de tirer le pied vers le bas)."""
    e = 1 / 1200

    def cz(t):
        th, P, p = ground_state(t, w_to, 0.0, k)
        return com_world(P, th, p)[1]
    t = T_B + 0.04
    while t < T_TO_NOM:
        az = (cz(t + e) - 2 * cz(t) + cz(t - e)) / (e * e)
        vz = (cz(t + e) - cz(t - e)) / (2 * e)
        if vz > 1.0 and az <= -G:
            return t
        t += e
    return T_TO_NOM


def takeoff_velocity(w_to, k, t_to):
    e = 1 / 2400
    th1, P1, p1 = ground_state(t_to, w_to, 0.0, k)
    th0, P0, p0 = ground_state(t_to - e, w_to, 0.0, k)
    c1, c0 = com_world(P1, th1, p1), com_world(P0, th0, p0)
    omega = (th1 - th0) / e
    return c1, [(c1[0] - c0[0]) / e, (c1[1] - c0[1]) / e], omega


def simulate_flight(w_nom, dt=1 / 1200):
    k = K_EXT
    t_to = find_takeoff(w_nom, k)
    th_to, P_to, p_to = ground_state(t_to, w_nom, 0.0, k)
    c1, vel, w_to = takeoff_velocity(w_nom, k, t_to)
    pose = flight_pose_fn(p_to)
    segs0 = segments(p_to)
    cl0 = com_of(segs0)
    L = inertia_of(segs0, cl0) * w_to + h_rel(lambda tau: pose(max(tau, 0.0)), 0.0)

    com = [c1[0], c1[1]]
    theta = th_to
    out = []
    tau = 0.0
    td = None
    while tau < 1.6:
        p = pose(tau)
        segs = segments(p)
        cl = com_of(segs)
        I = inertia_of(segs, cl)
        w = (L - h_rel(pose, tau)) / I
        rc = rot(theta, cl)
        P = (com[0] - rc[0], com[1] - rc[1])
        low = min(P[1] + rot(theta, c)[1] for c in corners_of(segs))
        out.append((tau, theta, P, p, w, low, tuple(com), tuple(vel)))
        if tau > 0.3 and vel[1] < 0 and low <= 0:
            td = len(out) - 1
            break
        # intégration
        theta += w * dt
        com[0] += vel[0] * dt
        com[1] += vel[1] * dt - 0.5 * G * dt * dt
        vel[1] -= G * dt
        tau += dt
    return out, td, th_to, P_to, p_to, L, k, t_to, w_to


def solve_flight():
    lo, hi = -16.0, -3.0
    target = -2 * math.pi + rad(LAMBDA_TD)

    def err(w):
        out, td, *_ = simulate_flight(w)
        if td is None:
            return None
        return out[td][1] - target
    elo, ehi = err(lo), err(hi)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        em = err(mid)
        if em is None:
            hi = mid
            continue
        if (elo is None) or (em > 0) == (elo > 0):
            lo, elo = mid, em
        else:
            hi, ehi = mid, em
    w = 0.5 * (lo + hi)
    return w, simulate_flight(w)


# --------------------------------------------------------------- phase 3 : réception
def landing_curves(start, s_phi):
    lam0, phi0, psi0, ar0, hd0 = start
    tb, ts = T_LAND_BOTTOM, T_LAND_STAND
    return {
        "lam": [(0, lam0, 0), (tb, rad(40), 0), (ts, 0, 0)],
        "phi": [(0, phi0, s_phi), (tb, rad(-70), 0), (ts, 0, 0)],
        "psi": [(0, psi0, 0.3 * s_phi), (tb, rad(20), 0), (ts, 0, 0)],
        "ar": [(0, ar0, 0), (tb, rad(-40), 0), (ts + 0.15, 0, 0)],
        "hd": [(0, hd0, 0), (tb, rad(-25), 0), (ts, 0, 0)],
    }


def landing_state(curves, tau, y_pin):
    lam = hermite(curves["lam"], tau)
    phi = hermite(curves["phi"], tau)
    psi = hermite(curves["psi"], tau)
    ar = hermite(curves["ar"], tau)
    hd = hermite(curves["hd"], tau)
    theta = -2 * math.pi + lam
    p = relative(theta, phi, psi, ar, hd)
    P = root_from_pin(theta, p, psi, y_pin)
    return theta, P, p


# ------------------------------------------------------------------- orchestration
class Salto:
    def __init__(self):
        self.w_nom, (self.fl, self.td, self.th_to, self.P_to, self.p_to, self.L, self.k, self.t_to, self.w_to) = solve_flight()
        tau, theta, P, p, w, low, com, vel = self.fl[self.td]
        self.t_ld = self.t_to + tau
        self.theta_td, self.P_td, self.p_td = theta, P, p
        self.vel_td = vel
        segs = segments(p)
        # pied pincé à l'endroit du toucher (centre de la semelle)
        fr = rot(theta, foot_of(p))
        self.y_pin = P[0] + fr[0]
        lam0 = theta + 2 * math.pi
        phi0 = lam0 + p[0]
        psi0 = phi0 + p[1]
        self.start = (lam0, phi0, psi0, p[2], p[3])
        # pente initiale de flexion pour que le centre de masse garde sa vitesse de chute au contact
        v_target = vel[1]

        def vz_of(s):
            cv = landing_curves(self.start, s)
            e = 1 / 2400
            t1, P1, p1 = landing_state(cv, e, self.y_pin)
            t0, P0, p0_ = landing_state(cv, 0.0, self.y_pin)
            return (com_world(P1, t1, p1)[1] - com_world(P0, t0, p0_)[1]) / e
        lo, hi = -40.0, 0.0
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            if vz_of(mid) > v_target:
                hi = mid
            else:
                lo = mid
        self.s_phi = 0.5 * (lo + hi)
        self.land = landing_curves(self.start, self.s_phi)

    def state(self, t):
        """Retourne dict : theta (rad, déroulé), P (y,z), p (th,kn,ar,hd), phase."""
        if t < self.t_to:
            th, P, p = ground_state(t, self.w_nom, 0.0, self.k)
            return {"theta": th, "P": P, "p": p, "phase": "sol", "tau": 0.0}
        if t < self.t_ld:
            tau = t - self.t_to
            i = min(len(self.fl) - 1, int(round(tau * 1200)))
            r = self.fl[i]
            return {"theta": r[1], "P": r[2], "p": r[3], "phase": "vol", "tau": tau}
        th, P, p = landing_state(self.land, t - self.t_ld, self.y_pin)
        return {"theta": th, "P": P, "p": p, "phase": "reception", "tau": t - self.t_ld}


def report(S):
    print(f"omega au decollage      : {math.degrees(S.w_to):7.1f} deg/s  (decollage a t={S.t_to:.3f} s)")
    com_to = com_world(S.P_to, S.th_to, S.p_to)
    r_to = S.fl[0]
    print(f"vitesse CM decollage    : vy={r_to[7][0]:5.2f} vz={r_to[7][1]:5.2f} u/s")
    apex = max(r[6][1] for r in S.fl)
    print(f"CM : decollage z={com_to[1]:.2f}, sommet z={apex:.2f} (saut de {apex - com_to[1]:.2f} u = {0.35 * (apex - com_to[1]):.2f} m)")
    print(f"temps de vol            : {S.t_ld - S.t_to:.3f} s ; toucher a t={S.t_ld:.3f} s (image {F_START + round(S.t_ld * FPS)})")
    print(f"rotation au toucher     : {-math.degrees(S.theta_td):.1f} deg ; vitesse de chute CM vz={S.vel_td[1]:.2f}")
    ws = [math.degrees(r[4]) for r in S.fl]
    print(f"vitesse de rotation     : min {min(ws):.0f} / max {max(ws):.0f} deg/s (groupe -> plus rapide)")
    # équilibre accroupi et pénétration du sol
    th, P, p = ground_state(T_B, S.w_nom, 0.0, S.k)
    cm = com_world(P, th, p)
    print(f"accroupi : CM y={cm[0]:.2f} (pied en 0, semelle -0.5..0.5), CM z={cm[1]:.2f}, hanche... ")
    worst = 0.0
    for f in range(F_START, F_END + 1):
        st = S.state((f - F_START) / FPS)
        segs = segments(st["p"])
        low = min(st["P"][1] + rot(st["theta"], c)[1] for c in corners_of(segs))
        worst = min(worst, low)
    print(f"penetration max du sol  : {worst:.3f} u")


# ======================================================================= Blender
PARTS = ["Head", "Torso", "Left Arm", "Right Arm"]


def new_empty(name, loc, parent=None, size=0.4):
    import bpy
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = size
    e.location = loc
    e.rotation_mode = "XYZ"
    bpy.context.scene.collection.objects.link(e)
    if parent is not None:
        bpy.context.view_layer.update()
        e.parent = parent
        e.matrix_parent_inverse = parent.matrix_world.inverted()
    return e


def split_leg(name):
    """Coupe une jambe R6 en deux au genou (z = 1) -> (cuisse, mollet), deux objets."""
    import bmesh
    import bpy
    src = bpy.data.objects[name]
    halves = []
    for upper in (True, False):
        me = src.data.copy()
        me.name = f"{name}_{'cuisse' if upper else 'mollet'}"
        bm = bmesh.new()
        bm.from_mesh(me)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        # le maillage Roblox est tourné de 90° : la hauteur monde z est l'axe local y
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 1.0, 0), plane_no=(0, 1, 0),
                               clear_inner=upper, clear_outer=not upper)
        cut = [e for e in bm.edges if all(abs(v.co.y - 1.0) < 1e-5 for v in e.verts)]
        bmesh.ops.holes_fill(bm, edges=cut, sides=64)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(me.name, me)
        ob.matrix_basis = src.matrix_basis.copy()
        bpy.context.scene.collection.objects.link(ob)
        halves.append(ob)
    src.hide_viewport = True
    src.hide_render = True
    for c in src.constraints:
        c.mute = True
    return halves


def checker_material(name, c1, c2, scale):
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.9
    coord = nt.nodes.new("ShaderNodeTexCoord")
    tex = nt.nodes.new("ShaderNodeTexChecker")
    tex.inputs["Color1"].default_value = (*c1, 1)
    tex.inputs["Color2"].default_value = (*c2, 1)
    tex.inputs["Scale"].default_value = scale
    nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def build(src, dst, S):
    import bpy
    from mathutils import Euler
    bpy.ops.wm.open_mainfile(filepath=src)
    sc = bpy.context.scene

    # 1) squelette d'empties : corps, tête, épaules, hanches, genoux (pivots exacts)
    root = new_empty("Salto_Root", (0, 0, 3.0), size=0.8)
    head = new_empty("Salto_Tete_Pivot", (0, 0, 4.0), root)
    arm_l = new_empty("Salto_BrasG_Pivot", (-1.5, 0, 3.6), root)
    arm_r = new_empty("Salto_BrasD_Pivot", (1.5, 0, 3.6), root)
    hip_l = new_empty("Salto_HancheG_Pivot", (-0.5, 0, 1.9), root)
    hip_r = new_empty("Salto_HancheD_Pivot", (0.5, 0, 1.9), root)
    knee_l = new_empty("Salto_GenouG_Pivot", (-0.5, 0, KNEE_Z), hip_l)
    knee_r = new_empty("Salto_GenouD_Pivot", (0.5, 0, KNEE_Z), hip_r)
    bpy.context.view_layer.update()

    thigh_l, shank_l = split_leg("Left Leg")
    thigh_r, shank_r = split_leg("Right Leg")
    attach = {"Torso": root, "Head": head, "Left Arm": arm_l, "Right Arm": arm_r}
    objs = {k: bpy.data.objects[k] for k in attach}
    objs.update({thigh_l.name: thigh_l, shank_l.name: shank_l, thigh_r.name: thigh_r, shank_r.name: shank_r})
    attach.update({thigh_l.name: hip_l, shank_l.name: knee_l, thigh_r.name: hip_r, shank_r.name: knee_r})
    for name, ob in objs.items():
        for c in ob.constraints:
            if c.type == "CHILD_OF":
                c.mute = True
        ob.parent = attach[name]
        ob.matrix_parent_inverse = attach[name].matrix_world.inverted()
    for n in ("Armature", "__Rig", "__RigMeta"):
        if n in bpy.data.objects:
            bpy.data.objects[n].hide_viewport = True
            bpy.data.objects[n].hide_render = True

    # 2) décor : sol à damier (1 case = 1 u = 35 cm), soleil, ciel
    ground = bpy.data.meshes.new("Sol")
    ground.from_pydata([(-150, -150, 0), (150, -150, 0), (150, 150, 0), (-150, 150, 0)], [], [(0, 1, 2, 3)])
    ground.materials.append(checker_material("Sol_damier", (0.34, 0.46, 0.27), (0.29, 0.40, 0.23), 1.0))
    gob = bpy.data.objects.new("Sol", ground)
    sc.collection.objects.link(gob)
    sun_data = bpy.data.lights.new("Soleil", "SUN")
    sun_data.energy = 3.5
    sun_data.angle = rad(3)
    sun = bpy.data.objects.new("Soleil", sun_data)
    sun.rotation_euler = (rad(52), rad(12), rad(-35))
    sc.collection.objects.link(sun)
    world = sc.world or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.45, 0.62, 0.85, 1)
    bg.inputs["Strength"].default_value = 0.9

    # 3) caméras : profil fixe (par défaut) et trois-quarts
    cam_data = bpy.data.cameras.new("Camera_Profil")
    cam_data.lens = 35
    cam = bpy.data.objects.new("Camera_Profil", cam_data)
    cam.location = (21.0, 1.0, 3.7)
    cam.rotation_euler = (rad(90), 0, rad(90))
    sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = new_empty("Camera_Cible", (0, 1.0, 3.6), size=0.3)
    cam2_data = bpy.data.cameras.new("Camera_TroisQuarts")
    cam2_data.lens = 40
    cam2 = bpy.data.objects.new("Camera_TroisQuarts", cam2_data)
    cam2.location = (-15.0, -17.0, 6.5)
    tr = cam2.constraints.new("TRACK_TO")
    tr.target = tgt
    tr.track_axis = "TRACK_NEGATIVE_Z"
    tr.up_axis = "UP_Y"
    sc.collection.objects.link(cam2)

    # 4) images clés (une par image, interpolation linéaire : la physique est déjà échantillonnée)
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = F_START, F_END
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.view_settings.view_transform = "Standard"
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    for f in range(F_START, F_END + 1):
        t = (f - F_START) / FPS
        st = S.state(t)
        th, kn, ar, hd = st["p"]
        root.location = (0.0, st["P"][0], st["P"][1])
        root.rotation_euler = Euler((st["theta"], 0, 0))
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
        # bras écartés : serrés en position groupée, ouverts pour la réception
        if st["phase"] == "vol":
            sp = rad(8) + rad(26) * smooth(0.46, 0.66, st["tau"])
        elif st["phase"] == "reception":
            sp = rad(34) * (1 - smooth(0.1, 0.7, st["tau"]))
        else:
            sp = rad(6) * smooth(0.5, 1.1, t) + rad(2)
        head.rotation_euler = Euler((hd, 0, 0))
        arm_l.rotation_euler = Euler((ar, sp, 0))
        arm_r.rotation_euler = Euler((ar, -sp, 0))
        hip_l.rotation_euler = Euler((th, 0, 0))
        hip_r.rotation_euler = Euler((th, 0, 0))
        knee_l.rotation_euler = Euler((kn, 0, 0))
        knee_r.rotation_euler = Euler((kn, 0, 0))
        for e in (head, arm_l, arm_r, hip_l, hip_r, knee_l, knee_r):
            e.keyframe_insert("rotation_euler", frame=f)
    sc.frame_set(F_START)
    bpy.ops.wm.save_as_mainfile(filepath=dst)
    print(f"OK: {dst}  (decollage t={S.t_to:.2f}s, toucher t={S.t_ld:.2f}s = image {F_START + round(S.t_ld * FPS)})")


if __name__ == "__main__":
    if "--sim" in sys.argv:
        S = Salto()
        report(S)
        for f in (1, 60, 66, 70, 78, 84, 90, 100, 110, 120, 130, 140, 150, 160, 180, 220):
            st = S.state((f - F_START) / FPS)
            cm = com_world(st["P"], st["theta"], st["p"])
            print(f"f{f:3d} {st['phase']:9s} theta={math.degrees(st['theta']):8.1f} CM=({cm[0]:5.2f},{cm[1]:5.2f}) "
                  f"th={math.degrees(st['p'][0]):6.1f} kn={math.degrees(st['p'][1]):6.1f}")
        sys.exit(0)
    S = Salto()
    report(S)
    build(sys.argv[-2], sys.argv[-1], S)
