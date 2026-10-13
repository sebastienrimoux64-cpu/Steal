"""Animation « Shidou Ryusei » (Blue Lock) sur le personnage R6.

Usage :
    python tools/make_shidou_r6.py ENTREE.blend SORTIE.blend   # construit le .blend
    python tools/make_shidou_r6.py --sim                       # simulation seule + diagnostics

Scène : Shidou guette dans la surface, courbé, tendu comme un prédateur. Un centre arrive en cloche. Il
s'élance et reprend le ballon en CISEAU RETOURNÉ (finition acrobatique, frappe puissante type « Drive
Shot »), le tir file dans la lucarne dans un ralenti dramatique, puis il s'écrase sur le dos et se met à
rire comme un fou avant de se relever, bras écartés, tête renversée : l'extase du but.

La physique est simulée (modèle 2D sagittal, 8 solides avec des fractions de masse humaines, jambes et
bras indépendants) : le centre de masse suit une parabole exacte, le moment cinétique est conservé en vol
(la vitesse de rotation est recalculée à chaque instant à partir du moment d'inertie), et la vitesse de
rotation au décollage est calculée pour que le pied frappeur rencontre le ballon à l'instant de la
frappe. Le ballon suit lui aussi une balistique exacte (g = 28 u/s², 1 u = 35 cm).
"""
import math
import sys

FPS = 60
G = 28.0                      # gravité (u/s²)

# ---------------------------------------------------------------- calendrier (s de simulation)
T_B = 1.15                    # fond de l'accroupissement (charge)
T_PUSH = 0.20
T_TO_NOM = T_B + T_PUSH
TAU_IMP = 0.50                # frappe, en secondes après le décollage
THETA_IMP = -96.0            # inclinaison du buste à la frappe (deg ; -90 = à plat sur le dos)
T_END = 6.2                   # fin de la scène (s de simulation)
K_EXT = 1.5
THETA_B, THETA_TO = 26.0, -6.0     # inclinaison du buste : fond de la charge / fin de la poussée (deg)
T_TOEOFF, TOEOFF_H = 0.12, 0.35

# ---------------------------------------------------------------- modèle du corps (y, z)
M_TORSO, M_HEAD, M_ARM, M_THIGH, M_SHANK = 0.50, 0.08, 0.05, 0.10, 0.06   # par segment (bras/jambes ×2)
HIP = (0.0, -1.1)
SHOULDER = (0.0, 0.6)
NECK = (0.0, 1.0)
HEAD_OFF = (0.0, 0.5)
ARM_OFF = (0.0, -0.6)
THIGH_LEN, THIGH_OFF = 0.9, (0.0, -0.4)
SHANK_LEN, SHANK_OFF = 1.0, (0.0, -0.5)
KNEE_Z = 1.0


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


def lerp(a, b, w):
    return a + (b - a) * w


def hermite(wps, t):
    """wps = [(t, valeur, pente), ...] triés ; interpolation d'Hermite cubique."""
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


def sym(th, kn, ar, hd):
    return (th, kn, th, kn, ar, ar, hd)


# pose p = (thA, knA, thB, knB, arA, arB, hd) : angles relatifs au torse (rad)
# jambe A = « Left Leg » (jambe d'appui), jambe B = « Right Leg » (jambe frappeuse)
def segments(p):
    tha, kna, thb, knb, ara, arb, hd = p
    segs = [(M_TORSO, 0.0, 0.0, 0.0, 1.0, 2.0, "torso"),
            (M_HEAD, *add(NECK, rot(hd, HEAD_OFF)), hd, 1.2, 1.2, "head")]
    for tag, ar in (("armA", ara), ("armB", arb)):
        segs.append((M_ARM, *add(SHOULDER, rot(ar, ARM_OFF)), ar, 1.0, 2.0, tag))
    for leg, th, kn in (("A", tha, kna), ("B", thb, knb)):
        knee = add(HIP, rot(th, (0.0, -THIGH_LEN)))
        sa = th + kn
        segs.append((M_THIGH, *add(HIP, rot(th, THIGH_OFF)), th, 1.0, 1.0, "thigh" + leg))
        segs.append((M_SHANK, *add(knee, rot(sa, SHANK_OFF)), sa, 1.0, 1.0, "shank" + leg))
    return segs


def com_of(segs):
    return (sum(s[0] * s[1] for s in segs), sum(s[0] * s[2] for s in segs))


def inertia_of(segs, com):
    return sum(s[0] * (s[4] ** 2 + s[5] ** 2) / 12 + s[0] * ((s[1] - com[0]) ** 2 + (s[2] - com[1]) ** 2)
               for s in segs)


def corners_of(segs):
    pts = []
    for m, cy, cz, ang, ly, lz, tag in segs:
        for sy in (-ly / 2, ly / 2):
            for sz in (-lz / 2, lz / 2):
                r = rot(ang, (sy, sz))
                pts.append((cy + r[0], cz + r[1]))
    return pts


def foot_of(p, leg="A"):
    th, kn = (p[0], p[1]) if leg == "A" else (p[2], p[3])
    knee = add(HIP, rot(th, (0.0, -THIGH_LEN)))
    return add(knee, rot(th + kn, (0.0, -SHANK_LEN)))


