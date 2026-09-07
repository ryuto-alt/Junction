# -*- coding: utf-8 -*-
"""stagedemo3(リミナル版)の机上シミュレータ。エンジンを起動せずに次を検査する。

    python source/sim_liminal.py

  1) 継ぎ目ごとの「合う場所」の分布  … 焦点の周りで角度誤差 < lock になる床の広さ。
     狭すぎる(見つからない) / 広すぎる(歩いていたら勝手に確定する) を数値で弾く。
  2) 順路の通し歩き               … 当たり判定だけを使った BFS。段差 0.32 / 頭上 1.8 /
     体の半径 0.34 を守って「継ぎ目を1つずつ確定させながら」出口まで行けるか。
  3) 破片の干渉                   … ずれた状態の破片が壁や床にめり込んでいないか、
     破片どうしが重なっていないか(重なると『どっちの破片か』が読めなくなる)。
  4) 組み上がった足場の連続性     … 階段の蹴上げ・橋の継ぎ目・踊り場の段差。

★ここを通らないものはエディタで開かない。実機の検証はこの後。
"""
import math, sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_liminal as G

CELL = 0.15
RADIUS = 0.34
STEP_UP = 0.32
HEAD = 1.80
EYE = G.EYE

OK = True
NL = chr(10)


def fail(msg):
    global OK
    OK = False
    print("  [NG] " + msg)


def ok(msg):
    print("  [OK] " + msg)


# ---------------------------------------------------------------- 箱の貫通(OBB)
class Obb:
    """yaw を持つ箱。既存の aabb() は回転を【広げて】見るので、斜めの板の貫通を
    測るのには使えない(嘘の重なりが出る)。分離軸できちんと測る。"""
    __slots__ = ("n", "cx", "cy", "cz", "hx", "hy", "hz", "c", "s", "aab", "thin", "rot")

    def __init__(self, e):
        p = e["transform"]["position"]
        sc = e["transform"]["scale"]
        yaw = math.radians(e["transform"]["rotation"][1])
        self.n = e["name"]
        self.cx, self.cy, self.cz = p
        self.hx, self.hy, self.hz = abs(sc[0]) / 2, abs(sc[1]) / 2, abs(sc[2]) / 2
        self.c, self.s = math.cos(yaw), math.sin(yaw)
        ex = abs(self.hx * self.c) + abs(self.hz * self.s)
        ez = abs(self.hx * self.s) + abs(self.hz * self.c)
        self.aab = (self.cx - ex, self.cy - self.hy, self.cz - ez,
                    self.cx + ex, self.cy + self.hy, self.cz + ez)
        self.thin = min(abs(sc[0]), abs(sc[1]), abs(sc[2]))
        self.rot = abs(e["transform"]["rotation"][1]) % 90 > 0.01


def pen_xz(a, b):
    """xz 平面での貫通量(m)。離れていれば 0。"""
    dx, dz = b.cx - a.cx, b.cz - a.cz
    best = 1e9
    for ax, az in ((a.c, -a.s), (a.s, a.c), (b.c, -b.s), (b.s, b.c)):
        ra = abs(a.hx * (ax * a.c - az * a.s)) + abs(a.hz * (ax * a.s + az * a.c))
        rb = abs(b.hx * (ax * b.c - az * b.s)) + abs(b.hz * (ax * b.s + az * b.c))
        o = ra + rb - abs(dx * ax + dz * az)
        if o <= 0:
            return 0.0
        best = min(best, o)
    return best


def obb_pairs(ents, shard_of, minpen=0.05, coplanar=0.006, minarea=0.35):
    """(貫通した組, 同一平面の組)。破片がらみ・斜めの箱がらみだけを見る
    (構造壁の角どうしの 0.30m の重なりは建物の組み方そのものなので対象外)。"""
    obs = [Obb(e) for e in ents
           if "primitive" in e and e["transform"]["position"][1] > -50.0]
    grid = {}
    for i, o in enumerate(obs):
        for gx in range(int(math.floor(o.aab[0] / 4.0)), int(math.floor(o.aab[3] / 4.0)) + 1):
            for gz in range(int(math.floor(o.aab[2] / 4.0)), int(math.floor(o.aab[5] / 4.0)) + 1):
                grid.setdefault((gx, gz), []).append(i)
    deep, flat, seen = [], [], set()
    for cell in grid.values():
        for i in range(len(cell)):
            for j in range(i + 1, len(cell)):
                key = (cell[i], cell[j])
                if key in seen:
                    continue
                seen.add(key)
                a, b = obs[key[0]], obs[key[1]]
                sa, sb = shard_of.get(a.n), shard_of.get(b.n)
                if not (sa or sb or a.rot or b.rot):
                    continue
                if sa and sb and {c for c, _ in sa} & {c for c, _ in sb}:
                    # 同じ継ぎ目の破片どうしは噛み合って良い(扉枠の隅・階段の蹴込み板)。
                    # 浮遊中の破片どうしの重なりは [1] が別に見ている。
                    continue
                if a.thin < 0.06 or b.thin < 0.06:
                    continue                  # 擦れ跡・光の線は貫通しても見えない
                pxz = pen_xz(a, b)
                if pxz <= 0.0:
                    continue
                oy = min(a.cy + a.hy, b.cy + b.hy) - max(a.cy - a.hy, b.cy - b.hy)
                if oy > minpen and pxz > minpen:
                    deep.append((min(oy, pxz), a.n, b.n))
                elif pxz > minarea:
                    for va, vb in ((a.cy + a.hy, b.cy + b.hy), (a.cy - a.hy, b.cy - b.hy)):
                        if abs(va - vb) < coplanar:
                            flat.append((a.n, b.n, va))
                            break
    deep.sort(key=lambda t: -t[0])
    return deep, flat


