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


class World:
    def __init__(self, entities):
        self.bodies = []
        self.byname = {}
        for e in entities:
            self.byname[e["name"]] = e
            if "rigidBody" in e:
                t = e["transform"]
                self.bodies.append(Body(e["name"], t["position"], t["scale"], t["rotation"][1]))
        self.index = {b.name: b for b in self.bodies}

    def enable(self, name, pos):
        self.index[name].move(pos)

    def disable(self, name):
        b = self.index[name]
        b.move((b.cx, b.cy - 500.0, b.cz))

    def tops(self, x, z):
        out = []
        for b in self.bodies:
            if b.contains_xz(x, z):
                out.append(round(b.top(), 3))
        return sorted(set(out))

    def blocked(self, x, z, h):
        """★『またげる高さ(stepHeight)以下の物は壁にならない』を必ず入れること。
        入れ忘れると階段の次の段が体の半径に入った瞬間に壁扱いになり、
        『階段があるのに一段も登れない』という嘘の詰みが出る(実際に踏んだ)。"""
        hi = h + 1.75
        for b in self.bodies:
            if b.top() <= h + STEP_UP + 0.001:
                continue
            if b.cy - b.hy >= hi - 0.001:
                continue
            if b.contains_xz(x, z, RADIUS):
                return True
        return False

    def headroom(self, x, z, h):
        best = 99.0
        for b in self.bodies:
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


