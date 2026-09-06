# -*- coding: utf-8 -*-
"""JUNCTION / stagedemo3 「見たものが、そうなる」— リミナル空間版の生成器。

    python source/gen_liminal.py          (標準ライブラリだけで動く)

出力:
  assets/scenes/stagedemo3.json          シーン本体
  assets/components/Liminal.lua          runtime + 自動生成データ(>>>DATA 〜 <<<DATA)

--------------------------------------------------------------------------
設計の核（前版 v14 への指摘を全部ここで潰している）
  ・**トグル(E)を廃止**。破片は【視点から重なって見えた瞬間に】実体化する。
    見る = 位置と向きの連続量なので、近づくほど輪郭の光と音が育つ。押す物は無い。
  ・**文字を出さない**。HUD は中央の小さな環ひとつだけ(合い具合が満ちる)。
    案内は「非常口の緑」「明るさの差」「床の擦れ跡」でやる。
  ・**リミナル**: 黄ばんだ壁紙 / 芥子色の絨毯 / 落とし天井 / 蛍光灯 / 誰も居ない。
    箱プリミティブ + テクスチャ + uvTiling で組む(Blender 不要 = 反復が速い)。

幾何の規約
  ・箱の UV: +Y面 u=z,v=x / ±Z面 u=x,v=y / ±X面 u=y,v=z。
    1タイル = 2m なので uvTiling は「その面の実寸 / 2」。face 引数で選ぶ。
  ・法線マップは貼らない(grazing で N·L が反転して面が消える既知の罠)。
  ・視点の高さは EYE=1.70 固定(しゃがみ・ジャンプ無し)。継ぎ目の焦点はすべて y=EYE。

継ぎ目(継手)の数学
  焦点 F から見て、破片を F 中心の相似変換で縮めると【投影が完全に一致】する:
      P' = F + k (P - F),  scale' = k scale
  ずれの尺度は「対応点への視線の角度差」の最大値(度)。F に立つと 0 になり、
  離れるほど増える。lock 未満で確定、warn で表示が始まる。
"""
from pathlib import Path
import hashlib, json, math

ROOT = Path(__file__).resolve().parents[1]
ES = []            # entities
CONNS = []         # 継ぎ目の定義(Lua へ渡す)

# ---------------------------------------------------------------- 定数
WT   = 0.30        # 壁厚
EYE  = 1.70        # 目の高さ = 体の中心 0.90 + 0.80
BODY = 0.90        # CharacterController の中心高(足元 0)

TEX = "models/tex/"
T_WALL   = TEX + "lm_wall_col.png"
T_WALL2  = TEX + "lm_wall2_col.png"
T_CARPET = TEX + "lm_carpet_col.png"
T_VINYL  = TEX + "lm_vinyl_col.png"
T_TILEF  = TEX + "lm_tilefloor_col.png"
T_TILEW  = TEX + "lm_tilewall_col.png"
T_CEIL   = TEX + "lm_ceil_col.png"
T_LAMP   = TEX + "lm_lamp_col.png"
T_CONC   = TEX + "lm_conc_col.png"
T_PAINT  = TEX + "lm_paint_col.png"
T_DOOR   = TEX + "lm_door_col.png"
T_METAL  = TEX + "lm_metal_col.png"
T_EXIT   = TEX + "lm_exit_col.png"

INK = "ReconnectInk.hlsl"
WARM = [1.00, 0.96, 0.86]      # 蛍光灯(白に近い。黄色は壁紙が出す)
COOL = [0.76, 0.94, 0.94]      # タイル室(青緑。プールルームの色)
GOLD = [1.00, 0.84, 0.52]      # 継ぎ目の光
GREEN = [0.42, 1.00, 0.66]     # 非常口


def guid(name):
    return hashlib.sha256(("liminal/" + name).encode()).hexdigest()[:16]


def ent(name, pos=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0)):
    e = dict(name=name, guid=guid(name),
             transform=dict(position=[round(v, 4) for v in pos],
                            rotation=[round(v, 4) for v in rot],
                            scale=[round(v, 4) for v in scale]))
    ES.append(e)
    return e


def _tiling(size, face):
    sx, sy, sz = size
    if face == "y":   return sz / 2.0, sx / 2.0      # 上下面: u=z, v=x
    if face == "z":   return sx / 2.0, sy / 2.0      # 前後面: u=x, v=y
    return sy / 2.0, sz / 2.0                        # 左右面: u=y, v=z


def box(name, c, s, tex, face="y", rough=0.92, solid=False, color=None,
        rot=(0, 0, 0), metal=0.0, tile=None):
    """テクスチャ付きの箱。solid=True で静的な当たり判定も付ける。"""
    e = ent(name, c, s, rot)
    e["primitive"] = "box"
    e["material"] = dict(metallic=metal, roughness=rough)
    e["materialTextureOverrides"] = [dict(albedo=tex)]
    u, v = tile if tile else _tiling(s, face)
    e["uvTiling"] = dict(u=round(max(u, 0.01), 4), v=round(max(v, 0.01), 4))
    e["color"] = color or [1, 1, 1]
    if solid:
        e["boxCollider"] = dict(halfExtents=[.5, .5, .5], offset=[0, 0, 0])
        e["rigidBody"] = dict(motionType=0, mass=1, friction=.75, restitution=0,
                              useGravity=False, linearDamping=.02, angularDamping=.01)
    return e


def glow(name, c, s, rgb=GOLD, power=1.0, rot=(0, 0, 0)):
    """自己発光の板/線(ReconnectInk = ライト非依存の単色)。power>1 でブルームに乗る。"""
    e = ent(name, c, s, rot)
    e["primitive"] = "box"
    e["material"] = dict(metallic=0, roughness=1)
    e["shader"] = INK
    e["shaderParams"] = [rgb[0], rgb[1], rgb[2], power]
    e["color"] = [1, 1, 1]
    return e


def hit(name, c, s, rot=(0, 0, 0), kinematic=False):
    """見えない当たり判定だけの箱。kinematic なら Transform で動かせる。"""
    e = ent(name, c, s, rot)
    e["boxCollider"] = dict(halfExtents=[.5, .5, .5], offset=[0, 0, 0])
    e["rigidBody"] = dict(motionType=1 if kinematic else 0, mass=1, friction=.8,
                          restitution=0, useGravity=False, linearDamping=.02,
                          angularDamping=.01)
    return e


def plight(name, p, color=WARM, intensity=6.0, rng=9.0):
    e = ent(name, p)
    e["pointLight"] = dict(color=list(color), intensity=intensity, range=rng,
                           castShadows=False)
    return e


# ---------------------------------------------------------------- 部品
def baseboard(name, c, s, face, color=(0.62, 0.60, 0.55)):
    box(name, c, s, T_PAINT, face, rough=0.55, color=list(color))


