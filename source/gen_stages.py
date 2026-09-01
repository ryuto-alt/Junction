# -*- coding: utf-8 -*-
"""JUNCTION / 継ぎ目 のステージを生成する。
シーン JSON はここが唯一の正。エディタで手で足した物は次の実行で消える。

★部屋は「同じ顔をした閉じた箱」。互いに 40m 以上離して置き、外からは見えない。
  ドアの向こうは常に白い虚無(Void_<id> の白板)で、繋がっていても物理的には
  通り抜けられない。通過は Junction.lua がテレポートで行う(=ポータル描画は不要)。

★ドアの向き: transform.rotation.y は「forward が部屋の内側を向く」ように置く。
  forward = (sin(yaw), 0, cos(yaw))。Junction.lua はこの規約に依存している。
"""
import json, math, random, os

random.seed(20260901)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "scenes")

HALF   = 6.0    # 部屋の内寸の半分(12m 角)
WALLT  = 0.3    # 壁の厚み
WALLH  = 4.0    # 天井高
DOORW  = 1.5    # ドアの幅
DOORH  = 2.6    # ドアの高さ

C_WALL    = [0.70, 0.71, 0.69]
C_FLOOR   = [0.52, 0.53, 0.51]
C_CEIL    = [0.78, 0.79, 0.77]
C_FRAME   = [0.30, 0.32, 0.29]
C_VOID    = [1.00, 1.00, 1.00]
C_MARK    = [0.06, 0.42, 0.29]
C_SLICE   = [0.10, 0.55, 0.38]
C_GOAL    = [0.10, 0.75, 0.50]

HIDE_Y = -200.0   # 隠す時に飛ばす高さ。scale=0 は退化三角形になるので使わない


def guid():
    return "%016x" % random.getrandbits(64)


def box(name, pos, scale, color, rot=(0, 0, 0), collide=True, rough=0.92):
    e = {
        "guid": guid(), "name": name, "primitive": "box",
        "color": list(color),
        "material": {"metallic": 0.0, "roughness": rough},
        "transform": {"position": [float(pos[0]), float(pos[1]), float(pos[2])],
                      "rotation": [float(rot[0]), float(rot[1]), float(rot[2])],
                      "scale": [float(scale[0]), float(scale[1]), float(scale[2])]},
    }
    if collide:
        e["boxCollider"] = {"halfExtents": [0.5, 0.5, 0.5], "offset": [0.0, 0.0, 0.0]}
        e["rigidBody"] = {"angularDamping": 0.01, "continuousCollision": False,
                          "friction": 0.6, "linearDamping": 0.02, "mass": 1.0,
                          "motionType": 0, "restitution": 0.0, "useGravity": False}
    return e


def plight(name, pos, color, intensity, rng):
    return {"guid": guid(), "name": name,
            "pointLight": {"castShadows": False, "color": list(color),
                           "intensity": float(intensity), "range": float(rng)},
            "transform": {"position": [float(pos[0]), float(pos[1]), float(pos[2])],
                          "rotation": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0]}}


def marker(name, pos, yaw=0.0):
    """当たり判定も見た目も持たない印。Junction.lua が transform だけを読む。"""
    return {"guid": guid(), "name": name,
            "transform": {"position": [float(pos[0]), float(pos[1]), float(pos[2])],
                          "rotation": [0.0, float(yaw), 0.0], "scale": [1.0, 1.0, 1.0]}}


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


