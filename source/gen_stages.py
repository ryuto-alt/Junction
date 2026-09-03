# -*- coding: utf-8 -*-
"""JUNCTION / 継ぎ目 v6 のステージを生成する。シーン JSON はここが唯一の正。契約書は docs/V6.md。

実行:
  python source/gen_stages.py     # scenes/*.json, Junction.lua の STAGES, models/manifest.json
  壁/廊下のモデルが足りない時は BlenderMCP から blender_kit.py(JX_MANIFEST_ONLY=True)を実行する。

★v6 の世界(2026-09-03): 【比較できる物を一切見せない】
  ・部屋には縮尺 S がある(0.5 / 1 / 2)。壁・天井・扉・家具・照明・テクスチャの目地まで全部 S 倍。
    中に居る限り、どの部屋も「普通の部屋」にしか見えない。同じ間取りを縮尺違いで並べる。
  ・部屋と部屋は 4m の壁を貫く【先細りの廊下】で繋がる。両端の口はそれぞれの部屋の縮尺の扉。
    廊下の中で自分の縮尺も連続的に変わる(Junction.lua)ので、廊下の絵は歩いても変わらない。
  ・縮尺が無い(絶対寸法の)物は 柵 1.7m / 隙間 1.0m / 溝 4.6m / 高い敷居 0.9m / 出口の扉 だけ。
    これが謎解きであり、唯一の手がかり(「あの部屋では柵が膝の高さ」「出口が小さく見える」)。
  ・口の大きさは必ずその部屋の縮尺の扉。大きさ違いの口を同じ壁に並べる U 継ぎ目は廃止。

★寸法は source/blender_kit.py の WALLT / DOORW / DOORH と【必ず一致】させること。
"""
import json, math, random, os, hashlib

random.seed(20260903)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "scenes")
MODELS = os.path.join(HERE, "..", "assets", "models")

WALLT = 0.3      # 壁モデルの厚み(単位寸法。部屋の縮尺が掛かる)
GAP = 4.0        # 隣り合う部屋の内寸の面と面の距離 = 廊下の長さ(絶対)
DOOR_W, DOOR_H = 2.0, 2.6     # 扉(単位寸法。部屋の縮尺が掛かる)
WIN_W, WIN_H, WIN_SILL = 3.6, 2.0, 1.0   # 窓(単位寸法)

SCALES = [0.125, 0.25, 0.5, 1.0, 2.0]   # Body_0..4。★Junction.lua の SCALES と一致
BODY_H = 1.8
EYE_H = 1.7
JUMP_H0 = 0.9
STEP_K = 0.25
SPEED0 = 3.4
GRAV = 14.0      # ★エンジン(Jolt)の重力は 9.8 ではなく 14。実測のジャンプ高さと一致
JD_K = 1.3       # FreeLook.lua の FAST(走り)

# 絶対寸法の物
BAR_H = 1.70     # 柵。登れる高さ climb_h: 1 -> 1.15 / 2 -> 2.30
EAVE_GAP = 1.00  # 隙間。体高 1.8*S < 1.0 = 0.5 以下
PIT_W = 4.6      # 溝。走り跳び: 1 -> 3.7 / 歩き跳び 2 -> 5.8
SILL_HI = 0.9    # 高い敷居。climb_h(0.5)=0.58 は登れない = 一方通行
PIT_DEPTH = 7.0


def jump_h(s):
    return JUMP_H0 * s


def climb_h(s):
    return jump_h(s) + STEP_K * s


def jump_dist(s):
    air = 2.0 * math.sqrt(2.0 * jump_h(s) / GRAV)
    return JD_K * SPEED0 * (s ** 0.6) * air + 2.0 * 0.35 * s * 0.766


def body_cc(s):
    r = 0.35 * s
    return dict(radius=r, halfHeight=BODY_H * 0.5 * s - r, stepHeight=STEP_K * s)


SHAPES = {
    "box12": dict(ix=12.0, iz=12.0, h=6.0, tag="", floor="models/floor.gltf",
                  ceil="models/ceiling.gltf",
                  lights=[(-3.2, -3.2), (3.2, -3.2), (-3.2, 3.2), (3.2, 3.2)], lrange=22.0),
    "hall20": dict(ix=20.0, iz=20.0, h=7.0, tag="20", floor="models/floor20.gltf",
                   ceil="models/ceiling20.gltf",
                   lights=[(x, z) for z in (-6.4, 0.0, 6.4) for x in (-6.4, 0.0, 6.4)],
                   lrange=24.0),
    "corr18": dict(ix=18.0, iz=8.0, h=3.2, tag="18", floor="models/floor18x8.gltf",
                   ceil="models/ceiling18x8.gltf",
                   lights=[(-6.0, 0.0), (0.0, 0.0), (6.0, 0.0)], lrange=15.0),
    # ★v6.1 回廊用。壁・床・天井を manifest(Blender)で出す
    "corr12": dict(ix=3.0, iz=12.0, h=3.2, tag="", floor=None, ceil=None, mf=True,
                   lights=[(0.0, -4.0), (0.0, 0.0), (0.0, 4.0)], lrange=10.0),
}
WALLTAG = {"box12": ("", ""), "hall20": ("20", "20"), "corr18": ("18", "8"), "corr12": ("", "")}

C_WALL = [0.62, 0.60, 0.55]
C_FLOOR = [0.24, 0.20, 0.12]
C_CEIL = [0.72, 0.72, 0.70]
C_GOAL = [0.10, 0.75, 0.50]
C_DIV = [0.55, 0.56, 0.54]
C_PAINT = [0.90, 0.89, 0.86]
C_PIT = [0.05, 0.05, 0.06]
HIDE_Y = -200.0

WALLS = {
    "N": {"yaw": 180.0, "axis": "z", "sign": +1},
    "S": {"yaw": 0.0, "axis": "z", "sign": -1},
    "E": {"yaw": 270.0, "axis": "x", "sign": +1},
    "W": {"yaw": 90.0, "axis": "x", "sign": -1},
}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


def guid():
    return "%016x" % random.getrandbits(64)


def base(name, pos, rot=(0, 0, 0), scale=(1, 1, 1), parent=None):
    e = {"guid": guid(), "name": name,
         "transform": {"position": [float(pos[0]), float(pos[1]), float(pos[2])],
                       "rotation": [float(rot[0]), float(rot[1]), float(rot[2])],
                       "scale": [float(scale[0]), float(scale[1]), float(scale[2])]}}
    if parent:
        e["parentGuid"] = parent
    return e


def box(name, pos, scale, color, rot=(0, 0, 0), collide=True, rough=0.92, parent=None,
        prim="box", kinematic=False, visible=True):
    e = base(name, pos, rot, scale, parent)
    if visible:
        e["primitive"] = prim
        e["color"] = list(color)
        e["material"] = {"metallic": 0.0, "roughness": rough}
    if collide:
        e["boxCollider"] = {"halfExtents": [0.5, 0.5, 0.5], "offset": [0.0, 0.0, 0.0]}
        e["rigidBody"] = {"angularDamping": 0.01, "continuousCollision": False,
                          "friction": 0.6, "linearDamping": 0.02, "mass": 1.0,
                          "motionType": 1 if kinematic else 0,
                          "restitution": 0.0, "useGravity": False}
    return e


def model(name, path, pos, yaw=0.0, parent=None, scale=(1, 1, 1)):
    e = base(name, pos, (0.0, yaw, 0.0), scale, parent)
    e["meshRenderer"] = {"modelPath": path}
    return e


def plight(name, pos, color, intensity, rng, parent=None):
    e = base(name, pos, parent=parent)
    e["pointLight"] = {"castShadows": False, "color": list(color),
                       "intensity": float(intensity), "range": float(rng)}
    return e


def marker(name, pos, yaw=0.0, parent=None):
    return base(name, pos, (0.0, float(yaw), 0.0), parent=parent)


def group(ents, name, parent=None):
    e = marker(name, (0.0, 0.0, 0.0), 0.0, parent)
    ents.append(e)
    return e["guid"]


def key_of(obj):
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.md5(s.encode()).hexdigest()[:8]


# ---------------------------------------------------------------- 幾何
def dims(r):
    """部屋の世界寸法。(半幅x, 半幅z, 天井高, 縮尺)"""
    S = SHAPES[r["shape"]]
    k = r["scale"]
    return S["ix"] * 0.5 * k, S["iz"] * 0.5 * k, S["h"] * k, k


def floor_y(r, wall=None):
    """部屋の床の高さ(絶対)。スロープは北の口だけ rise ぶん高い。"""
    y = r.get("y", 0.0)
    S = SHAPES[r["shape"]]
    if wall == "N" and S.get("rise"):
        y += S["rise"] * r["scale"]
    return y


def wall_frame(r, w):
    hx, hz, ch, k = dims(r)
    cx, cz = r["at"]
    info = WALLS[w]
    yaw = info["yaw"]
    rgt = (math.cos(math.radians(yaw)), -math.sin(math.radians(yaw)))
    S = SHAPES[r["shape"]]
    if info["axis"] == "z":
        face = (cx, cz + info["sign"] * hz)
        n = (0.0, float(info["sign"]))
        along = (1.0, 0.0)
        Lu = S["ix"] + WALLT
    else:
        face = (cx + info["sign"] * hx, cz)
        n = (float(info["sign"]), 0.0)
        along = (0.0, 1.0)
        Lu = S["iz"] + WALLT
    return dict(face=face, n=n, along=along, right=rgt, Lu=Lu, Hu=S["h"], L=Lu * k, h=ch, k=k,
                yaw=yaw, tag=WALLTAG[r["shape"]][0 if info["axis"] == "z" else 1])


