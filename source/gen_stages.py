# -*- coding: utf-8 -*-
"""JUNCTION / 継ぎ目 のステージを生成する。
シーン JSON はここが唯一の正。エディタで手で足した物は次の実行で消える。

実行(numpy/py は Blender 同梱のものを使う):
  "C:/Program Files/Blender Foundation/Blender 5.1/5.1/python/bin/python.exe" gen_stages.py

★部屋は「同じ顔をした閉じた箱」。互いに 40m 以上離して置き、外からは見えない。
  ドアの向こうは常に白い虚無(Void_<id> の白板)で、繋がっていても物理的には
  通り抜けられない。通過は Junction.lua がテレポートで行う(=ポータル描画は不要)。

★ドアの向き: transform.rotation.y は「forward が部屋の内側を向く」ように置く。
  forward = (sin(yaw), 0, cos(yaw))。Junction.lua はこの規約に依存している。

★2026-09-01(2): 見た目を作り直した。
  当たり判定は今まで通り「色の付いた箱」が持つが、その 5mm 手前に
  source/blender_kit.py が書き出した内装モデル(壁紙・絨毯・落とし天井・埋込照明)を
  置いて、箱を完全に隠す。モデル側には rigidBody を付けない = 物理に載らない。
  寸法は blender_kit.py の SPAN/WALLH/DOORW/DOORH と【必ず一致】させること。

★2026-09-01(3): 文字を出さないゲームにした。ルールは
  「カメラワーク + 色 + 床のレーン」だけで教える(Junction.lua の CINE/TEACH)。
  そのためステージを 8 面に増やし、1 面につき 1 つだけ新しいことを足す。

★階層: エンティティは [Rooms]/[Doors]/[System] の下にグループ分けしてある。
  グループ node は原点・無回転・スケール1なので、子の transform は world と一致する。
  ★MainCamera だけは親を付けない。CharacterController は world 座標で駆動され、
    PhysicsSystem が transform へ world を書き戻すので、親を持つと二重変換で壊れる。
"""
import json, math, random, os

random.seed(20260901)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "scenes")

HALF   = 6.0    # 部屋の内寸の半分(12m 角)
WALLT  = 0.3    # 壁の厚み
WALLH  = 4.0    # 天井高
DOORW  = 1.5    # ドアの幅
DOORH  = 2.6    # ドアの高さ
SPAN   = HALF * 2 + WALLT   # = 12.3。blender_kit.py の SPAN と一致

# 箱はモデルの裏に隠れるが、開口の縁から覗くことがあるので近い色にしておく
C_WALL    = [0.62, 0.60, 0.55]
C_FLOOR   = [0.24, 0.20, 0.12]
C_CEIL    = [0.72, 0.72, 0.70]
C_VOID    = [1.00, 1.00, 1.00]
C_GOAL    = [0.10, 0.75, 0.50]
C_BOUND   = [0.42, 0.44, 0.42]   # 角度の境界線(色は付けない。色はレーンが持つ)

# ドア固有色。Junction.lua の DOOR_COLOR と【必ず一致させること】
DOOR_COLORS = {
    "a": [0.20, 0.85, 0.55],   # 緑
    "b": [1.00, 0.55, 0.12],   # 橙
    "c": [0.95, 0.25, 0.45],   # 赤
    "d": [0.30, 0.60, 1.00],   # 青
    "e": [0.80, 0.40, 1.00],   # 紫
    "f": [0.20, 0.90, 0.95],   # 水
    "g": [1.00, 0.82, 0.15],   # 黄
    "h": [1.00, 0.45, 0.72],   # 桃
}

HIDE_Y = -200.0   # 隠す時に飛ばす高さ。scale=0 は退化三角形になるので使わない

MAX_EXITS = 5     # 合流点 5 枚 → 出口 4 つ。レーン/柱はこの数だけ用意する


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
        prim="box"):
    e = base(name, pos, rot, scale, parent)
    e["primitive"] = prim
    e["color"] = list(color)
    e["material"] = {"metallic": 0.0, "roughness": rough}
    if collide:
        e["boxCollider"] = {"halfExtents": [0.5, 0.5, 0.5], "offset": [0.0, 0.0, 0.0]}
        e["rigidBody"] = {"angularDamping": 0.01, "continuousCollision": False,
                          "friction": 0.6, "linearDamping": 0.02, "mass": 1.0,
                          "motionType": 0, "restitution": 0.0, "useGravity": False}
    return e