def h_rel(pose_fn, t, h=1 / 2400):
    """Moment cinétique des membres par rapport au torse (autour du centre de masse)."""
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


def com_world(P, theta, p):
    r = rot(theta, com_of(segments(p)))
    return (P[0] + r[0], P[1] + r[1])


def world_low(P, theta, p):
    return min(P[1] + rot(theta, c)[1] for c in corners_of(segments(p)))


def root_from_pin(theta, p, y_pin, lift=0.0):
    """Centre du torse quand la semelle (jambe A) reste collée en y_pin, sur son arête la plus basse."""
    psi = theta + p[0] + p[1]
    fr = rot(theta, foot_of(p, "A"))
    return (y_pin - fr[0], 0.5 * abs(math.sin(psi)) + lift - fr[1])


def root_contact(theta, p, y):
    """Centre du torse en y donné, posé sur le sol (le point le plus bas touche z = 0)."""
    low = min(rot(theta, c)[1] for c in corners_of(segments(p)))
    return (y, -low)


# ================================================================== phase 1 : au sol (guet, charge, poussée)
def ground1(t, w_to, k=K_EXT):
    tb, tto = T_B, T_TO_NOM
    # guet : on reste tapi, le buste penché, avec de petits balancements de prédateur
    sway = math.sin(2 * math.pi * 0.55 * t)
    th = hermite([(0, rad(16), 0), (0.5, rad(21), 0), (0.9, rad(18), 0), (tb, rad(THETA_B), 0),
                  (tto, rad(THETA_TO), w_to)], t)
    phi = hermite([(0, rad(-40), 0), (0.5, rad(-50), 0), (0.9, rad(-44), 0), (tb, rad(-85), 0),
                   (tto, 0, rad(500) * k)], t)
    psi = hermite([(0, rad(14), 0), (0.5, rad(19), 0), (0.9, rad(16), 0), (tb, rad(32), 0),
                   (tto, 0, rad(-80) * k)], t)
    ar = hermite([(0, rad(-14), 0), (0.5, rad(-6), 0), (0.9, rad(-10), 0), (tb, rad(62), 0),
                  (tto, rad(-150), rad(-600))], t)
    hd = hermite([(0, rad(-16), 0), (0.5, rad(-20), 0), (0.9, rad(-18), 0), (tb, rad(-22), 0),
                  (tto, rad(-12), 0)], t)
    pre = 1 - smooth(0.9, tb, t)
    # tics de prédateur : petites secousses de la tête et des mains
    twitch = max(0.0, math.sin(2 * math.pi * 0.9 * t + 0.6)) ** 6
    th += rad(2.2) * sway * pre
    ar += rad(3.0) * math.sin(2 * math.pi * 3.3 * t) * pre
    hd += rad(9) * twitch * pre
    return th, phi, psi, ar, hd


def relative(theta, phi, psi, ar, hd):
    return sym(phi - theta, psi - phi, ar, hd)


def ground_state(t, w_to, y_pin=0.0, k=K_EXT):
    th, phi, psi, ar, hd = ground1(t, w_to, k)
    p = relative(th, phi, psi, ar, hd)
    u = max(0.0, min(1.0, (t - (T_TO_NOM - T_TOEOFF)) / T_TOEOFF))
    P = root_from_pin(th, p, y_pin, TOEOFF_H * u * u)
    return th, P, p


def find_takeoff(w_nom, k):
    """Instant où le sol cesse de pousser : accélération verticale du centre de masse = -g."""
    e = 1 / 1200

    def cz(t):
        th, P, p = ground_state(t, w_nom, 0.0, k)
        return com_world(P, th, p)[1]
    t = T_B + 0.04
    while t < T_TO_NOM:
        az = (cz(t + e) - 2 * cz(t) + cz(t - e)) / (e * e)
        vz = (cz(t + e) - cz(t - e)) / (2 * e)
        if vz > 1.0 and az <= -G:
            return t
        t += e
    return T_TO_NOM


def takeoff_velocity(w_nom, k, t_to):
    e = 1 / 2400
    th1, P1, p1 = ground_state(t_to, w_nom, 0.0, k)
    th0, P0, p0 = ground_state(t_to - e, w_nom, 0.0, k)
    c1, c0 = com_world(P1, th1, p1), com_world(P0, th0, p0)
    return c1, [(c1[0] - c0[0]) / e, (c1[1] - c0[1]) / e], (th1 - th0) / e