class World:
    def __init__(self, st):
        self.st = st
        self.rooms = {r["id"]: r for r in st["rooms"]}
        self.openings = {}     # (room, wall) -> [dict(off(世界の壁沿い), w, h, y0, kind, id)]
        self.mouths = {}       # mouth id -> dict
        self.links = {}
        self.tunnels = []      # Lua へ
        self.manifest = {}
        self.fixtures = {}
        self.ents = []

    # ---- 口。off は部屋の【単位】座標(縮尺前)。世界では off*k ----
    def add_opening(self, rid, wall, off_u, kind, sill, oid):
        r = self.rooms[rid]
        fr = wall_frame(r, wall)
        k = fr["k"]
        fy = floor_y(r, wall)
        if kind == "door":
            w, h = DOOR_W * k, DOOR_H * k
            y0 = fy + sill
        else:
            w, h, y0 = WIN_W * k, WIN_H * k, fy + WIN_SILL * k
        off = off_u * k
        if abs(off) + w * 0.5 > fr["L"] * 0.5 - 0.6 * k:
            raise SystemExit("%s: %s.%s の口 %s が壁からはみ出す(off=%.1f)" % (self.st["name"], rid, wall, oid, off_u))
        lst = self.openings.setdefault((rid, wall), [])
        for o in lst:
            if abs(o["off"] - off) < (o["w"] + w) * 0.5 + 0.4 * k:
                raise SystemExit("%s: %s.%s で口 %s と %s が重なる" % (self.st["name"], rid, wall, o["id"], oid))
        lst.append(dict(off=off, w=w, h=h, y0=y0, kind=kind, id=oid))
        pos = (fr["face"][0] + fr["along"][0] * off, fr["face"][1] + fr["along"][1] * off)
        m = dict(room=rid, wall=wall, off=off, size=k, sill=y0, sillRel=(y0 - fy), pos=pos, w=w, h=h, n=fr["n"],
                 along=fr["along"], kind=kind)
        self.mouths[oid] = m
        return m

    def partner_room(self, rid, wall, pos):
        fr = wall_frame(self.rooms[rid], wall)
        n = fr["n"]
        q = (pos[0] + n[0] * GAP, pos[1] + n[1] * GAP)
        for oid, r in self.rooms.items():
            if oid == rid:
                continue
            w2 = OPPOSITE[wall]
            f2 = wall_frame(r, w2)
            if WALLS[wall]["axis"] == "z":
                if abs(f2["face"][1] - q[1]) > 1e-3:
                    continue
                off2 = q[0] - f2["face"][0]
            else:
                if abs(f2["face"][0] - q[0]) > 1e-3:
                    continue
                off2 = q[1] - f2["face"][1]
            if abs(off2) < f2["L"] * 0.5:
                return oid, w2, off2 / f2["k"]
        raise SystemExit("%s: %s.%s の向かい(4m 先)に部屋が無い pos=%s" % (self.st["name"], rid, wall, pos))

    # ---- 廊下(先細り)。a = 部屋側の口、b = 向こう ----
    def frustum(self, g, name, ma, mb, glass=False, L=None, solid=False):
        """口 a から口 b へ 4m の先細り廊下。見た目は Blender の台形メッシュ、
        当たり判定は 8 段の見えない箱。★中に灯りは置かない(部屋の光が差し込むだけ)。"""
        n, al = ma["n"], ma["along"]
        zax = abs(n[1]) > 0.5
        L = L or GAP
        wa, ha, ya = ma["w"], ma["h"], ma["sill"]
        wb, hb, yb = mb["w"], mb["h"], mb["sill"]
        spec = dict(tunnel=True, wa=round(wa, 3), ha=round(ha, 3), ya=round(ya, 3),
                    wb=round(wb, 3), hb=round(hb, 3), yb=round(yb, 3), L=round(L, 3), v=2)
        mname = "tn_%s" % key_of(spec)
        self.manifest[mname] = spec
        yaw = math.degrees(math.atan2(n[0], n[1]))
        self.ents.append(model("TunM_%s" % name, "models/%s.gltf" % mname,
                               (ma["pos"][0], 0.0, ma["pos"][1]), yaw, g))
        N = 8

        def at(t, lat):
            return (ma["pos"][0] + n[0] * t + al[0] * lat, ma["pos"][1] + n[1] * t + al[1] * lat)

        def S3(w, h, dp):
            return (w, h, dp) if zax else (dp, h, w)

        for i in range(N):
            t0, t1 = L * i / N, L * (i + 1) / N
            k0, k1 = i / N, (i + 1) / N
            # 区間の【狭い方】に合わせる = メッシュより内側に当たり判定(壁に食い込まない)
            w = min(wa + (wb - wa) * k0, wa + (wb - wa) * k1)
            y0 = max(ya + (yb - ya) * k0, ya + (yb - ya) * k1)
            ytop = min(ya + ha + (yb + hb - ya - ha) * k0, ya + ha + (yb + hb - ya - ha) * k1)
            tm = (t0 + t1) * 0.5
            # ★区間の長さは seg。ここを L という名前にすると外側の L(廊下の全長)を潰してしまい、
            #   2 個目以降の判定箱が全部入口に折り重なる(実測で「扉に入れない」になった)
            seg = t1 - t0 + 0.02
            x, z = at(tm, 0)
            self.ents.append(box("Tun_%s_%d_F" % (name, i), (x, y0 - 0.15, z), S3(w + 0.6, 0.3, seg),
                                 C_WALL, parent=g, visible=False))
            self.ents.append(box("Tun_%s_%d_C" % (name, i), (x, ytop + 0.15, z), S3(w + 0.6, 0.3, seg),
                                 C_WALL, parent=g, visible=False))
            for j, sg in enumerate((-1, 1)):
                x2, z2 = at(tm, sg * (w * 0.5 + 0.15))
                self.ents.append(box("Tun_%s_%d_S%d" % (name, i, j), (x2, (y0 + ytop) * 0.5, z2),
                                     S3(0.3, ytop - y0 + 0.6, seg), C_WALL, parent=g, visible=False))
        if solid:   # 偽の廊下: 一番奥に蓋をする
            x, z = at(L + 0.15, 0)
            self.ents.append(box("Back_%s" % name, (x, yb + hb * 0.5, z),
                                 S3(wb + 0.6, hb + 0.6, 0.3), C_WALL, parent=g, visible=False))
        if glass:
            x, z = at(L * 0.5, 0)
            wm, hm = (wa + wb) * 0.5, (ha + hb) * 0.5
            ym = (ya + yb) * 0.5
            self.ents.append(box("Glass_%s" % name, (x, ym + hm * 0.5, z), S3(wm + 0.2, hm + 0.4, 0.2),
                                 C_WALL, parent=g, visible=False))

    def seam(self, sp):
        sid = sp["id"]
        sill = sp.get("sill", 0.0)
        ma = self.add_opening(sp["room"], sp["wall"], sp["off"], "door", sill, sid + "a")
        rid2, w2, off2 = self.partner_room(sp["room"], sp["wall"], ma["pos"])
        mb = self.add_opening(rid2, w2, off2, "door", sill, sid + "b")
        self.links[sid + "a"] = sid + "b"
        self.links[sid + "b"] = sid + "a"
        g = group(self.ents, "Seam %s" % sid, self.g_seams)
        self.frustum(g, sid, ma, mb)
        n = ma["n"]
        # ★通路の中に弱い灯りを 1 つ置く。v7 は「部屋の光が差し込むだけ」だったので、
        #   白い壁に白い開口が空いているだけの絵になり、【壁にしか見えない=進めないと思う】
        #   という指摘を受けた(v8)。奥に光源があると床と側壁に勾配が出て、穴だと一目で分かる。
        #   偽の廊下(fake)は自前の照明列を持つのでここは通らない。
        for tt, ii in ((GAP * 0.62, 0), (GAP * 0.95, 1)):
            lx = ma["pos"][0] + n[0] * tt
            lz = ma["pos"][1] + n[1] * tt
            kk = ma["size"] + (mb["size"] - ma["size"]) * (tt / GAP)
            ly = ma["sill"] + (mb["sill"] - ma["sill"]) * (tt / GAP) + (ma["h"] + (mb["h"] - ma["h"]) * (tt / GAP)) * 0.86
            self.ents.append(plight("SeamL_%s_%d" % (sid, ii), (lx, ly, lz),
                                    (0.98, 0.96, 0.90), 2.4 + 1.6 * ii, 4.0 * kk + 2.0, g))
        self.tunnels.append(dict(id=sid, ax=ma["pos"][0], az=ma["pos"][1], nx=n[0], nz=n[1], L=GAP,
                                 sa=ma["size"], sb=mb["size"], wa=ma["w"], wb=mb["w"], y0=ma["sill"],
                                 a=sid + "a", b=sid + "b"))

    def fake(self, sp):
        """★偽の廊下(強制遠近法)。奥行き 2.5m の箱を、20m の廊下に見えるよう先細りにする。
        奥の口の見かけの角度 = 本物の 20m 先の口の角度 なので、入口からは【区別がつかない】。
        2 歩で突き当りに手が届き、そこで嘘が目の前で崩れる(Superliminal の「廊下だと思ったら壁」)。
        ★これは絵として見える錯覚。プレイヤーが自分で確かめられるのが肝。"""
        fid = sp["id"]
        ma = self.add_opening(sp["room"], sp["wall"], sp["off"], "door", 0.0, fid)
        D = sp.get("depth", 2.5)          # 実際の奥行き
        LOOK = sp.get("look", 20.0)       # 見せかけの奥行き
        r = D / LOOK
        mb = dict(w=ma["w"] * r, h=ma["h"] * r, sill=ma["sill"] + ma["h"] * 0.5 * (1 - r),
                  n=ma["n"], along=ma["along"], pos=ma["pos"])
        g = group(self.ents, "Fake %s" % fid, self.g_seams)
        self.frustum(g, fid, ma, mb, L=D, solid=True)
        n, al = ma["n"], ma["along"]
        zax = abs(n[1]) > 0.5

        def at(t, lat):
            return (ma["pos"][0] + n[0] * t + al[0] * lat, ma["pos"][1] + n[1] * t + al[1] * lat)

        # 天井の照明も同じ比で縮める。これが無いと「奥だけ暗い箱」に見えてバレる
        for i, dz in enumerate((5.0, 10.0, 15.0)):
            t = dz * r
            rr = 1.0 - (dz / LOOK) * (1 - r)
            x, z = at(t, 0)
            hh = ma["sill"] + ma["h"] * 0.5 + (ma["h"] * 0.5 - 0.02) * rr
            self.ents.append(model("FakeT_%s_%d" % (fid, i), "models/troffer.gltf", (x, hh, z), 0.0, g,
                                   (rr, rr, rr)))
            self.ents.append(plight("FakeL_%s_%d" % (fid, i), (x, hh - 0.1 * rr, z),
                                    (0.98, 0.96, 0.90), 3.0 * rr * rr + 0.3, 3.0 * rr + 0.4, g))
        # ★突き当りに【小さな出口の扉】。20m 先の緑の扉に見える = ここへ行くしかないと思わせる餌。
        #   実物と同じ物を r 倍で置くので、見かけの角度は本物とぴったり同じになる。
        x, z = at(D - 0.06, 0)
        yaw = math.degrees(math.atan2(-n[0], -n[1]))
        gk = r * 2.0
        self.ents.append(model("FakeD_%s" % fid, "models/goal.gltf", (x, mb["sill"], z), yaw, g,
                               (gk, gk, gk)))
        bx2, bz2 = n[0], n[1]
        self.ents.append(plight("FakeGL_%s" % fid, (x - bx2 * 0.9 * gk, mb["sill"] + 1.25 * gk, z - bz2 * 0.9 * gk),
                                (0.25, 1.0, 0.62), 2.6, 1.8 * gk + 0.6, g))

    def window(self, sp):
        rid, wall, off = sp["room"], sp["wall"], sp["off"]
        wid = "win_%s_%s" % (rid, wall)
        ma = self.add_opening(rid, wall, off, "win", 0.0, wid)
        rid2, w2, off2 = self.partner_room(rid, wall, ma["pos"])
        mb = self.add_opening(rid2, w2, off2, "win", 0.0, wid + "2")
        g = group(self.ents, "Window %s" % wid, self.g_seams)
        self.frustum(g, wid, ma, mb, glass=True)

    # ---- 壁 ----
    def wall_model(self, rid, wall):
        fr = wall_frame(self.rooms[rid], wall)
        ops = self.openings.get((rid, wall), [])
        r = self.rooms[rid]
        if not ops and not SHAPES[r["shape"]].get("mf"):
            return "models/wall%s.gltf" % fr["tag"]
        al, rg = fr["along"], fr["right"]
        kk = al[0] * rg[0] + al[1] * rg[1]
        k = fr["k"]
        fy = floor_y(r, wall)
        loc = sorted([[round(o["off"] * kk / k, 3), round(o["w"] / k, 3), round((o["y0"] - fy) / k, 3),
                       round((o["y0"] - fy + o["h"]) / k, 3)] for o in ops])
        spec = dict(L=round(fr["Lu"], 3), H=round(fr["Hu"], 3), ops=loc)
        name = "wm_%s_%s" % (fr["tag"] or "12", key_of(spec))
        self.manifest[name] = spec
        return "models/%s.gltf" % name

    def build_room(self, r):
        st = self.st
        rid = r["id"]
        cx, cz = r["at"]
        hx, hz, ch, k = dims(r)
        S = SHAPES[r["shape"]]
        spanx, spanz = (S["ix"] + WALLT) * k, (S["iz"] + WALLT) * k
        ents = self.ents
        g = group(ents, "Room %s (x%.2g)" % (rid, k), self.g_rooms)
        lay = r.get("layout", {})
        pits = [(axis, c * k) for (axis, c) in lay.get("pits", ())]
        sc3 = (k, k, k)
        fy = r.get("y", 0.0)
        rise = S.get("rise", 0.0) * k

        if rise > 0:
            # ★スロープ。床と天井を傾けた箱。壁は縦の箱(高い方に合わせる)
            ln = math.hypot(spanz, rise)
            ang = -math.degrees(math.atan2(rise, spanz))
            ents.append(box("%s_Floor" % rid, (cx, fy + rise * 0.5 - 0.15, cz), (spanx, 0.3, ln), C_FLOOR,
                            rot=(ang, 0, 0), rough=0.95, parent=g))
            fs = dict(floor=True, sx=round(spanx / k, 3), sz=round(ln / k, 3))
            nm = "fm_%s" % key_of(fs); self.manifest[nm] = fs
            ents.append(model("%s_FloorM" % rid, "models/%s.gltf" % nm, (cx, fy + rise * 0.5 + 0.005, cz), 0.0, g, sc3))
            ents[-1]["transform"]["rotation"] = [ang, 0.0, 0.0]
            ents.append(box("%s_Ceil" % rid, (cx, fy + rise * 0.5 + ch + 0.15 * k, cz), (spanx, 0.3 * k, ln), C_CEIL,
                            rot=(ang, 0, 0), parent=g))
            cs = dict(ceil=True, sx=round(spanx / k, 3), sz=round(ln / k, 3))
            nm = "cm_%s" % key_of(cs); self.manifest[nm] = cs
            ents.append(model("%s_CeilM" % rid, "models/%s.gltf" % nm, (cx, fy + rise * 0.5 + ch - 0.005, cz), 0.0, g, sc3))
            ents[-1]["transform"]["rotation"] = [ang, 0.0, 0.0]
        elif not pits:
            ents.append(box("%s_Floor" % rid, (cx, fy - 0.15, cz), (spanx, 0.3, spanz), C_FLOOR, rough=0.95, parent=g))
            if S.get("mf"):
                fs = dict(floor=True, sx=round(spanx / k, 3), sz=round(spanz / k, 3))
                nm = "fm_%s" % key_of(fs); self.manifest[nm] = fs
                ents.append(model("%s_FloorM" % rid, "models/%s.gltf" % nm, (cx, fy + 0.005, cz), 0.0, g, sc3))
            else:
                ents.append(model("%s_FloorM" % rid, S["floor"], (cx, fy + 0.005, cz), 0.0, g, sc3))
        else:
            axis, c = pits[0]
            c0, c1 = c - PIT_W * 0.5, c + PIT_W * 0.5
            half = hz if axis == "z" else hx
            for i, (p0, p1) in enumerate([(-half - WALLT * k * 0.5, c0), (c1, half + WALLT * k * 0.5)]):
                L = p1 - p0
                m = (p0 + p1) * 0.5
                if axis == "z":
                    pos, sc, fspec = (cx, -0.15, cz + m), (spanx, 0.3, L), dict(sx=spanx, sz=L)
                else:
                    pos, sc, fspec = (cx + m, -0.15, cz), (L, 0.3, spanz), dict(sx=L, sz=spanz)
                ents.append(box("%s_Floor%d" % (rid, i), pos, sc, C_FLOOR, rough=0.95, parent=g))
                # 床モデルは単位寸法で作って k 倍する(目地の大きさも縮尺に従う)
                fs = dict(floor=True, sx=round(fspec["sx"] / k, 3), sz=round(fspec["sz"] / k, 3))
                nm = "fm_%s" % key_of(fs)
                self.manifest[nm] = fs
                ents.append(model("%s_FloorM%d" % (rid, i), "models/%s.gltf" % nm, (pos[0], 0.005, pos[2]), 0.0, g, sc3))
            W = PIT_W
            if axis == "z":
                for i, (zc, sgn) in enumerate(((c0, 1), (c1, -1))):
                    ents.append(box("%s_PitW%d" % (rid, i), (cx, -PIT_DEPTH * 0.5, cz + zc - sgn * 0.15),
                                    (spanx, PIT_DEPTH, 0.3), C_PIT, rough=1.0, parent=g))
                ents.append(box("%s_PitB" % rid, (cx, -PIT_DEPTH - 0.15, cz + c), (spanx, 0.3, W), C_PIT, rough=1.0, parent=g))
                for sgn in (-1, 1):
                    ents.append(box("%s_PitS%d" % (rid, sgn), (cx + sgn * (hx + WALLT * k * 0.5), -PIT_DEPTH * 0.5, cz + c),
                                    (WALLT * k, PIT_DEPTH, W), C_PIT, rough=1.0, parent=g))
                px, pz = cx, cz + c
            else:
                for i, (xc, sgn) in enumerate(((c0, 1), (c1, -1))):
                    ents.append(box("%s_PitW%d" % (rid, i), (cx + xc - sgn * 0.15, -PIT_DEPTH * 0.5, cz),
                                    (0.3, PIT_DEPTH, spanz), C_PIT, rough=1.0, parent=g))
                ents.append(box("%s_PitB" % rid, (cx + c, -PIT_DEPTH - 0.15, cz), (W, 0.3, spanz), C_PIT, rough=1.0, parent=g))
                for sgn in (-1, 1):
                    ents.append(box("%s_PitS%d" % (rid, sgn), (cx + c, -PIT_DEPTH * 0.5, cz + sgn * (hz + WALLT * k * 0.5)),
                                    (W, PIT_DEPTH, WALLT * k), C_PIT, rough=1.0, parent=g))
                px, pz = cx + c, cz
            ents.append(plight("%s_PitL" % rid, (px, -PIT_DEPTH + 0.8, pz), (1.0, 0.25, 0.15), 3.0, 9.0, g))

        if rise <= 0:
            ents.append(box("%s_Ceil" % rid, (cx, fy + ch + 0.15 * k, cz), (spanx, 0.3 * k, spanz), C_CEIL, parent=g))
            if S.get("mf"):
                cs = dict(ceil=True, sx=round(spanx / k, 3), sz=round(spanz / k, 3))
                nm = "cm_%s" % key_of(cs); self.manifest[nm] = cs
                ents.append(model("%s_CeilM" % rid, "models/%s.gltf" % nm, (cx, fy + ch - 0.005, cz), 0.0, g, sc3))
            else:
                ents.append(model("%s_CeilM" % rid, S["ceil"], (cx, fy + ch - 0.005, cz), 0.0, g, sc3))

        for w in ("N", "S", "E", "W"):
            fr = wall_frame(r, w)
            info = WALLS[w]
            L = fr["L"]
            face, n, al = fr["face"], fr["n"], fr["along"]
            zax = info["axis"] == "z"
            T = WALLT * k
            wy = floor_y(r, w)            # この壁の床の高さ(スロープは北だけ高い)
            side = (rise > 0 and not zax)
            wh = ch + (rise if side else 0.0)   # スロープの横壁は上端まで覆う
            wy0 = fy if side else wy
            wc = (face[0] + n[0] * T * 0.5, wy0 + wh * 0.5, face[1] + n[1] * T * 0.5)
            mp = (face[0] - n[0] * 0.005, wy0, face[1] - n[1] * 0.005)
            if side:
                ents.append(box("%s_Wall_%s" % (rid, w), wc, (T, wh, L), C_PAINT, rough=0.85, parent=g))
                continue
            ents.append(model("%s_WallM_%s" % (rid, w), self.wall_model(rid, w), mp, info["yaw"], g, sc3))
            ops = sorted(self.openings.get((rid, w), []), key=lambda o: o["off"])
            if not ops:
                ents.append(box("%s_Wall_%s" % (rid, w), wc, (L, ch, T) if zax else (T, ch, L), C_WALL, parent=g))
                continue
            edges = [-L * 0.5]
            for o in ops:
                edges += [o["off"] - o["w"] * 0.5, o["off"] + o["w"] * 0.5]
            edges.append(L * 0.5)
            for i in range(0, len(edges), 2):
                a, b = edges[i], edges[i + 1]
                if b - a < 0.02:
                    continue
                m = (a + b) * 0.5
                p = (wc[0] + al[0] * m, wc[1], wc[2] + al[1] * m)
                ents.append(box("%s_Wall_%s_%d" % (rid, w, i // 2), p, (b - a, ch, T) if zax else (T, ch, b - a), C_WALL, parent=g))
            for o in ops:
                # ★扉板。開いた状態で蝶番の側に立てる。「ここは扉だ」を一目で言う
                if o["kind"] == "door":
                    # ★70 度開いた状態。板は蝶番から「壁沿い x cos70 + 部屋の内側 x sin70」へ伸びる。
                    #   モデルの局所 +X は right(yaw) = (cos yaw, -sin yaw) なので、そこから yaw を逆算する。
                    #   (v7 初回は info["yaw"]+108 で置いて【板が廊下の中に倒れていた】)
                    ang = math.radians(105.0)
                    inx, inz = -n[0], -n[1]
                    dx = al[0] * math.cos(ang) + inx * math.sin(ang)
                    dz = al[1] * math.cos(ang) + inz * math.sin(ang)
                    lyaw = math.degrees(math.atan2(-dz, dx))
                    lp = (wc[0] + al[0] * (o["off"] - o["w"] * 0.5) + inx * T * 0.55,
                          o["y0"],
                          wc[2] + al[1] * (o["off"] - o["w"] * 0.5) + inz * T * 0.55)
                    dk = o["w"] / DOOR_W
                    ents.append(model("%s_Leaf_%s" % (rid, o["id"]), "models/doorleaf.gltf", lp,
                                      lyaw, g, (dk, dk, dk)))
                y1 = o["y0"] + o["h"]
                lh = wy + ch - y1
                if lh > 0.01:
                    p = (wc[0] + al[0] * o["off"], y1 + lh * 0.5, wc[2] + al[1] * o["off"])
                    ents.append(box("%s_Lintel_%s_%s" % (rid, w, o["id"]), p, (o["w"], lh, T) if zax else (T, lh, o["w"]), C_WALL, parent=g))
                if o["y0"] - wy > 0.01:
                    sh = o["y0"] - wy
                    p = (wc[0] + al[0] * o["off"], wy + sh * 0.5, wc[2] + al[1] * o["off"])
                    ents.append(box("%s_Sill_%s_%s" % (rid, w, o["id"]), p, (o["w"], sh, T) if zax else (T, sh, o["w"]), C_WALL, parent=g))

        lightcol, intensity = st.get("lightcol", (0.98, 0.96, 0.88)), st.get("intensity", 9.0)
        for i, (ox, oz) in enumerate(S["lights"]):
            ly = fy + (rise * (0.5 + oz * k / spanz) if rise > 0 else 0.0)
            ents.append(model("%s_Troffer_%d" % (rid, i + 1), "models/troffer.gltf", (cx + ox * k, ly + ch - 0.01 * k, cz + oz * k), 0.0, g, sc3))
            # ★エンジンの減衰は逆二乗ではなく range で窓掛けされる(実測: k^2 だと白飛び)。
            #   range を k 倍にすると同じ見え方になる。強さはそのまま
            ents.append(plight("%s_Light_%d" % (rid, i + 1), (cx + ox * k, ly + ch - 0.45 * k, cz + oz * k),
                               lightcol, intensity * min(1.0, k) ** 0.8, S["lrange"] * k, g))

        # 隙間(絶対 1.0m)。壁は天井まで
        for (axis, c) in lay.get("eaves", ()):
            cw = c * k
            along_x = (axis == "z")
            span = spanx if along_x else spanz
            nseg = int(math.ceil(span / 4.4))
            for i in range(nseg):
                u = (i - (nseg - 1) * 0.5) * 4.4
                lx, lz = (u, cw) if along_x else (cw, u)
                ents.append(model("%s_Eave_%d" % (rid, i), "models/eave.gltf", (cx + lx, fy, cz + lz), 0.0 if along_x else 90.0, g))
            sx, sz = (span, 0.26) if along_x else (0.26, span)
            top = ch - EAVE_GAP
            lx, lz = (0.0, cw) if along_x else (cw, 0.0)
            ents.append(box("%s_EaveW" % rid, (cx + lx, fy + EAVE_GAP + top * 0.5, cz + lz), (sx, top, sz), C_PAINT, rough=0.6, parent=g))
            self.fixtures.setdefault(rid, []).append((cx + lx, cz + lz, 2.2, ch))

        for i, (kind, lx, lz, yaw) in enumerate(lay.get("props", ())):
            P = PROPS[kind]
            y = P["y"]
            if y is None:
                y = min(2.6, S["h"] * k - 0.6) if kind == "vent" else ch - 0.01
            # ★★什器は【部屋の縮尺を掛けない】。これが v7 の心臓。
            #   ベンチ 0.95m / ロッカー 1.95m は世界のどこでも同じ大きさなので、
            #   縮尺 2 の部屋では脛の高さに、0.5 の部屋では見上げる壁になる。
            #   v6 は什器も k 倍していたので【絵が完全に同じ】になり、錯覚が起きようがなかった。
            sc = (1.0, ch / 4.0, 1.0) if kind == "column" else (1.0, 1.0, 1.0)
            ents.append(model("%s_%s_%d" % (rid, kind, i), P["path"], (cx + lx * k, fy + y, cz + lz * k), yaw, g, sc))
            if P["block"]:
                top = P["top"] if P["top"] < 90.0 else ch
                self.fixtures.setdefault(rid, []).append((cx + lx * k, cz + lz * k, P["r"], top))

        # 柵(絶対 1.7m。長さだけ部屋に合わせる)
        for i, (axis, c) in enumerate(lay.get("bars", ())):
            cw = c * k
            along_x = (axis == "z")
            span = spanx if along_x else spanz
            lx, lz = (0.0, cw) if along_x else (cw, 0.0)
            ents.append(model("%s_Bar_%d" % (rid, i), "models/barrier.gltf", (cx + lx, fy, cz + lz), 0.0 if along_x else 90.0, g,
                              (span / 12.6, BAR_H / 1.35, 1.0)))
            sx = span if along_x else 0.14
            sz = 0.14 if along_x else span
            ents.append(box("%s_BarCol_%d" % (rid, i), (cx + lx, fy + BAR_H * 0.5 - 0.03, cz + lz), (sx - 0.03, BAR_H - 0.06, sz - 0.03), C_DIV, rough=0.6, parent=g))
            self.fixtures.setdefault(rid, []).append((cx + lx, cz + lz, 0.6, BAR_H))

    def build(self):
        st = self.st
        ents = self.ents
        g_sys = group(ents, "[System]")
        self.g_rooms = group(ents, "[Rooms]")
        self.g_seams = group(ents, "[Seams]")
        ents.append({"guid": guid(), "name": "Ambient", "parentGuid": g_sys,
                     # ★環境光 0.035 -> 0.16(v8)。点光源は castShadows=false で、天井の灯りしか無い。
                     #   そのため【灯りと平行な面】は N.L=0 で真っ黒になる。全開にした扉板の裏面が
                     #   部屋にぽっかり空いた黒い穴に見えた(実測)。底上げで面の存在が読めるようにする。
                     "directionalLight": {"ambient": 0.16, "color": [0.85, 0.88, 1.0],
                                          "direction": [-0.3, -0.9, -0.3], "intensity": 0.0},
                     "transform": {"position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0],
                                   "scale": [1.0, 1.0, 1.0]}})
        for sp in st.get("seams", ()):
            self.seam(sp)
        for sp in st.get("fakes", ()):
            self.fake(sp)
        for sp in st.get("windows", ()):
            self.window(sp)
        for r in st["rooms"]:
            self.build_room(r)
        # ---- 黙って転送する面(warp)。同じ見た目の廊下の中に置くので見えない ----
        self.warps = []
        for wp in st.get("warps", ()):
            ta = [t for t in self.tunnels if t["id"] == wp["fromTunnel"]][0]
            tb = [t for t in self.tunnels if t["id"] == wp["toTunnel"]][0]
            mid = lambda t: (t["ax"] + t["nx"] * GAP * 0.5, t["az"] + t["nz"] * GAP * 0.5)
            ma, mb = mid(ta), mid(tb)
            self.warps.append(dict(id=wp["id"], px=ma[0], pz=ma[1], nx=ta["nx"], nz=ta["nz"],
                                   dx=mb[0] - ma[0], dy=tb["y0"] - ta["y0"], dz=mb[1] - ma[1],
                                   loops=wp.get("loops", 3), hw=max(ta["wa"], ta["wb"]) * 0.5 + 0.3))
        # ---- 背後改変(morph)。★見ていない間に部屋そのものを書き換える ----
        #   P.T. の廊下と同じ。振り向いたら、来た扉が無い / 家具が違う / 光の色が違う。
        #   「今いる場所が確かだ」という感覚を壊すのが目的で、これはプレイヤーに【見える】。
        self.morphs = []
        for mo in st.get("morphs", ()):
            rid = mo["room"]
            r = self.rooms[rid]
            k = r["scale"]
            cx, cz = r["at"]
            fy = r.get("y", 0.0)
            gm = group(ents, "Morph %s" % mo["id"], self.g_seams)
            rows = []
            for tag, lst, hidden in (("A", mo.get("org", ()), False), ("B", mo.get("alt", ()), True)):
                for i, (kind, lx, lz, yaw) in enumerate(lst):
                    P = PROPS[kind]
                    y = P["y"]
                    if y is None:
                        y = SHAPES[r["shape"]]["h"] * k - 0.01
                    nm = "Morph%s_%s_%d" % (tag, mo["id"], i)
                    px, pz = cx + lx * k, cz + lz * k
                    ents.append(model(nm, P["path"], (px, HIDE_Y if hidden else fy + y, pz), yaw, gm))
                    rows.append((nm, px, fy + y, pz, tag))
            self.morphs.append(dict(id=mo["id"], room=rid, wx=cx, wz=cz,
                                    x=cx + mo.get("at", (0, 0))[0] * k,
                                    z=cz + mo.get("at", (0, 0))[1] * k, r=mo.get("r", 8.0),
                                    delay=mo.get("delay", 1.2), rows=rows,
                                    light0=tuple(st.get("lightcol", (0.98, 0.96, 0.88))),
                                    seal=list(mo.get("seal", ())), unseal=list(mo.get("unseal", ())),
                                    light=mo.get("light")))
            for mid in list(mo.get("seal", ())) + list(mo.get("unseal", ())):
                st.setdefault("_autoplugs", []).append(
                    dict(mouth=mid, mode="seal" if mid in mo.get("seal", ()) else "appear", auto=True))

        # ---- 栓(plug)。口を壁で塞ぐ箱。見ていない間に消える(appear)/現れる(seal) ----
        self.plugs = []
        for pg in list(st.get("plugs", ())) + list(st.get("_autoplugs", ())):
            m = self.mouths[pg["mouth"]]
            n = m["n"]
            zax = abs(n[1]) > 0.5
            x, z = m["pos"][0] + n[0] * 0.5, m["pos"][1] + n[1] * 0.5
            y = m["sill"] + m["h"] * 0.5
            hidden = (pg["mode"] == "seal")
            ents.append(box("Plug_%s" % pg["mouth"], (x, HIDE_Y if hidden else y, z),
                            (m["w"] + 0.1, m["h"] + 0.1, 0.7) if zax else (0.7, m["h"] + 0.1, m["w"] + 0.1),
                            C_WALL, rough=0.9, parent=self.g_seams, kinematic=True))
            self.plugs.append(dict(id=pg["mouth"], x=x, y=y, z=z, mode=pg["mode"], delay=pg.get("delay", 2.0),
                                   auto=pg.get("auto", False)))

        # 出口(絶対寸法)。縮尺 2 の部屋では小さく、0.5 では巨大に見える = 唯一の物差し
        gx, gz = st["goal"]
        gyaw = st.get("goalYaw", 0.0)
        gy = floor_y(self.rooms[st["goalRoom"]])     # ★出口も部屋の標高に置く(9m 上の部屋なら 9m)
        ents.append(model("GoalM", "models/goal.gltf", (gx, gy, gz), gyaw, g_sys))
        bx, bz = -math.sin(math.radians(gyaw)), -math.cos(math.radians(gyaw))
        # ★v8: 緑の板はモデル本体が持つ(goal.gltf の敷居)。ここは【当たり判定の印】だけ。
        #   旧版は緑の箱を門の前に重ねていたので、扉板と z ファイトしてチラついていた。
        ents.append(box("Goal", (gx, gy + 0.2, gz), (0.2, 0.2, 0.2), C_GOAL,
                        collide=False, parent=g_sys, visible=False))
        # 緑の光は両面に。門から漏れる光が床を照らすので、部屋のどこからでも「出口だ」と分かる
        for sgn, nm in ((-1.0, "F"), (1.0, "B")):
            # ★強すぎると敷居と標識がブルームで白飛びして【緑に見えなくなる】(v8 実測)。
            #   床へ緑を落とすのが仕事なので、低く・門から離して置く。
            ents.append(plight("GoalLight" + nm, (gx + bx * 1.5 * sgn, gy + 0.55, gz + bz * 1.5 * sgn),
                               (0.25, 1.0, 0.62), 5.0, 9.0, g_sys))
        gp = base("GoalFx", (gx, gy + 0.15, gz), parent=g_sys)
        gp["particleEmitter"] = {"kind": 0, "blend": 0, "rate": 14, "orient": 0,
                                 "playOnStart": True, "looping": True, "duration": 1.0,
                                 "dir": [0.0, 1.0, 0.0], "spread": 0.12, "speed": 0.9,
                                 "speedVar": 0.3, "size": 0.16, "sizeEnd": 0.0,
                                 "life": 2.6, "lifeVar": 0.5,
                                 "color": [0.35, 1.0, 0.7], "colorEnd": [0.1, 0.6, 0.4],
                                 "intensity": 2.4, "gravity": 0.0, "drag": 0.6}
        ents.append(gp)
        ents.append(box("Pilot", (0.0, HIDE_Y, 0.0), (0.22, 0.22, 0.22), (0.55, 1.0, 0.85),
                        collide=False, rough=0.2, parent=g_sys, prim="sphere"))
        ents.append(plight("PilotLight", (0.0, HIDE_Y, 0.0), (0.35, 1.0, 0.80), 2.6, 5.0, g_sys))

        sp = st["spawn"]
        for i, s in enumerate(SCALES):
            cc = body_cc(s)
            e = base("Body_%d" % i, (sp[0], HIDE_Y, sp[1]), (0.0, sp[2], 0.0))
            e["characterController"] = {
                "gravityScale": 1.0, "halfHeight": cc["halfHeight"],
                "jumpSpeed": math.sqrt(2 * GRAV * jump_h(s)),
                "mass": 70.0 * s, "maxSlopeDeg": 50.0, "offset": [0.0, 0.0, 0.0],
                "radius": cc["radius"], "stepHeight": cc["stepHeight"]}
            ents.append(e)
        ents.append({
            "guid": guid(), "name": "MainCamera",
            "camera": {"farClip": 300.0, "fovDegrees": 74.0, "isActive": True,
                       "nearClip": 0.02, "orthoSize": 10.0, "projection": 0},
            "luaScript": {"enabled": True, "scriptPath": "components/FreeLook.lua"},
            "transform": {"position": [sp[0], EYE_H, sp[1]], "rotation": [0.0, sp[2], 0.0],
                          "scale": [1.0, 1.0, 1.0]},
        })
        logic = marker("Logic_" + st["tag"], (0.0, 0.0, 0.0), 0.0, g_sys)
        logic["luaScript"] = {"enabled": True, "scriptPath": "components/Junction.lua"}
        ents.append(logic)
        return {
            "version": 1, "entities": ents, "shadows": True,
            "skybox": {"drawSkybox": False, "envMapPath": "", "iblIntensity": 0.0, "skyboxIntensity": 0.0},
            "ssao": {"bias": 0.025, "blur": True, "enabled": True, "intensity": 1.0,
                     "power": 1.7, "radius": 0.7, "sampleCount": 16},
            "postProcess": {
                "enabled": True, "tonemapper": 1, "exposureOn": True, "exposure": 1.0,
                "bloomOn": True, "bloom": 0.42, "bloomThreshold": 1.15,
                "bloomKnee": 0.5, "bloomRadius": 0.72,
                "vignetteOn": True, "vignette": 0.26, "caOn": True, "ca": 0.15,
                "grainOn": True, "grain": 0.045, "fxaaOn": True, "debandOn": True,
            },
        }


PROPS = {
    "bench":   dict(path="models/bench.gltf",   y=0.0, r=0.90, top=0.95, block=True),
    "column":  dict(path="models/column.gltf",  y=0.0, r=0.45, top=99.0, block=True),
    "locker":  dict(path="models/locker.gltf",  y=0.0, r=0.85, top=1.95, block=True),
    "crate":   dict(path="models/crate.gltf",   y=0.0, r=0.55, top=0.75, block=True),
    "railing": dict(path="models/railing.gltf", y=0.0, r=1.55, top=1.10, block=True),
    "vent":    dict(path="models/vent.gltf",    y=None, r=0.4, top=0.0, block=False),
    "pipes":   dict(path="models/pipes.gltf",   y=None, r=3.0, top=0.0, block=False),
}


# ---------------------------------------------------------------- 総当たり(状態 = 部屋, 区画。大きさは部屋が決める)
def _dividers(r):
    k = r["scale"]
    lay = r.get("layout", {})
    out = []
    for (axis, c) in lay.get("bars", ()):
        out.append((axis, c * k, ("big", 0)))
    for (axis, c) in lay.get("eaves", ()):
        out.append((axis, c * k, ("small", 0)))
    for (axis, c) in lay.get("pits", ()):
        out.append((axis, c * k, ("pit", PIT_W)))
    return out


def _zone_of(r, lx, lz):
    zx = zz = 0
    for (axis, c, _g) in sorted(_dividers(r), key=lambda d: (d[0], d[1])):
        if axis == "x" and lx > c:
            zx += 1
        if axis == "z" and lz > c:
            zz += 1
    return (zx, zz)


def _zone_edges(r):
    ds = sorted(_dividers(r), key=lambda d: (d[0], d[1]))
    xs = [d for d in ds if d[0] == "x"]
    zs = [d for d in ds if d[0] == "z"]
    e = {}
    for i, d in enumerate(xs):
        for zz in range(len(zs) + 1):
            e[((i, zz), (i + 1, zz))] = d
            e[((i + 1, zz), (i, zz))] = d
    for i, d in enumerate(zs):
        for zx in range(len(xs) + 1):
            e[((zx, i), (zx, i + 1))] = d
            e[((zx, i + 1), (zx, i))] = d
    return e


def _pass_gate(gate, s):
    kind, arg = gate
    if kind == "big":
        return climb_h(s) >= BAR_H - 1e-6
    if kind == "small":
        return BODY_H * s < EAVE_GAP - 1e-6
    if kind == "pit":
        return jump_dist(s) >= arg + 1e-6
    return False


def simulate(st, W, want_seen=False, start_state=None):
    rooms = W.rooms
    mouths = {}
    for mid, m in W.mouths.items():
        if m["kind"] != "door" or mid not in W.links:
            continue
        r = rooms[m["room"]]
        lx = m["pos"][0] - r["at"][0] - m["n"][0] * 0.5
        lz = m["pos"][1] - r["at"][1] - m["n"][1] * 0.5
        mouths[mid] = dict(room=m["room"], zone=_zone_of(r, lx, lz), sill=m["sillRel"],
                           pos=(m["pos"][0] - m["n"][0] * 1.2, m["pos"][1] - m["n"][1] * 1.2))
    gr = rooms[st["goalRoom"]]
    gx, gz = st["goal"]
    goal_zone = _zone_of(gr, gx - gr["at"][0], gz - gr["at"][1])
    sr = rooms[st["start"]]
    start = start_state or (st["start"], _zone_of(sr, st["spawn"][0], st["spawn"][1]))
    edges = {rid: _zone_edges(rooms[rid]) for rid in rooms}
    seen = {start: 0}
    prev = {start: None}
    frontier = [start]
    best, bestState = None, None
    while frontier:
        nxt = []
        for stt in frontier:
            room, zone = stt
            sc = rooms[room]["scale"]
            hops = seen[stt]
            if room == st["goalRoom"] and zone == goal_zone:
                if best is None or hops < best:
                    best, bestState = hops, stt
                continue
            r = rooms[room]
            for (za, zb), div in edges[room].items():
                if za == zone and _pass_gate(div[2], sc):
                    n = (room, zb)
                    if n not in seen:
                        axis, c, gate = div
                        wp = (r["at"][0], r["at"][1] + c) if axis == "z" else (r["at"][0] + c, r["at"][1])
                        seen[n] = hops
                        prev[n] = (stt, {"big": "跨ぐ", "small": "くぐる", "pit": "跳び越える"}[gate[0]], wp)
                        nxt.append(n)
            for mid, m in mouths.items():
                if m["room"] != room or m["zone"] != zone:
                    continue
                if climb_h(sc) < m["sill"] - 1e-6:
                    continue
                to = W.links[mid]
                mt = mouths[to]
                n = (mt["room"], mt["zone"])
                if n not in seen:
                    seen[n] = hops + 1
                    prev[n] = (stt, "%s→%s(x%.2g)" % (mid, to, rooms[mt["room"]]["scale"]), m["pos"])
                    nxt.append(n)
        frontier = nxt
    path, pts = [], []
    cur = bestState
    while cur is not None and prev.get(cur):
        cur, how, wp = prev[cur]
        path.append(how)
        pts.append(wp)
    path.reverse()
    pts.reverse()
    pts.append((gx, gz))
    if want_seen:
        return best, len(seen), path, pts, seen
    return best, len(seen), path, pts


def check_solvable(st, W):
    hops, states, path, pts = simulate(st, W)
    if hops is None:
        raise SystemExit("%s: ★出口に到達できない(全 %d 状態)" % (st["name"], states))
    if hops == 0:
        raise SystemExit("%s: ★口を 1 つもくぐらずに出口へ着けてしまう" % st["name"])
    if hops < st.get("minHops", 1):
        raise SystemExit("%s: 想定(%d)より短い(%d 回) : %s" % (st["name"], st.get("minHops", 1), hops, " / ".join(path)))
    print("  %-8s 最短 %d 回 : %s" % (st["name"], hops, " / ".join(path)))
    return pts


def check_no_deadend(st, W):
    _h, _s, _p, _pts, seen = simulate(st, W, want_seen=True)
    for s0 in list(seen):
        if simulate(st, W, start_state=s0)[0] is None:
            raise SystemExit("%s: ★詰み状態がある: 部屋 %s 区画 %s から出口へ戻れない" % (st["name"], s0[0], s0[1]))


def check_fakes(st, W):
    """★偽の廊下の口が【到達できる区画】に付いているかを見る(v8 で追加)。
    check_runup は什器しか見ないので、柵や隙間の【向こう側の壁】に偽の口を付けても
    素通りしてしまう。実際 v8 の第2/3/7/8 面で「行けない所に餌をぶら下げる」設計事故を
    起こした。餌は必ず、プレイヤーが最初に立っている区画から歩いて触れる所に置くこと。"""
    _h, _s, _p, _pts, seen = simulate(st, W, want_seen=True)
    for sp in st.get("fakes", ()):
        m = W.mouths[sp["id"]]
        r = W.rooms[m["room"]]
        lx = m["pos"][0] - r["at"][0] - m["n"][0] * 0.5
        lz = m["pos"][1] - r["at"][1] - m["n"][1] * 0.5
        z = _zone_of(r, lx, lz)
        if (m["room"], z) not in seen:
            raise SystemExit("%s: ★偽の廊下 %s が到達できない区画にある(部屋 %s 区画 %s)"
                             % (st["name"], sp["id"], m["room"], z))


def check_runup(st, W):
    for mid, m in W.mouths.items():
        if m["kind"] != "door":
            continue
        n = m["n"]
        ix, iz = -n[0], -n[1]
        for (fx, fz, fr, ftop) in W.fixtures.get(m["room"], ()):
            if fr >= 2.0:
                continue
            fwd = (fx - m["pos"][0]) * ix + (fz - m["pos"][1]) * iz
            lat = abs(-(fx - m["pos"][0]) * iz + (fz - m["pos"][1]) * ix)
            if -0.5 < fwd <= 2.5 * m["size"] and lat < m["w"] * 0.5 + fr:
                raise SystemExit("%s: 口 %s の手前に什器 前方=%.2f 横=%.2f" % (st["name"], mid, fwd, lat))


def check_footholds(st, W):
    for r in st["rooms"]:
        k = r["scale"]
        lay = r.get("layout", {})
        divs = [(axis, c * k) for (axis, c) in lay.get("bars", ())]
        if not divs:
            continue
        for (kind, lx, lz, yaw) in lay.get("props", ()):
            P = PROPS[kind]
            if not P["block"] or P["top"] >= 90.0:
                continue
            if P["top"] < 0.35:
                continue
            # ★踏み台になるのは「天端 + その部屋での登れる高さ」が柵に届く時だけ。
            #   縮尺 0.5 の部屋ではベンチ(0.95)に乗っても 1.525m で 1.7m の柵に届かない。
            #   縮尺を見ずに弾いていたので、小さい部屋に什器を置けなくなっていた(v8)
            if P["top"] + climb_h(k) < BAR_H:
                continue
            for (axis, c) in divs:
                d = abs((lx * k if axis == "x" else lz * k) - c)
                if d < 3.0 + P["r"]:
                    raise SystemExit("%s: 部屋 %s の %s が柵から %.1fm。跳び乗って越えられる" % (st["name"], r["id"], kind, d))


CAM_MARGIN, CAM_YMIN, CAM_YTOP = 1.2, 0.8, 0.5
CAM_CLEAR, CAM_TAIL, CAM_HEAD = 0.9, 2.0, 0.3


def check_cine(st, W):
    centers = {r["id"]: r["at"] for r in st["rooms"]}
    for i, (er, e, tr, t, dur) in enumerate(st.get("cine", ())):
        tag = "%s cine[%d]" % (st["name"], i)
        r0 = W.rooms[er]
        hx, hz, ch, k = dims(r0)
        if abs(e[0]) > hx - CAM_MARGIN or abs(e[2]) > hz - CAM_MARGIN:
            raise SystemExit("%s: 目が壁に近すぎる local=(%.1f,%.1f)" % (tag, e[0], e[2]))
        if e[1] < CAM_YMIN or e[1] > ch - CAM_YTOP:
            raise SystemExit("%s: 目の高さ %.2f が範囲外(天井 %.1f)" % (tag, e[1], ch))
        ex, ey, ez = centers[er][0] + e[0], e[1], centers[er][1] + e[2]
        tx, ty, tz = centers[tr][0] + t[0], t[1], centers[tr][1] + t[2]
        vx, vz = tx - ex, tz - ez
        seg = math.hypot(vx, vz)
        if seg < 0.5:
            raise SystemExit("%s: 目と注視点が近すぎる" % tag)
        for rid in (er, tr):
            rr = W.rooms[rid]
            for (axis, c, gate) in _dividers(rr):
                if gate[0] != "small":
                    continue
                a0, a1 = (ez - rr["at"][1], tz - rr["at"][1]) if axis == "z" else (ex - rr["at"][0], tx - rr["at"][0])
                if (a0 - c) * (a1 - c) < 0:
                    raise SystemExit("%s: 隙間の壁を横切る room=%s" % (tag, rid))
        t0 = min(0.9, CAM_HEAD / seg)
        t1 = max(t0, 1.0 - CAM_TAIL / seg)
        for rid in (er, tr):
            for (fx, fz, fr, ftop) in W.fixtures.get(rid, ()):
                if fr >= 2.0:
                    continue
                kk = ((fx - ex) * vx + (fz - ez) * vz) / (seg * seg)
                kk = max(t0, min(t1, kk))
                d = math.hypot(ex + vx * kk - fx, ez + vz * kk - fz)
                if d < CAM_CLEAR + fr and (ey + (ty - ey) * kk) < ftop + 0.25:
                    raise SystemExit("%s: 什器に刺さる room=%s (%.1f,%.1f) 距離=%.2f" % (tag, rid, fx, fz, d))
    return centers


def cine_world(st, centers):
    out, prev = [], None
    for (er, e, tr, t, dur) in st.get("cine", ()):
        ex, ey, ez = centers[er][0] + e[0], e[1], centers[er][1] + e[2]
        tx, ty, tz = centers[tr][0] + t[0], t[1], centers[tr][1] + t[2]
        if prev is not None and er != prev:
            out.append((ex, ey, ez, tx, ty, tz, 0.02))
        out.append((ex, ey, ez, tx, ty, tz, dur))
        prev = er
    sx, sz, syaw = st["spawn"]
    fx, fz = math.sin(math.radians(syaw)), math.cos(math.radians(syaw))
    out.append((sx, EYE_H, sz, sx + fx * 8.0, EYE_H, sz + fz * 8.0, 1.4))
    return out


# ================================ ステージ定義 ================================
def R(rid, shape, at, scale=1.0, layout=None):
    return dict(id=rid, shape=shape, at=at, scale=scale, layout=layout or {})


def SEAM(sid, room, wall, off, sill=0.0):
    return dict(id=sid, room=room, wall=wall, off=off, sill=sill)


def FAKE(fid, room, wall, off, depth=2.5, look=20.0):
    return dict(id=fid, room=room, wall=wall, off=off, depth=depth, look=look)


def MORPH(mid, room, at=(0.0, 0.0), r=8.0, delay=1.2, org=(), alt=(), seal=(), unseal=(), light=None):
    return dict(id=mid, room=room, at=at, r=r, delay=delay, org=org, alt=alt,
                seal=seal, unseal=unseal, light=light)


def WIN(room, wall, off):
    return dict(room=room, wall=wall, off=off)


# ================================ 間取り(v8) ================================
# ★v8 の骨格: 【同じ間取りを縮尺違いで並べ、什器は絶対寸法のまま置く】。
#   ベンチ 0.95m / ロッカー 1.95m / 木箱 0.75m は世界のどこでも同じ大きさなので、
#   縮尺 2 の部屋では脛・腰・靴に、縮尺 0.5 の部屋では見上げる壁になる。
#   部屋の絵が同じで什器だけ違う = 「同じ部屋なのに見え方が違う」がそのまま錯覚になる。
#   だから【全部の面で同じ什器配置 SET を使う】。これが唯一の物差し。
SET = [("bench", 1.6, -1.0, 90.0), ("locker", 5.4, 2.6, 270.0), ("crate", 3.4, -4.6, 20.0)]
SET_B = [("bench", -1.6, 1.0, 270.0), ("locker", -5.4, -2.6, 90.0), ("crate", -3.4, 4.6, 200.0)]


def LAY(bars=(), eaves=(), pits=(), props=None):
    return dict(bars=list(bars), eaves=list(eaves), pits=list(pits),
                props=list(props if props is not None else SET))


# 4 つの関門。通れる縮尺は物理から一意に決まる(docs/V8.md)
#   柵 1.70m   … 跨げるのは k=2 だけ        (climb_h = 1.15k)
#   隙間 1.00m … くぐれるのは k=0.5 だけ     (体高 = 1.8k)
#   溝 4.60m   … 跳べるのは k=2 だけ        (jump_dist)
#   高い敷居 0.9m … k=0.5 の部屋からは出られない = 一方通行
L_BAR = LAY(bars=[("x", -2.5)])
L_EAVE = LAY(eaves=[("x", 2.5)])
# ★奥行き方向に割る版。縮尺 0.5 の部屋(内寸 6m)で出口を横に置くと、くぐった直後の
#   1.5m 先に高さ 2.9m の門が立ち【近すぎて門に見えない】(v8 実測)。部屋の奥行きを
#   まるごと使い、入口から一直線に門が見える構図にするためのもの。
L_EAVE_N = LAY(eaves=[("z", -2.0)])
L_BOTH = LAY(bars=[("x", -3.5)], eaves=[("x", 2.5)])
L_PLAIN = LAY()
L_BAR_B = LAY(bars=[("x", 2.5)], props=SET_B)
L_HALL = dict(pits=[("z", 2.0)], props=[("column", -7.0, -7.0, 0.0), ("column", 7.0, -7.0, 0.0),
                                        ("bench", 1.6, -6.0, 90.0), ("locker", 8.4, 4.6, 270.0)])

# 背後改変で入れ替える什器。★「同じ物が別の場所に居る」ことが効く
ALT_A = [("locker", -5.2, 3.0, 90.0), ("crate", 4.6, 1.0, 40.0)]
ALT_B = [("bench", -3.0, 3.4, 0.0), ("crate", -4.2, -2.0, 60.0)]

STAGES = [
    # ===================== 1「扉」 錯覚の道具を一通り見せる =====================
    #   S(x1) 見慣れた部屋。ベンチは腰、ロッカーは自分より高い。柵 1.7m は絶対に越えられない。
    #   北の開口の奥に【20m の廊下と突き当りの緑の扉】。行くしかない → 2 歩で壁だった(強制遠近法)。
    #   振り返ると部屋が違う。光が橙に変わり、壁だった東に扉が開いている(変化盲)。
    #   東 → B(x0.5) 同じ間取りなのにベンチが目の高さ。奥で振り返ると来た扉が無い。
    #   北 → C(x2) 同じ間取りなのに、越えられなかった柵が膝の高さで転がっている。跨いで出口。
    dict(name="stage1", tag="Stage_1", title=1,
         rooms=[R("S", "box12", (0.0, 0.0), 1.0, L_BAR),
                R("B", "box12", (13.0, 0.0), 0.5, L_PLAIN),
                R("C", "box12", (13.0, 19.0), 2.0, LAY(bars=[("x", -1.0)]))],
         seams=[SEAM("t1", "S", "E", -2.0), SEAM("t2", "B", "N", 4.0)],
         fakes=[FAKE("f1", "S", "N", 0.0, depth=2.5, look=20.0)],
         morphs=[MORPH("m1", "S", at=(0.0, 7.6), r=2.6, delay=0.5,
                       org=[("locker", 5.4, 2.6, 270.0)], alt=ALT_A,
                       unseal=["t1a"], light=(1.00, 0.62, 0.30)),
                 MORPH("m2", "B", at=(2.6, 2.2), r=3.0, delay=0.8,
                       org=[("crate", 3.4, -4.6, 20.0)], alt=[("bench", -3.0, 3.4, 0.0)],
                       seal=["t1b"], light=(0.62, 0.80, 1.00))],
         spawn=(2.0, -4.6, 0.0), goal=(5.0, 19.0), goalYaw=90.0,
         start="S", goalRoom="C", minHops=2, teach="walk",
         cine=[("S", (4.0, 2.2, -4.5), "S", (0.0, 1.6, 5.8), 2.4),
               ("S", (2.0, 1.7, -4.6), "S", (2.0, 1.6, 5.0), 1.4)]),

    # ===================== 2「窓」 見比べる道具を渡す =====================
    # ★狙い: 【窓は物差しだと教える】面。二択で、正解は窓の中の家具の大きさだけが教える。
    #   A(x1) の北と東に扉。それぞれの隣に窓があり、向こうの部屋が見えている。
    #   どちらも A と【まったく同じ間取り・同じ家具配置】。違うのは縮尺だけ。
    #   北の窓: ベンチが脛、ロッカーが腰 = 大きい体になる部屋 → 柵を跨げる。
    #   東の窓: ベンチが目の高さ、ロッカーが壁 = 小さい体になる部屋 → 柵は越えられない。
    #   西には廊下が見えるが、これは偽物(2 歩で壁)。「見えている物を疑え」の予告編。
    dict(name="stage2", tag="Stage_2", title=2,
         rooms=[R("A", "box12", (0.0, 0.0), 1.0, L_BAR),
                R("P", "box12", (0.0, 22.0), 2.0, L_BAR),
                R("Q", "box12", (13.0, 0.0), 0.5, L_BAR)],
         seams=[SEAM("s1", "A", "N", 4.0), SEAM("s2", "A", "E", -2.0)],
         windows=[WIN("A", "N", -3.5), WIN("A", "E", 1.5)],
         fakes=[FAKE("f1", "A", "S", 0.0, depth=2.2, look=18.0)],
         spawn=(3.0, -4.0, 0.0), goal=(-9.0, 22.0), goalYaw=90.0,
         start="A", goalRoom="P", minHops=1, teach="jump",
         cine=[("P", (7.0, 5.0, -9.0), "P", (-9.0, 1.2, 0.0), 2.4),
               ("A", (3.0, 1.7, -4.0), "A", (2.0, 1.6, 6.0), 1.6)]),

    # ===================== 3「敷居」 入ったら戻れない =====================
    # ★狙い: 【小さくなると損をする】を体で分かる形にする。
    #   膝の高さの敷居(絶対 0.9m)を跨いで小さい部屋へ入る。入った先では自分が 0.9m なので、
    #   同じ敷居が【胸の高さ】になり、二度と登れない。振り返ると来た扉が頭の上にある。
    #   代わりに、A では絶対に通れなかった 1.0m の隙間が、ここでは立ったままくぐれる。
    #   背を向けている間に来た扉は塞がれ、部屋には出口しか残らない(P.T.)。
    dict(name="stage3", tag="Stage_3", title=3,
         rooms=[R("A", "box12", (0.0, 0.0), 1.0, L_EAVE_N),
                R("B", "box12", (0.0, 13.0), 0.5, L_EAVE_N)],
         seams=[SEAM("s1", "A", "N", 0.0, sill=SILL_HI)],
         fakes=[FAKE("f1", "A", "W", 0.0, depth=2.4, look=19.0)],
         morphs=[MORPH("m1", "A", at=(-7.9, 0.0), r=2.8, delay=0.6,
                       org=[("crate", 3.4, -4.6, 20.0)], alt=ALT_B,
                       light=(0.72, 0.78, 0.98)),
                 MORPH("m2", "B", at=(0.0, 3.0), r=2.4, delay=0.9,
                       org=[("bench", 1.6, -1.0, 90.0)], alt=[("crate", -1.0, -3.0, 15.0)],
                       seal=["s1b"], light=(1.00, 0.66, 0.34))],
         spawn=(0.0, 1.0, 0.0), goal=(-1.4, 15.0), goalYaw=180.0,
         start="A", goalRoom="B", minHops=1, teach=None,
         cine=[("A", (0.0, 2.4, -1.0), "A", (0.0, 1.4, 6.0), 2.4),
               ("A", (0.0, 1.7, 0.6), "A", (0.0, 1.5, 6.0), 1.6)]),

    # ===================== 4「三つの廊下」 見えている物を疑う =====================
    # ★狙い: 強制遠近法を【自分で確かめさせる】面。東・西の開口の奥には、どう見ても
    #   20m の廊下と突き当りの緑の扉がある。行くと 2 歩で壁。振り返るたびに部屋が変わる。
    #   北の扉は最初【塞がれている】。東の嘘を確かめて振り返った時に、音も無く開く。
    #   「行ける道は、行けないと思った所にしか無い」。
    dict(name="stage4", tag="Stage_4", title=4,
         rooms=[R("A", "box12", (0.0, 0.0), 1.0, L_PLAIN),
                R("C", "box12", (0.0, 22.0), 2.0, L_BAR)],
         seams=[SEAM("s1", "A", "N", 0.0)],
         fakes=[FAKE("f1", "A", "E", 0.0, depth=2.5, look=20.0),
                FAKE("f2", "A", "W", 0.0, depth=2.5, look=22.0)],
         morphs=[MORPH("m1", "A", at=(7.9, 0.0), r=2.8, delay=0.5,
                       org=[("locker", 5.4, 2.6, 270.0)], alt=ALT_A,
                       unseal=["s1a"], light=(1.00, 0.60, 0.28)),
                 MORPH("m2", "A", at=(-7.9, 0.0), r=2.8, delay=0.5,
                       org=[("bench", 1.6, -1.0, 90.0)], alt=[("bench", -2.0, -4.4, 0.0)],
                       seal=["f1"], light=(0.55, 0.72, 1.00))],
         spawn=(0.0, -4.0, 90.0), goal=(-9.0, 22.0), goalYaw=90.0,
         start="A", goalRoom="C", minHops=1, teach=None,
         cine=[("A", (0.0, 2.4, -4.6), "A", (6.0, 1.6, 0.0), 2.4),
               ("A", (0.0, 1.7, -4.0), "A", (6.0, 1.6, 0.0), 1.4)]),

    # ===================== 5「溝」 大広間。柱が物差しになる =====================
    # ★狙い: 部屋を大きくしても【柱の太さは変わらない】。縮尺 2 の大広間では、
    #   さっきまで抱えるほど太かった柱が爪楊枝のように細く見える。床の溝 4.6m も同じで、
    #   x1 の広間では絶対に跳べない裂け目が、x2 の写しでは 1 歩で跨げる。
    dict(name="stage5", tag="Stage_5", title=5,
         rooms=[R("H", "hall20", (0.0, 0.0), 1.0, L_HALL),
                R("H2", "hall20", (0.0, -34.0), 2.0, L_HALL),
                R("T", "box12", (0.0, -61.0), 0.5, L_EAVE)],
         seams=[SEAM("s1", "H", "S", -6.0), SEAM("s2", "H2", "S", 0.0, sill=SILL_HI)],
         windows=[WIN("H", "S", 4.0)],
         spawn=(-6.0, -6.0, 180.0), goal=(2.3, -62.5), goalYaw=90.0,
         start="H", goalRoom="T", minHops=2, teach=None,
         cine=[("H2", (-10.0, 7.0, 14.0), "H2", (0.0, 1.0, -14.0), 2.6),
               ("H", (-4.0, 1.7, -2.0), "H", (-6.0, 1.5, -10.0), 1.6)]),

    # ===================== 6「輪」 回っていたら最初の部屋に戻った =====================
    # ★狙い: 【同じ部屋に戻ってきた】と確信させてから、それが縮尺違いの写しだと分からせる。
    #   A(x1) → B(x2) → C(x1) と回ると、C は A と寸分違わぬ絵になる(什器の見え方まで同じ)。
    #   ここで初めて「さっきの部屋はどれだったのか」が分からなくなる。
    #   C で背を向けている間に家具が入れ替わるので、確信はさらに強くなる。
    dict(name="stage6", tag="Stage_6", title=6,
         # ★A と C は【縮尺も間取りも家具も同じ】= 絵として区別がつかない。これが仕掛けの本体。
         rooms=[R("A", "box12", (0.0, 0.0), 1.0, L_PLAIN),
                R("B", "box12", (22.0, 0.0), 2.0, L_PLAIN),
                R("C", "box12", (22.0, 22.0), 1.0, L_PLAIN),
                R("D", "box12", (35.0, 22.0), 0.5, L_EAVE)],
         seams=[SEAM("s1", "A", "E", 0.0), SEAM("s2", "B", "N", 0.0), SEAM("s3", "C", "E", 0.0)],
         # ★窓は置けない: 縮尺 2 の相手側では扉 4.0m と窓 7.2m で 6.4m 離す必要があり、
         #   A 側では 12.8m 相当 = 壁(12.3m)に収まらない。窓は第2面で教えてある。
         fakes=[FAKE("f1", "A", "N", 0.0, depth=2.4, look=20.0)],
         morphs=[MORPH("m1", "C", at=(0.0, -4.4), r=3.4, delay=1.0,
                       org=[("crate", 3.4, -4.6, 20.0)], alt=[("crate", -3.0, 3.0, 20.0)],
                       light=(0.98, 0.94, 0.86))],
         spawn=(3.0, -3.0, 0.0), goal=(37.3, 23.5), goalYaw=90.0,
         start="A", goalRoom="D", minHops=3, teach=None,
         cine=[("C", (4.0, 1.7, -4.0), "C", (-1.0, 1.4, 4.0), 2.2),
               ("A", (2.0, 1.7, -4.5), "A", (6.0, 1.5, 0.0), 1.6)]),

    # ===================== 7「一棟」 4 つの写しを縮尺で渡り歩く =====================
    # ★狙い: ここまでの関門を 1 本に繋ぐ。全部同じ間取り(柵 x=-3.5 / 隙間 x=2.5)で、
    #   縮尺だけが 1 → 2 → 0.5 → 2 と変わる。同じ柵が「壁 / 膝 / 見上げる壁 / 膝」に見える。
    #   x2 → x0.5 の扉は膝の敷居なので、入ったら二度と戻れない。
    dict(name="stage7", tag="Stage_7", title=7,
         # ★口はすべて北へ。西の壁に付けると【柵が扉の 5m 手前に立ちはだかる】ので
         #   助走が取れない(check_runup が弾く)。柵は必ず口から遠い側で跨がせる。
         rooms=[R("A", "box12", (0.0, 0.0), 1.0, L_BOTH),
                R("C", "box12", (0.0, 22.0), 2.0, L_BOTH),
                R("D", "box12", (-8.8, 41.0), 0.5, L_BOTH),
                R("E", "box12", (-7.3, 60.0), 2.0, L_BOTH)],
         seams=[SEAM("s1", "A", "N", 0.0), SEAM("s2", "C", "N", -4.4, sill=SILL_HI),
                SEAM("s3", "D", "N", 3.0)],
         fakes=[FAKE("f1", "A", "S", 0.0, depth=2.5, look=20.0)],
         morphs=[MORPH("m1", "A", at=(0.0, -8.0), r=2.8, delay=0.5,
                       org=[("crate", 3.4, -4.6, 20.0)], alt=ALT_B,
                       light=(0.62, 0.74, 1.00))],
         spawn=(0.0, -4.0, 0.0), goal=(-16.3, 60.0), goalYaw=90.0,
         start="A", goalRoom="E", minHops=3, teach=None,
         cine=[("E", (-2.0, 5.0, -8.0), "E", (-9.2, 1.0, 0.0), 2.4),
               ("A", (0.0, 1.7, -4.4), "A", (0.0, 1.6, 6.0), 1.6)]),

    # ===================== 8「鏡」 左右が反転した同じ部屋 =====================
    # ★狙い: 最終面。間取りは同じでも【什器が左右反転して置かれた写し】を混ぜる。
    #   絵として見慣れているのに、体が覚えた「柵は西」が通用しない。
    #   偽の廊下・背後改変・一方通行の敷居を全部同時に使う。
    #   A(x1 柵は西) → B(x2 柵は東・鏡) 跨ぐ → C(x0.5) 隙間をくぐる → D(x2) 出口。
    dict(name="stage8", tag="Stage_8", title=8,
         rooms=[R("A", "box12", (0.0, 0.0), 1.0, L_BOTH),
                R("B", "box12", (0.0, 22.0), 2.0, L_BAR_B),
                R("C", "box12", (19.0, 22.0), 0.5, L_EAVE),
                R("D", "box12", (20.5, 41.0), 2.0, L_BAR_B)],
         seams=[SEAM("s1", "A", "N", 0.0), SEAM("s2", "B", "E", 0.0, sill=SILL_HI),
                SEAM("s3", "C", "N", 3.0)],
         fakes=[FAKE("f1", "A", "S", 0.0, depth=2.5, look=21.0)],
         morphs=[MORPH("m1", "A", at=(0.0, -8.0), r=2.8, delay=0.5,
                       org=[("locker", 5.4, 2.6, 270.0)], alt=ALT_A,
                       light=(1.00, 0.58, 0.26)),
                 MORPH("m2", "C", at=(0.0, -2.2), r=2.4, delay=0.9,
                       org=[("crate", 3.4, -4.6, 20.0)], alt=[("bench", -2.0, 3.0, 0.0)],
                       seal=["s2b"], light=(0.58, 0.74, 1.00))],
         spawn=(0.0, -4.0, 0.0), goal=(29.0, 41.0), goalYaw=270.0,
         start="A", goalRoom="D", minHops=3, teach=None,
         cine=[("D", (2.0, 5.0, -8.0), "D", (8.5, 1.0, 0.0), 2.4),
               ("A", (0.0, 1.7, -4.4), "A", (0.0, 1.6, 6.0), 1.6)]),
]


def main():
    lua = []
    manifest = {}
    for i, st in enumerate(STAGES):
        W = World(st)
        data = W.build()
        check_footholds(st, W)
        check_runup(st, W)
        check_fakes(st, W)
        pts = check_solvable(st, W)
        check_no_deadend(st, W)
        centers = check_cine(st, W)
        manifest.update(W.manifest)

        path = os.path.join(OUT, st["name"] + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("wrote", path)

        nxt = STAGES[i + 1]["name"] if i + 1 < len(STAGES) else None
        cine = cine_world(st, centers)
        L = []
        L.append('    ["Logic_%s"] = { n = %d, scene = "scenes/%s.json", next = %s,'
                 % (st["tag"], st["title"], st["name"], ('"scenes/%s.json"' % nxt) if nxt else "nil"))
        L.append('        tunnels = {')
        for t in W.tunnels:
            L.append('            { id = "%s", ax = %.3f, az = %.3f, nx = %.3f, nz = %.3f, L = %.2f, '
                     'sa = %.3f, sb = %.3f, wa = %.2f, wb = %.2f, y0 = %.2f },'
                     % (t["id"], t["ax"], t["az"], t["nx"], t["nz"], t["L"], t["sa"], t["sb"], t["wa"], t["wb"], t["y0"]))
        L.append('        },')
        L.append('        warps = {')
        for w in W.warps:
            L.append('            { id = "%s", px = %.3f, pz = %.3f, nx = %.3f, nz = %.3f, dx = %.3f, dy = %.3f, dz = %.3f, loops = %d, hw = %.2f },'
                     % (w["id"], w["px"], w["pz"], w["nx"], w["nz"], w["dx"], w["dy"], w["dz"], w["loops"], w["hw"]))
        L.append('        },')
        L.append('        morphs = {')
        for mo in W.morphs:
            L.append('            { id = "%s", x = %.3f, z = %.3f, wx = %.3f, wz = %.3f, r = %.2f, delay = %.1f, light = %s, light0 = %s,'
                     % (mo["id"], mo["x"], mo["z"], mo["wx"], mo["wz"], mo["r"], mo["delay"],
                        ("{ %.2f, %.2f, %.2f }" % mo["light"]) if mo["light"] else "nil",
                        "{ %.2f, %.2f, %.2f }" % mo["light0"]))
            L.append('              room = "%s", seal = { %s }, unseal = { %s },'
                     % (mo["room"], ", ".join('"%s"' % x for x in mo["seal"]),
                        ", ".join('"%s"' % x for x in mo["unseal"])))
            L.append('              rows = { %s } },'
                     % ", ".join('{ "%s", %.2f, %.2f, %.2f, "%s" }' % rr for rr in mo["rows"]))
        L.append('        },')
        L.append('        plugs = {')
        for pg in W.plugs:
            L.append('            { id = "%s", x = %.3f, y = %.3f, z = %.3f, mode = "%s", delay = %.1f, auto = %s },'
                     % (pg["id"], pg["x"], pg["y"], pg["z"], pg["mode"], pg["delay"],
                        "true" if pg["auto"] else "false"))
        L.append('        },')
        L.append('        hint = { %s },' % ", ".join("{ %.2f, %.2f }" % (x, z) for (x, z) in pts))
        L.append('        start = "%s", goalRoom = "%s",' % (st["start"], st["goalRoom"]))
        L.append('        spawn = { %.1f, %.1f, %.1f }, teach = %s,'
                 % (st["spawn"][0], st["spawn"][1], st["spawn"][2], ('"%s"' % st["teach"]) if st.get("teach") else "nil"))
        L.append('        cine = {')
        for c in cine:
            L.append('            { %.2f, %.2f, %.2f, %.2f, %.2f, %.2f, %.2f },' % c)
        L.append('        } },')
        lua.append("\n".join(L))

    mpath = os.path.join(MODELS, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    missing = [k for k in manifest if not os.path.exists(os.path.join(MODELS, k + ".gltf"))]
    print("manifest: %d models, %d missing" % (len(manifest), len(missing)))
    if missing:
        print("  ★ BlenderMCP で blender_kit.py(JX_MANIFEST_ONLY=True)を実行して出すこと:", missing[:6], "...")

    lpath = os.path.join(HERE, "..", "assets", "components", "Junction.lua")
    with open(lpath, encoding="utf-8") as f:
        src = f.read()
    head = "-- >>>STAGES (source/gen_stages.py が自動生成)"
    tail = "    -- <<<STAGES"
    a = src.index(head) + len(head)
    b = src.index(tail)
    src = src[:a] + "\n" + "\n".join(lua) + "\n" + src[b:]
    with open(lpath, "w", encoding="utf-8") as f:
        f.write(src)
    print("patched", lpath)


if __name__ == "__main__":
    main()