def model(name, path, pos, yaw=0.0, parent=None, scale=(1, 1, 1)):
    """内装モデル。★rigidBody を付けない = 物理に載らない(当たり判定は箱側が持つ)。"""
    e = base(name, pos, (0.0, yaw, 0.0), scale, parent)
    e["meshRenderer"] = {"modelPath": path}
    return e


def plight(name, pos, color, intensity, rng, parent=None):
    e = base(name, pos, parent=parent)
    e["pointLight"] = {"castShadows": False, "color": list(color),
                       "intensity": float(intensity), "range": float(rng)}
    return e


def marker(name, pos, yaw=0.0, parent=None):
    """当たり判定も見た目も持たない印。Junction.lua が transform だけを読む。"""
    return base(name, pos, (0.0, float(yaw), 0.0), parent=parent)


def group(ents, name, parent=None):
    """階層整理用の空 node。原点・無回転・スケール1 = 子の transform は world のまま。"""
    e = marker(name, (0.0, 0.0, 0.0), 0.0, parent)
    ents.append(e)
    return e["guid"]


# ---- 壁の向き。inward = 部屋の中心を向くベクトル ----
WALLS = {
    "N": {"yaw": 180.0, "axis": "z", "sign": +1},
    "S": {"yaw":   0.0, "axis": "z", "sign": -1},
    "E": {"yaw": 270.0, "axis": "x", "sign": +1},
    "W": {"yaw":  90.0, "axis": "x", "sign": -1},
}


def inward(yaw):
    r = math.radians(yaw)
    return math.sin(r), math.cos(r)


def door_entities(ents, did, wc, info, parent):
    """ドア 1 枚ぶんの実体一式。名前の規約は Junction.lua と対。"""
    g = group(ents, "Door %s" % did, parent)
    yaw = info["yaw"]
    dx, dz = wc[0], wc[2]
    ix, iz = inward(yaw)
    col = DOOR_COLORS[did]

    ents.append(marker("Door_%s" % did, (dx, 0.0, dz), yaw, g))

    # 虚無の白板。常に塞がっている(通過はテレポート)
    sc = (DOORW, DOORH, 0.10) if info["axis"] == "z" else (0.10, DOORH, DOORW)
    ents.append(box("Void_%s" % did, (dx, DOORH * 0.5, dz), sc, C_VOID, rough=1.0, parent=g))

    # 白板を白飛びさせる灯り。inward 側へ少し出す
    ents.append(plight("VoidLight_%s" % did, (dx + ix * 0.55, 1.35, dz + iz * 0.55),
                       (1.0, 1.0, 1.0), 5.2, 3.2, g))

    # ★枠はドア固有色。これが「このドアは青」の一次表示。
    #   モデルのケーシング(白い縁飾り)の外側に細い色帯として乗せる
    fw = 0.10
    FACE = 0.185   # 壁中心 -> 内装モデル面(0.155)より少し手前。ここを間違えると色帯が壁に埋まる
    for s in (-1, +1):
        if info["axis"] == "z":
            p = (dx + s * (DOORW * 0.5 + 0.13 + fw * 0.5), DOORH * 0.5 + 0.05,
                 dz + iz * FACE)
            sc2 = (fw, DOORH + 0.26, 0.12)
        else:
            p = (dx + ix * FACE, DOORH * 0.5 + 0.05,
                 dz + s * (DOORW * 0.5 + 0.13 + fw * 0.5))
            sc2 = (0.12, DOORH + 0.26, fw)
        ents.append(box("Frame_%s_%d" % (did, s), p, sc2, col, collide=False,
                        rough=0.35, parent=g))
    # まぐさ側の色帯(遠くからでもドアの色が分かるように)
    if info["axis"] == "z":
        p = (dx, DOORH + 0.13 + fw * 0.5, dz + iz * FACE)
        sc3 = (DOORW + 0.26 + fw * 2, fw, 0.12)
    else:
        p = (dx + ix * FACE, DOORH + 0.13 + fw * 0.5, dz)
        sc3 = (0.12, fw, DOORW + 0.26 + fw * 2)
    ents.append(box("Frame_%s_top" % did, p, sc3, col, collide=False, rough=0.35, parent=g))

    # 合流点の刻印(この枠が合流点の何番目か)。既定は隠す
    for k in range(1, 6):
        ents.append(box("Mark_%s_%d" % (did, k), (dx, HIDE_Y, dz), (0.10, 0.26, 0.06),
                        col, collide=False, rough=0.4, parent=g))

    # 角度の分割線(境界)。既定は隠す
    for k in range(1, 7):
        ents.append(box("Slice_%s_%d" % (did, k), (dx, HIDE_Y, dz), (0.06, 0.02, 1.0),
                        C_BOUND, collide=False, parent=g))

    # ★助走レーン(スライスの中心線)と、その先に立つ柱。行き先のドア色で塗る。
    #   「青い柱の所から歩いてドアに入れば、青いドアから出る」を体で覚えさせる装置
    for k in range(1, MAX_EXITS + 1):
        ents.append(box("Lane_%s_%d" % (did, k), (dx, HIDE_Y, dz), (0.14, 0.02, 1.0),
                        C_VOID, collide=False, rough=0.5, parent=g))
        ents.append(box("Post_%s_%d" % (did, k), (dx, HIDE_Y, dz), (0.16, 1.15, 0.16),
                        C_VOID, collide=False, rough=0.4, parent=g))