# ================================================================== phase 2 : vol (ciseau retourné)
def flight_pose_fn(p0):
    tha0, kna0, thb0, knb0, ara0, arb0, hd0 = p0
    ti = TAU_IMP
    w = {
        # jambe A (ciseau) : genou remonté pour se grouper (rotation rapide), puis jambe tendue vers le haut
        "tha": [(0, tha0, 0), (0.08, rad(-62), 0), (0.34, rad(-66), 0), (ti, rad(-86), 0),
                (0.9, rad(-86), 0), (3, rad(-60), 0)],
        "kna": [(0, kna0, 0), (0.08, rad(85), 0), (0.34, rad(88), 0), (ti, rad(6), 0),
                (0.9, rad(8), 0), (3, rad(30), 0)],
        # jambe B (frappe) : talon vers la fesse (armée), puis fouettée vers le ballon
        "thb": [(0, thb0, 0), (0.08, rad(28), 0), (0.34, rad(24), 0), (ti, rad(-74), rad(-1100)),
                (0.72, rad(-92), 0), (3, rad(-70), 0)],
        "knb": [(0, knb0, 0), (0.08, rad(78), 0), (0.34, rad(96), 0), (ti, rad(2), rad(-1200)),
                (0.72, rad(12), 0), (3, rad(30), 0)],
        # bras : serrés devant (groupé) puis jetés derrière la tête pour amortir la chute
        "ara": [(0, ara0, 0), (0.08, rad(-70), 0), (0.34, rad(-70), 0), (ti, rad(-168), 0),
                (0.9, rad(-176), 0), (3, rad(-176), 0)],
        "arb": [(0, arb0, 0), (0.08, rad(-62), 0), (0.34, rad(-62), 0), (ti, rad(-155), 0),
                (0.9, rad(-170), 0), (3, rad(-170), 0)],
        # tête : menton rentré puis les yeux rivés sur le ballon
        "hd": [(0, hd0, 0), (0.12, rad(20), 0), (0.34, rad(18), 0), (ti, rad(8), 0), (0.8, rad(-8), 0), (3, rad(-20), 0)],
    }

    def pose(tau):
        return tuple(hermite(w[k], tau) for k in ("tha", "kna", "thb", "knb", "ara", "arb", "hd"))
    return pose


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
        if tau > TAU_IMP + 0.1 and vel[1] < 0 and low <= 0:
            td = len(out) - 1
            break
        theta += w * dt
        com[0] += vel[0] * dt
        com[1] += vel[1] * dt - 0.5 * G * dt * dt
        vel[1] -= G * dt
        tau += dt
    return out, td, th_to, P_to, p_to, L, k, t_to, w_to


def solve_flight():
    lo, hi = -16.0, -2.0
    target = rad(THETA_IMP)
    idx = int(round(TAU_IMP * 1200))

    def err(w):
        out, td, *_ = simulate_flight(w)
        if td is None or td < idx:
            return None
        return out[idx][1] - target
    elo = err(lo)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        em = err(mid)
        if em is None:
            hi = mid
            continue
        if elo is None or (em > 0) == (elo > 0):
            lo, elo = mid, em
        else:
            hi = mid
    w = 0.5 * (lo + hi)
    return w, simulate_flight(w)


# ================================================================== phases 3+ : chute, rire, relevé, extase
T_SETTLE, T_LAUGH_END = 0.35, 1.15
T_SIT, T_TUCK, T_STAND = 0.60, 0.40, 0.65
LYING = (rad(-8), rad(10), rad(-3), rad(5), rad(-20), rad(-30), rad(-28))


def ease(x):
    return smooth(0.0, 1.0, x)