def troffer(name, x, y, z, on=True, warm=WARM, intensity=8.0, rng=7.2, size=(1.24, 0.30)):
    """埋め込み蛍光灯。枠(金属) + 乳白カバー(自己発光) + 点光源。
    ★カバーを ReconnectInk にしているのは、ライトの当たり方に左右されず
      『そこが光源だ』と一目で分かるため(リミナルの絵はこれが要)。"""
    w, d = size
    box(name + "_f", (x, y - 0.04, z), (w + 0.16, 0.08, d + 0.16), T_METAL, "y",
        rough=0.45, metal=0.55, color=[0.55, 0.55, 0.53])
    if on:
        glow(name + "_p", (x, y - 0.085, z), (w, 0.03, d), warm, 1.35)
        plight(name + "_l", (x, y - 0.35, z), warm, intensity, rng)
    else:
        box(name + "_p", (x, y - 0.085, z), (w, 0.03, d), T_LAMP, "y",
            rough=0.6, color=[0.30, 0.30, 0.29])


def vent(name, c, s, face):
    box(name, c, s, T_METAL, face, rough=0.5, metal=0.4, color=[0.62, 0.62, 0.60])
    # ルーバー(細い暗い線を数本)
    if face == "x":
        for i in range(4):
            box(name + "_s%d" % i, (c[0] + (0.012 if s[0] > 0 else 0), c[1] - s[1] * 0.3 + s[1] * 0.2 * i, c[2]),
                (s[0] * 0.4, s[1] * 0.07, s[2] * 0.88), T_METAL, "x", color=[0.2, 0.2, 0.2])
    else:
        for i in range(4):
            box(name + "_s%d" % i, (c[0], c[1] - s[1] * 0.3 + s[1] * 0.2 * i, c[2] - s[2] * 0.4),
                (s[0] * 0.88, s[1] * 0.07, s[2] * 0.4), T_METAL, "z", color=[0.2, 0.2, 0.2])


def door_closed(name, x, y, z, w=1.02, h=2.10, axis="z", depth=0.06, inset=0.045):
    """開かない扉(装飾)。枠 + 板 + ノブ。★リミナルは『開かない扉が並ぶ』のが肝。"""
    fw = 0.09
    if axis == "z":
        box(name + "_l", (x - w / 2 - fw / 2, y + h / 2, z), (fw, h + fw, 0.14), T_PAINT, "z", rough=0.5)
        box(name + "_r", (x + w / 2 + fw / 2, y + h / 2, z), (fw, h + fw, 0.14), T_PAINT, "z", rough=0.5)
        box(name + "_t", (x, y + h + fw / 2, z), (w + fw * 2, fw, 0.14), T_PAINT, "z", rough=0.5)
        box(name + "_d", (x, y + h / 2, z - inset), (w, h, depth), T_DOOR, "z", rough=0.55,
            tile=(w / 2, h / 2))
        box(name + "_k", (x + w / 2 - 0.14, y + 1.02, z - inset - depth / 2 - 0.03),
            (0.07, 0.07, 0.06), T_METAL, "z", rough=0.35, metal=0.8, color=[0.75, 0.72, 0.62])
    else:
        sgn = 1.0 if inset >= 0 else -1.0
        box(name + "_l", (x, y + h / 2, z - w / 2 - fw / 2), (0.14, h + fw, fw), T_PAINT, "x", rough=0.5)
        box(name + "_r", (x, y + h / 2, z + w / 2 + fw / 2), (0.14, h + fw, fw), T_PAINT, "x", rough=0.5)
        box(name + "_t", (x, y + h + fw / 2, z), (0.14, fw, w + fw * 2), T_PAINT, "x", rough=0.5)
        box(name + "_d", (x - abs(inset) * sgn, y + h / 2, z), (depth, h, w), T_DOOR, "x", rough=0.55,
            tile=(h / 2, w / 2))
        # ★把手が無いと「扉の絵」に見える。1 個の小さな箱で説得力が変わる
        box(name + "_k", (x - abs(inset) * sgn - sgn * (depth / 2 + 0.03), y + 1.02, z + w / 2 - 0.14),
            (0.06, 0.07, 0.07), T_METAL, "x", rough=0.35, metal=0.8, color=[0.75, 0.72, 0.62])


FRAME_COL = [0.44, 0.46, 0.42]     # 枠は壁より濃い塗装。遠くから輪郭が読めるのが仕事
JW, JD = 0.20, 0.22                # 枠の見付・見込


def frame_half(prefix, sgn, cx, y0, z, dw, dh, glow_power=1.25):
    """扉枠の【左半分 or 右半分】。方立 + 楣の半分 + 沓摺の半分 の『⊐』字。
    ★左右が合わさると閉じた長方形になるのが肝。開いた形(方立と楣だけ)だと
      別々の白い棒にしか見えず、『これは扉枠の片割れだ』が伝わらない(実測)。
    戻り値: (パーツ, 光る線)"""
    hx = dw / 2 + JW / 2
    parts, gl = [], []
    parts.append(box("%s_jamb" % prefix, (cx + sgn * hx, y0 + (dh + JW + 0.10) / 2, z),
                     (JW, dh + JW - 0.10, JD), T_PAINT, "z", rough=0.45, color=FRAME_COL))
    parts.append(box("%s_head" % prefix, (cx + sgn * (dw / 4 + JW / 4), y0 + dh + JW / 2, z),
                     (dw / 2 + JW / 2, JW, JD), T_PAINT, "z", rough=0.45, color=FRAME_COL))
    parts.append(box("%s_sill" % prefix, (cx + sgn * (dw / 4 + JW / 4), y0 + 0.05, z),
                     (dw / 2 + JW / 2, 0.10, JD), T_PAINT, "z", rough=0.45, color=FRAME_COL))
    zg = z + JD / 2 + 0.012
    g1 = glow("%s_g1" % prefix, (cx + sgn * (dw / 2 + 0.015), y0 + (dh + 0.10) / 2, zg),
              (0.03, dh - 0.10, 0.03), GOLD, glow_power)
    g2 = glow("%s_g2" % prefix, (cx + sgn * (dw / 4), y0 + dh - 0.015, zg),
              (dw / 2, 0.03, 0.03), GOLD, glow_power)
    g3 = glow("%s_g3" % prefix, (cx + sgn * (dw / 4), y0 + 0.115, zg),
              (dw / 2, 0.03, 0.03), GOLD, glow_power)
    parts += [g1, g2, g3]
    gl += [g1, g2, g3]
    return parts, gl


def sign_plate(name, x, y, z, color=(1, 1, 1)):
    """非常口の板そのもの(-Z 側から見る)。テクスチャは既に左右反転して作ってある。"""
    e = ent(name, (x, y, z - 0.045), (0.62, 0.26, 0.03))
    e["primitive"] = "box"
    e["material"] = dict(metallic=0, roughness=0.9)
    e["materialTextureOverrides"] = [dict(albedo=T_EXIT)]
    e["uvTiling"] = dict(u=1.0, v=1.0)
    e["color"] = list(color)
    return e