# ---------------------------------------------------------------- 部屋の中の物
def props(ents, rid, cx, cz, spec, parent):
    """spec: [(種類, x, z, yaw), ...] 部屋ローカル座標。部屋の識別性を上げる小物。
    ★どれも当たり判定を持たない(通り抜ける)。行き先の判断を邪魔しないため。"""
    PATH = {"bench": "models/bench.gltf", "column": "models/column.gltf"}
    for i, (kind, lx, lz, yaw) in enumerate(spec):
        if kind == "vent":
            ents.append(model("%s_Vent_%d" % (rid, i), "models/vent.gltf",
                              (cx + lx, 2.6, cz + lz), yaw, parent))
        else:
            ents.append(model("%s_%s_%d" % (rid, kind, i), PATH[kind],
                              (cx + lx, 0.0, cz + lz), yaw, parent))


def room(ents, rid, cx, cz, doors, doors_parent, rooms_parent,
         lightcol=(0.98, 0.96, 0.88), intensity=8.0, propspec=()):
    """doors: {"N": "a", ...} 壁 -> ドア id。"""
    g = group(ents, "Room %s" % rid, rooms_parent)

    # ---- 当たり判定の箱(見えない位置に隠れる) ----
    ents.append(box("%s_Floor" % rid, (cx, -0.15, cz), (SPAN, 0.3, SPAN), C_FLOOR,
                    rough=0.95, parent=g))
    ents.append(box("%s_Ceil" % rid, (cx, WALLH + 0.15, cz), (SPAN, 0.3, SPAN), C_CEIL,
                    parent=g))
    # ---- 内装モデル(箱の 5mm 内側) ----
    ents.append(model("%s_FloorM" % rid, "models/floor.gltf", (cx, 0.005, cz), 0.0, g))
    ents.append(model("%s_CeilM" % rid, "models/ceiling.gltf", (cx, WALLH - 0.005, cz),
                      0.0, g))

    for w in ("N", "S", "E", "W"):
        info = WALLS[w]
        off = HALF + WALLT * 0.5
        if info["axis"] == "z":
            wc = (cx, WALLH * 0.5, cz + info["sign"] * off)
            full = (SPAN, WALLH, WALLT)
            mp = (cx, 0.0, cz + info["sign"] * (HALF - 0.005))
        else:
            wc = (cx + info["sign"] * off, WALLH * 0.5, cz)
            full = (WALLT, WALLH, SPAN)
            mp = (cx + info["sign"] * (HALF - 0.005), 0.0, cz)

        did = doors.get(w)
        # 内装モデル(+Z が部屋の内側を向く)
        ents.append(model("%s_WallM_%s" % (rid, w),
                          "models/wall_door.gltf" if did else "models/wall.gltf",
                          mp, info["yaw"], g))

        if did is None:
            ents.append(box("%s_Wall_%s" % (rid, w), wc, full, C_WALL, parent=g))
            continue

        segw = (SPAN - DOORW) * 0.5
        segc = (DOORW + segw) * 0.5
        for s in (-1, +1):
            if info["axis"] == "z":
                p = (wc[0] + s * segc, wc[1], wc[2]); sc = (segw, WALLH, WALLT)
            else:
                p = (wc[0], wc[1], wc[2] + s * segc); sc = (WALLT, WALLH, segw)
            tag = "%s_Wall_%s_%s" % (rid, w, "n" if s < 0 else "p")
            ents.append(box(tag, p, sc, C_WALL, parent=g))
        lin_h = WALLH - DOORH
        if info["axis"] == "z":
            p = (wc[0], DOORH + lin_h * 0.5, wc[2]); sc = (DOORW, lin_h, WALLT)
        else:
            p = (wc[0], DOORH + lin_h * 0.5, wc[2]); sc = (WALLT, lin_h, DOORW)
        ents.append(box("%s_Lintel_%s" % (rid, w), p, sc, C_WALL, parent=g))

        door_entities(ents, did, wc, info, doors_parent)

    # ---- 埋め込み照明。灯りは器具の少し下に置く(乳白カバーを下から光らせる) ----
    # ★2灯だと 12m 角の隅まで届かず天井が灰色に沈む(= リミナルに見えない)。
    #   実物の office と同じく 2x2 で天井を面で光らせる。
    for i, (ox, oz) in enumerate(((-3.1, -3.1), (3.1, -3.1), (-3.1, 3.1), (3.1, 3.1))):
        ents.append(model("%s_Troffer_%d" % (rid, i), "models/troffer.gltf",
                          (cx + ox, WALLH - 0.01, cz + oz), 0.0, g))
        ents.append(plight("%s_Light_%d" % (rid, i), (cx + ox, WALLH - 0.45, cz + oz),
                           lightcol, intensity, 16.0, g))

    props(ents, rid, cx, cz, propspec, g)


