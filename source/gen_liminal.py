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
import hashlib, json, math, random

ROOT = Path(__file__).resolve().parents[1]
ES = []            # entities
CONNS = []         # 継ぎ目の定義(Lua へ渡す)

# 到達点(落ちた時の戻り先)。★半径で進む(z のしきい値だと第三幕のように
# 東へ折れる順路で進まなくなる)。y は体の中心の高さ = 床 + 0.90
CHECKS = [
    dict(x=0.00, y=0.90, z=-6.0, r=99.0),
    dict(x=0.00, y=0.90, z=16.6, r=2.4),
    dict(x=-4.60, y=0.90, z=17.0, r=2.0),       # ★F2 の上に置かない(戻った瞬間に解ける)
    dict(x=5.30, y=0.90, z=36.4, r=2.6),
    dict(x=5.50, y=0.90, z=47.6, r=2.6),
    dict(x=6.10, y=4.30, z=63.6, r=2.4),
    dict(x=6.10, y=4.30, z=82.0, r=2.4),        # 白い部屋
    dict(x=6.10, y=4.30, z=87.5, r=2.6),        # 大ホール
    dict(x=6.00, y=4.30, z=106.6, r=2.4),       # 前室
    dict(x=7.00, y=4.30, z=111.0, r=2.6),       # 折り返しの間
    dict(x=22.50, y=4.30, z=126.0, r=2.6),      # 多義の間(溝の手前)
    dict(x=22.00, y=4.30, z=144.0, r=2.6),      # 揺れの間
    dict(x=22.00, y=6.70, z=158.0, r=2.6),      # 終わりの間
    dict(x=22.00, y=6.70, z=173.0, r=2.4),      # 第三幕 連絡通路
    dict(x=22.00, y=6.70, z=179.0, r=2.6),      # 吊られた板の部屋(溝の手前)
    dict(x=22.00, y=6.70, z=188.2, r=2.4),      # 溝を渡った先
    dict(x=22.00, y=6.70, z=192.4, r=2.6),      # 階段室の床
    dict(x=28.80, y=8.50, z=195.2, r=1.8),      # 渡り廊下の東端
    dict(x=32.00, y=8.50, z=195.4, r=2.0),      # 吹き抜け 西の桟
    dict(x=43.20, y=8.50, z=195.4, r=2.2),      # 吹き抜け 東の桟
    dict(x=47.60, y=8.50, z=195.4, r=1.8),      # 見てはいけない廊下(入口)
    dict(x=58.60, y=8.50, z=195.4, r=2.0),      # その先
    dict(x=68.00, y=8.50, z=192.6, r=2.6),      # 模型の大部屋
    dict(x=68.00, y=8.50, z=208.6, r=2.4),      # 終わりの間
    dict(x=68.00, y=8.50, z=221.0, r=2.0),      # 第四幕 連絡通路
    dict(x=68.00, y=8.50, z=224.2, r=2.6),      # 大展示室(南の回廊)
    dict(x=68.00, y=11.50, z=245.4, r=2.0),     # 出口の踊り場
    # ---- 第五幕(環の間。床 10.60) ----
    dict(x=68.00, y=11.50, z=255.0, r=1.8),     # 連絡通路
    dict(x=68.00, y=11.50, z=263.0, r=2.6),     # 柱の森
    dict(x=68.00, y=11.50, z=287.5, r=2.6),     # 井戸を渡った先
    dict(x=77.00, y=12.10, z=299.0, r=2.4),     # 棚の上
    dict(x=56.30, y=13.90, z=299.0, r=2.2),     # 踊り場
]
GOAL = dict(x=56.0, y=13.00, z=302.60, r=0.95, need=25)

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


# ---------------------------------------------------------------- 床の目印
# ★★確定域は「点」ではなく【焦点と対象を結ぶ方向へ伸びた細長い管】(横に敏感・奥行きに鈍感)。
#   そこへ四角い印を被せると「印の上に立ってるのに繋がらない」になる。実際に何度もなった。
#   なので印の【大きさと向き】は手で決めず、機械で測って決める:
#       python source/calib_marks.py       … 確定域を測って下の表を書き直す
#   表を書き換えたら gen_liminal.py を回し直すこと。
#   値は (幅, 長さ, yaw)。長さは箱のローカル z 方向。
# 継ぎ目ごとの許容角(度)。★手で決めない。calib_marks.py が「印の上ならどこでも繋がる」
# を条件に逆算した値をここへ書き戻す。
LOCKS = {
    1: 2.0,
    2: 1.1,
    3: 3.4,
    5: 5.2,
    6: 2.0,
    7: 5.2,
    8: 5.2,
    9: 4.6,
    15: 5.2,
    17: 4.0,
    18: 4.6,
    19: 3.4,
    20: 5.2,
    21: 4.6,
    22: 3.4,
    23: 4.6,
    24: 4.6,
    25: 4.6,
}

# 破片のずらし量の弱め方。k' = 1 - (1-k)*soft。1 へ寄せるほど勾配がなだらかになり、
# lock を緩めずに確定域が広がる(浮き方は控えめになる)。これも calib_marks.py が決める。
SOFT = {
    5: 0.85,
    9: 0.72,
    15: 0.85,
    18: 0.85,
    20: 0.72,
    21: 0.72,
    24: 0.72,
}

MARKS = {
    "G1_ibA": (0.39, 1.24, 23.4),
    "G1_ibB": (0.49, 1.24, 5.6),
    "G1_ibC": (0.44, 1.34, 149.8),
    "G1_ibD": (0.29, 2.14, 0.0),
    "C1_mark": (0.34, 1.64, 5.2),
    "C2_mark": (0.39, 1.54, 36.0),
    "C3_mark": (0.34, 1.44, 70.7),
    "C5_mark": (0.49, 1.04, 171.3),
    "C6_mark": (0.34, 2.34, 128.3),
    "C7_mark": (0.49, 1.04, 67.1),
    "C8_mark": (0.39, 1.24, 114.2),
    "C9_mark": (0.39, 1.44, 36.1),
    "C15_mark": (0.64, 0.84, 176.0),
    "C18_mark": (0.49, 1.04, 20.3),
    "C19_mark": (0.39, 1.24, 52.9),
    "C20_mark": (0.49, 1.04, 51.5),
    "C21_mark": (0.49, 1.04, 69.2),
    "C22_mark": (0.24, 0.84, 114.5),
    "C23_mark": (0.64, 0.84, 87.4),
    "C24_mark": (0.44, 0.54, 106.1),
    "C25_mark": (0.34, 0.54, 121.2),
}


def mark(name, c, tex, color, rough=0.95, thick=0.012):
    """焦点の床に置く擦れ跡。大きさ/向きは MARKS(実測値)から引く。"""
    w, L, yaw = MARKS.get(name, (1.20, 1.20, 0.0))
    return box(name, (c[0], c[1], c[2]), (w, thick, L), tex, "y", rough=rough,
               color=list(color), rot=(0, yaw, 0),
               tile=(max(w / 2.0, 0.2), max(L / 2.0, 0.2)))


def floor_shadow(tag, F, ents, y, pad=0.10, color=(0.055, 0.055, 0.05)):
    """焦点 F から見た ents(浮遊姿勢の破片)の影を、床 y の上に落とす。

    ★第五幕の新しい【見え方】。これまでの継ぎ目は目標が一切見えず、
      「破片の浮き方」だけを頼りに立ち位置を探させていた。ここでは目標が
      床の黒い影として初めて目に見える ＝ 探し方そのものが変わる。
      影は破片の【投影】そのものなので、焦点に立つと破片が影にぴたりと収まる。
    ★影どうしは必ず重なる(階段を真上から見れば帯が重なる)ので、高さを 12mm ずつ
      変えて z ファイティングを避ける(机上検査 [6] の許容は 6mm)。"""
    out = []
    for i, e in enumerate(ents):
        p = e["transform"]["position"]
        sc = e["transform"]["scale"]
        lo = [1e9, 1e9]
        hi = [-1e9, -1e9]
        for c0 in range(8):
            q = [p[0] + (sc[0] / 2 if c0 & 1 else -sc[0] / 2),
                 p[1] + (sc[1] / 2 if c0 & 2 else -sc[1] / 2),
                 p[2] + (sc[2] / 2 if c0 & 4 else -sc[2] / 2)]
            dy = q[1] - F[1]
            if dy > -0.05:                 # 目より上の点は床に落ちない
                return out
            t = (y - F[1]) / dy
            X = F[0] + t * (q[0] - F[0])
            Z = F[2] + t * (q[2] - F[2])
            lo[0] = min(lo[0], X); hi[0] = max(hi[0], X)
            lo[1] = min(lo[1], Z); hi[1] = max(hi[1], Z)
        out.append(box(tag + "%d" % i,
                       ((lo[0] + hi[0]) / 2, y + 0.020 + 0.012 * i, (lo[1] + hi[1]) / 2),
                       (hi[0] - lo[0] + pad, 0.012, hi[1] - lo[1] + pad), T_CONC, "y",
                       rough=0.97, color=list(color)))
    return out


