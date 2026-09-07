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

# 到達点(落ちた時の戻り先)。z が at を越えると次へ進む。y は体の中心の高さ
CHECKS = [
    dict(x=0.00, y=0.90, z=-6.0, at=-1e9),
    dict(x=0.00, y=0.90, z=16.6, at=15.6),
    dict(x=-4.60, y=0.90, z=17.0, at=17.6),     # ★F2 の上に置かない(戻った瞬間に解ける)
    dict(x=5.30, y=0.90, z=36.4, at=35.6),
    dict(x=5.50, y=0.90, z=47.6, at=46.6),
    dict(x=6.10, y=4.30, z=63.6, at=62.6),
    dict(x=6.10, y=4.30, z=82.0, at=80.6),      # 白い部屋
    dict(x=6.10, y=4.30, z=87.5, at=86.2),      # 大ホール
    dict(x=6.00, y=4.30, z=106.6, at=105.2),    # 前室
    dict(x=7.00, y=4.30, z=111.0, at=109.6),    # 折り返しの間
    dict(x=22.50, y=4.30, z=126.0, at=124.8),   # 多義の間(溝の手前)
    dict(x=22.00, y=4.30, z=144.0, at=142.8),   # 揺れの間
    dict(x=22.00, y=6.70, z=158.0, at=156.8),   # 終わりの間
]
GOAL = dict(x=22.0, y=5.80, z=163.82, r=0.62, need=10)

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


def frame_half_x(prefix, sgn, cz, y0, x, dw, dh, glow_power=1.25):
    """frame_half の東西壁版(開口の幅が z 方向)。枠は -x 側(部屋の内側)へ出る。"""
    hz = dw / 2 + JW / 2
    parts, gl = [], []
    parts.append(box("%s_jamb" % prefix, (x, y0 + (dh + JW + 0.10) / 2, cz + sgn * hz),
                     (JD, dh + JW - 0.10, JW), T_PAINT, "x", rough=0.45, color=FRAME_COL))
    parts.append(box("%s_head" % prefix, (x, y0 + dh + JW / 2, cz + sgn * (dw / 4 + JW / 4)),
                     (JD, JW, dw / 2 + JW / 2), T_PAINT, "x", rough=0.45, color=FRAME_COL))
    parts.append(box("%s_sill" % prefix, (x, y0 + 0.05, cz + sgn * (dw / 4 + JW / 4)),
                     (JD, 0.10, dw / 2 + JW / 2), T_PAINT, "x", rough=0.45, color=FRAME_COL))
    xg = x - JD / 2 - 0.012
    g1 = glow("%s_g1" % prefix, (xg, y0 + (dh + 0.10) / 2, cz + sgn * (dw / 2 + 0.015)),
              (0.03, dh - 0.10, 0.03), GOLD, glow_power)
    g2 = glow("%s_g2" % prefix, (xg, y0 + dh - 0.015, cz + sgn * (dw / 4)),
              (0.03, 0.03, dw / 2), GOLD, glow_power)
    g3 = glow("%s_g3" % prefix, (xg, y0 + 0.115, cz + sgn * (dw / 4)),
              (0.03, 0.03, dw / 2), GOLD, glow_power)
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


def exit_sign_x(name, x, y, z, lit=True):
    """東西の壁に付ける非常口(面は -x を向く)。★箱の -Z 面を -X へ向けるには yaw=+90。"""
    e = box(name + "_b", (x, y, z), (0.68, 0.32, 0.06), T_METAL, "z", rough=0.5,
            color=[0.35, 0.35, 0.34])
    e["transform"]["rotation"] = [0, 90, 0]
    p = sign_plate(name, x, y, z)
    p["transform"]["position"] = [x - 0.045, y, z]
    p["transform"]["rotation"] = [0, 90, 0]
    plight(name + "_l", (x - 0.30, y - 0.30, z), GREEN, 0.35 if lit else 0.0, 1.8)


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