def exit_sign(name, x, y, z, lit=True):
    """非常口。★この作品で緑は出口にしか使わない = 文字なしの唯一の道標。"""
    box(name + "_b", (x, y, z), (0.68, 0.32, 0.06), T_METAL, "z",
        rough=0.5, color=[0.35, 0.35, 0.34])
    sign_plate(name, x, y, z)
    plight(name + "_l", (x, y - 0.30, z - 0.30), GREEN, 0.35 if lit else 0.0, 1.8)


def room_shell(tag, x0, x1, z0, z1, h, ytop, floor_tex, wall_tex, ceil=True,
               y=0.0, floor=True, wall_color=None, ceil_tex=None):
    """内寸 [x0,x1]x[z0,z1]・床 y・天井高 h の箱。壁は外側 WT。"""
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    sx, sz = (x1 - x0), (z1 - z0)
    if floor:
        box(tag + "_flr", (cx, y - WT / 2, cz), (sx + WT * 2, WT, sz + WT * 2), floor_tex, "y",
            rough=0.95, solid=True)
    if ceil:
        box(tag + "_cil", (cx, y + h + WT / 2, cz), (sx + WT * 2, WT, sz + WT * 2),
            ceil_tex or T_CEIL, "y", rough=0.94)
    for sgn, nm in ((-1, "w"), (1, "e")):
        box(tag + "_" + nm, (cx + sgn * (sx / 2 + WT / 2), y + h / 2, cz), (WT, h, sz),
            wall_tex, "x", rough=0.9, solid=True, color=wall_color)
        baseboard(tag + "_" + nm + "b", (cx + sgn * (sx / 2 - 0.02), y + 0.07, cz),
                  (0.05, 0.14, sz), "x")
    return cx, cz, sx, sz


def wall_with_door(tag, axis, at, lo, hi, y, h, dx, dw, dh, tex, color=None, solid=True):
    """開口(幅 dw・高さ dh・中心 dx)を持つ壁。axis='z' なら z=at の壁で lo..hi は x 範囲。"""
    left = (lo, dx - dw / 2)
    right = (dx + dw / 2, hi)
    for i, (a, b) in enumerate((left, right)):
        if b - a < 0.01:
            continue
        c = ((a + b) / 2, y + h / 2, at)
        s = (b - a, h, WT)
        if axis == "x":
            c = (at, y + h / 2, (a + b) / 2)
            s = (WT, h, b - a)
        box("%s_%d" % (tag, i), c, s, tex, "z" if axis == "z" else "x",
            rough=0.9, solid=solid, color=color)
    if dh < h - 0.01:
        c = (dx, y + dh + (h - dh) / 2, at)
        s = (dw, h - dh, WT)
        if axis == "x":
            c = (at, y + dh + (h - dh) / 2, dx)
            s = (WT, h - dh, dw)
        box(tag + "_hd", c, s, tex, "z" if axis == "z" else "x", rough=0.9,
            solid=solid, color=color)


def door_casing(tag, axis, at, dx, y, dw, dh, depth=0.16):
    """開口のケーシング(枠飾り)。開口があると分かるだけで通路の説得力が変わる。"""
    fw = 0.10
    if axis == "z":
        box(tag + "_cl", (dx - dw / 2 - fw / 2, y + dh / 2, at), (fw, dh + fw, depth), T_PAINT, "z", rough=0.5)
        box(tag + "_cr", (dx + dw / 2 + fw / 2, y + dh / 2, at), (fw, dh + fw, depth), T_PAINT, "z", rough=0.5)
        box(tag + "_ct", (dx, y + dh + fw / 2, at), (dw + fw * 2, fw, depth), T_PAINT, "z", rough=0.5)
    else:
        box(tag + "_cl", (at, y + dh / 2, dx - dw / 2 - fw / 2), (depth, dh + fw, fw), T_PAINT, "x", rough=0.5)
        box(tag + "_cr", (at, y + dh / 2, dx + dw / 2 + fw / 2), (depth, dh + fw, fw), T_PAINT, "x", rough=0.5)
        box(tag + "_ct", (at, y + dh + fw / 2, dx), (depth, fw, dw + fw * 2), T_PAINT, "x", rough=0.5)


def locker(name, x, y, z, n=3, axis="z"):
    """ロッカー。無人の建物に『人が居た痕跡』を 1 つだけ置く。"""
    w, h, d = 0.42 * n, 1.86, 0.48
    box(name, (x, y + h / 2, z), (w, h, d) if axis == "z" else (d, h, w), T_METAL,
        "z" if axis == "z" else "x", rough=0.42, metal=0.55, color=[0.52, 0.55, 0.52])
    for i in range(n):
        o = -w / 2 + 0.42 * (i + 0.5)
        c = (x + o, y + h * 0.55, z + (d / 2 + 0.012 if axis == "z" else 0))
        s = (0.36, h * 0.80, 0.02)
        if axis == "x":
            c = (x + d / 2 + 0.012, y + h * 0.55, z + o)
            s = (0.02, h * 0.80, 0.36)
        box(name + "_d%d" % i, c, s, T_METAL, "z" if axis == "z" else "x",
            rough=0.4, metal=0.5, color=[0.44, 0.47, 0.44])


def bench(name, x, y, z, axis="z", L=1.7):
    s = (L, 0.07, 0.44) if axis == "z" else (0.44, 0.07, L)
    box(name, (x, y + 0.44, z), s, T_PAINT, "y", rough=0.5, color=[0.72, 0.70, 0.63])
    for o in (-L / 2 + 0.16, L / 2 - 0.16):
        c = (x + o, y + 0.22, z) if axis == "z" else (x, y + 0.22, z + o)
        box(name + "_l%.2f" % o, c, (0.06, 0.44, 0.34) if axis == "z" else (0.34, 0.44, 0.06),
            T_METAL, "z", rough=0.4, metal=0.6, color=[0.5, 0.5, 0.48])