# ---------------------------------------------------------------- 継ぎ目
class Conn:
    """1 つの継ぎ目。shard() で破片を足すと、その場でシーンの transform を
    【ずれた状態】へ書き換え、実体の値を Lua 用データへ残す。"""

    def __init__(self, cid, focus, lock, warn, center, note="",
                 min_y=None, max_y=None, needs=(), anti=False,
                 per_shard=False, peri=False, dark=False, touch=None, dark_lights=(),
                 occl=None):
        self.cid = cid
        self.focus = focus
        self.lock = LOCKS.get(cid, lock)   # ★実測で決めた値があればそれを使う
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
        self.hides = []         # 接続後に消える物(塞がれた道・選ばれなかった方)
        self.excl = []          # 同じ破片を取り合う継ぎ目(多義)の相手
        # ★目の高さの窓。x/z だけでは解が決まらない継ぎ目(「何段目に立つか」)に使う。
        #   幾何そのものは高さにも敏感だが、階段のように【解の線が斜面と平行】だと
        #   どの段からでも解けてしまう。ここで段を 1 つに絞る。
        self.min_y = min_y
        self.max_y = max_y
        self.needs = list(needs)   # 先に確定していないと成立しない継ぎ目(連鎖)
        self.anti = anti           # ★解くと道が【塞がる】継ぎ目。解かないのが正解
        # ---- 別の【解き方】をつくるスイッチ ----
        self.per_shard = per_shard   # 巡る: 破片ごとに別の立ち位置。1 つずつ実体化する
        self.peri = peri             # 直視しない: 周辺視(24〜68度)でだけ成立する
        self.dark = dark             # 暗の一瞬: 明滅する部屋が暗い間だけ成立する
        self.touch = touch           # 触れる: 2 点が画面上で重なったら成立(焦点を使わない)
        # ★規則F「かくれて合わせる」: 指定した点が【何かの陰に隠れている】位置でだけ成立する。
        #   偽物が見えている限り決まらない ＝ 立ち位置探しに「何を隠すか」が加わる。
        #   occl = dict(p=[x,y,z], boxes=[[minx,miny,minz,maxx,maxy,maxz], ...])
        self.occl = occl
        self.dark_lights = list(dark_lights)
        self.solve_order = cid     # 机上検査で解く順。17 は島が要るので後ろへ回す
        CONNS.append(self)

    def shard(self, k, ents, glows=(), osc=None, focus=None):
        """ents: box()/glow() の戻り値。実体の transform を記録してから k 倍に縮める。
        osc=(dx,dy,dz,周期) を渡すと、ずれた姿勢で【揺れる】(合う姿勢で速度 0)。"""
        # ★ずらし量を弱める(calib_marks.py が決める)。実体の位置は動かさないので、
        #   当たり判定も見た目の行き先も変わらない ── 浮き方だけが控えめになる。
        k = 1.0 - (1.0 - k) * SOFT.get(self.cid, 1.0)
        rec = []
        fx, fy, fz = focus or self.focus       # ★破片ごとに焦点を持てる(巡る / 二つ同時)
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
        if focus:
            d["focus"] = [round(v, 4) for v in focus]
        if osc:
            d["osc"] = list(osc)
        self.shards.append(d)
        for g in glows:
            self.glows.append(g["name"])

    def shard_free(self, ents, disp, dk=1.0, glows=()):
        """★「触れる」規則用の破片。実体の姿勢を記録して、disp だけずらし dk 倍した
        【浮遊姿勢】へ動かす。相似変換の縛りが無いので、焦点は使わない
        (成立判定は touch の 2 点が画面上で重なるかどうかで行う)。"""
        rec = []
        for e in ents:
            p = e["transform"]["position"]
            sc = e["transform"]["scale"]
            rec.append(dict(n=e["name"], p=list(p), s=list(sc)))
            e["transform"]["position"] = [round(p[i] + disp[i], 4) for i in range(3)]
            e["transform"]["scale"] = [round(v * dk, 4) for v in sc]
        self.shards.append(dict(k=1.0, ents=rec, pts=[list(rec[0]["p"])],
                                disp=[round(v, 4) for v in disp], dk=dk))
        for g in glows:
            self.glows.append(g["name"])
        return self

    def free_pos(self, e, disp):
        """shard_free に渡す前の実体位置から、浮遊姿勢の座標を求める(touch の点に使う)。"""
        p = self.real_pos(e)
        return [round(p[i] + disp[i], 4) for i in range(3)]

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
        """接続で動く物(塞ぎ板が沈む・扉が開く)。to は最終 position(絶対)。
        ★破片を動かすなら必ず mover_by を使うこと。ここへ
          `e["transform"]["position"] + オフセット` を渡すと【縮んだ座標】を掴む。"""
        self.movers.append(dict(n=e["name"], to=[round(v, 4) for v in to],
                                dur=dur, delay=delay))
        return e

    def mover_by(self, e, d, dur=1.1, delay=0.0):
        """★破片を動かす時はこちら。実体の位置から d だけずらした先を目標にする。
        シャッターの欠けた一枚(k=0.16)を mover() で動かしていた時は、縮んだ座標を基準に
        していたので【確定した瞬間に原寸へ戻り、そのまま 10m 手前の宙へ飛ぶ】…
        つまり『モデルが急にでっかくなって変な所へ行く』というバグになっていた。"""
        p = self.real_pos(e)
        return self.mover(e, (p[0] + d[0], p[1] + d[1], p[2] + d[2]), dur=dur, delay=delay)

    def lamp(self, name, to, dur=0.8, delay=0.0):
        self.lights.append(dict(n=name, to=to, dur=dur, delay=delay))

    def shine(self, e, rgb, power):
        """接続後に自己発光の板を点ける(ReconnectInk の shaderParams を差し替える)。"""
        self.shines.append(dict(n=e["name"], c=[rgb[0], rgb[1], rgb[2], power]))
        return e

    def real_pos(self, e):
        """★破片は shard() の時点で【縮んだ位置】へ書き換わっている。
        丁番も当たり判定も『実体の位置』が要るので、必ずここから引くこと
        (e["transform"]["position"] を直に読むと縮んだ値を掴む = 扉が飛ぶ)。"""
        n = e["name"]
        for sh in self.shards:
            for r in sh["ents"]:
                if r["n"] == n:
                    return list(r["p"])
        return list(e["transform"]["position"])

    def hinge(self, e, pivot, deg, dur=1.4, delay=0.45):
        """接続後に扉が開く。pivot(丁番)まわりに deg 度回す。
        ★実行時は焼き込んだ座標を使わず【その場の transform】を回す(runtime の easeSwing)。
        ここに残す p は机上シミュレータと目視デバッグ用の実体位置。
        dur/delay は【見られている時】のイージング用(視界の外なら一度に置く)。"""
        self.hinges.append(dict(n=e["name"], p=[round(v, 4) for v in self.real_pos(e)],
                                piv=[round(v, 4) for v in pivot], deg=deg,
                                dur=dur, delay=delay))
        return e

    def hide(self, e):
        """接続後に消える物。負の継ぎ目(解くと塞がる)で『開いていた側』を消すのに使う。"""
        self.hides.append(e["name"] if isinstance(e, dict) else e)
        return e

    def data(self):
        return dict(id=self.cid, focus=[round(v, 4) for v in self.focus],
                    lock=self.lock, warn=self.warn,
                    center=[round(v, 4) for v in self.center], note=self.note,
                    shards=self.shards, glows=self.glows, solids=self.solids,
                    movers=self.movers, lights=self.lights, hinges=self.hinges,
                    shines=self.shines, hides=self.hides, excl=self.excl,
                    needs=self.needs, anti=self.anti,
                    minY=self.min_y, maxY=self.max_y,
                    perShard=self.per_shard, peri=self.peri, dark=self.dark,
                    touch=self.touch, darkLights=self.dark_lights, occl=self.occl)


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
        # ★長さ 16.6 だと端面が側壁の外面とぴったり同一平面になる。16.4 で壁の内側に納める
        box("H1_bm%.0f" % z, (6.0, Y2 + HH - 0.35, z), (16.4, 0.7, 0.45), T_CONC, "z", rough=0.9)
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
    c5 = Conn(5, F5, 3.2, 20.0, (SHX, Y2 + SHH / 2, HZ1 - 0.2), "shutter")
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
    # 揃うとシャッターが巻き上がる。★mover_by(実体からの相対) で渡すこと。
    #   絶対座標を e["transform"]["position"] から作ると【縮んだ破片の座標】を掴んでしまい、
    #   確定で原寸に戻った板が 10m 手前の宙へ飛ぶ(「モデルがでっかくなる」バグ)
    for p in panels + [miss] + ribs + mg:
        c5.mover_by(p, (0.0, SHH + 0.15, 0.0), dur=2.2, delay=0.0)
    # ★破片は【照らさないと真っ黒の穴に見える】。合っているのに合っていないように見えるので致命的。
    #   焦点の斜め後ろから当てる灯りを 1 つ足す(床の目印も一緒に見える)
    plight("C5_fill", (6.0, Y2 + 5.0, 89.6), WARM, 8.0, 12.0)
    mark("C5_mark", (F5[0], Y2 + 0.008, F5[2]), T_CONC, (0.72, 0.72, 0.70), rough=0.9,
         thick=0.016)

    # ============================================================ V 前室（材質が事務所へ戻る）
    shell("V1", 3.0, 9.0, HZ1 + WT, 108.5, 3.0, T_CARPET, T_WALL, y=Y2, walls="we")
    # ★T の南壁(T1_s)が開口ごとこの位置の壁を兼ねる。ここには建てない
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
    c6 = Conn(6, F6, 0.5, 5.0, (TX1 - 0.2, Y2 + 1.2, TDZ), "behind")
    ZF6 = TX1 - 0.11
    rp, rg = frame_half_x("C6_R", +1, TDZ, Y2, ZF6, DW, DH)
    c6.shard(1.0, rp, glows=rg)
    lp, lg = frame_half_x("C6_L", -1, TDZ, Y2, ZF6, DW, DH)
    c6.shard(0.46, lp, glows=lg)
    panel6 = box("C6_Panel", (TX1 + WT / 2, Y2 + DH / 2, TDZ), (WT - 0.02, DH, DW), T_WALL, "x",
                 solid=True)
    c6.mover(panel6, (TX1 + WT / 2, Y2 - DH / 2 - 0.2, TDZ), dur=1.3, delay=0.0)
    plight("C6_fill", (9.4, Y2 + 2.9, 115.4), WARM, 5.0, 8.0)
    mark("C6_mark", (F6[0], Y2 + 0.006, F6[2]), T_CARPET, (0.72, 0.70, 0.66), rough=0.98)

    # ============================================================ X 廊下（東 → 北）
    shell("X1", TX1 + WT, 24.0, 109.0, 112.0, 2.9, T_CARPET, T_WALL, y=Y2, walls="s")
    shell("X2", 21.0, 24.0, 112.0, 124.0, 2.9, T_CARPET, T_WALL, y=Y2, walls="we",
          floor=False, ceil=False)
    # ★X1 の床/天井が z=112.3 まで出ているので、X2 はその先から敷く(重ねると z ファイティング)
    box("X2_flr", (22.5, Y2 - WT / 2, 118.3), (3.6, WT, 12.0), T_CARPET, "y", rough=0.95,
        solid=True)
    box("X2_cil", (22.5, Y2 + 2.9 + WT / 2, 118.3), (3.6, WT, 12.0), T_CEIL, "y", rough=0.94)
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
    BR_Y = Y2 + 0.09          # ★床の【上に載せる】(面一だと 0.63m が床と見切りに潜る)
    A_X, B_X = 26.0, 18.0
    F7 = (18.71, EYEY, 126.5)                 # 西に立つ → 東(A_X)の橋
    F8 = (25.00, EYEY, 126.5)                 # 東に立つ → 西(B_X)の橋
    segs = []
    for i in range(3):
        zc = 132.0 + (i - 1) * 1.78
        d = [F7[0] + KM * (A_X - F7[0]), F7[1] + KM * (BR_Y - F7[1]), F7[2] + KM * (zc - F7[2])]
        segs.append(box("C7_s%d" % i, d, (1.8 * KM, 0.18 * KM, 1.7 * KM), T_PAINT, "y",
                        rough=0.8, color=[0.52, 0.52, 0.48], tile=(0.85, 0.9)))
    edges = []
    for i, sgn in enumerate((-1, 1)):
        edges.append(glow("C7_e%d" % i, (segs[1]["transform"]["position"][0] + sgn * 0.86 * KM,
                                         segs[1]["transform"]["position"][1] + 0.14 * KM,
                                         segs[1]["transform"]["position"][2]),
                          (0.06 * KM, 0.05 * KM, 5.2 * KM), GOLD, 1.25))
    c7 = Conn(7, F7, 1.6, 10.0, (A_X, Y2, 132.0), "bridge-east")
    c7.shard_display(KM, segs + edges, glows=edges)
    c8 = Conn(8, F8, 1.6, 10.0, (B_X, Y2, 132.0), "bridge-west")
    c8.shard_display(KM, segs + edges, glows=edges)
    c7.excl = [8]
    c8.excl = [7]
    for c, bx in ((c7, A_X), (c8, B_X)):
        c.solid(hit("C%d_hit" % c.cid, (bx, BR_Y, 132.0), (1.9, 0.20, TR1 - TR0 + 1.4),
                    kinematic=True))
    for f, nm in ((F7, "C7"), (F8, "C8")):
        mark(nm + "_mark", (f[0], Y2 + 0.014, f[2]), T_TILEF, (0.80, 0.82, 0.80),
             rough=0.3, thick=0.014)

    # ============================================================ S 揺れの間
    SX0, SX1, SZ0, SZ1, SH_ = 14.0, 30.0, 142.3, 156.0, 5.6
    shell("S1", SX0, SX1, SZ0, SZ1, SH_, T_CONC, T_CONC, y=Y2, walls="we", ceil_tex=T_CONC,
          base=False)
    # ★M の北壁(M1_n)がこの位置の壁を兼ねる。ここで 2 枚目を建てると 38m2 が同一平面になり
    #   見る位置で色が入れ替わる。S の方が天井が高いぶんだけを【上に足す】
    slab("S1_s", "z", SZ0 - WT / 2, SX0 - WT, SX1 + WT, Y2 + 5.0 + WT, Y2 + SH_, T_CONC)
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
    c9 = Conn(9, F9, 2.5, 14.0, (22.0, Y2 + 1.2, 151.0), "drift")
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
    mark("C9_mark", (F9[0], Y2 + 0.008, F9[2]), T_CONC, (0.72, 0.72, 0.70), rough=0.9,
         thick=0.016)

    # ============================================================ Z 終わりの間
    ZX0, ZX1, ZZ0, ZZ1, ZH = 14.0, 30.0, 156.3, 170.0, 6.0
    shell("Z1", ZX0, ZX1, ZZ0, ZZ1, ZH, T_PAINT, T_PAINT, y=SILL2, walls="we",
          ceil_tex=T_PAINT, base=False)
    # ★S の北壁(S1_n)が開口ごとこの位置の壁を兼ねる。Z の方が高いぶんだけを上に足す
    slab("Z1_s", "z", ZZ0 - WT / 2, ZX0 - WT, ZX1 + WT, Y2 + 5.6 + WT, SILL2 + ZH, T_PAINT)
    # ★白い部屋は終わりではなく【第三幕への戸口】。戸口(継ぎ目10)が建つまでは塞がっている
    wall_with_door("Z1_n", "z", ZZ1 + WT / 2, ZX0 - WT, ZX1 + WT, SILL2, ZH, 22.0, DW, DH, T_PAINT)
    door_casing("Z1_nc", "z", ZZ1 - 0.02, 22.0, SILL2, DW, DH)
    exit_sign("Z1_exit", 22.0, SILL2 + DH + 0.36, ZZ1 - 0.10)
    for x, z in ((18.0, 160.0), (26.0, 160.0), (18.0, 167.0), (26.0, 167.0)):
        glow("Z1_lg%.0f_%.0f" % (x, z), (x, SILL2 + ZH - 0.12, z), (1.6, 0.06, 1.6),
             [1.0, 0.99, 0.96], 1.15)
        plight("Z1_ll%.0f_%.0f" % (x, z), (x, SILL2 + ZH - 0.5, z), [1.0, 0.99, 0.96], 8.0, 14.0)

    # ---- 継ぎ目 10: 何にも寄りかかっていない【自立した戸口】 ----
    F10 = (22.0, SILL2 + EYE, 158.2)
    c10 = Conn(10, F10, 2.2, 13.0, (22.0, SILL2 + 1.2, 164.0), "gate")
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
    # 戸口が建つと、北の壁の塞ぎ板が(見ていない間に)床下へ消える
    zpanel = box("C10_Panel", (22.0, SILL2 + DH / 2, ZZ1 + WT / 2), (DW, DH, WT - 0.02),
                 T_PAINT, "z", solid=True)
    c10.mover(zpanel, (22.0, SILL2 - DH / 2 - 0.25, ZZ1 + WT / 2))
    return SILL2