# ---------------------------------------------------------------- 幾何
def aabb(e):
    p = e["transform"]["position"]
    s = e["transform"]["scale"]
    r = e["transform"]["rotation"]
    if abs(r[1]) > 0.01:                       # yaw 回転は AABB を広げて保守的に見る
        c, sn = abs(math.cos(math.radians(r[1]))), abs(math.sin(math.radians(r[1])))
        sx = s[0] * c + s[2] * sn
        sz = s[0] * sn + s[2] * c
        s = [sx, s[1], sz]
    return (p[0] - s[0] / 2, p[1] - s[1] / 2, p[2] - s[2] / 2,
            p[0] + s[0] / 2, p[1] + s[1] / 2, p[2] + s[2] / 2)


def overlap(a, b, eps=0.0):
    return (a[0] < b[3] - eps and b[0] < a[3] - eps and
            a[1] < b[4] - eps and b[1] < a[4] - eps and
            a[2] < b[5] - eps and b[2] < a[5] - eps)


class Body:
    """当たり判定 1 個。yaw 回転を持てる(橋が斜めなので AABB では代用できない)。"""
    __slots__ = ("name", "cx", "cy", "cz", "hx", "hy", "hz", "cos", "sin", "aab")

    def __init__(self, name, pos, scale, yaw):
        self.name = name
        self.cx, self.cy, self.cz = pos
        self.hx, self.hy, self.hz = scale[0] / 2, scale[1] / 2, scale[2] / 2
        self.cos = math.cos(math.radians(yaw))
        self.sin = math.sin(math.radians(yaw))
        self._bake()

    def _bake(self):
        ex = abs(self.hx * self.cos) + abs(self.hz * self.sin)
        ez = abs(self.hx * self.sin) + abs(self.hz * self.cos)
        self.aab = (self.cx - ex, self.cy - self.hy, self.cz - ez,
                    self.cx + ex, self.cy + self.hy, self.cz + ez)

    def move(self, pos):
        self.cx, self.cy, self.cz = pos
        self._bake()

    def contains_xz(self, x, z, pad=0.0):
        dx, dz = x - self.cx, z - self.cz
        # ワールド -> 箱のローカル(yaw の逆回転)
        lx = dx * self.cos - dz * self.sin
        lz = dx * self.sin + dz * self.cos
        return abs(lx) <= self.hx + pad and abs(lz) <= self.hz + pad

    def top(self):
        return self.cy + self.hy


GRID = 2.0


class World:
    """★ボディを 2m 角のバケツに入れておく。全数走査だと 10 面 155 ボディで
    BFS が数分かかる(升ごとに全ボディを見るため)。"""

    def __init__(self, entities):
        self.bodies = []
        self.byname = {}
        for e in entities:
            self.byname[e["name"]] = e
            if "rigidBody" in e:
                t = e["transform"]
                self.bodies.append(Body(e["name"], t["position"], t["scale"], t["rotation"][1]))
        self.index = {b.name: b for b in self.bodies}
        self.rebuild()

    def rebuild(self):
        self.grid = {}
        for b in self.bodies:
            if b.cy < -100:
                continue
            gx0 = int(math.floor((b.aab[0] - RADIUS) / GRID))
            gx1 = int(math.floor((b.aab[3] + RADIUS) / GRID))
            gz0 = int(math.floor((b.aab[2] - RADIUS) / GRID))
            gz1 = int(math.floor((b.aab[5] + RADIUS) / GRID))
            for gx in range(gx0, gx1 + 1):
                for gz in range(gz0, gz1 + 1):
                    self.grid.setdefault((gx, gz), []).append(b)

    def near(self, x, z):
        return self.grid.get((int(math.floor(x / GRID)), int(math.floor(z / GRID))), ())

    def enable(self, name, pos):
        self.index[name].move(pos)
        self.rebuild()

    def disable(self, name):
        b = self.index.get(name)      # 当たり判定を持たない見た目だけの物もある
        if b:
            b.move((b.cx, b.cy - 500.0, b.cz))
            self.rebuild()

    SUPPORT_PAD = 0.06        # ★足場は点で見ない。板の継ぎ目(数 cm)で落ちる嘘の失敗が出る
                              #   (実機の CharacterController は半径 0.34 なので落ちない)

    def tops(self, x, z):
        out = []
        for b in self.near(x, z):
            if b.contains_xz(x, z, self.SUPPORT_PAD):
                out.append(round(b.top(), 3))
        return sorted(set(out))

    def blocked(self, x, z, h):
        """★『またげる高さ(stepHeight)以下の物は壁にならない』を必ず入れること。
        入れ忘れると階段の次の段が体の半径に入った瞬間に壁扱いになり、
        『階段があるのに一段も登れない』という嘘の詰みが出る(実際に踏んだ)。"""
        hi = h + 1.75
        for b in self.near(x, z):
            if b.top() <= h + STEP_UP + 0.001:
                continue
            if b.cy - b.hy >= hi - 0.001:
                continue
            if b.contains_xz(x, z, RADIUS):
                return True
        return False

    def headroom(self, x, z, h):
        best = 99.0
        for b in self.near(x, z):
            if b.cy - b.hy >= h + 0.5 and b.contains_xz(x, z):
                best = min(best, b.cy - b.hy - h)
        return best