class Shidou:
    def __init__(self):
        (self.w_nom, (self.fl, self.td, self.th_to, self.P_to, self.p_to, self.L, self.k,
                      self.t_to, self.w_to)) = solve_flight()
        self.t_imp = self.t_to + TAU_IMP
        tau, theta, P, p, w, low, com, vel = self.fl[self.td]
        self.t_td = self.t_to + tau
        self.theta_td, self.P_td, self.p_td, self.w_td, self.vel_td = theta, P, p, w, vel
        # impact : position du ballon (au bout du pied frappeur)
        i = int(round(TAU_IMP * 1200))
        _, th_i, P_i, p_i, *_ = self.fl[i]
        foot = add(P_i, rot(th_i, foot_of(p_i, "B")))
        axis = rot(th_i + p_i[2] + p_i[3], (0.0, -1.0))
        self.imp_foot = foot
        self.imp_axis = axis
        # états figés aux frontières des phases
        self._build_post()

    # ----- phases après le toucher (temps tau_l écoulé depuis le toucher)
    def _lying(self, tl):
        th = hermite([(0, self.theta_td, self.w_td * 0.2), (0.20, rad(-93), 0), (0.35, rad(-89), 0),
                      (0.55, rad(-90), 0)], tl)
        env = smooth(0.4, 0.55, tl) * (1 - smooth(T_LAUGH_END - 0.1, T_LAUGH_END, tl))
        th += rad(2.4) * env * math.sin(2 * math.pi * 9 * tl)
        a = smooth(0.0, T_SETTLE, tl)
        p = tuple(lerp(x, y, a) for x, y in zip(self.p_td, LYING))
        hd = p[6] + rad(9) * env * math.sin(2 * math.pi * 11 * tl + 1.0)
        p = p[:6] + (hd,)
        k = 7.0
        y = self.P_td[0] + self.vel_td[0] * (1 - math.exp(-k * tl)) / k
        return th, p, y

    def _build_post(self):
        th, p, y = self._lying(T_LAUGH_END)
        P = root_contact(th, p, y)
        self.hip_y = P[0] + rot(th, HIP)[0]
        self.lying_end = (th, p)
        # fin du tuck : pose accroupie ; on y fixe le pied
        thq, pq = self._tuck_pose(1.0)
        Pq = root_contact(thq, pq, self.hip_y - rot(thq, HIP)[0])
        self.y_pin = Pq[0] + rot(thq, foot_of(pq, "A"))[0]

    def _sit_pose(self, u):
        e = ease(u)
        th = lerp(rad(-90), rad(4), e)
        phi = rad(-90)
        lying = self.lying_end[1]
        ar = lerp(lying[4], rad(-85), e)
        hd = lerp(lying[6], rad(-5), e)
        return th, sym(phi - th, 0.0, ar, hd)

    def _tuck_pose(self, u):
        e = ease(u)
        th = lerp(rad(4), rad(28), e)
        phi = lerp(rad(-90), rad(-112), e)
        psi = lerp(rad(-90), rad(8), e)
        ar = lerp(rad(-85), rad(-60), e)
        return th, sym(phi - th, psi - phi, ar, rad(-5))

    def _stand_pose(self, u):
        e = ease(u)
        th = lerp(rad(28), rad(-8), e)
        phi = lerp(rad(-112), 0.0, e)
        psi = lerp(rad(8), 0.0, e)
        ar = lerp(rad(-60), rad(-12), e)
        hd = lerp(rad(-5), rad(-38), e)
        return th, sym(phi - th, psi - phi, ar, hd)

    def state(self, t):
        """dict : theta (rad, déroulé), P (y,z), p (pose), phase, tau (s dans la phase), sp (écart des bras)."""
        if t < self.t_to:
            th, P, p = ground_state(t, self.w_nom, 0.0, self.k)
            return {"theta": th, "P": P, "p": p, "phase": "sol", "tau": t, "sp": rad(10)}
        if t < self.t_td:
            tau = t - self.t_to
            r = self.fl[min(len(self.fl) - 1, int(round(tau * 1200)))]
            sp = rad(10) + rad(24) * smooth(0.15, 0.45, tau)
            return {"theta": r[1], "P": r[2], "p": r[3], "phase": "vol", "tau": tau, "sp": sp}
        tl = t - self.t_td
        t_sit = T_LAUGH_END
        t_tuck = t_sit + T_SIT
        t_stand = t_tuck + T_TUCK
        t_hold = t_stand + T_STAND
        if tl < t_sit:
            th, p, y = self._lying(tl)
            P = root_contact(th, p, y)
            sp = lerp(rad(34), rad(80), smooth(0.0, 0.5, tl))
            return {"theta": th, "P": P, "p": p, "phase": "allonge", "tau": tl, "sp": sp}
        if tl < t_tuck:
            th, p = self._sit_pose((tl - t_sit) / T_SIT)
            P = root_contact(th, p, self.hip_y - rot(th, HIP)[0])
            return {"theta": th, "P": P, "p": p, "phase": "assis", "tau": tl, "sp": lerp(rad(80), rad(25), ease((tl - t_sit) / T_SIT))}
        if tl < t_stand:
            u = (tl - t_tuck) / T_TUCK
            th, p = self._tuck_pose(u)
            P = root_contact(th, p, self.hip_y - rot(th, HIP)[0])
            return {"theta": th, "P": P, "p": p, "phase": "repli", "tau": tl, "sp": lerp(rad(25), rad(15), ease(u))}
        u = min(1.0, (tl - t_stand) / T_STAND)
        th, p = self._stand_pose(u)
        hold = max(0.0, tl - t_hold)
        env = smooth(0.0, 0.4, hold)
        sh = math.sin(2 * math.pi * 8.5 * hold)
        th += rad(1.6) * env * sh
        p = (p[0], p[1], p[2], p[3], p[4] + rad(5) * env * math.sin(2 * math.pi * 7 * hold),
             p[5] + rad(5) * env * math.sin(2 * math.pi * 7 * hold + 1.2),
             p[6] + rad(7) * env * math.sin(2 * math.pi * 5 * hold) - rad(6) * env)
        P = root_from_pin(th, p, self.y_pin)
        sp = lerp(rad(15), rad(88), ease(u))
        return {"theta": th, "P": P, "p": p, "phase": "extase", "tau": tl, "sp": sp}


# ----------------------------------------------------------------------------- ballon
BALL_R = 0.45
GOAL_Y = 14.0                 # ligne de but
GOAL_W, GOAL_H, NET_D = 21.0, 7.0, 3.5   # largeur, hauteur (2,44 m), profondeur du filet
T_LAUNCH = 0.45
SHOT_SPEED = 70.0             # ~24 m/s
LAUNCH = (0.0, -46.0, 1.2)    # (x, y, z) du centre envoyé par un coéquipier hors champ
TARGET = (4.3, GOAL_Y, 5.7)   # lucarne (x, y, z)