def shell(tag, x0, x1, z0, z1, h, floor_tex, wall_tex, y=0.0, walls="wens",
          ceil=True, ceil_tex=None, wall_color=None, floor=True, base=True):
    """room_shell の自由版。walls に建てたい壁の頭文字を並べる(w/e/n/s)。
    開口のある面は walls から抜いて wall_with_door で建てること。"""
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    sx, sz = (x1 - x0), (z1 - z0)
    if floor:
        box(tag + "_flr", (cx, y - WT / 2, cz), (sx + WT * 2, WT, sz + WT * 2), floor_tex, "y",
            rough=0.95, solid=True)
    if ceil:
        box(tag + "_cil", (cx, y + h + WT / 2, cz), (sx + WT * 2, WT, sz + WT * 2),
            ceil_tex or T_CEIL, "y", rough=0.94)
    for ch, sgn in (("w", -1), ("e", 1)):
        if ch in walls:
            box(tag + "_" + ch, (cx + sgn * (sx / 2 + WT / 2), y + h / 2, cz), (WT, h, sz + WT * 2),
                wall_tex, "x", rough=0.9, solid=True, color=wall_color)
            if base:
                baseboard(tag + "_" + ch + "b", (cx + sgn * (sx / 2 - 0.02), y + 0.07, cz),
                          (0.05, 0.14, sz), "x")
    for ch, sgn in (("s", -1), ("n", 1)):
        if ch in walls:
            box(tag + "_" + ch, (cx, y + h / 2, cz + sgn * (sz / 2 + WT / 2)), (sx, h, WT),
                wall_tex, "z", rough=0.9, solid=True, color=wall_color)
            if base:
                baseboard(tag + "_" + ch + "b", (cx, y + 0.07, cz + sgn * (sz / 2 - 0.02)),
                          (sx, 0.14, 0.05), "z")
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
        self.shines = []        # 接続後に光らせる面
        self.excl = []          # 同じ破片を取り合う継ぎ目(多義)の相手
        CONNS.append(self)

    def shard(self, k, ents, glows=(), osc=None):
        """ents: box()/glow() の戻り値。実体の transform を記録してから k 倍に縮める。
        osc=(dx,dy,dz,周期) を渡すと、ずれた姿勢で【揺れる】(合う姿勢で速度 0)。"""
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
        d = dict(k=k, ents=rec, pts=pts)
        if osc:
            d["osc"] = list(osc)
        self.shards.append(d)
        for g in glows:
            self.glows.append(g["name"])

    def shard_display(self, k, ents, glows=()):
        """★多義の破片用。ents の【今の transform を "浮いている姿" とみなし】、
        この焦点・この k から見て一致する【実体】を逆算して記録する:
            P = F + (D - F) / k
        同じ破片に対して別の (F, k) で 2 回呼べば、**同じ浮遊物が 2 通りの実体になる**。
        エンティティの transform は触らない(既に浮遊姿勢なので)。"""
        rec = []
        fx, fy, fz = self.focus
        lo = [1e9] * 3
        hi = [-1e9] * 3
        for e in ents:
            d = e["transform"]["position"]
            ds = e["transform"]["scale"]
            p = [round(fx + (d[0] - fx) / k, 4), round(fy + (d[1] - fy) / k, 4),
                 round(fz + (d[2] - fz) / k, 4)]
            s = [round(v / k, 4) for v in ds]
            rec.append(dict(n=e["name"], p=p, s=s))
            for i in range(3):
                lo[i] = min(lo[i], p[i] - abs(s[i]) / 2)
                hi[i] = max(hi[i], p[i] + abs(s[i]) / 2)
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

    def shine(self, e, rgb, power):
        """接続後に自己発光の板を点ける(ReconnectInk の shaderParams を差し替える)。"""
        self.shines.append(dict(n=e["name"], c=[rgb[0], rgb[1], rgb[2], power]))
        return e

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
                    movers=self.movers, lights=self.lights, hinges=self.hinges,
                    shines=self.shines, excl=self.excl)


