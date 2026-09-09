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
import hashlib, json, math, random, re, sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
    # ---- 第三幕「立坑」(入口 5.80 / L1 3.00 / L2 7.60。y は体の中心 = 床 + 0.90) ----
    # ★★到達点は【降りる途中にも要る】。落下復帰は `p.y < CHECKS[cp].y - 2.0` なので、
    #   到達点どうしの高さが 2.0 以上離れていると、普通に降りただけで
    #   「落ちた」と誤判定されて上へ引き戻される(実機で踏んだ。巻き段が 2.8m 下る)。
    dict(x=22.00, y=6.70, z=173.0, r=2.4),      # 立坑への渡り
    dict(x=23.00, y=6.70, z=177.5, r=2.6),      # 立坑の棚(ここから先は 17m 下が水)
    dict(x=22.90, y=5.61, z=194.0, r=2.2),      # 巻き段 西
    dict(x=36.00, y=4.68, z=195.1, r=2.2),      # 巻き段 東
    dict(x=36.50, y=3.90, z=184.5, r=2.6),      # 降りきり
    dict(x=30.00, y=3.90, z=188.0, r=3.0),      # ドラムの天端
    dict(x=52.00, y=3.90, z=195.0, r=3.0),      # 柱の道
    dict(x=62.40, y=3.90, z=200.4, r=2.4),      # 折り返し段の下
    dict(x=64.00, y=6.20, z=210.6, r=2.4),      # 折り返しの踊り場
    dict(x=57.10, y=8.50, z=203.0, r=2.6),      # 上の回廊
    dict(x=57.10, y=8.50, z=210.0, r=2.4),      # 庇の道
    dict(x=67.00, y=8.50, z=213.0, r=2.4),      # 出口の床
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
# ★第三幕をどちらで建てるか。作り直し版が机上検査を通ったら True を既定にする
ACT3_SMALL = True

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


def water(name, c, s, tex, color, alpha=0.72, reflect=0.60,
          flow=0.10, wave=0.010, distort=0.018, tile=None):
    """水面。MeshShader/FlowWater.hlsl を貼った、当たり判定の無い薄い板。

    ★なぜ FlowWater で、PoolWater ではないのか:
      PoolWater.hlsl は g_sceneColor(t1) と g_reflection(t2) を読むが、このエンジンの
      メッシュ経路が t1/t2 に流すのは【法線マップと metallic-roughness マップ】。
      渡す口が無いので反射も屈折も出ない(調べた上でこう決めている)。
      FlowWater は g_albedo(t0) だけで完結するので、そのまま正しく動く。

    ★b0 の並びはエンジン側で決まっている:
        effectValue(1) → shaderEffectValue
        _reserved(3)   → shaderParamsB   = flowSpeed / waveStrength / distortionStrength
        shaderParams(4)→ shaderParams    = waterColor(rgba。a が透明度)
      シェーダーの宣言順とこの並びが一致していないと、値が別の変数へ入る。

    ★止まった水でも flow を 0 にしない。まったく動かない水面は【青い床】にしか
      見えない(空プールへ最初に水を張った時に実際そう見えた)。ゆっくり流す。
    """
    e = ent(name, c, s)
    e["primitive"] = "box"
    e["material"] = dict(metallic=0.0, roughness=0.08)
    e["materialTextureOverrides"] = [dict(albedo=tex)]
    u, v = tile if tile else _tiling(s, "y")
    e["uvTiling"] = dict(u=round(max(u, 0.01), 4), v=round(max(v, 0.01), 4))
    e["color"] = [1, 1, 1]
    e["shader"] = "MeshShader/FlowWater.hlsl"
    e["shaderAlphaBlend"] = True
    e["shaderEffectValue"] = reflect
    e["shaderParamsB"] = [flow, wave, distort]
    e["shaderParams"] = [color[0], color[1], color[2], alpha]
    return e


UNBUILT = "Unbuilt.hlsl"
GHOST_A = 0.14          # 幽霊の【面】の不透明度。★縁は下のシェーダーが別に立てるので、
                        #   ここは思い切り薄くてよい。濃いと本物と見分けがつかない


def make_ghost(e):
    """未実体の破片を【半透明の幽霊】にする。当たり判定の有無と見た目を一致させる。

    ★2026-09-09。破片は本物と同じ材質で作ってあったので、歩ける物と歩けない物が
      見分けられず、同じ階段でも当たり判定があったり無かったりして
      【バグにしか見えない】状態だった。透けている物には乗れない、と一目で分かるようにする。
    ★合図ではない。近づいても狙っても何も変わらない。「まだ無い物はこう見える」
      という材質の決まりごと。合っているかどうかは今までどおり重なりだけで判断させる。
    ★確定したら Liminal.lua が scene:setMeshEffect(e, 1) で不透明の本物へ戻す。
    """
    if "primitive" not in e:
        return e                      # meshRenderer の破片(模型など)は対象外
    if e.get("shader"):
        return e                      # 光の線(ReconnectInk)はそのまま
    col = e.get("color") or [1, 1, 1]
    e["shader"] = UNBUILT
    e["shaderAlphaBlend"] = True
    e["shaderEffectValue"] = 0.0
    e["shaderParams"] = [col[0], col[1], col[2], GHOST_A]
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


def locker(name, x, y, z, n=3, axis="z", flip=False):
    """ロッカー。無人の建物に『人が居た痕跡』を 1 つだけ置く。
    ★作った箱を返す(継ぎ目 16 では 1 台まるごとが 1 つの破片になる)。"""
    w, h, d = 0.42 * n, 1.86, 0.48
    out = [box(name, (x, y + h / 2, z), (w, h, d) if axis == "z" else (d, h, w), T_METAL,
               "z" if axis == "z" else "x", rough=0.42, metal=0.55, color=[0.52, 0.55, 0.52])]
    for i in range(n):
        o = -w / 2 + 0.42 * (i + 0.5)
        sg = -1.0 if flip else 1.0          # ★扉の向き。壁際に背を付けるときは flip=True
        c = (x + o, y + h * 0.55, z + (sg * (d / 2 + 0.012) if axis == "z" else 0))
        s = (0.36, h * 0.80, 0.02)
        if axis == "x":
            c = (x + sg * (d / 2 + 0.012), y + h * 0.55, z + o)
            s = (0.02, h * 0.80, 0.36)
        out.append(box(name + "_d%d" % i, c, s, T_METAL, "z" if axis == "z" else "x",
                       rough=0.4, metal=0.5, color=[0.44, 0.47, 0.44]))
    return out


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
    2: 0.9,
    3: 3.4,
    5: 4.6,
    6: 2.9,
    7: 2.0,
    8: 2.4,
    9: 1.3,
    10: 4.0,
    11: 2.9,
    12: 5.2,
    13: 3.4,
    14: 4.0,
    16: 4.0,
    17: 2.9,
    18: 4.6,
    19: 3.4,
    20: 5.2,
    21: 5.2,
    22: 3.4,
    23: 3.4,
    24: 4.6,
    25: 4.6,
}

# 破片のずらし量の弱め方。k' = 1 - (1-k)*soft。1 へ寄せるほど勾配がなだらかになり、
# lock を緩めずに確定域が広がる(浮き方は控えめになる)。これも calib_marks.py が決める。
SOFT = {
    5: 0.85,
    11: 0.72,
    12: 0.85,
    14: 0.72,
    16: 0.72,
    18: 0.85,
    20: 0.72,
    21: 0.72,
    24: 0.72,
}

MARKS = {
    "G1_ibA": (0.34, 0.94, 22.2),
    "G1_ibB": (0.34, 0.94, 0.9),
    "G1_ibC": (0.26, 1.14, 150.9),
    "G1_ibD": (0.29, 0.94, 0.0),
    "C12_mk0": (0.54, 1.04, 153.6),
    "C12_mk1": (0.49, 1.04, 30.3),
    "C12_mk2": (0.49, 1.14, 141.2),
    "C1_mark": (0.34, 1.64, 5.2),
    "C2_mark": (0.39, 0.54, 41.3),
    "C3_mark": (0.34, 1.44, 70.7),
    "C5_mark": (0.44, 1.04, 167.2),
    "C6_mark": (0.29, 1.04, 0.0),
    "C7_mark": (0.34, 1.54, 39.0),
    "C8_mark": (0.34, 1.14, 2.1),
    "C9_mark": (0.29, 1.54, 79.4),
    "C10_mark": (0.54, 1.04, 22.9),
    "C11_mark": (0.26, 0.84, 22.4),
    "C13_mark": (0.34, 0.64, 99.6),
    "C14_mark": (0.49, 1.04, 66.8),
    "C16_mark": (0.26, 0.64, 50.3),
    "C18_mark": (0.49, 1.04, 18.4),
    "C19_mark": (0.39, 1.24, 52.9),
    "C20_mark": (0.54, 1.04, 52.2),
    "C21_mark": (0.49, 1.04, 68.6),
    "C22_mark": (0.24, 0.84, 114.5),
    "C23_mark": (0.34, 0.94, 90.4),
    "C24_mark": (0.44, 0.54, 106.1),
    "C25_mark": (0.34, 0.54, 121.2),
}