def scene(st):
    ents = []
    g_sys = group(ents, "[System]")
    g_rooms = group(ents, "[Rooms]")
    g_doors = group(ents, "[Doors]")

    ents.append({"guid": guid(), "name": "Ambient", "parentGuid": g_sys,
                 "directionalLight": {"ambient": 0.035, "color": [0.85, 0.88, 1.0],
                                      "direction": [-0.3, -0.9, -0.3], "intensity": 0.0},
                 "transform": {"position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0],
                               "scale": [1.0, 1.0, 1.0]}})

    for r in st["rooms"]:
        rid, cx, cz, doors = r[0], r[1], r[2], r[3]
        pr = r[4] if len(r) > 4 else ()
        room(ents, rid, cx, cz, doors, g_doors, g_rooms, propspec=pr,
             lightcol=st.get("lightcol", (0.98, 0.96, 0.88)),
             intensity=st.get("intensity", 8.0))

    # 出口の目印。★太い箱だと「緑の箱」にしか見えない。細く高い光柱にする
    gx, gz = st["goal"]
    ents.append(box("Goal", (gx, 1.7, gz), (0.42, 3.4, 0.42), C_GOAL,
                    collide=False, rough=0.25, parent=g_sys))
    ents.append(box("GoalBase", (gx, 0.04, gz), (1.5, 0.08, 1.5), C_GOAL,
                    collide=False, rough=0.3, parent=g_sys))
    ents.append(plight("GoalLight", (gx, 1.9, gz), (0.25, 1.0, 0.62), 9.0, 12.0, g_sys))
    gp = base("GoalFx", (gx, 0.15, gz), parent=g_sys)
    gp["particleEmitter"] = {"kind": 0, "blend": 0, "rate": 14, "orient": 0,
                             "playOnStart": True, "looping": True, "duration": 1.0,
                             "dir": [0.0, 1.0, 0.0], "spread": 0.12, "speed": 0.9,
                             "speedVar": 0.3, "size": 0.16, "sizeEnd": 0.0,
                             "life": 2.6, "lifeVar": 0.5,
                             "color": [0.35, 1.0, 0.7], "colorEnd": [0.1, 0.6, 0.4],
                             "intensity": 2.4, "gravity": 0.0, "drag": 0.6}
    ents.append(gp)

    # 虚無に浮かぶドアの候補(接続モードで使い回す)。既定は隠す
    g_proxy = group(ents, "Proxies", g_sys)
    for i in range(1, 9):
        ents.append(box("Proxy_%d" % i, (0.0, HIDE_Y, 0.0), (0.9, 1.7, 0.08),
                        C_VOID, collide=False, rough=0.55, parent=g_proxy))

    # ★案内の光。文字を出さない代わりに「次に行く場所」をこれが漂って示す
    ents.append(box("Pilot", (0.0, HIDE_Y, 0.0), (0.22, 0.22, 0.22), (0.55, 1.0, 0.85),
                    collide=False, rough=0.2, parent=g_sys, prim="sphere"))
    ents.append(plight("PilotLight", (0.0, HIDE_Y, 0.0), (0.35, 1.0, 0.80), 2.6, 5.0, g_sys))

    # ★プレイヤーは親を付けない(CharacterController は world 駆動)
    sp = st["spawn"]
    ents.append({
        "guid": guid(), "name": "MainCamera",
        "camera": {"farClip": 300.0, "fovDegrees": 74.0, "isActive": True,
                   "nearClip": 0.06, "orthoSize": 10.0, "projection": 0},
        "characterController": {"gravityScale": 1.0, "halfHeight": 1.3, "jumpSpeed": 6.0,
                                "mass": 70.0, "maxSlopeDeg": 50.0, "offset": [0.0, 0.0, 0.0],
                                "radius": 0.35, "stepHeight": 0.3},
        "luaScript": {"enabled": True, "scriptPath": "components/FreeLook.lua"},
        "transform": {"position": [sp[0], 1.7, sp[1]], "rotation": [0.0, sp[2], 0.0],
                      "scale": [1.0, 1.0, 1.0]},
    })

    logic = marker("Logic_" + st["tag"], (0.0, 0.0, 0.0), 0.0, g_sys)
    logic["luaScript"] = {"enabled": True, "scriptPath": "components/Junction.lua"}
    ents.append(logic)

    return {
        "version": 1,
        "entities": ents,
        "shadows": True,
        "skybox": {"drawSkybox": False, "envMapPath": "", "iblIntensity": 0.0,
                   "skyboxIntensity": 0.0},
        "ssao": {"bias": 0.025, "blur": True, "enabled": True, "intensity": 1.0,
                 "power": 1.7, "radius": 0.7, "sampleCount": 16},
        "postProcess": {
            "enabled": True, "tonemapper": 1,
            "exposureOn": True, "exposure": 1.0,
            "bloomOn": True, "bloom": 0.42, "bloomThreshold": 1.15,
            "bloomKnee": 0.5, "bloomRadius": 0.72,
            "vignetteOn": True, "vignette": 0.26,
            "caOn": True, "ca": 0.15,
            "grainOn": True, "grain": 0.045,
            "fxaaOn": True, "debandOn": True,
        },
    }