# ================================================================ 第二幕（継ぎ目 5〜10）
def act2(Y2, DW, DH):
    """白い部屋の奥から続く別棟。同じ 1 つの規則で【思考の型】を変えた 6 つの継ぎ目。

      5  巨大 × 極小   目の前の 40cm が、5m の扉の欠けた一枚になる
      6  振り返る       出口は【入って来た側】に組み上がる
      7/8 多義          同じ浮遊物が、立つ場所によって【別々の橋】になる（片方を選ぶと他方は消える）
      9  揺れる         漂う破片が合う姿勢で止まる一瞬を待つ
      10 自立する戸口   何にも寄りかかっていない扉が空間に建つ
    """
    EYEY = Y2 + EYE

    # ============================================================ F 大ホール（機械室）
    HX0, HX1, HZ0, HZ1, HH = -2.0, 14.0, 85.5, 104.0, 7.0
    shell("H1", HX0, HX1, HZ0, HZ1, HH, T_CONC, T_CONC, y=Y2, walls="we",
          ceil_tex=T_CONC, base=False)
    wall_with_door("H1_s", "z", HZ0 - WT / 2, HX0 - WT, HX1 + WT, Y2, HH, 6.1, DW, DH, T_CONC)
    # 北壁: 貨物シャッターの大開口(5.0 x 4.2)
    SHW, SHH, SHX = 5.0, 4.2, 6.0
    wall_with_door("H1_n", "z", HZ1 + WT / 2, HX0 - WT, HX1 + WT, Y2, HH, SHX, SHW, SHH, T_CONC)
    for x in (0.5, 11.5):
        for z in (90.0, 99.0):
            box("H1_col%.0f_%.0f" % (x, z), (x, Y2 + HH / 2, z), (0.7, HH, 0.7), T_CONC, "x",
                rough=0.92, solid=True)
    for z in (88.5, 94.0, 99.5):                       # 天井の梁
        box("H1_bm%.0f" % z, (6.0, Y2 + HH - 0.35, z), (16.6, 0.7, 0.45), T_CONC, "z", rough=0.9)
    for x, z, on in ((1.5, 89.0, True), (10.5, 89.0, False), (1.5, 96.0, False),
                     (10.5, 96.0, True), (6.0, 101.5, True)):
        # 吊り下げの工場灯(笠 + 光る面)
        box("H1_lp%.0f_%.0f" % (x, z), (x, Y2 + HH - 1.15, z), (0.10, 1.4, 0.10), T_METAL, "x",
            rough=0.5, metal=0.6, color=[0.35, 0.35, 0.33])
        box("H1_ls%.0f_%.0f" % (x, z), (x, Y2 + HH - 1.95, z), (0.86, 0.22, 0.86), T_METAL, "y",
            rough=0.45, metal=0.6, color=[0.42, 0.42, 0.40])
        if on:
            glow("H1_lg%.0f_%.0f" % (x, z), (x, Y2 + HH - 2.09, z), (0.62, 0.05, 0.62), WARM, 1.5)
            plight("H1_ll%.0f_%.0f" % (x, z), (x, Y2 + HH - 2.4, z), WARM, 9.0, 11.0)
    for i, (bx_, bz) in enumerate(((-0.9, 92.5), (-0.2, 92.9), (12.6, 97.0), (12.0, 97.4))):
        box("H1_bx%d" % i, (bx_, Y2 + 0.32, bz), (0.64, 0.64, 0.64), T_PAINT, "y", rough=0.9,
            color=[0.58, 0.54, 0.44], solid=True, rot=(0, 21 * i, 0))
    exit_sign("H1_exit", SHX, Y2 + SHH + 0.42, HZ1 - 0.10)

    # ---- 継ぎ目 05: 5m のシャッターの欠けた一枚 ----
    F5 = (6.6, EYEY, 92.0)
    c5 = Conn(5, F5, 4.2, 26.0, (SHX, Y2 + SHH / 2, HZ1 - 0.2), "shutter")
    ZS = HZ1 - 0.16
    QW, QH = SHW / 2, SHH / 2
    panels = []
    for qx, qy, nm in ((-1, -1, "ll"), (1, -1, "lr"), (1, 1, "ur")):
        p = box("C5_" + nm, (SHX + qx * QW / 2, Y2 + QH / 2 + (0 if qy < 0 else QH), ZS),
                (QW - 0.03, QH - 0.03, 0.14), T_METAL, "z", rough=0.5, metal=0.55,
                color=[0.46, 0.46, 0.44], solid=True, tile=(QW / 2, QH / 2))
        panels.append(p)
        for r in range(4):                                   # 横のリブ(シャッターらしさ)
            box("C5_%s_r%d" % (nm, r),
                (SHX + qx * QW / 2, Y2 + (0 if qy < 0 else QH) + 0.26 + r * 0.5, ZS - 0.09),
                (QW - 0.12, 0.07, 0.05), T_METAL, "z", rough=0.45, metal=0.6,
                color=[0.34, 0.34, 0.32])
    # 欠けているのは【左上】。高い所なので、穴が空いていても通り抜けとは読まれない
    miss = box("C5_ul", (SHX - QW / 2, Y2 + QH + QH / 2, ZS), (QW - 0.03, QH - 0.03, 0.14),
               T_METAL, "z", rough=0.5, metal=0.55, color=[0.46, 0.46, 0.44],
               tile=(QW / 2, QH / 2))
    ribs = []
    for r in range(4):                                       # 欠けた一枚にも同じリブを付ける
        ribs.append(box("C5_ul_r%d" % r, (SHX - QW / 2, Y2 + QH + 0.26 + r * 0.5, ZS - 0.09),
                        (QW - 0.12, 0.07, 0.05), T_METAL, "z", rough=0.45, metal=0.6,
                        color=[0.34, 0.34, 0.32]))
    mg = []
    for i, (ox, oy, sx_, sy_) in enumerate(((0, QH / 2 - 0.02, QW - 0.03, 0.05),
                                            (QW / 2 - 0.02, 0, 0.05, QH - 0.03))):
        mg.append(glow("C5_ulg%d" % i, (SHX - QW / 2 + ox, Y2 + QH + QH / 2 + oy, ZS - 0.085),
                       (sx_, sy_, 0.05), GOLD, 1.25))
    c5.shard(1.0, panels)
    c5.shard(0.16, [miss] + ribs + mg, glows=mg)
    for p in panels + [miss] + ribs + mg:                          # 揃うとシャッターが巻き上がる
        c5.mover(p, (p["transform"]["position"][0], p["transform"]["position"][1] + SHH + 0.15,
                     p["transform"]["position"][2]), dur=2.2, delay=0.5)
    # ★破片は【照らさないと真っ黒の穴に見える】。合っているのに合っていないように見えるので致命的。
    #   焦点の斜め後ろから当てる灯りを 1 つ足す(床の目印も一緒に見える)
    plight("C5_fill", (6.0, Y2 + 5.0, 89.6), WARM, 8.0, 12.0)
    box("C5_mark", (F5[0], Y2 + 0.008, F5[2]), (1.5, 0.016, 1.5), T_CONC, "y", rough=0.9,
        color=[0.72, 0.72, 0.70], tile=(0.75, 0.75))

    # ============================================================ V 前室（材質が事務所へ戻る）
    shell("V1", 3.0, 9.0, HZ1 + WT, 108.5, 3.0, T_CARPET, T_WALL, y=Y2, walls="we")
    wall_with_door("V1_n", "z", 108.5 + WT / 2, 2.7, 9.3, Y2, 3.0, 6.0, DW, DH, T_WALL)
    troffer("V1_tr", 6.0, Y2 + 3.0, 106.4, on=True)

    # ============================================================ T 折り返しの間
    TX0, TX1, TZ0, TZ1, TH = 2.0, 18.0, 108.8, 122.0, 3.6
    shell("T1", TX0, TX1, TZ0, TZ1, TH, T_CARPET, T_WALL, y=Y2, walls="wn")
    wall_with_door("T1_s", "z", TZ0 - WT / 2, TX0 - WT, TX1 + WT, Y2, TH, 6.0, DW, DH, T_WALL)
    # 東壁: ここに【出口の扉】が組み上がる(入って来た側 = 振り返らないと見えない)
    TDZ = 110.5
    wall_with_door("T1_e", "x", TX1 + WT / 2, TZ0 - WT, TZ1 + WT, Y2, TH, TDZ, DW, DH, T_WALL)
    for x, z, on in ((6.0, 112.0, True), (13.0, 112.0, True), (6.0, 118.5, True),
                     (13.0, 118.5, False), (16.0, 110.5, True)):
        troffer("T1_tr%.0f_%.0f" % (x, z), x, Y2 + TH, z, on=on)
    locker("T1_lk", 3.0, Y2, 116.0, 3, axis="x")
    bench("T1_bench", 16.6, Y2, 119.0, axis="x")
    door_closed("T1_d1", 2.0 + 0.07, Y2, 120.0, axis="x", inset=0.045)
    # ★出口の標識だけ先に点いている。振り返らせるための唯一の手掛かり
    exit_sign_x("T1_exit", TX1 - 0.16, Y2 + DH + 0.42, TDZ)

    F6 = (7.4, EYEY, 118.6)
    c6 = Conn(6, F6, 1.0, 11.0, (TX1 - 0.2, Y2 + 1.2, TDZ), "behind")
    ZF6 = TX1 - 0.11
    rp, rg = frame_half_x("C6_R", +1, TDZ, Y2, ZF6, DW, DH)
    c6.shard(1.0, rp, glows=rg)
    lp, lg = frame_half_x("C6_L", -1, TDZ, Y2, ZF6, DW, DH)
    c6.shard(0.46, lp, glows=lg)
    panel6 = box("C6_Panel", (TX1 + WT / 2, Y2 + DH / 2, TDZ), (WT - 0.02, DH, DW), T_WALL, "x",
                 solid=True)
    c6.mover(panel6, (TX1 + WT / 2, Y2 - DH / 2 - 0.2, TDZ), dur=1.5, delay=0.55)
    plight("C6_fill", (9.4, Y2 + 2.9, 115.4), WARM, 5.0, 8.0)
    box("C6_mark", (F6[0], Y2 + 0.006, F6[2]), (1.5, 0.012, 1.5), T_CARPET, "y", rough=0.98,
        color=[0.72, 0.70, 0.66], tile=(0.75, 0.75))

    # ============================================================ X 廊下（東 → 北）
    shell("X1", TX1 + WT, 24.0, 109.0, 112.0, 2.9, T_CARPET, T_WALL, y=Y2, walls="s")
    shell("X2", 21.0, 24.0, 112.0, 124.0, 2.9, T_CARPET, T_WALL, y=Y2, walls="we")
    box("X1_nw", (19.5, Y2 + 2.9 / 2, 112.15), (3.0, 2.9, WT), T_WALL, "z", rough=0.9, solid=True)
    troffer("X1_tr", 21.0, Y2 + 2.9, 110.5, on=True)
    for z in (115.0, 121.0):
        troffer("X2_tr%.0f" % z, 22.5, Y2 + 2.9, z, on=(z != 121.0))

    # ============================================================ M 多義の間（タイル）
    MX0, MX1, MZ0, MZ1, MH = 14.0, 30.0, 124.3, 142.0, 5.0
    TR0, TR1, TRD = 130.0, 134.0, 2.6          # 溝
    box("M1_flr_s", (22.0, Y2 - WT / 2, (MZ0 + TR0) / 2), (16.6, WT, TR0 - MZ0), T_TILEF, "y",
        rough=0.28, solid=True)
    box("M1_flr_n", (22.0, Y2 - WT / 2, (TR1 + MZ1) / 2), (16.6, WT, MZ1 - TR1), T_TILEF, "y",
        rough=0.28, solid=True)
    box("M1_pit", (22.0, Y2 - TRD - WT / 2, (TR0 + TR1) / 2), (16.6, WT, TR1 - TR0), T_CONC, "y",
        rough=0.95, solid=True)
    for sgn in (-1, 1):
        box("M1_pw%d" % sgn, (22.0 + sgn * 8.15, Y2 - TRD / 2, (TR0 + TR1) / 2), (WT, TRD, TR1 - TR0),
            T_CONC, "x", rough=0.95, solid=True)
    for z in (TR0 + 0.06, TR1 - 0.06):
        box("M1_pf%.0f" % z, (22.0, Y2 - TRD / 2, z), (16.0, TRD, 0.12), T_TILEW, "z", rough=0.3)
        box("M1_pl%.0f" % z, (22.0, Y2 + 0.02, z + (-0.16 if z < TR1 - 1 else 0.16)),
            (16.0, 0.05, 0.20), T_TILEW, "y", rough=0.28)
    shell("M1", MX0, MX1, MZ0, MZ1, MH, T_TILEF, T_TILEW, y=Y2, walls="we", floor=False)
    wall_with_door("M1_s", "z", MZ0 - WT / 2, MX0 - WT, MX1 + WT, Y2, MH, 22.5, DW, DH, T_TILEW)
    wall_with_door("M1_n", "z", MZ1 + WT / 2, MX0 - WT, MX1 + WT, Y2, MH, 22.0, DW, DH, T_TILEW)
    door_casing("M1_nc", "z", MZ1 - 0.02, 22.0, Y2, DW, DH)
    exit_sign("M1_exit", 22.0, Y2 + DH + 0.36, MZ1 - 0.10)
    for x, z in ((17.0, 127.0), (27.0, 127.0), (17.0, 138.0), (27.0, 138.0), (22.0, 132.0)):
        troffer("M1_tr%.0f_%.0f" % (x, z), x, Y2 + MH, z, on=(x, z) != (22.0, 132.0),
                warm=COOL, intensity=8.0, rng=12.0)

    # ---- 継ぎ目 07/08: 同じ浮遊物が「東の橋」にも「西の橋」にもなる ----
    # ★数学: D = F + k(X - F) を 2 通り満たすには (1-k)(F7 - F8) = k(B - A)。
    #   高さと大きさを揃えれば k は共通になり、焦点だけが (B-A) の方向にずれる。
    #   結果として【西に立つと東の橋、東に立つと西の橋】という交差が自然に出る。
    KM = 0.44
    BR_Y = Y2 - 0.12
    A_X, B_X = 26.0, 18.0
    F7 = (18.71, EYEY, 126.5)                 # 西に立つ → 東(A_X)の橋
    F8 = (25.00, EYEY, 126.5)                 # 東に立つ → 西(B_X)の橋
    segs = []
    for i in range(3):
        zc = 132.0 + (i - 1) * 1.78
        d = [F7[0] + KM * (A_X - F7[0]), F7[1] + KM * (BR_Y - F7[1]), F7[2] + KM * (zc - F7[2])]
        segs.append(box("C7_s%d" % i, d, (1.8 * KM, 0.24 * KM, 1.7 * KM), T_PAINT, "y",
                        rough=0.8, color=[0.52, 0.52, 0.48], tile=(0.85, 0.9)))
    edges = []
    for i, sgn in enumerate((-1, 1)):
        edges.append(glow("C7_e%d" % i, (segs[1]["transform"]["position"][0] + sgn * 0.86 * KM,
                                         segs[1]["transform"]["position"][1] + 0.14 * KM,
                                         segs[1]["transform"]["position"][2]),
                          (0.06 * KM, 0.05 * KM, 5.2 * KM), GOLD, 1.25))
    c7 = Conn(7, F7, 1.5, 12.0, (A_X, Y2, 132.0), "bridge-east")
    c7.shard_display(KM, segs + edges, glows=edges)
    c8 = Conn(8, F8, 1.5, 12.0, (B_X, Y2, 132.0), "bridge-west")
    c8.shard_display(KM, segs + edges, glows=edges)
    c7.excl = [8]
    c8.excl = [7]
    for c, bx in ((c7, A_X), (c8, B_X)):
        c.solid(hit("C%d_hit" % c.cid, (bx, BR_Y, 132.0), (1.9, 0.26, TR1 - TR0 + 1.4),
                    kinematic=True))
    for f, nm in ((F7, "C7"), (F8, "C8")):
        box(nm + "_mark", (f[0], Y2 + 0.014, f[2]), (1.5, 0.014, 1.5), T_TILEF, "y", rough=0.3,
            color=[0.80, 0.82, 0.80], tile=(0.75, 0.75))

    # ============================================================ S 揺れの間
    SX0, SX1, SZ0, SZ1, SH_ = 14.0, 30.0, 142.3, 156.0, 5.6
    shell("S1", SX0, SX1, SZ0, SZ1, SH_, T_CONC, T_CONC, y=Y2, walls="we", ceil_tex=T_CONC,
          base=False)
    wall_with_door("S1_s", "z", SZ0 - WT / 2, SX0 - WT, SX1 + WT, Y2, SH_, 22.0, DW, DH, T_CONC)
    SILL2 = Y2 + 2.40
    wall_with_door("S1_n", "z", SZ1 + WT / 2, SX0 - WT, SX1 + WT, Y2, SH_, 22.0, DW,
                   (SILL2 - Y2) + DH, T_CONC)
    box("S1_sill", (22.0, SILL2 - 0.06, SZ1 + WT / 2), (DW, 0.12, WT), T_CONC, "z", rough=0.9)
    door_casing("S1_nc", "z", SZ1 - 0.02, 22.0, SILL2, DW, DH)
    exit_sign("S1_exit", 22.0, SILL2 + DH + 0.34, SZ1 - 0.10)
    for x, z, on in ((17.5, 145.0, True), (26.5, 145.0, False), (17.5, 153.0, False),
                     (26.5, 153.0, True)):
        box("S1_ls%.0f_%.0f" % (x, z), (x, Y2 + SH_ - 0.35, z), (0.9, 0.24, 0.9), T_METAL, "y",
            rough=0.45, metal=0.6, color=[0.42, 0.42, 0.40])
        if on:
            glow("S1_lg%.0f_%.0f" % (x, z), (x, Y2 + SH_ - 0.49, z), (0.64, 0.05, 0.64), WARM, 1.5)
            plight("S1_ll%.0f_%.0f" % (x, z), (x, Y2 + SH_ - 0.8, z), WARM, 9.0, 12.0)

    # ---- 継ぎ目 09: 漂う破片。合う姿勢で【速度が 0 になる】ので、待てば必ず止まる ----
    F9 = (18.2, EYEY, 146.6)
    c9 = Conn(9, F9, 3.0, 15.0, (22.0, Y2 + 1.2, 151.0), "drift")
    RISE9, RUN9, W9 = 0.30, 0.70, 1.70
    ZST = 148.0
    real, drift, upper = [], [], []
    for i in range(8):
        top = Y2 + RISE9 * (i + 1)
        z0 = ZST + RUN9 * i
        s = box("C9_s%d" % i, (22.0, top - 0.11, z0 + RUN9 / 2), (W9, 0.22, RUN9), T_METAL, "y",
                rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47])
        r = box("C9_r%d" % i, (22.0, top - 0.22 - RISE9 / 2 + 0.055, z0 + 0.02), (W9, RISE9, 0.04),
                T_METAL, "z", rough=0.5, metal=0.5, color=[0.40, 0.40, 0.38])
        g = glow("C9_e%d" % i, (22.0 - W9 / 2 + 0.03, top + 0.005, z0 + RUN9 / 2),
                 (0.055, 0.04, RUN9 - 0.04), GOLD, 1.25)
        (real if i < 2 else drift if i < 5 else upper).append((s, r, g))
        h = hit("C9_h%d" % i, (22.0, top - 0.11, z0 + RUN9 / 2), (W9, 0.22, RUN9), kinematic=True)
        if i >= 2:
            c9.solid(h)
    box("C9_land", (22.0, SILL2 - 0.11, 154.9), (W9 + 0.4, 0.22, 2.6), T_METAL, "y", rough=0.5,
        metal=0.5, color=[0.50, 0.50, 0.47], solid=True)
    c9.shard(1.0, [e for g in real for e in g])
    c9.shard(0.52, [e for g in drift for e in g],
             glows=[g[2] for g in drift], osc=(0.62, 0.34, 0.0, 5.0))
    c9.shard(0.36, [e for g in upper for e in g], glows=[g[2] for g in upper])
    box("C9_mark", (F9[0], Y2 + 0.008, F9[2]), (1.5, 0.016, 1.5), T_CONC, "y", rough=0.9,
        color=[0.72, 0.72, 0.70], tile=(0.75, 0.75))

    # ============================================================ Z 終わりの間
    ZX0, ZX1, ZZ0, ZZ1, ZH = 14.0, 30.0, 156.3, 170.0, 6.0
    shell("Z1", ZX0, ZX1, ZZ0, ZZ1, ZH, T_PAINT, T_PAINT, y=SILL2, walls="wen",
          ceil_tex=T_PAINT, base=False)
    wall_with_door("Z1_s", "z", ZZ0 - WT / 2, ZX0 - WT, ZX1 + WT, SILL2, ZH, 22.0, DW, DH, T_PAINT)
    for x, z in ((18.0, 160.0), (26.0, 160.0), (18.0, 167.0), (26.0, 167.0)):
        glow("Z1_lg%.0f_%.0f" % (x, z), (x, SILL2 + ZH - 0.12, z), (1.6, 0.06, 1.6),
             [1.0, 0.99, 0.96], 1.15)
        plight("Z1_ll%.0f_%.0f" % (x, z), (x, SILL2 + ZH - 0.5, z), [1.0, 0.99, 0.96], 8.0, 14.0)

    # ---- 継ぎ目 10: 何にも寄りかかっていない【自立した戸口】 ----
    F10 = (22.0, SILL2 + EYE, 158.2)
    c10 = Conn(10, F10, 3.2, 16.0, (22.0, SILL2 + 1.2, 164.0), "gate")
    GZ = 164.0
    GW, GH = 1.30, 2.35
    parts = [[], [], [], []]
    ks = (0.72, 0.60, 0.50, 0.42)
    jw = 0.24
    p0 = box("C10_jl", (22.0 - GW / 2 - jw / 2, SILL2 + (GH + jw) / 2, GZ), (jw, GH + jw, 0.30),
             T_PAINT, "z", rough=0.45, color=FRAME_COL)
    p1 = box("C10_jr", (22.0 + GW / 2 + jw / 2, SILL2 + (GH + jw) / 2, GZ), (jw, GH + jw, 0.30),
             T_PAINT, "z", rough=0.45, color=FRAME_COL)
    p2 = box("C10_hd", (22.0, SILL2 + GH + jw / 2, GZ), (GW + jw * 2, jw, 0.30), T_PAINT, "z",
             rough=0.45, color=FRAME_COL)
    p3 = box("C10_sl", (22.0, SILL2 + 0.06, GZ), (GW + jw * 2, 0.12, 0.30), T_PAINT, "z",
             rough=0.45, color=FRAME_COL)
    g0 = glow("C10_g0", (22.0 - GW / 2 - 0.02, SILL2 + GH / 2, GZ + 0.16), (0.04, GH, 0.04), GOLD, 1.25)
    g1 = glow("C10_g1", (22.0 + GW / 2 + 0.02, SILL2 + GH / 2, GZ + 0.16), (0.04, GH, 0.04), GOLD, 1.25)
    g2 = glow("C10_g2", (22.0, SILL2 + GH + 0.02, GZ + 0.16), (GW, 0.04, 0.04), GOLD, 1.25)
    g3 = glow("C10_g3", (22.0, SILL2 + 0.14, GZ + 0.16), (GW, 0.04, 0.04), GOLD, 1.25)
    for i, (p, g) in enumerate(((p0, g0), (p1, g1), (p2, g2), (p3, g3))):
        c10.shard(ks[i], [p, g], glows=[g])
    plight("C10_fill", (22.0, SILL2 + 2.3, 157.4), [1.0, 0.99, 0.96], 7.0, 9.0)
    # 戸口の中身(揃うと白い面が立つ = くぐる先)
    inner = glow("C10_in", (22.0, SILL2 + GH / 2, GZ - 0.02), (GW, GH, 0.03), [1.0, 0.99, 0.96], 0.0)
    c10.shine(inner, [1.0, 0.99, 0.96], 1.30)
    return


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
    # ★白い部屋は「終わり」ではなく【節目】。奥の壁に開口を空けて第二幕へ続ける
    wall_with_door("E_back", "z", 85.1, DX3 - 2.15, DX3 + 2.15, YD, 3.2, DX3, DW, DH, T_PAINT)
    for sgn in (-1, 1):
        glow("E_glow%d" % sgn, (DX3 + sgn * 1.45, YD + 1.5, 84.92), (1.25, 2.9, 0.04),
             [1.0, 0.98, 0.94], 1.05)
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
    # ★ここは第一幕の終わりの継ぎ目だが、床の目印は置かない。
    #   ここまでで『立つ位置が世界を決める』は伝わっている

    act2(YD, DW, DH)

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
    # ★中央の点は置かない。合っていない時の画面は【完全に空】にする
    #   （常に何かが出ていると『照準』に見えて、見る事そのものが道具だと伝わらない）
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
    block = ("-- >>>DATA (gen_liminal.py が書く。手で触らない)\nCONNS = "
             + lua_value([c.data() for c in CONNS])
             + "\nCHECKS = " + lua_value(CHECKS)
             + "\nGOAL = " + lua_value(GOAL)
             + "\n-- <<<DATA\n")
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