def mark(name, c, tex, color, rough=0.95, thick=0.012):
    """焦点の床に置く擦れ跡。大きさ/向きは MARKS(実測値)から引く。

    ★★2026-09-09「せめて何か手がかりがほしい」への直し。
      印は今まで灰色の擦れ跡(0.74,0.74,0.72)でしかなく、床の汚れと区別がつかなかった。
      破片の輪郭には金の線(GOLD)が走っているのに、印とは何の関係も見えない。
      ＝ 立ち位置と破片が【仲間だ】と読む手がかりが一つも無かった。

      直し方は合図(点滅・音・HUD)ではなく【色を揃える】こと:
        ・印そのものを、金にごく近い色へ寄せる
        ・印の外周に、破片と同じ GOLD の細い線を 1 本置く
      これで「金の線がある所どうしは仲間」という読み方が世界の中で成立する。
      光ったり動いたりはしない。近づいても何も起きない。ただ同じ色をしている。
    """
    w, L, yaw = MARKS.get(name, (1.20, 1.20, 0.0))
    e = box(name, (c[0], c[1], c[2]), (w, thick, L), tex, "y", rough=rough,
            color=[0.82, 0.76, 0.60], rot=(0, yaw, 0),
            tile=(max(w / 2.0, 0.2), max(L / 2.0, 0.2)))
    # 外周の線。破片の輪郭と同じ GOLD。★細く・弱く。線であって光源ではない
    for i, (dx, dz, sx, sz) in enumerate(((0, -L / 2 + 0.03, w, 0.05),
                                          (0, L / 2 - 0.03, w, 0.05),
                                          (-w / 2 + 0.03, 0, 0.05, L),
                                          (w / 2 - 0.03, 0, 0.05, L))):
        ra = math.radians(yaw)
        ox = dx * math.cos(ra) + dz * math.sin(ra)
        oz = -dx * math.sin(ra) + dz * math.cos(ra)
        glow(name + "_e%d" % i, (c[0] + ox, c[1] + thick * 0.6, c[2] + oz),
             (sx, 0.03, sz), GOLD, 0.55, rot=(0, yaw, 0))
    return e


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
                 occl=None, sweep=False, trail=None, trail_r=0.95, relay=None, slot=None,
                 lens=None):
        self.cid = cid
        self.focus = focus
        # ★実測で決めた値があればそれを使う(source/calib_marks.py が確定域を
        #   測って書き込む)。第三幕を作り直した時は、旧版向けの値のままだと
        #   確定域が 0.02m2 まで潰れるので【必ず calib_marks.py を回し直すこと】。
        self.lock = LOCKS.get(cid, lock)
        self.warn = warn
        self.center = center
        self.note = note
        JOINT_NOTE[cid] = note      # ★階層の見出しに使う(group_entities)
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
        # ★規則G「なぞる」: 節は【照準が通った瞬間】に決まる(待つ時間が無い)。
        #   立ち止まって一点を探す今までの動詞と違い、端から端へ首を振り切るのが仕事。
        self.sweep = sweep
        # ★規則H「踏んでなぞる」: 床の擦れ跡を順に踏む。照準を一切使わない唯一の規則。
        #   trail = [[x, z], ...]。i 番目を踏むと i 番目の破片が落ちる。
        self.trail = [[round(v, 3) for v in w] for w in trail] if trail else None
        self.trail_r = trail_r
        # ★規則I「送り」: relay = dict(secs=..., weight="<錘の名前>", drop=[dx,dy,dz])。
        #   破片は 2 組。1 組目の焦点で【窓を開け】、動いている間に 2 組目の焦点で決める。
        self.relay = relay
        # ★規則「回る」: slot = dict(ent=筒の名前, c=[cx,cz], r=半径, half=スリット半幅deg,
        #   speed=deg/秒)。中に吊った破片は、スリットがこちらを向いた一瞬しか見えない。
        self.slot = slot
        # ★★規則「レンズ」: 立ち位置で【画面の写り方そのもの】が変わる。
        #   これまでの規則は全部「どこに立って、どこを見るか」の言い換えだった
        #   (24 本中 9 本がただ合わせるだけ、残りも同じ規則の使い回し)。
        #   これは【見え方を変えて、初めて同じ形に見える】= 動詞そのものが違う。
        #
        #   lens = dict(kind=..., at=[x,y,z], r=効き始める半径, r0=最大になる半径,
        #               need=成立に要る効き具合(0..1))
        #
        #   kind:
        #     "outline" 線にする   … 色と陰影を捨てて輪郭だけにする。
        #                            材質が違って別物に見えていた 2 つが同じ形だと分かる
        #     "blur"    ぼかす     … 細部を潰すと低い周波数の構造が浮く(目を細める錯視)
        #     "warp"    歪ませる   … 樽型に曲げる。わざと曲げて置いた破片が真っ直ぐになる
        #     "drain"   色を抜く   … 明度が同じで色だけ違う 2 つが、彩度を落とすと融合する
        #     "band"    階調を潰す … なだらかな陰影に隠れた形が、段になった瞬間に輪郭で出る
        #
        #   ★どれも【画面全体が連続的に変わる】ので、効いていることは見れば分かる。
        #     初見殺しにしないための条件がこれ: 効果が段階的で、近づくほど強くなること。
        self.lens = lens
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
        for e in ents:
            make_ghost(e)             # ★未実体の見た目にする(確定で本物へ戻る)
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
        for e in ents:
            make_ghost(e)             # ★未実体の見た目にする(確定で本物へ戻る)
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
                    perShard=self.per_shard, sweep=self.sweep,
                    trail=self.trail, trailR=self.trail_r, relay=self.relay,
                    slot=self.slot, lens=self.lens,
                    peri=self.peri, dark=self.dark,
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
    pribs = []          # ★実在する 3 枚のリブ。巻き上げの一覧に載せ忘れると【棒だけ残る】
    for qx, qy, nm in ((-1, -1, "ll"), (1, -1, "lr"), (1, 1, "ur")):
        p = box("C5_" + nm, (SHX + qx * QW / 2, Y2 + QH / 2 + (0 if qy < 0 else QH), ZS),
                (QW - 0.03, QH - 0.03, 0.14), T_METAL, "z", rough=0.5, metal=0.55,
                color=[0.46, 0.46, 0.44], solid=True, tile=(QW / 2, QH / 2))
        panels.append(p)
        for r in range(4):                                   # 横のリブ(シャッターらしさ)
            pribs.append(box("C5_%s_r%d" % (nm, r),
                (SHX + qx * QW / 2, Y2 + (0 if qy < 0 else QH) + 0.26 + r * 0.5, ZS - 0.09),
                (QW - 0.12, 0.07, 0.05), T_METAL, "z", rough=0.45, metal=0.6,
                color=[0.34, 0.34, 0.32]))
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
    # ★★リブを一覧から漏らすと「シャッターは上がったのに横の棒だけ宙に残る」。
    #   板は shard() に載っているので real_pos が引けるが、リブは載っていないので
    #   mover_by は e["transform"]["position"] を読む ── リブは縮めていないので実位置と同じ。
    for p in panels + pribs + [miss] + ribs + mg:
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

    # ============================================================ N 別棟の大室（統合）
    # ★★4 部屋(折り返し / 廊下 / 多義 / 揺れ)を 1 つにした。28 x 47m・高さ 13m。
    #   「一部屋一問」をやめるのがこの幕の作り替えの核。部屋は増やしていない ── 壁を抜いた。
    NX0, NX1, NZ0, NZ1, NH = 2.0, 30.0, 108.8, 156.0, 13.0
    TR0, TR1, TRD = 130.0, 134.0, 2.6          # 溝(部屋の全幅を横切る)
    shell("N1", NX0, NX1, NZ0, NZ1, NH, T_TILEF, T_TILEW, y=Y2, walls="we",
          ceil_tex=T_CONC, base=False, floor=False)
    wall_with_door("N1_s", "z", NZ0 - WT / 2, NX0 - WT, NX1 + WT, Y2, NH, 6.0, DW, DH, T_WALL)
    SILL2 = Y2 + 2.40
    wall_with_door("N1_n", "z", NZ1 + WT / 2, NX0 - WT, NX1 + WT, Y2, NH, 22.0, DW,
                   (SILL2 - Y2) + DH, T_CONC)
    box("N1_sill", (22.0, SILL2 - 0.06, NZ1 + WT / 2), (DW, 0.12, WT), T_CONC, "z", rough=0.9)
    door_casing("N1_nc", "z", NZ1 - 0.02, 22.0, SILL2, DW, DH)
    exit_sign("N1_exit", 22.0, SILL2 + DH + 0.34, NZ1 - 0.10)
    # 床は溝の南北 2 枚。★溝は【全幅】を横切るので、渡る道は継ぎ目7/8 しか無い
    box("N1_flr_s", ((NX0 + NX1) / 2, Y2 - WT / 2, (NZ0 + TR0) / 2),
        (NX1 - NX0 + WT * 2, WT, TR0 - NZ0 + WT), T_TILEF, "y", rough=0.28, solid=True)
    box("N1_flr_n", ((NX0 + NX1) / 2, Y2 - WT / 2, (TR1 + NZ1) / 2),
        (NX1 - NX0 + WT * 2, WT, NZ1 - TR1 + WT), T_TILEF, "y", rough=0.28, solid=True)
    box("N1_pit", ((NX0 + NX1) / 2, Y2 - TRD - WT / 2, (TR0 + TR1) / 2),
        (NX1 - NX0, WT, TR1 - TR0), T_CONC, "y", rough=0.95, solid=True)
    for z in (TR0 + 0.06, TR1 - 0.06):
        box("N1_pf%.0f" % z, ((NX0 + NX1) / 2, Y2 - TRD / 2, z), (NX1 - NX0 - 0.6, TRD, 0.12),
            T_TILEW, "z", rough=0.3)
        box("N1_pl%.0f" % z, ((NX0 + NX1) / 2, Y2 + 0.02, z + (-0.16 if z < TR1 - 1 else 0.16)),
            (NX1 - NX0 - 0.6, 0.05, 0.20), T_TILEW, "y", rough=0.28)
    plight("N1_pitl", (16.0, Y2 - TRD + 1.4, 132.0), COOL, 5.0, 10.0)
    # ★灯は弱く・飛び飛びに。28x47m を均一に照らすと「ただの白い箱」になる
    for lx, lz, on in ((6.0, 113.0, True), (24.0, 113.0, False), (6.0, 124.0, False),
                       (24.0, 124.0, True), (6.0, 140.0, True), (24.0, 140.0, False),
                       (6.0, 151.0, False), (24.0, 151.0, True), (15.0, 132.0, False),
                       (20.0, 138.0, True), (17.0, 147.0, True)):
        box("N1_ls%.0f_%.0f" % (lx, lz), (lx, Y2 + NH - 0.35, lz), (1.0, 0.24, 1.0), T_METAL,
            "y", rough=0.45, metal=0.6, color=[0.42, 0.42, 0.40])
        if on:
            glow("N1_lg%.0f_%.0f" % (lx, lz), (lx, Y2 + NH - 0.49, lz), (0.72, 0.05, 0.72),
                 WARM, 1.5)
            plight("N1_ll%.0f_%.0f" % (lx, lz), (lx, Y2 + NH - 1.2, lz), WARM, 9.0, 15.0)
    locker("N1_lk", 3.2, Y2, 118.0, 3, axis="x")
    bench("N1_bench", 27.4, Y2, 121.0, axis="x")
    for i, (bx_, bz) in enumerate(((4.2, 143.0), (4.9, 143.6), (27.0, 148.0))):
        box("N1_bx%d" % i, (bx_, Y2 + 0.32, bz), (0.64, 0.64, 0.64), T_PAINT, "y", rough=0.9,
            color=[0.58, 0.54, 0.44], solid=True, rot=(0, 24 * i, 0))

    # ---- 継ぎ目 06: 振り返る（入って来た南の壁に【テラス】が立ち上がる）----
    # ★扉をやめた。部屋が 1 つになったので「隣の部屋への扉」が成り立たない。
    #   代わりに入って来た壁際に塊が立ち上がる。振り返らないと一生見えないのは同じ。
    # ★★【床から立ち上がる塊】であること。床の上に浮く板にすると、机上検査の
    #   到達高さが下の床のままになり、その上を焦点にした継ぎ目(7/8)が
    #   「立ち位置が床の上に無い」で全部落ちる(実際に落とした)。
    # ★入口(x=6.0)は塞がないこと。テラスは x 10〜26 に置いて、西 8m を通路に残す。
    CWY = Y2 + 2.60                     # テラスの天端
    TZC, TZD = 111.20, 4.40             # z の中心と奥行き
    F6 = (14.00, EYEY, 122.00)
    c6 = Conn(6, F6, 0.9, 8.0, (17.0, CWY, TZC), "behind-terrace")
    exit_sign("N1_lure6", 6.0, Y2 + DH + 0.30, NZ0 + 0.16)
    grp6 = [[], [], []]
    for i in range(4):
        xw = 12.0 + 4.0 * i
        pl6 = box("C6_p%d" % i, (xw, (Y2 + CWY) / 2, TZC), (3.90, CWY - Y2, TZD),
                  T_CONC, "x", rough=0.9, color=[0.72, 0.72, 0.70], tile=(1.3, 2.2))
        # ★天板を別の箱で載せない。塊の天面と同じ高さになって z ファイティングする
        g6 = glow("C6_g%d" % i, (xw, CWY + 0.02, TZC + TZD / 2 - 0.10), (3.70, 0.04, 0.05),
                  GOLD, 1.1)
        # ★縦の線も要る。水平 1 本だけだと【ただの黒い塊】に見えて、
        #   「これは破片だ」がこの作品の語彙で伝わらない
        v6 = [glow("C6_v%d_%d" % (i, q), (xw + (-1.90 if q == 0 else 1.90), (Y2 + CWY) / 2,
                                          TZC + TZD / 2 - 0.06), (0.05, CWY - Y2 - 0.2, 0.05),
                   GOLD, 1.1) for q in range(2)]
        grp6[i * 3 // 4] += [pl6, g6] + v6
        c6.solid(hit("C6_h%d" % i, (xw, (Y2 + CWY) / 2, TZC), (4.10, CWY - Y2, TZD + 0.2)))
    # テラスへ上がる段(東端。北から南へ 9 段で昇る)
    for i in range(9):
        yy6 = Y2 + 0.289 * (9 - i)
        zz6 = 113.90 + 0.95 * i
        st6 = box("C6_s%d" % i, (24.60, yy6 - 0.09, zz6), (3.20, 0.18, 1.45), T_METAL, "y",
                  rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47], tile=(1.6, 0.72))
        grp6[2].append(st6)
        c6.solid(hit("C6_hs%d" % i, (24.60, yy6 - 0.09, zz6), (3.40, 0.18, 1.75),
                     kinematic=True))
    # ★k の下限を上げること。低いと板が目の 3m 先に来て確定域が 1 升まで潰れる
    for gi, k6 in enumerate((0.46, 0.60, 0.74)):
        c6.shard(k6, grp6[gi],
                 glows=[e for e in grp6[gi]
                        if e["name"].startswith("C6_g") or e["name"].startswith("C6_v")])
    mark("C6_mark", (F6[0], Y2 + 0.006, F6[2]), T_TILEF, (0.72, 0.70, 0.66), rough=0.4)
    # ★★灯は【プレイヤーが来る側】に置くこと。破片の裏に置くと、見える面が
    #   全部影になって「ただの真っ黒な板」になる(docs/LIMINAL.md が継ぎ目5 で
    #   記録している「破片は照らさないと真っ黒の穴に見える」の再発)。
    #   ここは南西から来るので、灯りも南西に置く。
    plight("C6_fill", (9.0, Y2 + 2.6, 119.5), WARM, 9.0, 16.0)
    plight("C6_fill2", (19.0, Y2 + 3.4, 120.5), WARM, 7.0, 14.0)

    # ---- 継ぎ目 07/08: 同じ浮遊物が「東の橋」にも「西の橋」にもなる ----
    # ★数学: D = F + k(X - F) を 2 通り満たすには (1-k)(F7 - F8) = k(B - A)。
    #   高さと大きさを揃えれば k は共通になり、焦点だけが (B-A) の方向にずれる。
    #   結果として【西に立つと東の橋、東に立つと西の橋】という交差が自然に出る。
    # ★★2026-09-08: 焦点を【桟橋の上】へ上げた。継ぎ目6 を解いて登らないと
    #   多義の浮遊物が一度も読めない ＝ 6 → 7/8 が本当の連鎖になる。
    #   焦点の間隔は数式で決まる: F7x - F8x = (A_X - B_X)·k/(k-1)。
    #   k=0.44 だと 6.29m あって桟橋(幅 16.6m)に対して広すぎ、二つの印が
    #   離れすぎて「同じ物が二通りに見える」が伝わらない。k=0.30 で 3.43m。
    KM = 0.30
    BR_Y = Y2 + 0.09          # ★床の【上に載せる】(面一だと 0.63m が床と見切りに潜る)
    A_X, B_X = 26.0, 18.0
    F7 = (12.60, CWY + EYE, TZC)              # テラスの西寄りに立つ → 東(A_X)の橋
    F8 = (16.03, CWY + EYE, TZC)              # テラスの東寄りに立つ → 西(B_X)の橋
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
    c7 = Conn(7, F7, 1.6, 10.0, (A_X, Y2, 132.0), "bridge-east", needs=(6,),
              min_y=F7[1] - 0.30, max_y=F7[1] + 0.30)
    c7.shard_display(KM, segs + edges, glows=edges)
    c8 = Conn(8, F8, 1.6, 10.0, (B_X, Y2, 132.0), "bridge-west", needs=(6,),
              min_y=F8[1] - 0.30, max_y=F8[1] + 0.30)
    c8.shard_display(KM, segs + edges, glows=edges)
    c7.excl = [8]
    c8.excl = [7]
    for c, bx in ((c7, A_X), (c8, B_X)):
        c.solid(hit("C%d_hit" % c.cid, (bx, BR_Y, 132.0), (1.9, 0.20, TR1 - TR0 + 1.4),
                    kinematic=True))
    for f, nm in ((F7, "C7"), (F8, "C8")):
        mark(nm + "_mark", (f[0], CWY + 0.014, f[2]), T_METAL, (0.66, 0.66, 0.63),
             rough=0.6, thick=0.014)

    # （揺れの間の殻は N1 に統合済み。ここは継ぎ目9 の足場だけ）

    # ---- 継ぎ目 09: 回る（スリット付きの筒。一周に一度だけ中が見える）----
    # ★★大室に直径 12m・高さ 10m の筒を立てた。壁に 38.6 度のスリットが 1 本あり、
    #   筒はゆっくり回っている。中に吊った破片は【スリットがこちらを向いた一瞬】
    #   しか見えない。位置を合わせてから、スリットが回って来るのを待つ。
    #   暗の一瞬(規則E)の空間版だが、待つ対象が目の前で回っている巨大な筒なので、
    #   何を待てばいいのかが絵だけで分かる(文字が無いこの作品ではそこが全て)。
    # ★★焦点 → 筒 → 出来る物 が一直線であること。浮遊姿勢は F + k(実体 - F) なので、
    #   筒は【焦点と実体の間】にしか置けない。ここは 焦点 x=6 / 筒 x=16 / 段 x=22。
    # ★★筒は【全体が視野に入る大きさと距離】でなければ仕掛けとして読めない。
    #   最初 半径 6m の筒を目の 4m 先に置いたら、画面がまるごとコンクリの壁になり、
    #   中の破片も、そもそも筒が回っていることすら見えなかった。
    #   半径 4m・目から 11m にして、視野に 43 度で収まるようにした。
    #   (docs/LIMINAL.md の「焦点は隠すのに使う物の手前ではなく横に置く」と同じ罠)
    DR9, DH9 = 4.0, 10.0
    DC9 = (14.0, 148.0)
    dr9 = ent("N1_drum", (DC9[0], Y2, DC9[1]), (DR9 / 7.0, DH9 / 16.12, DR9 / 7.0))
    dr9["meshRenderer"] = dict(modelPath="models/arch/shaft/sh_drum.gltf")
    # ★当たり判定は内接する箱で足りる(中へ入る必要は無い)。角が壁の外へ出ないこと
    # ★名前を _hollow で終わらせると、机上検査[1]/[8] が【破片が中に居てよい殻】
    #   として扱う。この筒は中に破片を吊るのが仕掛けそのものなので必要。
    # ★★円柱を 1 個の箱で塞いではいけない。箱の辺は半径 3.6 でしか止めないので、
    #   見た目(半径 6)の中へ 2.4m 歩いて入れてしまう。45 度ずつ回した 4 枚で
    #   八角形に近づけると、どの向きでも半径 5.2 以上で止まる。
    for qi in range(4):
        hit("N1_drum%d_hollow" % qi, (DC9[0], Y2 + DH9 / 2, DC9[1]),
            (DR9 * 1.85, DH9, DR9 * 0.78), rot=(0, 45.0 * qi, 0))
    plight("N1_druml", (DC9[0] - DR9 - 2.0, Y2 + 3.4, DC9[1]), WARM, 8.0, 12.0)

    F9 = (3.20, EYEY, 146.00)
    c9 = Conn(9, F9, 2.5, 14.0, (22.0, Y2 + 1.2, 151.0), "slot-drum",
              slot=dict(ent="N1_drum", c=[DC9[0], DC9[1]], r=DR9, half=19.3, speed=26.0))
    # ★速さは【待てる長さ】から決める。窓が短すぎると「探す」ができない。
    # ★★2026-09-09「回るやつ、まじ判定厳しい」への直し。3 つ直した:
    #   (1) half 17.0 -> 19.3。モデルのスリットは 38.6 度なのに判定は 34 度しか
    #       開いておらず、【スリット越しに見えているのに繋がらない】帯が
    #       1 周に 0.13 秒あった。絵と判定を一致させる。これはバグに近い。
    #   (2) speed 36 -> 26 度/秒(一周 13.8 秒、窓 1.48 秒)。
    #       ★本当の問題は「窓 < 確定時間」ではなく【探している間に情報が来ない】こと。
    #         破片は筒の中に吊ってあるので、破片が見えるのも窓が開いている間だけ。
    #         36 度/秒だと 10 秒のうち 9 秒はコンクリの壁を見ていることになり、
    #         立ち位置を 10 か所試すのに 100 秒かかって 90 秒が無駄になっていた。
    #         窓を 0.94 -> 1.48 秒(時間の 9.4% -> 10.7%)へ広げ、
    #         一度の窓で「直した結果」を確かめられる長さにする。
    #   (3) 判定の的を c.center(筒の【向こう側】にある階段の中心)から
    #       【破片そのもの】へ変えた(liminal_runtime.lua 側)。
    #       目で追っている物と判定が開く瞬間がずれていたのを揃えた。
    #   ★一周 13.8 秒は長いが、hold が窓を跨いで溜まるようにしたので
    #     「待たされる」のではなく「合わせておけば次の窓で決まる」になる。
    RISE9, RUN9, W9 = 0.30, 0.70, 1.70
    ZST = 148.0
    grp9 = [[], [], []]
    for i in range(8):
        top = Y2 + RISE9 * (i + 1)
        z0 = ZST + RUN9 * i
        s9 = box("C9_s%d" % i, (22.0, top - 0.11, z0 + RUN9 / 2), (W9, 0.22, RUN9), T_METAL,
                 "y", rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47])
        r9 = box("C9_r%d" % i, (22.0, top - 0.22 - RISE9 / 2 + 0.055, z0 + 0.02),
                 (W9, RISE9, 0.04), T_METAL, "z", rough=0.5, metal=0.5,
                 color=[0.40, 0.40, 0.38])
        g9 = glow("C9_e%d" % i, (22.0 - W9 / 2 + 0.03, top + 0.005, z0 + RUN9 / 2),
                  (0.055, 0.04, RUN9 - 0.04), GOLD, 1.25)
        grp9[i * 3 // 8] += [s9, r9, g9]
        c9.solid(hit("C9_h%d" % i, (22.0, top - 0.11, z0 + RUN9 / 2), (W9, 0.22, RUN9 + 0.2),
                     kinematic=True))
    box("C9_land", (22.0, SILL2 - 0.11, 154.9), (W9 + 0.4, 0.22, 2.6), T_METAL, "y", rough=0.5,
        metal=0.5, color=[0.50, 0.50, 0.47], solid=True)
    # ★k は【筒の内側(x 10.3〜21.7)に収まる範囲】で広く散らす。
    #   浮遊 x = 3.2 + 18.8k なので k = 0.42 / 0.58 / 0.74 → 11.1 / 14.1 / 17.1。
    #   詰めると 3 塊が団子になって「どれがどれだか読めない」
    for gi, k9 in enumerate((0.42, 0.58, 0.74)):
        c9.shard(k9, grp9[gi],
                 glows=[e for e in grp9[gi] if e["name"].startswith("C9_e")])
    mark("C9_mark", (F9[0], Y2 + 0.008, F9[2]), T_TILEF, (0.72, 0.72, 0.70), rough=0.4,
         thick=0.016)
    # ★灯は【浮遊している所】＝筒の中へ。外から差し込むように置く
    plight("C9_fill", (7.0, Y2 + 3.0, 146.5), WARM, 8.0, 14.0)
    plight("C9_fill2", (14.0, Y2 + 5.5, 148.0), WARM, 6.0, 12.0)

    # ============================================================ Z 終わりの間
    ZX0, ZX1, ZZ0, ZZ1, ZH = 14.0, 30.0, 156.3, 170.0, 6.0
    shell("Z1", ZX0, ZX1, ZZ0, ZZ1, ZH, T_PAINT, T_PAINT, y=SILL2, walls="we",
          ceil_tex=T_PAINT, base=False)
    # ★S の北壁(S1_n)が開口ごとこの位置の壁を兼ねる。Z の方が高いぶんだけを上に足す
    # ★Z1_s は廃止。大室(N1)の北壁が高さ 13m あるので、ここに 2 枚目を建てると
    #   同一平面になって見る位置で色が入れ替わる(検査 [6] が捕まえた)
    # ★白い部屋は終わりではなく【第三幕への戸口】。戸口(継ぎ目10)が建つまでは塞がっている
    wall_with_door("Z1_n", "z", ZZ1 + WT / 2, ZX0 - WT, ZX1 + WT, SILL2, ZH, 22.0, DW, DH, T_PAINT)
    door_casing("Z1_nc", "z", ZZ1 - 0.02, 22.0, SILL2, DW, DH)
    exit_sign("Z1_exit", 22.0, SILL2 + DH + 0.36, ZZ1 - 0.10)
    for x, z in ((18.0, 160.0), (26.0, 160.0), (18.0, 167.0), (26.0, 167.0)):
        glow("Z1_lg%.0f_%.0f" % (x, z), (x, SILL2 + ZH - 0.12, z), (1.6, 0.06, 1.6),
             [1.0, 0.99, 0.96], 1.15)
        plight("Z1_ll%.0f_%.0f" % (x, z), (x, SILL2 + ZH - 0.5, z), [1.0, 0.99, 0.96], 8.0, 14.0)

    # ---- 継ぎ目 10: 何にも寄りかかっていない【自立した戸口】 ----
    # ★規則B「触れる」。焦点は無い。天井から吊った灯り(a)と、浮いている戸口の
    #   楣の光(b)が【画面の上で重なった】ら建つ。奥行きに寛容・向きに厳しいので、
    #   第二幕でここだけ手触りが違う(第二幕は 5〜9 が全部 A 相似だった)。
    # ★a と b を結ぶ線が【目の高さで部屋の中を通る】ように置くこと。
    #   a を b とほぼ同じ高さにすると、線が目の高さへ降りてくるのが部屋の外になり、
    #   立てる場所が一つも無くなる(紙の上で 4 回やり直した)。
    F10 = (18.48, SILL2 + EYE, 158.63)
    # ★★2026-09-09「gate が全然錯覚じゃない」への直し。
    #   前は【金色に光る枠を、吊り灯と画面上で重ねる】だった。枠がはっきり見えている
    #   以上、やることは的当てでしかなく、錯覚は一つも起きていなかった。
    #
    #   仕掛け(touch = 2 点が画面で重なる)はそのまま残す。これは強制遠近法そのもので、
    #   悪いのは規則ではなく【見せ方】だった。変えたのはそこ:
    #     ・枠の色を壁とほぼ同じにした(FRAME_COL 0.44 -> 0.93)
    #     ・光る線を 1.25 -> 0.30 まで落とした
    #   こうすると、なだらかな灯りの falloff の中に枠が溶けて【どこにあるか分からない】。
    #   そこへ規則「階調を潰す」を重ねる。段になった瞬間、枠と壁が別の段へ落ちて
    #   輪郭が現れる ── ポスタリゼーションで浮き上がる隠し絵、そのもの。
    #   ★見つけることそのものが錯視になり、そのあとに重ねる作業が来る。
    c10 = Conn(10, F10, 1.3, 9.0, (22.0, SILL2 + 1.2, 164.0), "hidden-gate",
               lens=dict(kind="band", at=[round(v, 3) for v in F10],
                         r=6.2, r0=1.5, need=0.78))
    GATE_COL = [0.93, 0.93, 0.91]      # 壁とほぼ同じ。段を落とさないと境界が出ない
    GZ = 164.0
    GW, GH = 1.30, 2.35
    parts = [[], [], [], []]
    jw = 0.24
    p0 = box("C10_jl", (22.0 - GW / 2 - jw / 2, SILL2 + (GH + jw) / 2, GZ), (jw, GH + jw, 0.30),
             T_PAINT, "z", rough=0.45, color=GATE_COL)
    p1 = box("C10_jr", (22.0 + GW / 2 + jw / 2, SILL2 + (GH + jw) / 2, GZ), (jw, GH + jw, 0.30),
             T_PAINT, "z", rough=0.45, color=GATE_COL)
    p2 = box("C10_hd", (22.0, SILL2 + GH + jw / 2, GZ), (GW + jw * 2, jw, 0.30), T_PAINT, "z",
             rough=0.45, color=GATE_COL)
    p3 = box("C10_sl", (22.0, SILL2 + 0.06, GZ), (GW + jw * 2, 0.12, 0.30), T_PAINT, "z",
             rough=0.45, color=GATE_COL)
    g0 = glow("C10_g0", (22.0 - GW / 2 - 0.02, SILL2 + GH / 2, GZ + 0.16), (0.04, GH, 0.04), GOLD, 0.30)
    g1 = glow("C10_g1", (22.0 + GW / 2 + 0.02, SILL2 + GH / 2, GZ + 0.16), (0.04, GH, 0.04), GOLD, 0.30)
    g2 = glow("C10_g2", (22.0, SILL2 + GH + 0.02, GZ + 0.16), (GW, 0.04, 0.04), GOLD, 0.30)
    g3 = glow("C10_g3", (22.0, SILL2 + 0.14, GZ + 0.16), (GW, 0.04, 0.04), GOLD, 0.30)
    # 吊り灯(a)。★これは実体。最初から点いていて、b と重なる位置を探す目印になる
    lamp10 = glow("C10_lamp", (23.0, 11.20, 166.0), (0.26, 0.26, 0.26),
                  [1.0, 0.90, 0.62], 2.2)
    box("C10_lampr", (23.0, 11.55, 166.0), (0.07, 0.60, 0.07), T_METAL, "y", rough=0.45,
        metal=0.7, color=[0.52, 0.52, 0.50])
    DISP10 = (-1.60, 0.90, -2.40)
    c10.touch = dict(a=[23.0, 11.20, 166.0],
                     b=[round(22.0 + DISP10[0], 3), round(8.17 + DISP10[1], 3),
                        round(164.16 + DISP10[2], 3)],
                     near=3.0, far=12.0)
    c10.shard_free([p0, p1, p2, p3, g0, g1, g2, g3], DISP10, dk=0.60,
                   glows=[g0, g1, g2, g3])
    mark("C10_mark", (F10[0], SILL2 + 0.008, F10[2]), T_PAINT, (0.74, 0.73, 0.70), rough=0.9)
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
    """★2026-09-08 全面作り替え ── 第三幕「立坑」。

    前は小部屋 6 個が一直線に並んでいた(連絡通路 / 吊られた板 / 大階段 / 吹き抜け /
    廊下 / 大部屋 / 終わりの間)。ここが「同じパズルの繰り返し」の本体だったので、
    **6 個を全部消して、58 x 42m・高さ 28m の縦穴 1 つ**にした。

      11 巻き段    縁の一点からだけ、宙の巨大な塊が【ドラムを巻く段】に見える(k>1)
      12 水鏡      15m 下の水に映った像でだけ重ねられる。下を向いて解く
      13 回る      ドラムの縦リブが、或る位相の時だけ絵を完成させる
      14 多義      同じ塊が、東から見ると庇、西から見ると段。選ばぬ方は永久に消える
      15 負        見てしまうと壁が建つ。伏し目で通る
      16 模型      縁に浮かぶ【立坑そのものの模型】。重ねると出口の床が生える

    ★出来る物に橋も扉も階段も無い: 巻き段 / 柱 / 庇 / 床。
    ★歩ける面は必ず水平にすること。机上シミュレータの Body は
      【yaw しか見ない】(sim_liminal.World)。傾けた板は当たり判定が嘘になる。
    """
    EY = Y3 + EYE
    Y4 = Y3 + 1.80                 # 出口の高さ(第四幕の床) = 7.60
    SX0, SX1, SZ0, SZ1 = 14.0, 72.0, 172.0, 214.0
    YB = Y3 - 20.0                 # 底(水面) = -14.20。歩かない。ずっと足の下にある
    # ★歩くのは上の 5m だけ。下の 17m は【落ちたら死ぬ空虚】として見せる物で、
    #   道にはしない。ここを歩かせようとすると登りが 7m になり、0.283 刻みで
    #   25 段の階段が要る ＝ 破片が団子になって読めなくなる(実際にそうなった)。
    L1 = Y3 - 2.80                 # 3.00  ドラムの天端 / 柱の頭
    L2 = Y3 + 1.80                 # 7.60  出口の高さ(= Y4)
    TOP = Y3 + 8.0                 # 13.80 天井
    DCX, DCZ, DR = 30.0, 188.0, 7.0
    DSY = (L1 - (Y3 - 20.0)) / 16.12   # sh_drum を水面から天端まで伸ばす
    DBY = L1 - 16.12 * DSY         # ドラムの底

    # ============================================================ 殻
    box("S3_flr", ((SX0 + SX1) / 2, YB - WT / 2, (SZ0 + SZ1) / 2),
        (SX1 - SX0 + WT * 2, WT, SZ1 - SZ0 + WT * 2), T_CONC, "y", rough=0.95, solid=True)
    # ★水面。当たり判定は付けない(落ちたら復帰する)。粗さを落として【映す面】にする
    # ★★立坑は【水没している】。水面は L1 の 6m 下(= WY)。底は更に 11m 下。
    #   水面を底に置くと、そこから立てる柱が 17m になり、破片の縦の広がりが
    #   そのまま角度感度になって確定域が 1 升(0.02m2)まで潰れる ＝ 誰も解けない。
    WY = L1 - 6.00
    box("S3_water", ((SX0 + SX1) / 2, WY, (SZ0 + SZ1) / 2),
        (SX1 - SX0, 0.06, SZ1 - SZ0), T_TILEF, "y", rough=0.06, metal=0.35,
        color=[0.24, 0.28, 0.30], tile=(8.0, 8.0))
    box("S3_cil", ((SX0 + SX1) / 2, TOP + WT / 2, (SZ0 + SZ1) / 2),
        (SX1 - SX0 + WT * 2, WT, SZ1 - SZ0 + WT * 2), T_CONC, "y", rough=0.94)
    for ch, sgn in (("w", -1), ("e", 1)):
        box("S3_" + ch, ((SX0 + SX1) / 2 + sgn * ((SX1 - SX0) / 2 + WT / 2), (YB + TOP) / 2,
                         (SZ0 + SZ1) / 2), (WT, TOP - YB, SZ1 - SZ0 + WT * 2), T_CONC, "x",
            rough=0.9, solid=True)
    # 南: 入口(第二幕から)。北: 出口(第四幕へ)。どちらも【床から浮いた開口】
    wall_hole("S3_s", "z", SZ0 - WT / 2, SX0 - WT, SX1 + WT, YB, TOP, 22.0, DW, Y3, DH, T_CONC)
    XITX, XITW, XITH = 68.0, 2.20, 2.40
    wall_hole("S3_n", "z", SZ1 + WT / 2, SX0 - WT, SX1 + WT, YB, TOP, XITX, XITW, Y4, XITH,
              T_CONC)
    # ★縦穴の深さを読ませる帯(各レベルの高さに 1 本ずつ)。無いと 28m が 8m に見える
    for yy in (L1, L2, Y3, Y4):
        for sgn in (-1, 1):
            box("S3_bd%.0f_%d" % (yy * 10, sgn > 0),
                ((SX0 + SX1) / 2 + sgn * ((SX1 - SX0) / 2 - 0.06), yy - 0.30, (SZ0 + SZ1) / 2),
                (0.12, 0.16, SZ1 - SZ0 - 1.0), T_CONC, "x", rough=0.9,
                color=[0.60, 0.60, 0.58])

    # ---- 入口の棚(南西) ----
    # ★第二幕の白い部屋は z=170 で終わる。立坑の南壁は z=172。この 2m に床が無いと
    #   【第三幕へ一歩も入れない】(机上検査 [2] が「継ぎ目10 を解いても行けない」で捕まえた)
    # ★床は 1 枚で通すこと。白い部屋の床・渡りの床・棚を別々に敷くと、
    #   同じ高さの面が重なって z ファイティングする(検査 [6] が 3 組捕まえた)
    box("S3_in_cil", (22.0, Y3 + 2.9 + WT / 2, 171.1), (3.6, WT, 2.6), T_CONC, "y", rough=0.94)
    for sgn in (-1, 1):
        box("S3_inw%d" % sgn, (22.0 + sgn * 1.9, Y3 + 1.45, 171.1), (WT, 2.9, 2.6), T_CONC,
            "x", rough=0.9, solid=True)
    # ★棚は【巻き段の 1 段目に届くまで】伸ばすこと。届いていないと、解いても
    #   段へ一歩も乗れない(机上検査 [2] の「解いても行けない」で捕まえた)
    box("S3_led", (23.0, Y3 - WT / 2, 174.45), (10.0, WT, 8.3), T_CONC, "y", rough=0.95,
        solid=True)
    box("S3_ledk", (23.0, Y3 + 0.11, 178.5), (10.0, 0.22, 0.16), T_CONC, "z", rough=0.9,
        color=[0.58, 0.58, 0.56])
    exit_sign("S3_lure", 22.0, Y3 + DH + 0.30, SZ0 + 0.16)

    # ---- ドラム(立坑の中心装置。回るのは継ぎ目13) ----
    d = ent("S3_drum", (DCX, DBY, DCZ), (1.0, DSY, 1.0))
    d["meshRenderer"] = dict(modelPath="models/arch/shaft/sh_drum.gltf")
    # ★円柱を 1 個の箱で囲うと【角が半径 9.4 まで届いて】巻き段(内縁 7.5)を塞ぐ。
    #   中へ入れる必要は無いので、内接する小さい箱で足りる
    hit("S3_drumh", (DCX, (DBY + L1) / 2, DCZ), (DR * 1.20, L1 - DBY, DR * 1.20))
    # ★天端は【巻き段の内縁(半径 7.5)に届く大きさ】にすること。届かないと
    #   段を降りきってもドラムに乗れない
    # ★見える天端は巻き段に【触れるだけ】(2.157*7 = 半径 7.55、段の内縁 7.5)。
    #   食い込ませると検査[8]が「組み上がり後にめり込んでいる」で落とす
    hit("S3_drumcap", (DCX, L1 - 0.11, DCZ), (DR * 2.157, 0.22, DR * 2.157))

    # 灯り。★弱く・飛び飛びに(34x44m を明るく照らしたら「ただの白い箱」になった前例)
    # ★★58 x 42 x 28m を「照らそう」とすると、霧の中で全部が同じ灰色になって
    #   【ただの箱】になる(実際にそうなった)。灯は道筋の上にだけ・強さは半分。
    #   下の 15m は【暗いままにする】。深さは明るさでは伝わらない ── 暗さで伝わる。
    for lx, lz, ly in ((20.0, 180.0, Y3 + 2.8), (38.0, 191.0, L1 + 3.0),
                       (52.0, 197.0, L1 + 3.0),
                       (66.0, 206.0, L2 + 2.8), (65.0, 212.0, Y4 + 2.4)):
        box("S3_ls%.0f_%.0f" % (lx, lz), (lx, ly + 0.30, lz), (1.1, 0.22, 1.1), T_METAL, "y",
            rough=0.45, metal=0.6, color=[0.42, 0.42, 0.40])
        glow("S3_lg%.0f_%.0f" % (lx, lz), (lx, ly + 0.16, lz), (0.78, 0.05, 0.78), WARM, 1.5)
        plight("S3_ll%.0f_%.0f" % (lx, lz), (lx, ly - 0.4, lz), WARM, 6.0, 11.0)
    # ★★下の 17m は「暗いままにする」だけでは足りなかった。縁に立って見下ろしても
    #   灰色の霧しか無く、【深さがある】ことが一切伝わらない(実際に立って撮って判明)。
    #   水面を冷たい色で薄く照らして、遥か下に面があることだけを見せる。
    #   暖色の通路の灯りと色を分けてあるので、明るくしても「同じ空間」には見えない。
    for wx, wz in ((30.0, 186.0), (52.0, 198.0), (40.0, 205.0)):
        plight("S3_wl%.0f_%.0f" % (wx, wz), (wx, WY + 2.6, wz), COOL, 7.0, 22.0)

    # ================================================== 継ぎ目 11: 巻き段（k>1）
    # ★継ぎ目5 の「巨大 x 極小」の逆。宙に浮かぶ【原寸より大きい塊】が、縁の一点
    #   からだけドラムを巻く段に重なる。k>1 なので破片は焦点から【遠ざかって大きく】なる。
    # ★k を上げすぎると破片が立坑の外へ出る。ここでは 1.46 が上限(実測で詰めた)。
    F11 = (22.60, EY, 176.60)
    # ★規則「線にする」。焦点へ近づくほど画面から色と陰影が抜けて輪郭だけになる。
    #   立坑の破片は錆・塗装・コンクリと材質がばらばらで、色があるうちは【別々の物】に
    #   見える。線画になると材質の差が消えて、同じ 1 本の輪郭だと分かる。
    #   ★装置は焦点そのもの。近づくと画面が変わる = 近いことが分かる案内も兼ねる。
    c11 = Conn(11, F11, 2.6, 14.0, (DCX, (Y3 + L1) / 2, DCZ - DR - 2.0), "coil",
               lens=dict(kind="outline", at=[round(v, 3) for v in F11],
                         r=7.0, r0=1.8, need=0.72))

    # ★★2026-09-09「入ってすぐの階段。普通に下れると思ったら落ちる」への直し。
    #   前は 18 段すべてが破片だった ＝ 入口の目の前に【降りられそうな段の形】が
    #   浮いていて、歩くと 8.8m 落ちる。ただの罠で、しかも何をすればいいのかも
    #   伝わっていなかった。
    #
    #   ★試して駄目だった直し方を 2 つ残す:
    #     (1) 縁に手すりを立てる … 「入るな」としか言わず、何をすればいいかを
    #         何も伝えないので詰まったままになる。
    #     (2) 手前 12 段を実在させて歩いて降りられるようにする …
    #         段の途切れから【飛び降りて継ぎ目11 を飛ばせてしまう】。
    #         机上検査が「解く前に (30.0,188.0) へ行けてしまう」で捕まえた。
    #         実在の段と破片の段が混ざるので、めり込みも 8 組出た。
    #   ★採った直し方は【材質】。段は 18 段とも破片のままだが、未実体の破片は
    #     半透明の幽霊で描くようにした(assets/shaders/Unbuilt.hlsl)。
    #     透けている段には乗れないと一目で分かるので、
    #     「歩けると思って落ちる」も「当たり判定があったり無かったり」も起きない。
    NS, RS, RW = 18, 9.30, 3.60             # 段数 / 巻く半径 / 段の幅(半径方向)
    A0 = -130.0                              # 棚の北の縁に 1 段目が来る角度
    coil = [[] for _ in range(6)]
    STEP_A = 270.0 / NS
    for i in range(NS):
        a = math.radians(A0 - STEP_A * i)              # 時計回りに降りる
        top = Y3 - (Y3 - L1) * (i + 1) / NS
        px, pz = DCX + RS * math.cos(a), DCZ + RS * math.sin(a)
        st = box("C11_s%d" % i, (px, top - 0.11, pz), (RW, 0.22, 2.55), T_METAL, "y",
                 rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47],
                 rot=(0, -math.degrees(a), 0), tile=(1.3, 1.28))
        g = glow("C11_g%d" % i, (px - math.cos(a) * (RW / 2 - 0.05),
                                 top + 0.02, pz - math.sin(a) * (RW / 2 - 0.05)),
                 (0.05, 0.04, 2.4), GOLD, 1.1, rot=(0, -math.degrees(a), 0))
        coil[i * 6 // NS] += [st, g]
        c11.solid(hit("C11_h%d" % i, (px, top - 0.11, pz), (RW, 0.22, 2.75),
                      rot=(0, -math.degrees(a), 0), kinematic=True))
    for gi, k in enumerate((1.10, 1.17, 1.24, 1.31, 1.38, 1.46)):
        c11.shard(k, coil[gi], glows=[e for e in coil[gi] if e["name"].startswith("C11_g")])
    mark("C11_mark", (F11[0], Y3 + 0.008, F11[2]), T_CONC, (0.74, 0.74, 0.72), rough=0.9)
    plight("C11_fill", (26.0, Y3 + 2.6, 182.0), WARM, 9.0, 14.0)

    # ================================================== 継ぎ目 12: 水鏡
    # ★★この作品で初めて【下を向いて解く】継ぎ目。本物はドラムの陰で直接は見えない。
    #   15m 下の水面に映った像でだけ重ねられる(規則K。ランタイムは目を水面で反転する)。
    #   いまは相似規則のまま置いてある ── 次に mirrorY を入れて切り替える。
    # ★★焦点は【道の軸の上・手前の端】に置くこと。横に置くと、隣り合う頭どうしが
    #   縮めた後も接したまま重なる(歩ける = 接している = 縮めても接している)。
    #   軸の上に置くと f_i = F + k_i*d_i*u となり、k と d が同時に増えるぶん
    #   破片が軸に沿って一列に開く。継ぎ目3(プールの階段)が通っているのと同じ理屈。
    F12 = (37.12, L1 + EYE, 182.02)          # 巻き段の降りきった段の上
    # ★規則C「巡る」。ドラムの天端(直径 15m)の縁を歩き回り、【立つ場所ごとに
    #   柱を 1 本ずつ】立てる。一箇所で終わらないので、道が自分の足元から伸びていく。
    #   ★焦点はすべてドラムの上 = 最初から立てる場所に置くこと。
    #     「次の柱の上」に置くと、解く前に行けない焦点になって机上検査が落ちる。
    c12 = Conn(12, F12, 2.4, 13.0, (50.0, L1 - 1.0, 191.0), "visit-columns", needs=(11,),
               per_shard=True, min_y=L1 + EYE - 0.5, max_y=L1 + EYE + 0.5)
    # ★頭は 4.8m 角。中心間隔 4.18m なので【必ず接する】。跳べないゲームなので
    #   ここを空けると、解いても渡れない橋になる
    NC, CW3 = 7, 4.80
    for i in range(NC):
        cx_ = 43.40 + (19.00 / (NC - 1)) * i
        cz_ = 186.70 + (13.70 / (NC - 1)) * i
        # ★手前 2 本は【破片ですらない実体】。巡る規則は破片ごとに焦点を持つので、
        #   k=1 の破片を混ぜると「どこからでも誤差 0」の枠がひとつ増えてしまう。
        # ★★k を 1 に寄せすぎてはいけない。0.96 の破片は実体とほぼ同じ位置なので
        #   【どこから見ても誤差 0】になり、確定域がドラムの天端まるごと(53m2)になる。
        # ★★遠い柱ほど k を【小さく】する。角度は距離に反比例するので、遠い物に
        #   大きい k(=小さいずれ)を与えると鈍くなり、確定域がドラムの天端まるごと
        #   広がる。巡る規則は lock を破片ごとに持てない(Conn に 1 つ)ので、
        #   感度を幾何の側で揃えておく必要がある。
        # ★★感度は (1-k)/距離 でほぼ決まる。ここは焦点から柱までの距離が
        #   23.8〜30.8m とほぼ揃っているので、k も揃えるのが正解。
        #   0.82→0.42 のように振ると、確定域が 31m2〜1.3m2 と 24 倍もばらつく。
        #   巡る規則は lock を破片ごとに持てないので、幾何で感度を揃える。
        k = None if i < 2 else (0.42 + 0.020 * (6 - i))
        # ★柱は【水面から】立てる。17m の細長い柱が 6 本並ぶのが立坑の絵になる
        col = ent("C12_c%d" % i, (cx_, WY - 0.50, cz_), (1.60, (L1 - WY + 0.50) / 9.0, 1.60))
        col["meshRenderer"] = dict(modelPath="models/arch/shaft/sh_col.gltf")
        # ★見える頭は 4.40(中心間隔 4.47 なので触れない)。渡すのは当たり判定 5.0 の方
        cap_ = box("C12_t%d" % i, (cx_, L1 - 0.11, cz_), (3.10, 0.22, 3.10), T_METAL, "y",
                   rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47], tile=(1.55, 1.55))
        g = glow("C12_g%d" % i, (cx_, L1 + 0.02, cz_ - 1.45), (2.8, 0.04, 0.05), GOLD, 1.1)
        if k is None:
            hit("C12_r%d" % i, (cx_, L1 - 0.11, cz_), (4.70, 0.22, 4.70))
        else:
            # ★破片ごとの焦点をドラムの縁に散らす(角度を変えて 5 か所)
            fa = math.radians(-118.0 + 24.0 * (i - 2))
            fpt = (DCX + 5.60 * math.cos(fa), L1 + EYE, DCZ + 5.60 * math.sin(fa))
            # ★★遠くの柱 1 本だけだと角度が鈍く、確定域が 53m2(ドラムの上のどこでも)
            #   まで広がる。【近い対象を 1 つ混ぜる】= この作品の締め方(docs/LIMINAL.md)。
            #   ドラムの縁の反対側に見通し杭を立て、同じ破片に入れる。
            pa = fa + math.radians(128.0)
            post = box("C12_q%d" % i, (DCX + 6.90 * math.cos(pa), L1 + 0.75,
                                       DCZ + 6.90 * math.sin(pa)), (0.16, 1.50, 0.16),
                       T_METAL, "x", rough=0.45, metal=0.7, color=[0.56, 0.56, 0.53])
            pg = glow("C12_qg%d" % i, (DCX + 6.90 * math.cos(pa), L1 + 1.52,
                                       DCZ + 6.90 * math.sin(pa)), (0.10, 0.10, 0.10),
                      GOLD, 1.25)
            c12.shard(k, [col, cap_, g, post, pg], focus=fpt, glows=[g, pg])
            c12.solid(hit("C12_h%d" % i, (cx_, L1 - 0.11, cz_), (4.70, 0.22, 4.70),
                          kinematic=True))
    # ★巡る規則の印は【破片ごと】。calib_marks が G1_ib* と同じ流儀で名前を引く
    for j2 in range(5):
        fa = math.radians(-118.0 + 24.0 * j2)
        mark("C12_mk%d" % j2, (DCX + 5.60 * math.cos(fa), L1 + 0.008,
                               DCZ + 5.60 * math.sin(fa)), T_METAL,
             (0.66, 0.66, 0.63), rough=0.6)
    plight("C12_fill", (48.0, L1 + 3.0, 191.0), WARM, 7.0, 12.0)

    # ================================================== 継ぎ目 13: 回る
    # ★ドラムの縦リブが【或る位相の時だけ】絵を完成させる(規則は次で入れる)。
    # ★★焦点を【ドラムの天端】＝ 階段から 33m 離れた所に置いてある。
    #   これが肝: 相似で縮める時、焦点が近いと塊どうしが団子になって重なる。
    #   遠いと k の差がそのまま距離の差になり、4 つの塊が一列に並んで離れる。
    #   代わりに角度が鈍るので、確定域を締めるために【近い対象】(手すり)を 1 つ混ぜる。
    # ★登りは 4.6m を 16 段(0.2875 刻み)。折り返して 2 本の梯子段にする。
    # ★規則F「かくれて合わせる」。北の虚空に【偽の段板】が吊ってあり、それが
    #   見えている限り決まらない。ドラムの天端に立つ細い柱の陰へ入れると決まる。
    # ★遮蔽は【近くの細い物】でやること(docs/LIMINAL.md)。太い物で隠すと陰の帯が
    #   確定域より広くなり、規則が一度も効かない飾りになる。
    #   ここは 0.30m の柱を 2.5m 先に立て、偽の板をその 14m 先へ置いた
    #   → 横へ 0.5m ずれると偽物が 0.41m はみ出す = 確定域(±0.4m)を実際に切る。
    # ★目標(東の段)と偽物(北)で【方向を分けてある】。同じ方向に置くと、隠すための
    #   柱が肝心の破片を覆ってしまい「解けるのに読めない絵」になる。
    F13 = (DCX + 3.20, L1 + EYE, DCZ + 2.60)
    MAST = (33.03, 193.10)
    LURE3 = (32.20, L1 + 1.00, 205.00)
    box("S3_mast", (MAST[0], L1 + 1.80, MAST[1]), (0.30, 3.60, 0.30), T_METAL, "x",
        rough=0.5, metal=0.55, color=[0.50, 0.50, 0.48], solid=True)
    # 偽の段板(絶対に実体化しない)。★浮遊中の破片と同じ見かけにする
    box("S3_lure3", LURE3, (3.40, 0.22, 1.70), T_METAL, "y", rough=0.5, metal=0.5,
        color=[0.50, 0.50, 0.47], tile=(1.7, 0.85))
    glow("S3_lure3g", (LURE3[0] - 1.60, LURE3[1] + 0.13, LURE3[2]), (0.05, 0.04, 1.6),
         GOLD, 1.1)
    plight("S3_lure3l", (LURE3[0] + 1.6, LURE3[1] + 2.0, LURE3[2] - 1.4), WARM, 6.0, 9.0)
    c13 = Conn(13, F13, 2.2, 12.0, (66.0, (L1 + L2) / 2, 207.0), "hide-behind-mast",
               needs=(12,), min_y=L1 + EYE - 0.5, max_y=L1 + EYE + 0.5,
               occl=dict(p=[LURE3[0], LURE3[1], LURE3[2]],
                         boxes=[[MAST[0] - 0.15, L1, MAST[1] - 0.15,
                                 MAST[0] + 0.15, L1 + 3.60, MAST[1] + 0.15]]))
    NS13, RISE13 = 16, (L2 - L1) / 16.0
    grp13 = [[] for _ in range(4)]
    for i in range(NS13):
        yy = L1 + RISE13 * (i + 1)
        if i < 8:                                   # 1 本目: 東の壁沿いに北へ
            xx, zz = 66.00, 201.00 + 1.15 * i
        else:                                       # 2 本目: 折り返して南へ
            xx, zz = 62.00, 210.20 - 1.15 * (i - 8)
        pl = box("C13_p%d" % i, (xx, yy - 0.11, zz), (3.40, 0.22, 1.70), T_METAL, "y",
                 rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47], tile=(1.7, 0.85))
        g = glow("C13_g%d" % i, (xx + (-1.60 if i < 8 else 1.60), yy + 0.02, zz),
                 (0.05, 0.04, 1.6), GOLD, 1.1)
        grp13[i * 4 // NS13] += [pl, g]
        c13.solid(hit("C13_h%d" % i, (xx, yy - 0.11, zz), (3.60, 0.22, 1.90), kinematic=True))
    # 折り返しの踊り場
    # ★見た目の板は段と【面で重ねない】(同じ高さで重なると z ファイティング)。
    #   渡すのは当たり判定の方で、そちらは少し大きく取ってよい。
    land13 = box("C13_land", (64.00, L2 - RISE13 * 8 - 0.11, 211.20), (7.4, 0.22, 2.2),
                 T_METAL, "y", rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47], tile=(3.7, 1.1))
    grp13[1].append(land13)
    c13.solid(hit("C13_landh", (64.00, L2 - RISE13 * 8 - 0.11, 210.70), (7.6, 0.22, 3.6),
                  kinematic=True))
    # 庇のモデル(何を作っているかの見本)
    for gi, zz in ((0, 203.3), (3, 204.5)):
        cv = ent("C13_v%d" % gi, (68.40 if gi == 0 else 66.60,
                                  (L1 if gi == 0 else L2) - 0.34, zz),
                 (0.55, 1.0, 0.55), rot=(0, 180 if gi == 0 else 0, 0))
        cv["meshRenderer"] = dict(modelPath="models/arch/shaft/sh_canopy.gltf")
        grp13[gi].append(cv)
    # ★近い対象を 1 つ混ぜて確定域を締める(遠い物だけだと角度が鈍く、部屋の
    #   1/3 のどこに立っても解けてしまう)。ドラムの天端の手すり。
    rl13 = box("C13_rail", (DCX + 7.10, L1 + 1.05, DCZ), (0.09, 0.09, 6.4), T_METAL, "y",
               rough=0.45, metal=0.7, color=[0.56, 0.56, 0.53])
    rg13 = glow("C13_railg", (DCX + 7.10, L1 + 1.12, DCZ), (0.03, 0.03, 6.0), GOLD, 1.1)
    for gi, k in enumerate((0.30, 0.50, 0.70, 0.90)):
        c13.shard(k, grp13[gi],
                  glows=[e for e in grp13[gi] if e["name"].startswith("C13_g")])
    c13.shard(0.62, [rl13, rg13], glows=[rg13])
    mark("C13_mark", (F13[0], L1 + 0.008, F13[2]), T_METAL, (0.66, 0.66, 0.63), rough=0.6)
    # ★★埋め草の灯りは【浮遊している所】に置くこと。実体の位置に置くと、
    #   解く前に見るべき破片が暗いままになる(解いた後にだけ明るい灯り、は無意味)。
    #   継ぎ目13 の破片は k=0.30〜0.90 で x 43〜62 に散っているので、その真ん中へ。
    plight("C13_fill", (50.0, L1 + 4.0, 198.0), WARM, 8.0, 16.0)
    plight("C13_fill2", (62.0, L1 + 3.4, 206.0), WARM, 6.0, 12.0)

    # ================================================== 継ぎ目 14: 庇の道
    # ★ここは多義にできない。多義の数学 (1-k)(F14-F15) = k(B-A) は、
    #   二つの実体が【平行移動だけ違う】ことを要求する。だから「どちらの道を選んでも
    #   同じ出口へ着く」は作れない(片方が必ず出口から離れる = 詰み)。多義は
    #   第二幕の継ぎ目7/8 で既にやっているので、ここは別の絵にする。
    # ★焦点は【道の軸の上・手前の端】(継ぎ目12 と同じ理屈)。
    # ★★回廊は折り返し段の【真上に張り出させない】。段の頭上が 1.04m しか
    #   空かず、上り切る手前で通れなくなる(升を直接覗いて判明。平面で逃がすこと)
    box("S3_gal", (56.60, L2 - WT / 2, 202.25), (6.8, WT, 4.9), T_CONC, "y", rough=0.95,
        solid=True)
    F14 = (57.10, L2 + EYE, 203.00)
    # ★規則D「直視しない」。庇を正面に据えると【絶対に決まらない】。
    #   周辺視(24〜68度)に入れたまま合わせる ＝ 立ち位置と首の向きが別々の答えになる。
    c14 = Conn(14, F14, 2.4, 13.0, (57.1, L2, 209.0), "canopy-peri", needs=(13,),
               peri=True, min_y=L2 + EYE - 0.5, max_y=L2 + EYE + 0.5)
    for i, k in enumerate((0.34, 0.56, 0.78)):
        zz = 206.20 + 2.60 * i
        cv = ent("C14_v%d" % i, (60.30, L2 - 0.34, zz), (0.62, 1.0, 0.50), rot=(0, 90, 0))
        cv["meshRenderer"] = dict(modelPath="models/arch/shaft/sh_canopy.gltf")
        pl = box("C14_p%d" % i, (57.10, L2 - 0.11, zz), (5.60, 0.22, 2.70), T_METAL, "y",
                 rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47], tile=(2.8, 1.35))
        g = glow("C14_g%d" % i, (54.40, L2 + 0.02, zz), (0.05, 0.04, 2.5), GOLD, 1.1)
        c14.shard(k, [cv, pl, g], glows=[g])
        c14.solid(hit("C14_h%d" % i, (57.10, L2 - 0.11, zz), (5.80, 0.22, 2.90),
                      kinematic=True))
    mark("C14_mark", (F14[0], L2 + 0.008, F14[2]), T_CONC, (0.74, 0.74, 0.72), rough=0.9)
    plight("C14_fill", (59.0, L2 + 3.0, 209.0), WARM, 8.0, 13.0)

    # ================================================== 継ぎ目 16: 模型
    # ★出口の縁に【立坑そのものの模型】が浮いている。重ねると本物の出口の床が生える。
    F16 = (57.10, Y4 + EYE, 210.20)
    # ★規則E「暗の一瞬」。立坑の最後は【明かりが落ちる 1 秒】にしか決まらない。
    #   位置を合わせてから、待つ。第五幕の仕上げと同じ手だが、ここは 28m の縦穴の
    #   縁で待たされるので手触りがまるで違う。
    DARK3 = []
    for bx3 in (60.0, 66.0):
        nm3 = "C16_bk%.0f" % bx3
        troffer(nm3, bx3, Y4 + 3.2, 210.0, on=True, intensity=11.0, rng=14.0)
        DARK3.append(nm3)
    c16 = Conn(16, F16, 2.2, 12.0, (XITX, Y4 + 0.4, SZ1 - 2.0), "model-dark", needs=(14,),
               dark=True, dark_lights=DARK3,
               min_y=Y4 + EYE - 0.5, max_y=Y4 + EYE + 0.5)
    c16.solve_order = 16.0
    deck = []
    for i in range(3):
        # ★★z=212.60 に置くと、折り返し段の 8 段目の真上 1.79m に来て頭上判定(1.8)を
        #   1cm 割り、【上り口ごと通れなくなる】。段の z 範囲(〜211.05)より北へ逃がす。
        # ★x は庇の東端(59.9)から【ちょうど接する】ように並べる。重ねると面が
        #   同じ高さで重なって z ファイティング、離すと渡れない。
        # ★z は北壁(214.0)を貫かないこと。破片は解いた後に実体の位置へ行くので、
        #   壁にめり込んだ床が壁の中に現れる。
        deck.append(box("C16_d%d" % i, (61.45 + 3.10 * i, Y4 - 0.11, 212.60),
                        (3.10, 0.22, 2.70), T_METAL, "y", rough=0.5, metal=0.5,
                        color=[0.50, 0.50, 0.47], tile=(1.55, 1.35)))
        c16.solid(hit("C16_h%d" % i, (61.45 + 3.10 * i, Y4 - 0.11, 212.60),
                      (3.30, 0.22, 2.90), kinematic=True))
    gg = glow("C16_g", (65.6, Y4 + 0.02, 211.30), (9.0, 0.04, 0.05), GOLD, 1.1)
    deck.append(gg)
    c16.shard(0.42, deck, glows=[gg])
    mark("C16_mark", (F16[0], Y4 + 0.008, F16[2]), T_CONC, (0.74, 0.74, 0.72), rough=0.9)
    plight("C16_fill", (64.0, Y4 + 2.6, 210.0), WARM, 8.0, 12.0)
    exit_sign("S3_exit", XITX, Y4 + XITH + 0.32, SZ1 - 0.12)

    # ---- 出口の先(白い部屋 = 第四幕への戸口)。前の版と同じ受け渡し ----
    # ★出口の床(破片)は壁の手前で止めるので、白い部屋の床を南へ伸ばして受ける
    box("Y3_flr", (68.0, Y4 - WT / 2, 216.9), (4.4, WT, 5.9), T_PAINT, "y", rough=0.9,
        solid=True)
    box("Y3_cil", (68.0, Y4 + 3.2, 216.9), (4.4, WT, 5.6), T_PAINT, "y", rough=0.9)
    for sgn in (-1, 1):
        box("Y3_w%d" % sgn, (68.0 + sgn * 2.2, Y4 + 1.6, 216.9), (WT, 3.2, 5.6), T_PAINT, "x",
            rough=0.9, solid=True)
    wall_with_door("Y3_n", "z", 219.7, 65.65, 70.35, Y4, 3.2, 68.0, DW, DH, T_PAINT)
    door_casing("Y3_nc", "z", 219.55, 68.0, Y4, DW, DH)
    for sgn in (-1, 1):
        glow("Y3_g%d" % sgn, (68.0 + sgn * 1.86, Y4 + 1.5, 219.52), (0.9, 2.9, 0.04),
             [1.0, 0.98, 0.94], 1.05)
    plight("Y3_l1", (68.0, Y4 + 2.2, 217.4), [1.0, 0.98, 0.94], 10.0, 9.0)


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
    # ★規則「歪ませる」。peri(直視しない)は継ぎ目 14 と同じ規則で、2 本目は
    #   「またこれか」にしかならない。ここは【画面が樽型に曲がる】に差し替えた。
    #   柱はわざと外へ反らせて置いてあり、歪みが十分に効いた所でだけ真っ直ぐに揃う。
    #   ★歩くと画面の曲がり方が連続で変わるので、何が起きているかは見れば分かる。
    c18 = Conn(18, F18, 2.5, 14.0, (61.0, Y4, 233.95), "warp-lens",
               lens=dict(kind="warp", at=[round(v, 3) for v in F18],
                         r=6.4, r0=1.5, need=0.75))
    # ★橋は窪みの見切り(x=PX0+0.05)から島の際(x=62.5)まで。手前の板だけ 1.45m にして
    #   見切りへ潜らせない(0.05m でも窪みの底から見上げると板が壁を突き抜けて見える)
    # ★橋をやめて【窪みから生える 2 本の柱】にした。第四幕は 18/19/21 と
    #   3 本続けて「板が架かる」で、結果の見た目が完全に同じだった(自己採点で 橋 6 本)。
    #   規則(直視しない)も焦点も確定域も変えていない ── 出来上がる物だけ差し替える。
    # ★見える頭は間隔(1.45)より小さく(1.35)。重ねると同一平面の検査に落ちる。
    #   渡すのは当たり判定(1.75)の方。
    for i, k in enumerate((0.44, 0.62)):
        xc18 = PX0 + 0.05 + 0.725 + 1.45 * i
        col18 = ent("C18_c%d" % i, (xc18, PY, 233.95), (0.547, (Y4 - PY) / 9.0, 0.547))
        col18["meshRenderer"] = dict(modelPath="models/arch/shaft/sh_col.gltf")
        pl = box("C18_p%d" % i, (xc18, Y4 - 0.09, 233.95), (1.35, 0.18, 1.35),
                 T_METAL, "y", rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47],
                 tile=(0.68, 0.68))
        g = glow("C18_g%d" % i, (xc18, Y4 + 0.01, 233.30), (1.20, 0.04, 0.06),
                 GOLD, 1.25)
        c18.shard(k, [col18, pl, g], glows=[g])
        c18.solid(hit("C18_h%d" % i, (xc18, Y4 - 0.09, 233.95), (1.75, 0.18, 1.90),
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
    # ★規則「色を抜く」。踏み石は色だけが違って明度はほぼ同じにしてある。
    #   色が乗っているうちは【赤い石と緑の石】に見えるが、彩度が落ちると
    #   同じ濃さの 1 つながりの面に融合する(等輝度の錯視そのもの)。
    c20 = Conn(20, F20, 3.4, 17.0, (65.5, Y4 + 0.9, 228.8), "drain-lens",
               lens=dict(kind="drain", at=[round(v, 3) for v in F20],
                         r=6.8, r0=1.6, need=0.80))
    # ★ここも【平たい板】をやめる(自己採点で「橋」が 10 本もあった)。1.1m 角・厚み 0.28 の
    #   踏み石を 2 つ。床から 0.28 上がるが、またげる 0.32 以下なので歩ける。
    # ★2 つの踏み石は【明度をそろえて色相だけ変える】= 等輝度の錯視。
    #   Rec.709 の輝度 (0.2126R + 0.7152G + 0.0722B) はどちらも 0.54〜0.55 で、
    #   まわりのコンクリ(0.57)ともほぼ同じ。色が乗っているうちは「赤い石と緑の石」で
    #   別々の物にしか見えないが、彩度が落ちると 3 つとも同じ濃さになって
    #   1 つながりの面に融合する。だから【色を抜かないと形が見えない】。
    STONE = ([0.86, 0.46, 0.40], [0.36, 0.62, 0.44])
    for i, k in enumerate((0.40, 0.58)):
        zc = 226.05 + i * 1.10                       # 回廊(225.5) と 島D(227.7) の間ぴったり
        pl = box("C20_p%d" % i, (68.0, Y4 + 0.14, zc), (1.1, 0.28, 1.10),
                 T_CONC, "y", rough=0.85, color=STONE[i])
        c20.shard(k, [pl])
        c20.solid(hit("C20_h%d" % i, (68.0, Y4 + 0.14, zc), (1.1, 0.28, 1.24), kinematic=True))
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
    # ★規則「ぼかす」。dark(暗の一瞬)は継ぎ目 16 と 25 でも使っていて 3 本目になる。
    #   ここは【ピントを外す】に差し替えた。細部が潰れると低い周波数の構造だけが残り、
    #   庇の輪郭が浮き上がる ── 目を細めると絵が見えてくる、あの見え方。
    #   ★はっきり見ようとするほど解けない。この作品で唯一「よく見ない」が正解の規則。
    c21 = Conn(21, F21, 3.2, 16.0, (65.5, Y4, 241.7), "blur-lens",
               lens=dict(kind="blur", at=[round(v, 3) for v in F21],
                         r=6.0, r0=1.4, need=0.78))
    # ★ここも橋をやめて【回廊から張り出す庇】にした。18(柱)・19(触れる板)・21(庇)で
    #   第四幕の 3 本が別々の見た目になる。規則も焦点も確定域も変えていない。
    for i, k in enumerate((0.42, 0.60)):
        zc = 242.25 - i * 1.10                       # 回廊(242.8) と 島B(240.6) の間ぴったり
        cv21 = ent("C21_v%d" % i, (65.5, Y4 - 0.34, zc + 0.55), (0.36, 1.0, 0.22),
                   rot=(0, 180, 0))
        cv21["meshRenderer"] = dict(modelPath="models/arch/shaft/sh_canopy.gltf")
        pl = box("C21_p%d" % i, (65.5, Y4 - 0.09, zc), (2.0, 0.18, 1.10),
                 T_METAL, "y", rough=0.5, metal=0.5, color=[0.50, 0.50, 0.47])
        g = glow("C21_g%d" % i, (65.5, Y4 + 0.01, zc), (1.9, 0.04, 0.06), GOLD, 1.25)
        c21.shard(k, [cv21, pl, g], glows=[g])
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
DECOR_RE = re.compile(r"(_mark$|dud\d*$|lure|_exit(_b)?$|_c[lrt]$)")


JOINT_NOTE = {}          # cid -> note。group_entities が見出しに使う


def group_entities():
    """ヒエラルキーを【幕 → 部屋 / 継ぎ目】へ仕分ける。

    ★なぜ要るか: 1200 個の実体が全部シーンの直下に並んでいて、エディタの階層が
      読めなかった。名前(A_ / C12_ / S3a_ …)に規則はあるが、目で追える量ではない。

    ★親の transform は必ず単位(位置0 / 回転0 / 倍率1)にすること。
      このエンジンの親子は【transform の親子】なので、親を動かすと子が全部ずれる。
      ここで作る親は「入れ物」でしかないので、何も持たせない。

    仕分けの決め方:
      ・C<数字>_ で始まる物 … その番号の継ぎ目へ。番号から幕が決まる
      ・それ以外            … z 座標でどの幕かを決める(幕は z で並んでいる)
      ・LM_ と Sun          … システム(プレイヤー・カメラ・HUD・太陽)
      ★既に親を持つ物(HUD の中身)はそのまま。二重に親を付け替えない。
    """
    def act_of_cid(cid):
        return 1 if cid <= 4 else 2 if cid <= 10 else 3 if cid <= 16 else 4 if cid <= 21 else 5

    def act_of_z(z):
        return 1 if z < 80.0 else 2 if z < 172.0 else 3 if z < 220.0 else 4 if z < 250.0 else 5

    made = []

    def group(name, parent=None):
        for g in made:
            if g["name"] == name:
                return g
        g = dict(name=name, guid=guid("group/" + name),
                 transform=dict(position=[0, 0, 0], rotation=[0, 0, 0], scale=[1, 1, 1]))
        if parent is not None:
            g["parentGuid"] = parent["guid"]
        made.append(g)
        return g

    acts = {a: group("第%d幕" % a) for a in (1, 2, 3, 4, 5)}
    rooms = {a: group("第%d幕 / 部屋と什器" % a, acts[a]) for a in (1, 2, 3, 4, 5)}
    system = group("システム")
    joints = {}

    for e in ES:
        n = e["name"]
        if "parentGuid" in e:
            continue                                  # HUD の中身。既に親がいる
        if n == "Sun" or n.startswith("LM_"):
            e["parentGuid"] = system["guid"]
            continue
        m = re.match(r"^C(\d+)_", n)
        if m:
            cid = int(m.group(1))
            if cid not in joints:
                a = act_of_cid(cid)
                note = JOINT_NOTE.get(cid, "")
                joints[cid] = group("第%d幕 / 継ぎ目%02d %s" % (a, cid, note), acts[a])
            e["parentGuid"] = joints[cid]["guid"]
            continue
        z = e.get("transform", {}).get("position", [0, 0, 0])[2]
        e["parentGuid"] = rooms[act_of_z(z)]["guid"]

    # ★入れ物を先頭へ置く。読み込みは guid で引くので順序は問わないが、
    #   エディタの階層とシーン JSON のどちらも、親が上にある方が読みやすい。
    ES[:0] = made
    print("  ヒエラルキーを %d 個の入れ物へ仕分けた(幕 5 / 部屋 5 / 継ぎ目 %d / システム 1)"
          % (len(made), len(joints)))
    return len(made)


def hud_guid(name):
    """HUD の guid は名前から決める。★source/gen_ui.js の guidOf と同じ式にしてある。
    どちらで組んでも同じ guid になるので、作り直しても差分が出ない。"""
    h1, h2 = 0x9e3779b9, 0x85ebca6b
    for ch in name:
        h1 = ((h1 ^ ord(ch)) * 0x01000193) & 0xFFFFFFFF
        h2 = ((h2 + ord(ch)) * 0x85ebca6b) & 0xFFFFFFFF
    return ("%08x%08x" % (h1, h2))[:16]


def build_hud(canvas):
    """source/hud_layout.json の表どおりに、案内 / 操作と設定の UI を組む。

    ★表は source/hud_layout.json が唯一の編集元。同じ表を source/gen_ui.js も読んで、
      Python の無い環境から既存のシーンへ差し込めるようにしてある。
      位置や文言を直すのは hud_layout.json だけでよい。
    """
    layout = json.loads((ROOT / "source/hud_layout.json").read_text(encoding="utf-8"))
    pal = layout["palette"]
    made = 0

    for el in layout["elements"]:
        if "name" not in el:            # "_" だけの行はコメント
            continue
        x0 = el["x0"] if "x0" in el else el["x"] - el["w"] / 2
        x1 = el["x1"] if "x1" in el else el["x"] + el["w"] / 2
        y0, y1 = el["y"] - el["h"] / 2, el["y"] + el["h"] / 2

        e = ent(el["name"])
        e["guid"] = hud_guid(el["name"])
        e["parentGuid"] = canvas["guid"]
        e["uiRect"] = dict(anchorMin=[0, 0], anchorMax=[0, 0], pivot=[0.5, 0.5],
                           offsetMin=[x0, y0], offsetMax=[x1, y1],
                           # ★hidden の要素は消した状態で置く。UIText の縁取りと
                           #   UIImage の枠は color のアルファとは別枠で描かれるので、
                           #   アルファ 0 で置くだけでは【縁だけが画面に残る】。
                           #   出すのは Liminal.lua の uiFade の仕事。
                           visible=not el.get("hidden", False),
                           order=el.get("order", 0))

        rgb = el.get("color") or (pal["sub"] if el.get("sub") else pal["ink"])
        a = el.get("a", 1)
        if el["type"] == "image":
            img = dict(texturePath=el.get("tex", ""), color=[rgb[0], rgb[1], rgb[2], a])
            if el.get("radius"):
                img["cornerRadius"] = el["radius"]
            # ★飾りはクリックを遮らない。暗幕(LM_Menu_Dim)が既定のままだと画面全部を
            #   覆ってクリックを吸い、下のボタンが一切押せなくなる。
            if el.get("noRay"):
                img["raycastBlock"] = False
            e["uiImage"] = img
        else:
            e["uiText"] = dict(text=el.get("text", ""), fontSize=el.get("size", 22),
                               color=[rgb[0], rgb[1], rgb[2], a],
                               alignH=el.get("align", 1), alignV=1, wrap=False,
                               # ★縁取りは付けない。エンジンは縁のアルファを本体の color.w
                               #   とは別勘定で描く(outlineColor.w * ctx.alphaMul)ので、
                               #   薄くすると【縁だけ残る】。hud_layout.json の頭を読むこと。
                               outlineWidth=0, outlineColor=[0.03, 0.03, 0.03, 0])

        # マウスで押せる要素。当たり判定も拡縮も UISystem がやる。
        # ★ボタンの色は【描く時に掛ける倍率】なので、uiFade の setUiColor と喧嘩しない
        if el.get("button"):
            if el.get("flat"):      # 行そのもの。押せるが見た目は変えない
                e["uiButton"] = dict(onClickEvent=el["button"], normalColor=[1, 1, 1, 1],
                                     hoverColor=[1, 1, 1, 1], pressedColor=[1, 1, 1, 1],
                                     interactable=True)
            else:                   # − / + / 閉じる
                e["uiButton"] = dict(onClickEvent=el["button"],
                                     normalColor=[0.80, 0.80, 0.76, 1],
                                     hoverColor=[1, 1, 1, 1],
                                     pressedColor=[0.55, 0.55, 0.50, 1], interactable=True)
        made += 1

    print("  HUD 要素を %d 個 組んだ(source/hud_layout.json)" % made)
    return made


def add_walk_colliders(p_height=1.80, p_step=0.32):
    """歩いて当たるはずなのに擦り抜ける箱へ、静的な当たり判定をまとめて足す。

    ★なぜ機械で決めるか: 什器は 900 個ある。box(solid=True) の付け忘れは手では必ず出るし、
      逆に天井の照明や床の擦れ跡へ付けると『見えない壁』になる。そこで
      【床からの高さ帯に掛かるか】という一つの規則だけで決める。

        ・箱の下端が身長より上   … いらない(頭上を通るだけ)
        ・箱の上端がまたげる高さ … いらない(踏んで歩ける)
        ・その間に掛かる         … 要る(体が通れない)

    付けないもの:
      ・継ぎ目の仕掛けが掴んでいる実体(破片・出現物・可動物・丁番・標識)。
        破片は焦点から見た時だけ形になる幻で、動く。
      ・glow() の発光板。物ではなく明かり。
      ・囮と偽の印(lure / dud / mark)。★囮の板は「浮いている破片と同じ見かけ」に
        【わざと】してある。当たり判定を付けると、ぶつかるかどうかで本物の破片と
        見分けがついてしまい、謎解きが崩れる。
      ・非常口の標識と開口のケーシング。壁に貼った薄い飾りで、壁側に当たり判定がある。

    ★同じ規則が source/fix_colliders.js にもある(Python の無い環境から直すため)。
      片方だけ直さないこと。
    """
    reserved = set()
    for c in CONNS:
        d = c.data()
        for sh in d.get("shards", ()):
            for e in sh.get("ents", ()):
                reserved.add(e["n"])
        for key in ("solids", "movers", "hinges", "lights", "shines", "hides"):
            for x in d.get(key, ()) or ():
                reserved.add(x["n"] if isinstance(x, dict) else x)
        for x in d.get("glows", ()) or ():
            reserved.add(x)
        for n in d.get("darkLights", ()) or ():
            reserved.update((n, n + "_l", n + "_p"))
        if d.get("slot"):
            reserved.add(d["slot"]["ent"])
        if d.get("relay"):
            reserved.add(d["relay"]["weight"])
        for t in d.get("trail", ()) or ():
            if isinstance(t, dict) and "n" in t:
                reserved.add(t["n"])

    def aabb(e):
        x, y, z = e["transform"]["position"]
        w, h, dd = e["transform"]["scale"]
        return (x - w / 2, x + w / 2, y - h / 2, y + h / 2, z - dd / 2, z + dd / 2)

    floors = [aabb(e) for e in ES if "boxCollider" in e and "transform" in e]
    added = 0

    for e in ES:
        if e.get("primitive") != "box" or "boxCollider" in e or "transform" not in e:
            continue
        if e["name"] in reserved or DECOR_RE.search(e["name"]):
            continue
        # glow() は ReconnectInk シェーダーだけを持ち、テクスチャを持たない
        if "shader" in e and "materialTextureOverrides" not in e:
            continue

        x0, x1, y0, y1, z0, z1 = aabb(e)
        floor_y = None
        for fx0, fx1, fy0, fy1, fz0, fz1 in floors:
            if x0 >= fx1 or x1 <= fx0 or z0 >= fz1 or z1 <= fz0:
                continue
            if fy1 > y1 - 0.02:              # 自分より上の面は床ではない
                continue
            if floor_y is None or fy1 > floor_y:
                floor_y = fy1
        if floor_y is None:
            continue
        if y0 - floor_y >= p_height or y1 - floor_y <= p_step:
            continue

        e["boxCollider"] = dict(halfExtents=[.5, .5, .5], offset=[0, 0, 0])
        e["rigidBody"] = dict(motionType=0, mass=1, friction=.75, restitution=0,
                              useGravity=False, linearDamping=.02, angularDamping=.01)
        added += 1

    print("  歩行用の当たり判定を %d 個 追加した" % added)
    return added


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

    # ---- 案内板 3 枚(【文字を一切使わない】遊び方の説明。第1幕の入口だけ) ----
    # ★何のためにあるか: 初めて立った人には「押す物が無い」ことすら分からない。
    #   HUD も文字も出さない作品なので、説明は【施設の案内板】として世界の中に置く。
    #   非常口の標識と同じ語彙(壁に貼った板・絵記号だけ)にしてあるので、
    #   リミナル空間の「誰も居ない建物」という体裁を壊さない。
    # ★3 枚で言うことは 3 つだけ:
    #     1 歩く / 見る          … 押すボタンは無い
    #     2 床の金の印の上に立つ … 金 = 継ぎ目の色(GOLD)。印と破片が仲間だと繋げる
    #     3 破片が 1 つに重なる  … 何が起きたら正解なのか
    # ★絵は source/ui_icons/svg_signs/*.svg → assets/ui/signs/*.png(build_signs.js)。
    #   額縁は Blender 製 assets/models/props/sign_guide.gltf(source/blender_signs.py)。
    #   額縁と絵を分けてあるので、絵の描き直しに Blender は要らない。
    SIGN_Y = 2.24          # 板の中心の高さ。★下端 1.91m は身長 1.80 より上
    SIGN_W, SIGN_H = 1.00, 0.66

    def guide_sign(name, z, side, png):
        """壁に貼る案内板 1 枚。額縁(模型) + 絵の板(箱) + 小さな灯り。

        side = +1 … 東の壁(x=+1.5)に貼る。面は -X を向く → yaw = +90
        side = -1 … 西の壁(x=-1.5)に貼る。面は +X を向く → yaw = -90
        ★箱の -Z 面を横向きに回す作法は exit_sign_x と同じ。面の出す向きへ
          0.045 ずらすところまで揃えてある(揃えないと絵だけ壁へ潜る)。

        ★★当たり判定は付けない(壁に貼った飾りで、壁側に当たり判定がある)。
          add_walk_colliders() は「床から p_height=1.80 より上にある箱」を対象外に
          するので、板の下端(2.24 - 0.33 = 1.91)がそれより上にあることが条件。
          高さを下げるなら、その規則の側も一緒に見直すこと。
          ついでに、この高さは【施設の案内板の高さ】そのものでもある(目線 1.70 の少し上)。
        """
        x = side * 1.5
        yaw = 90.0 * side
        out = side * -0.045          # 面が出ている向き(廊下の中心へ向かう向き)
        # 額縁。原点 = 壁の面の中心で、-Z が見る側。倍率は 1(実寸で作ってある)
        fr = ent(name + "_fr", (x, SIGN_Y, z), (1, 1, 1), (0, yaw, 0))
        fr["meshRenderer"] = dict(modelPath="models/props/sign_guide.gltf")
        # 絵の板。額縁の開口(0.98 x 0.64)へ 1cm ずつ噛ませて落とし込む
        # ★uvTiling は 1x1。焼いた PNG を 1 枚だけ貼る(繰り返さない)
        pl = box(name, (x + out, SIGN_Y, z), (SIGN_W, SIGN_H, 0.03), png, "z",
                 rough=0.86, tile=(1.0, 1.0))
        pl["transform"]["rotation"] = [0, yaw, 0]
        # 板を照らす小さな灯り。★弱く(0.9)。強いと壁に白い染みが出て、
        #   「飛び飛びに点いた蛍光灯」で作った明暗の縞が消える
        plight(name + "_l", (x + out * 7.0, SIGN_Y + 0.22, z), WARM, 0.9, 2.4)

    # 置き場所は「見える順」。★z=-1.6 は出発点(0,0.9,-6)から真っ直ぐ見える位置に選んだ。
    #   最初の 1 枚を見落とすと以降が全部効かないので、ここだけは視界の中心寄りにする。
    #   2 枚目は床の印(F1 = z 6.30)の手前、3 枚目は突き当りへ歩き出す辺り。
    #   東 → 西 → 東 と互い違いにして、同じ壁で見落としが続かないようにする。
    guide_sign("A_sign1", -1.60, +1, "ui/signs/sign_walk_look.png")
    guide_sign("A_sign2", 3.40, -1, "ui/signs/sign_stand_mark.png")
    guide_sign("A_sign3", 11.40, +1, "ui/signs/sign_shards_align.png")

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

    # ---- 水を張る --------------------------------------------------------
    # ★rough を落とすだけで灯りが線状に映り込み『水面』に見える(空プールの頃の
    #   水たまりで確認済みの手口)。エンジンには g_sceneColor / g_reflection を
    #   カスタムシェーダーへ渡す口が無いので、PoolWater.hlsl の反射は当てにしない。
    #   ここは素の PBR で作り、粗さと金属質と色だけで水にする。
    # ★水位は -0.42。一番上の段(-0.35)だけが水の上に出る = 段を降りると水に入る、
    #   という高さ関係が一目で読める。深い所で約 1.0m。
    WLV = -0.42
    # ★alpha は 0.45 まで下げる。FlowWater は【加算の】スペキュラを乗せるので、
    #   不透明にすると室内灯を拾って乳白色に飛び、色もタイルも消える(実際に飛んだ)。
    #   薄くして下のタイルを透かせると、白い艶は水面の照り返しとして正しく読める。
    # ★reflect も 0.3 まで。fresnel と流れの筋の両方に掛かるので、上げると縁が白く縁取られる。
    water("C_water", (0, WLV, (50.90 + 58.94) / 2), (PW * 2 - 0.24, 0.02, 58.94 - 50.90),
          T_TILEF, [0.11, 0.31, 0.35], alpha=0.45, reflect=0.30,
          flow=0.09, wave=0.010, distort=0.020, tile=(3.0, 2.2))
    # 水際の線。★これが無いと水面が『床に貼った青い板』に見える。
    #   壁の内側に一本だけ濃い帯を入れると、そこまで水が来ていると読める
    for sgn in (-1, 1):
        box("C_wline%d" % sgn, (sgn * (PW - 0.13), WLV - 0.03, 55.92),
            (0.02, 0.06, 6.04), T_TILEW, "x", rough=0.25, color=[0.42, 0.55, 0.55])
    box("C_wlinen", (0, WLV - 0.03, 58.93 - 0.02), (PW * 2 - 0.26, 0.06, 0.02),
        T_TILEW, "z", rough=0.25, color=[0.42, 0.55, 0.55])
    # 水の中は光が回らない。底を少しだけ暗く沈ませる灯りを 1 つ置く
    plight("C_wlight", (0, WLV + 0.55, 55.6), COOL, 3.2, 7.0)
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
    # ★第三幕は 2 つある。ACT3_SMALL で切り替える(受け渡しは同じなので差し替え可能)。
    #     False … 旧版 act3()。58x42m・高さ 28m の縦穴。【通し検査 PASS 済み】
    #     True  … 人間の尺度へ作り直した版(source/act3_small.py)。体積 約 1/20。
    #             ★まだ机上検査を通っていない(確定域の詰めと面の重なりが残っている)。
    if ACT3_SMALL:
        import act3_small
        act3_small.build(sys.modules[__name__], Y3, DW, DH)
    else:
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
    build_hud(canvas)

    t = ui("LM_End", (0, 0.5), (1, 0.5), (0, -30), (0, 30), 3)
    # ★終わりは白い部屋で出す = 文字は【暗色】。明色 + 黒縁だと縁だけが残って潰れる
    t["uiText"] = dict(text="", fontSize=42, color=[0.13, 0.13, 0.12, 0.0], alignH=1, alignV=1,
                       wrap=False, outlineWidth=0.0, outlineColor=[1, 1, 1, 0.0])

    add_walk_colliders()
    group_entities()

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