def door_entities(ents, did, wc, info):
    """ドア 1 枚ぶんの実体一式。名前の規約は Junction.lua と対。"""
    yaw = info["yaw"]
    dx, dz = wc[0], wc[2]
    ix, iz = inward(yaw)

    ents.append(marker("Door_%s" % did, (dx, 0.0, dz), yaw))

    # 虚無の白板。常に塞がっている(通過はテレポート)
    if info["axis"] == "z":
        sc = (DOORW, DOORH, 0.10)
    else:
        sc = (0.10, DOORH, DOORW)
    ents.append(box("Void_%s" % did, (dx, DOORH * 0.5, dz), sc, C_VOID, rough=1.0))

    # 白板を白飛びさせる灯り。inward 側へ少し出す
    ents.append(plight("VoidLight_%s" % did, (dx + ix * 0.55, 1.35, dz + iz * 0.55),
                       (1.0, 1.0, 1.0), 5.2, 3.2))

    # 枠(ドアだと分かる縁取り)
    fw = 0.14
    for s in (-1, +1):
        if info["axis"] == "z":
            p = (dx + s * (DOORW * 0.5 + fw * 0.5), DOORH * 0.5, dz + iz * 0.18)
            sc2 = (fw, DOORH + fw, 0.16)
        else:
            p = (dx + ix * 0.18, DOORH * 0.5, dz + s * (DOORW * 0.5 + fw * 0.5))
            sc2 = (0.16, DOORH + fw, fw)
        ents.append(box("Frame_%s_%d" % (did, s), p, sc2, C_FRAME, collide=False))

    # 合流点の刻印 Ⅰ/Ⅱ/Ⅲ… 枠の上。既定は隠す
    for k in range(1, 6):
        ents.append(box("Mark_%s_%d" % (did, k), (dx, HIDE_Y, dz), (0.10, 0.26, 0.06),
                        C_MARK, collide=False))

    # 角度の分割線(床のデカール代わりの細い板)。既定は隠す
    for k in range(1, 7):
        ents.append(box("Slice_%s_%d" % (did, k), (dx, HIDE_Y, dz), (0.06, 0.02, 1.0),
                        C_SLICE, collide=False))


def room(ents, rid, cx, cz, doors, lightcol=(0.94, 0.96, 1.0)):
    """doors: {"N": "a", ...} 壁 -> ドア id。"""
    span = HALF * 2 + WALLT
    ents.append(box("%s_Floor" % rid, (cx, -0.15, cz), (span, 0.3, span), C_FLOOR, rough=0.95))
    ents.append(box("%s_Ceil" % rid, (cx, WALLH + 0.15, cz), (span, 0.3, span), C_CEIL))

    for w in ("N", "S", "E", "W"):
        info = WALLS[w]
        off = HALF + WALLT * 0.5
        if info["axis"] == "z":
            wc = (cx, WALLH * 0.5, cz + info["sign"] * off)
            full = (span, WALLH, WALLT)
        else:
            wc = (cx + info["sign"] * off, WALLH * 0.5, cz)
            full = (WALLT, WALLH, span)

        did = doors.get(w)
        if did is None:
            ents.append(box("%s_Wall_%s" % (rid, w), wc, full, C_WALL))
            continue

        # 開口を挟む 2 枚 + まぐさ
        segw = (span - DOORW) * 0.5
        segc = (DOORW + segw) * 0.5
        for s in (-1, +1):
            if info["axis"] == "z":
                p = (wc[0] + s * segc, wc[1], wc[2])
                sc = (segw, WALLH, WALLT)
            else:
                p = (wc[0], wc[1], wc[2] + s * segc)
                sc = (WALLT, WALLH, segw)
            tagname = "%s_Wall_%s_%s" % (rid, w, "n" if s < 0 else "p")
            ents.append(box(tagname, p, sc, C_WALL))
        lin_h = WALLH - DOORH
        if info["axis"] == "z":
            p = (wc[0], DOORH + lin_h * 0.5, wc[2])
            sc = (DOORW, lin_h, WALLT)
        else:
            p = (wc[0], DOORH + lin_h * 0.5, wc[2])
            sc = (WALLT, lin_h, DOORW)
        ents.append(box("%s_Lintel_%s" % (rid, w), p, sc, C_WALL))

        door_entities(ents, did, wc, info)

    # 照明(蛍光灯 2 本ぶん)
    for i, dz2 in enumerate((-2.6, 2.6)):
        ents.append(plight("%s_Light_%d" % (rid, i), (cx, WALLH - 0.5, cz + dz2),
                           lightcol, 3.1, 13.0))