# ================================ ステージ定義 ================================
# 部屋は 40m 以上離す。1 マス = 52m にしてある。
def P(i):
    return i * 52.0

BENCH = [("bench", -4.2, 3.4, 12.0), ("vent", 0.0, -5.98, 0.0)]
COL2  = [("column", -3.4, -3.4, 0.0), ("column", 3.4, 3.4, 0.0)]
VENT  = [("vent", 5.98, 0.0, 270.0)]

STAGES = [
    # ---- 1: 触れる・つなぐ・通る。予算 1・候補 1 枚 = 失敗しようがない ----
    dict(name="stage1", tag="Stage_1", title=1,
         rooms=[("S", P(0), P(0), {"N": "a"}, BENCH),
                ("G", P(0), P(1), {"S": "g"}, VENT)],
         spawn=(0.0, -3.5, 0.0), goal=(P(0), P(1) + 2.6),
         doors=["a", "g"], room_of=dict(a="S", g="G"),
         budget=1, start="S", goalRoom="G", timed=False, teach="connect"),

    # ---- 2: 合流3枚と角度。左右のレーンで行き先が変わることを体で教える ----
    #        ★教える面なので色は【最も遠い 2 色】(青と黄)を使う。橙と黄は
    #          白い虚無の中では同じ色に見えて、授業にならなかった。
    dict(name="stage2", tag="Stage_2", title=2,
         rooms=[("S", P(0), P(0), {"N": "a"}, BENCH),
                ("A", P(-1), P(1), {"S": "d"}, COL2),
                ("G", P(1), P(1), {"S": "g"}, VENT)],
         spawn=(0.0, -3.5, 0.0), goal=(P(1), P(1) + 2.6),
         doors=["a", "d", "g"], room_of=dict(a="S", d="A", g="G"),
         budget=3, start="S", goalRoom="G", timed=False, teach="angle"),

    # ---- 3: 合流(既存)。ここから時間制限が入る ----
    dict(name="stage3", tag="Stage_3", title=3,
         rooms=[("S", P(0), P(0), {"N": "a"}, VENT),
                ("A", P(0), P(1), {"S": "b"}, COL2),
                ("G", P(1), P(1), {"S": "g"}, ())],
         spawn=(0.0, -3.5, 0.0), goal=(P(1), P(1) + 2.6),
         doors=["a", "b", "g"], room_of=dict(a="S", b="A", g="G"),
         budget=3, start="S", goalRoom="G"),

    # ---- 4: 二つの出口(GDD で開示した面)。ドア c は触ると詰む罠 ----
    dict(name="stage4", tag="Stage_4", title=4,
         rooms=[("S", P(0), P(0), {"N": "a"}, ()),
                ("P", P(0), P(1), {"S": "b"}, COL2),
                ("Q", P(1), P(0), {"S": "c"}, ()),
                ("G", P(1), P(1), {"S": "d"}, VENT)],
         spawn=(0.0, -3.5, 0.0), goal=(P(1), P(1) + 2.6),
         doors=["a", "b", "c", "d"], room_of=dict(a="S", b="P", c="Q", d="G"),
         budget=2, start="S", goalRoom="G"),

    # ---- 5: 遠近の罠。虚無に浮かぶ大きさは実距離で決まる ----
    #        近くの d と ずっと遠くの g が同じくらいの見かけになるよう配置してある
    dict(name="stage5", tag="Stage_5", title=5,
         rooms=[("S", P(0), P(0), {"N": "a"}, ()),
                ("P", P(0), P(1), {"S": "b"}, ()),
                ("Q", P(1), P(1), {"S": "c"}, COL2),
                ("R", P(1), P(0), {"S": "d"}, ()),
                ("G", P(4), P(3), {"S": "g"}, VENT)],
         spawn=(0.0, -3.5, 0.0), goal=(P(4), P(3) + 2.6),
         doors=["a", "b", "c", "d", "g"], room_of=dict(a="S", b="P", c="Q", d="R", g="G"),
         budget=3, start="S", goalRoom="G"),

    # ---- 6: 四枚合流。40度スライス = 助走の設計が要る ----
    dict(name="stage6", tag="Stage_6", title=6,
         rooms=[("S", P(0), P(0), {"N": "a"}, ()),
                ("P", P(0), P(1), {"S": "b"}, ()),
                ("Q", P(1), P(1), {"S": "c"}, ()),
                ("R", P(1), P(0), {"S": "d"}, COL2),
                ("G", P(2), P(1), {"S": "g"}, VENT)],
         spawn=(0.0, -3.5, 0.0), goal=(P(2), P(1) + 2.6),
         doors=["a", "b", "c", "d", "g"], room_of=dict(a="S", b="P", c="Q", d="R", g="G"),
         budget=4, start="S", goalRoom="G"),

    # ---- 7: 精密射撃。5枚合流 = 30度スライス。部屋 T は 2 枚ドアの中継 ----
    dict(name="stage7", tag="Stage_7", title=7,
         rooms=[("S", P(0), P(0), {"N": "a"}, ()),
                ("T", P(0), P(1), {"S": "b", "E": "e"}, COL2),
                ("P", P(1), P(1), {"S": "c"}, ()),
                ("Q", P(1), P(0), {"S": "d"}, ()),
                ("U", P(2), P(0), {"N": "f"}, ()),
                ("G", P(2), P(1), {"S": "g"}, VENT)],
         spawn=(0.0, -3.5, 0.0), goal=(P(2), P(1) + 2.6),
         doors=["a", "b", "c", "d", "e", "f", "g"],
         room_of=dict(a="S", b="T", c="P", d="Q", e="T", f="U", g="G"),
         budget=4, start="S", goalRoom="G"),

    # ---- 8: 一棟。ドア 8 枚・予算 3。合流点の崩壊(6枚目)が初めて起こり得る ----
    dict(name="stage8", tag="Stage_8", title=8,
         rooms=[("S", P(0), P(0), {"N": "a", "E": "h"}, ()),
                ("T", P(0), P(1), {"S": "b"}, ()),
                ("P", P(1), P(1), {"S": "c", "E": "e"}, ()),
                ("Q", P(1), P(0), {"S": "d"}, ()),
                ("U", P(2), P(1), {"S": "f"}, COL2),
                ("G", P(3), P(2), {"S": "g"}, VENT)],
         spawn=(0.0, -3.5, 0.0), goal=(P(3), P(2) + 2.6),
         doors=["a", "b", "c", "d", "e", "f", "g", "h"],
         room_of=dict(a="S", b="T", c="P", d="Q", e="P", f="U", g="G", h="S"),
         budget=3, start="S", goalRoom="G",
         lightcol=(1.0, 0.93, 0.74), intensity=6.2),
]