def field(c, seen, floor_of, half=4.0):
    """焦点の周りを 4m 角で走査し、床がある所だけ誤差を測る。"""
    fx, fz = c.focus[0], c.focus[2]
    good, warm, best, bestp = [], 0, 1e9, None
    n = int(half / CELL)
    for iz in range(-n, n + 1):
        for ix in range(-n, n + 1):
            x, z = fx + ix * CELL, fz + iz * CELL
            k = (round(x / CELL), round(z / CELL))
            if k not in seen:
                continue
            eye = (x, seen[k] + EYE, z)
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
    bounds = (-9.5, -10.0, 9.5, 86.0)
    print("=" * 68)
    print("stagedemo3 / liminal — 机上シミュレーション")
    print("=" * 68)
    print("entities=%d  colliders=%d  joints=%d" % (len(ents), len(world.bodies), len(conns)))

    # ---------------------------------------------------- 破片の干渉
    print("\n[1] 破片(ずれた状態)の干渉")
    shard_boxes = []
    for c in conns:
        for si, sh in enumerate(c.shards):
            if sh["k"] >= 0.999:
                continue
            for r in sh["ents"]:
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
    print("\n[2] 順路の通し歩き(継ぎ目を1つずつ確定させる)")
    start = (0.0, -6.0, 0.0)
    B = bounds

    def apply(c):
        for s in c.solids:
            world.enable(s["n"], s["p"])
        for m in c.movers:
            world.disable(m["n"])

    stages = []
    r, seen, flat = walk(world, start, {"F1": (conns[0].focus[0], conns[0].focus[2], 0.0)}, B)
    stages.append(("開始 → 継ぎ目1の焦点", r, flat, seen))
    apply(conns[0])
    r, seen, flat = walk(world, start, {"F2": (conns[1].focus[0], conns[1].focus[2], 0.0),
                                        "穴の縁": (-5.0, 22.4, 0.0)}, B)
    stages.append(("継ぎ目1 → 事務室・継ぎ目2の焦点", r, flat, seen))
    apply(conns[1])
    r, seen, flat = walk(world, start, {"対岸": (5.3, 36.0, 0.0),
                                        "タイル室": (5.5, 47.5, 0.0),
                                        "F3": (conns[2].focus[0], conns[2].focus[2], 0.0)}, B)
    stages.append(("継ぎ目2(橋) → 対岸・タイル室・継ぎ目3の焦点", r, flat, seen))
    apply(conns[2])
    r, seen, flat = walk(world, start, {"踊り場": (6.1, 61.0, 3.40),
                                        "F4": (conns[3].focus[0], conns[3].focus[2], 3.40)}, B)
    stages.append(("継ぎ目3(階段) → 踊り場・上階・継ぎ目4の焦点", r, flat, seen))
    apply(conns[3])
    r, seen, flat = walk(world, start, {"白い部屋": (6.1, 82.6, 3.40)}, B)
    stages.append(("継ぎ目4(出口) → 白い部屋", r, flat, seen))

    for label, reach, flat, seen in stages:
        miss = [k for k, v in reach.items() if not v]
        if miss:
            fail("%s: 到達できない %s" % (label, miss))
        else:
            ok("%s: %s 到達 (状態 %d)" % (label, "/".join(reach.keys()), len(seen)))

    def standing(seen, x, z, h, tol=0.35):
        cx, cz = round(x / CELL), round(z / CELL)
        return any(abs(v - h) < tol for (kx, kz, _), v in seen.items() if kx == cx and kz == cz)

    # 各段階で「まだ先へ行けない」ことも確認(順序が飛ばされない)
    if standing(stages[0][3], 0.0, 20.0, 0.0):
        fail("継ぎ目1を解く前に事務室へ入れてしまう")
    else:
        ok("継ぎ目1を解くまで扉は塞がっている")
    if standing(stages[1][3], 5.3, 36.0, 0.0):
        fail("橋なしで穴を渡れてしまう")
    else:
        ok("橋が無いと穴は渡れない")
    if standing(stages[2][3], 6.1, 63.6, 3.40):
        fail("階段なしで上階へ行けてしまう")
    else:
        ok("階段が無いと上階へ行けない")
    if standing(stages[3][3], 6.1, 82.6, 3.40):
        fail("継ぎ目4を解く前に出口へ入れてしまう")
    else:
        ok("継ぎ目4を解くまで出口は塞がっている")

    # ---------------------------------------------------- 合う場所の広さ
    print("\n[3] 継ぎ目ごとの『合う場所』")
    for i, c in enumerate(conns):
        good, warm, best, bestp = field(c, stages[i][2], None)
        area = len(good) * CELL * CELL
        if not good:
            fail("継ぎ目%d: 誤差が lock(%.1f°)を切る立ち位置が床の上に無い(最小 %.2f°)"
                 % (c.cid, c.lock, best))
            continue
        xs = [p[0] for p in good]; zs = [p[1] for p in good]
        w, d = max(xs) - min(xs) + CELL, max(zs) - min(zs) + CELL
        msg = ("継ぎ目%d(%s): 確定域 %.2fm2 (%.2f x %.2f m) 最小誤差 %.2f° / 予兆域 %.1fm2"
               % (c.cid, c.note, area, w, d, best, warm * CELL * CELL))
        if area < 0.10:
            fail(msg + "  ← 狭すぎる(見つけられない)")
        elif area > 1.60:
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
    for (x, z) in [(0, -7), (0, 0), (0, 12), (0, 18), (-6.3, 18.3), (0, 28), (5.3, 36),
                   (5.5, 44), (5.5, 48), (-5.4, 53.6), (0, 56), (6.1, 61), (6.1, 66),
                   (6.1, 74), (6.1, 79)]:
        s = 0.0
        for p, L in lights:
            d = math.dist((x, 1.5, z), (p[0], p[1], p[2]))
            if d < L["range"]:
                s += L["intensity"] * max(0.0, 1.0 - d / L["range"]) ** 2
        if s < 0.35:
            print("  [!!] (%.1f,%.1f) が暗い (照度指標 %.2f)" % (x, z, s))
            dark += 1
    if dark == 0:
        ok("順路上の 15 点すべてに灯が届いている")

    print("\n" + ("=" * 68))
    print("RESULT: " + ("PASS" if OK else "FAIL"))
    return 0 if OK else 1


if __name__ == "__main__":
    sys.exit(main())