def walk(world, start, targets, bounds, maxcells=3000000):
    """BFS。★同じ升でも【高さが違えば別の状態】として扱う(階段の下に床があると、
    先に床側で升を潰してしまい『階段を登れない』という嘘の失敗が出る)。
    targets は {名前: (x, z)} か {名前: (x, z, 高さ)}。"""
    x0, z0, x1, z1 = bounds
    sx, sz, sh = start
    q = deque()
    seen = {}                                  # (cx,cz,層) -> 高さ
    flat = {}                                  # (cx,cz) -> 一番低い到達高さ(表示用)

    def push(cx, cz, h):
        k = (cx, cz, round(h * 4))
        if k in seen:
            return
        seen[k] = h
        if (cx, cz) not in flat or h < flat[(cx, cz)]:
            flat[(cx, cz)] = h
        q.append((cx, cz, h))

    push(round(sx / CELL), round(sz / CELL), sh)
    n = 0
    while q and n < maxcells:
        cx, cz, h = q.popleft()
        n += 1
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = cx + dx, cz + dz
            wx, wz = nx * CELL, nz * CELL
            if not (x0 <= wx <= x1 and z0 <= wz <= z1):
                continue
            cand = None
            for t in world.tops(wx, wz):
                if t <= h + STEP_UP + 0.001 and (cand is None or t > cand):
                    cand = t
            if cand is None or cand < h - 4.0:      # 4m 超の落下は「戻れない」= 進路にしない
                continue
            if world.blocked(wx, wz, cand):
                continue
            if world.headroom(wx, wz, cand) < HEAD:
                continue
            push(nx, nz, cand)
    reach = {}
    for name, t in targets.items():
        tx, tz = t[0], t[1]
        th = t[2] if len(t) > 2 else None
        cx, cz = round(tx / CELL), round(tz / CELL)
        hits = [v for (kx, kz, _), v in seen.items() if kx == cx and kz == cz]
        reach[name] = bool(hits) if th is None else any(abs(v - th) < 0.35 for v in hits)
    return reach, seen, flat


# ---------------------------------------------------------------- 継ぎ目の検査
def align_error(eye, F, k, pts):
    worst = 0.0
    for p in pts:
        a = (p[0] - eye[0], p[1] - eye[1], p[2] - eye[2])
        b = (F[0] + k * (p[0] - F[0]) - eye[0],
             F[1] + k * (p[1] - F[1]) - eye[1],
             F[2] + k * (p[2] - F[2]) - eye[2])
        cr = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
        cross = math.sqrt(sum(v * v for v in cr))
        dot = sum(a[i] * b[i] for i in range(3))
        worst = max(worst, math.degrees(math.atan2(cross, dot)))
    return worst


def pair_angle(eye, a, b):
    """2 点が画面上で重なって見えるか(度)。「触れる」規則。"""
    u = (a[0] - eye[0], a[1] - eye[1], a[2] - eye[2])
    v = (b[0] - eye[0], b[1] - eye[1], b[2] - eye[2])
    cr = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    return math.degrees(math.atan2(math.sqrt(sum(t * t for t in cr)),
                                   sum(u[i] * v[i] for i in range(3))))


def shard_error(c, sh, eye):
    if sh.get("disp"):
        return 0.0                      # 自由な破片は touch 規則で判定する
    # ★k>1(遠くの巨大 -> 手元の小)も必ず数える。k<0.999 だけ見ていると
    #   継ぎ目13 のような逆スケールの破片が「誤差 0」に見えて検査をすり抜ける
    if abs(sh["k"] - 1.0) <= 0.001:
        return 0.0
    return align_error(eye, sh.get("focus") or c.focus, sh["k"], sh["pts"])


def conn_error(c, eye, only=None):
    """only を渡すとその破片だけ(巡る規則の 1 枚ぶんの検査に使う)。"""
    if c.touch:
        return pair_angle(eye, c.touch["a"], c.touch["b"])
    if only is not None:
        return shard_error(c, c.shards[only], eye)
    return max([shard_error(c, sh, eye) for sh in c.shards] or [0.0])


FOCUS_LOCK = 7.0     # 実行時と同じ足切り(焦点から遠いと確定しない)


def occluded(occl, eye):
    """規則F「かくれて合わせる」: 目 → 指定した点 の線分が、遮蔽箱のどれかを
    通っているか。★実行時(Liminal.lua の hidden)と同じ式にしておくこと。
    ここを入れ忘れると、机上で測る確定域が【実際より広い】ままになり、
    床の目印が『印の上なのに繋がらない』場所に置かれる。"""
    p = occl["p"]
    d = (p[0] - eye[0], p[1] - eye[1], p[2] - eye[2])
    for b in occl["boxes"]:
        t0, t1, hit_ = 0.0, 1.0, True
        for a in range(3):
            if abs(d[a]) < 1e-9:
                if eye[a] < b[a] or eye[a] > b[a + 3]:
                    hit_ = False
                    break
            else:
                ta = (b[a] - eye[a]) / d[a]
                tb = (b[a + 3] - eye[a]) / d[a]
                if ta > tb:
                    ta, tb = tb, ta
                t0 = max(t0, ta)
                t1 = min(t1, tb)
                if t0 > t1:
                    hit_ = False
                    break
        if hit_:
            return True
    return False