class Ball:
    """Trajectoire du ballon : centre en cloche, frappe, tir, filet, rebonds."""

    def __init__(self, S):
        f, a = S.imp_foot, S.imp_axis
        self.B = (0.0, f[0] + a[0] * BALL_R, f[1] + a[1] * BALL_R)         # centre du ballon à la frappe
        T = S.t_imp - T_LAUNCH
        x0, y0, z0 = LAUNCH
        self.v0 = ((self.B[0] - x0) / T, (self.B[1] - y0) / T, (self.B[2] - z0 + 0.5 * G * T * T) / T)
        self.t_launch, self.t_imp = T_LAUNCH, S.t_imp
        # vitesse de sortie : tir tendu vers la lucarne, résolu avec la gravité
        dx, dy = TARGET[0] - self.B[0], TARGET[1] - self.B[1]
        D = math.hypot(dx, dy)
        dz = TARGET[2] - self.B[2]
        s = SHOT_SPEED
        disc = s**4 - G * (G * D * D + 2 * dz * s * s)
        ang = math.atan2(s * s - math.sqrt(max(disc, 0.0)), G * D)
        self.vout = (s * math.cos(ang) * dx / D, s * math.cos(ang) * dy / D, s * math.sin(ang))
        self.shot_time = D / (s * math.cos(ang))
        # intégration dense après la frappe (filet, rebonds, roulé)
        dt = 1 / 1200
        n = int((T_END - self.t_imp) / dt) + 2
        pos = list(self.B)
        v = list(self.vout)
        spin = 0.0
        self.after = []
        for _ in range(n):
            self.after.append((tuple(pos), spin))
            if pos[1] > GOAL_Y:                                 # dans le filet : freiné
                k = math.exp(-10 * dt)
                v[0] *= k
                v[1] *= k
                v[2] *= math.exp(-3 * dt)
                if pos[1] > GOAL_Y + NET_D - BALL_R:
                    pos[1] = GOAL_Y + NET_D - BALL_R
                    v[1] = -abs(v[1]) * 0.15
            v[2] -= G * dt
            for i in range(3):
                pos[i] += v[i] * dt
            if pos[2] < BALL_R:
                pos[2] = BALL_R
                if v[2] < -2.0:
                    v[2] = -v[2] * 0.42
                    v[0] *= 0.8
                    v[1] *= 0.8
                else:
                    v[2] = 0.0
                    v[0] *= math.exp(-1.5 * dt)
                    v[1] *= math.exp(-1.5 * dt)
            spin += -(v[1] / BALL_R) * dt
        self.goal_time = None
        for i, (q, _) in enumerate(self.after):
            if q[1] >= GOAL_Y:
                self.goal_time = self.t_imp + i * dt
                break

    def at(self, t):
        """(x, y, z, spin) ou None si le ballon n'est pas encore lancé."""
        if t < self.t_launch:
            return None
        if t < self.t_imp:
            tt = t - self.t_launch
            x0, y0, z0 = LAUNCH
            return (x0 + self.v0[0] * tt, y0 + self.v0[1] * tt, z0 + self.v0[2] * tt - 0.5 * G * tt * tt,
                    -(self.v0[1] * tt) / BALL_R * 0.7)
        i = min(len(self.after) - 1, int((t - self.t_imp) * 1200))
        q, spin = self.after[i]
        spin0 = -(self.v0[1] * (self.t_imp - self.t_launch)) / BALL_R * 0.7
        return (q[0], q[1], q[2], spin0 + spin)


# ----------------------------------------------------------------------------- ralenti
def speed(t, t_imp):
    """Vitesse de lecture : 1 = temps réel ; ralenti dramatique autour de la frappe."""
    a = smooth(t_imp - 0.34, t_imp - 0.10, t)
    b = smooth(t_imp + 0.22, t_imp + 0.55, t)
    return 1.0 - 0.82 * a * (1 - b)


def time_table(t_imp):
    """Temps de simulation pour chaque image (début à 1) : intègre la vitesse de lecture."""
    ts = [0.0]
    while ts[-1] < T_END:
        ts.append(ts[-1] + speed(ts[-1], t_imp) / FPS)
    return ts


# ----------------------------------------------------------------------------- diagnostics
def report(S, B):
    print(f"decollage a t={S.t_to:.3f} s ; frappe a t={S.t_imp:.3f} s ; toucher a t={S.t_td:.3f} s")
    r0 = S.fl[0]
    print(f"vitesse CM decollage : vy={r0[7][0]:.2f} vz={r0[7][1]:.2f} u/s ; omega decollage {math.degrees(S.w_to):.0f} deg/s")
    i = int(round(TAU_IMP * 1200))
    print(f"a la frappe : theta={math.degrees(S.fl[i][1]):.1f} deg, omega={math.degrees(S.fl[i][4]):.0f} deg/s, "
          f"CM z={S.fl[i][6][1]:.2f}")
    print(f"ballon : impact en (y={B.B[1]:.2f}, z={B.B[2]:.2f}) ; centre lance de y={LAUNCH[1]} vitesse "
          f"({B.v0[1]:.1f}, {B.v0[2]:.1f}) u/s ; tir {math.hypot(*B.vout):.0f} u/s -> but a t={B.goal_time:.3f} s")
    # pénétration du sol et continuité aux frontières de phases
    worst = (0.0, 0.0, "")
    prev = None
    jumps = []
    t = 0.0
    while t < T_END:
        st = S.state(t)
        low = world_low(st["P"], st["theta"], st["p"])
        if low < worst[0]:
            worst = (low, t, st["phase"])
        if prev is not None and prev["phase"] != st["phase"]:
            dP = math.hypot(st["P"][0] - prev["P"][0], st["P"][1] - prev["P"][1])
            dth = abs(st["theta"] - prev["theta"])
            jumps.append((prev["phase"], st["phase"], round(dP, 3), round(math.degrees(dth), 2)))
        prev = st
        t += 1 / 600
    print("pire penetration du sol :", f"{worst[0]:.3f} u a t={worst[1]:.2f} ({worst[2]})")
    print("sauts aux frontieres (phase, phase, d position, d angle deg) :")
    for j in jumps:
        print("  ", j)


