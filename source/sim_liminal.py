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

    def tops(self, x, z):
        out = []
        for b in self.near(x, z):
            if b.contains_xz(x, z):
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


def walk(world, start, targets, bounds, maxcells=900000):
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


def conn_error(c, eye):
    e = 0.0
    for sh in c.shards:
        if sh["k"] < 0.999:
            e = max(e, align_error(eye, c.focus, sh["k"], sh["pts"]))
    return e


FOCUS_LOCK = 7.0     # 実行時と同じ足切り(焦点から遠いと確定しない)


def field(c, seen, floor_of, half=3.6):
    """焦点の周りを走査し、床がある所だけ誤差を測る。"""
    fx, fz = c.focus[0], c.focus[2]
    good, warm, best, bestp = [], 0, 1e9, None
    n = int(half / CELL)
    for iz in range(-n, n + 1):
        for ix in range(-n, n + 1):
            x, z = fx + ix * CELL, fz + iz * CELL
            k = (round(x / CELL), round(z / CELL))
            if k not in seen:
                continue
            # ★焦点と違う高さの床(溝の底など)は数えない。目の高さが変われば別の話
            if abs(seen[k] + EYE - c.focus[1]) > 0.4:
                continue
            eye = (x, seen[k] + EYE, z)
            if math.dist(eye, tuple(c.focus)) > FOCUS_LOCK:
                continue
            err = conn_error(c, eye)
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
    bounds = (-10.0, -10.0, 32.0, 176.0)
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
        10: (None, None),
    }
    flats = {}
    order = sorted(conns, key=lambda c: c.cid)
    for c in order:
        fx, fz, fy = c.focus[0], c.focus[2], c.focus[1] - EYE
        r, seen, flat = walk(world, start, {"F%d" % c.cid: (fx, fz, fy)}, B)
        flats[c.cid] = flat
        if not r["F%d" % c.cid]:
            fail("継ぎ目%d(%s): 焦点 (%.1f, %.1f) へ歩いて行けない" % (c.cid, c.note, fx, fz))
        before, after = PLAN[c.cid]
        if before and standing(seen, *before):
            fail("継ぎ目%d を解く前に (%.1f, %.1f) へ行けてしまう" % (c.cid, before[0], before[1]))
        if c.cid == 8:
            continue                      # 多義の片割れ。7 を採った世界で進む(8 は下で別途検査)
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

    # ---------------------------------------------------- 合う場所の広さ
    print(NL + "[3] 継ぎ目ごとの『合う場所』")
    for c in order:
        good, warm, best, bestp = field(c, flats[c.cid], None)
        area = len(good) * CELL * CELL
        if not good:
            fail("継ぎ目%d(%s): 誤差が lock(%.1f°)を切る立ち位置が床の上に無い(最小 %.2f°)"
                 % (c.cid, c.note, c.lock, best))
            continue
        xs = [q[0] for q in good]; zs = [q[1] for q in good]
        w, d = max(xs) - min(xs) + CELL, max(zs) - min(zs) + CELL
        msg = ("継ぎ目%-2d(%-12s): 確定域 %5.2fm2 (%.2f x %.2f m) 最小誤差 %.2f° / 予兆域 %5.1fm2"
               % (c.cid, c.note, area, w, d, best, warm * CELL * CELL))
        if area < 0.10:
            fail(msg + "  ← 狭すぎる(見つけられない)")
        elif area > 1.80:
            fail(msg + "  ← 広すぎる(歩いていて勝手に確定する)")
        else:
            ok(msg)
        if conn_error(c, (c.focus[0], c.focus[1], c.focus[2])) > 0.01:
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

    # 橋の高さ(床と面一か)
    for s in conns[1].solids:
        e = world.byname[s["n"]]
        top = s["p"][1] + e["transform"]["scale"][1] / 2
        if abs(top) > 0.02:
            fail("橋の天端が床と面一でない: %s (%.3f)" % (s["n"], top))
    ok("橋の天端は床と面一")

    # ---------------------------------------------------- 明るさの粗い確認
    print("\n[5] 照明")
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
           (22.0, 7.3, 160), (22.0, 7.3, 166)]
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

    print("\n" + ("=" * 68))
    print("RESULT: " + ("PASS" if OK else "FAIL"))
    return 0 if OK else 1


if __name__ == "__main__":
    sys.exit(main())