def field(c, seen, floor_of, half=3.6, only=None):
    """焦点の周りを走査し、床がある所だけ誤差を測る。
    only を渡すと【その破片の焦点】の周りを見る(巡る規則)。"""
    F = (c.shards[only].get("focus") or c.focus) if only is not None else c.focus
    fx, fz = F[0], F[2]
    good, warm, best, bestp = [], 0, 1e9, None
    n = int(half / CELL)
    for iz in range(-n, n + 1):
        for ix in range(-n, n + 1):
            x, z = fx + ix * CELL, fz + iz * CELL
            k = (round(x / CELL), round(z / CELL))
            if k not in seen:
                continue
            # ★焦点と違う高さの床(溝の底など)は数えない。目の高さが変われば別の話
            if abs(seen[k] + EYE - F[1]) > 0.4:
                continue
            eye = (x, seen[k] + EYE, z)
            # ★「何段目に立つか」を問う継ぎ目は、実行時と同じ高さの窓で足切りする
            if c.min_y is not None and eye[1] < c.min_y:
                continue
            if c.max_y is not None and eye[1] > c.max_y:
                continue
            if c.touch:
                m = [(c.touch["a"][q] + c.touch["b"][q]) / 2 for q in range(3)]
                dm = math.dist(eye, tuple(m))
                if dm < c.touch.get("near", 1.5) or dm > c.touch.get("far", 13.0):
                    continue
            elif math.dist(eye, tuple(F)) > FOCUS_LOCK:
                continue
            if c.occl and not occluded(c.occl, eye):
                continue
            err = conn_error(c, eye, only)
            if err < c.lock:
                good.append((x, z))
            if err < c.warn:
                warm += 1
            if err < best:
                best, bestp = err, (x, z)
    return good, warm, best, bestp