# ======================================================================= Blender
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
    """Coupe une jambe R6 en deux au genou (z = 1) -> (cuisse, mollet)."""
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


def mat_simple(name, color, rough=0.6, emission=0.0):
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    if emission:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emission
    return m


def mat_checker(name, c1, c2, scale):
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.95
    co = nt.nodes.new("ShaderNodeTexCoord")
    tex = nt.nodes.new("ShaderNodeTexChecker")
    tex.inputs["Color1"].default_value = (*c1, 1)
    tex.inputs["Color2"].default_value = (*c2, 1)
    tex.inputs["Scale"].default_value = scale
    nt.links.new(co.outputs["Object"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    return m


def mat_ball():
    import bpy
    m = bpy.data.materials.new("Ballon")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.35
    co = nt.nodes.new("ShaderNodeTexCoord")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 2.4
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.34
    ramp.color_ramp.elements[0].color = (0.02, 0.02, 0.02, 1)
    ramp.color_ramp.elements[1].position = 0.36
    ramp.color_ramp.elements[1].color = (0.95, 0.95, 0.95, 1)
    nt.links.new(co.outputs["Object"], vo.inputs["Vector"])
    nt.links.new(vo.outputs["Distance"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


def bar(bm, p0, p1, r):
    """Barre cylindrique entre deux points (poteaux et barres du but)."""
    import bmesh
    from mathutils import Matrix, Vector
    a, b = Vector(p0), Vector(p1)
    d = b - a
    q = d.to_track_quat("Z", "Y")
    m = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=10, radius1=r, radius2=r,
                          depth=d.length, matrix=m)


def net_grid(bm, p00, p10, p01, p11, nu, nv):
    from mathutils import Vector
    p00, p10, p01, p11 = (Vector(x) for x in (p00, p10, p01, p11))
    vs = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            row.append(bm.verts.new((p00 * (1 - u) + p10 * u) * (1 - v) + (p01 * (1 - u) + p11 * u) * v))
        vs.append(row)
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))


def build_goal():
    import bmesh
    import bpy
    sc = bpy.context.scene
    W = GOAL_W / 2
    yb = GOAL_Y + NET_D
    hb = GOAL_H - 2.0
    bm = bmesh.new()
    r = 0.17
    bar(bm, (-W, GOAL_Y, 0), (-W, GOAL_Y, GOAL_H), r)
    bar(bm, (W, GOAL_Y, 0), (W, GOAL_Y, GOAL_H), r)
    bar(bm, (-W, GOAL_Y, GOAL_H), (W, GOAL_Y, GOAL_H), r)
    for sx in (-W, W):
        bar(bm, (sx, GOAL_Y, GOAL_H), (sx, yb, hb), r * 0.7)
        bar(bm, (sx, yb, hb), (sx, yb, 0), r * 0.7)
        bar(bm, (sx, GOAL_Y, 0), (sx, yb, 0), r * 0.7)
    bar(bm, (-W, yb, hb), (W, yb, hb), r * 0.7)
    me = bpy.data.meshes.new("But_cadre")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_simple("But_blanc", (0.95, 0.95, 0.95), 0.4))
    ob = bpy.data.objects.new("But_cadre", me)
    sc.collection.objects.link(ob)

    bm = bmesh.new()
    net_grid(bm, (-W, yb, 0), (W, yb, 0), (-W, yb, hb), (W, yb, hb), 42, 10)                  # fond
    net_grid(bm, (-W, GOAL_Y, GOAL_H), (W, GOAL_Y, GOAL_H), (-W, yb, hb), (W, yb, hb), 42, 6)  # toit
    for sx in (-W, W):
        net_grid(bm, (sx, GOAL_Y, 0), (sx, yb, 0), (sx, GOAL_Y, GOAL_H), (sx, yb, hb), 8, 14)  # côtés
    me = bpy.data.meshes.new("But_filet")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_simple("But_filet", (0.9, 0.92, 0.95), 0.7))
    net = bpy.data.objects.new("But_filet", me)
    sc.collection.objects.link(net)
    wf = net.modifiers.new("fil", "WIREFRAME")
    wf.thickness = 0.035
    wf.use_even_offset = True


def build_pitch():
    import bmesh
    import bpy
    sc = bpy.context.scene
    g = bpy.data.meshes.new("Pelouse")
    g.from_pydata([(-200, -200, 0), (200, -200, 0), (200, 200, 0), (-200, 200, 0)], [], [(0, 1, 2, 3)])
    g.materials.append(mat_checker("Pelouse", (0.16, 0.38, 0.14), (0.13, 0.33, 0.12), 0.09))
    sc.collection.objects.link(bpy.data.objects.new("Pelouse", g))
    bm = bmesh.new()
    lw = 0.14

    def line(x0, y0, x1, y1):
        bmesh.ops.create_cube(bm, size=1.0, matrix=__import__("mathutils").Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, 0.02))
                              @ __import__("mathutils").Matrix.Diagonal((abs(x1 - x0) + lw, abs(y1 - y0) + lw, 0.03, 1.0)))
    line(-36, GOAL_Y, 36, GOAL_Y)                    # ligne de but
    line(-26, -1.7, 26, -1.7)                        # ligne de la surface de but
    line(-26, -1.7, -26, GOAL_Y)
    line(26, -1.7, 26, GOAL_Y)
    me = bpy.data.meshes.new("Lignes")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_simple("Lignes", (0.95, 0.95, 0.95), 0.8))
    sc.collection.objects.link(bpy.data.objects.new("Lignes", me))