def scene(rooms, stage_tag, spawn, goal_pos):
    ents = []
    ents.append({"guid": guid(), "name": "Ambient",
                 "directionalLight": {"ambient": 0.045, "color": [0.80, 0.85, 1.0],
                                      "direction": [-0.3, -0.9, -0.3], "intensity": 0.0},
                 "transform": {"position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0],
                               "scale": [1.0, 1.0, 1.0]}})

    for rid, cx, cz, doors in rooms:
        room(ents, rid, cx, cz, doors)

    # 出口の目印
    ents.append(box("Goal", (goal_pos[0], 1.1, goal_pos[1]), (0.9, 2.2, 0.9), C_GOAL,
                    collide=False, rough=0.35))
    ents.append(plight("GoalLight", (goal_pos[0], 2.4, goal_pos[1]), (0.25, 1.0, 0.62), 4.5, 9.0))

    # 虚無に浮かぶドアの候補(接続モードで使い回す)。既定は隠す
    for i in range(1, 9):
        ents.append(box("Proxy_%d" % i, (0.0, HIDE_Y, 0.0), (0.9, 1.7, 0.08),
                        C_VOID, collide=False, rough=1.0))

    # プレイヤー
    ents.append({
        "guid": guid(), "name": "MainCamera",
        "camera": {"farClip": 300.0, "fovDegrees": 74.0, "isActive": True,
                   "nearClip": 0.06, "orthoSize": 10.0, "projection": 0},
        "characterController": {"gravityScale": 1.0, "halfHeight": 1.3, "jumpSpeed": 6.0,
                                "mass": 70.0, "maxSlopeDeg": 50.0, "offset": [0.0, 0.0, 0.0],
                                "radius": 0.35, "stepHeight": 0.3},
        "luaScript": {"enabled": True, "scriptPath": "components/FreeLook.lua"},
        "transform": {"position": [spawn[0], 1.7, spawn[1]], "rotation": [0.0, spawn[2], 0.0],
                      "scale": [1.0, 1.0, 1.0]},
    })

    # ゲームロジック。ステージ設定は名前(Logic_Stage_N)で引く
    logic = marker("Logic_" + stage_tag, (0.0, 0.0, 0.0))
    logic["luaScript"] = {"enabled": True, "scriptPath": "components/Junction.lua"}
    ents.append(logic)

    return {
        "version": 1,
        "entities": ents,
        "shadows": True,
        "skybox": {"drawSkybox": False, "envMapPath": "", "iblIntensity": 0.0,
                   "skyboxIntensity": 0.0},
        "ssao": {"bias": 0.025, "blur": True, "enabled": True, "intensity": 0.9,
                 "power": 1.6, "radius": 0.6, "sampleCount": 16},
        "postProcess": {
            "enabled": True, "tonemapper": 1,
            "exposureOn": True, "exposure": 1.0,
            "bloomOn": True, "bloom": 0.55, "bloomThreshold": 1.05,
            "bloomKnee": 0.5, "bloomRadius": 0.72,
            "vignetteOn": True, "vignette": 0.22,
            "fxaaOn": True, "debandOn": True,
            "saturationOn": True, "saturation": 0.78,
        },
    }


# ================================ ステージ定義 ================================
# 第3面「合流」: 3 枚合流と角度を教える。予算 3(1 本余る)
STAGE3 = dict(
    tag="Stage_3",
    rooms=[("S", 0.0, 0.0, {"N": "a"}),
           ("A", 0.0, 44.0, {"S": "b"}),
           ("G", 52.0, 44.0, {"S": "g"})],
    spawn=(0.0, -3.5, 0.0), goal=(52.0, 46.5),
)
# 第4面「二つの出口」: GDD で開示した面。予算 2、ドア 4 枚、c は罠
STAGE4 = dict(
    tag="Stage_4",
    rooms=[("S", 0.0, 0.0, {"N": "a"}),
           ("P", 0.0, 44.0, {"S": "b"}),
           ("Q", 52.0, 0.0, {"S": "c"}),
           ("G", 52.0, 44.0, {"S": "d"})],
    spawn=(0.0, -3.5, 0.0), goal=(52.0, 46.5),
)

if __name__ == "__main__":
    for name, st in (("stage3", STAGE3), ("stage4", STAGE4)):
        d = scene(st["rooms"], st["tag"], st["spawn"], st["goal"])
        p = os.path.normpath(os.path.join(OUT, name + ".json"))
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print("wrote", p, len(d["entities"]), "entities")