# ---------------------------------------------------------------- 継ぎ目
class Conn:
    """1 つの継ぎ目。shard() で破片を足すと、その場でシーンの transform を
    【ずれた状態】へ書き換え、実体の値を Lua 用データへ残す。"""

    def __init__(self, cid, focus, lock, warn, center, note=""):
        self.cid = cid
        self.focus = focus
        self.lock = lock
        self.warn = warn
        self.center = center
        self.note = note
        self.shards = []
        self.glows = []
        self.solids = []
        self.movers = []
        self.lights = []
        self.hinges = []
        CONNS.append(self)

    def shard(self, k, ents, glows=()):
        """ents: box()/glow() の戻り値。実体の transform を記録してから k 倍に縮める。"""
        rec = []
        fx, fy, fz = self.focus
        lo = [1e9] * 3
        hi = [-1e9] * 3
        for e in ents:
            p = e["transform"]["position"]
            s = e["transform"]["scale"]
            rec.append(dict(n=e["name"], p=list(p), s=list(s)))
            for i in range(3):
                lo[i] = min(lo[i], p[i] - abs(s[i]) / 2)
                hi[i] = max(hi[i], p[i] + abs(s[i]) / 2)
            e["transform"]["position"] = [round(fx + k * (p[0] - fx), 4),
                                          round(fy + k * (p[1] - fy), 4),
                                          round(fz + k * (p[2] - fz), 4)]
            e["transform"]["scale"] = [round(v * k, 4) for v in s]
        pts = [[lo[0] if i & 1 else hi[0], lo[1] if i & 2 else hi[1], lo[2] if i & 4 else hi[2]]
               for i in range(8)]
        self.shards.append(dict(k=k, ents=rec, pts=pts))
        for g in glows:
            self.glows.append(g["name"])
        return self

    def solid(self, e, hidden_dy=-80.0):
        """接続で出現する当たり判定。生成時は地下へ沈めておく。"""
        p = e["transform"]["position"]
        self.solids.append(dict(n=e["name"], p=list(p)))
        e["transform"]["position"] = [p[0], p[1] + hidden_dy, p[2]]
        return e

    def mover(self, e, to, dur=1.1, delay=0.0):
        """接続で動く物(塞ぎ板が沈む・扉が開く)。to は最終 position。"""
        self.movers.append(dict(n=e["name"], to=[round(v, 4) for v in to],
                                dur=dur, delay=delay))
        return e

    def lamp(self, name, to, dur=0.8, delay=0.0):
        self.lights.append(dict(n=name, to=to, dur=dur, delay=delay))

    def hinge(self, e, pivot, deg, dur=1.3, delay=0.0):
        """接続後に扉が開く。pivot(丁番)まわりに deg 度回す。位置と回転を両方書く。"""
        p = e["transform"]["position"]
        self.hinges.append(dict(n=e["name"], p=[round(v, 4) for v in p],
                                piv=[round(v, 4) for v in pivot], deg=deg, dur=dur, delay=delay))
        return e

    def data(self):
        return dict(id=self.cid, focus=[round(v, 4) for v in self.focus],
                    lock=self.lock, warn=self.warn,
                    center=[round(v, 4) for v in self.center], note=self.note,
                    shards=self.shards, glows=self.glows, solids=self.solids,
                    movers=self.movers, lights=self.lights, hinges=self.hinges)