def main():
    G.build()
    ents, conns = G.ES, G.CONNS
    world = World(ents)
    bounds = (-10.0, -12.0, 90.0, 312.0)
    print("=" * 68)
    print("stagedemo3 / liminal — 机上シミュレーション")
    print("=" * 68)
    print("entities=%d  colliders=%d  joints=%d" % (len(ents), len(world.bodies), len(conns)))

    # ---------------------------------------------------- 破片の干渉
    print("\n[1] 破片(ずれた状態)の干渉")
    shard_boxes = []
    seen_names = set()
    for c in conns:
        for si, sh in enumerate(c.shards):
            if sh["k"] >= 0.999:
                continue
            for r in sh["ents"]:
                if r["n"] in seen_names:      # 多義の破片は 2 つの継ぎ目で共有する
                    continue
                seen_names.add(r["n"])
                e = world.byname[r["n"]]
                shard_boxes.append((c.cid, si, r["n"], aabb(e)))
    bad = 0
    for cid, si, name, b in shard_boxes:
        for sb in world.bodies:
            if overlap(b, sb.aab, 0.02):
                # 床の擦れ跡など極薄の物とは重なってよい
                if sb.aab[4] - sb.aab[1] < 0.05:
                    continue
                fail("破片 %s が %s にめり込んでいる" % (name, sb.name))
                bad += 1
    for i in range(len(shard_boxes)):
        for j in range(i + 1, len(shard_boxes)):
            a, b = shard_boxes[i], shard_boxes[j]
            if a[0] == b[0] and a[1] == b[1]:
                continue
            if overlap(a[3], b[3], 0.02):
                fail("破片 %s と %s が空間で重なっている" % (a[2], b[2]))
                bad += 1
    if bad == 0:
        ok("%d 個の破片、めり込み・相互干渉なし" % len(shard_boxes))

    # ---------------------------------------------------- 順路(段階ごと)
    print(NL + "[2] 順路の通し歩き(継ぎ目を1つずつ確定させる)")
    start = (0.0, -6.0, 0.0)
    B = bounds

    def apply(c):
        for sd in c.solids:
            world.enable(sd["n"], sd["p"])
        for m in c.movers:
            world.disable(m["n"])

    def standing(seen, x, z, h, tol=0.4):
        cx, cz = round(x / CELL), round(z / CELL)
        return any(abs(v - h) < tol for (kx, kz, _), v in seen.items() if kx == cx and kz == cz)

    # (継ぎ目id, その継ぎ目を解く前に【行けてはいけない】点, 解いた後に【行けるべき】点)
    #  点は (x, z, 立つ高さ)。None は検査しない
    PLAN = {
        1:  ((0.0, 20.0, 0.0),    (0.0, 17.0, 0.0)),
        2:  ((5.3, 36.0, 0.0),    (5.3, 36.0, 0.0)),
        3:  ((6.1, 63.6, 3.40),   (6.1, 63.6, 3.40)),
        4:  ((6.1, 82.6, 3.40),   (6.1, 82.6, 3.40)),
        5:  ((6.0, 106.5, 3.40),  (6.0, 106.5, 3.40)),
        6:  ((22.5, 120.0, 3.40), (22.5, 120.0, 3.40)),
        7:  ((22.0, 138.0, 3.40), (22.0, 138.0, 3.40)),
        8:  (None, (22.0, 138.0, 3.40)),
        9:  ((22.0, 158.0, 5.80), (22.0, 158.0, 5.80)),
        10: ((22.0, 173.0, 5.80), (22.0, 173.0, 5.80)),
        # ---- 第三幕 ----
        11: ((22.0, 188.2, 5.80), (22.0, 188.2, 5.80)),   # 溝を渡る
        12: ((32.0, 195.4, 7.60), (32.0, 195.4, 7.60)),   # 渡り廊下 -> 吹き抜けへ
        13: ((43.2, 195.4, 7.60), (43.2, 195.4, 7.60)),   # 巨人の板 -> 東の桟へ
        14: (None, None),                                  # ★負の継ぎ目。解かないのが正解
        15: ((68.0, 208.6, 7.60), (68.0, 208.6, 7.60)),   # 模型 -> 本物の廊下
        16: ((68.0, 217.0, 7.60), (68.0, 217.0, 7.60)),   # 扉 -> 白い部屋
        # ---- 第四幕(大展示室・順番は自由。18〜21 が 4 本の橋、17 が出口の階段) ----
        18: ((64.3, 233.95, 7.60), (64.3, 233.95, 7.60)),  # 西の橋 -> 島A
        19: ((73.7, 233.95, 7.60), (73.7, 233.95, 7.60)),  # 東の橋 -> 島C
        20: ((68.0, 229.50, 7.60), (68.0, 229.50, 7.60)),  # 南の橋 -> 島D
        21: ((68.0, 238.80, 7.60), (68.0, 238.80, 7.60)),  # 北の橋 -> 島B
        17: ((68.0, 249.00, 10.60), (68.0, 249.00, 10.60)),  # 階段 -> 白い部屋
        # ---- 第五幕(環の間。床 10.60)。前の継ぎ目が作った足場に立たないと次が解けない ----
        22: ((68.0, 288.00, 10.60), (68.0, 288.00, 10.60)),  # 井戸の床 -> 北半分へ
        23: ((77.0, 299.00, 11.20), (77.0, 299.00, 11.20)),  # 影の段 -> 棚の上へ
        24: ((56.3, 299.00, 13.00), (56.3, 299.00, 13.00)),  # 片持ちの段 -> 踊り場へ
        25: ((56.0, 304.00, 13.00), (56.0, 304.00, 13.00)),  # 北壁が割れる -> 出口
    }
    flats = {}
    order = sorted(conns, key=lambda c: c.solve_order)
    for c in order:
        tg = {}
        if c.per_shard:
            for i, sh in enumerate(c.shards):
                f = sh.get("focus") or c.focus
                tg["F%d_%d" % (c.cid, i)] = (f[0], f[2], f[1] - EYE)
        else:
            tg["F%d" % c.cid] = (c.focus[0], c.focus[2], c.focus[1] - EYE)
        r, seen, flat = walk(world, start, tg, B)
        flats[c.cid] = flat
        for nm, ok_ in r.items():
            if not ok_:
                fail("継ぎ目%d(%s): 焦点 %s へ歩いて行けない" % (c.cid, c.note, nm))
        before, after = PLAN[c.cid]
        if before and standing(seen, *before):
            fail("継ぎ目%d を解く前に (%.1f, %.1f) へ行けてしまう" % (c.cid, before[0], before[1]))
        if c.cid == 8:
            continue                      # 多義の片割れ。7 を採った世界で進む(8 は下で別途検査)
        if c.anti:
            # ★負の継ぎ目は【解かずに】進むのが正解なので、順路には適用しない。
            #   解いてしまった世界(迂回路)は下で別に検査する
            continue
        apply(c)
        if after:
            r2, seen2, _ = walk(world, start, {"t": after}, B)
            if not r2["t"]:
                fail("継ぎ目%d を解いても (%.1f, %.1f) へ行けない" % (c.cid, after[0], after[1]))
    if OK:
        ok("継ぎ目 1〜10 を順に確定させて出口まで到達。各段階で【解く前は行けない】ことも確認")

    # 多義のもう片方(西の橋)でも渡れるか: 世界を作り直して 8 だけを採る
    w2 = World(G.ES)
    for c in order:
        if c.cid == 7:
            continue
        for sd in c.solids:
            w2.enable(sd["n"], sd["p"])
        for m in c.movers:
            w2.disable(m["n"])
    r3, _, _ = walk(w2, start, {"t": (22.0, 138.0, 3.40)}, B)
    if r3["t"]:
        ok("多義: 西の橋(継ぎ目8)を選んでも溝を渡れる")
    else:
        fail("多義: 継ぎ目8 を選ぶと溝を渡れない(詰み)")

    # ★負の継ぎ目(見ると壁が建つ)を【解いてしまった世界】でも先へ行けるか。
    #   ここが通らないと「見ただけで詰む」= 一番たちの悪い作りになる
    anti = [c for c in order if c.anti]
    if anti:
        w3 = World(G.ES)
        for c in order:
            if c.cid == 8:
                continue
            for sd in c.solids:
                w3.enable(sd["n"], sd["p"])
            for m in c.movers:
                w3.disable(m["n"])
        r4, _, _ = walk(w3, start, {"t": (58.6, 195.4, 7.60)}, B)
        if r4["t"]:
            ok("負の継ぎ目: 壁が建ってしまっても迂回路で先へ行ける(詰まない)")
        else:
            fail("負の継ぎ目: 壁が建つと詰む(迂回路が通っていない)")

    # ---------------------------------------------------- 合う場所の広さ
    print(NL + "[3] 継ぎ目ごとの『合う場所』")
    for c in sorted(conns, key=lambda x: x.cid):
        slots = range(len(c.shards)) if c.per_shard else [None]
        for only in slots:
            good, warm, best, bestp = field(c, flats[c.cid], None, only=only)
            area = len(good) * CELL * CELL
            tag = "継ぎ目%-2d(%-12s)%s" % (c.cid, c.note,
                                          "" if only is None else "[%d]" % only)
            if not good:
                fail("%s: 誤差が lock(%.1f°)を切る立ち位置が床の上に無い(最小 %.2f°)"
                     % (tag, c.lock, best))
                continue
            xs = [q[0] for q in good]; zs = [q[1] for q in good]
            w, d = max(xs) - min(xs) + CELL, max(zs) - min(zs) + CELL
            msg = ("%s: 確定域 %5.2fm2 (%.2f x %.2f m) 最小誤差 %.2f° / 予兆域 %5.1fm2"
                   % (tag, area, w, d, best, warm * CELL * CELL))
            if area < 0.08:
                fail(msg + "  ← 狭すぎる(見つけられない)")
            elif area > 10.00:
                # ★上限は昔 1.80 だった。当時は「広い = 歩いていたら勝手に確定する」だったが、
                #   いまは STILL(1.10m/s 以下)・DWELL 0.36 秒・視野 26 度の 3 つが要るので
                #   通りすがりでは決まらない。そして【印の上ならどこでも繋がる】方が大事。
                fail(msg + "  ← 広すぎる(歩いていて勝手に確定する)")
            else:
                ok(msg)
        if not c.touch and conn_error(c, tuple(c.focus)) > 0.01 and not c.per_shard:
            fail("継ぎ目%d: 焦点で誤差が 0 にならない(相似変換が壊れている)" % c.cid)

    # ---------------------------------------------------- 足場の連続性
    print("\n[4] 組み上がった足場")
    # 階段: C3_h* すべて(k=1 の実在段も含む)を z 順に見る
    st = []
    for name, e in world.byname.items():
        if name.startswith("C3_h"):
            p = e["transform"]["position"]
            real = None
            for c in conns:
                for s2 in c.solids:
                    if s2["n"] == name:
                        real = s2["p"]
            st.append((real or p, e["transform"]["scale"], name))
    st.sort(key=lambda t: t[0][2])
    prev = 0.0
    okstair = True
    for p, sc, name in st:
        top = p[1] + sc[1] / 2
        if top - prev > STEP_UP + 0.001:
            fail("階段の蹴上げが %.3f m (上限 %.2f): %s" % (top - prev, STEP_UP, name))
            okstair = False
        prev = top
    land = world.byname["C_land"]
    lt = land["transform"]["position"][1] + land["transform"]["scale"][1] / 2
    if lt - prev > STEP_UP + 0.001:
        fail("踊り場への段差が %.3f m" % (lt - prev))
        okstair = False
    if okstair:
        ok("階段 %d 段 + 踊り場、段差はすべて %.2f m 以下" % (len(st), STEP_UP))
    # 第三幕の大階段(実在。継ぎ目ではない)
    st3 = []
    for name, e in world.byname.items():
        if name.startswith("Q1_st"):
            t = e["transform"]
            st3.append((t["position"][2], t["position"][1] + t["scale"][1] / 2, name))
    st3.sort()
    prev3, ok3 = G.CHECKS[16]["y"] - 0.90, True
    for _z, top, name in st3:
        if top - prev3 > STEP_UP + 0.001:
            fail("第三幕の階段の蹴上げが %.3f m: %s" % (top - prev3, name))
            ok3 = False
        prev3 = top
    if ok3:
        ok("第三幕の大階段 %d 段、蹴上げはすべて %.2f m 以下" % (len(st3), STEP_UP))

    # 橋の高さ(床の上に載っているか)。★以前は「床と面一」を要求していたが、
    # 面一にすると板が床スラブと穴の見切りへ潜り込み、天端が同じ高さで重なって
    # ちらつく。いまは【床の上に載せる】= 0 以上、またげる高さ(0.32)以下。
    bt = []
    for s in conns[1].solids:
        e = world.byname[s["n"]]
        top = s["p"][1] + e["transform"]["scale"][1] / 2
        bt.append(top)
        if top < -0.02 or top > STEP_UP:
            fail("橋の天端 %.3f m: 床へ潜っているか、またげない高さ: %s" % (top, s["n"]))
    ok("橋は床の上に載っている(天端 %.2f m / またげる上限 %.2f)"
       % (max(bt) if bt else 0.0, STEP_UP))

    # ---------------------------------------------------- 同一平面の面(z ファイティング)
    # ★この作品で一番効く罠。「同じ場所に壁を 2 枚建てない」を機械で見張る。
    #   面が同じ平面に乗っていて、その面の上で 0.35m 角より広く重なっている組だけを拾う
    #   (0.30 = 壁厚 ぶんの角の柱は部屋の外なので無視してよい)。
    # ---------------------------------------------------- 床の目印は嘘をついていないか
    # ★この作品で一番人を殺した罠。確定域は【焦点と対象を結ぶ方向へ伸びた細長い管】
    #   なので、そこへ四角い印を被せると「印の上に立ってるのに繋がらない」になる。
    #   印の大きさ/向きは source/calib_marks.py が実測で決める。ここはその見張り。
    print("")
    print("[5] 床の目印(印の上ならどこに立っても繋がるか)")
    ISLN = {0: "A", 1: "D", 2: "C", 3: "B"}
    marks = {e["name"]: e for e in ents if e["name"].endswith("_mark")
             or e["name"].startswith("G1_ib")}
    nbad = 0
    for c in sorted(conns, key=lambda x: x.cid):
        slots = list(range(len(c.shards))) if c.per_shard else [None]
        for only in slots:
            nm = ("G1_ib" + ISLN[only]) if only is not None else ("C%d_mark" % c.cid)
            mk = marks.get(nm)
            if mk is None:
                continue
            mp = mk["transform"]["position"]
            ms = mk["transform"]["scale"]
            yaw = mk["transform"]["rotation"][1]
            F = (c.shards[only].get("focus") or c.focus) if only is not None else c.focus
            sn, cs = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
            hit = tot = 0
            worst = 0.0
            for a in range(11):
                for b in range(11):
                    u = -ms[0] / 2 + ms[0] * a / 10.0
                    v = -ms[2] / 2 + ms[2] * b / 10.0
                    x = mp[0] + u * cs + v * sn
                    z = mp[2] - u * sn + v * cs
                    k = (round(x / CELL), round(z / CELL))
                    if k not in flats[c.cid]:
                        continue
                    eye = (x, flats[c.cid][k] + EYE, z)
                    tot += 1
                    e2 = conn_error(c, eye, only)
                    worst = max(worst, e2)
                    if e2 < c.lock:
                        hit += 1
            if tot == 0:
                fail("%s: 印が床の上に無い" % nm)
                nbad += 1
                continue
            cov = 100.0 * hit / tot
            if cov < 99.9:
                fail("%s(継ぎ目%d): 印の上でも %.0f%% しか繋がらない(最悪 %.2f度 / lock %.2f度)"
                     % (nm, c.cid, cov, worst, c.lock))
                nbad += 1
    if nbad == 0:
        ok("印 %d 個すべて、上に立てばどこでも繋がる" % len(marks))

    print("")
    print("[6] 同一平面の面(z ファイティング)")
    EPSP, MINOV = 0.006, 0.35
    bx = []
    for e in ents:
        if "primitive" not in e:
            continue
        rr = e["transform"]["rotation"]
        if abs(rr[0]) > 0.01 or abs(rr[2]) > 0.01 or abs(rr[1]) % 180 > 0.01:
            continue
        pp, sc = e["transform"]["position"], e["transform"]["scale"]
        sx, sz = (sc[2], sc[0]) if abs(abs(rr[1]) - 90) < 0.01 else (sc[0], sc[2])
        bx.append((e["name"], (pp[0] - sx / 2, pp[1] - sc[1] / 2, pp[2] - sz / 2),
                   (pp[0] + sx / 2, pp[1] + sc[1] / 2, pp[2] + sz / 2)))
    gr = {}
    for i2, (nm2, lo2, hi2) in enumerate(bx):
        for gx in range(int(lo2[0] // 4.0), int(hi2[0] // 4.0) + 1):
            for gz in range(int(lo2[2] // 4.0), int(hi2[2] // 4.0) + 1):
                gr.setdefault((gx, gz), []).append(i2)
    seenp, nzf = set(), 0
    for cell in gr.values():
        for ii in range(len(cell)):
            for jj in range(ii + 1, len(cell)):
                key = (cell[ii], cell[jj])
                if key in seenp:
                    continue
                seenp.add(key)
                na, la, ha = bx[key[0]]
                nb2, lb, hb = bx[key[1]]
                if not all(la[q] < hb[q] + EPSP and lb[q] < ha[q] + EPSP for q in range(3)):
                    continue
                for ax in range(3):
                    o1, o2 = [q for q in range(3) if q != ax]
                    if (min(ha[o1], hb[o1]) - max(la[o1], lb[o1]) < MINOV or
                            min(ha[o2], hb[o2]) - max(la[o2], lb[o2]) < MINOV):
                        continue
                    if abs(ha[ax] - hb[ax]) < EPSP or abs(la[ax] - lb[ax]) < EPSP:
                        fail("同一平面: %s と %s (%s 軸 @%.3f)"
                             % (na, nb2, "xyz"[ax], ha[ax]))
                        nzf += 1
                        break
    if nzf == 0:
        ok("見える箱 %d 個、同一平面で重なっている面は無し" % len(bx))

    # ---------------------------------------------------- 明るさの粗い確認
    print("\n[7] 照明")
    lights = [(e["transform"]["position"], e["pointLight"]) for e in ents if "pointLight" in e]
    dark = 0
    # ★確認点は (x, 目の高さ, z)。第二幕は床が y=3.4 なので固定 1.5 で測ると
    #   全部「暗い」と出る(実際に嘘の警告を出した)
    PTS = [(0, 1.5, -7), (0, 1.5, 0), (0, 1.5, 12), (0, 1.5, 18), (-6.3, 1.5, 18.3),
           (0, 1.5, 28), (5.3, 1.5, 36), (5.5, 1.5, 44), (5.5, 1.5, 48), (-5.4, 1.5, 53.6),
           (0, 1.5, 56), (6.1, 4.9, 61), (6.1, 4.9, 66), (6.1, 4.9, 74), (6.1, 4.9, 79),
           (6.1, 4.9, 88), (6.6, 4.9, 92), (6.0, 4.9, 100), (6.0, 4.9, 106),
           (7.4, 4.9, 118), (13.0, 4.9, 112), (22.5, 4.9, 118), (18.7, 4.9, 126.5),
           (25.0, 4.9, 126.5), (22.0, 4.9, 138), (18.2, 4.9, 146.6), (22.0, 4.9, 152),
           (22.0, 7.3, 160), (22.0, 7.3, 166),
           # ---- 第三幕(床 5.8 -> 目 7.5 / 床 7.6 -> 目 9.3) ----
           (22.0, 7.3, 173), (18.0, 7.3, 180), (22.0, 7.3, 179), (22.0, 7.3, 188),
           (22.0, 7.3, 192.5), (18.3, 9.3, 195.0), (24.0, 9.1, 195.2), (18.3, 8.9, 200.5),
           (32.0, 9.1, 195.4), (38.0, 9.1, 195.4), (43.2, 9.1, 195.4),
           (49.6, 9.1, 195.4), (53.0, 9.1, 202.6), (58.6, 9.1, 195.4),
           (68.0, 9.1, 192.6), (68.0, 9.1, 200.0), (68.0, 9.1, 209.0), (68.0, 9.1, 213.0),
           # ---- 第五幕(床 10.60 -> 目 12.30 / 棚 11.80 -> 13.50 / 踊り場 13.30 -> 15.00) ----
           (68.0, 12.3, 255.0), (68.0, 12.3, 262.0), (68.0, 12.3, 268.0),
           (66.8, 12.3, 265.6), (68.0, 12.3, 278.0), (68.0, 12.3, 287.0),
           (68.0, 12.3, 289.0), (77.2, 12.3, 293.0), (77.0, 12.9, 299.0),
           (68.0, 13.2, 300.8), (61.0, 14.1, 300.8), (56.3, 14.7, 299.0),
           (56.0, 14.7, 305.0)]
    for (x, yy, z) in PTS:
        s = 0.0
        for p, L in lights:
            d = math.dist((x, yy, z), (p[0], p[1], p[2]))
            if d < L["range"]:
                s += L["intensity"] * max(0.0, 1.0 - d / L["range"]) ** 2
        if s < 0.35:
            print("  [!!] (%.1f,%.1f) が暗い (照度指標 %.2f)" % (x, z, s))
            dark += 1
    if dark == 0:
        ok("順路上の %d 点すべてに灯が届いている" % len(PTS))

    # ------------------------------------------------ 箱の貫通(斜めの箱も見る)
    # ★[1] は【当たり判定を持つ物】としか比べず、[6] は【軸に沿った箱】しか見ない。
    #   その隙間で、第一幕の斜めの橋が床と穴の壁に 24cm めり込んだまま通っていた。
    print(NL + "[8] 箱の貫通(OBB。斜めの箱も、組み上がった後も見る)")
    shard_of, keep = {}, {}
    for c in conns:
        for si, sh in enumerate(c.shards):
            for r in sh["ents"]:
                shard_of.setdefault(r["n"], []).append((c.cid, si))
    for label in ("浮遊中", "組み上がり後"):
        if label == "組み上がり後":
            for c in conns:
                for sh in c.shards:
                    for r in sh["ents"]:
                        e = world.byname.get(r["n"])
                        if e is None:
                            continue
                        keep.setdefault(r["n"], (list(e["transform"]["position"]),
                                                 list(e["transform"]["scale"])))
                        e["transform"]["position"] = list(r["p"])
                        e["transform"]["scale"] = list(r["s"])
        deep, flat = obb_pairs(ents, shard_of)
        for pen, na, nb in deep[:30]:
            fail("%s: %s が %s に %.2fm めり込んでいる" % (label, na, nb, pen))
        if len(deep) > 30:
            fail("%s: ほかにも %d 組" % (label, len(deep) - 30))
        for na, nb, y in flat[:30]:
            fail("%s: %s と %s の面が同じ高さ %.3f で重なっている(ちらつく)"
                 % (label, na, nb, y))
        if len(flat) > 30:
            fail("%s: 同じ高さの面が ほかにも %d 組" % (label, len(flat) - 30))
        if not deep and not flat:
            ok("%s: 破片・斜めの箱がらみの貫通なし" % label)
    for nm, (pp, ss) in keep.items():
        world.byname[nm]["transform"]["position"] = pp
        world.byname[nm]["transform"]["scale"] = ss

    print("\n" + ("=" * 68))
    print("RESULT: " + ("PASS" if OK else "FAIL"))
    return 0 if OK else 1


if __name__ == "__main__":
    sys.exit(main())