# ================================================================ 第三幕（継ぎ目 11〜16）
def aabb_of(e):
    p, s = e["transform"]["position"], e["transform"]["scale"]
    return (p[0] - s[0] / 2, p[1] - s[1] / 2, p[2] - s[2] / 2,
            p[0] + s[0] / 2, p[1] + s[1] / 2, p[2] + s[2] / 2)


def bb_hit(a, b, pad=0.0):
    return (a[0] - pad < b[3] and b[0] - pad < a[3] and
            a[1] - pad < b[4] and b[1] - pad < a[4] and
            a[2] - pad < b[5] and b[2] - pad < a[5])


def corridor(tag, x0, x1, z0, z1, y, h, floor_tex, wall_tex, ceil_tex=None):
    """床と天井だけ。壁は呼ぶ側が置く(迂回路のように壁を共有する所で使う)。"""
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    box(tag + "_flr", (cx, y - WT / 2, cz), (x1 - x0, WT, z1 - z0), floor_tex, "y",
        rough=0.95, solid=True)
    box(tag + "_cil", (cx, y + h + WT / 2, cz), (x1 - x0, WT, z1 - z0),
        ceil_tex or T_CEIL, "y", rough=0.94)


def slab(tag, axis, at, lo, hi, y0, y1, tex, color=None):
    """1 枚の壁(開口なし)。axis='x' なら x=at の壁で lo..hi は z 範囲。"""
    if hi - lo < 0.01 or y1 - y0 < 0.01:
        return
    if axis == "x":
        box(tag, (at, (y0 + y1) / 2, (lo + hi) / 2), (WT, y1 - y0, hi - lo), tex, "x",
            rough=0.9, solid=True, color=color)
    else:
        box(tag, ((lo + hi) / 2, (y0 + y1) / 2, at), (hi - lo, y1 - y0, WT), tex, "z",
            rough=0.9, solid=True, color=color)


def wall_hole(tag, axis, at, lo, hi, y0, y1, dc, dw, sill, dh, tex, color=None):
    """y0..y1 の壁に、中心 dc・幅 dw・下端 sill・高さ dh の開口を空ける。
    wall_with_door と違い【床から浮いた開口(中段の扉)】が作れる。"""
    slab(tag + "_a", axis, at, lo, dc - dw / 2, y0, y1, tex, color)
    slab(tag + "_b", axis, at, dc + dw / 2, hi, y0, y1, tex, color)
    slab(tag + "_c", axis, at, dc - dw / 2, dc + dw / 2, y0, sill, tex, color)
    slab(tag + "_d", axis, at, dc - dw / 2, dc + dw / 2, sill + dh, y1, tex, color)