def build_hair(head_pivot):
    """Cheveux en pointes (rouge sombre) : l'allure sauvage de Shidou."""
    import bmesh
    import bpy
    from mathutils import Matrix, Vector
    bm = bmesh.new()
    c = Vector((0, 0, 4.5))
    # pas de pointes vers l'arrière : elles traverseraient le sol quand il est allongé sur le dos
    dirs = [(0, 0, 1), (0, -0.45, 0.9), (0.7, 0.0, 0.7), (-0.7, 0.0, 0.7), (0.4, -0.5, 0.75),
            (-0.4, -0.5, 0.75), (0.6, 0.15, 0.75), (-0.6, 0.15, 0.75)]
    for d in dirs:
        d = Vector(d).normalized()
        q = d.to_track_quat("Z", "Y")
        m = Matrix.Translation(c + d * 0.72) @ q.to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=6, radius1=0.24, radius2=0.0,
                              depth=0.7, matrix=m)
    me = bpy.data.meshes.new("Shidou_cheveux")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_simple("Cheveux_Shidou", (0.55, 0.04, 0.10), 0.5))
    ob = bpy.data.objects.new("Shidou_cheveux", me)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    ob.parent = head_pivot
    ob.matrix_parent_inverse = head_pivot.matrix_world.inverted()


def cam_hermite(wps, t):
    out = []
    for k in range(3):
        out.append(hermite([(w[0], w[1][k], 0.0) for w in wps], t))
    return out