if __name__ == "__main__":
    for st in STAGES:
        d = scene(st)
        p = os.path.normpath(os.path.join(OUT, st["name"] + ".json"))
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print("wrote", p, len(d["entities"]), "entities")

    # ★ステージ表は Junction.lua の中の印で囲まれた範囲へ差し込む。
    #   エンジンの Lua に require/dofile が無いので別ファイルに切り出せない。
    #   二重管理を避けるため、正はここ(STAGES)だけ。Lua 側は手で編集しない。
    lua = []
    for i, st in enumerate(STAGES):
        nxt = STAGES[i + 1]["name"] if i + 1 < len(STAGES) else ""
        lua.append('    ["Logic_%s"] = { n = %d, scene = "scenes/%s.json", next = %s,'
                   % (st["tag"], st["title"], st["name"],
                      ('"scenes/%s.json"' % nxt) if nxt else "nil"))
        lua.append('        doors = { %s },'
                   % ", ".join('"%s"' % d for d in st["doors"]))
        lua.append('        room = { %s },'
                   % ", ".join('%s = "%s"' % (k, v) for k, v in sorted(st["room_of"].items())))
        lua.append('        budget = %d, start = "%s", goalRoom = "%s",'
                   % (st["budget"], st["start"], st["goalRoom"]))
        lua.append('        spawn = { %.1f, 1.7, %.1f, %.1f }, timed = %s, teach = %s },'
                   % (st["spawn"][0], st["spawn"][1], st["spawn"][2],
                      "true" if st.get("timed", True) else "false",
                      ('"%s"' % st["teach"]) if st.get("teach") else "nil"))
    lp = os.path.normpath(os.path.join(OUT, "..", "components", "Junction.lua"))
    src = open(lp, encoding="utf-8").read()
    A, B = "-- >>>STAGES", "-- <<<STAGES"
    ia, ib = src.index(A), src.index(B)
    src = src[:ia] + A + " (source/gen_stages.py が自動生成)\n" + "\n".join(lua) + "\n    " + src[ib:]
    open(lp, "w", encoding="utf-8").write(src)
    print("patched", lp, len(STAGES), "stages")