def act3(Y3, DW, DH):
    """白い部屋の北から続く第三幕。規則は 1 つのまま【探し方】を 6 通りに割る。

      11 偽の破片   宙に吊られた 24 枚の板。本物は 3 枚だけ ＝ まず【見分ける】
      12 何段目     大階段の【途中の一段】だけが焦点。x/z ではなく【高さ】が答え
      13 巨人       吹き抜けに浮かぶ巨大な板(k>1)が足元の渡し板になる ＝ 継ぎ目5 の逆
      14 見ない     見ると【壁が建って塞がる】継ぎ目。合わせないことが正解
      15 模型       宙に浮いた廊下の模型(k=0.42)が本物の廊下になる ＝ 強制遠近法
      16 扉         組み上がった扉が丁番でひらく(第三幕の出口)
    """
    EY = Y3 + EYE
    Y4 = Y3 + 1.80          # 第三幕の上層(7.60)

    # ============================================================ W 連絡通路
    shell("W1", 20.2, 23.8, 170.3, 176.0, 2.9, T_CARPET, T_WALL, y=Y3, walls="we")
    troffer("W1_tr", 22.0, Y3 + 2.9, 173.2, on=True)
    door_closed("W1_d1", 20.2 + 0.07, Y3, 174.4, axis="x", inset=0.045)

    # ============================================================ P 吊られた板の部屋（継ぎ目11）
    PX0, PX1, PZ0, PZ1, PH = 14.0, 30.0, 176.3, 190.0, 8.4
    GZ0, GZ1, GY = 182.0, 186.0, 2.40           # 床の切れ目。底は 3.4m 下
    shell("P1", PX0, PX1, PZ0, PZ1, PH, T_CONC, T_CONC, y=Y3, walls="we",
          ceil_tex=T_CONC, base=False, floor=False)
    wall_with_door("P1_s", "z", PZ0 - WT / 2, PX0 - WT, PX1 + WT, Y3, PH, 22.0, DW, DH, T_CONC)
    wall_with_door("P1_n", "z", PZ1 + WT / 2, PX0 - WT, PX1 + WT, Y3, PH, 22.0, DW, DH, T_CONC)
    door_casing("P1_nc", "z", PZ1 - 0.02, 22.0, Y3, DW, DH)
    exit_sign("P1_exit", 22.0, Y3 + DH + 0.36, PZ1 - 0.10)
    # ★床は溝の南北 2 枚。重ねる所は必ず壁の下に隠す(coplanar は z ファイティング)
    box("P1_fs", (22.0, Y3 - WT / 2, (PZ0 - WT + GZ0) / 2), (16.6, WT, GZ0 - PZ0 + WT),
        T_CONC, "y", rough=0.95, solid=True)
    box("P1_fn", (22.0, Y3 - WT / 2, (GZ1 + PZ1 + WT) / 2), (16.6, WT, PZ1 + WT - GZ1),
        T_CONC, "y", rough=0.95, solid=True)
    box("P1_pit", (22.0, GY - WT / 2, (GZ0 + GZ1) / 2), (16.6, WT, GZ1 - GZ0), T_CONC, "y",
        rough=0.95, solid=True)
    for z in (GZ0, GZ1):                                   # 溝の側面(深さが読める)
        box("P1_pf%.0f" % z, (22.0, (GY + Y3) / 2, z), (16.6, Y3 - GY, 0.10), T_CONC, "z",
            rough=0.92, color=[0.58, 0.58, 0.56])
    plight("P1_pl", (22.0, GY + 1.3, 184.0), COOL, 3.5, 6.5)
    for x, z, on in ((17.0, 179.0, True), (27.0, 179.0, False), (17.0, 188.0, False),
                     (27.0, 188.0, True), (22.0, 179.4, True)):
        box("P1_ls%.0f_%.0f" % (x, z), (x, Y3 + PH - 0.35, z), (0.9, 0.24, 0.9), T_METAL, "y",
            rough=0.45, metal=0.6, color=[0.42, 0.42, 0.40])
        if on:
            glow("P1_lg%.0f_%.0f" % (x, z), (x, Y3 + PH - 0.49, z), (0.64, 0.05, 0.64), WARM, 1.5)
            plight("P1_ll%.0f_%.0f" % (x, z), (x, Y3 + PH - 0.9, z), WARM, 12.0, 15.0)

    # ---- 継ぎ目 11: 24 枚のうち 3 枚だけが本物 ----
    # ★ここだけ【継ぎ目の光を付けない】。金の線が付いていたら本物が一目で分かる。
    #   代わりに斜め前から灯りを当てて、板の面が読めるようにする(黒い板対策)。
    F11 = (18.0, EY, 180.0)
    c11 = Conn(11, F11, 3.2, 16.0, (22.0, Y3, 184.0), "decoys")
    # ★見た目の板は【隙間なく】並べる(重ねると上面が同一平面になって z ファイティング)。
    #   当たり判定だけは前後に伸ばして重ねる ＝ 継ぎ目で足が抜けない
    PD = (GZ1 - GZ0) / 3.0
    for i, k in enumerate((0.42, 0.55, 0.68)):
        zc = GZ0 + PD * (i + 0.5)
        pl = box("C11_p%d" % i, (22.0, Y3 - 0.08, zc), (2.2, 0.16, PD), T_METAL, "y",
                 rough=0.5, metal=0.45, color=[0.50, 0.50, 0.47])
        c11.shard(k, [pl])
        c11.solid(hit("C11_h%d" % i, (22.0, Y3 - 0.08, zc), (2.3, 0.16, PD + 0.30),
                      kinematic=True))
    plight("C11_fill", (19.4, Y3 + 3.2, 179.2), WARM, 10.0, 14.0)
    # 偽の破片。★大きさも材質も本物と同じ。違うのは「どこからも重ならない」ことだけ
    rg = random.Random(20260906)
    keep = [aabb_of(e) for e in ES if e["name"].startswith("C11_p")]
    made, tries = 0, 0
    while made < 24 and tries < 6000:
        tries += 1
        w = 0.62 + rg.random() * 1.75
        d = 0.42 + rg.random() * 0.95
        x = 15.0 + rg.random() * 14.0
        y = Y3 + 0.55 + rg.random() * 2.45
        z = 177.4 + rg.random() * 11.8
        bb = (x - w / 2, y - 0.09, z - d / 2, x + w / 2, y + 0.09, z + d / 2)
        if abs(x - 22.0) < 1.9 and (z < GZ0 + 0.2 or z > GZ1 - 0.2):
            continue                                    # 歩く帯には置かない
        if 17.0 < x < 23.5 and 179.4 < z < 186.5 and Y3 + 0.25 < y < Y3 + 1.7:
            continue                                    # 焦点 -> 本物 の視線を塞がない
        if any(bb_hit(bb, s, 0.30) for s in keep):
            continue
        keep.append(bb)
        box("P1_fk%d" % made, (x, y, z), (w, 0.16, d), T_METAL, "y", rough=0.5, metal=0.45,
            color=[0.50, 0.50, 0.47])
        made += 1

    # ============================================================ Q 階段室（継ぎ目12）
    QX0, QX1, QZ0, QZ1, QH = 16.0, 30.0, 190.3, 204.0, 8.4
    shell("Q1", QX0, QX1, QZ0, QZ1, QH, T_CONC, T_CONC, y=Y3, walls="wn",
          ceil_tex=T_CONC, base=False)
    QDZ = 195.2                                          # 東壁の扉(中段 y=7.6)
    wall_hole("Q1_e", "x", QX1 + WT / 2, QZ0 - WT, QZ1 + WT, Y3, Y3 + QH,
              QDZ, DW, Y4, DH, T_CONC)
    door_casing("Q1_ec", "x", QX1 - 0.02, QDZ, Y4, DW, DH)
    exit_sign_x("Q1_exit", QX1 - 0.16, Y4 + DH + 0.40, QDZ)
    QPanel = box("C12_Panel", (QX1 + WT / 2, Y4 + DH / 2, QDZ), (WT - 0.02, DH, DW), T_CONC, "x",
                 solid=True)
    # 大階段(12 段・蹴上げ 0.30)。★一番上の踊り場は封鎖された扉 = 見せかけの正解
    SW3, SX3, SZ3, RISE3, RUN3 = 2.6, 18.3, 192.0, 0.30, 0.55
    for i in range(1, 13):
        top = Y3 + RISE3 * i
        box("Q1_st%d" % i, (SX3, (Y3 + top) / 2, SZ3 + RUN3 * (i - 0.5)), (SW3, top - Y3, RUN3),
            T_CONC, "y", rough=0.9, solid=True)
    ZTOP = SZ3 + RUN3 * 12
    box("Q1_land", (SX3, Y3 + 3.60 - 0.15, (ZTOP + QZ1 - 0.3) / 2),
        (SW3, 0.30, QZ1 - 0.3 - ZTOP), T_CONC, "y", rough=0.9, solid=True)
    door_closed("Q1_dead", SX3, Y3 + 3.60, QZ1 - 0.34, axis="z", inset=0.045)
    for x, z, on in ((18.3, 193.2, True), (18.3, 200.8, True), (25.0, 194.0, True),
                     (25.0, 201.0, False), (22.0, 197.4, True)):
        box("Q1_ls%.0f_%.0f" % (x, z), (x, Y3 + QH - 0.35, z), (0.9, 0.24, 0.9), T_METAL, "y",
            rough=0.45, metal=0.6, color=[0.42, 0.42, 0.40])
        if on:
            glow("Q1_lg%.0f_%.0f" % (x, z), (x, Y3 + QH - 0.49, z), (0.64, 0.05, 0.64), WARM, 1.5)
            plight("Q1_ll%.0f_%.0f" % (x, z), (x, Y3 + QH - 0.9, z), WARM, 13.0, 16.0)

    # ---- 継ぎ目 12: 焦点は【6 段目の上】。x/z を合わせても高さが違えば解けない ----
    F12 = (SX3, Y3 + RISE3 * 6 + EYE, SZ3 + RUN3 * 5.5)          # (18.3, 9.30, 195.025)
    c12 = Conn(12, F12, 3.6, 16.0, (24.5, Y4, QDZ), "which-step",
               min_y=F12[1] - 0.18, max_y=F12[1] + 0.18)
    CWD = 1.60                                                    # 渡り廊下の幅(z)
    # ★階段側の一枚は【最初から実在】させる。これが「何を組もうとしているか」の見本になり、
    #   同時に破片を目から離す(近すぎる破片は少し動くだけで暴れて確定域が消える)
    box("C12_anchor", (20.5, Y4 - 0.09, QDZ), (2.2, 0.18, CWD), T_METAL, "y", rough=0.5,
        metal=0.5, color=[0.50, 0.50, 0.47], solid=True)
    for i, k in enumerate((0.45, 0.58, 0.70, 0.82)):
        # ★一番奥の板は東壁の面(x=30.0)で止める。2.2m のままだと壁と踊り場へ 0.40m 潜り、
        #   天端が同じ高さで重なってちらつく(組み上がった後にしか出ない不具合だった)
        w12 = 2.2 if i < 3 else 1.7      # 1.7 = 東壁のケーシング(x=29.90)の手前まで
        xc = 21.6 + 2.2 * i + w12 / 2
        pl = box("C12_p%d" % i, (xc, Y4 - 0.09, QDZ), (w12, 0.18, CWD), T_METAL, "y",
                 rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47])
        g = glow("C12_g%d" % i, (xc, Y4 + 0.01, QDZ - CWD / 2 + 0.05), (w12 - 0.1, 0.04, 0.06),
                 GOLD, 1.25)
        c12.shard(k, [pl, g], glows=[g])
        c12.solid(hit("C12_h%d" % i, (xc, Y4 - 0.09, QDZ), (w12 + 0.3, 0.18, CWD),
                      kinematic=True))
    c12.mover(QPanel, (QX1 + WT / 2, Y4 - DH / 2 - 0.30, QDZ))
    plight("C12_fill", (23.0, Y4 + 2.4, QDZ - 2.6), WARM, 9.0, 13.0)

    # ============================================================ R 吹き抜け（継ぎ目13）
    RX0, RX1, RZ0, RZ1, RH = 30.3, 46.0, 190.0, 206.0, 16.0
    shell("R1", RX0, RX1, RZ0, RZ1, RH, T_CONC, T_CONC, y=0.0, walls="ns",
          ceil_tex=T_CONC, base=False)
    slab("R1_wlo", "x", RX0 - WT / 2, RZ0 - WT, RZ1 + WT, 0.0, Y3, T_CONC)
    slab("R1_whi", "x", RX0 - WT / 2, RZ0 - WT, RZ1 + WT, Y3 + QH, RH, T_CONC)
    RDZ = 195.4
    wall_hole("R1_e", "x", RX1 + WT / 2, RZ0 - WT, RZ1 + WT, 0.0, RH, RDZ, DW, Y4, DH, T_CONC)
    box("R1_lw", (31.85, Y4 - WT / 2, 195.75), (3.7, WT, 6.5), T_METAL, "y",
        rough=0.5, metal=0.5, color=[0.48, 0.48, 0.46], solid=True)
    box("R1_le", (43.65, Y4 - WT / 2, 195.75), (5.3, WT, 6.5), T_METAL, "y",
        rough=0.5, metal=0.5, color=[0.48, 0.48, 0.46], solid=True)
    box("C13_anchor", (40.25, Y4 - 0.09, RDZ), (1.9, 0.18, 2.0), T_METAL, "y", rough=0.5,
        metal=0.5, color=[0.50, 0.50, 0.47], solid=True)
    for x, z in ((32.2, 192.9), (32.2, 198.6), (43.4, 192.9), (43.4, 198.6)):
        glow("R1_lg%.0f_%.0f" % (x, z), (x, Y4 + 3.4, z), (1.0, 0.05, 1.0), WARM, 1.5)
        plight("R1_ll%.0f_%.0f" % (x, z), (x, Y4 + 3.1, z), WARM, 11.0, 14.0)
    for x in (38.5, 42.5):                                # ★巨大な破片を照らす(黒い板対策)
        plight("R1_deep%.0f" % x, (x, Y4 + 1.2, RDZ), COOL, 16.0, 18.0)
    exit_sign_x("R1_exit", RX1 - 0.16, Y4 + DH + 0.40, RDZ)

    # ---- 継ぎ目 13: k>1。【遠くの巨大】が足元の板になる(継ぎ目 5 のちょうど逆) ----
    F13 = (32.0, Y4 + EYE, RDZ)
    c13 = Conn(13, F13, 3.2, 16.0, (36.5, Y4, RDZ), "giant")
    # ★手前の板は踊り場の面(x=33.7)から始める(2.2m だと 0.20m 潜って天端がちらつく)
    for i, (xc, w3, k) in enumerate(((34.7, 2.0, 2.40), (36.8, 2.2, 1.90), (38.6, 1.4, 1.55))):
        pl = box("C13_p%d" % i, (xc, Y4 - 0.09, RDZ), (w3, 0.18, 2.0), T_METAL, "y",
                 rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47])
        g = glow("C13_g%d" % i, (xc, Y4 + 0.01, RDZ - 0.96), (w3 - 0.1, 0.04, 0.06), GOLD, 1.25)
        c13.shard(k, [pl, g], glows=[g])
        c13.solid(hit("C13_h%d" % i, (xc, Y4 - 0.09, RDZ), (w3 + 0.4, 0.18, 2.0),
                      kinematic=True))

    # ============================================================ T 廊下（継ぎ目14: 見てはいけない）
    TX0, TX1, TZ0, TZ1, TH3 = 46.3, 60.0, 193.8, 197.0, 2.9
    corridor("T3", TX0 - WT, TX1 + WT, TZ0 - WT, TZ1 + WT, Y4, TH3, T_CARPET, T_WALL)
    slab("T3_s", "z", TZ0 - WT / 2, TX0 - WT, TX1 + WT, Y4, Y4 + TH3, T_WALL)
    for i, (a, b) in enumerate(((TX0 - WT, 48.4), (51.0, 55.0), (57.6, TX1 + WT))):
        slab("T3_n%d" % i, "z", TZ1 + WT / 2, a, b, Y4, Y4 + TH3, T_WALL)
    wall_hole("T3_e", "x", TX1 + WT / 2, TZ0 - WT, TZ1 + WT, Y4, Y4 + TH3,
              195.4, DW, Y4, DH, T_WALL)
    for x in (48.0, 51.6, 56.4, 59.0):
        troffer("T3_tr%.0f" % x, x, Y4 + TH3, 195.4, on=(x != 51.6))
    exit_sign("T3_exit", 58.6, Y4 + DH + 0.40, TZ1 - 0.12)
    # 迂回路(北を回る)。★見てしまった人のための、確実に通れる道
    corridor("T3dA", 48.25, 51.15, TZ1 + WT, 201.0, Y4, TH3, T_CARPET, T_WALL)
    corridor("T3dB", 48.25, 57.75, 201.0, 204.15, Y4, TH3, T_CARPET, T_WALL)
    corridor("T3dC", 54.85, 57.75, TZ1 + WT, 201.0, Y4, TH3, T_CARPET, T_WALL)
    slab("T3d_w1", "x", 48.25, TZ1 - 0.15, 204.3, Y4, Y4 + TH3, T_WALL)
    slab("T3d_w2", "x", 51.15, TZ1 - 0.15, 201.15, Y4, Y4 + TH3, T_WALL)
    slab("T3d_w3", "x", 54.85, TZ1 - 0.15, 201.15, Y4, Y4 + TH3, T_WALL)
    slab("T3d_w4", "x", 57.75, TZ1 - 0.15, 204.3, Y4, Y4 + TH3, T_WALL)
    slab("T3d_n", "z", 204.15, 48.1, 57.9, Y4, Y4 + TH3, T_WALL)
    slab("T3d_s", "z", 200.85, 51.15, 54.85, Y4, Y4 + TH3, T_WALL)
    for x, z in ((49.7, 199.4), (53.0, 202.6), (56.3, 199.4)):
        troffer("T3d_tr%.0f_%.0f" % (x, z), x, Y4 + TH3, z, on=True)

    # ---- 継ぎ目 14: 解くと【壁が建って直進できなくなる】。合わせないのが正解 ----
    F14 = (49.6, Y4 + EYE, 195.4)
    c14 = Conn(14, F14, 2.5, 13.0, (53.0, Y4 + 1.45, 195.4), "do-not-look", anti=True)
    for i, k in enumerate((0.55, 0.68, 0.80)):
        yc = Y4 + 0.4833 + 0.9667 * i
        sl = box("C14_s%d" % i, (53.0, yc, 195.4), (0.30, 0.9467, TZ1 - TZ0), T_CONC, "x",
                 rough=0.9, color=[0.56, 0.56, 0.54])
        c14.shard(k, [sl])
    c14.solid(hit("C14_h", (53.0, Y4 + 1.45, 195.4), (0.30, 2.9, TZ1 - TZ0)))
    box("T3_worn", (49.7, Y4 + 0.006, 197.6), (1.7, 0.012, 1.7), T_CARPET, "y", rough=0.98,
        color=[0.72, 0.70, 0.66], tile=(0.85, 0.85))

    # ============================================================ U 大部屋（継ぎ目15: 模型）
    UX0, UX1, UZ0, UZ1, UH = 60.3, 76.0, 190.0, 206.0, 5.0
    shell("U3", UX0, UX1, UZ0, UZ1, UH, T_PAINT, T_PAINT, y=Y4, walls="es",
          ceil_tex=T_PAINT, base=False)
    wall_with_door("U3_n", "z", UZ1 + WT / 2, UX0 - WT, UX1 + WT, Y4, UH, 68.0, DW, DH, T_PAINT)
    door_casing("U3_nc", "z", UZ1 - 0.02, 68.0, Y4, DW, DH)
    exit_sign("U3_exit", 68.0, Y4 + DH + 0.36, UZ1 - 0.10)
    UPanel = box("C15_Panel", (68.0, Y4 + DH / 2, UZ1 + WT / 2), (DW, DH, WT - 0.02), T_PAINT, "z",
                 solid=True)
    for x, z in ((63.5, 193.0), (73.0, 193.0), (63.5, 203.0), (73.0, 203.0)):
        glow("U3_lg%.0f_%.0f" % (x, z), (x, Y4 + UH - 0.12, z), (1.5, 0.06, 1.5),
             [1.0, 0.99, 0.96], 1.15)
        plight("U3_ll%.0f_%.0f" % (x, z), (x, Y4 + UH - 0.5, z), [1.0, 0.99, 0.96], 10.0, 16.0)

    # ---- 継ぎ目 15: 宙に浮いた【廊下の模型】が、本物の廊下になる ----
    # ★強制遠近法そのもの。模型 = 実物を焦点まわりに k 倍しただけなので、焦点に立つと
    #   「床に建っている長い廊下」に完全に一致する。床は本物を流用するので模型には置かない
    #   (置くと本物の床と同一平面になって z ファイティングする)。
    F15 = (68.0, Y4 + EYE, 191.0)
    c15 = Conn(15, F15, 2.5, 13.0, (68.0, Y4 + 1.45, 199.5), "maquette")
    CZ0, CZ1, CW, CH3, KM3 = 195.0, UZ1 - 0.15, 2.8, 2.90, 0.52
    czc, czl = (CZ0 + CZ1) / 2, CZ1 - CZ0
    for sgn, nm in ((-1, "w"), (1, "e")):
        wl = box("C15_%s" % nm, (68.0 + sgn * (CW / 2 + WT / 2), Y4 + CH3 / 2, czc),
                 (WT, CH3, czl), T_WALL, "x", rough=0.9)
        c15.shard(KM3, [wl])
        c15.solid(hit("C15_h%s" % nm, (68.0 + sgn * (CW / 2 + WT / 2), Y4 + CH3 / 2, czc),
                      (WT, CH3, czl)))
    cl = box("C15_c", (68.0, Y4 + CH3 + WT / 2, czc), (CW + WT * 2, WT, czl), T_CEIL, "y",
             rough=0.94)
    c15.shard(KM3, [cl])
    g15 = glow("C15_g", (68.0, Y4 + 0.02, CZ0 + 0.09), (CW, 0.04, 0.06), GOLD, 1.25)
    c15.shard(KM3, [g15], glows=[g15])
    c15.mover(UPanel, (68.0, Y4 - DH / 2 - 0.30, UZ1 + WT / 2))
    plight("C15_fill", (68.0, Y4 + 2.5, 196.0), [1.0, 0.99, 0.96], 9.0, 13.0)
    # ★印は必ず【焦点の真上】に置くこと。ここだけ 1.1m ずらしてあって、
    #   印の上に立っても 0% しか繋がらない状態になっていた(机上検査 [5] が捕まえた)
    mark("C15_mark", (F15[0], Y4 + 0.006, F15[2]), T_PAINT, (0.80, 0.79, 0.75), rough=0.9)

    # ============================================================ X 終わりの間（継ぎ目16: 扉）
    XX0, XX1, XZ0, XZ1, XH = 64.0, 72.0, 206.3, 214.0, 3.0
    shell("X3", XX0, XX1, XZ0, XZ1, XH, T_CARPET, T_WALL, y=Y4, walls="we")
    for z in (208.6, 212.0):
        troffer("X3_tr%.0f" % z, 68.0, Y4 + XH, z, on=(z < 210.0))
    bench("X3_bench", 65.3, Y4, 211.2, axis="z")
    door_closed("X3_d1", 72.0 - 0.07, Y4, 209.6, axis="x", inset=-0.045)
    wall_with_door("X3_n", "z", XZ1 + WT / 2, XX0 - WT, XX1 + WT, Y4, XH, 68.0, DW, DH, T_WALL)
    xpanel = box("C16_Panel", (68.0, Y4 + DH / 2, XZ1 + WT / 2), (DW, DH, WT - 0.02), T_WALL, "z",
                 solid=True)
    # 扉の向こう(白い部屋 = 終わり)
    box("Y3_flr", (68.0, Y4 - WT / 2, 216.9), (4.4, WT, 5.6), T_PAINT, "y", rough=0.9, solid=True)
    box("Y3_cil", (68.0, Y4 + 3.2, 216.9), (4.4, WT, 5.6), T_PAINT, "y", rough=0.9)
    for sgn in (-1, 1):
        box("Y3_w%d" % sgn, (68.0 + sgn * 2.2, Y4 + 1.6, 216.9), (WT, 3.2, 5.6), T_PAINT, "x",
            rough=0.9, solid=True)
    # ★白い部屋は終わりではなく【第四幕への戸口】
    wall_with_door("Y3_n", "z", 219.7, 65.65, 70.35, Y4, 3.2, 68.0, DW, DH, T_PAINT)
    door_casing("Y3_nc", "z", 219.55, 68.0, Y4, DW, DH)
    for sgn in (-1, 1):
        glow("Y3_g%d" % sgn, (68.0 + sgn * 1.86, Y4 + 1.5, 219.52), (0.9, 2.9, 0.04),
             [1.0, 0.98, 0.94], 1.05)
    plight("Y3_l1", (68.0, Y4 + 2.2, 217.4), [1.0, 0.98, 0.94], 10.0, 9.0)

    # ---- 継ぎ目 16: 4 片が噛み合って扉になり、【丁番でひらく】 ----
    F16 = (68.0 - 0.55, Y4 + EYE, 207.6)
    c16 = Conn(16, F16, 2.2, 13.0, (68.0, Y4 + 1.2, XZ1 - 0.1), "door")
    ZF16 = XZ1 - 0.08
    sgn_b = box("C16_signb", (68.0, Y4 + DH + 0.36, ZF16 - 0.02), (0.68, 0.32, 0.06), T_METAL, "z",
                rough=0.5, color=[0.35, 0.35, 0.34])
    sgn16 = sign_plate("C16_sign", 68.0, Y4 + DH + 0.36, ZF16 - 0.02, color=(0.34, 0.38, 0.35))
    plight("C16_sign_l", (68.0, Y4 + DH + 0.06, ZF16 - 0.35), GREEN, 0.0, 1.8)
    c16.shard(1.0, [sgn_b, sgn16])
    lp16, lg16 = frame_half("C16_L", -1, 68.0, Y4, ZF16, DW, DH)
    c16.shard(0.55, lp16, glows=lg16)
    rp16, rg16 = frame_half("C16_R", +1, 68.0, Y4, ZF16, DW, DH)
    c16.shard(0.38, rp16, glows=rg16)
    leaf16 = box("C16_Leaf", (68.0, Y4 + DH / 2, ZF16 - 0.12), (DW - 0.04, DH - 0.04, 0.06),
                 T_DOOR, "z", rough=0.55, tile=(DW / 2, DH / 2))
    knob16 = box("C16_Knob", (68.0 + DW / 2 - 0.16, Y4 + 1.02, ZF16 - 0.19), (0.07, 0.07, 0.07),
                 T_METAL, "z", rough=0.35, metal=0.8, color=[0.75, 0.72, 0.62])
    kick16 = glow("C16_Lfink", (68.0, Y4 + 0.03, ZF16 - 0.12), (DW - 0.06, 0.03, 0.03), GOLD, 1.25)
    c16.shard(0.71, [leaf16, knob16, kick16], glows=[kick16])
    c16.mover(xpanel, (68.0, Y4 - DH / 2 - 0.30, XZ1 + WT / 2))
    c16.lamp("C16_sign", 1.0, dur=0.7, delay=0.15)
    # ★丁番。shard() の後に呼んでも【実体の位置】から回る(Conn.real_pos が引き直す)。
    #   焼き込んだ座標をそのまま使っていたのが「扉が飛んでから回る」不具合の原因だった。
    HINGE16 = (68.0 - DW / 2, Y4 + DH / 2, ZF16 - 0.12)
    for e2 in (leaf16, knob16, kick16):
        c16.hinge(e2, HINGE16, -82.0)
    plight("C16_fill", (68.0, Y4 + 2.4, 210.4), WARM, 8.0, 10.0)