def build(src, dst, S, B):
    import bpy
    from mathutils import Euler, Vector
    bpy.ops.wm.open_mainfile(filepath=src)
    sc = bpy.context.scene

    # 1) squelette d'empties (pivots exacts) et genoux
    root = new_empty("Shidou_Root", (0, 0, 3.0), size=0.8)
    head = new_empty("Shidou_Tete_Pivot", (0, 0, 4.0), root)
    arm_l = new_empty("Shidou_BrasG_Pivot", (-1.5, 0, 3.6), root)
    arm_r = new_empty("Shidou_BrasD_Pivot", (1.5, 0, 3.6), root)
    hip_l = new_empty("Shidou_HancheG_Pivot", (-0.5, 0, 1.9), root)
    hip_r = new_empty("Shidou_HancheD_Pivot", (0.5, 0, 1.9), root)
    knee_l = new_empty("Shidou_GenouG_Pivot", (-0.5, 0, KNEE_Z), hip_l)
    knee_r = new_empty("Shidou_GenouD_Pivot", (0.5, 0, KNEE_Z), hip_r)
    bpy.context.view_layer.update()
    thigh_l, shank_l = split_leg("Left Leg")
    thigh_r, shank_r = split_leg("Right Leg")
    attach = {"Torso": root, "Head": head, "Left Arm": arm_l, "Right Arm": arm_r,
              thigh_l.name: hip_l, shank_l.name: knee_l, thigh_r.name: hip_r, shank_r.name: knee_r}
    for name, piv in attach.items():
        ob = bpy.data.objects[name]
        for c in ob.constraints:
            if c.type == "CHILD_OF":
                c.mute = True
        ob.parent = piv
        ob.matrix_parent_inverse = piv.matrix_world.inverted()
    for n in ("Armature", "__Rig", "__RigMeta"):
        if n in bpy.data.objects:
            bpy.data.objects[n].hide_viewport = True
            bpy.data.objects[n].hide_render = True
    build_hair(head)

    # 2) décor : pelouse, but et filet, ballon
    build_pitch()
    build_goal()
    me = bpy.data.meshes.new("Ballon")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=BALL_R)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    me.materials.append(mat_ball())
    ball = bpy.data.objects.new("Ballon", me)
    ball.rotation_mode = "XYZ"
    sc.collection.objects.link(ball)

    # 3) lumières : soleil bas et chaud, ciel du soir, flash rouge à la frappe
    sun_d = bpy.data.lights.new("Soleil", "SUN")
    sun_d.energy = 4.2
    sun_d.color = (1.0, 0.86, 0.72)
    sun_d.angle = rad(2.5)
    sun = bpy.data.objects.new("Soleil", sun_d)
    sun.rotation_euler = (rad(62), rad(8), rad(-28))
    sc.collection.objects.link(sun)
    fl_d = bpy.data.lights.new("Flash_frappe", "POINT")
    fl_d.color = (1.0, 0.30, 0.18)
    fl_d.energy = 0.0
    flash = bpy.data.objects.new("Flash_frappe", fl_d)
    flash.location = B.B
    sc.collection.objects.link(flash)
    world = sc.world or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.20, 0.30, 0.55, 1)
    bg.inputs["Strength"].default_value = 0.8

    # 4) caméras
    tt = time_table(S.t_imp)
    nF = len(tt)
    cam_d = bpy.data.cameras.new("Camera_Shidou")
    cam_d.lens = 30
    cam = bpy.data.objects.new("Camera_Shidou", cam_d)
    sc.collection.objects.link(cam)
    tgt = new_empty("Camera_Cible", (0, 0, 3), size=0.3)
    tr = cam.constraints.new("TRACK_TO")
    tr.target = tgt
    tr.track_axis = "TRACK_NEGATIVE_Z"
    tr.up_axis = "UP_Y"
    sc.camera = cam
    cam2_d = bpy.data.cameras.new("Camera_Profil")
    cam2_d.lens = 28
    cam2 = bpy.data.objects.new("Camera_Profil", cam2_d)
    cam2.location = (24.0, 3.0, 4.2)
    cam2.rotation_euler = (rad(90), 0, rad(90))
    sc.collection.objects.link(cam2)
    t_g = B.goal_time or (S.t_imp + 0.3)
    cam_wps = [
        (0.0, (11.0, -8.5, 1.7)), (1.0, (9.6, -6.6, 1.5)), (S.t_to + 0.05, (12.5, -5.0, 2.4)),
        (S.t_imp, (15.5, -2.8, 3.7)), (S.t_imp + 0.55, (14.5, 3.0, 3.4)), (t_g + 0.7, (11.5, 6.5, 3.0)),
        (S.t_td + 1.6, (-8.0, -11.0, 1.4)), (T_END, (-6.2, -9.0, 1.7)),
    ]

    # 5) images clés : une par image, la physique est déjà échantillonnée (temps de simulation -> image)
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, nF
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.view_settings.view_transform = "Standard"
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    tpos = Vector((0.0, 0.0, 3.0))
    for f in range(1, nF + 1):
        t = tt[f - 1]
        st = S.state(t)
        tha, kna, thb, knb, ara, arb, hd = st["p"]
        root.location = (0.0, st["P"][0], st["P"][1])
        root.rotation_euler = Euler((st["theta"], 0, 0))
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
        sp = st["sp"]
        head.rotation_euler = Euler((hd, 0, 0))
        arm_l.rotation_euler = Euler((ara, sp, 0))
        arm_r.rotation_euler = Euler((arb, -sp, 0))
        hip_l.rotation_euler = Euler((tha, 0, 0))
        hip_r.rotation_euler = Euler((thb, 0, 0))
        knee_l.rotation_euler = Euler((kna, 0, 0))
        knee_r.rotation_euler = Euler((knb, 0, 0))
        for e in (head, arm_l, arm_r, hip_l, hip_r, knee_l, knee_r):
            e.keyframe_insert("rotation_euler", frame=f)
        # ballon
        bp = B.at(t)
        if bp is None:
            ball.location = (0, LAUNCH[1], -50)
        else:
            ball.location = bp[:3]
            ball.rotation_euler = Euler((bp[3], 0, 0))
        ball.keyframe_insert("location", frame=f)
        ball.keyframe_insert("rotation_euler", frame=f)
        # flash rouge à la frappe
        dt_i = t - S.t_imp
        fl_d.energy = 5000.0 * math.exp(-dt_i / 0.05) if 0 <= dt_i < 0.4 else 0.0
        fl_d.keyframe_insert("energy", frame=f)
        # caméra : trajectoire lissée, cible = Shidou puis ballon puis Shidou
        com = com_world(st["P"], st["theta"], st["p"])
        c3 = Vector((0.0, com[0], com[1] + 0.4))
        w_ball = smooth(S.t_imp - 0.02, S.t_imp + 0.25, t) * (1 - smooth(t_g + 0.15, t_g + 0.9, t))
        bpos = Vector(bp[:3]) if bp is not None else c3
        want = c3 * (1 - w_ball) + bpos * w_ball
        if t > S.t_td + 1.6:
            want = Vector((0.0, com[0], com[1] + 0.7))
        k = 1 - math.exp(-1 / FPS / 0.22)
        tpos = tpos + (want - tpos) * k
        tgt.location = tpos
        tgt.keyframe_insert("location", frame=f)
        cx, cy, cz = cam_hermite(cam_wps, t)
        shake = 0.0
        if 0 <= dt_i < 0.5:
            shake = 0.12 * math.exp(-dt_i / 0.12) * math.sin(2 * math.pi * 14 * dt_i)
        cam.location = (cx, cy, cz + shake)
        cam.keyframe_insert("location", frame=f)
    sc.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=dst)
    print(f"OK: {dst} ({nF} images, {nF / FPS:.1f} s) ; frappe a l'image {tt.index(min(tt, key=lambda x: abs(x - S.t_imp))) + 1}")


if __name__ == "__main__":
    if "--sim" in sys.argv:
        S = Shidou()
        B = Ball(S)
        report(S, B)
        tt = time_table(S.t_imp)
        print("images :", len(tt), "(", len(tt) / FPS, "s )")
        sys.exit(0)
    S = Shidou()
    B = Ball(S)
    report(S, B)
    build(sys.argv[-2], sys.argv[-1], S, B)
