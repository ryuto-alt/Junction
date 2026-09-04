# -*- coding: utf-8 -*-
"""JUNCTION / 継ぎ目 v6 のステージを生成する。シーン JSON はここが唯一の正。契約書は docs/V6.md。

実行:
  python source/gen_stages.py     # scenes/*.json, Junction.lua の STAGES, models/gen/manifest.json
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
MANIFEST = os.path.join(MODELS, "gen", "manifest.json")

# ---------------------------------------------------------------- 置き場所(assets/models/ 以下)
# ★source/blender_kit.py の同名関数と【必ず一致】させること。片方だけ直すと
#   シーンが参照するパスと実ファイルの場所がずれて、モデルが丸ごと出なくなる。
#   新しいモデルを足したら、ここにも足す(知らない名前は例外で落とす = 直下に散らかさない)。
_TRIM = ("column", "doorleaf", "eave", "seam", "divider", "blocker", "barrier", "railing", "fence")
_PROPS = ("bench", "locker", "crate", "vent", "pipes", "troffer", "rack", "drum", "sign")
_GAME = ("goal", "pin", "band", "lane", "figure", "hand", "joint", "jframe",
         "membrane", "ball", "plate")


def dest_of(name):
    """モデル名(拡張子なし)から assets/models/ 以下の置き場所を返す。"""
    if name.startswith("fm_"):
        return "gen/floor"
    if name.startswith("cm_"):
        return "gen/ceil"
    if name.startswith("tn_"):
        return "gen/tunnel"
    if name.startswith("am_"):
        return "gen/room"
    if name.startswith("wm_"):
        return "gen/wall"
    if name.startswith("wall"):
        return "arch/wall"
    if name.startswith("floor") or name.startswith("ceiling"):
        return "arch/slab"
    if name in _TRIM:
        return "arch/trim"
    if name in _PROPS:
        return "props"
    if name in _GAME:
        return "game"
    raise KeyError("置き場所が決まっていないモデル名: %s (dest_of に足すこと)" % name)


def mdl(name):
    """モデル名 -> シーン JSON に書く assets 相対パス。★パスを直書きせず
    必ずここを通すこと(フォルダ構成を変えてもここ 1 箇所で済む)。"""
    return "models/%s/%s.gltf" % (dest_of(name), name)

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
CARRY_TOP = 0.70  # 運べる木箱の天端。踏み台にすると climb_h に足される
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
    "box12": dict(ix=12.0, iz=12.0, h=6.0, tag="", floor=mdl("floor"),
                  ceil=mdl("ceiling"),
                  lights=[(-3.2, -3.2), (3.2, -3.2), (-3.2, 3.2), (3.2, 3.2)], lrange=22.0),
    "hall20": dict(ix=20.0, iz=20.0, h=7.0, tag="20", floor=mdl("floor20"),
                   ceil=mdl("ceiling20"),
                   lights=[(x, z) for z in (-6.4, 0.0, 6.4) for x in (-6.4, 0.0, 6.4)],
                   lrange=24.0),
    "corr18": dict(ix=18.0, iz=8.0, h=3.2, tag="18", floor=mdl("floor18x8"),
                   ceil=mdl("ceiling18x8"),
                   lights=[(-6.0, 0.0), (0.0, 0.0), (6.0, 0.0)], lrange=15.0),
    # ★v6.1 回廊用。壁・床・天井を manifest(Blender)で出す
    "corr12": dict(ix=3.0, iz=12.0, h=3.2, tag="", floor=None, ceil=None, mf=True,
                   lights=[(0.0, -4.0), (0.0, 0.0), (0.0, 4.0)], lrange=10.0),
    # ---------------- v10「継ぎ目の館」。超巨大な施設のための間取り ----------------
    # ★全部 mf=True(壁も床も天井も manifest で出す)。寸法は自由に足してよい。
    "atrium40": dict(ix=40.0, iz=40.0, h=14.0, tag="40", floor=None, ceil=None, mf=True,
                     lights=[(x, z) for z in (-15.0, -7.5, 0.0, 7.5, 15.0)
                             for x in (-15.0, -7.5, 0.0, 7.5, 15.0)], lrange=30.0),
    "hall26": dict(ix=26.0, iz=26.0, h=9.0, tag="26", floor=None, ceil=None, mf=True,
                   lights=[(x, z) for z in (-8.5, 0.0, 8.5) for x in (-8.5, 0.0, 8.5)],
                   lrange=24.0),
    "corr36": dict(ix=36.0, iz=9.0, h=5.0, tag="36", floor=None, ceil=None, mf=True,
                   lights=[(x, 0.0) for x in (-14.0, -7.0, 0.0, 7.0, 14.0)], lrange=15.0),
    "corr30": dict(ix=9.0, iz=30.0, h=4.4, tag="30", floor=None, ceil=None, mf=True,
                   lights=[(0.0, z) for z in (-12.0, -6.0, 0.0, 6.0, 12.0)], lrange=14.0),
    "store22": dict(ix=22.0, iz=16.0, h=5.5, tag="22", floor=None, ceil=None, mf=True,
                    lights=[(x, z) for z in (-5.0, 5.0) for x in (-7.5, 0.0, 7.5)], lrange=16.0),
    "tilt16": dict(ix=16.0, iz=16.0, h=6.0, tag="16", floor=None, ceil=None, mf=True,
                   lights=[(x, z) for z in (-5.0, 5.0) for x in (-5.0, 5.0)], lrange=18.0),
}
WALLTAG = {"box12": ("", ""), "hall20": ("20", "20"), "corr18": ("18", "8"), "corr12": ("", ""),
           "atrium40": ("40", "40"), "hall26": ("26", "26"), "corr36": ("36", "9"),
           "corr30": ("9", "30"), "store22": ("22", "16"), "tilt16": ("16", "16")}

C_WALL = [0.62, 0.60, 0.55]
C_FLOOR = [0.24, 0.20, 0.12]
C_CEIL = [0.72, 0.72, 0.70]
C_GOAL = [0.10, 0.75, 0.50]
C_DIV = [0.55, 0.56, 0.54]
C_PAINT = [0.90, 0.89, 0.86]
C_PIT = [0.05, 0.05, 0.06]
# ★継ぎ手の筒の中。環境光 0.16 を掛けても 0.005 なので【何も見えない】。
#   ★真っ黒(0.03)にしたら【転送前が暗黒 / 転送後は部屋の光で灰色】になり、
#     明るさの落差そのものが切り替わりを教えてしまった(実測)。
#     筒は【薄暗いが見えている】くらいが正しい。両端の筒は同じ材質・同じ灯りなので、
#     見えていても区別が付かない。変わるのは奥の板が明るい口に変わることだけ。
C_DARK = [0.072, 0.072, 0.080]
C_SHUT = [0.175, 0.178, 0.188]   # 継ぎ手の奥の板(シャッターに見える明度)
# ★継ぎ手の筒の奥行きと、転送面の位置。ここは【実測で決めた】。
#   転送の瞬間に見えているのは「筒の奥にある面」だけ。その面までの距離が
#   入る側(奥の板まで D-P)と出る側(向こうの口まで P)で【違うと画角が変わる】=
#   切り替わりが一目で分かる。P = D/2 にすると前後で
#   【同じ位置・同じ大きさの長方形】になり、変わるのは中身の明るさだけになる。
#   絵としては「奥のシャッターが開いた」に見える。
#     実測: D=2.0 / P=1.55 -> 転送直後に部屋が画面の 7 割。誰でも気づく
#           D=4.2 / P=2.1  -> 前後とも 2.1m 先の長方形。落差は明るさだけ
PORT_D = 4.2
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


def _flat(xs):
    out = []
    for x in xs:
        out.extend(x) if isinstance(x, (list, tuple)) else out.append(x)
    return out


def key_of(obj):
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.md5(s.encode()).hexdigest()[:8]


# ---------------------------------------------------------------- v10: 回転(オイラー角)の合成
# ★エンジンの Transform は【行ベクトル・ZXY 順】(src/ecs/Components.cpp):
#     v' = v * Rz(rotation.z) * Rx(rotation.x) * Ry(rotation.y)
#   だから「先にローカルで転がして、後からワールドの Y 回りに振る」は
#   (z=転がし, y=振り) をそのまま書けばいい。それ以外(傾いた板・傾いた部屋)は
#   行列で組んでから分解する。手で三角関数を展開すると必ず規約を取り違える。
def m_mul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def m_rx(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[1, 0, 0], [0, c, s], [0, -s, c]]


def m_ry(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, 0, -s], [0, 1, 0], [s, 0, c]]


def m_rz(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, s, 0], [-s, c, 0], [0, 0, 1]]


def m_of_euler(rot):
    """rotation=(x,y,z) 度 -> 行ベクトルの回転行列(行 = ローカル軸のワールド向き)"""
    return m_mul(m_mul(m_rz(rot[2]), m_rx(rot[0])), m_ry(rot[1]))


def euler_of_m(M):
    """行列 -> rotation=(x,y,z) 度。QuaternionToEulerDegrees と同じ解き方。"""
    sp = max(-1.0, min(1.0, -M[2][1]))
    pitch = math.asin(sp)
    if abs(sp) < 0.9999:
        yaw = math.atan2(M[2][0], M[2][2])
        roll = math.atan2(M[0][1], M[1][1])
    else:                                   # ジンバルロック
        yaw = math.atan2(-M[0][2], M[0][0])
        roll = 0.0
    return (math.degrees(pitch), math.degrees(yaw), math.degrees(roll))


def m_apply(M, v):
    """行ベクトル v * M"""
    return tuple(sum(v[k] * M[k][j] for k in range(3)) for j in range(3))


def euler_of_basis(ex, ey, ez):
    """ローカル X/Y/Z 軸のワールド向き(正規直交)から rotation を出す。
    傾いた板の当たり判定はこれで置く。"""
    return euler_of_m([list(ex), list(ey), list(ez)])


def norm3(v):
    n = math.sqrt(sum(q * q for q in v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def cross3(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def plate_from_quad(name, pts, thick, color, parent, rough=0.92, outward=None, pad=0.0):
    """★平面な四角形 pts(4点)を、そのまま【傾けた板 1 枚】の当たり判定にする。
    v9 の教訓: 傾いた面を軸並行の箱で刻むと階段になって視点が跳ねる。平面は 1 枚で厳密。
    outward = 部屋の【外】を向く向き。板はそちらへ厚み分だけ逃がす(表面は四角形のまま)。"""
    cx = sum(p[0] for p in pts) / 4.0
    cy = sum(p[1] for p in pts) / 4.0
    cz = sum(p[2] for p in pts) / 4.0
    u = norm3(tuple(pts[1][i] - pts[0][i] + pts[2][i] - pts[3][i] for i in range(3)))
    w = tuple(pts[3][i] - pts[0][i] + pts[2][i] - pts[1][i] for i in range(3))
    n = norm3(cross3(u, w))
    w = norm3(cross3(n, u))
    lu = max(abs(sum((p[i] - (cx, cy, cz)[i]) * u[i] for i in range(3))) for p in pts) * 2.0 + pad
    lw = max(abs(sum((p[i] - (cx, cy, cz)[i]) * w[i] for i in range(3))) for p in pts) * 2.0 + pad
    if outward is not None and sum(n[i] * outward[i] for i in range(3)) > 0:
        n = (-n[0], -n[1], -n[2])
        w = (-w[0], -w[1], -w[2])
    c = (cx - n[0] * thick * 0.5, cy - n[1] * thick * 0.5, cz - n[2] * thick * 0.5)
    rot = euler_of_basis(u, n, w)           # ローカル X=u / Y=n(厚み) / Z=w
    return box(name, c, (lu, thick, lw), color, rot=rot, parent=parent, rough=rough,
               visible=False)


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
        self.ports = []        # v10: 継ぎ手の口
        self.linkrows = []     # v10: 継ぎ手の結線
        self.portrooms = {}
        self.watchers = []     # v10: 見ている間は動かない物
        self.creeps = []       # v10: 気づかない速さで動く物
        self.rolls = []        # v10: 視界を傾ける区画
        self.amesboxes = []    # v10: エイムズの部屋の外形(検査用)
        self.amesmap = {}      # v10: 別棟の局所座標 -> 世界座標
        self.dynprops = []     # v11: 動く剛体(やり直しで元の位置へ戻す)
        self.gates = []        # v11: 継ぎ手の枠
        self.gpairs = []       # v11: 重ねると繋がる枠の組
        self.plates = []       # v11: 重量板
        self.tilts = []        # v11: 視線で傾く床
        self._tiltprops = []
        self.marks = []        # v11.1: 立ち位置の印
        self.fovramps = []     # v11: 歩く位置で画角を変える帯
        self.noleaf = set()    # v10: 扉板を立てない口(継ぎ手と別棟の入口)

    # ---- 口。off は部屋の【単位】座標(縮尺前)。世界では off*k ----
    def add_opening(self, rid, wall, off_u, kind, sill, oid, osize=None):
        """★osize = その口だけの縮尺。省略すると部屋の縮尺。
        部屋の縮尺と違う大きさの口を開けられる = 【大きい部屋に小さな戸】が作れる。
        口の大きさは廊下の sa/sb にもなるので、両端を同じ osize にすると
        先細りしない廊下 = 通っても体の大きさが変わらない道になる。"""
        r = self.rooms[rid]
        fr = wall_frame(r, wall)
        k = fr["k"]
        ok = k if osize is None else float(osize)
        fy = floor_y(r, wall)
        if kind == "door":
            w, h = DOOR_W * ok, DOOR_H * ok
            y0 = fy + sill
        else:
            w, h, y0 = WIN_W * ok, WIN_H * ok, fy + WIN_SILL * ok
        off = off_u * k
        if abs(off) + w * 0.5 > fr["L"] * 0.5 - 0.6 * k:
            raise SystemExit("%s: %s.%s の口 %s が壁からはみ出す(off=%.1f)" % (self.st["name"], rid, wall, oid, off_u))
        lst = self.openings.setdefault((rid, wall), [])
        for o in lst:
            if abs(o["off"] - off) < (o["w"] + w) * 0.5 + 0.4 * k:
                raise SystemExit("%s: %s.%s で口 %s と %s が重なる" % (self.st["name"], rid, wall, o["id"], oid))
        lst.append(dict(off=off, w=w, h=h, y0=y0, kind=kind, id=oid))
        pos = (fr["face"][0] + fr["along"][0] * off, fr["face"][1] + fr["along"][1] * off)
        m = dict(room=rid, wall=wall, off=off, size=ok, sill=y0, sillRel=(y0 - fy), pos=pos, w=w, h=h, n=fr["n"],
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
    def frustum(self, g, name, ma, mb, glass=False, L=None, solid=False, cap=False, mat=None):
        """口 a から口 b へ 4m の先細り廊下。見た目は Blender の台形メッシュ、
        当たり判定は【面ごとに 1 枚の傾けた板】。

        ★v9-1「部屋と部屋の間に白い壁がある」の真犯人は cap だった。
          台形メッシュは【突き当りの壁】を必ず持っていて、偽の廊下ではそれが落ちだが、
          本物の継ぎ目でも同じメッシュを使っていたので、向こうの部屋の開口を
          白い板が【完全に塞いでいた】。当たり判定は無いので歩けば通り抜けるが、
          絵は「部屋と部屋の間の白い壁」。→ cap は偽の廊下だけ True。
          本物は突き当りが無い = 向こうの部屋がそのまま見える。

        ★v9-2「坂道でがくんと視点が跳ねる」の真犯人もここ。当たり判定を 8 段の箱で
          刻んでいたので、床が傾いている廊下(偽の廊下は強制遠近法で床が上がる)を歩くと
          1 段 0.14m の階段を 8 回登ることになり、CharacterController の段差登りが
          そのつどカメラを跳ね上げていた。床も天井も側壁も【平面】なので、
          傾けた板 1 枚ずつで厳密に置き換えられる。段差ゼロ = 跳ねない。
        """
        n, al = ma["n"], ma["along"]
        zax = abs(n[1]) > 0.5
        L = L or GAP
        wa, ha, ya = ma["w"], ma["h"], ma["sill"]
        wb, hb, yb = mb["w"], mb["h"], mb["sill"]
        spec = dict(tunnel=True, wa=round(wa, 3), ha=round(ha, 3), ya=round(ya, 3),
                    wb=round(wb, 3), hb=round(hb, 3), yb=round(yb, 3), L=round(L, 3),
                    cap=1 if cap else 0, v=3)
        # ★廊下の床は【母屋と同じ材質】でなければならない。v10 で部屋をコンクリートに
        #   したのに廊下だけカーペットのままだったので、偽の廊下が【床の色で一目で分かった】。
        if mat:
            spec["mat"] = mat
        mname = "tn_%s" % key_of(spec)
        self.manifest[mname] = spec
        yaw = math.degrees(math.atan2(n[0], n[1]))
        self.ents.append(model("TunM_%s" % name, mdl(mname),
                               (ma["pos"][0], 0.0, ma["pos"][1]), yaw, g))

        def at(t, lat):
            return (ma["pos"][0] + n[0] * t + al[0] * lat, ma["pos"][1] + n[1] * t + al[1] * lat)

        def S3(w, h, dp):
            return (w, h, dp) if zax else (dp, h, w)

        T, MG = 0.3, 0.6                       # 板の厚み / 幅の余裕
        wmax = max(wa, wb) + MG
        cx, cz = at(L * 0.5, 0.0)

        def plate(nm, ymid, dy):
            """進行方向に沿って dy だけ上がる板。1 枚で坂を作る。
            ★回転の符号は build_room のスロープ床と同じ規約(右手系)。"""
            ang = math.degrees(math.atan2(dy, L))
            ln = math.hypot(L, dy)
            if zax:
                sc, rot = (wmax, T, ln), (-ang * n[1], 0.0, 0.0)
            else:
                sc, rot = (ln, T, wmax), (0.0, 0.0, ang * n[0])
            self.ents.append(box(nm, (cx, ymid, cz), sc, C_WALL, rot=rot, parent=g, visible=False))

        # 床(上面が ya→yb)と天井(下面が ya+ha→yb+hb)
        plate("Tun_%s_F" % name, (ya + yb) * 0.5 - T * 0.5, yb - ya)
        plate("Tun_%s_C" % name, (ya + ha + yb + hb) * 0.5 + T * 0.5, (yb + hb) - (ya + ha))
        # 側壁。すぼまる向きへ yaw で寝かせた板 1 枚(ここも 8 段だと横に引っかかっていた)
        ylo = min(ya, yb) - MG * 0.5
        yhi = max(ya + ha, yb + hb) + MG * 0.5
        for j, sg in enumerate((-1, 1)):
            dxw = n[0] * L + al[0] * sg * (wb - wa) * 0.5
            dzw = n[1] * L + al[1] * sg * (wb - wa) * 0.5
            x2, z2 = at(L * 0.5, sg * ((wa + wb) * 0.25 + T * 0.5))
            self.ents.append(box("Tun_%s_S%d" % (name, j), (x2, (ylo + yhi) * 0.5, z2),
                                 (T, yhi - ylo, math.hypot(dxw, dzw)), C_WALL,
                                 rot=(0.0, math.degrees(math.atan2(dxw, dzw)), 0.0),
                                 parent=g, visible=False))
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
        ma = self.add_opening(sp["room"], sp["wall"], sp["off"], "door", sill, sid + "a",
                              sp.get("osize"))
        rid2, w2, off2 = self.partner_room(sp["room"], sp["wall"], ma["pos"])
        mb = self.add_opening(rid2, w2, off2, "door", sill, sid + "b", sp.get("osizeB"))
        self.links[sid + "a"] = sid + "b"
        self.links[sid + "b"] = sid + "a"
        g = group(self.ents, "Seam %s" % sid, self.g_seams)
        self.frustum(g, sid, ma, mb, mat=self.rooms[sp["room"]].get("floorMat"))
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
        self.frustum(g, fid, ma, mb, L=D, solid=True, cap=True,
                     mat=self.rooms[sp["room"]].get("floorMat"))
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
            self.ents.append(model("FakeT_%s_%d" % (fid, i), mdl("troffer"), (x, hh, z), 0.0, g,
                                   (rr, rr, rr)))
            self.ents.append(plight("FakeL_%s_%d" % (fid, i), (x, hh - 0.1 * rr, z),
                                    (0.98, 0.96, 0.90), 3.0 * rr * rr + 0.3, 3.0 * rr + 0.4, g))
        # ★突き当りに【小さな出口の扉】。20m 先の緑の扉に見える = ここへ行くしかないと思わせる餌。
        #   実物と同じ物を r 倍で置くので、見かけの角度は本物とぴったり同じになる。
        x, z = at(D - 0.06, 0)
        yaw = math.degrees(math.atan2(-n[0], -n[1]))
        gk = r * 2.0
        self.ents.append(model("FakeD_%s" % fid, mdl("goal"), (x, mb["sill"], z), yaw, g,
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

    # ================================ v10: 継ぎ手(port / link) ================================
    # ★このゲームの中心装置。「継ぎ目の向こう」を【任意の場所】にする。
    #
    #   口の奥は 2m の【真っ暗な行き止まりの筒】で、両端の筒は寸法も材質も同じ。
    #   筒の奥 1.55m の面を越えた瞬間に、相手の筒の同じ位置・同じ姿勢へ置き換える。
    #   ・暗いので筒の中では何も見えない = 入れ替わった絵の変化が【存在しない】
    #   ・横位置と向きを相手の筒の座標系へ写すので、歩き続けるだけで自然に出てくる
    #   ・音も出さない。振り返っても、来たとおりの筒がある
    #
    #   結果:【歩いた距離と方角】でプレイヤーが作る心の地図だけが壊れる。
    #   目の前で何かが変わるわけではないので、その場では絶対に気づけない。
    #   気づくのは「東へ 40m 歩いたのに、ホールの西側に立っている」時。
    #
    # ★warp(v6)との違い: warp は【同じ廊下の中で前の廊下へ戻す】だけで、方角を変えられず、
    #   継ぎ目(先細りの廊下)が要った。port は壁でも部屋の真ん中でも置け、向きも大きさも
    #   付け替えられる。施設まるごとを非ユークリッドに組める。
    def port(self, sp):
        pid = sp["id"]
        D = sp.get("depth", PORT_D)
        sz = sp.get("size", 1.0)
        rid = sp["room"]
        r = self.rooms[rid]
        g = group(self.ents, "Port %s" % pid, self.g_seams)
        if sp.get("wall"):
            hole = sp.get("hole", sz)
            m = self.add_opening(rid, sp["wall"], sp.get("off", 0.0), "door", 0.0, pid, osize=hole)
            n, al = m["n"], m["along"]
            pos, sill = m["pos"], m["sill"]
            w, h = DOOR_W * sz, DOOR_H * sz
            self.noleaf.add(pid)
            self.ents.append(model("PortF_%s" % pid, mdl("jframe"), (pos[0], sill, pos[1]),
                                   WALLS[sp["wall"]]["yaw"], g, (sz, sz, sz)))
            if hole > sz + 1e-6:
                # ★母屋の穴が筒より大きい時の【襟】。傾いた部屋は壁ごと転がっているので、
                #   開口も転がる = 水平な筒とは角がずれる。大きめに開けて水平な襟で塞ぐと、
                #   「建物は傾いているのに継ぎ手だけが水平」という絵になる(そういう施設に見える)。
                HW = DOOR_W * hole * 0.5 * 1.22        # 襟の半幅(転がった開口の外接を覆う)
                HH = DOOR_H * hole * 1.16              # 襟の高さ
                zax0 = abs(n[1]) > 0.5
                for nm, (ox, oy, sx, sy) in (
                        ("T", (0.0, (h + HH) * 0.5, HW * 2, HH - h)),
                        ("L", (-(HW + w * 0.5) * 0.5, h * 0.5, HW - w * 0.5, h)),
                        ("R", ((HW + w * 0.5) * 0.5, h * 0.5, HW - w * 0.5, h))):
                    if sx <= 0.02 or sy <= 0.02:
                        continue
                    self.ents.append(box("PortC_%s_%s" % (pid, nm),
                                         (pos[0] + al[0] * ox - n[0] * 0.18, sill + oy,
                                          pos[1] + al[1] * ox - n[1] * 0.18),
                                         (sx, sy, 0.36) if zax0 else (0.36, sy, sx),
                                         C_DIV, parent=g, rough=0.55))
        else:
            # 部屋の中に単体で立つ継ぎ手ユニット。★筐体(joint.gltf)が外から見える箱になる
            into = sp["into"]
            n = (float(WALLS[into]["sign"]) if WALLS[into]["axis"] == "x" else 0.0,
                 float(WALLS[into]["sign"]) if WALLS[into]["axis"] == "z" else 0.0)
            al = (-n[1], n[0])
            k = r["scale"]
            cx, cz = r["at"]
            if sp.get("ames"):
                aid2, alat, at2 = sp["ames"]
                qq = self.amesmap[aid2](alat, 0.0, at2)
                pos = (qq[0], qq[2])
            else:
                pos = (cx + sp["at"][0] * k, cz + sp["at"][1] * k)
            w, h = DOOR_W * sz, DOOR_H * sz
            sill = floor_y(r)
            yaw = math.degrees(math.atan2(n[0], n[1]))
            self.ents.append(model("PortH_%s" % pid, mdl("joint"), (pos[0], sill, pos[1]), yaw, g,
                                   (sz, sz, sz)))
            self.ents.append(model("PortF_%s" % pid, mdl("jframe"), (pos[0], sill, pos[1]),
                                   (yaw + 180.0) % 360.0, g, (sz, sz, sz)))
            m = dict(room=rid, wall=None, off=0.0, size=sz, sill=sill, sillRel=0.0, pos=pos,
                     w=w, h=h, n=n, along=al, kind="door")
            self.mouths[pid] = m
            # 筐体の外殻の当たり判定(側面と背面。中は通れる)
            HW, HD = w * 0.5 + 0.30 * sz, D + 0.30 * sz
            for s2 in (-1, 1):
                x2 = pos[0] + n[0] * HD * 0.5 + al[0] * s2 * HW
                z2 = pos[1] + n[1] * HD * 0.5 + al[1] * s2 * HW
                self.ents.append(box("PortHS_%s_%d" % (pid, s2 > 0), (x2, sill + h * 0.5, z2),
                                     (0.30 * sz, h + 0.7 * sz, HD) if abs(n[1]) > 0.5
                                     else (HD, h + 0.7 * sz, 0.30 * sz),
                                     C_WALL, parent=g, visible=False))
        self.portrooms[pid] = rid
        # ---- 筒(暗い前室)。床・天井・左右・奥の 5 枚 ----
        # ★MG(横の余裕)は 0 に近くないといけない。0.3 も空けると、口の縁と筒の側壁の間に
        #   ポケットができ、斜めから見たときにそこから【母屋の明るい壁】が覗く(実測)。
        T, MG = 0.3, 0.02
        hw = w * 0.5 + MG
        cx2, cz2 = pos[0] + n[0] * D * 0.5, pos[1] + n[1] * D * 0.5
        zax = abs(n[1]) > 0.5
        S3 = (lambda a, b, c: (a, b, c) if zax else (c, b, a))
        self.ents.append(box("PortT_%s_F" % pid, (cx2, sill - T * 0.5, cz2),
                             S3(hw * 2, T, D), C_DARK, parent=g, rough=0.98))
        self.ents.append(box("PortT_%s_C" % pid, (cx2, sill + h + T * 0.5, cz2),
                             S3(hw * 2, T, D), C_DARK, parent=g, rough=0.98))
        for s2 in (-1, 1):
            x2 = cx2 + al[0] * s2 * (hw + T * 0.5)
            z2 = cz2 + al[1] * s2 * (hw + T * 0.5)
            self.ents.append(box("PortT_%s_S%d" % (pid, s2 > 0), (x2, sill + h * 0.5, z2),
                                 S3(T, h, D), C_DARK, parent=g, rough=0.98))
        bx, bz = pos[0] + n[0] * (D + T * 0.5), pos[1] + n[1] * (D + T * 0.5)
        # ★奥の板だけ少し明るい。ここが【転送の瞬間に見えている唯一の面】なので、
        #   真っ黒にすると「暗黒 -> 明るい口」の落差になる。金属のシャッターに見える明度にする。
        self.ents.append(box("PortT_%s_B" % pid, (bx, sill + h * 0.5, bz),
                             S3(hw * 2 + T * 2, h, T), C_SHUT, parent=g, rough=0.55))
        # ★灯りは 2 つ。口の内側(ここが通路だと分かる)と、一番奥のごく弱い灯り。
        #   奥が【真っ暗】だと、入れ替わった瞬間に「暗黒 -> 明るい部屋」の落差が出て
        #   切り替わりが見えてしまう。奥をうっすら照らしておくと落差が小さくなる。
        self.ents.append(plight("PortL_%s" % pid, (pos[0] + n[0] * 0.30, sill + h * 0.80,
                                                   pos[1] + n[1] * 0.30),
                                (0.72, 0.80, 0.92), 2.3, 3.4 * sz + 0.8, g))
        self.ents.append(plight("PortLb_%s" % pid, (pos[0] + n[0] * (D - 0.85), sill + h * 0.78,
                                                    pos[1] + n[1] * (D - 0.85)),
                                (0.70, 0.78, 0.92), 1.7, 3.0 * sz + 0.6, g))
        self.ports.append(dict(id=pid, x=pos[0], z=pos[1], nx=n[0], nz=n[1], alx=al[0], alz=al[1],
                               hw=hw, P=D * 0.5, y0=floor_y(r), size=sz, room=rid,
                               free=not sp.get("wall"),
                               yaw=math.degrees(math.atan2(n[0], n[1]))))

    # ================================ v11: 継ぎ手の枠(gate) ================================
    # ★v11 の心臓。v10 の「暗い筒」は【行き先が分からない】(指摘: 最初の転送先が意味不明)ので捨てた。
    #
    #   枠は部屋の中に単体で立っている金属の門で、中に【膜】が張ってある。
    #   ★二つの枠が【自分の目から見て重なった】ときだけ、その二枚は繋がる。
    #     手前の枠の開口の中に、向こうの枠が見えていること。それが唯一の条件。
    #   繋がると膜の縫い目がほどけ、くぐると【向こうの枠の裏】から出てくる。
    #
    #   つまりプレイヤーは【カメラの絵で地図を編む】。どの枠に重ねるかで行き先が変わる。
    #   見えていない枠へは繋がらないので、行き先は必ず自分の目で確かめてから通ることになる。
    def gate(self, sp):
        gid = sp["id"]
        rid = sp["room"]
        r = self.rooms[rid]
        k = r["scale"]
        cx, cz = r["at"]
        sz = sp.get("size", 1.0)
        x = cx + sp["at"][0] * k
        z = cz + sp["at"][1] * k
        fy = floor_y(r) + sp.get("y", 0.0)
        f = sp.get("facing", "S")
        n = (float(WALLS[f]["sign"]) if WALLS[f]["axis"] == "x" else 0.0,
             float(WALLS[f]["sign"]) if WALLS[f]["axis"] == "z" else 0.0)
        al = (-n[1], n[0])
        yaw = math.degrees(math.atan2(n[0], n[1]))
        w, h = DOOR_W * sz, DOOR_H * sz
        g = group(self.ents, "Gate %s" % gid, self.g_seams)
        self.ents.append(model("Gate_%s" % gid, mdl("jframe"), (x, fy, z), yaw, g, (sz, sz, sz)))
        # 台座。枠が床から生えているように見せる + 転がってきた玉を止めない厚みにする
        self.ents.append(box("GateB_%s" % gid, (x, fy + 0.05, z),
                             (w + 0.9 * sz, 0.10, 0.7 * sz) if abs(n[1]) > 0.5
                             else (0.7 * sz, 0.10, w + 0.9 * sz),
                             C_DIV, parent=g, rough=0.5))
        # 枠の柱(当たり判定)。中央の開口だけが通れる
        for s2 in (-1, 1):
            self.ents.append(box("GateJ_%s_%d" % (gid, s2 > 0),
                                 (x + al[0] * s2 * (w * 0.5 + 0.16 * sz), fy + h * 0.5,
                                  z + al[1] * s2 * (w * 0.5 + 0.16 * sz)),
                                 (0.32 * sz, h + 0.34 * sz, 0.34 * sz) if abs(n[1]) > 0.5
                                 else (0.34 * sz, h + 0.34 * sz, 0.32 * sz),
                                 C_WALL, parent=g, visible=False))
        # ★膜。カスタムシェーダー(Membrane.hlsl)。繋がり具合を Lua が effectValue で送る
        m = model("GateM_%s" % gid, mdl("membrane"), (x, fy + 0.02, z), yaw, g, (sz, sz, sz))
        m["shader"] = "Membrane.hlsl"
        m["shaderAlphaBlend"] = True
        m["shaderEffectValue"] = 0.0
        m["shaderParams"] = [round((abs(hash(gid)) % 997) / 997.0, 3), 0.0, 0.35, 0.0]
        self.ents.append(m)
        # ★枠の光。対の色を gpair が上書きする。needs 付きの枠は Lua が【消灯】する
        self.ents.append(plight("GateL_%s" % gid, (x - n[0] * 0.5, fy + h * 0.86, z - n[1] * 0.5),
                                (0.62, 0.76, 0.95), 2.6, 4.6 * sz, g))
        # 総当たり検査(simulate)へ渡すための擬似的な「口」
        lx = x - cx - n[0] * 0.5
        lz = z - cz - n[1] * 0.5
        self.mouths[gid] = dict(room=rid, wall=None, off=0.0, size=sz, sill=fy, sillRel=0.0,
                                pos=(x, z), w=w, h=h, n=n, along=al, kind="door")
        self.gates.append(dict(id=gid, x=x, z=z, y0=fy, nx=n[0], nz=n[1], alx=al[0], alz=al[1],
                               hw=w * 0.5, hh=h, size=sz, room=rid))

    def gpair(self, sp):
        byid = {q["id"]: q for q in self.gates}
        for q in (sp["a"], sp["b"]):
            if q not in byid:
                raise SystemExit("%s: 枠の組 %s が無い" % (self.st["name"], q))
        col = sp.get("col", "cyan")
        rgb = PAIRCOL[col]
        hue = PAIRHUE[col]
        self.gpairs.append(dict(a=sp["a"], b=sp["b"], both=1 if sp.get("both", True) else 0,
                                needs=sp.get("needs") or "", col=col, rgb=rgb, hue=hue))
        # ★両方の枠を同じ色で光らせる。色が合っている枠どうしだけが繋がる、と目で分かる
        for q in (sp["a"], sp["b"]):
            g = byid[q]
            g["rgb"] = rgb
            g["hue"] = hue
            g["needs"] = sp.get("needs") or ""
        # ★立ち位置の印。手前の枠から見て「向こうの枠と重なる線」の上に置く
        if sp.get("mark", 0.0) > 0.0:
            A, B = byid[sp["a"]], byid[sp["b"]]
            dx, dz = A["x"] - B["x"], A["z"] - B["z"]
            L = math.hypot(dx, dz) or 1.0
            m = sp["mark"]
            mx, mz = A["x"] + dx / L * m, A["z"] + dz / L * m
            gg = group(self.ents, "Mark %s" % sp["a"], self.g_seams)
            yaw = math.degrees(math.atan2(-dx / L, -dz / L))
            self.ents.append(model("MarkL_%s" % sp["a"], mdl("lane"), (mx, floor_y(A_room(self, A)) + 0.02, mz),
                                   yaw, gg, (1.6, 1.0, m * 0.85)))
            self.ents.append(plight("MarkLi_%s" % sp["a"], (mx, 0.45, mz), rgb, 2.6, 3.4, gg))
            self.marks.append(dict(ent="MarkL_%s" % sp["a"], light="MarkLi_%s" % sp["a"],
                                   rgb=rgb, x=mx, z=mz))
        self.links[sp["a"]] = sp["b"]
        if sp.get("both", True):
            self.links[sp["b"]] = sp["a"]

    def plate(self, sp):
        pid = sp["id"]
        r = self.rooms[sp["room"]]
        k = r["scale"]
        x = r["at"][0] + sp["at"][0] * k
        z = r["at"][1] + sp["at"][1] * k
        fy = floor_y(r)
        g = group(self.ents, "Plate %s" % pid, self.g_seams)
        self.ents.append(model("Plate_%s" % pid, mdl("plate"), (x, fy, z), 0.0, g))
        self.ents.append(plight("PlateL_%s" % pid, (x, fy + 0.5, z), (1.0, 0.45, 0.2), 2.6, 4.6, g))
        self.plates.append(dict(id=pid, ent="Plate_%s" % pid, light="PlateL_%s" % pid,
                                x=x, z=z, y0=fy, r=sp.get("r", 1.05), room=sp["room"],
                                rgb=(1.0, 0.45, 0.2)))

    # ================================ v10: エイムズの部屋 ================================
    # ★これは「大きさが変わる」ではなく【本物の目の錯覚】。部屋そのものが嘘の形をしている。
    #
    #   作り方: 理想の直方体の部屋(幅 w・奥行 d・高さ h)の 8 隅を、覗き穴 V から伸ばした
    #   直線の上で s = 1/(1 + α·横位置) 倍だけ遠ざける/近づける。
    #   これは【同次座標では線形 = 射影変換】なので、
    #     ・面は面のまま(床も天井も壁も平面。当たり判定は傾けた板 1 枚ずつで厳密に置ける)
    #     ・V から見た絵は理想の直方体と【1 画素も違わない】
    #   の 2 つが同時に成り立つ。実物のエイムズの部屋と同じ原理。
    #
    #   結果: 左奥の隅は本当は 1.4 倍遠くて 1.4 倍大きいのに、同じ大きさに見える。
    #   そこへ【左右まったく同じロッカー(1.95m)】を置くと、左は小さく右は大きく見える。
    #   ★この game は「什器は絶対寸法 = 唯一の物差し」で組んである。
    #     その物差しが嘘をつく部屋なので、ここだけは今までの全部が通用しない。
    def ames(self, sp):
        aid = sp["id"]
        rid = sp["room"]
        r = self.rooms[rid]
        Wd, Dp, Ht = sp.get("w", 8.0), sp.get("d", 14.0), sp.get("h", 5.0)
        aa = sp.get("alpha", 0.075)
        ma = self.add_opening(rid, sp["wall"], sp.get("off", 0.0), "door", 0.0, aid)
        self.noleaf.add(aid)
        n = ma["n"]
        fy = floor_y(r)
        eye = sp.get("eye", EYE_H)
        vx, vz = ma["pos"][0], ma["pos"][1]
        yaw = math.degrees(math.atan2(n[0], n[1]))
        hw = Wd * 0.5

        # ---- (1) 射影で歪める。局所座標 x=横 / y=高さ(床が 0) / z=奥 ----
        #      覗き穴は (0, eye, 0)。横位置 lat だけで倍率が決まるので、
        #      【真ん中の線(lat=0)は動かない】= 戸口の高さも床の高さも保たれる。
        def pj(lat, y, t):
            s = 1.0 / (1.0 + aa * lat)
            return (lat * s, eye + (y - eye) * s, t * s)

        # ---- (2) 床を水平に戻す。★歪めた床は「戸口から奥へ伸びる線」を軸に傾いた平面。
        #      その軸まわりに転がして水平へ戻すと、母屋の床とぴったり繋がる(段差ゼロ)。
        #      覗き穴が 21cm 横へずれるだけで、絵はほぼそのまま(立体視の無い一人称では
        #      21cm の頭の位置なんて誰にも分からない)。★これをやらないと戸口の左右で
        #      床が 60cm 食い違い、壁の下に【虚空へ抜ける隙間】が空く。
        q = pj(-hw, 0.0, 0.0)
        phi = math.degrees(math.atan2(-q[1], q[0])) if abs(q[0]) > 1e-9 else 0.0
        phi = (phi + 90.0) % 180.0 - 90.0
        Mloc = m_mul(m_rz(phi), m_ry(yaw))

        def W3(lat, y, t):
            """理想の部屋の座標 -> 実際の世界座標"""
            pw = m_apply(Mloc, pj(lat, y, t))
            return (vx + pw[0], fy + pw[1], vz + pw[2])

        g = group(self.ents, "Ames %s" % aid, self.g_rooms)
        C, Lo = {}, {}
        for sx, lat in (("L", -hw), ("R", hw)):
            for sy, y in (("0", 0.0), ("1", Ht)):
                for sz, t in (("n", 0.0), ("f", Dp)):
                    C[sx + sy + sz] = W3(lat, y, t)
                    Lo[sx + sy + sz] = pj(lat, y, t)
        # ---- 見える面(Blender)。近い側の面は【母屋の壁が覆う】ので張らない ----
        spec = dict(ames=True, v=1, c={k: [round(x, 4) for x in v] for k, v in Lo.items()})
        mname = "am_%s" % key_of(spec)
        self.manifest[mname] = spec
        self.ents.append(model("AmesM_%s" % aid, mdl(mname), (vx, fy, vz), yaw, g))
        self.ents[-1]["transform"]["rotation"] = [0.0, yaw, phi]
        # ---- 当たり判定。面は全部【平面】なので傾けた板 1 枚ずつで厳密 ----
        up, dn = (0.0, 1.0, 0.0), (0.0, -1.0, 0.0)
        lft = m_apply(Mloc, (-1.0, 0.0, 0.0))
        rgt = m_apply(Mloc, (1.0, 0.0, 0.0))
        for nm, quad, out in (
                ("F", ("L0n", "R0n", "R0f", "L0f"), dn),
                ("C", ("L1n", "R1n", "R1f", "L1f"), up),
                ("SL", ("L0n", "L1n", "L1f", "L0f"), lft),
                ("SR", ("R0n", "R1n", "R1f", "R0f"), rgt),
                ("B", ("L0f", "R0f", "R1f", "L1f"), (n[0], 0.0, n[1]))):
            self.ents.append(plate_from_quad("Ames_%s_%s" % (aid, nm), [C[q] for q in quad],
                                             0.5, C_WALL, g, outward=out, pad=0.8))
        # ---- 照明。★天井の【実際の】高さに沿って置く。奥ほど小さくするのは
        #      強制遠近法と同じで、「奥は遠い」という嘘を灯りの側からも支えるため ----
        for i, (lat, t) in enumerate(sp.get("lights") or
                                     [(-hw * 0.55, Dp * 0.30), (hw * 0.55, Dp * 0.30),
                                      (-hw * 0.55, Dp * 0.76), (hw * 0.55, Dp * 0.76)]):
            qq = W3(lat, Ht, t)
            s = 1.0 / (1.0 + aa * lat)
            self.ents.append(model("AmesT_%s_%d" % (aid, i), mdl("troffer"),
                                   (qq[0], qq[1] - 0.03 * s, qq[2]), yaw, g, (s, s, s)))
            self.ents.append(plight("AmesL_%s_%d" % (aid, i), (qq[0], qq[1] - 0.5 * s, qq[2]),
                                    (0.98, 0.96, 0.90), 4.6, 15.0 * s, g))
        # ---- 什器。★理想座標で置くので【絵の上では左右対称】。実物は左が 1.43 倍遠い。
        #      同じロッカーが、片方は目の高さ・片方は腰までしか無いように見える ----
        for i, (kind, lat, t, yw) in enumerate(sp.get("props", ())):
            P = PROPS[kind]
            qq = W3(lat, 0.0, t)
            self.ents.append(model("Ames_%s_%s_%d" % (aid, kind, i), P["path"],
                                   (qq[0], fy, qq[2]), yaw + yw, g))
            if P["block"]:
                # ★母屋の外(別棟)に居るので、部屋の什器とは別の帳簿に載せる
                self.fixtures.setdefault("ames:" + aid, []).append((qq[0], qq[2], P["r"], P["top"]))
        self.amesmap[aid] = W3
        self.amesboxes.append(dict(id=aid, room=rid, pts=list(C.values()),
                                   near=[C[k] for k in ("L0n", "R0n", "L1n", "R1n")],
                                   phi=phi, floorErr=max(abs(C[k][1] - fy) for k in
                                                         ("L0n", "R0n", "L0f", "R0f"))))

    # ================================ v10: 部屋ごと傾ける ================================
    # ★平衡感覚を壊す装置。部屋の【全部】(床・壁・天井・什器・照明・当たり判定)を
    #   歩く向きの軸まわりに転がす。重力はワールドの真下のままなので、
    #   「部屋の垂直」と「本当の垂直」が食い違う = 錯覚小屋(Mystery Spot)と同じ状況になる。
    #
    # ★継ぎ手の筒は【転がさない】(g_seams にあるので此処の範囲外)。
    #   建物が傾いていて継ぎ手だけが水平、という絵になる。母屋の開口は大きめに開けて
    #   水平な襟(collar)で塞いであるので、転がっても角が抜けない。
    def tilt_slice(self, r, i0, i1):
        deg = float(r["tilt"])
        ax = r.get("tiltAxis", "z")
        k = r["scale"]
        px, py, pz = r.get("tiltAt", (0.0, 0.0, 0.0))
        pv = (r["at"][0] + px * k, floor_y(r) + py, r["at"][1] + pz * k)
        M = m_rx(deg) if ax == "x" else m_rz(deg)
        for e in self.ents[i0:i1]:
            if not any(q in e for q in ("meshRenderer", "primitive", "pointLight", "boxCollider",
                                        "particleEmitter")):
                continue                      # 入れ物(グループの目印)は動かさない
            t = e["transform"]
            p = t["position"]
            q = m_apply(M, (p[0] - pv[0], p[1] - pv[1], p[2] - pv[2]))
            t["position"] = [pv[0] + q[0], pv[1] + q[1], pv[2] + q[2]]
            t["rotation"] = list(euler_of_m(m_mul(m_of_euler(t["rotation"]), M)))

    # ================================ v10: 見張り / 忍び寄り / 傾ける区画 ============
    def extras(self):
        st = self.st
        g = group(self.ents, "[v10]")
        # ---- 見張り(watch)。★視界に入っている間は 1mm も動かない ----
        #   動く瞬間を絶対に見せないので、「動いた」ではなく【さっきと違う】としか思えない。
        #   変化盲(change blindness)は、変化そのものを隠すのが一番強い。
        for w in st.get("watchers", ()):
            r = self.rooms[w["room"]]
            k = r["scale"]
            x = r["at"][0] + w["at"][0] * k
            z = r["at"][1] + w["at"][1] * k
            sc = w.get("h", 1.85)
            self.ents.append(model(w["id"], mdl(w.get("model", "figure")),
                                   (x, floor_y(r), z), w.get("yaw", 0.0), g, (sc, sc, sc)))
            # ★押しのけられる。視線をふさぐ物なのに動かせないと理不尽になる
            self.ents[-1]["boxCollider"] = {"halfExtents": [0.30, sc * 0.5, 0.22],
                                            "offset": [0.0, sc * 0.5, 0.0]}
            self.ents[-1]["rigidBody"] = {"angularDamping": 0.9, "continuousCollision": False,
                                          "friction": 0.7, "linearDamping": 0.9, "mass": 34.0,
                                          "motionType": 2, "restitution": 0.02, "useGravity": True}
            self.watchers.append(dict(ent=w["id"], x=x, z=z, y=floor_y(r), step=w.get("step", 2.6),
                                      near=w.get("near", 2.2), rng=w.get("range", 34.0),
                                      wait=w.get("wait", 0.5), turn=1 if w.get("face", True) else 0))
        # ---- 忍び寄り(creep)。★気づかない速さで動き続ける物 ----
        for c in st.get("creeps", ()):
            self.creeps.append(dict(id=c["id"], ents=list(c["ents"]), dx=c.get("dx", 0.0),
                                    dy=c.get("dy", 0.0), dz=c.get("dz", 0.0),
                                    axis=c.get("axis", "z"), a=c["a"], b=c["b"],
                                    x0=c["zone"][0], x1=c["zone"][1], z0=c["zone"][2], z1=c["zone"][3]))
        for q in st.get("rolls", ()):
            self.rolls.append(dict(axis=q.get("axis", "z"), a=q["a"], b=q["b"],
                                   d0=q["deg"][0], d1=q["deg"][1],
                                   x0=q["zone"][0], x1=q["zone"][1], z0=q["zone"][2], z1=q["zone"][3]))
        for q in st.get("fovramps", ()):
            self.fovramps.append(dict(axis=q.get("axis", "z"), a=q["a"], b=q["b"],
                                      f0=q["f0"], f1=q["f1"], x0=q["zone"][0], x1=q["zone"][1],
                                      z0=q["zone"][2], z1=q["zone"][3]))

    def link(self, sp):
        """継ぎ手 from の奥を越えたら to の奥へ出す。times>0 なら最初の times 回だけ。
        ★同じ戸が、通った回数で行き先を変える = 「同じ廊下を三度歩かされる」が作れる。"""
        a = [p for p in self.ports if p["id"] == sp["from"]]
        b = [p for p in self.ports if p["id"] == sp["to"]]
        if not a or not b:
            raise SystemExit("%s: link の端 %s -> %s が無い" % (self.st["name"], sp["from"], sp["to"]))
        a, b = a[0], b[0]
        # 出る向き: a へ入る向き(na)が、b から出る向き(-nb)になるように振る
        dy = math.degrees(math.atan2(-b["nx"], -b["nz"])) - math.degrees(math.atan2(a["nx"], a["nz"]))
        dy = (dy + 180.0) % 360.0 - 180.0
        c, s = math.cos(math.radians(dy)), math.sin(math.radians(dy))
        rlx = a["alx"] * c + a["alz"] * s          # 横方向の基底も同じ角度で回す
        rlz = a["alz"] * c - a["alx"] * s
        self.linkrows.append(dict(frm=sp["from"], to=sp["to"], times=sp.get("times", 0),
                                  dyaw=dy, rlx=rlx, rlz=rlz))

    # ---- 壁 ----
    def wall_model(self, rid, wall):
        fr = wall_frame(self.rooms[rid], wall)
        ops = self.openings.get((rid, wall), [])
        r = self.rooms[rid]
        if not ops and not SHAPES[r["shape"]].get("mf"):
            return mdl("wall%s" % fr["tag"])
        al, rg = fr["along"], fr["right"]
        kk = al[0] * rg[0] + al[1] * rg[1]
        k = fr["k"]
        fy = floor_y(r, wall)
        loc = sorted([[round(o["off"] * kk / k, 3), round(o["w"] / k, 3), round((o["y0"] - fy) / k, 3),
                       round((o["y0"] - fy + o["h"]) / k, 3)] for o in ops])
        spec = dict(L=round(fr["Lu"], 3), H=round(fr["Hu"], 3), ops=loc)
        name = "wm_%s_%s" % (fr["tag"] or "12", key_of(spec))
        self.manifest[name] = spec
        return mdl(name)

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
        # ★溝は (axis, 中心) か (axis, 中心, 幅)。幅を省くと PIT_W(4.6m = 跳べる溝)。
        #   v10 の受入ホールは【跳べない 14m の谷】を使うので幅を渡せるようにした。
        pits = [(p[0], p[1] * k, (p[2] if len(p) > 2 else PIT_W)) for p in lay.get("pits", ())]
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
            ents.append(model("%s_FloorM" % rid, mdl(nm), (cx, fy + rise * 0.5 + 0.005, cz), 0.0, g, sc3))
            ents[-1]["transform"]["rotation"] = [ang, 0.0, 0.0]
            ents.append(box("%s_Ceil" % rid, (cx, fy + rise * 0.5 + ch + 0.15 * k, cz), (spanx, 0.3 * k, ln), C_CEIL,
                            rot=(ang, 0, 0), parent=g))
            cs = dict(ceil=True, sx=round(spanx / k, 3), sz=round(ln / k, 3))
            nm = "cm_%s" % key_of(cs); self.manifest[nm] = cs
            ents.append(model("%s_CeilM" % rid, mdl(nm), (cx, fy + rise * 0.5 + ch - 0.005, cz), 0.0, g, sc3))
            ents[-1]["transform"]["rotation"] = [ang, 0.0, 0.0]
        elif r.get("tiltFloor"):
            # ★v11: 視線で傾く床。床は【1 枚の動く板(KINEMATIC)】。
            #   部屋より 5m 大きく作って端を壁の中へ埋める = 傾いても縁が見えない。
            #   さらに壁の下へ「腰板」を垂らして、下がった側にできる隙間を塞ぐ。
            tf = r["tiltFloor"]
            ov = tf.get("over", 5.0)
            ents.append(box("%s_Floor" % rid, (cx, fy - 0.25, cz),
                            (spanx + ov, 0.5, spanz + ov), C_FLOOR, rough=0.95, parent=g,
                            kinematic=True))
            fs = dict(floor=True, sx=round((spanx + ov) / k, 3), sz=round((spanz + ov) / k, 3))
            if r.get("floorMat"):
                fs["mat"] = r["floorMat"]
            nm = "fm_%s" % key_of(fs); self.manifest[nm] = fs
            ents.append(model("%s_FloorM" % rid, mdl(nm), (cx, fy + 0.005, cz), 0.0, g, sc3))
            for w2 in ("N", "S", "E", "W"):
                fr2 = wall_frame(r, w2)
                nn, T2 = fr2["n"], WALLT * k
                ents.append(box("%s_Skirt_%s" % (rid, w2),
                                (fr2["face"][0] + nn[0] * T2 * 0.5, fy - 1.6,
                                 fr2["face"][1] + nn[1] * T2 * 0.5),
                                (fr2["L"] + ov, 3.2, T2) if WALLS[w2]["axis"] == "z"
                                else (T2, 3.2, fr2["L"] + ov),
                                C_WALL, parent=g))   # ★当たり判定あり: 床が下がった側で
                                                     #   壁の下から物が逃げるのを止める
            self._tiltprops = []
            tw = [("%s_Floor" % rid, cx, fy - 0.25, cz), ("%s_FloorM" % rid, cx, fy + 0.005, cz)]
            for i2, (bx2, bz2, bw2, bd2, bh2) in enumerate(tf.get("walls", ())):
                nm2 = "%s_TWall_%d" % (rid, i2)
                ents.append(box(nm2, (cx + bx2 * k, fy + bh2 * 0.5, cz + bz2 * k),
                                (bw2, bh2, bd2), C_DIV, parent=g, rough=0.6, kinematic=True))
                tw.append((nm2, cx + bx2 * k, fy + bh2 * 0.5, cz + bz2 * k))
            self.tilts.append(dict(room=rid, x=cx, y=fy, z=cz, deg=tf.get("deg", 6.0),
                                   ents=tw, extra=list(tf.get("with", ())), _late=True))
        elif not pits:
            ents.append(box("%s_Floor" % rid, (cx, fy - 0.15, cz), (spanx, 0.3, spanz), C_FLOOR, rough=0.95, parent=g))
            if S.get("mf"):
                fs = dict(floor=True, sx=round(spanx / k, 3), sz=round(spanz / k, 3))
                if r.get("floorMat"):
                    fs["mat"] = r["floorMat"]
                nm = "fm_%s" % key_of(fs); self.manifest[nm] = fs
                ents.append(model("%s_FloorM" % rid, mdl(nm), (cx, fy + 0.005, cz), 0.0, g, sc3))
            else:
                ents.append(model("%s_FloorM" % rid, S["floor"], (cx, fy + 0.005, cz), 0.0, g, sc3))
        else:
            axis, c, PW = pits[0]
            c0, c1 = c - PW * 0.5, c + PW * 0.5
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
                if r.get("floorMat"):
                    fs["mat"] = r["floorMat"]
                nm = "fm_%s" % key_of(fs)
                self.manifest[nm] = fs
                ents.append(model("%s_FloorM%d" % (rid, i), mdl(nm), (pos[0], 0.005, pos[2]), 0.0, g, sc3))
            W = PW
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
                ents.append(model("%s_CeilM" % rid, mdl(nm), (cx, fy + ch - 0.005, cz), 0.0, g, sc3))
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
                if o["kind"] == "door" and o["id"] not in self.noleaf:
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
                    ents.append(model("%s_Leaf_%s" % (rid, o["id"]), mdl("doorleaf"), lp,
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

        # ★部屋ごとに明るさを変えられる(保管庫だけ暗くする等)。既定は面ぜんたいの値
        lightcol = r.get("lightcol", st.get("lightcol", (0.98, 0.96, 0.88)))
        intensity = r.get("intensity", st.get("intensity", 9.0))
        for i, (ox, oz) in enumerate(S["lights"]):
            ly = fy + (rise * (0.5 + oz * k / spanz) if rise > 0 else 0.0)
            ents.append(model("%s_Troffer_%d" % (rid, i + 1), mdl("troffer"), (cx + ox * k, ly + ch - 0.01 * k, cz + oz * k), 0.0, g, sc3))
            # ★エンジンの減衰は逆二乗ではなく range で窓掛けされる(実測: k^2 だと白飛び)。
            #   range を k 倍にすると同じ見え方になる。強さはそのまま
            ents.append(plight("%s_Light_%d" % (rid, i + 1), (cx + ox * k, ly + ch - 0.45 * k, cz + oz * k),
                               lightcol, intensity * min(1.0, k) ** 0.8, S["lrange"] * k, g))

        # 隙間(絶対 1.0m)。壁は天井まで
        for (axis, c) in lay.get("eaves", ()):
            cw = c * k
            along_x = (axis == "z")
            span = spanx if along_x else spanz
            # ★eave.gltf は長さ 4.4m。ceil で並べると両端が壁を 0.45m 突き抜けていた。
            #   間隔を span/nseg に詰めて、必ず壁の内側で終わらせる。
            nseg = int(math.ceil(span / 4.4))
            step = span / nseg
            for i in range(nseg):
                u = (i - (nseg - 1) * 0.5) * step
                lx, lz = (u, cw) if along_x else (cw, u)
                ents.append(model("%s_Eave_%d" % (rid, i), mdl("eave"), (cx + lx, fy, cz + lz), 0.0 if along_x else 90.0, g))
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
            nm2 = "%s_%s_%d" % (rid, kind, i)
            ents.append(model(nm2, P["path"], (cx + lx * k, fy + y, cz + lz * k), yaw, g, sc))
            # ★当たり判定。柱だけは天井まで伸ばすので高さも scale される
            prop_body(ents[-1], P, sc[1] if kind == "column" else 1.0)
            if P.get("phys") == "dyn":
                # ★physics:setPosition は【コライダーの中心】を指す。原点(足元)を渡すと
                #   その差ぶん地面へ埋まる。中心までの高さを一緒に覚えておく
                sh = P["col"]
                off = sh[1] if sh[0] == "sphere" else sh[2] * 0.5
                self.dynprops.append((nm2, off))
            elif r.get("tiltFloor") and P.get("phys") == "fix":
                # ★傾く部屋の什器は【床にくっついて】一緒に上下する。
                #   静止体(motionType 0)のままだと transform を書いても当たり判定が動かないので
                #   KINEMATIC(1)へ。これをやらないとロッカーだけ空中に取り残される。
                ents[-1]["rigidBody"]["motionType"] = 1
                self._tiltprops.append((nm2, cx + lx * k, fy + y, cz + lz * k))
            if P["block"]:
                top = P["top"] if P["top"] < 90.0 else ch
                self.fixtures.setdefault(rid, []).append((cx + lx * k, cz + lz * k, P["r"], top))

        # 柵(絶対 1.7m。長さだけ部屋に合わせる)
        for i, (axis, c) in enumerate(lay.get("bars", ())):
            cw = c * k
            along_x = (axis == "z")
            span = spanx if along_x else spanz
            lx, lz = (0.0, cw) if along_x else (cw, 0.0)
            ents.append(model("%s_Bar_%d" % (rid, i), mdl(lay.get("barMdl", "barrier")), (cx + lx, fy, cz + lz), 0.0 if along_x else 90.0, g,
                              (span / 12.6, BAR_H / 1.35, 1.0)))
            sx = span if along_x else 0.14
            sz = 0.14 if along_x else span
            # ★当たり判定は【見えない板】。v9 までは C_DIV の箱を見せていたが、
            #   40m のホールに置くと【向こうが一切見えない壁】になり、
            #   「見えているのに行けない」という設計そのものが成立しない。
            #   見た目は手すりモデル(barrier)だけに任せる。
            ents.append(box("%s_BarCol_%d" % (rid, i), (cx + lx, fy + BAR_H * 0.5 - 0.03, cz + lz), (sx - 0.03, BAR_H - 0.06, sz - 0.03), C_DIV, rough=0.6, parent=g, visible=False))
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
        # ---- v10: 別棟(エイムズ) -> 継ぎ手 の順。口は壁に穴を開けるので【部屋を建てる前】に。
        #      継ぎ手は別棟の中にも立てられる(at=("E1", 横, 奥))ので、別棟が先に要る ----
        for sp in st.get("ames", ()):
            self.ames(sp)
        for sp in st.get("ports", ()):
            self.port(sp)
        for sp in _flat(st.get("links", ())):     # JOIN() は 2 本まとめて返すので均す
            self.link(sp)
        # ---- v11: 継ぎ手の枠 / 重量板 / 重ねると繋がる組 ----
        for sp in st.get("gates", ()):
            self.gate(sp)
        for sp in st.get("plates", ()):
            self.plate(sp)
        for sp in _flat(st.get("pairs", ())):
            self.gpair(sp)
        # ★総当たり検査(simulate)は口と口の対応表(links)しか見ない。
        #   回数で行き先が変わる結線(times>0)は【最後に落ち着く方】だけを教える
        #   (輪は遠回りであって、行けない場所を作らないから)。
        for lk in self.linkrows:
            if lk["times"] == 0:
                self.links[lk["frm"]] = lk["to"]
        for r in st["rooms"]:
            i0 = len(self.ents)
            self._tiltprops = []
            self.build_room(r)
            # ★什器は床の後に作られるので、部屋を建て終えてから傾ける一覧へ足す
            if self._tiltprops and self.tilts:
                self.tilts[-1]["ents"].extend(self._tiltprops)
            if abs(r.get("tilt", 0.0)) > 1e-6:
                self.tilt_slice(r, i0, len(self.ents))
        self.extras()
        # ---- 黙って転送する面(warp)。同じ見た目の廊下の中に置くので見えない ----
        self.warps = []
        for wp in st.get("warps", ()):
            ta = [t for t in self.tunnels if t["id"] == wp["fromTunnel"]][0]
            tb = [t for t in self.tunnels if t["id"] == wp["toTunnel"]][0]
            mid = lambda t: (t["ax"] + t["nx"] * GAP * 0.5, t["az"] + t["nz"] * GAP * 0.5)
            ma, mb = mid(ta), mid(tb)
            self.warps.append(dict(id=wp["id"], px=ma[0], pz=ma[1], nx=ta["nx"], nz=ta["nz"],
                                   dx=mb[0] - ma[0], dy=tb["y0"] - ta["y0"], dz=mb[1] - ma[1],
                                   loops=wp.get("loops", 3), hw=max(ta["wa"], ta["wb"]) * 0.5 + 0.3,
                                   scales=list(wp.get("scales", ()))))
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
            # ★開く口の扉板は【最初は隠しておく】。栓(mode="appear")で塗り潰された開口の
            #   横に開いたままの扉板が立っていると、「壁なのに扉がある」という妙な絵になる。
            #   tag "B" は morph で rw[2],rw[3],rw[4] へ出す = 板が現れる。
            for mid in list(mo.get("unseal", ())):
                mm = self.mouths.get(mid)
                if not mm:
                    continue
                nm = "%s_Leaf_%s" % (mm["room"], mid)
                for e in self.ents:
                    if e["name"] == nm:
                        q = e["transform"]["position"]
                        rows.append((nm, q[0], q[1], q[2], "B"))
                        q[1] = HIDE_Y
                        break
            # ★塞いだ口の扉板も一緒に消す。板は開口とは別のエンティティなので、栓だけ出すと
            #   「塗り潰された開口の横に、開いたままの扉板が立っている」という妙な絵になる。
            #   rows の tag "A" は【morph で HIDE_Y へ送る】ので、座標は使われない。
            for mid in list(mo.get("seal", ())):
                mm = self.mouths.get(mid)
                if mm:
                    rows.append(("%s_Leaf_%s" % (mm["room"], mid), 0.0, 0.0, 0.0, "A"))
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
        seen_plugs = set()
        for pg in list(st.get("plugs", ())) + list(st.get("_autoplugs", ())):
            # ★同じ口に栓を 2 つ作らせない。morph の seal/unseal は栓を【自動で足す】ので、
            #   同じ口を plugs にも書くと Plug_xxx が 2 体できる。名前引きは 1 体しか
            #   掴めないので、もう 1 体が口を塞いだまま残る = 扉が永久に開かない。
            if pg["mouth"] in seen_plugs:
                raise SystemExit("%s: 口 %s の栓が二重に定義されている(morph の seal/unseal と plugs)"
                                 % (st["name"], pg["mouth"]))
            seen_plugs.add(pg["mouth"])
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

        # ---- 大きさの門(sizegates)。床に立った枠。くぐると大きさが変わる ----
        self.sizegates = []
        for sg in st.get("sizegates", ()):
            r = self.rooms[sg["room"]]
            k = r["scale"]
            cx, cz = r["at"]
            gx, gz = cx + sg["at"][0] * k, cz + sg["at"][1] * k
            yaw = WALLS[sg["facing"]]["yaw"]
            n = (math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))
            m = sg["size"]
            self.ents.append(model("SGate_%s" % sg["id"], mdl("seam"), (gx, floor_y(r), gz),
                                   yaw, self.g_seams, (m, m, m)))
            # 枠が白い部屋で溶けないように、下から弱く照らす
            self.ents.append(plight("SGateL_%s" % sg["id"], (gx, floor_y(r) + 0.35 * m, gz),
                                    (0.72, 0.86, 1.00), 2.6, 4.0 * m, self.g_seams))
            self.sizegates.append(dict(id=sg["id"], x=gx, z=gz, nx=n[0], nz=n[1],
                                       hw=0.5 * m + 0.2, sf=sg["sf"], sb=sg["sb"]))

        # ---- 角度固定の門(anchors)。★近づいても画面上の大きさが変わらない物 ----
        #   Lua が毎フレーム scale = k x (カメラからの距離) / d0 に書き換える。
        #   当たり判定は持たせない(絵だけ)。触れないので伸縮しても破綻しない。
        self.anchors = []
        for i, (ax, az, ayaw, k, d0) in enumerate(st.get("anchors", ())):
            nm = "Anchor_%d" % i
            ents.append(model(nm, mdl("goal"), (ax, 0.0, az), ayaw, g_sys))
            ents.append(plight("AnchorL_%d" % i, (ax, 0.55, az),
                               (0.25, 1.0, 0.62), 4.0, 9.0, g_sys))
            self.anchors.append(dict(ent=nm, x=ax, z=az, k=k, d0=d0))

        # ---- 運べる物(carries)。木箱 + それに付いて回る動かせる当たり判定 ----
        #   ★什器(props)は当たり判定を持たない飾りだが、これは【乗れる】必要があるので
        #     kinematic な箱を重ねる(motionType 0 の静止体は実行時に動かせない)。
        self.carries = []
        for i, (cx0, cz0, cyaw) in enumerate(st.get("carries", ())):
            nm, cl = "Carry_%d" % i, "CarryC_%d" % i
            ents.append(model(nm, mdl("crate"), (cx0, 0.0, cz0), cyaw, g_sys))
            ents.append(box(cl, (cx0, CARRY_TOP * 0.5, cz0), (0.80, CARRY_TOP, 0.80), C_WALL,
                            parent=g_sys, kinematic=True, visible=False))
            self.carries.append(dict(ent=nm, col=cl, x=cx0, z=cz0, yaw=cyaw, h=CARRY_TOP))

        # 出口(絶対寸法)。縮尺 2 の部屋では小さく、0.5 では巨大に見える = 唯一の物差し
        gx, gz = st["goal"]
        gyaw = st.get("goalYaw", 0.0)
        gy = floor_y(self.rooms[st["goalRoom"]])     # ★出口も部屋の標高に置く(9m 上の部屋なら 9m)
        ents.append(model("GoalM", mdl("goal"), (gx, gy, gz), gyaw, g_sys))
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
        # ★見えるのに行けない門(decoy)。当たり判定も判定用の印も持たない【ただの絵】。
        #   「出口はもう見えている。届かないのは自分の大きさのせいだ」を無言で言うための装置で、
        #   v9 の 1〜3 面はこれを軸に組んである(柵の向こう / 隙間の向こうに置く)。
        for i, (dx, dz, dyaw) in enumerate(st.get("decoys", ())):
            ents.append(model("Decoy_%d" % i, mdl("goal"), (dx, 0.0, dz), dyaw, g_sys))
            ux, uz = -math.sin(math.radians(dyaw)), -math.cos(math.radians(dyaw))
            for sgn, nm in ((-1.0, "F"), (1.0, "B")):
                ents.append(plight("DecoyLight%d%s" % (i, nm),
                                   (dx + ux * 1.5 * sgn, 0.55, dz + uz * 1.5 * sgn),
                                   (0.25, 1.0, 0.62), 5.0, 9.0, g_sys))

        # ★v11: くぐった瞬間に【カメラの前を通り過ぎる膜】。床下に隠してある。
        #   実行時に spawn した entity は描画されないので、必ずシーンに置くこと。
        if st.get("gates"):
            v = model("WarpVeil", mdl("membrane"), (0.0, HIDE_Y, 0.0), 0.0, g_sys)
            v["shader"] = "Membrane.hlsl"
            v["shaderAlphaBlend"] = True
            v["shaderEffectValue"] = 0.0
            v["shaderParams"] = [0.61, 0.9, 2.2, 0.0]
            ents.append(v)
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
                "enabled": True, "tonemapper": 1, "exposureOn": True,
                # ★露出。灯りの数が多い面(v10 の 40m ホールは 25 灯)は 1.0 だと
                #   コンクリートの床が【真っ白に飛ぶ】。面ごとに落とせるようにした。
                "exposure": st.get("exposure", 1.0),
                "bloomOn": True, "bloom": 0.42, "bloomThreshold": 1.15,
                "bloomKnee": 0.5, "bloomRadius": 0.72,
                "vignetteOn": True, "vignette": 0.26, "caOn": True, "ca": 0.15,
                "grainOn": True, "grain": 0.045, "fxaaOn": True, "debandOn": True,
            },
        }


# ★v11: 什器に【当たり判定】と【物理】を持たせた。
#   phys="fix" … 動かない当たり判定(棚・ロッカー・ベンチ・柱)。押しても微動だにしない
#   phys="dyn" … 動く剛体。押せば転がる/滑る。mass は現実の重さに近い値
#   col = ("box", 幅, 高さ, 奥行) / ("sphere", 半径)。原点は床なので中心は高さの半分
#   ★v10 までは什器は【全部すり抜ける飾り】だった。指摘「オブジェクト個々に当たり判定を」
PROPS = {
    "rack":    dict(path=mdl("rack"),    y=0.0, r=1.45, top=2.40, block=True,
                    phys="fix", col=("box", 2.60, 2.40, 0.90)),
    "drum":    dict(path=mdl("drum"),    y=0.0, r=0.34, top=0.88, block=True,
                    phys="dyn", mass=26.0, col=("box", 0.60, 0.88, 0.60),
                    fric=0.42, rest=0.06, ldamp=0.22, adamp=0.55),
    # ★転がり抵抗。0.10 だと床を水平に戻しても止まらず、狙った所へ置けない(実測)。
    #   0.62 にすると「傾けている間だけ転がり、離すと数十cmで止まる」= 狙える
    "ball":    dict(path=mdl("ball"),    y=0.0, r=0.40, top=0.72, block=False,
                    phys="dyn", mass=48.0, col=("sphere", 0.36),
                    fric=0.45, rest=0.10, ldamp=0.62, adamp=0.55),
    "sign":    dict(path=mdl("sign"),    y=3.20, r=0.9, top=0.0, block=False),
    "bench":   dict(path=mdl("bench"),   y=0.0, r=0.90, top=0.95, block=True,
                    phys="fix", col=("box", 1.80, 0.95, 0.62)),
    "column":  dict(path=mdl("column"),  y=0.0, r=0.45, top=99.0, block=True,
                    phys="fix", col=("box", 0.92, 4.00, 0.92)),
    "locker":  dict(path=mdl("locker"),  y=0.0, r=0.85, top=1.95, block=True,
                    phys="fix", col=("box", 1.60, 1.95, 0.55)),
    "crate":   dict(path=mdl("crate"),   y=0.0, r=0.55, top=0.75, block=True,
                    phys="dyn", mass=17.0, col=("box", 0.78, 0.75, 0.78),
                    fric=0.55, rest=0.04, ldamp=0.25, adamp=0.65),
    "railing": dict(path=mdl("railing"), y=0.0, r=1.55, top=1.10, block=True),
    "vent":    dict(path=mdl("vent"),    y=None, r=0.4, top=0.0, block=False),
    "pipes":   dict(path=mdl("pipes"),   y=None, r=3.0, top=0.0, block=False),
}


def A_room(W, g):
    return W.rooms[g["room"]]


def prop_body(e, P, k=1.0):
    """★什器のエンティティに当たり判定と剛体を足す。
    ・fix … 動かない壁と同じ扱い(motionType 0)。押しても動かない
    ・dyn … 転がる/滑る(motionType 2)。★ガクガクさせないための値:
             restitution を 0.2 以下に(跳ね返りが小さいほど落ち着く)、
             linearDamping/angularDamping を入れて微振動を殺す、
             mass は現実の値(ドラム缶 26kg / 木箱 17kg / 鋼球 48kg)。
             軽すぎると人にぶつかった瞬間に吹き飛んで嘘に見える。
    ★CharacterVirtual は接触した動的剛体を押す(Jolt の既定 mMaxStrength)。
      だから「歩いてぶつかると転がる」が Lua を 1 行も書かずに成立する。"""
    ph = P.get("phys")
    if not ph:
        return e
    shape = P["col"]
    if shape[0] == "sphere":
        e["sphereCollider"] = {"radius": shape[1] * k, "offset": [0.0, shape[1] * k, 0.0]}
    else:
        _, w, h, d = shape
        e["boxCollider"] = {"halfExtents": [w * 0.5 * k, h * 0.5 * k, d * 0.5 * k],
                            "offset": [0.0, h * 0.5 * k, 0.0]}
    dyn = (ph == "dyn")
    e["rigidBody"] = {"angularDamping": P.get("adamp", 0.4) if dyn else 0.01,
                      "continuousCollision": dyn,
                      "friction": P.get("fric", 0.5),
                      "linearDamping": P.get("ldamp", 0.2) if dyn else 0.02,
                      "mass": P.get("mass", 1.0),
                      "motionType": 2 if dyn else 0,
                      "restitution": P.get("rest", 0.05),
                      "useGravity": dyn}
    return e


# ---------------------------------------------------------------- 総当たり(状態 = 部屋, 区画。大きさは部屋が決める)
def _dividers(r):
    k = r["scale"]
    lay = r.get("layout", {})
    out = []
    for (axis, c) in lay.get("bars", ()):
        out.append((axis, c * k, ("big", 0)))
    for (axis, c) in lay.get("eaves", ()):
        out.append((axis, c * k, ("small", 0)))
    for pp in lay.get("pits", ()):
        out.append((pp[0], pp[1] * k, ("pit", pp[2] if len(pp) > 2 else PIT_W)))
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


def _scales_of(st, room, sc):
    """その部屋で【取りうる体の大きさ】。既定は今の大きさそのもの。
    ★bodyScales が効くのは【大きさの門(sizegate)がその部屋にある】時だけ。
      面全体に効かせると「どの部屋でも x2 になれる」と甘く見て、
      解けないはずの関門を通れることにしてしまう(実際 demo2 で踏んだ)。"""
    if room in st.get("_sgrooms", ()):
        return st.get("bodyScales") or [sc]
    return [sc]


def _pass_gate(gate, s, aid=0.0):
    """aid = 手元にある踏み台の天端(運べる木箱)。0 なら素手。
    ★踏み台が効くのは【その上に登れる時だけ】。climb_h(0.5)=0.575 < 0.70 なので
      小さいと木箱には登れず、道具として成立しない。"""
    kind, arg = gate
    if kind == "big":
        if climb_h(s) >= BAR_H - 1e-6:
            return True
        return (aid > 0.0 and climb_h(s) >= aid - 1e-6
                and aid + climb_h(s) >= BAR_H - 1e-6)
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
                           size=m["size"],
                           pos=(m["pos"][0] - m["n"][0] * 1.2, m["pos"][1] - m["n"][1] * 1.2))
    gr = rooms[st["goalRoom"]]
    gx, gz = st["goal"]
    goal_zone = _zone_of(gr, gx - gr["at"][0], gz - gr["at"][1])
    sr = rooms[st["start"]]
    s0 = st.get("startScale", sr["scale"])
    # ★運べる木箱がどの部屋・区画に置いてあるか。そこへ一度でも行けば以後は
    #   踏み台として使える、と見なす(置き直しは自由なので十分に安全側)。
    st["_sgrooms"] = {g["room"] for g in st.get("sizegates", ())}
    boxes = set()
    for (bx, bz, _yaw) in st.get("carries", ()):
        for rid, r in rooms.items():
            hx, hz, _ch, _k = dims(r)
            if abs(bx - r["at"][0]) <= hx and abs(bz - r["at"][1]) <= hz:
                boxes.add((rid, _zone_of(r, bx - r["at"][0], bz - r["at"][1])))
    has0 = (st["start"], _zone_of(sr, st["spawn"][0], st["spawn"][1])) in boxes
    start = start_state or (st["start"], _zone_of(sr, st["spawn"][0], st["spawn"][1]), s0, has0)
    edges = {rid: _zone_edges(rooms[rid]) for rid in rooms}
    seen = {start: 0}
    prev = {start: None}
    frontier = [start]
    best, bestState = None, None
    while frontier:
        nxt = []
        for stt in frontier:
            room, zone, sc, hasbox = stt
            aid = CARRY_TOP if hasbox else 0.0
            hops = seen[stt]
            if room == st["goalRoom"] and zone == goal_zone:
                if best is None or hops < best:
                    best, bestState = hops, stt
                continue
            r = rooms[room]
            scs = _scales_of(st, room, sc)
            for (za, zb), div in edges[room].items():
                if za == zone and any(_pass_gate(div[2], q, aid) for q in scs):
                    n = (room, zb, sc, hasbox or ((room, zb) in boxes))
                    if n not in seen:
                        axis, c, gate = div
                        wp = (r["at"][0], r["at"][1] + c) if axis == "z" else (r["at"][0] + c, r["at"][1])
                        seen[n] = hops
                        prev[n] = (stt, {"big": "跨ぐ", "small": "くぐる", "pit": "跳び越える"}[gate[0]], wp)
                        nxt.append(n)
            for mid, m in mouths.items():
                if m["room"] != room or m["zone"] != zone:
                    continue
                if all(climb_h(q) < m["sill"] - 1e-6 for q in scs):
                    continue
                to = W.links[mid]
                mt = mouths[to]
                # ★体の大きさは【出る側の口】で決まる(Junction.lua と対)。
                #   両端が同じなら結果として大きさは変わらない = 小さいまま帰れる。
                ns = mt["size"]
                n = (mt["room"], mt["zone"], ns, hasbox or ((mt["room"], mt["zone"]) in boxes))
                if n not in seen:
                    seen[n] = hops + 1
                    prev[n] = (stt, "%s→%s(x%.2g)" % (mid, to, ns), m["pos"])
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


def check_layout(st):
    """★部屋どうしが重なっていないかを見る(v9 で追加)。
    縮尺が違う部屋を格子に並べると、角が 2m だけ噛み合う配置が簡単に作れてしまう。
    生成は通り、絵も一見それらしいのに、壁が壁を貫いて中が見える。目で見つけるのは無理。"""
    boxes = []
    for r in st["rooms"]:
        hx, hz, _ch, k = dims(r)
        cx, cz = r["at"]
        t = WALLT * k * 0.5
        boxes.append((r["id"], cx - hx - t, cx + hx + t, cz - hz - t, cz + hz + t))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            ox = min(a[2], b[2]) - max(a[1], b[1])
            oz = min(a[4], b[4]) - max(a[3], b[3])
            if ox > 1e-6 and oz > 1e-6:
                raise SystemExit("%s: ★部屋 %s と %s が重なっている(x %.2f m / z %.2f m)"
                                 % (st["name"], a[0], b[0], ox, oz))


def check_corridors(st, W):
    """★廊下(継ぎ目・偽の廊下)が【関係ない部屋】を貫いていないかを見る。
    偽の廊下は部屋の壁から外へ 3.2m 突き出す箱なので、隣の部屋の角に刺さっていても
    check_layout(部屋どうし)は通ってしまう。刺さると向こうの部屋に白い箱が生え、
    しかも当たり判定だけはあるので「何も無い所で止まる」。v9 の第1面で実際に踏んだ。"""
    rooms = []
    for r in st["rooms"]:
        hx, hz, _ch, k = dims(r)
        cx, cz = r["at"]
        t = WALLT * k * 0.5
        rooms.append((r["id"], cx - hx - t, cx + hx + t, cz - hz - t, cz + hz + t))

    def clash(name, x0, x1, z0, z1, skip):
        for (rid, a0, a1, b0, b1) in rooms:
            if rid in skip:
                continue
            ox = min(x1, a1) - max(x0, a0)
            oz = min(z1, b1) - max(z0, b0)
            if ox > 1e-6 and oz > 1e-6:
                raise SystemExit("%s: ★廊下 %s が部屋 %s を貫いている(x %.2f m / z %.2f m)"
                                 % (st["name"], name, rid, ox, oz))

    def span(px, pz, n, L, hw):
        xs = [px - hw * abs(n[1]), px + hw * abs(n[1]), px + n[0] * L]
        zs = [pz - hw * abs(n[0]), pz + hw * abs(n[0]), pz + n[1] * L]
        return min(xs), max(xs), min(zs), max(zs)

    for sp in st.get("fakes", ()):
        m = W.mouths[sp["id"]]
        x0, x1, z0, z1 = span(m["pos"][0], m["pos"][1], m["n"], sp.get("depth", 3.2), m["w"] * 0.5)
        clash("fake %s" % sp["id"], x0, x1, z0, z1, {m["room"]})

    for t in W.tunnels:
        x0, x1, z0, z1 = span(t["ax"], t["az"], (t["nx"], t["nz"]), t["L"],
                              max(t["wa"], t["wb"]) * 0.5)
        clash("seam %s" % t["id"], x0, x1, z0, z1,
              {W.mouths[t["a"]]["room"], W.mouths[t["b"]]["room"]})


def _room_boxes(st):
    out = []
    for r in st["rooms"]:
        hx, hz, _ch, k = dims(r)
        cx, cz = r["at"]
        t = WALLT * k * 0.5
        out.append((r["id"], cx - hx - t, cx + hx + t, cz - hz - t, cz + hz + t))
    return out


def check_ports(st, W):
    """★継ぎ手の検査。ここが崩れると「暗い筒を歩いたら別の場所」という一番大事な嘘が
    目に見えてしまうので、次の 4 つを機械で見る。

      1. 筒(2m の箱)が【関係ない部屋】へ突き刺さっていないか
         → 刺さると部屋の中に黒い箱が生え、当たり判定だけある壁になる
      2. 筒どうしが重なっていないか
      3. 結ばれた 2 つの口の【寸法が同じ】か
         → 違うと入った筒と出た筒の幅が変わり、暗くても輪郭で分かってしまう
      4. どの口にも結線があるか(行き止まりの黒い穴を残さない)
    """
    rooms = _room_boxes(st)
    boxes = []
    for q in W.ports:
        n = (q["nx"], q["nz"])
        hw = q["hw"]
        x0 = min(q["x"] - hw * abs(n[1]), q["x"] + n[0] * (q["P"] + 0.9))
        x1 = max(q["x"] + hw * abs(n[1]), q["x"] + n[0] * (q["P"] + 0.9))
        z0 = min(q["z"] - hw * abs(n[0]), q["z"] + n[1] * (q["P"] + 0.9))
        z1 = max(q["z"] + hw * abs(n[0]), q["z"] + n[1] * (q["P"] + 0.9))
        boxes.append((q["id"], x0, x1, z0, z1, q["room"], q.get("free", False)))
    for (pid, x0, x1, z0, z1, own, free) in boxes:
        if free:
            continue          # 部屋の中に立つ筐体は、その部屋に入っていて当たり前
        for (rid, a0, a1, b0, b1) in rooms:
            ox = min(x1, a1) - max(x0, a0)
            oz = min(z1, b1) - max(z0, b0)
            if ox > 0.35 and oz > 0.35:      # 壁の厚みぶんは重なって当然
                raise SystemExit("%s: ★継ぎ手 %s の筒が部屋 %s へ刺さっている(x %.2f / z %.2f)"
                                 % (st["name"], pid, rid, ox, oz))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            ox = min(a[2], b[2]) - max(a[1], b[1])
            oz = min(a[4], b[4]) - max(a[3], b[3])
            if ox > 1e-6 and oz > 1e-6:
                raise SystemExit("%s: ★継ぎ手 %s と %s の筒が重なっている" % (st["name"], a[0], b[0]))
    size = {q["id"]: q["size"] for q in W.ports}
    outs = set()
    for lk in W.linkrows:
        outs.add(lk["frm"])
        if abs(size[lk["frm"]] - size[lk["to"]]) > 1e-3:
            raise SystemExit("%s: ★継ぎ手 %s(%.2f) と %s(%.2f) は寸法が違う。筒の幅が変わると入れ替わりが見える"
                             % (st["name"], lk["frm"], size[lk["frm"]], lk["to"], size[lk["to"]]))
    for q in W.ports:
        if q["id"] not in outs:
            raise SystemExit("%s: ★継ぎ手 %s に結線が無い(行き止まりの黒い穴になる)" % (st["name"], q["id"]))


def check_ames(st, W):
    """エイムズの部屋の検査。★床が水平か(戻し回転が効いているか)と、
    歪めた外形が他の部屋を貫いていないか。"""
    rooms = _room_boxes(st)
    for a in W.amesboxes:
        if a["floorErr"] > 0.02:
            raise SystemExit("%s: ★エイムズ %s の床が水平でない(最大 %.3fm)。戻し回転が合っていない"
                             % (st["name"], a["id"], a["floorErr"]))
        xs = [p[0] for p in a["pts"]]
        zs = [p[2] for p in a["pts"]]
        for (rid, a0, a1, b0, b1) in rooms:
            if rid == a["room"]:
                continue
            ox = min(max(xs), a1) - max(min(xs), a0)
            oz = min(max(zs), b1) - max(min(zs), b0)
            if ox > 1e-6 and oz > 1e-6:
                raise SystemExit("%s: ★エイムズ %s が部屋 %s と重なっている(x %.2f / z %.2f)"
                                 % (st["name"], a["id"], rid, ox, oz))
        r = W.rooms[a["room"]]
        hx, hz, _c, k = dims(r)
        nl = a["near"]
        for p in nl:
            lx, lz = p[0] - r["at"][0], p[2] - r["at"][1]
            if abs(lx) > hx + 0.4 and abs(lz) > hz + 0.4:
                continue
            if abs(lx) - 1e-6 > hx + 0.4 or abs(lz) - 1e-6 > hz + 0.4:
                raise SystemExit("%s: ★エイムズ %s の手前の口が母屋の壁からはみ出す(local %.2f, %.2f)"
                                 % (st["name"], a["id"], lx, lz))


def check_props(st, W):
    """★什器どうしがめり込んでいないか / 壁を突き抜けていないか。
    v10 は部屋が広く物が多いので、目視では絶対に見つからない。"""
    for rid, fx in W.fixtures.items():
        if rid not in W.rooms:
            continue                    # "ames:xx" = 別棟の帳簿。壁の判定は母屋の壁ではない
        r = W.rooms[rid]
        hx, hz, _ch, k = dims(r)
        for i, (x, z, rr, top) in enumerate(fx):
            if rr >= 2.0:
                continue
            lx, lz = abs(x - r["at"][0]), abs(z - r["at"][1])
            # ★什器は壁に背をつけて置くのが正しいので、中心が【内寸の外】に出た時だけ弾く。
            #   半径ぶんの余裕を見ると、壁付けの置き方が全部引っかかる(v9 の SET1 も落ちる)。
            if lx > hx - 0.15 or lz > hz - 0.15:
                raise SystemExit("%s: 部屋 %s の什器 %d が壁の外にある(local %.1f,%.1f / 内寸 %.1f,%.1f)"
                                 % (st["name"], rid, i, x - r["at"][0], z - r["at"][1], hx, hz))
            for j, (x2, z2, r2, _t2) in enumerate(fx):
                if j <= i or r2 >= 2.0:
                    continue
                d = math.hypot(x - x2, z - z2)
                if d < (rr + r2) * 0.62:
                    raise SystemExit("%s: 部屋 %s の什器 %d と %d が重なっている(距離 %.2f)"
                                     % (st["name"], rid, i, j, d))


def check_solvable(st, W):
    hops, states, path, pts = simulate(st, W)
    if hops is None:
        raise SystemExit("%s: ★出口に到達できない(全 %d 状態)" % (st["name"], states))
    if hops == 0 and st.get("minHops", 1) > 0:
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
        if not any(k[0] == m["room"] and k[1] == z for k in seen):
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
            # ★★そもそも【天端に登れない】物は踏み台にならない。ロッカー(1.95m)は
            #   climb_h(1)=1.15 でも climb_h(0.5)=0.58 でも登れない。ここを見ていなかったので、
            #   縮尺 0.5 の部屋(内寸 6m)では「ロッカーを柵から 3.85m 離す」が
            #   【幾何的に不可能】になり、同じ間取りを 0.5 倍で置けなかった。
            #   ★積み重ね(木箱→ロッカー)は見ていない。SET1 の 3 つではどの組み合わせも
            #   届かない(0.75+1.15=1.90 < 1.95)ことを確かめてある。
            if climb_h(k) < P["top"] - 1e-6:
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


def cine_world(st, centers, eye=EYE_H):
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
    out.append((sx, eye, sz, sx + fx * 8.0, eye, sz + fz * 8.0, 1.4))
    return out


# ================================ ステージ定義 ================================
def R(rid, shape, at, scale=1.0, layout=None, tilt=0.0, tiltAxis="z", tiltAt=(0.0, 0.0, 0.0),
      intensity=None, lightcol=None, floorMat=None, tiltFloor=None):
    d = dict(id=rid, shape=shape, at=at, scale=scale, layout=layout or {},
             tilt=tilt, tiltAxis=tiltAxis, tiltAt=tiltAt)
    if intensity is not None:
        d["intensity"] = intensity
    if lightcol is not None:
        d["lightcol"] = lightcol
    if floorMat is not None:
        d["floorMat"] = floorMat
    if tiltFloor is not None:
        d["tiltFloor"] = tiltFloor
    return d


def SEAM(sid, room, wall, off, sill=0.0, osize=None, osizeB=None):
    """osize = room 側の口の大きさ / osizeB = 向こう側の口の大きさ(省略で osize と同じ)。
    ★体の大きさは【出る側の口】で決まる(Junction.lua)。だから左右で大きさを変えると、
      同じ戸が【行きと帰りで違う結果】を出す = このゲームの仕掛けの本体になる。
      例: A 側 4.0m / B 側 1.0m なら、B から入れば 2 倍で出てきて、A から入れば 0.5 倍で出る。"""
    return dict(id=sid, room=room, wall=wall, off=off, sill=sill,
                osize=osize, osizeB=osizeB if osizeB is not None else osize)


def FAKE(fid, room, wall, off, depth=3.2, look=16.0):
    """偽の廊下。★奥行 2.5m / 見かけ 20m(v8)は縮み率 0.125 = 床が 2.5m で 1.14m 上がる
    【24.5 度の坂】になっていた。当たり判定を平面にして段差は消えたが、2 歩で 1.1m 登るのは
    それ自体が不自然。3.2m / 16m にすると縮み率 0.2 = 18 度。嘘の強さはほぼ変わらない。"""
    return dict(id=fid, room=room, wall=wall, off=off, depth=depth, look=look)


def MORPH(mid, room, at=(0.0, 0.0), r=8.0, delay=1.2, org=(), alt=(), seal=(), unseal=(), light=None):
    return dict(id=mid, room=room, at=at, r=r, delay=delay, org=org, alt=alt,
                seal=seal, unseal=unseal, light=light)


def WARP(wid, fromTunnel, toTunnel, loops=30, scales=()):
    """廊下の途中で黙って別の廊下へ運ぶ。★scales を付けると【運ぶと同時に体の大きさが変わる】。
    運ぶ先を「同じ部屋の反対側の口」にすると、プレイヤーは同じ部屋へ戻ってくるのに
    大きさだけが違う = 部屋そのものが伸び縮みしたようにしか見えない。"""
    return dict(id=wid, fromTunnel=fromTunnel, toTunnel=toTunnel, loops=loops, scales=list(scales))


def SGATE(gid, room, at, facing, sf, sb, size=3.2):
    """大きさの門。床に立った枠(seam.gltf)。くぐると【その場で】大きさが変わる。
    at は部屋の単位座標、facing は枠の正面("N"/"S"/"E"/"W")。
    sf = 正面から入った時の大きさ / sb = 背面から入った時の大きさ。
    ★size は seam.gltf(幅 1.0 / 高さ 1.3)の一様倍率。一番大きい体(1.8 x s)が
      くぐれる高さが要る: size 3.2 なら開口 3.2 x 4.16 で s=2(3.6m)が通る。"""
    return dict(id=gid, room=room, at=at, facing=facing, sf=sf, sb=sb, size=size)


def WIN(room, wall, off):
    return dict(room=room, wall=wall, off=off)


# ================================ v10 の語彙 ================================
def PORT(pid, room, wall=None, off=0.0, at=None, into=None, depth=PORT_D, size=1.0, hole=None,
         ames=None):
    """継ぎ手の口。壁に開ける(wall=)か、部屋の中に単体で立てる(at=, into=)。
    into = そこへ【入る時に歩く向き】。hole = 母屋に開ける穴の大きさ(既定 size)。"""
    d = dict(id=pid, room=room, depth=depth, size=size)
    if wall:
        d.update(wall=wall, off=off, hole=hole if hole is not None else size)
    else:
        d.update(at=at, into=into, ames=ames)
    return d


def LINK(frm, to, times=0):
    """継ぎ手 frm の奥を越えたら to から出る。times>0 なら【最初の times 回だけ】。
    ★同じ戸が回数で行き先を変えられる = 「三度歩かされる廊下」が書ける。"""
    return dict(**{"from": frm, "to": to, "times": times})


def JOIN(a, b, times=0):
    """両通行の継ぎ手 1 組。LINK 2 本(行きと帰り)の砂糖。"""
    return [LINK(a, b, times), LINK(b, a, times)]


def AMES(aid, room, wall, off=0.0, w=8.0, d=14.0, h=5.0, alpha=0.075, props=(), lights=None,
         eye=EYE_H):
    return dict(id=aid, room=room, wall=wall, off=off, w=w, d=d, h=h, alpha=alpha,
                props=list(props), lights=lights, eye=eye)


def WATCH(wid, room, at, yaw=0.0, h=1.85, step=2.6, near=2.2, rng=34.0, wait=0.5, model="figure"):
    return dict(id=wid, room=room, at=at, yaw=yaw, h=h, step=step, near=near, range=rng,
                wait=wait, model=model)


def CREEP(cid, ents, zone, axis="z", a=0.0, b=1.0, dx=0.0, dy=0.0, dz=0.0):
    """zone の中で、座標 axis が a→b と進むにつれて ents を (dx,dy,dz) だけずらす。
    ★進み具合は【戻らない】(ラチェット)。だから引き返しても元には戻っていない。"""
    return dict(id=cid, ents=list(ents), zone=zone, axis=axis, a=a, b=b, dx=dx, dy=dy, dz=dz)


def ROLL(zone, axis="z", a=0.0, b=1.0, deg=(0.0, 0.0)):
    return dict(zone=zone, axis=axis, a=a, b=b, deg=deg)


# ================================ v11 の語彙 ================================
def GATE(gid, room, at, facing="S", size=1.0, y=0.0):
    """継ぎ手の枠。部屋の中に単体で立つ門。中に膜(Membrane.hlsl)が張ってある。
    facing = 【正面が向く方位】。プレイヤーはその側から入る。"""
    return dict(id=gid, room=room, at=at, facing=facing, size=size, y=y)


# ★対の色。同じ色の枠どうしだけが繋がる。これが「どれとどれを重ねるのか」を
#   文字なしで言う唯一の手段(指摘: 解き方がぜんぜん分からない)。
PAIRCOL = {
    "amber":  (1.00, 0.62, 0.18),
    "cyan":   (0.24, 0.82, 1.00),
    "green":  (0.32, 1.00, 0.48),
    "violet": (0.72, 0.46, 1.00),
    "red":    (1.00, 0.32, 0.28),
    "blue":   (0.38, 0.52, 1.00),
}
PAIRHUE = {"amber": 0.09, "cyan": 0.53, "green": 0.35, "violet": 0.76,
           "red": 0.99, "blue": 0.62}


def PAIR(a, b, both=True, needs=None, col="cyan", mark=0.0):
    """★重ねると繋がる枠の組。手前の枠の開口の中に向こうの枠が【見えている】時だけ有効。
    col   … 対の色。両方の枠が同じ色で光る = 一目でどれと組か分かる
    needs … 重量板の id。押されるまで枠は【消灯】して繋がらない
    mark  … >0 なら手前の枠の正面 mark m の床に【立ち位置の印】を描く(最初の教える組だけ)"""
    return dict(a=a, b=b, both=both, needs=needs, col=col, mark=mark)


def PLATE(pid, room, at, r=1.05):
    """重量板。動く剛体(玉・ドラム缶・木箱)が乗ると押される。"""
    return dict(id=pid, room=room, at=at, r=r)


def TILTF(deg=6.0, over=5.0, walls=(), withEnts=()):
    """視線で傾く床。★見ている方へ床が下がるので、玉は【見た方へ】転がる。
    walls = 床と一緒に傾く低い壁 (x, z, 幅, 奥行, 高さ)。withEnts = 一緒に傾ける物の名前。"""
    return dict(deg=deg, over=over, walls=list(walls), **{"with": list(withEnts)})


def FOVR(zone, axis="z", a=0.0, b=1.0, fov=(74.0, 74.0)):
    """歩く位置で画角を連続的に変える帯。★画角を絞ると【近づいても大きくならない】。
    奥の壁が遠ざかって見えるので、廊下がいつまでも終わらない。"""
    return dict(zone=zone, axis=axis, a=a, b=b, f0=fov[0], f1=fov[1])


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

# ================================ v9: 1〜3 面の語彙 ================================
# ★什器の座標を引き直した。v8 の SET は
#     ・ロッカー(5.4, 2.6)が東壁の窓の【真正面 0.6m】に立ち、向こうの部屋を隠す
#     ・柵を z 軸に回すと、どこに置いても check_footholds が落ちる(踏み台になる)
#   ので、1〜3 面は SET1 を使う。SET1 は次を全部満たす:
#     ・全部 x >= 1.8(単位)。柵を x=-2.5 に置いても「柵から 3m + 半径」より遠い
#     ・東西の壁の口の助走(2.5 x 縮尺)を潰さない
#     ・窓(中心 z=+1.6 / 幅 3.6)の正面に何も無い
#   ★4〜8 面は v8 のまま(SET)。物差しは【1 つの面の中で】揃っていればいい。
SET1 = [("locker", 4.6, 4.6, 180.0), ("bench", 1.8, -1.0, 90.0), ("crate", 3.6, -4.4, 20.0)]


def LAY1(bars=(), eaves=(), pits=(), props=None):
    return dict(bars=list(bars), eaves=list(eaves), pits=list(pits),
                props=list(props if props is not None else SET1))


# 柵は部屋の【西 1/3】を切り離す。跨げるのは k=2 だけなので、
# 西側に門を置くと「見えているのに行けない出口」がそのまま謎解きになる。
L9_BAR = LAY1(bars=[("x", -2.5)])
# 隙間は部屋を【南北】に割る。東西の壁に付けた扉と窓を潰さないため(v8 は x 軸で窓を殺していた)
L9_EAVE = LAY1(eaves=[("z", 1.2)])
L9_PLAIN = LAY1()
# 第3面の出口の部屋(k=0.5)。門の側には何も置かない(v8 第3面はベンチが門を隠した)
L9_GOAL_S = LAY1(eaves=[("z", 1.0)],
                 props=[("bench", -1.8, -1.0, 90.0), ("crate", 3.6, -4.4, 20.0)])
# 第3面の餌の部屋(k=2)。隙間の向こうに門。3.6m の体では絶対にくぐれない
L9_TEASE = LAY1(eaves=[("x", 2.0)])

STAGES = [
    # ★【2026-09-03 v9.1】面は demo1 一本に絞った。
    #   v8 の 1〜8 面と demo2/demo3 は廃止。この仕掛けを詰め切ることを優先する。
    #   ★下の L_BAR / SET / L9_* 等の語彙は残してある(面を増やす時に使う)。
    # ---------------- demo1「四つの戸」完成版 ----------------
    # ★部屋は A(本体) と B(東ねぐら) の 2 つだけ。写しは無い。
    #
    # ★仕掛けの核:【体の大きさは『出る側の口』で決まる】。
    #   だから左右で大きさの違う口は、【同じ戸なのに行きと帰りで結果が違う】。
    #   Z は A 側 4.0m / B 側 1.0m。A から入れば 0.5 倍になって B へ、
    #   B から入れば 2 倍になって A へ戻る。行きと帰りで自分の寸法が反転する。
    #
    # ★B 側は四つとも 1.0m で【見分けがつかない】。しかも 1 つは偽の廊下。
    #     Z → A の手前側へ【 2 倍】で出る。溝 4.6m を跳べるのはこれだけ = 正解。
    #     Q → A の手前側へ【小さいまま】。溝は絶対に跳べない。
    #     R → 【柵の向こう】へ小さいまま。壁を越えたのに、そこも行き止まり。
    #     F → 奥に緑の門が見えるが 3 歩で壁(強制遠近法)。
    #
    # ★溝を使った理由: 【穴は視界を塞がない】。出口の門は最初の 3 秒から
    #   溝の向こうに見えていて、最後までそこにある。庵(1.0m)だと壁で門が隠れてしまう。
    #
    # ★什器は壁に背をつけて軸に揃える。東の壁にロッカーとベンチを並べ、
    #   木箱は溝の向こう(門の脂)に置いて、向こう岸の大きさの物差しにする。
    dict(name="stagedemo1", tag="Demo_1", title=1,
         rooms=[R("A", "box12", (0.0, 0.0), 1.0,
                  LAY1(bars=[("x", -2.5)], pits=[("z", -1.0)],
                       props=[("locker", 5.65, 4.80, 270.0),   # 東の壁
                              ("bench", 5.55, 2.50, 270.0),    # 東の壁
                              ("crate", 2.00, -4.80, 0.0)])),  # 溝の向こう
                R("B", "hall20", (0.0, 15.0), 0.5, LAY1(props=[]))],
         # ★Z だけが左右で大きさが違う。Q/R は両端 1.0m = 抜けても大きさが変わらない。
         #   R の口は x=-4.0..-3.0 で、柵(x=-2.5)をまたいでいない(またぐと柵を迴回できる)。
         seams=[SEAM("Z", "A", "N", 2.2, osize=2.0, osizeB=0.5),
                SEAM("Q", "A", "N", -1.0, osize=0.5),
                SEAM("R", "A", "N", -3.5, osize=0.5)],
         # ★off は【その部屋の単位座標】。B は x0.5 なのでワールド -2.2 に置くには -4.4 と書く。
         fakes=[FAKE("f2", "B", "S", -4.4)],
         spawn=(2.0, 4.5, 180.0), goal=(0.0, -4.80), goalYaw=0.0,
         start="A", goalRoom="A", minHops=2, teach="walk",
         cine=[("A", (3.0, 2.4, 4.0), "A", (0.0, 1.4, -4.8), 2.4),
               ("A", (2.0, 1.7, 4.5), "A", (0.0, 1.2, -4.8), 1.6)]),


    # ================ stagedemo2「まわり道」 トンネルだけで騙す ================
    # ★demo1 と同じ顔にならないよう、部屋の形を全部変えた。
    #   H = hall20(20x20x7 の大広間) / L = corr18(18x8x3.2 の低くて長い部屋)
    #   S = box12 x0.5(6m の小部屋)  / G = box12 x2(24m の巨大な部屋)
    #   柵も溝も使わない。関門は【隔間 1.0m】一つだけで、跳ぶ必要が無い。
    #
    # ★【騙しは全部トンネルの設定だけで作る】。使っている手は 6 つ:
    #
    #   (1) 【大きい口に入ると巨人になる】 t5: H側 4.0m / G側 4.0m。
    #       体の大きさは『出る側の口』で決まるので、x1 で入ると x2 で出る。
    #       しかも G は x2 の部屋なので【着いても普通の部屋にしか見えない】。
    #       置いてあるベンチ(0.95m 絶対寸法)だけが脇の高さ = 唯一の手掛かり。
    #
    #   (2) 【小さな穴から出ると小人になる】 t3: H側 1.0m / G側 4.0m。
    #       ★(1) のちょうど逆。G(x2)から見れば t3 も t5 も【同じ 4.0m の口】で、
    #       見分けがつかない。片方は大きさが変わらず、片方は四分の一になる。
    #
    #   (3) 【行きと帰りで結果が違う戸】 t2: H側 2.0m / S側 1.0m。
    #       行きは縮むが、帰りは元に戻る。S は x0.5 の部屋なので着いても普通。
    #       ここは【行き止まり】= 縮んだだけでは何も解けない、という餅。
    #
    #   (4) 【両端同じ大きさの戸】 t1: H側も L 側も 2.0m。抜けても大きさが変わらない。
    #       【変わる戸と変わらない戸が同じ顔で並んでいる】のがこの面の核。
    #
    #   (5) 【通れないのに見える】 窓(H ↔ L)。低い部屋の中が見えるが入れない。
    #
    #   (6) 【奥に緑の門が見える偽の廊下】 L の北壁。3 歩で壁。
    #
    # ★解き筋(検査器もこの道を確認している):
    #   H(x1)。隔間 1.0m の向こうに出口が見えているが 1.8m の体ではくぐれない。
    #   → t5(大きい口)で G へ。x2 になっているが部屋も x2 なので気づかない。
    #   → G の壁には同じ顔の口が 2 つ。t3 を抜けると【x0.5 で H へ戻る】。
    #   → 小人になって隔間をくぐり、出口へ。
    dict(name="stagedemo2", tag="Demo_2", title=2,
         rooms=[R("H", "hall20", (0.0, 0.0), 1.0,
                  LAY1(eaves=[("z", -4.0)],
                       props=[("locker", 7.50, 9.40, 180.0),
                              ("bench", 9.50, 5.00, 270.0)])),
                R("L", "corr18", (0.0, 18.0), 1.0,
                  LAY1(props=[("bench", -5.00, 0.00, 0.0)])),
                R("S", "box12", (17.0, 0.0), 0.5, LAY1(props=[])),
                R("G", "box12", (-26.0, 0.0), 2.0,
                  LAY1(props=[("bench", 2.00, -3.00, 0.0)]))],
         seams=[SEAM("t1", "H", "N", 0.0, osize=1.0),                 # 大きさ変わらず
                SEAM("t2", "H", "E", 0.0, osize=1.0, osizeB=0.5),     # 行きだけ縮む
                SEAM("t5", "H", "W", 5.0, osize=2.0),                 # 入ると巨人
                SEAM("t3", "H", "W", 0.0, osize=0.5, osizeB=2.0)],    # 出ると小人
         windows=[WIN("H", "N", 5.0)],
         fakes=[FAKE("f1", "L", "N", 0.0)],
         carries=[(3.0, 18.0, 0.0)],
         # ★(1) 角度固定の門。L(18x8x3.2 の低い部屋)の西端に置く。
         #   歩いて近づいても画面上の大きさが 1px も変わらないので【永遠に着かない】。
         #   d0=14 は「L の東端から見たときが等倍」。k=0.55 で天井(3.2m)に当たらない大きさに。
         anchors=[(-7.0, 18.0, 90.0, 0.55, 14.0)],
         # ★(2) 連続スケール場。L の中を西へ歩くほど連続的に縮む。
         #   トンネルのような【変化点が無い】ので、どこで変わったのか指させない。
         #   入口(x=0)で等倍、西端(x=-9)で半分。東側は clamp されるso行き来で自然に戻る。
         field=dict(axis="x", a=0.0, b=-9.0, s0=1.0, s1=0.5,
                    x0=-9.5, x1=0.5, z0=13.5, z1=22.5),
         # ★(3) ドリーズーム。隙間をくぐる直前で FOV を絞る = 自分は動いていないのに部屋が伸びる。
         dolly=[(0.0, -5.0, 5.5, 52.0)],
         spawn=(4.0, 3.0, 180.0), goal=(0.0, -8.0), goalYaw=0.0,
         start="H", goalRoom="H", minHops=2, teach="walk",
         cine=[("H", (4.0, 2.6, 5.0), "H", (-2.0, 1.4, -2.0), 2.4),
               ("H", (4.0, 1.7, 3.0), "H", (-2.0, 1.3, -2.0), 1.6)]),

    # ======================================================================================
    # stagedemo3「継ぎ目の館 / SORTING HOUSE」 v11.2 — 4 回くぐって 1 つ解く
    # ======================================================================================
    # ★指摘「その部屋でなにすればいいか分からん」への答えは【短くする】ことだった。
    #   v11.1 は往復 3 回・板 2 枚・分岐 5 本で、道筋そのものが読めなかった。
    #
    #   必須はこれだけ:
    #     1. 始まりの帯で【琥珀】の枠を重ねて柵を越える
    #     2. 中の帯から【水色】の枠を重ねて傾く部屋へ(東の窓ごしに見える)
    #     3. 傾く部屋で鋼球を【青い重量板】へ転がす  ← ここが唯一のパズル
    #     4. 水色で戻り、【青】の枠を重ねて谷を渡る   ← 青い板が青い枠を点ける
    #
    #   ★中の帯に立つと、谷の向こうの出口と、消えている青い枠と、
    #     東の窓の向こうの青い板が【全部同時に見える】。やる事は見れば分かる。
    #
    #   寄り道(行かなくても終われる): 緑=機械室(エイムズの部屋)/ 赤=仕分け廊(画角の嘘)/
    #   紫=保管庫(視線をふさぐ人型)。
    dict(name="stagedemo3", tag="Demo_3", title=3,
         intensity=5.2, exposure=0.82,
         rooms=[
             R("A", "atrium40", (0.0, 0.0), 1.0,
               dict(bars=[("z", -13.0)], barMdl="fence", pits=[("z", 0.0, 14.0)],
                    props=[("rack", -17.0, -18.4, 0.0), ("rack", 17.0, -18.4, 0.0),
                           ("drum", -9.0, -17.8, 0.0), ("drum", -8.2, -18.3, 40.0),
                           ("bench", -2.0, -18.6, 0.0), ("bench", 2.0, -18.6, 0.0),
                           ("locker", 18.4, -16.0, 270.0), ("crate", 10.5, -17.5, 20.0),
                           ("rack", -18.4, -10.0, 90.0), ("drum", 17.6, -8.4, 0.0),
                           ("crate", -16.0, -8.6, 35.0),
                           ("column", -16.0, 16.0, 0.0), ("column", 16.0, 16.0, 0.0),
                           ("rack", -15.0, 18.4, 180.0), ("rack", 15.0, 18.4, 180.0),
                           ("drum", 12.0, 9.0, 0.0), ("bench", -6.0, 8.6, 180.0)]),
               floorMat="concrete", intensity=3.4),
             # ★傾く部屋。受入ホールの【東】。中の帯から窓ごしに中が見える
             R("G", "tilt16", (32.0, -10.0), 1.0,
               dict(props=[("ball", 5.0, 4.0, 0.0),
                           ("locker", -6.6, 6.6, 90.0), ("bench", -6.4, -5.6, 90.0)]),
               floorMat="concrete", intensity=4.4,
               tiltFloor=TILTF(deg=6.5, over=5.0,
                               walls=[(0.0, -2.2, 4.6, 0.35, 0.55),
                                      (-2.3, -1.0, 0.35, 2.4, 0.55),
                                      (2.3, -1.0, 0.35, 2.4, 0.55)],
                               withEnts=["Plate_p1", "PlateL_p1"])),
             # ---- ここから下は寄り道 ----
             R("D", "hall26", (-37.0, -10.0), 1.0,
               dict(props=[("column", -8.0, -8.0, 0.0), ("column", 8.0, -8.0, 0.0),
                           ("column", -8.0, 8.0, 0.0), ("column", 8.0, 8.0, 0.0),
                           ("rack", 11.0, -4.0, 270.0), ("rack", 11.0, 4.0, 270.0),
                           ("drum", 3.0, 8.4, 0.0), ("drum", 3.9, 8.9, 30.0),
                           ("crate", -1.0, 9.6, 15.0),
                           ("locker", 6.0, -11.4, 0.0), ("bench", -6.0, -3.0, 90.0),
                           ("pipes", 0.0, -7.0, 0.0)]),
               floorMat="concrete"),
             R("B", "corr36", (0.0, -28.5), 1.0,
               dict(props=[("rack", -10.0, -3.2, 0.0), ("rack", -6.0, -3.2, 0.0),
                           ("rack", 6.0, -3.2, 0.0), ("rack", 10.0, -3.2, 0.0),
                           ("rack", -8.0, 3.2, 180.0), ("rack", 8.0, 3.2, 180.0),
                           ("drum", -2.6, 3.4, 0.0), ("crate", 2.0, -3.4, 0.0)]),
               floorMat="concrete"),
             R("H", "store22", (0.0, -45.0), 1.0,
               dict(props=[("rack", -8.0, -4.5, 0.0), ("rack", -4.0, -4.5, 0.0),
                           ("rack", 4.0, -4.5, 0.0), ("rack", 8.0, -4.5, 0.0),
                           ("rack", -8.0, 3.5, 0.0), ("rack", 8.0, 3.5, 0.0),
                           ("drum", -9.6, 6.4, 0.0), ("crate", 9.0, -6.6, 25.0),
                           ("locker", 9.6, 6.4, 270.0)]),
               floorMat="concrete", intensity=1.7, lightcol=(0.82, 0.87, 1.0)),
         ],
         # ---- 窓。隣の部屋は【見えるが入口が無い】 ----
         windows=[WIN("A", "E", -10.0),     # 中の帯 -> 傾く部屋(青い板が見える)
                  WIN("A", "W", -10.0),     # 中の帯 -> 機械室(寄り道)
                  WIN("A", "S", -14.0),     # 始まりの帯 -> 仕分け廊(寄り道)
                  WIN("B", "S", 0.0)],      # 仕分け廊 -> 保管庫(寄り道)
         gates=[GATE("s1", "A", (6.0, -15.5), "S"),      # 1. 柵を越える
                GATE("m1", "A", (6.0, -10.0), "S"),
                GATE("m2", "A", (12.0, -10.0), "W"),     # 2. 東の窓ごしに傾く部屋
                GATE("g1", "G", (-6.0, 0.0), "W"),
                GATE("m3", "A", (0.0, -9.5), "S"),       # 4. 谷を渡る(青い板が要る)
                GATE("n1", "A", (0.0, 12.0), "S"),
                GATE("m4", "A", (-12.0, -10.0), "E"),    # 寄り道: 機械室
                GATE("d1", "D", (11.0, 0.0), "E"),
                GATE("s2", "A", (-14.0, -18.0), "N"),    # 寄り道: 仕分け廊
                GATE("b1", "B", (-14.0, 1.5), "N"),
                GATE("b2", "B", (0.0, -1.5), "N"),       # 寄り道: 保管庫
                GATE("h1", "H", (0.0, 6.0), "N")],
         # ★板は【玉が自然に止まる所】= 囲いの南の突き当りに置く。
         #   真ん中に置いたら玉が板を通り過ぎて南壁で止まり、1.7m 手前で止まった(実測)。
         plates=[PLATE("p1", "G", (0.0, -1.5), r=1.5)],
         # ★青い板が青い枠を点ける。色だけが理屈。文字はいらない
         pairs=[PAIR("s1", "m1", col="amber", mark=2.6),
                PAIR("m2", "g1", col="cyan", mark=3.0),
                PAIR("m3", "n1", col="blue", needs="p1", mark=3.0),
                PAIR("m4", "d1", col="green"),
                PAIR("s2", "b1", col="red"),
                PAIR("b2", "h1", col="violet")],
         # ---- 案内。★文字ではなく【光の玉】が次にやる事の上に浮く ----
         guide=[(6.0, -18.1, "cross:s1"),
                (9.0, -10.0, "cross:m2"),
                (32.0, -10.0, "plate:p1"),
                (27.6, -10.0, "cross:g1"),
                (0.0, -12.5, "cross:m3"),
                (0.0, 17.0, "")],
         ames=[AMES("E1", "D", "W", 0.0, w=9.0, d=15.0, h=5.0, alpha=0.07,
                    props=[("locker", -3.6, 13.0, 0.0), ("locker", 3.6, 13.0, 0.0),
                           ("bench", -3.6, 5.5, 0.0), ("bench", 3.6, 5.5, 0.0),
                           ("drum", -1.6, 8.5, 0.0), ("drum", 1.6, 8.5, 0.0)])],
         fakes=[FAKE("f_d", "D", "S", 0.0)],
         anchors=[(16.5, -28.5, 270.0, 1.0, 31.0)],
         watchers=[WATCH("W1", "H", (-4.0, 1.0), yaw=180.0, near=3.2, step=1.4, wait=1.0),
                   WATCH("W2", "H", (3.0, 2.0), yaw=180.0, near=3.6, step=1.2, wait=1.3),
                   WATCH("W3", "H", (7.0, 0.0), yaw=180.0, near=4.0, step=1.1, wait=1.6)],
         fovramps=[FOVR(zone=(-19.0, 19.0, -34.0, -23.0), axis="x", a=-14.0, b=14.0,
                        fov=(74.0, 46.0))],
         rolls=[ROLL(zone=(-19.0, 19.0, -34.0, -23.0), axis="x", a=-12.0, b=14.0,
                     deg=(0.0, 8.0))],
         dolly=[(0.0, -8.5, 5.0, 54.0)],
         morphs=[MORPH("m1", "A", at=(0.0, -10.0), r=15.0, delay=1.2,
                       org=[("drum", 12.0, 9.0, 0.0), ("bench", -6.0, 8.6, 180.0)],
                       alt=[("drum", -12.5, 9.6, 0.0), ("bench", 7.0, 12.0, 90.0)],
                       light=(0.93, 0.93, 1.0))],
         spawn=(6.0, -19.2, 0.0), goal=(0.0, 17.0), goalYaw=180.0,
         start="A", goalRoom="A", minHops=2, teach=None,
         hintPath=[(6.0, -18.1)],
         cine=[("A", (11.0, 7.5, -18.0), "A", (0.0, 2.2, 14.0), 3.0),
               ("A", (6.0, 2.7, -18.6), "A", (6.0, 2.5, 10.0), 1.8)]),


]


def main():
    lua = []
    manifest = {}
    for i, st in enumerate(STAGES):
        check_layout(st)
        W = World(st)
        data = W.build()
        check_footholds(st, W)
        check_corridors(st, W)
        check_ports(st, W)
        check_ames(st, W)
        check_props(st, W)
        check_runup(st, W)
        check_fakes(st, W)
        pts = check_solvable(st, W)
        # ★案内の光の経路は simulate() が出すが、simulate は【栓(plug)を見ていない】。
        #   morph で開くまで塞がっている扉へ最初から光が飛ぶと「案内が壁を指している」に
        #   なる。栓で道順そのものを作る面(第1面)は hintPath で手で書く。
        if st.get("hintPath"):
            pts = [tuple(q) for q in st["hintPath"]]
        else:
            pts = [tuple(q) for q in st.get("hintPre", ())] + pts
        check_no_deadend(st, W)
        centers = check_cine(st, W)
        manifest.update(W.manifest)

        path = os.path.join(OUT, st["name"] + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("wrote", path)

        nxt = STAGES[i + 1]["name"] if i + 1 < len(STAGES) else None
        cine = cine_world(st, centers,
                          EYE_H * st.get("startScale", W.rooms[st["start"]]["scale"]))
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
            L.append('            { id = "%s", px = %.3f, pz = %.3f, nx = %.3f, nz = %.3f, dx = %.3f, dy = %.3f, dz = %.3f, loops = %d, hw = %.2f, scales = { %s } },'
                     % (w["id"], w["px"], w["pz"], w["nx"], w["nz"], w["dx"], w["dy"], w["dz"],
                        w["loops"], w["hw"], ", ".join("%.3f" % q for q in w.get("scales", ()))))
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
        # ---------------- v10 ----------------
        L.append('        ports = {')
        for q in W.ports:
            L.append('            { id = "%s", x = %.3f, z = %.3f, nx = %.3f, nz = %.3f, alx = %.3f, alz = %.3f, '
                     'hw = %.2f, P = %.2f, y0 = %.2f, size = %.3f },'
                     % (q["id"], q["x"], q["z"], q["nx"], q["nz"], q["alx"], q["alz"],
                        q["hw"], q["P"], q["y0"], q["size"]))
        L.append('        },')
        L.append('        links = {')
        pidx = {q["id"]: i + 1 for i, q in enumerate(W.ports)}
        for lk in W.linkrows:
            L.append('            { from = %d, to = %d, times = %d, dyaw = %.3f, rlx = %.4f, rlz = %.4f },'
                     % (pidx[lk["frm"]], pidx[lk["to"]], lk["times"], lk["dyaw"], lk["rlx"], lk["rlz"]))
        L.append('        },')
        L.append('        watchers = {')
        for q in W.watchers:
            L.append('            { ent = "%s", x = %.3f, y = %.3f, z = %.3f, step = %.2f, near = %.2f, '
                     'rng = %.1f, wait = %.2f, turn = %d },'
                     % (q["ent"], q["x"], q["y"], q["z"], q["step"], q["near"], q["rng"],
                        q["wait"], q["turn"]))
        L.append('        },')
        L.append('        creeps = {')
        for q in W.creeps:
            L.append('            { id = "%s", axis = "%s", a = %.2f, b = %.2f, dx = %.3f, dy = %.3f, dz = %.3f, '
                     'x0 = %.2f, x1 = %.2f, z0 = %.2f, z1 = %.2f, ents = { %s } },'
                     % (q["id"], q["axis"], q["a"], q["b"], q["dx"], q["dy"], q["dz"],
                        q["x0"], q["x1"], q["z0"], q["z1"],
                        ", ".join('"%s"' % e for e in q["ents"])))
        L.append('        },')
        L.append('        rolls = {')
        for q in W.rolls:
            L.append('            { axis = "%s", a = %.2f, b = %.2f, d0 = %.2f, d1 = %.2f, '
                     'x0 = %.2f, x1 = %.2f, z0 = %.2f, z1 = %.2f },'
                     % (q["axis"], q["a"], q["b"], q["d0"], q["d1"],
                        q["x0"], q["x1"], q["z0"], q["z1"]))
        L.append('        },')
        L.append('        gates = {')
        for q in W.gates:
            rgb = q.get("rgb", (0.62, 0.76, 0.95))
            L.append('            { id = "%s", ent = "Gate_%s", mem = "GateM_%s", light = "GateL_%s", '
                     'x = %.3f, z = %.3f, y0 = %.2f, '
                     'nx = %.3f, nz = %.3f, alx = %.3f, alz = %.3f, hw = %.2f, hh = %.2f, size = %.2f, '
                     'cr = %.3f, cg = %.3f, cb = %.3f, hue = %.3f, needs = "%s" },'
                     % (q["id"], q["id"], q["id"], q["id"], q["x"], q["z"], q["y0"], q["nx"], q["nz"],
                        q["alx"], q["alz"], q["hw"], q["hh"], q["size"],
                        rgb[0], rgb[1], rgb[2], q.get("hue", 0.53), q.get("needs", "")))
        L.append('        },')
        gidx = {q["id"]: i + 1 for i, q in enumerate(W.gates)}
        L.append('        pairs = {')
        for q in W.gpairs:
            # ★色は枠の側に持たせる。ここで r/g/b を書くと【b が枠の番号 b を上書きする】
            #   (Lua のテーブルは後勝ち)。実際にそれで seeThrough に nil が渡って落ちた。
            L.append('            { a = %d, b = %d, both = %d, needs = "%s" },'
                     % (gidx[q["a"]], gidx[q["b"]], q["both"], q["needs"]))
        L.append('        },')
        L.append('        plates = {')
        pcol = {}
        for q in W.gpairs:
            if q["needs"]:
                pcol[q["needs"]] = q["rgb"]
        for q in W.plates:
            c = pcol.get(q["id"], (1.0, 0.45, 0.2))
            L.append('            { id = "%s", ent = "%s", light = "%s", x = %.3f, z = %.3f, y0 = %.2f, r = %.2f, '
                     'cr = %.3f, cg = %.3f, cb = %.3f },'
                     % (q["id"], q["ent"], q["light"], q["x"], q["z"], q["y0"], q["r"], c[0], c[1], c[2]))
        L.append('        },')
        L.append('        guide = {')
        for q in st.get("guide", ()):
            L.append('            { x = %.2f, z = %.2f, need = "%s" },' % (q[0], q[1], q[2]))
        L.append('        },')
        L.append('        marks = {')
        for q in W.marks:
            L.append('            { ent = "%s", light = "%s", x = %.3f, z = %.3f, '
                     'cr = %.3f, cg = %.3f, cb = %.3f },'
                     % (q["ent"], q["light"], q["x"], q["z"],
                        q["rgb"][0], q["rgb"][1], q["rgb"][2]))
        L.append('        },')
        L.append('        tilts = {')
        for q in W.tilts:
            L.append('            { x = %.3f, y = %.3f, z = %.3f, deg = %.2f, ents = { %s }, extra = { %s } },'
                     % (q["x"], q["y"], q["z"], q["deg"],
                        ", ".join('{ "%s", %.3f, %.3f, %.3f }' % e for e in q["ents"]),
                        ", ".join('"%s"' % e for e in q["extra"])))
        L.append('        },')
        L.append('        fovramps = {')
        for q in W.fovramps:
            L.append('            { axis = "%s", a = %.2f, b = %.2f, f0 = %.1f, f1 = %.1f, '
                     'x0 = %.2f, x1 = %.2f, z0 = %.2f, z1 = %.2f },'
                     % (q["axis"], q["a"], q["b"], q["f0"], q["f1"],
                        q["x0"], q["x1"], q["z0"], q["z1"]))
        L.append('        },')
        L.append('        dynprops = { %s },'
                 % ", ".join('{ ent = "%s", off = %.3f }' % (e[0], e[1]) for e in W.dynprops))
        L.append('        anchors = {')
        for a in W.anchors:
            L.append('            { ent = "%s", x = %.3f, z = %.3f, k = %.3f, d0 = %.3f },'
                     % (a["ent"], a["x"], a["z"], a["k"], a["d0"]))
        L.append('        },')
        fd = st.get("field")
        if fd:
            L.append('        field = { axis = "%s", a = %.2f, b = %.2f, s0 = %.3f, s1 = %.3f, '
                     'x0 = %.2f, x1 = %.2f, z0 = %.2f, z1 = %.2f },'
                     % (fd["axis"], fd["a"], fd["b"], fd["s0"], fd["s1"],
                        fd["x0"], fd["x1"], fd["z0"], fd["z1"]))
        L.append('        dolly = {')
        for d in st.get("dolly", ()):
            L.append('            { x = %.3f, z = %.3f, r = %.2f, fov = %.1f },' % d)
        L.append('        },')
        L.append('        carries = {')
        for c in W.carries:
            L.append('            { ent = "%s", col = "%s", x = %.3f, z = %.3f, yaw = %.1f, h = %.2f },'
                     % (c["ent"], c["col"], c["x"], c["z"], c["yaw"], c["h"]))
        L.append('        },')
        L.append('        sizegates = {')
        for g in W.sizegates:
            L.append('            { id = "%s", x = %.3f, z = %.3f, nx = %.3f, nz = %.3f, hw = %.2f, sf = %.3f, sb = %.3f },'
                     % (g["id"], g["x"], g["z"], g["nx"], g["nz"], g["hw"], g["sf"], g["sb"]))
        L.append('        },')
        L.append('        hint = { %s },' % ", ".join("{ %.2f, %.2f }" % (x, z) for (x, z) in pts))
        # ★startScale: 始まりの部屋の縮尺。v8 は「必ず縮尺 1 の部屋から始まる」前提で
        #   Junction.lua が体を 1.0 で置いていた。第3面は縮尺 2 の大広間から始めるので、
        #   ここを渡さないと 3.6m の部屋に 1.8m の体で立つことになり、関門の判定が全部ずれる。
        L.append('        startScale = %.3f,'
                 % st.get("startScale", W.rooms[st["start"]]["scale"]))
        L.append('        start = "%s", goalRoom = "%s",' % (st["start"], st["goalRoom"]))
        L.append('        spawn = { %.1f, %.1f, %.1f }, teach = %s,'
                 % (st["spawn"][0], st["spawn"][1], st["spawn"][2], ('"%s"' % st["teach"]) if st.get("teach") else "nil"))
        L.append('        cine = {')
        for c in cine:
            L.append('            { %.2f, %.2f, %.2f, %.2f, %.2f, %.2f, %.2f },' % c)
        L.append('        } },')
        lua.append("\n".join(L))

    mpath = MANIFEST
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    missing = [k for k in manifest if not os.path.exists(os.path.join(MODELS, dest_of(k), k + ".gltf"))]
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