# ================================================================ 第四幕（大展示室・継ぎ目 17〜21）
def act4(Y4, DW, DH):
    """★これまでと違い【一つの大きな部屋に 5 つ】。順番は自由。
    しかも 4 つは今までと【規則そのものが違う】ので、同じ手が通用しない。

      18 直視しない  周辺視(24〜68度)でだけ成立する。正面で見ると絶対に決まらない
      19 触れる      焦点を使わない。柱の頭と板の先端が【画面の上で重なれば】くっつく
      20 二つ同時    一つの立ち位置で、別々の方向にある 2 つを同時に満たす
      21 暗の一瞬    明滅する照明が【暗い間だけ】成立する。明るいと絶対に決まらない
      17 巡る        4 つの島それぞれから 1 枚ずつ。歩き回って階段を組み上げる

    18〜21 が 4 本の橋を架け、その先の島が 17 の 4 つの立ち位置になっている。
    ＝【どれから手を付けてもよく、最後に全部が要る】。
    """
    EY = Y4 + EYE
    GX0, GX1, GZ0, GZ1, GH = 56.0, 82.0, 222.3, 246.0, 8.0
    PX0, PX1, PZ0, PZ1, PY = 59.5, 78.5, 225.5, 242.8, 3.00     # 中央の窪み(底 y=3.0)

    # ---- 連絡通路(白い部屋 -> 大展示室) ----
    shell("W4", 66.0, 70.0, 219.9, 222.3, 2.9, T_CARPET, T_WALL, y=Y4, walls="we",
          floor=False, ceil=False)
    # ★床は大展示室の回廊(z=222.0 から)と重ならない所で止める
    box("W4_flr", (68.0, Y4 - WT / 2, 220.95), (4.6, WT, 2.7), T_CARPET, "y", rough=0.95,
        solid=True)
    box("W4_cil", (68.0, Y4 + 2.9 + WT / 2, 220.95), (4.6, WT, 2.7), T_CEIL, "y", rough=0.94)
    troffer("W4_tr", 68.0, Y4 + 2.9, 221.1, on=True)

    # ---- 部屋の殻(床は穴あきなので自前で敷く) ----
    shell("G1", GX0, GX1, GZ0, GZ1, GH, T_CONC, T_CONC, y=Y4, walls="wen",
          ceil_tex=T_CONC, base=False, floor=False)
    wall_with_door("G1_s", "z", GZ0 - WT / 2, GX0 - WT, GX1 + WT, Y4, GH, 68.0, DW, DH, T_CONC)
    # 回廊(窪みの周り 4 枚)。★重ならないように帯で敷く
    box("G1_fs", (69.0, Y4 - WT / 2, (GZ0 - WT + PZ0) / 2), (GX1 - GX0 + WT * 2, WT,
        PZ0 - GZ0 + WT), T_CONC, "y", rough=0.95, solid=True)
    box("G1_fn", (69.0, Y4 - WT / 2, (PZ1 + GZ1 + WT) / 2), (GX1 - GX0 + WT * 2, WT,
        GZ1 + WT - PZ1), T_CONC, "y", rough=0.95, solid=True)
    box("G1_fw", ((GX0 - WT + PX0) / 2, Y4 - WT / 2, (PZ0 + PZ1) / 2), (PX0 - GX0 + WT, WT,
        PZ1 - PZ0), T_CONC, "y", rough=0.95, solid=True)
    box("G1_fe", ((PX1 + GX1 + WT) / 2, Y4 - WT / 2, (PZ0 + PZ1) / 2), (GX1 + WT - PX1, WT,
        PZ1 - PZ0), T_CONC, "y", rough=0.95, solid=True)
    box("G1_pit", ((PX0 + PX1) / 2, PY - WT / 2, (PZ0 + PZ1) / 2), (PX1 - PX0, WT, PZ1 - PZ0),
        T_CONC, "y", rough=0.95, solid=True)
    for z in (PZ0, PZ1):                                    # 窪みの側面(深さが読める)
        box("G1_pf%.0f" % z, ((PX0 + PX1) / 2, (PY + Y4) / 2, z), (PX1 - PX0, Y4 - PY, 0.10),
            T_CONC, "z", rough=0.92, color=[0.58, 0.58, 0.56])
    for x in (PX0, PX1):
        box("G1_pg%.0f" % x, (x, (PY + Y4) / 2, (PZ0 + PZ1) / 2), (0.10, Y4 - PY, PZ1 - PZ0),
            T_CONC, "x", rough=0.92, color=[0.58, 0.58, 0.56])
    plight("G1_pl", (69.0, PY + 1.6, 234.0), COOL, 4.0, 12.0)

    # ---- 4 つの島(それぞれ 17 の立ち位置になる) ----
    # 北の島(B)だけ東西に長い。橋は西寄り、出口の階段は東寄りに架かるので頭上が空く
    ISL = {"A": (64.3, 233.95), "B": (67.5, 238.8), "C": (73.7, 233.95), "D": (68.0, 229.5)}
    ISW = {"A": 3.6, "B": 7.0, "C": 3.6, "D": 3.6}
    for nm, (ix, iz) in ISL.items():
        box("G1_is" + nm, (ix, Y4 - WT / 2, iz), (ISW[nm], WT, 3.6), T_CONC, "y",
            rough=0.95, solid=True)
        mark("G1_ib" + nm, (ix, Y4 + 0.006, iz), T_CONC, (0.74, 0.74, 0.72), rough=0.9)
        plight("G1_il" + nm, (ix, Y4 + 3.2, iz), WARM, 7.0, 9.0)

    # ---- 照明 ----
    for x, z, on in ((59.0, 226.0, True), (79.0, 226.0, True), (59.0, 243.0, False),
                     (79.0, 243.0, True), (68.0, 224.5, True)):
        box("G1_ls%.0f_%.0f" % (x, z), (x, Y4 + GH - 0.35, z), (0.9, 0.24, 0.9), T_METAL, "y",
            rough=0.45, metal=0.6, color=[0.42, 0.42, 0.40])
        if on:
            glow("G1_lg%.0f_%.0f" % (x, z), (x, Y4 + GH - 0.49, z), (0.64, 0.05, 0.64), WARM, 1.5)
            plight("G1_ll%.0f_%.0f" % (x, z), (x, Y4 + GH - 0.9, z), WARM, 13.0, 17.0)
    # ★北の橋のあたりだけを照らす明滅バンク(継ぎ目21 が「暗の一瞬」で成立するため)
    DARKN = []
    for x in (65.0, 71.0):
        nm = "G1_bk%.0f" % x
        troffer(nm, x, Y4 + GH, 243.4, on=True, intensity=12.0, rng=15.0)
        DARKN.append(nm)

    # ================================================== 継ぎ目 18: 直視しない（西の橋）
    # ★焦点は橋の【手前側】。回廊を北へ歩く向きから見ると橋は 50 度ほど横にある。
    #   正面に据えた瞬間に成立しなくなるので、「見ないまま合わせる」ことになる。
    F18 = (57.5, EY, 228.6)
    c18 = Conn(18, F18, 2.5, 14.0, (61.0, Y4, 233.95), "dont-look", peri=True)
    # ★橋は窪みの見切り(x=PX0+0.05)から島の際(x=62.5)まで。手前の板だけ 1.45m にして
    #   見切りへ潜らせない(0.05m でも窪みの底から見上げると板が壁を突き抜けて見える)
    for i, k in enumerate((0.44, 0.62)):
        w18 = 1.45 if i == 0 else 1.5
        xc18 = PX0 + 0.05 + (0.0 if i == 0 else 1.45) + w18 / 2
        pl = box("C18_p%d" % i, (xc18, Y4 - 0.09, 233.95), (w18, 0.18, 2.0),
                 T_METAL, "y", rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47])
        g = glow("C18_g%d" % i, (xc18, Y4 + 0.01, 232.99), (w18 - 0.1, 0.04, 0.06),
                 GOLD, 1.25)
        c18.shard(k, [pl, g], glows=[g])
        c18.solid(hit("C18_h%d" % i, (xc18, Y4 - 0.09, 233.95), (w18 + 0.2, 0.18, 2.0),
                      kinematic=True))
    mark("C18_mark", (F18[0], Y4 + 0.006, F18[2]), T_CONC, (0.74, 0.74, 0.72), rough=0.9)
    # 視線を北へ誘う灯り(これを見ていると橋が視野の端に入る)
    exit_sign("G1_lure", 57.8, Y4 + 2.5, 242.6)
    plight("C18_fill", (59.6, Y4 + 3.0, 231.0), WARM, 8.0, 10.0)

    # ================================================== 継ぎ目 19: 触れる（東の橋）
    # ★焦点は無い。窪みに立つ柱の頭(a)と、浮いている板の先端(b)が
    #   【画面の上で重なった】ら成立する。奥行きには寛容で、向きに厳しい。
    box("C19_col", (72.0, (PY + 11.6) / 2, 230.0), (0.62, 11.6 - PY, 0.62), T_CONC, "x",
        rough=0.9, solid=True, color=[0.62, 0.62, 0.60])
    cap = glow("C19_cap", (72.0, 11.60, 230.0), (0.30, 0.30, 0.30), [1.0, 0.90, 0.62], 2.2)
    DISP19 = (-1.90, 2.47, -0.35)
    tip = glow("C19_tip", (78.40, 7.75, 233.95), (0.26, 0.26, 0.26), [1.0, 0.90, 0.62], 2.2)
    p19 = []
    W19 = (1.5, 1.45)                       # ★奥の板は窪みの見切り(x=78.45)で止める
    X19 = (76.25, 77.725)
    for i in range(2):
        p19.append(box("C19_p%d" % i, (X19[i], Y4 - 0.09, 233.95), (W19[i], 0.18, 2.0),
                       T_METAL, "y", rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47]))
    c19 = Conn(19, (79.5, EY, 236.0), 1.3, 9.0, (76.0, Y4 + 1.2, 234.5), "touch")
    c19.touch = dict(a=[72.0, 11.60, 230.0],
                     b=[round(78.40 + DISP19[0], 3), round(7.75 + DISP19[1], 3),
                        round(233.95 + DISP19[2], 3)],
                     near=3.0, far=12.0)
    c19.shard_free(p19 + [tip], DISP19, dk=0.62, glows=[tip])
    for i in range(2):
        c19.solid(hit("C19_h%d" % i, (X19[i], Y4 - 0.09, 233.95), (W19[i] + 0.2, 0.18, 2.0),
                      kinematic=True))
    mark("C19_mark", (79.5, Y4 + 0.006, 236.0), T_CONC, (0.74, 0.74, 0.72), rough=0.9)
    plight("C19_fill", (77.0, Y4 + 3.0, 235.6), WARM, 8.0, 11.0)

    # ================================================== 継ぎ目 20: 二つ同時（南の橋）
    # ★一つの立ち位置で、別々の方向にある 2 つを同時に満たす。
    #   管が交差するので確定域が小さく、【一点に追い込む】手触りになる。
    F20 = (63.5, EY, 223.6)
    c20 = Conn(20, F20, 3.4, 17.0, (65.5, Y4 + 0.9, 228.8), "two-at-once")
    for i, k in enumerate((0.40, 0.58)):
        zc = 226.05 + i * 1.10                       # 回廊(225.5) と 島D(227.7) の間ぴったり
        pl = box("C20_p%d" % i, (68.0, Y4 - 0.09, zc), (2.0, 0.18, 1.10),
                 T_METAL, "y", rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47])
        c20.shard(k, [pl])
        c20.solid(hit("C20_h%d" % i, (68.0, Y4 - 0.09, zc), (2.0, 0.18, 1.36), kinematic=True))
    # ★もう一方の拘束は【同じ画面に収まる位置】へ置くこと。視野の外にあると
    #   合っているかどうかが見えず、ただの理不尽になる(橋の左 17 度・枠の右 17 度)
    FX, FZ = 63.0, 231.0
    fr = []
    for nm, c_, s_ in (("l", (FX - 0.95, Y4 + 1.80, FZ), (0.14, 2.10, 0.14)),
                       ("r", (FX + 0.95, Y4 + 1.80, FZ), (0.14, 2.10, 0.14)),
                       ("t", (FX, Y4 + 2.78, FZ), (2.04, 0.14, 0.14)),
                       ("b", (FX, Y4 + 0.82, FZ), (2.04, 0.14, 0.14))):
        fr.append(box("C20_f" + nm, c_, s_, T_PAINT, "z", rough=0.45, color=FRAME_COL))
    gw = glow("C20_fg", (FX, Y4 + 1.80, FZ + 0.09), (1.76, 1.82, 0.04), [1.0, 0.97, 0.90], 1.20)
    c20.shard(0.34, fr + [gw], glows=[gw])
    mark("C20_mark", (F20[0], Y4 + 0.006, F20[2]), T_CONC, (0.74, 0.74, 0.72), rough=0.9)
    plight("C20_fill", (68.0, Y4 + 3.0, 227.4), WARM, 8.0, 11.0)

    # ================================================== 継ぎ目 21: 暗の一瞬（北の橋）
    # ★明滅する照明が【暗い間だけ】成立する。明るいと絶対に決まらない。
    #   位置を合わせてから、暗くなる瞬間を待つ。
    F21 = (70.0, EY, 244.6)
    c21 = Conn(21, F21, 3.2, 16.0, (65.5, Y4, 241.7), "dark-only", dark=True,
               dark_lights=DARKN)
    for i, k in enumerate((0.42, 0.60)):
        zc = 242.25 - i * 1.10                       # 回廊(242.8) と 島B(240.6) の間ぴったり
        pl = box("C21_p%d" % i, (65.5, Y4 - 0.09, zc), (2.0, 0.18, 1.10),
                 T_METAL, "y", rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47])
        g = glow("C21_g%d" % i, (65.5, Y4 + 0.01, zc), (1.9, 0.04, 0.06), GOLD, 1.25)
        c21.shard(k, [pl, g], glows=[g])
        c21.solid(hit("C21_h%d" % i, (65.5, Y4 - 0.09, zc), (2.0, 0.18, 1.36), kinematic=True))
    mark("C21_mark", (F21[0], Y4 + 0.006, F21[2]), T_CONC, (0.74, 0.74, 0.72), rough=0.9)

    # ================================================== 継ぎ目 17: 巡る（出口の階段）
    # ★破片ごとに【別の島】が焦点。4 つの島を回って 1 枚ずつ置いていく。
    #   一箇所で全部は決まらない ＝ 今までのどれとも違う歩き方になる。
    SZ4, RISE4, SW4 = 240.9, 0.30, 2.4
    RUN4 = (GZ1 - SZ4) / 10.0        # 10 段でちょうど壁の内側(246.0)に着く = 0.51
    c17 = Conn(17, (ISL["A"][0], EY, ISL["A"][1]), 1.3, 9.0, (68.0, Y4 + 1.4, 243.0),
               "visit", per_shard=True)
    c17.solve_order = 21.5         # ★4 つの島は 18〜21 が架かって初めて立てる
    groups = [("A", 0, 3), ("D", 3, 6), ("C", 6, 8), ("B", 8, 10)]
    for nm, a, b in groups:
        ents = []
        for i in range(a, b):
            top = Y4 + RISE4 * (i + 1)
            ents.append(box("C17_s%d" % i, (68.0, top - 0.11, SZ4 + RUN4 * i),
                            (SW4, 0.22, RUN4), T_METAL, "y", rough=0.5, metal=0.5,
                            color=[0.50, 0.50, 0.47]))
            c17.solid(hit("C17_h%d" % i, (68.0, top - 0.11, SZ4 + RUN4 * i),
                          (SW4, 0.22, RUN4 + 0.26), kinematic=True))
        # ★島によって階段までの距離が 5〜14m と違うので、k を距離で釣り合わせる。
        #   同じ k にすると、近い島だけ極端に敏感になって lock を共有できない
        c17.shard({"A": 0.55, "D": 0.30, "C": 0.34, "B": 0.62}[nm], ents,
                  focus=(ISL[nm][0], EY, ISL[nm][1]))
    # 出口(組み上がった階段の先。北壁の中段)
    XY4 = Y4 + RISE4 * 10
    wall_hole("G1_n2", "z", GZ1 + WT / 2, GX0 - WT, GX1 + WT, Y4, Y4 + GH, 68.0, DW, XY4, DH,
              T_CONC)
    for e2 in list(ES):
        if e2["name"] == "G1_n":                       # shell が建てた無地の北壁を捨てる
            ES.remove(e2)
    door_casing("G1_nc", "z", GZ1 - 0.02, 68.0, XY4, DW, DH)
    exit_sign("G1_exit", 68.0, XY4 + DH + 0.34, GZ1 - 0.10)
    plight("C17_fill", (68.0, XY4 + 1.8, 242.0), WARM, 9.0, 11.0)

    # ---- 出口の先(白い部屋 = 終わり) ----
    box("V4_flr", (68.0, XY4 - WT / 2, 249.05), (4.4, WT, 5.5), T_PAINT, "y", rough=0.9,
        solid=True)
    box("V4_cil", (68.0, XY4 + 3.2, 249.0), (4.4, WT, 5.6), T_PAINT, "y", rough=0.9)
    for sgn in (-1, 1):
        box("V4_w%d" % sgn, (68.0 + sgn * 2.2, XY4 + 1.6, 249.0), (WT, 3.2, 5.6), T_PAINT, "x",
            rough=0.9, solid=True)
    # ★白い部屋は「終わり」ではなく幕間になった(第一幕→第二幕と同じ扱い)。北へ抜ける
    wall_hole("V4_n", "z", 251.8, 65.65, 70.35, XY4, XY4 + 3.2, 68.0, DW, XY4, DH, T_PAINT)
    for sgn in (-1, 1):
        glow("V4_g%d" % sgn, (68.0 + sgn * 1.5, XY4 + 1.5, 251.62), (1.3, 2.9, 0.04),
             [1.0, 0.98, 0.94], 1.05)
    plight("V4_l1", (68.0, XY4 + 2.2, 249.4), [1.0, 0.98, 0.94], 10.0, 9.0)
    return XY4