# ================================================================ ステージ
def build():
    ES.clear(); CONNS.clear()

    # ---- 環境光(屋内なので太陽は影の向きだけ。明るさは点光源で作る) ----
    # ★環境光を下げすぎると「灯りの当たらない面」が真っ黒の板になる(扉枠の側面など)。
    #   跳ね返り光の無いエンジンなので 0.085 を下限として敷く。太陽そのものは消灯(屋内)。
    e = ent("Sun")
    e["directionalLight"] = dict(direction=[-0.25, -0.94, 0.22],
                                 color=[0.86, 0.88, 0.92], intensity=0.0, ambient=0.085)

    # ============================================================ A 入口の廊下
    ZA0, ZA1, HA = -9.0, 14.5, 2.75
    room_shell("A", -1.5, 1.5, ZA0, ZA1, HA, HA, T_CARPET, T_WALL)
    box("A_back", (0, HA / 2, ZA0 - WT / 2), (3.0 + WT * 2, HA, WT), T_WALL, "z", solid=True)
    # ★灯を 4m ごとに全部点けると falloff が重なって『のっぺり明るい廊下』になる。
    #   器具は等間隔に並べ、【点いているのは飛び飛び】にする = 明暗の縞ができる
    for z, on in ((-7.0, True), (-3.0, False), (1.0, True), (5.0, False), (9.0, True), (13.0, True)):
        troffer("A_tr%+03d" % z, 0, HA, z, on=on)
    # 開かない扉(左右)。同じ物が繰り返し出てくるのがリミナル
    door_closed("A_d1", -1.5 + 0.07, 0, -5.0, axis="x", inset=0.045)
    door_closed("A_d2", -1.5 + 0.07, 0, 7.0, axis="x", inset=0.045)
    door_closed("A_d3", 1.5 - 0.07, 0, 2.0, axis="x", inset=-0.045)
    vent("A_v1", (1.44, 2.30, -6.0), (0.05, 0.34, 0.60), "x")
    bench("A_bench", -1.20, 0, 10.6, axis="x")

    # ---- 突き当りの壁(継ぎ目 01 の舞台) ----
    ZW = ZA1                       # 壁の内側の面
    DW, DH = 1.10, 2.20            # 開口
    wall_with_door("A_end", "z", ZW + WT / 2, -1.65, 1.65, 0, HA, 0.0, DW, DH, T_WALL)
    # 開口を塞ぐ板(接続で床下へ沈む)
    panel = box("C1_Panel", (0.0, DH / 2, ZW + WT / 2), (DW, DH, WT - 0.02), T_WALL, "z", solid=True)

    # 継ぎ目 01: 扉枠の左右の半分。近い方(左)が縮んで浮いている
    # ★焦点は廊下の中心から少し左へ外す。中心のままだと「真っ直ぐ歩いていたら
    #   勝手に確定した」になり、位置が効いていることが伝わらない。
    F1 = (-0.52, EYE, 6.30)
    c1 = Conn(1, F1, 1.6, 12.0, (0.0, 1.20, ZW - 0.08), "door")
    ZF = ZW - JD / 2               # 枠は壁の手前に出す
    rp, rg = frame_half("C1_R", +1, 0.0, 0.0, ZF, DW, DH)
    c1.shard(1.0, rp, glows=rg)
    lp, lg = frame_half("C1_L", -1, 0.0, 0.0, ZF, DW, DH)
    c1.shard(0.42, lp, glows=lg)
    c1.mover(panel, (0.0, -DH / 2 - 0.15, ZW + WT / 2), dur=1.5, delay=0.55)
    # 床の擦れ跡(焦点の目印)。案内の文字の代わり
    box("C1_mark", (F1[0], 0.006, F1[2]), (1.5, 0.012, 1.5), T_CARPET, "y",
        rough=0.98, color=[0.72, 0.70, 0.66], tile=(0.75, 0.75))

    # ============================================================ B 事務室
    XB, HB = 8.0, 3.20
    ZB0, ZB1 = ZA1 + WT, 40.0      # 14.8 .. 40
    PZ0, PZ1 = 23.0, 34.5          # 穴
    PY = -5.5
    cx = 0.0
    # 床(手前・奥)と天井・側壁
    box("B_flr0", (0, -WT / 2, (ZB0 + PZ0) / 2), (XB * 2 + WT * 2, WT, PZ0 - ZB0), T_CARPET, "y",
        rough=0.95, solid=True)
    box("B_flr1", (0, -WT / 2, (PZ1 + ZB1) / 2), (XB * 2 + WT * 2, WT, ZB1 - PZ1), T_CARPET, "y",
        rough=0.95, solid=True)
    box("B_cil", (0, HB + WT / 2, (ZB0 + ZB1) / 2), (XB * 2 + WT * 2, WT, ZB1 - ZB0), T_CEIL, "y", rough=0.94)
    for sgn, nm in ((-1, "w"), (1, "e")):
        box("B_" + nm, (sgn * (XB + WT / 2), HB / 2, (ZB0 + ZB1) / 2), (WT, HB, ZB1 - ZB0),
            T_WALL2, "x", rough=0.9, solid=True)
        baseboard("B_" + nm + "b", (sgn * (XB - 0.02), 0.07, (ZB0 + PZ0) / 2), (0.05, 0.14, PZ0 - ZB0), "x")
        baseboard("B_" + nm + "b2", (sgn * (XB - 0.02), 0.07, (PZ1 + ZB1) / 2), (0.05, 0.14, ZB1 - PZ1), "x")
        # 穴の側面(コンクリ)
        box("B_pit" + nm, (sgn * (XB + WT / 2), PY / 2, (PZ0 + PZ1) / 2), (WT, -PY, PZ1 - PZ0),
            T_CONC, "x", rough=0.95, solid=True)
    box("B_pitfloor", (0, PY - WT / 2, (PZ0 + PZ1) / 2), (XB * 2 + WT * 2, WT, PZ1 - PZ0), T_CONC, "y",
        rough=0.96, solid=True)
    box("B_pitn", (0, PY / 2, PZ0 + 0.06), (XB * 2, -PY, 0.12), T_CONC, "z", rough=0.95)
    box("B_pitf", (0, PY / 2, PZ1 - 0.06), (XB * 2, -PY, 0.12), T_CONC, "z", rough=0.95)
    # 穴の縁(危険を伝える濃い帯)
    for z, nm in ((PZ0 - 0.14, "n"), (PZ1 + 0.14, "f")):
        box("B_edge" + nm, (0, 0.012, z), (XB * 2, 0.024, 0.28), T_METAL, "y",
            rough=0.6, metal=0.3, color=[0.30, 0.29, 0.26])
    # 奥の壁(タイル室への扉) と 手前の壁(廊下 A の裏)
    DX2 = 5.5
    wall_with_door("B_end", "z", ZB1 + WT / 2, -XB - WT, XB + WT, 0, HB, DX2, DW, DH, T_WALL2)
    door_casing("B_endc", "z", ZB1 - 0.02, DX2, 0, DW, DH)
    exit_sign("B_exit", DX2, DH + 0.36, ZB1 - 0.10)
    # ★ここに壁を建てない。廊下 A の突き当り(A_end)が【そのまま事務室の手前壁】。
    #   両方建てると同一平面で z ファイティングして、色が場所ごとに入れ替わる。
    #   事務室側は広いので、開口の左右だけ壁紙の色を変える板を薄く重ねる…のもやめる(同じ罠)。
    door_casing("B_nearc", "z", ZB0 + 0.06, 0.0, 0, DW, DH)
    # 照明: 中央(穴の上)は死んでいて暗い = 危険が読める
    for x, z, on in ((-4.5, 17.0, True), (4.5, 17.0, True), (-4.5, 20.6, True), (4.5, 20.6, True),
                     (-4.5, 24.5, False), (4.5, 24.5, False), (0.0, 28.8, True),
                     (-4.5, 32.5, False), (4.5, 32.5, False),
                     (-4.5, 36.4, True), (4.5, 36.4, True), (0.0, 38.8, True)):
        troffer("B_tr%.0f_%.0f" % (x + 9, z), x, HB, z, on=on)
    locker("B_lk1", -6.6, 0, 16.6, 3, axis="x")
    locker("B_lk2", -6.6, 0, 19.4, 2, axis="x")
    bench("B_bench", 6.4, 0, 36.6, axis="x")
    vent("B_v1", (XB - 0.06, 2.6, 18.0), (0.05, 0.4, 0.7), "x")
    vent("B_v2", (-XB + 0.06, 2.6, 36.4), (0.05, 0.4, 0.7), "x")
    # 天井の吸気口(空調が生きている音だけがする建物)
    for x, z in ((-3.0, 19.0), (3.4, 37.2)):
        box("B_cv%.0f_%.0f" % (x + 9, z), (x, HB - 0.02, z), (0.62, 0.05, 0.62), T_METAL, "y",
            rough=0.5, metal=0.4, color=[0.48, 0.48, 0.46])
        for i in range(5):
            box("B_cv%.0f_%.0f_s%d" % (x + 9, z, i), (x, HB - 0.05, z - 0.24 + 0.12 * i),
                (0.56, 0.03, 0.045), T_METAL, "y", color=[0.2, 0.2, 0.2])
    for i, (bx_, bz) in enumerate(((-7.0, 21.6), (-6.4, 21.9), (6.9, 20.0))):
        box("B_bx%d" % i, (bx_, 0.22, bz), (0.44, 0.44, 0.44), T_PAINT, "y", rough=0.85,
            color=[0.66, 0.60, 0.48], solid=True, rot=(0, 18 * i, 0))

    # ---- 継ぎ目 02: 穴を渡す通路 ----
    A2 = (-5.0, 0.0, PZ0 - 0.10)      # 手前の取り付き
    B2 = (5.30, 0.0, PZ1 + 0.10)      # 奥の取り付き
    dxz = (B2[0] - A2[0], B2[2] - A2[2])
    L2 = math.hypot(*dxz)
    YAW2 = math.degrees(math.atan2(dxz[0], dxz[1]))
    F2 = (-6.30, EYE, 18.30)
    c2 = Conn(2, F2, 1.4, 11.0, ((A2[0] + B2[0]) / 2, 0.0, (A2[2] + B2[2]) / 2), "bridge")
    NSEG, WID, THK = 4, 1.70, 0.24
    KS = (1.0, 0.72, 0.53, 0.40)
    for i in range(NSEG):
        t0, t1 = i / NSEG, (i + 1) / NSEG
        cxs = A2[0] + dxz[0] * (t0 + t1) / 2
        czs = A2[2] + dxz[1] * (t0 + t1) / 2
        seg = L2 / NSEG
        parts = []
        deck = box("C2_s%d" % i, (cxs, -THK / 2, czs), (WID, THK, seg - 0.02), T_PAINT, "y",
                   rough=0.8, color=[0.52, 0.52, 0.48], rot=(0, YAW2, 0), tile=(seg / 2, WID / 2))
        parts.append(deck)
        # 縁の光(切断面)。両端に細く
        for sgn in (-1, 1):
            ox = math.cos(math.radians(YAW2)) * sgn * (WID / 2 - 0.03)
            oz = -math.sin(math.radians(YAW2)) * sgn * (WID / 2 - 0.03)
            parts.append(glow("C2_s%de%d" % (i, sgn + 1), (cxs + ox, 0.020, czs + oz),
                              (0.055, 0.04, seg - 0.06), GOLD, 1.25, rot=(0, YAW2, 0)))
        g = [p for p in parts if p["name"].endswith(("e0", "e2"))]
        c2.shard(KS[i], parts, glows=g)
        h = hit("C2_h%d" % i, (cxs, -THK / 2, czs), (WID, THK, seg), rot=(0, YAW2, 0),
                kinematic=True)
        # ★k=1 の断片は最初から本物 = 当たり判定も最初から要る(これが無いと
        #   組み上がった橋の【取り付きだけ】が空洞になって渡れない)
        if KS[i] < 0.999:
            c2.solid(h)
    box("C2_mark", (F2[0], 0.006, F2[2]), (1.6, 0.012, 1.6), T_CARPET, "y", rough=0.98,
        color=[0.72, 0.70, 0.66], tile=(0.8, 0.8))

    # ============================================================ 連絡通路 → C
    ZC0, ZC1, HC = 46.0, 62.0, 6.0
    room_shell("K", DX2 - 1.1, DX2 + 1.1, ZB1 + WT, ZC0, 2.6, 2.6, T_TILEF, T_TILEW)
    troffer("K_tr", DX2, 2.6, 43.4, on=True, warm=COOL, intensity=5.0, rng=7.0)

    # ============================================================ C タイル室
    XC = 7.0
    box("C_flr_s", (0, -WT / 2, (ZC0 + 0.3 + 50.0) / 2), (XC * 2 + WT * 2, WT, 50.0 - ZC0 - 0.3), T_TILEF, "y",
        rough=0.25, solid=True)
    box("C_flr_n", (0, -WT / 2, (59.0 + ZC1) / 2), (XC * 2 + WT * 2, WT, ZC1 - 59.0), T_TILEF, "y",
        rough=0.25, solid=True)
    for sgn in (-1, 1):
        box("C_deck%d" % sgn, (sgn * (3.6 + (XC - 3.6) / 2), -WT / 2, 54.5),
            (XC - 3.6, WT, 9.0), T_TILEF, "y", rough=0.25, solid=True)
    box("C_cil", (0, HC + WT / 2, (ZC0 + ZC1) / 2), (XC * 2 + WT * 2, WT, ZC1 - ZC0), T_CEIL, "y", rough=0.9)
    for sgn, nm in ((-1, "w"), (1, "e")):
        box("C_" + nm, (sgn * (XC + WT / 2), HC / 2, (ZC0 + ZC1) / 2), (WT, HC, ZC1 - ZC0),
            T_TILEW, "x", rough=0.30, solid=True)
    wall_with_door("C_s", "z", ZC0 - WT / 2, -XC - WT, XC + WT, 0, HC, DX2, DW, DH, T_TILEW)
    # 北壁: 高い所に扉(継ぎ目 03 の目的地)
    SILL, DX3 = 3.40, 6.10
    wall_with_door("C_n", "z", ZC1 + WT / 2, -XC - WT, XC + WT, 0, HC, DX3, DW, SILL + DH, T_TILEW)
    box("C_nsill", (DX3, SILL - 0.06, ZC1 + WT / 2), (DW, 0.12, WT), T_TILEW, "z", rough=0.3)
    door_casing("C_nc", "z", ZC1 - 0.02, DX3, SILL, DW, DH)
    exit_sign("C_exit", DX3, SILL + DH + 0.34, ZC1 - 0.10)
    # 空のプール(南が浅い階段、北へ 1.40 下がる)
    PW = 3.6
    steps = [(-0.35, 50.0, 50.9), (-0.70, 50.9, 51.8), (-1.05, 51.8, 52.7)]
    for i, (yy, z0, z1) in enumerate(steps):
        box("C_st%d" % i, (0, yy - 0.12, (z0 + z1) / 2), (PW * 2, 0.24, z1 - z0), T_TILEF, "y",
            rough=0.28, solid=True)
        box("C_stf%d" % i, (0, yy + 0.175, z0 - 0.01), (PW * 2, 0.35, 0.02), T_TILEW, "z", rough=0.3)
    box("C_pool", (0, -1.40 - WT / 2, (52.7 + 59.0) / 2), (PW * 2, WT, 59.0 - 52.7), T_TILEF, "y",
        rough=0.20, solid=True)
    for sgn in (-1, 1):
        box("C_poolw%d" % sgn, (sgn * (PW + 0.06), -0.70, 54.5), (0.12, 1.40, 9.0), T_TILEW, "x",
            rough=0.3, solid=True)
    box("C_pooln", (0, -0.70, 59.0 - 0.06), (PW * 2, 1.40, 0.12), T_TILEW, "z", rough=0.3, solid=True)
    box("C_drain", (0, -1.395, 57.4), (0.34, 0.03, 0.34), T_METAL, "y", rough=0.5, metal=0.6,
        color=[0.30, 0.30, 0.28])
    # 抜けきらなかった水。★rough を下げるだけで灯りが線状に映り込み『濡れている』に見える
    box("C_water", (0, -1.386, 56.6), (5.4, 0.012, 4.2), T_TILEF, "y", rough=0.055, metal=0.15,
        color=[0.52, 0.60, 0.60])
    box("C_water2", (-1.6, -1.386, 53.6), (2.4, 0.012, 1.8), T_TILEF, "y", rough=0.07, metal=0.12,
        color=[0.56, 0.63, 0.62])
    # プールの縁(見切り)
    for sgn in (-1, 1):
        box("C_lip%d" % sgn, (sgn * (PW + 0.16), 0.02, 54.5), (0.20, 0.05, 9.2), T_TILEW, "y", rough=0.28)
    box("C_lipn", (0, 0.02, 59.10), (PW * 2 + 0.4, 0.05, 0.20), T_TILEW, "y", rough=0.28)
    box("C_lips", (0, 0.02, 49.90), (PW * 2 + 0.4, 0.05, 0.20), T_TILEW, "y", rough=0.28)
    for x, z in ((-4.9, 48.6), (4.9, 48.6), (-4.9, 55.5), (4.9, 55.5), (0.0, 60.6), (0.0, 47.2)):
        troffer("C_tr%.0f_%.0f" % (x + 9, z), x, HC, z, on=(x, z) != (-4.9, 55.5),
                warm=COOL, intensity=8.5, rng=13.0, size=(1.30, 0.32))

    # ---- 継ぎ目 03: 階段 ----
    RISE, RUN, SW = 0.28333, 0.80, 1.70
    SX, SZ0 = DX3, 50.0
    F3 = (-5.40, EYE, 53.60)
    c3 = Conn(3, F3, 2.2, 13.0, (SX, 1.8, 55.0), "stair")
    groups = [(0, 3, 1.0), (3, 7, 0.62), (7, 10, 0.46), (10, 12, 0.355)]
    si = 0
    for (a, b, k) in groups:
        parts, gl = [], []
        for i in range(a, b):
            top = RISE * (i + 1)
            z0 = SZ0 + RUN * i
            parts.append(box("C3_s%d" % i, (SX, top - 0.11, z0 + RUN / 2), (SW, 0.22, RUN),
                             T_PAINT, "y", rough=0.6, color=[0.50, 0.52, 0.48]))
            parts.append(box("C3_r%d" % i, (SX, top - 0.22 - RISE / 2 + 0.055, z0 + 0.02),
                             (SW, RISE, 0.04), T_TILEW, "z", rough=0.3))
            g = glow("C3_e%d" % i, (SX - SW / 2 + 0.03, top + 0.005, z0 + RUN / 2),
                     (0.055, 0.04, RUN - 0.04), GOLD, 1.25)
            parts.append(g); gl.append(g)
            si += 1
        c3.shard(k, parts, glows=gl)
        for i in range(a, b):
            top = RISE * (i + 1)
            z0 = SZ0 + RUN * i
            h = hit("C3_h%d" % i, (SX, top - 0.11, z0 + RUN / 2), (SW, 0.22, RUN), kinematic=True)
            if k < 0.999:
                c3.solid(h)
    # 上の踊り場(これは最初から実在する = 目的地が見えている)
    # ★最上段の先端 z=59.6 とぴったり接すること。0.2m でも空くと『登れるのに入れない』
    #   という一番たちの悪い詰みになる(シミュレータで実際に踏んだ)。
    ZLAND0 = SZ0 + RUN * 12
    box("C_land", (SX, SILL - 0.11, (ZLAND0 + ZC1) / 2), (SW + 0.4, 0.22, ZC1 - ZLAND0),
        T_PAINT, "y", rough=0.6, color=[0.70, 0.70, 0.66], solid=True)
    box("C_landf", (SX, SILL - 0.60, ZLAND0 + 0.02), (SW + 0.4, 1.0, 0.16), T_TILEW, "z", rough=0.3)
    box("C3_mark", (F3[0], 0.014, F3[2]), (1.5, 0.014, 1.5), T_TILEF, "y", rough=0.30,
        color=[0.78, 0.80, 0.78], tile=(0.75, 0.75))

    # ============================================================ D 上階の廊下(A の再演)
    ZD0, ZD1, YD, HD = ZC1 + WT, 80.0, SILL, 2.75
    room_shell("D", DX3 - 1.5, DX3 + 1.5, ZD0, ZD1, HD, HD, T_CARPET, T_WALL, y=YD)
    for z in (64.5, 68.5, 72.5, 76.5):
        troffer("D_tr%.0f" % z, DX3, YD + HD, z, on=(z != 76.5))
    door_closed("D_d1", DX3 - 1.5 + 0.07, YD, 67.0, axis="x", inset=0.045)
    door_closed("D_d2", DX3 + 1.5 - 0.07, YD, 71.5, axis="x", inset=-0.045)
    bench("D_bench", DX3 - 1.20, YD, 74.6, axis="x")
    vent("D_v1", (DX3 + 1.44, YD + 2.30, 65.0), (0.05, 0.34, 0.60), "x")

    # ---- 継ぎ目 04: 出口 ----
    ZE = ZD1
    wall_with_door("D_end", "z", ZE + WT / 2, DX3 - 1.65, DX3 + 1.65, YD, HD, DX3, DW, DH, T_WALL)
    epanel = box("C4_Panel", (DX3, YD + DH / 2, ZE + WT / 2), (DW, DH, WT - 0.02), T_WALL, "z", solid=True)
    # 扉の向こうの白い部屋
    box("E_flr", (DX3, YD - WT / 2, 82.75), (4.0, WT, 4.9), T_PAINT, "y", rough=0.9, solid=True)
    box("E_cil", (DX3, YD + 3.2, 82.6), (4.0, WT, 5.2), T_PAINT, "y", rough=0.9)
    for sgn in (-1, 1):
        box("E_w%d" % sgn, (DX3 + sgn * 2.0, YD + 1.6, 82.6), (WT, 3.2, 5.2), T_PAINT, "x", rough=0.9, solid=True)
    box("E_back", (DX3, YD + 1.6, 85.1), (4.3, 3.2, WT), T_PAINT, "z", rough=0.9, solid=True)
    glow("E_glow", (DX3, YD + 1.5, 84.9), (3.6, 2.9, 0.05), [1.0, 0.98, 0.94], 1.05)
    plight("E_l1", (DX3, YD + 2.2, 83.6), [1.0, 0.98, 0.94], 9.0, 7.5)

    # ★廊下 A と同じ「中心から少し左」。最初の継ぎ目で覚えた事をそのまま使わせる
    F4 = (DX3 - 0.55, YD + EYE, 69.20)
    c4 = Conn(4, F4, 2.0, 13.0, (DX3, YD + 1.2, ZE - 0.1), "exit")
    ZF4 = ZE - 0.08
    # 実在するのは標識だけ(消灯している = ここが出口だと薄く分かる)
    sgn_b = box("C4_signb", (DX3, YD + DH + 0.36, ZF4 - 0.02), (0.68, 0.32, 0.06), T_METAL, "z",
                rough=0.5, color=[0.35, 0.35, 0.34])
    sgn = sign_plate("C4_sign", DX3, YD + DH + 0.36, ZF4 - 0.02, color=(0.34, 0.38, 0.35))
    plight("C4_sign_l", (DX3, YD + DH + 0.06, ZF4 - 0.35), GREEN, 0.0, 1.8)
    c4.shard(1.0, [sgn_b, sgn])
    # 左右の枠と扉板が別々の奥行きから寄ってくる(4 つが一度に噛み合うのが最後の見せ場)
    lp, lg_ = frame_half("C4_L", -1, DX3, YD, ZF4, DW, DH)
    c4.shard(0.55, lp, glows=lg_)
    rp, rg_ = frame_half("C4_R", +1, DX3, YD, ZF4, DW, DH)
    c4.shard(0.35, rp, glows=rg_)
    leaf = box("C4_Leaf", (DX3, YD + DH / 2, ZF4 - 0.12), (DW - 0.04, DH - 0.04, 0.06), T_DOOR, "z",
               rough=0.55, tile=(DW / 2, DH / 2))
    knob = box("C4_Knob", (DX3 + DW / 2 - 0.16, YD + 1.02, ZF4 - 0.19), (0.07, 0.07, 0.07), T_METAL, "z",
               rough=0.35, metal=0.8, color=[0.75, 0.72, 0.62])
    lgk = glow("C4_Lfink", (DX3, YD + 0.03, ZF4 - 0.12), (DW - 0.06, 0.03, 0.03), GOLD, 1.25)
    c4.shard(0.72, [leaf, knob, lgk], glows=[lgk])
    c4.mover(epanel, (DX3, YD - DH / 2 - 0.25, ZE + WT / 2), dur=1.6, delay=0.5)
    c4.lamp("C4_sign", 1.0, dur=0.6, delay=0.35)
    # ★扉は【開く】。閉じたままだと『見た目は閉扉なのにすり抜けられる』一番悪い絵になる
    HINGE = (DX3 - DW / 2, YD + DH / 2, ZF4 - 0.12)
    c4.hinge(leaf, HINGE, -82.0, dur=1.5, delay=0.9)
    c4.hinge(knob, HINGE, -82.0, dur=1.5, delay=0.9)
    c4.hinge(lgk, HINGE, -82.0, dur=1.5, delay=0.9)
    # ★最後だけ床の目印を置かない。ここまでで『立つ位置が世界を決める』は伝わっている

    # ============================================================ プレイヤー・UI
    p = ent("LM_Player", (0.0, BODY, -6.0))
    p["characterController"] = dict(radius=0.34, halfHeight=0.56, offset=[0, 0, 0],
                                    stepHeight=0.32, jumpSpeed=0.0, gravityScale=1.0,
                                    mass=70, maxSlopeDeg=52)
    cam = ent("LM_Camera", (0.0, EYE, -6.0))
    cam["camera"] = dict(fovDegrees=72, nearClip=0.035, farClip=180, projection=0, isActive=True)
    lg = ent("LM_Logic")
    lg["luaScript"] = dict(enabled=True, scriptPath="components/Liminal.lua")

    canvas = ent("LM_HUD")
    canvas["uiCanvas"] = dict(refWidth=1600, refHeight=900, scaleMode=0, sortOrder=0, visible=True)

    def ui(name, amin, amax, omin, omax, order=0):
        e = ent(name)
        e["parentGuid"] = canvas["guid"]
        e["uiRect"] = dict(anchorMin=list(amin), anchorMax=list(amax), pivot=[0.5, 0.5],
                           offsetMin=list(omin), offsetMax=list(omax), visible=True, order=order)
        return e

    r = ui("LM_Ring", (0.5, 0.5), (0.5, 0.5), (-26, -26), (26, 26), 1)
    r["uiImage"] = dict(texturePath="", color=[1.0, 0.86, 0.55, 0.0], shape=2, ringThickness=2.6,
                        fillAmount=0.0, fillDir=4, fillOrigin=0.0, raycastBlock=False)
    d = ui("LM_Dot", (0.5, 0.5), (0.5, 0.5), (-2.5, -2.5), (2.5, 2.5), 2)
    d["uiImage"] = dict(texturePath="", color=[0.90, 0.91, 0.88, 0.34], shape=1, raycastBlock=False)
    h = ui("LM_Hint", (0, 0), (1, 0), (0, 790), (0, 830), 0)
    h["uiText"] = dict(text="WASD  歩く      マウス  見る", fontSize=21,
                       color=[0.92, 0.91, 0.85, 0.55], alignH=1, alignV=1, wrap=False,
                       outlineWidth=0.8, outlineColor=[0.03, 0.03, 0.03, 0.55])
    t = ui("LM_End", (0, 0.5), (1, 0.5), (0, -30), (0, 30), 3)
    # ★終わりは白い部屋で出す = 文字は【暗色】。明色 + 黒縁だと縁だけが残って潰れる
    t["uiText"] = dict(text="", fontSize=42, color=[0.13, 0.13, 0.12, 0.0], alignH=1, alignV=1,
                       wrap=False, outlineWidth=0.0, outlineColor=[1, 1, 1, 0.0])

    return dict(
        version=1, entities=ES, shadows=False,
        skybox=dict(drawSkybox=False, envMapPath="", iblIntensity=0.0, skyboxIntensity=0.0),
        ssao=dict(enabled=True, radius=0.55, intensity=0.85, power=1.5, bias=0.02,
                  blur=True, sampleCount=16),
        contactShadow=dict(enabled=True, intensity=1.0, rayLength=0.30, steps=16,
                           thickness=0.20, bias=0.02, maxDistance=40.0, fadeDistance=8.0),
        ssgi=dict(enabled=False), ssr=dict(enabled=False), taa=dict(enabled=False),
        volumetricFog=dict(enabled=True, density=0.010, albedo=[1.0, 0.98, 0.94],
                           ambient=[0.030, 0.029, 0.026], anisotropy=0.25, distance=70.0,
                           depthDistribution=2.0, heightFalloff=0.02, heightRef=0.0,
                           lightScattering=True, sunIntensity=0.0, temporal=True,
                           temporalBlend=0.08, extendBeyondRange=True),
        postProcess=dict(enabled=True, tonemapper=1, exposureOn=True, exposure=1.06,
                         bloomOn=True, bloom=0.20, bloomThreshold=1.05, bloomKnee=0.55,
                         bloomRadius=0.72, fxaaOn=True, debandOn=True,
                         vignetteOn=True, vignette=0.30, vignetteRadius=0.62,
                         vignetteSoftness=0.55, grainOn=True, grain=0.035, grainSize=1.0,
                         saturationOn=True, saturation=1.07,
                         warmthOn=True, warmth=0.05, contrastOn=True, contrast=1.04),
    )