# ================================================================ 第五幕（環の間・継ぎ目 22〜25）
def act5(Y5, DW, DH):
    """第五幕 — 環の間。ここまでの「印に立って見る」だけの遊びを【組み合わせ】へ上げる幕。
    扉も、渡し板の橋も 1 つも出さない。

      22 かくれて合わせる  柱の陰に入って偽物を隠さないと決まらない → 井戸に【床】が閉じる
      23 床の影にはめる    影が床に描いてある(目標が初めて目に見える) → 出来るのは影の場所ではない
      24 三つの印         2 つは嘘の印。22/23 を解いた後、【棚の上】でしか成立しない
                          → 北壁から片持ちの段が生えて上の踊り場へ
      25 四つ同時         1 点で北・南・東・西を同時に満たす → 【北壁が割れて開く】

    ★連鎖(needs)と、焦点そのものを「前の継ぎ目が作った足場の上」に置くことで、
      順番に解かないと立てないようにしてある ＝ 一問一答ではなく積み上げになる。
    """
    EY5 = Y5 + EYE
    X0, X1, Z0, Z1, HH = 52.0, 86.0, 258.0, 302.0, 9.0
    PZ0, PZ1, PDEP = 272.0, 284.0, 6.0            # 井戸(部屋の全幅・深さ 6m)

    # ---- 白い部屋 → 環の間 ----
    corridor("X5", 66.6, 69.4, 251.95, Z0, Y5, 2.6, T_CARPET, T_WALL)
    slab("X5_w", "x", 66.6 - WT / 2, 251.95, Z0, Y5, Y5 + 2.6, T_WALL)
    slab("X5_e", "x", 69.4 + WT / 2, 251.95, Z0, Y5, Y5 + 2.6, T_WALL)
    troffer("X5_tr", 68.0, Y5 + 2.6, 254.8, on=True)

    # ---- 環の間(34 x 44m。ここまでで一番広い) ----
    shell("W5", X0, X1, Z0, Z1, HH, T_CONC, T_CONC, y=Y5, walls="we", ceil_tex=T_CONC,
          base=False, floor=False)
    wall_with_door("W5_s", "z", Z0 - WT / 2, X0 - WT, X1 + WT, Y5, HH, 68.0, DW, DH, T_CONC)
    # 北壁の開口は【中段】(踊り場と同じ高さ)。継ぎ目 25 が割れて開くまで塞がっている
    XIT_X, XIT_W, XIT_Y, XIT_H = 56.0, 2.20, Y5 + 2.40, 2.40
    wall_hole("W5_n", "z", Z1 + WT / 2, X0 - WT, X1 + WT, Y5, Y5 + HH,
              XIT_X, XIT_W, XIT_Y, XIT_H, T_CONC)
    box("W5_fs", ((X0 + X1) / 2, Y5 - WT / 2, (Z0 + PZ0) / 2),
        (X1 - X0 + WT * 2, WT, PZ0 - Z0), T_CONC, "y", rough=0.95, solid=True)
    box("W5_fn", ((X0 + X1) / 2, Y5 - WT / 2, (PZ1 + Z1) / 2),
        (X1 - X0 + WT * 2, WT, Z1 - PZ1), T_CONC, "y", rough=0.95, solid=True)
    box("W5_pit", ((X0 + X1) / 2, Y5 - PDEP - WT / 2, (PZ0 + PZ1) / 2),
        (X1 - X0, WT, PZ1 - PZ0), T_CONC, "y", rough=0.95, solid=True)
    # 井戸の見切り(深さが読める)。★床スラブの面より【内側】へ置く(面が重なるとちらつく)
    for z, sgn in ((PZ0 + 0.05, 1), (PZ1 - 0.05, -1)):
        box("W5_pf%.0f" % z, ((X0 + X1) / 2, (Y5 - PDEP + Y5) / 2, z),
            (X1 - X0, PDEP, 0.10), T_CONC, "z", rough=0.92, color=[0.58, 0.58, 0.56])
    for lz in (275.0, 281.0):
        plight("W5_pl%.0f" % lz, (68.0, Y5 - PDEP + 2.6, lz), COOL, 7.0, 13.0)

    # ---- 柱の森(南半分)。★このうち 1 本が継ぎ目 22 の「隠すもの」になる ----
    for px in (58.0, 68.0, 78.0):
        for pz in (262.0, 268.0):
            box("W5_c%.0f_%.0f" % (px, pz), (px, Y5 + HH / 2, pz), (1.4, HH, 1.4), T_CONC,
                "x", rough=0.92, solid=True, color=[0.61, 0.61, 0.59])
    # ★灯は【弱く・飛び飛びに】。最初 15.0/19.0 で 6 灯点けたら、34x44m が
    #   まるごと白飛びして「ただの白い箱」になった(第四幕の大展示室と並べて確認)。
    #   リミナルの絵は明暗の縞で出来ているので、暗い区画を必ず残す。
    for lx, lz, on in ((57.0, 261.0, True), (68.0, 261.0, False), (79.0, 261.0, False),
                       (57.0, 268.0, False), (68.0, 268.0, True), (79.0, 268.0, False),
                       (57.0, 288.0, False), (68.0, 288.0, True), (79.0, 288.0, False),
                       (57.0, 296.0, True), (68.0, 296.0, False), (79.0, 296.0, True)):
        box("W5_ls%.0f_%.0f" % (lx, lz), (lx, Y5 + HH - 0.35, lz), (1.0, 0.24, 1.0), T_METAL,
            "y", rough=0.45, metal=0.6, color=[0.42, 0.42, 0.40])
        if on:
            glow("W5_lg%.0f_%.0f" % (lx, lz), (lx, Y5 + HH - 0.49, lz), (0.72, 0.05, 0.72),
                 WARM, 1.5)
            plight("W5_ll%.0f_%.0f" % (lx, lz), (lx, Y5 + HH - 1.1, lz), WARM, 9.0, 14.0)
    # 緑の非常口で north へ誘う(この作品の案内はこれと明暗と擦れ跡だけ)
    exit_sign("W5_lure1", 68.0, Y5 + 3.0, PZ1 + 0.30)
    exit_sign("W5_lure2", 77.0, Y5 + 3.4, Z1 - 0.10)

    # ================================================== 継ぎ目 22: かくれて合わせる（遮蔽）
    # ★偽の板が視界にある限り決まらない。柱の陰に入れて【消す】と決まる。
    #   「どこに立つか」に「何を見ないようにするか」が重なる ＝ 今までに無い探し方。
    # ★焦点は「隠すのに使う柱」の【手前】ではなく【横】に置くこと。最初は柱の真南に
    #   置いたので、立ち位置から見て柱が画面の右半分を塞ぎ、肝心の破片が見えなかった
    #   (解けるのに読めない絵になっていた。実機で確認して直した)。
    #   いま: 目標(井戸の蓋)は北。偽の板は【西】の柱の陰。方向が分かれている。
    # ★遮蔽は【近くの細い物】で隠すこと。太い柱で隠すと、陰の帯が確定域より広くなって
    #   規則が一度も効かない(最初は 1.4m の柱でやって、±1.0m の帯 > ±0.6m の確定域 =
    #   ただの飾りだった)。細い配管を立ち位置の 2.3m 先に立て、偽の板をその 10m 先へ置くと
    #   陰の帯は ±0.23m になり、確定域を実際に切る ＝ 横へ一歩ずれると偽物が顔を出す。
    F22 = (63.50, EY5, 265.60)
    PIPE = (61.80, 266.40)                                # 隠すのに使う配管(細い)
    LURE = (54.45, Y5 + 0.82, 269.86)                     # 偽の板(絶対に実体化しない)
    box("W5_pipe", (PIPE[0], Y5 + HH / 2, PIPE[1]), (0.30, HH, 0.30), T_METAL, "x",
        rough=0.5, metal=0.55, color=[0.50, 0.50, 0.48], solid=True)
    c22 = Conn(22, F22, 2.6, 14.0, (68.0, Y5 + 0.4, 278.0), "hide-behind",
               occl=dict(p=[round(v, 3) for v in LURE],
                         boxes=[[PIPE[0] - 0.15, Y5, PIPE[1] - 0.15,
                                 PIPE[0] + 0.15, Y5 + HH, PIPE[1] + 0.15]]))
    # ★偽の板は【浮遊中の破片と同じ見かけ】にする(原寸で置くと一目で別物と分かる)
    box("W5_lure", LURE, (3.30, 0.10, 2.15), T_CONC, "y", rough=0.9, color=[0.55, 0.55, 0.53])
    glow("W5_lureg", (LURE[0] - 1.62, LURE[1] + 0.06, LURE[2]), (0.04, 0.03, 2.1), GOLD, 1.25)
    plight("C22_lurel", (LURE[0] + 1.0, LURE[1] + 1.6, LURE[2] - 1.2), WARM, 7.0, 9.0)
    # ★k を下げすぎると浮遊中の破片が【柱を突き抜ける】(0.40 で 7cm めり込んでいた)
    for i, k in enumerate((0.55, 0.66, 0.76)):
        zc = PZ0 + 2.0 + 4.0 * i
        pl = box("C22_p%d" % i, (68.0, Y5 + 0.09, zc), (6.0, 0.18, 3.90), T_CONC, "y",
                 rough=0.9, color=[0.55, 0.55, 0.53])
        g = glow("C22_g%d" % i, (65.05, Y5 + 0.20, zc), (0.06, 0.04, 3.8), GOLD, 1.25)
        c22.shard(k, [pl, g], glows=[g])
        c22.solid(hit("C22_h%d" % i, (68.0, Y5 + 0.09, zc), (6.0, 0.18, 4.10), kinematic=True))
    mark("C22_mark", (F22[0], Y5 + 0.008, F22[2]), T_CONC, (0.74, 0.74, 0.72), rough=0.9)
    plight("C22_fill", (68.0, Y5 + 2.6, 271.0), WARM, 9.0, 12.0)

    # ================================================== 継ぎ目 23: 床の影にはめる
    # ★この作品で初めて【目標が目に見える】継ぎ目。床に落ちた影に浮遊物を重ねる。
    #   影は焦点から床への投影そのものなので、焦点に立つと破片が影にぴたりと収まる。
    # ★★対象は 0.60m より高くしないこと。床への影は 1/(1 - h/1.70) 倍に伸びるので、
    #   1.20m の階段でやったら上の段の影が 3.4 倍に伸びて【部屋の外へ出た】。
    #   低い物なら伸びは 1.55 倍で収まり、しかも影は【これから建つ場所】に落ちる。
    # ★焦点の置き方で影の落ちる先が決まる(影は焦点から見て破片の【向こう側】へ伸びる)。
    #   南から見上げる位置だと影が棚の陰に入って読めない。北西へ寄せて、影が
    #   棚の南東の開けた床に落ちるようにした。
    F23 = (70.50, EY5, 295.50)
    c23 = Conn(23, F23, 2.4, 13.0, (77.2, Y5 + 0.3, 294.8), "floor-shadow")
    # 登った先の棚(最初から実在。何を組もうとしているかの見本になる)
    box("W5_deck", (77.0, Y5 + 0.30, 299.0), (6.0, 0.60, 6.0), T_METAL, "y", rough=0.5,
        metal=0.5, color=[0.48, 0.48, 0.46], solid=True)
    st23 = []
    for j2, (h, zc) in enumerate(((0.30, 294.5), (0.60, 295.5))):
        st23.append(box("C23_s%d" % j2, (77.2, Y5 + h / 2, zc), (2.4, h, 1.0), T_METAL, "y",
                        rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47]))
        c23.solid(hit("C23_h%d" % j2, (77.2, Y5 + h / 2, zc), (2.4, h, 1.12), kinematic=True))
    g23 = glow("C23_g", (77.2, Y5 + 0.62, 295.5), (2.3, 0.04, 0.06), GOLD, 1.25)
    c23.shard(0.52, st23 + [g23], glows=[g23])
    floor_shadow("C23_sh", F23, st23 + [g23], Y5)
    mark("C23_mark", (F23[0], Y5 + 0.008, F23[2]), T_CONC, (0.74, 0.74, 0.72), rough=0.9)
    plight("C23_fill", (74.0, Y5 + 2.8, 292.0), WARM, 10.0, 13.0)

    # ================================================== 継ぎ目 24: 三つの印（偽の印 + 連鎖）
    # ★印が 3 つある。2 つは嘘。しかも 22/23 を解いて【棚の上】に立たないと本物も成立しない。
    F24 = (77.00, Y5 + 0.60 + EYE, 299.00)
    c24 = Conn(24, F24, 2.2, 12.0, (68.0, Y5 + 1.6, 300.8), "three-marks",
               needs=(22, 23), min_y=F24[1] - 0.25, max_y=F24[1] + 0.25)
    for j2 in range(6):
        xc = 72.8 - 2.4 * j2
        top = Y5 + 0.90 + 0.30 * j2
        # ★奥行きは 2.4m 要る。1.2m だと棚から西へ歩いた時に段の南を踏み外して落ちる
        pl = box("C24_p%d" % j2, (xc, top - 0.11, 300.80), (2.7, 0.22, 2.40), T_METAL, "y",
                 rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47])
        g = glow("C24_g%d" % j2, (xc, top + 0.01, 299.65), (2.6, 0.04, 0.06), GOLD, 1.25)
        # ★k は【広く】散らすこと。0.44〜0.84 の等間隔だと浮遊中の板どうしが重なり、
        #   どれがどれだか読めなくなる(机上検査 [1] が 6cm の重なりで捕まえた)
        c24.shard((0.42, 0.53, 0.64, 0.75, 0.84, 0.92)[j2], [pl, g], glows=[g])
        c24.solid(hit("C24_h%d" % j2, (xc, top - 0.11, 300.80), (3.0, 0.22, 2.40),
                      kinematic=True))
    # ★遠い対象(西へ 16m の段)だけだと角度が鈍く、確定域が 6.5m2 まで広がって
    #   「どの印でも解ける」になってしまう。棚の際の手すり = 近い対象を 1 つ混ぜて締める。
    rl = box("C24_rail", (79.60, Y5 + 1.15, 299.0), (0.09, 0.09, 5.4), T_METAL, "y",
             rough=0.45, metal=0.7, color=[0.56, 0.56, 0.53])
    rg = glow("C24_railg", (79.60, Y5 + 1.22, 299.0), (0.03, 0.03, 5.0), GOLD, 1.25)
    c24.shard(0.55, [rl, rg], glows=[rg])
    mark("C24_mark", (F24[0], Y5 + 0.608, F24[2]), T_METAL, (0.66, 0.66, 0.63), rough=0.6)
    # 嘘の印(ここでは何も起きない)。★大きさも色も本物と同じにする
    for j2, (mx, mz) in enumerate(((74.6, 297.2), (79.4, 300.6))):
        box("C24_dud%d" % j2, (mx, Y5 + 0.608, mz), (1.20, 0.012, 1.20), T_METAL, "y",
            rough=0.6, color=[0.66, 0.66, 0.63], tile=(0.6, 0.6))
    plight("C24_fill", (70.0, Y5 + 3.4, 299.0), WARM, 11.0, 15.0)

    # ================================================== 継ぎ目 25: 四つ同時（仕上げ）
    # ★1 つの立ち位置で北・南・東・西の 4 方向を同時に満たす。管が 4 本交差するので
    #   確定域は狭く、しかも【明かりが落ちる 1 秒】の間しか決まらない。22〜24 が前提。
    # ★東端は最後の段(x=59.3 から)の面で止める。6.6m だと段が 0.3m 潜って天端がちらつく
    box("W5_land", (56.10, Y5 + 1.20, 299.0), (6.4, 2.40, 6.0), T_METAL, "y", rough=0.5,
        metal=0.5, color=[0.48, 0.48, 0.46], solid=True)
    # 踊り場だけを照らす明滅バンク(仕上げは【暗い一瞬】にしか決まらない)
    DARK5 = []
    for bx in (54.0, 58.0):
        nm = "C25_bk%.0f" % bx
        troffer(nm, bx, Y5 + HH, 299.0, on=True, intensity=12.0, rng=15.0)
        DARK5.append(nm)
    F25 = (56.00, Y5 + 2.40 + EYE, 299.00)
    # ★仕上げは規則を【重ねる】: 4 方向同時(A) × 暗の一瞬(E) × 連鎖(22〜24)。
    #   立ち位置を合わせてから、明かりが落ちる 1 秒を待つ ＝ 一問一答では絶対に解けない。
    c25 = Conn(25, F25, 2.9, 13.0, (56.0, Y5 + 3.3, 301.0), "four-at-once",
               needs=(22, 23, 24), min_y=F25[1] - 0.25, max_y=F25[1] + 0.25,
               dark=True, dark_lights=DARK5)
    # ★塞ぎ板は【最初から実在して道を塞ぐ】。破片を当たり判定にすると、解く前から
    #   出口を通り抜けられてしまう(机上検査の「解く前は行けない」で捕まえた)。
    panel = box("C25_Panel", (XIT_X, XIT_Y + XIT_H / 2, Z1 + 0.10),
                (XIT_W - 0.02, XIT_H, 0.24), T_CONC, "z", rough=0.9,
                color=[0.57, 0.57, 0.55], solid=True)
    # 4 本の欄干。★焦点から見て 南・西・東・北 と【方向が散っている】のが肝。
    #   管(確定域)は焦点と対象を結ぶ向きへ伸びるので、4 方向を同時に満たす場所は
    #   交点だけ ＝ この作品で一番狭い確定域になる。
    rails = ((0.52, "s", (56.10, Y5 + 2.95, 296.10), (6.4, 0.09, 0.09)),
             (0.60, "w", (53.10, Y5 + 2.95, 299.0), (0.09, 0.09, 6.0)),
             (0.68, "e", (59.10, Y5 + 2.95, 299.0), (0.09, 0.09, 6.0)),
             (0.76, "n", (58.50, Y5 + 2.95, 301.90), (1.8, 0.09, 0.09)))
    for k, nm, c0, s0 in rails:
        r = box("C25_r%s" % nm, c0, s0, T_METAL, "y", rough=0.45, metal=0.7,
                color=[0.56, 0.56, 0.53])
        gg = glow("C25_rg%s" % nm, (c0[0], c0[1] + 0.07, c0[2]),
                  (s0[0] * 0.9, 0.03, s0[2] * 0.9), GOLD, 1.25)
        c25.shard(k, [r, gg], glows=[gg])
    # 4 本が揃うと、塞ぎ板が沈んで北壁が開く
    c25.mover(panel, (XIT_X, XIT_Y - XIT_H / 2 - 0.30, Z1 + 0.10), dur=1.6)
    # ★ここだけ印を【小さく薄く】する。難しくはするが、理不尽にはしない
    mark("C25_mark", (F25[0], Y5 + 2.408, F25[2]), T_METAL, (0.60, 0.60, 0.57), rough=0.6)
    exit_sign("W5_exit", XIT_X, XIT_Y + XIT_H + 0.34, Z1 - 0.10)

    # ---- 出口の先(白い部屋 = 終わり) ----
    VY = XIT_Y
    box("V5_flr", (XIT_X, VY - WT / 2, 305.05), (4.4, WT, 5.5), T_PAINT, "y", rough=0.9,
        solid=True)
    box("V5_cil", (XIT_X, VY + 3.2, 305.0), (4.4, WT, 5.6), T_PAINT, "y", rough=0.9)
    for sgn in (-1, 1):
        box("V5_w%d" % sgn, (XIT_X + sgn * 2.2, VY + 1.6, 305.0), (WT, 3.2, 5.6), T_PAINT,
            "x", rough=0.9, solid=True)
    box("V5_n", (XIT_X, VY + 1.6, 307.8), (4.7, 3.2, WT), T_PAINT, "z", rough=0.9, solid=True)
    for sgn in (-1, 1):
        glow("V5_g%d" % sgn, (XIT_X + sgn * 1.5, VY + 1.5, 307.62), (1.3, 2.9, 0.04),
             [1.0, 0.98, 0.94], 1.05)
    plight("V5_l1", (XIT_X, VY + 2.2, 305.4), [1.0, 0.98, 0.94], 10.0, 9.0)


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
    c1 = Conn(1, F1, 2.0, 12.0, (0.0, 1.20, ZW - 0.08), "door")
    ZF = ZW - JD / 2               # 枠は壁の手前に出す
    rp, rg = frame_half("C1_R", +1, 0.0, 0.0, ZF, DW, DH)
    c1.shard(1.0, rp, glows=rg)
    lp, lg = frame_half("C1_L", -1, 0.0, 0.0, ZF, DW, DH)
    # ★k=0.42 だと勾配が急すぎて、確定域が幅 15cm の筋にしかならない。
    #   0.60 まで寄せると同じ角度誤差でも帯が 1m 幅になり、印の上なら繋がる
    c1.shard(0.60, lp, glows=lg)
    c1.mover(panel, (0.0, -DH / 2 - 0.15, ZW + WT / 2), dur=1.3, delay=0.0)
    # 床の擦れ跡(焦点の目印)。案内の文字の代わり
    # ★印は確定域の形(廊下に沿って伸びた帯)に合わせる。四角い印は嘘になる
    mark("C1_mark", (F1[0], 0.006, F1[2]), T_CARPET, (0.72, 0.70, 0.66), rough=0.98)

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
    c2 = Conn(2, F2, 2.0, 11.0, ((A2[0] + B2[0]) / 2, 0.0, (A2[2] + B2[2]) / 2), "bridge")
    # ★橋は床に【潜り込ませない】。天端を床と面一にすると、斜めの板の隅が
    #   床スラブと穴の見切りを 0.24m 貫通し、天端どうしが同じ高さで重なって【ちらつく】。
    #   斜めの箱は既存の検査 3 種すべてが対象外だったので、ずっと素通りしていた。
    #   床の【上に載せる】と貫通も同一平面も同時に消え、「板を渡した」絵になる。
    NSEG, WID, THK = 4, 1.70, 0.18
    # ★最初の橋なので【教える側】。k を 1 へ寄せて勾配をなだらかにする。
    #   (1.0, 0.72, 0.53, 0.40) だと確定域が幅 26cm の帯にしかならず、
    #   1.6m 四方の床の目印の【11% しか当たらない】= 印の上に立っても繋がらない。
    KS = (1.0, 0.80, 0.64, 0.52)
    for i in range(NSEG):
        t0, t1 = i / NSEG, (i + 1) / NSEG
        cxs = A2[0] + dxz[0] * (t0 + t1) / 2
        czs = A2[2] + dxz[1] * (t0 + t1) / 2
        seg = L2 / NSEG
        parts = []
        deck = box("C2_s%d" % i, (cxs, THK / 2, czs), (WID, THK, seg - 0.02), T_PAINT, "y",
                   rough=0.8, color=[0.52, 0.52, 0.48], rot=(0, YAW2, 0), tile=(seg / 2, WID / 2))
        parts.append(deck)
        # 縁の光(切断面)。両端に細く
        for sgn in (-1, 1):
            ox = math.cos(math.radians(YAW2)) * sgn * (WID / 2 - 0.03)
            oz = -math.sin(math.radians(YAW2)) * sgn * (WID / 2 - 0.03)
            parts.append(glow("C2_s%de%d" % (i, sgn + 1), (cxs + ox, THK + 0.020, czs + oz),
                              (0.055, 0.04, seg - 0.06), GOLD, 1.25, rot=(0, YAW2, 0)))
        g = [p for p in parts if p["name"].endswith(("e0", "e2"))]
        c2.shard(KS[i], parts, glows=g)
        h = hit("C2_h%d" % i, (cxs, THK / 2, czs), (WID, THK, seg), rot=(0, YAW2, 0),
                kinematic=True)
        # ★k=1 の断片は最初から本物 = 当たり判定も最初から要る(これが無いと
        #   組み上がった橋の【取り付きだけ】が空洞になって渡れない)
        if KS[i] < 0.999:
            c2.solid(h)
    # ★確定域は橋の方向へ伸びた【細長い帯】なので、印もその形・その向きにする。
    #   四角い印を置くと「印の上なのに繋がらない」になる(実際になった)。
    mark("C2_mark", (F2[0], 0.006, F2[2]), T_CARPET, (0.72, 0.70, 0.66), rough=0.98)

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
        # ★0.01 だと段の前面と同一平面になる。0.03 引いて確実に内側へ入れる
        box("C_stf%d" % i, (0, yy + 0.175, z0 - 0.03), (PW * 2, 0.35, 0.02), T_TILEW, "z", rough=0.3)
    box("C_pool", (0, -1.40 - WT / 2, (52.7 + 59.0) / 2), (PW * 2, WT, 59.0 - 52.7), T_TILEF, "y",
        rough=0.20, solid=True)
    for sgn in (-1, 1):
        box("C_poolw%d" % sgn, (sgn * (PW - 0.06), -0.70, 54.5), (0.12, 1.40, 9.0), T_TILEW, "x",
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
    c3 = Conn(3, F3, 1.15, 8.0, (SX, 1.8, 55.0), "stair")
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
    # ★見切り板は最上段の【手前】へ(+0.02 だと最上段の後端に 0.06m 食い込む)
    box("C_landf", (SX, SILL - 0.72, ZLAND0 - 0.08), (SW + 0.4, 1.0, 0.16), T_TILEW, "z",
        rough=0.3)
    mark("C3_mark", (F3[0], 0.014, F3[2]), T_TILEF, (0.78, 0.80, 0.78), rough=0.30,
         thick=0.014)

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
    c4 = Conn(4, F4, 1.3, 10.0, (DX3, YD + 1.2, ZE - 0.1), "exit")
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
    c4.mover(epanel, (DX3, YD - DH / 2 - 0.25, ZE + WT / 2), dur=1.3, delay=0.0)
    c4.lamp("C4_sign", 1.0, dur=0.7, delay=0.15)
    # ★扉は【開く】。閉じたままだと『見た目は閉扉なのにすり抜けられる』一番悪い絵になる
    HINGE = (DX3 - DW / 2, YD + DH / 2, ZF4 - 0.12)
    for _e in (leaf, knob, lgk):
        c4.hinge(_e, HINGE, -82.0)
    # ★ここは第一幕の終わりの継ぎ目だが、床の目印は置かない。
    #   ここまでで『立つ位置が世界を決める』は伝わっている

    Y3 = act2(YD, DW, DH)
    act3(Y3, DW, DH)
    Y5 = act4(Y3 + 1.80, DW, DH)
    act5(Y5, DW, DH)

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

    # ★HUD は案内文とクリア文字だけ。合い具合の環は【作らない】。
    #   環があると「近づいている / 遠ざかっている」が画面で分かってしまう ＝ つながる演出。
    #   合っているかどうかは破片そのものの重なりで判断させる。
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
            if val is None:          # ★Lua に nil のキーは書かない(minY/maxY は任意)
                continue
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