# ---------------------------------------------------------------- 書き出し
def lua_value(v, indent=0):
    sp = "  " * indent
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(round(float(v), 4))
    if isinstance(v, str):
        return '"%s"' % v.replace('"', '\\"')
    if isinstance(v, (list, tuple)):
        if v and all(isinstance(x, (int, float)) for x in v):
            return "{" + ",".join(repr(round(float(x), 4)) for x in v) + "}"
        return "{\n" + ",\n".join(sp + "  " + lua_value(x, indent + 1) for x in v) + "\n" + sp + "}"
    if isinstance(v, dict):
        items = []
        for k, val in v.items():
            items.append("%s  %s=%s" % (sp, k, lua_value(val, indent + 1)))
        return "{\n" + ",\n".join(items) + "\n" + sp + "}"
    raise TypeError(type(v))


def main():
    data = build()
    scene = ROOT / "assets/scenes/stagedemo3.json"
    scene.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    runtime = (ROOT / "source/liminal_runtime.lua").read_text(encoding="utf-8")
    block = "-- >>>DATA (gen_liminal.py が書く。手で触らない)\nCONNS = " + \
            lua_value([c.data() for c in CONNS]) + "\n-- <<<DATA\n"
    a = runtime.index("-- >>>DATA")
    b = runtime.index("-- <<<DATA") + len("-- <<<DATA\n")
    out = runtime[:a] + block + runtime[b:]
    (ROOT / "assets/components/Liminal.lua").write_text(out, encoding="utf-8")

    ncol = sum(1 for e in ES if "rigidBody" in e)
    nlit = sum(1 for e in ES if "pointLight" in e)
    print("stagedemo3(liminal): %d entities / %d colliders / %d lights / %d joints"
          % (len(ES), ncol, nlit, len(CONNS)))
    for c in CONNS:
        print("  conn%d focus=%s lock=%.1fdeg shards=%d solids=%d"
              % (c.cid, c.focus, c.lock, len(c.shards), len(c.solids)))


if __name__ == "__main__":
    main()
