# -*- coding: utf-8 -*-
"""JUNCTION / 継ぎ目 のステージを生成する。
シーン JSON はここが唯一の正。エディタで手で足した物は次の実行で消える。

実行(numpy は要らないので素の python でもよい):
  "C:/Program Files/Blender Foundation/Blender 5.1/5.1/python/bin/python.exe" gen_stages.py

★部屋は「閉じた箱」。互いに 52m 離して置き、外からは見えない。
  ドアの向こうは常に白い虚無(Void_<id> の白板)で、繋がっていても物理的には
  通り抜けられない。通過は Junction.lua がテレポートで行う(=ポータル描画は不要)。
  ★例外は第1面だけ。S と G を【隣接】させ、窓越しに出口が見えるようにしてある。
    「見た目の先」と「繋いだ先」は別物、というこのゲームの前提を最初の 30 秒で渡す。

★ドアの向き: transform.rotation.y は「forward が部屋の内側を向く」ように置く。
  forward = (sin(yaw), 0, cos(yaw))。Junction.lua はこの規約に依存している。

★2026-09-01(4) 作り直し:
  1. 部屋の形を寸法パラメータ化した(SHAPES)。8 面すべてが 12m 角の同じ箱だったのが
     「新しい事を足しても画面が同じなので新しく見えない」の直接の原因(docs/REDESIGN.md)。
  2. 湧き位置・ドアの壁・開幕カメラを面ごとに変えた。
  3. カメラ(cine)は【部屋ローカル座標】で書き、ここでワールドへ直して Junction.lua へ
     流し込む。刺さるカメラは assert で落とす(下の check_cine)。
  4. Mark_/Slice_/Lane_/Post_ の生成をやめた。
  5. ★Preload グループ。エンジンは【シーンを開いた時点で読み込まれていないモデルは
     scene:spawn しても描画しない】(entity は valid、MeshRenderer も付く、AABB も正しい、
     Lua もエラーを出さない。ただ出ない)。Lua が実行時に出す扇・針・ピンを出すには、
     シーン JSON がそのモデルを 1 個は参照している必要がある。床下 y=-200 のダミーがそれ。
     ★これを消すと帯もレーンもピンも【無言で】出なくなる。

★2026-09-01(5) 「角度」から「通った場所」へ(docs/GATE.md):
  6. DOORW 1.5 -> 2.0。開口を行き先の数だけ縦の帯に割るので、袖壁・まぐさ・Void_・
     Frame_ の見た目と当たり判定を全部追従させた(定数 1 個から出ている)。
  7. Preload を wedge*/needle から band/lane/pin へ差し替えた。モデルはもう存在しない。
  8. 第2面の 4m 仕切り(divider)を捨て、ドアの正面だけを塞ぐ衝立(blocker)にした。
     仕切りはドアの中心線上に立っていて【真ん中しか通れない】形だった。
  9. check_lanes / check_blockers を足した。レーンの上に什器が刺さる配置と、
     体が回り込めない衝立を【コミットできないようにする】。

★階層: エンティティは [Rooms]/[Doors]/[System] の下にグループ分けしてある。
  グループ node は原点・無回転・スケール1なので、子の transform は world と一致する。
  ★MainCamera だけは親を付けない。CharacterController は world 座標で駆動され、
    PhysicsSystem が transform へ world を書き戻すので、親を持つと二重変換で壊れる。

★寸法は source/blender_kit.py の FOOTPRINTS / WALLT / DOORW / DOORH / WIN* と
  【必ず一致】させること。片方だけ変えると壁がずれて隙間が空く。
"""
import json, math, random, os

random.seed(20260901)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "scenes")

WALLT  = 0.3    # 壁の厚み
DOORW  = 2.0    # ★ドアの開口幅(全形共通)。1.5 -> 2.0 に拡張した(docs/GATE.md)。
                #   開口を行き先の数だけ縦の帯に割るので、4 出口でも 1 帯 0.5m 要る
                #   (1.5 だと 0.375m でプレイヤー直径 0.7m に対して狙いが厳しすぎた)。
                #   ★blender_kit.py の DOORW と【必ず一致】。片方だけ直すと
                #   「見た目は開いているのに見えない壁がある」「壁の中を歩ける」になる。
                #   袖壁 segw / まぐさ / Void_ / Frame_ は全部この定数から出ている。
DOORH  = 2.6    # ドアの開口高(全形共通)
WINW   = 6.0    # 窓の開口幅
WINY0  = 1.0    # 窓の下端。★腰壁が 1.0m 残るので stepHeight 0.3 では乗り越えられない
WINY1  = 3.0    # 窓の上端

# ---- 部屋の形。blender_kit.py の FOOTPRINTS と対 ----
#   ix,iz = 内寸 / h = 天井高 / wh = 壁モデルの高さ(cell8 だけ天井より 0.2 高い)
#   ns/ew = その向きの壁モデル(ns = X 方向へ伸びる壁 = 北と南)
#   lights = 天井灯の (x,z)。★2 灯だと 12m 角の隅まで届かず天井が灰色に沈む
#            (= リミナルに見えない)。実物の office と同じく面で光らせる。
SHAPES = {
    "box12": dict(
        ix=12.0, iz=12.0, h=4.0, wh=4.0,
        floor="models/floor.gltf", ceil="models/ceiling.gltf",
        ns=("models/wall.gltf", "models/wall_door.gltf"),
        ew=("models/wall.gltf", "models/wall_door.gltf"),
        win="models/wall_window.gltf",
        lights=[(-3.1, -3.1), (3.1, -3.1), (-3.1, 3.1), (3.1, 3.1)], lrange=16.0),
    "hall20": dict(
        ix=20.0, iz=20.0, h=7.0, wh=7.0,
        floor="models/floor20.gltf", ceil="models/ceiling20.gltf",
        ns=("models/wall20.gltf", "models/wall20_door.gltf"),
        ew=("models/wall20.gltf", "models/wall20_door.gltf"),
        win=None,
        lights=[(x, z) for z in (-6.4, 0.0, 6.4) for x in (-6.4, 0.0, 6.4)], lrange=22.0),
    "corr18": dict(
        ix=18.0, iz=8.0, h=3.2, wh=3.2,
        floor="models/floor18x8.gltf", ceil="models/ceiling18x8.gltf",
        ns=("models/wall18.gltf", "models/wall18_door.gltf"),
        ew=("models/wall8.gltf", "models/wall8_door.gltf"),
        win=None,
        lights=[(-6.0, 0.0), (0.0, 0.0), (6.0, 0.0)], lrange=15.0),
    "cell8": dict(
        ix=8.0, iz=8.0, h=3.0, wh=3.2,
        floor="models/floor8.gltf", ceil="models/ceiling8.gltf",
        ns=("models/wall8.gltf", "models/wall8_door.gltf"),
        ew=("models/wall8.gltf", "models/wall8_door.gltf"),
        win=None,
        lights=[(0.0, 0.0)], lrange=12.0),
}

# 箱はモデルの裏に隠れるが、開口の縁から覗くことがあるので近い色にしておく
C_WALL    = [0.62, 0.60, 0.55]
C_FLOOR   = [0.24, 0.20, 0.12]
C_CEIL    = [0.72, 0.72, 0.70]
C_VOID    = [1.00, 1.00, 1.00]
C_GOAL    = [0.10, 0.75, 0.50]
C_DIV     = [0.55, 0.56, 0.54]   # 仕切りの当たり判定(モデルの中に完全に隠れる)

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

# ★Lua が実行時に scene:spawn するモデル。シーンが 1 個も参照していないと
#   「spawn は成功するのに描画されない」に化ける(冒頭の注記)。床下に置いて先読みさせる。
PRELOAD = [
    ("Preload_Band", "models/band.gltf"),
    ("Preload_Lane", "models/lane.gltf"),
    ("Preload_Pin",  "models/pin.gltf"),
]


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
    """ドア 1 枚ぶんの実体一式。名前の規約は Junction.lua と対。
    ★Mark_/Slice_/Lane_/Post_ は廃止した。開口の帯 Band_<id>_<k> と床のレーン
      Lane_<id>_<k> は Junction.lua が実行時に spawn する(Preload のダミーが要る)。"""
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


# ---------------------------------------------------------------- 部屋の中の物
# (種類, モデル, 置く高さ, 判定用の半径, 判定用の天端)
#   半径と天端は「カメラが刺さらないか」の assert(check_cine)にだけ使う。
#   天井に付く物(vent/pipes)は下を通っても遮らないので候補から外す(block=False)。
PROPS = {
    "bench":   dict(path="models/bench.gltf",   y=0.0, r=0.90, top=0.95, block=True),
    "column":  dict(path="models/column.gltf",  y=0.0, r=0.45, top=99.0, block=True),
    "locker":  dict(path="models/locker.gltf",  y=0.0, r=0.85, top=1.95, block=True),
    "crate":   dict(path="models/crate.gltf",   y=0.0, r=0.55, top=0.75, block=True),
    "railing": dict(path="models/railing.gltf", y=0.0, r=1.55, top=1.10, block=True),
    "vent":    dict(path="models/vent.gltf",    y=None, r=0.4, top=0.0, block=False),
    "pipes":   dict(path="models/pipes.gltf",   y=None, r=3.0, top=0.0, block=False),
}


def props(ents, rid, cx, cz, ch, spec, parent, fixtures):
    """spec: [(種類, x, z, yaw), ...] 部屋ローカル座標。部屋の識別性を上げる小物。
    ★どれも当たり判定を持たない(通り抜ける)。行き先の判断を邪魔しないため。
      当たり判定を持つのは衝立(blocker)だけ = 通り抜けられたら意味が無いから。"""
    for i, (kind, lx, lz, yaw) in enumerate(spec):
        P = PROPS[kind]
        y = P["y"]
        if y is None:                       # 天井/壁付け。低い部屋でも埋まらないように下げる
            y = min(2.6, ch - 0.6) if kind == "vent" else ch - 0.01
        sc = (1.0, 1.0, 1.0)
        if kind == "column":                # 柱は 4m 固定なので天井の高い部屋では伸ばす
            sc = (1.0, ch / 4.0, 1.0)
        ents.append(model("%s_%s_%d" % (rid, kind, i), P["path"],
                          (cx + lx, y, cz + lz), yaw, parent, sc))
        if P["block"]:
            top = P["top"] if P["top"] < 90.0 else ch
            fixtures.setdefault(rid, []).append((cx + lx, cz + lz, P["r"], top))


BLK_LEN, BLK_H, BLK_T = 1.2, 1.15, 0.14   # blocker.gltf の実寸(長さは X 方向、面は ±Z)


def blockers(ents, rid, cx, cz, spec, parent, fixtures):
    """衝立。ドアの【正面だけ】を塞ぐ短い板(spec: [(x, z, yaw), ...] 部屋ローカル)。

    ★(4) までは 4m の仕切り divider をドアの中心線上に立てていた。あれは
      「塞ぐべき中央を開け、開けるべき左右を塞ぐ」の真逆で、ドアの手前 1.15m が
      袋小路になり横歩きでしか入れず、入れても 2 つの帯のちょうど境目にしか立てなかった。
      衝立は開口(2.0)より狭い 1.2 なので、左右に体(直径 0.7)が回り込む隙間が必ず残る。
      真っ直ぐは入れないので【どちらの帯を通るかを必ず選ぶ】ことになる。

    ★これだけは【当たり判定を持たせる】。他の什器と違い、通り抜けられたら
      幾何の強制そのものが成立しない。判定箱は板の中に完全に隠す。"""
    for i, (lx, lz, yaw) in enumerate(spec):
        ents.append(model("%s_Blocker_%d" % (rid, i), "models/blocker.gltf",
                          (cx + lx, 0.0, cz + lz), yaw, parent))
        # yaw 0 で長さ方向が X、90 で Z。斜めには置かない(判定箱が板からはみ出す)
        along_x = abs(math.cos(math.radians(yaw))) > 0.5
        sx = BLK_LEN if along_x else BLK_T
        sz = BLK_T if along_x else BLK_LEN
        ents.append(box("%s_BlockerCol_%d" % (rid, i),
                        (cx + lx, BLK_H * 0.5 - 0.03, cz + lz),
                        (sx - 0.03, BLK_H - 0.06, sz - 0.03), C_DIV, rough=0.6,
                        parent=parent))
        fixtures.setdefault(rid, []).append((cx + lx, cz + lz, BLK_LEN * 0.5, BLK_H))


# ---------------------------------------------------------------- 部屋
def room(ents, r, doors_parent, rooms_parent, lightcol, intensity, dimhalf, fixtures):
    rid, shape = r["id"], r["shape"]
    cx, cz = r["at"]
    S = SHAPES[shape]
    hx, hz, ch, wh = S["ix"] * 0.5, S["iz"] * 0.5, S["h"], S["wh"]
    spanx, spanz = S["ix"] + WALLT, S["iz"] + WALLT
    doors = r.get("doors", {})
    wins = r.get("win", ())

    g = group(ents, "Room %s" % rid, rooms_parent)

    # ---- 当たり判定の箱(内装モデルの裏に隠れる) ----
    ents.append(box("%s_Floor" % rid, (cx, -0.15, cz), (spanx, 0.3, spanz), C_FLOOR,
                    rough=0.95, parent=g))
    ents.append(box("%s_Ceil" % rid, (cx, ch + 0.15, cz), (spanx, 0.3, spanz), C_CEIL,
                    parent=g))
    # ---- 内装モデル(箱の 5mm 内側) ----
    ents.append(model("%s_FloorM" % rid, S["floor"], (cx, 0.005, cz), 0.0, g))
    ents.append(model("%s_CeilM" % rid, S["ceil"], (cx, ch - 0.005, cz), 0.0, g))

    for w in ("N", "S", "E", "W"):
        info = WALLS[w]
        if info["axis"] == "z":
            L = spanx
            wc = (cx, wh * 0.5, cz + info["sign"] * (hz + WALLT * 0.5))
            full = (L, wh, WALLT)
            mp = (cx, 0.0, cz + info["sign"] * (hz - 0.005))
            mdl = S["ns"]
        else:
            L = spanz
            wc = (cx + info["sign"] * (hx + WALLT * 0.5), wh * 0.5, cz)
            full = (WALLT, wh, L)
            mp = (cx + info["sign"] * (hx - 0.005), 0.0, cz)
            mdl = S["ew"]

        did = doors.get(w)
        isw = (w in wins)
        if isw and not S["win"]:
            raise SystemExit("%s: %s には窓の壁モデルが無い" % (rid, shape))
        if did and isw:
            raise SystemExit("%s: 壁 %s にドアと窓の両方は置けない" % (rid, w))

        path = S["win"] if isw else (mdl[1] if did else mdl[0])
        ents.append(model("%s_WallM_%s" % (rid, w), path, mp, info["yaw"], g))

        if did is None and not isw:
            ents.append(box("%s_Wall_%s" % (rid, w), wc, full, C_WALL, parent=g))
            continue

        # ---- 開口のある壁。左右の袖 + まぐさ(+ 窓なら腰壁) ----
        ow = WINW if isw else DOORW
        y0 = WINY0 if isw else 0.0
        y1 = WINY1 if isw else DOORH
        segw = (L - ow) * 0.5
        segc = (ow + segw) * 0.5
        for s in (-1, +1):
            if info["axis"] == "z":
                p = (wc[0] + s * segc, wc[1], wc[2]); sc = (segw, wh, WALLT)
            else:
                p = (wc[0], wc[1], wc[2] + s * segc); sc = (WALLT, wh, segw)
            tag = "%s_Wall_%s_%s" % (rid, w, "n" if s < 0 else "p")
            ents.append(box(tag, p, sc, C_WALL, parent=g))
        # まぐさ(開口の上)
        lh = wh - y1
        if lh > 0.01:
            sc = (ow, lh, WALLT) if info["axis"] == "z" else (WALLT, lh, ow)
            ents.append(box("%s_Lintel_%s" % (rid, w), (wc[0], y1 + lh * 0.5, wc[2]),
                            sc, C_WALL, parent=g))
        # ★腰壁(窓の下)。高さ 1.0m が残るので stepHeight 0.3 では越えられない。
        #   「出口が見えているのに歩いては行けない」はこの箱が成立させている。
        if y0 > 0.01:
            sc = (ow, y0, WALLT) if info["axis"] == "z" else (WALLT, y0, ow)
            ents.append(box("%s_Sill_%s" % (rid, w), (wc[0], y0 * 0.5, wc[2]),
                            sc, C_WALL, parent=g))

        if did:
            door_entities(ents, did, wc, info, doors_parent)

    # ---- 埋め込み照明。灯りは器具の少し下に置く(乳白カバーを下から光らせる) ----
    for i, (ox, oz) in enumerate(S["lights"]):
        ents.append(model("%s_Troffer_%d" % (rid, i + 1), "models/troffer.gltf",
                          (cx + ox, ch - 0.01, cz + oz), 0.0, g))
        # ★第7面: 蛍光灯が半分死んでいる。暗さで難しくするのではなく不安にさせるのが目的
        it = intensity * (0.28 if (dimhalf and i % 2 == 1) else 1.0)
        ents.append(plight("%s_Light_%d" % (rid, i + 1), (cx + ox, ch - 0.45, cz + oz),
                           lightcol, it, S["lrange"], g))

    props(ents, rid, cx, cz, ch, r.get("props", ()), g, fixtures)
    blockers(ents, rid, cx, cz, r.get("blocks", ()), g, fixtures)


# ---------------------------------------------------------------- カメラの掟
CAM_MARGIN  = 1.2    # 目が部屋の内側に持つべき余裕
CAM_YMIN    = 0.8
CAM_YTOP    = 0.5    # 天井からこれだけ下
CAM_CLEAR   = 0.9    # 什器の中心から線分までの XZ 距離
CAM_TAIL    = 2.0    # 注視点の手前これだけは見ない(見せたい物そのものは遮蔽ではない)
CAM_HEAD    = 0.3


def check_cine(st, centers, fixtures):
    """★刺さるカメラをコミットできないようにする(docs/LEVELS.md「カメラの掟」)。
    目で見て気づくのでは遅いので、生成時に落とす。
    1) 目が部屋の内側に CAM_MARGIN 以上の余裕を持って入っている
    2) 目の y が CAM_YMIN 以上 / 天井 -CAM_YTOP 以下
    3) 目→注視点の線分の XZ 近傍 CAM_CLEAR に什器の中心が無い
       ★ただし「その点でのカメラの高さが什器の天端より上」なら見下ろしているだけなので許す
         (第2面は仕切りを俯瞰で見せるのが狙い。真上を通るのは遮蔽ではない)。
       ★注視点の手前 CAM_TAIL は見ない。見せたい物そのものを遮蔽扱いにしても意味が無い。
    ★第1面は【窓越しに別の部屋を見る】ので「目と注視点が同じ部屋」を前提にしない。
    """
    for i, (er, e, tr, t, dur) in enumerate(st.get("cine", ())):
        tag = "%s cine[%d]" % (st["name"], i)
        if er not in centers or tr not in centers:
            raise SystemExit("%s: 知らない部屋 %s/%s" % (tag, er, tr))
        S = SHAPES[centers[er][2]]
        hx, hz, ch = S["ix"] * 0.5, S["iz"] * 0.5, S["h"]
        if abs(e[0]) > hx - CAM_MARGIN or abs(e[2]) > hz - CAM_MARGIN:
            raise SystemExit("%s: 目が壁に近すぎる local=(%.1f,%.1f) 内寸半分=(%.1f,%.1f)"
                             % (tag, e[0], e[2], hx, hz))
        if e[1] < CAM_YMIN or e[1] > ch - CAM_YTOP:
            raise SystemExit("%s: 目の高さ %.2f が [%.2f, %.2f] の外"
                             % (tag, e[1], CAM_YMIN, ch - CAM_YTOP))

        ex, ey, ez = centers[er][0] + e[0], e[1], centers[er][1] + e[2]
        tx, ty, tz = centers[tr][0] + t[0], t[1], centers[tr][1] + t[2]
        vx, vz = tx - ex, tz - ez
        seg = math.hypot(vx, vz)
        if seg < 0.5:
            raise SystemExit("%s: 目と注視点が近すぎる" % tag)
        t0 = min(0.9, CAM_HEAD / seg)
        t1 = max(t0, 1.0 - CAM_TAIL / seg)
        for rid in (er, tr):
            for (fx, fz, fr, ftop) in fixtures.get(rid, ()):
                k = ((fx - ex) * vx + (fz - ez) * vz) / (seg * seg)
                k = max(t0, min(t1, k))
                d = math.hypot(ex + vx * k - fx, ez + vz * k - fz)
                if d < CAM_CLEAR + fr and (ey + (ty - ey) * k) < ftop + 0.25:
                    raise SystemExit(
                        "%s: 什器に刺さる room=%s fixture=(%.1f,%.1f) 距離=%.2f"
                        % (tag, rid, fx, fz, d))


# ---------------------------------------------------------------- レーンと衝立の掟
LANE_LEN = 3.5   # Junction.lua の LANE_LEN と対。レーンが開口から手前へ伸びる長さ
RUNUP    = 4.0   # ★助走路。ここに物があるとレーンが読めない(docs/GATE.md)
BODY_R   = 0.35  # プレイヤーの半径(characterController.radius)。直径 0.7


def door_axes(r, w):
    """壁 w のドアの (中心 x, 中心 z, 部屋の内側を向く単位ベクトル)。room() と同じ式。"""
    S = SHAPES[r["shape"]]
    cx, cz = r["at"]
    hx, hz = S["ix"] * 0.5, S["iz"] * 0.5
    info = WALLS[w]
    ix, iz = inward(info["yaw"])
    if info["axis"] == "z":
        return cx, cz + info["sign"] * (hz + WALLT * 0.5), ix, iz
    return cx + info["sign"] * (hx + WALLT * 0.5), cz, ix, iz


def check_lanes(st, pfx):
    """★ドアの手前 RUNUP に什器を置けなくする。
    レーンは開口から手前へ LANE_LEN 伸び、その先も助走路。ここに机や柱が刺さると
    「レーンと帯が地続きに見える」が崩れ、機構そのものが伝わらなくなる。
    目で見て気づくのでは遅いので生成時に落とす(衝立は【意図して】ここに立てるので対象外)。"""
    for r in st["rooms"]:
        for w in r.get("doors", {}):
            dx, dz, ix, iz = door_axes(r, w)
            for (fx, fz, fr, ftop) in pfx.get(r["id"], ()):
                fwd = (fx - dx) * ix + (fz - dz) * iz
                lat = abs(-(fx - dx) * iz + (fz - dz) * ix)
                if -0.5 < fwd <= RUNUP and lat < DOORW * 0.5 + fr:
                    raise SystemExit(
                        "%s: ドア %s%s の助走路に什器 local前方=%.2f 横=%.2f (許容 横>=%.2f)"
                        % (st["name"], r["id"], w, fwd, lat, DOORW * 0.5 + fr))


def check_blockers(st):
    """★衝立の左右に体が通る隙間が残っているかを数える。
    衝立は「正面だけ塞ぐ」物なので、開口より狭くなければならない。ここを満たさない
    衝立は (4) の仕切りと同じ「真ん中しか通れない」失敗の再来になる。"""
    for r in st["rooms"]:
        for (lx, lz, yaw) in r.get("blocks", ()):
            S = SHAPES[r["shape"]]
            hx, hz = S["ix"] * 0.5, S["iz"] * 0.5
            if BLK_LEN >= DOORW:
                raise SystemExit("%s: 衝立(%.2f)が開口(%.2f)より狭くない"
                                 % (st["name"], BLK_LEN, DOORW))
            # 衝立の脇から部屋の壁までの空き。ここが体の直径より広ければ回り込める
            gapL = (lx - BLK_LEN * 0.5) - (-hx)
            gapR = hx - (lx + BLK_LEN * 0.5)
            if min(gapL, gapR) < BODY_R * 2 + 0.2:
                raise SystemExit("%s: 衝立の脇が狭すぎる 左=%.2f 右=%.2f"
                                 % (st["name"], gapL, gapR))
            # 衝立はドアの正面・手前 1.2〜3.0m。近すぎると袋小路、遠いと避けずに済む
            ok = False
            for w, _did in r.get("doors", {}).items():
                dx, dz, ix, iz = door_axes(r, w)
                cx, cz = r["at"]
                fwd = (cx + lx - dx) * ix + (cz + lz - dz) * iz
                lat = abs(-(cx + lx - dx) * iz + (cz + lz - dz) * ix)
                if 1.2 <= fwd <= 3.0 and lat < 0.05:
                    ok = True
            if not ok:
                raise SystemExit("%s: 衝立がドアの正面・手前 1.2〜3.0m に無い" % st["name"])
            if abs(lz) > hz - 1.0:
                raise SystemExit("%s: 衝立が壁に近すぎる" % st["name"])


def cine_world(st, centers):
    """部屋ローカルの cine をワールドへ直し、Lua が食う { ex,ey,ez, tx,ty,tz, dur } にする。
    ★Junction.lua は【最初の 1 手だけ】カット(瞬間移動+白フラッシュ)で、2 手目以降は
      前の手から補間する。部屋をまたぐ手をそのまま書くと 52m の空中散歩になるので、
      目の部屋が変わる手の前に「ほぼ 0 秒の手」を差し込んでカットに化けさせる。
      (Lua を触らずにカットを増やす唯一の手。差し込み位置がここなのは生成物だから。)"""
    out, prev = [], None
    for (er, e, tr, t, dur) in st.get("cine", ()):
        ex, ey, ez = centers[er][0] + e[0], e[1], centers[er][1] + e[2]
        tx, ty, tz = centers[tr][0] + t[0], t[1], centers[tr][1] + t[2]
        if prev is not None and er != prev:
            out.append((ex, ey, ez, tx, ty, tz, 0.02))
        out.append((ex, ey, ez, tx, ty, tz, dur))
        prev = er
    return out


# ---------------------------------------------------------------- シーン
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

    fixtures = {}
    for r in st["rooms"]:
        room(ents, r, g_doors, g_rooms,
             st.get("lightcol", (0.98, 0.96, 0.88)), st.get("intensity", 8.0),
             st.get("dimhalf", False), fixtures)

    # ★Preload。これが無いと扇・針・ピンが【無言で】出ない(冒頭の注記)。
    #   meshRenderer だけ。rigidBody/boxCollider は付けない(床下に判定を撒かない)。
    g_pre = group(ents, "Preload", g_sys)
    for nm, path in PRELOAD:
        ents.append(model(nm, path, (0.0, HIDE_Y, 0.0), 0.0, g_pre))

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
# 部屋は 52m 離す。★第1面の S と G だけは【隣接】(12.6m = 壁の背中合わせ)。
def P(i):
    return i * 52.0


def R(rid, shape, at, doors=None, **kw):
    d = dict(id=rid, shape=shape, at=at, doors=doors or {})
    d.update(kw)
    return d


BENCH  = [("bench", -4.2, 3.4, 12.0), ("vent", 0.0, -5.98, 0.0)]
# ★柱は「ドアの手前の助走路」に置かない。扇が読めなくなると角度の授業が成立しない。
#   その部屋のドアが南壁なら COL2N(北側)、北壁なら COL2S(南側)を使う。
COL2N  = [("column", -3.4, 3.4, 0.0), ("column", 3.4, 3.4, 0.0)]
COL2S  = [("column", -3.4, -3.4, 0.0), ("column", 3.4, -3.4, 0.0)]
VENT   = [("vent", 5.98, 0.0, 270.0)]
# 第6面。半径 8m の円周上。★ドア(南壁)の手前は助走路なので空ける = 南の 2 本は置かない。
#   扇が読めなくなる物を助走路に置いてはいけない(docs/LEVELS.md 第6面)。
COL6   = [("column", x, z, 0.0) for (x, z) in
          ((3.06, 7.39), (-3.06, 7.39), (7.39, 3.06), (-7.39, 3.06),
           (7.39, -3.06), (-7.39, -3.06))]

# 第8面の主室は南(c)と東(e)の 2 枚なので、どちらの助走路にもかからない北西側だけに柱を残す
COL8P  = [("column", x, z, 0.0) for (x, z) in
          ((3.06, 7.39), (-3.06, 7.39), (-7.39, 3.06), (-7.39, -3.06))]

STAGES = [
    # ---- 1: 「ドアは見た目の先ではなく繋いだ先に出る」 ----
    #   S と G を隣接させ、東の窓越しに出口の光柱を見せる。窓の下は腰壁 1.0m で
    #   歩いては行けない。使えるドアは北壁の a だけ、候補は 1 枚 = 失敗しようがない。
    dict(name="stage1", tag="Stage_1", title=1,
         rooms=[R("S", "box12", (0.0, 0.0), {"N": "a"}, win=("E",), props=BENCH),
                R("G", "box12", (12.6, 0.0), {"N": "g"}, win=("W",), props=VENT)],
         spawn=(0.0, -4.2, 0.0), goal=(12.6, 2.6),
         doors=["a", "g"], room_of=dict(a="S", g="G"),
         budget=1, start="S", goalRoom="G", timed=False, teach="connect",
         # 窓越しの寄り。★引きの 1 手だけだと 15m 先の光柱が細すぎて読めなかったので、
         #   窓へ寄る手を足した(撮って見てから直している)。3 手とも S の中 = 補間で繋がる
         cine=[("S", (-3.2, 1.9, -2.2), "G", (0.0, 1.6, 2.6), 1.6),
               ("S", (3.0, 1.75, 0.4), "G", (0.0, 1.7, 2.6), 2.4),
               ("S", (0.0, 1.7, -3.5), "S", (0.0, 1.5, 6.0), 1.8)]),

    # ---- 2: 「入る側で行き先が変わる」を【幾何で強制】する ----
    #   部屋 A の床に腰高の仕切りが立っていて、ドア d へは左か右からしか入れない。
    #   予算 3・制限時間なし = 間違えても歩いて戻ればやり直せる。
    dict(name="stage2", tag="Stage_2", title=2,
         rooms=[R("S", "box12", (P(0), P(0)), {"N": "a"}, props=BENCH),
                R("A", "box12", (P(0), P(1)), {"S": "d"},
                  # ★衝立はドアの正面・手前 2.0m。ドア d は壁の中心なので x=0。
                  #   幅 1.2 < 開口 2.0 なので左右に回り込む隙間が残る(check_blockers)。
                  blocks=[(0.0, -4.15, 0.0)], props=[("bench", 4.4, 4.0, 200.0)]),
                R("G", "box12", (P(1), P(1)), {"S": "g"}, props=VENT)],
         spawn=(-3.0, -3.6, 15.0), goal=(P(1), P(1) + 2.6),
         doors=["a", "d", "g"], room_of=dict(a="S", d="A", g="G"),
         budget=3, start="S", goalRoom="G", timed=False, teach="angle",
         # 斜め上からの俯瞰。★真上から見下ろすと仕切りの板が真横を向いて線になり、
         #   「左右に割れている」が一切伝わらない(撮って確認した)。横へずらして板の面とドアを同じ絵に入れる
         cine=[("A", (4.5, 3.2, 3.5), "A", (0.0, 1.4, -6.0), 2.2),
               ("S", (0.0, 1.7, -3.5), "S", (0.0, 1.5, 6.0), 1.4)]),

    # ---- 3: 仕切りが消える。自分で助走を決める + 制限時間 ----
    #   まっすぐ歩くしかない廊下(corr18)から、天井 7m の吹き抜け(hall20)へ出る。
    #   選択肢が増えたことを、部屋の広さで感じさせる。
    dict(name="stage3", tag="Stage_3", title=3,
         rooms=[R("S", "corr18", (P(0), P(0)), {"W": "a"},
                  props=[("locker", 2.0, 3.2, 180.0), ("pipes", -4.0, -2.6, 0.0)]),
                R("A", "hall20", (P(0), 60.0), {"S": "d"},
                  props=[("railing", -8.6, 6.0, 0.0), ("railing", 8.6, 6.0, 0.0)]),
                R("G", "box12", (60.0, 60.0), {"S": "g"}, props=VENT)],
         spawn=(7.2, 0.0, 270.0), goal=(60.0, 62.6),
         doors=["a", "d", "g"], room_of=dict(a="S", d="A", g="G"),
         budget=3, start="S", goalRoom="G",
         # 吹き抜けの降下 → 廊下の奥行き。
         # ★扇が出るのはドア(南壁)の手前なので北側から南を見る。逆を向くと床しか写らなかった
         cine=[("A", (0.0, 6.4, 8.0), "A", (0.0, 0.4, -8.0), 1.2),
               ("A", (0.0, 2.4, 4.0), "A", (0.0, 1.3, -9.0), 2.4),
               ("S", (7.0, 1.7, 0.0), "S", (-8.5, 1.6, 0.0), 1.6)]),

    # ---- 4: GDD 第4面。全部繋ぎたくなる誘惑が罠になる ----
    #   間違い(P/Q)は cell8 = 天井 3m の物置、正解(G)は hall20 = 開ける。
    #   広さそのものが正誤のフィードバックになっている。
    dict(name="stage4", tag="Stage_4", title=4,
         rooms=[R("S", "box12", (P(0), P(0)), {"N": "a"}, props=BENCH),
                R("P", "cell8", (P(0), P(1)), {"N": "b"},
                  props=[("locker", -2.6, 2.6, 180.0), ("crate", 2.4, -2.2, 20.0)]),
                R("Q", "cell8", (P(1), P(0)), {"N": "c"},
                  props=[("crate", -2.4, -2.4, 40.0), ("crate", -2.0, 2.6, 0.0)]),
                R("G", "hall20", (P(1), P(1)), {"S": "d"},
                  props=[("column", -7.4, 7.4, 0.0), ("column", 7.4, 7.4, 0.0)])],
         spawn=(3.4, -4.0, 340.0), goal=(P(1), P(1) + 2.6),
         doors=["a", "b", "c", "d"], room_of=dict(a="S", b="P", c="Q", d="G"),
         budget=2, start="S", goalRoom="G",
         lightcol=(1.0, 0.90, 0.72), intensity=6.0,
         # 速い刻み。狭い / 狭い / 広い を並べて見せる
         cine=[("P", (0.0, 2.2, -2.6), "P", (0.0, 1.2, 1.0), 0.9),
               ("Q", (0.0, 2.2, -2.6), "Q", (0.0, 1.2, 1.0), 0.9),
               ("G", (0.0, 4.0, -8.0), "G", (0.0, 1.4, 2.6), 1.6),
               ("S", (0.0, 1.7, -3.5), "S", (0.0, 1.5, 6.0), 1.4)]),

    # ---- 5: 遠近の錯覚。虚無に浮かぶ候補の見かけは実距離で決まる ----
    #   近い d と、ずっと遠い g が同じくらいの見かけになるよう G を離してある。
    dict(name="stage5", tag="Stage_5", title=5,
         rooms=[R("S", "corr18", (P(0), P(0)), {"E": "a"},
                  props=[("bench", -5.0, 3.0, 180.0), ("pipes", 3.0, -2.6, 0.0)]),
                R("P", "corr18", (P(0), 60.0), {"W": "b"},
                  props=[("locker", 4.0, 3.2, 180.0)]),
                R("Q", "cell8", (60.0, 60.0), {"S": "c"},
                  props=[("crate", 2.4, 2.4, 15.0)]),
                R("R", "box12", (60.0, P(0)), {"N": "d"}, props=COL2S),
                R("G", "hall20", (208.0, 156.0), {"S": "g"}, props=VENT)],
         spawn=(0.0, 0.0, 90.0), goal=(208.0, 158.6),
         doors=["a", "b", "c", "d", "g"], room_of=dict(a="S", b="P", c="Q", d="R", g="G"),
         budget=3, start="S", goalRoom="G",
         # 廊下の押し込み(トラック)。第3面の「引き」とは逆の運動にする
         cine=[("G", (0.0, 3.2, -8.0), "G", (0.0, 1.4, 2.6), 1.6),
               ("S", (-7.6, 1.6, 0.0), "S", (8.6, 1.5, 0.0), 1.0),
               ("S", (2.0, 1.6, 0.0), "S", (8.6, 1.5, 0.0), 2.6)]),

    # ---- 6: 四枚合流 = 40°。助走の設計が要る ----
    #   主室 Q は hall20 + 柱林。★扇の出る床(ドアの手前)には何も置かない。
    dict(name="stage6", tag="Stage_6", title=6,
         rooms=[R("S", "box12", (P(0), P(0)), {"W": "a"}, props=BENCH),
                R("P", "corr18", (P(0), P(1)), {"N": "b"},
                  props=[("locker", -5.0, 3.2, 180.0), ("pipes", 4.0, -2.6, 0.0)]),
                R("Q", "hall20", (P(1), P(1)), {"S": "c"}, props=COL6),
                R("R", "cell8", (P(1), P(0)), {"E": "d"},
                  props=[("crate", -2.4, 2.4, 30.0)]),
                R("G", "hall20", (P(2), P(1)), {"S": "g"}, props=VENT)],
         spawn=(3.0, 2.0, 270.0), goal=(P(2), P(1) + 2.6),
         doors=["a", "b", "c", "d", "g"], room_of=dict(a="S", b="P", c="Q", d="R", g="G"),
         budget=4, start="S", goalRoom="G",
         # 回り込み。★部屋の中心を見るとドアが画面に入らなかったので、
         #   ドアを固定したまま左から右へ回る(手前の柱が流れて奥行きが出る)
         cine=[("Q", (-6.0, 2.4, -1.0), "Q", (0.0, 1.3, -9.5), 1.6),
               ("Q", (6.0, 2.4, -1.0), "Q", (0.0, 1.3, -9.5), 2.8),
               ("S", (3.0, 1.7, 3.0), "S", (-6.0, 1.6, 0.0), 1.5)]),

    # ---- 7: 五枚合流 = 30°。精密射撃 ----
    #   中継室 T は corr18(両端にドア) = 助走が一直線しか取れない。
    #   照明は半分死んでいる(dimhalf)。暗さで難しくするのではなく不安にさせるのが目的。
    dict(name="stage7", tag="Stage_7", title=7,
         rooms=[R("S", "box12", (P(0), P(0)), {"E": "a"}, props=BENCH),
                R("T", "corr18", (P(0), P(1)), {"W": "b", "E": "e"},
                  props=[("locker", -5.0, 3.2, 180.0), ("locker", 5.0, 3.2, 180.0),
                         ("pipes", 0.0, -2.8, 0.0)]),
                R("P", "cell8", (P(1), P(1)), {"N": "c"},
                  props=[("crate", 2.4, -2.4, 25.0)]),
                R("Q", "box12", (P(1), P(0)), {"S": "d"}, props=COL2N),
                R("U", "cell8", (P(2), P(0)), {"W": "f"},
                  props=[("crate", 2.2, 2.4, 0.0)]),
                R("G", "hall20", (P(2), P(1)), {"S": "g"}, props=VENT)],
         spawn=(-3.0, -2.0, 80.0), goal=(P(2), P(1) + 2.6),
         doors=["a", "b", "c", "d", "e", "f", "g"],
         room_of=dict(a="S", b="T", c="P", d="Q", e="T", f="U", g="G"),
         budget=4, start="S", goalRoom="G",
         lightcol=(0.90, 0.95, 1.0), intensity=7.0, dimhalf=True,
         # あおり。目線を落として天井と奥行きを見上げる
         cine=[("T", (-7.0, 0.9, 0.0), "T", (8.6, 2.4, 0.0), 1.4),
               ("T", (0.0, 0.9, 0.0), "T", (8.6, 2.4, 0.0), 2.4),
               ("S", (0.0, 1.7, -3.0), "S", (6.0, 1.6, 0.0), 1.4)]),

    # ---- 8: 一棟。ドア 8 枚・予算 3。合流点の崩壊(6 枚目)が初めて起こり得る ----
    #   形を全部混ぜ、照明は非常灯だけ。最終面だと絵で分かる。
    dict(name="stage8", tag="Stage_8", title=8,
         rooms=[R("S", "corr18", (P(0), P(0)), {"W": "a", "E": "h"},
                  props=[("bench", -4.0, 3.0, 180.0), ("pipes", 4.0, -2.6, 0.0)]),
                R("T", "cell8", (P(0), P(1)), {"S": "b"},
                  props=[("crate", -2.4, 2.4, 10.0)]),
                R("P", "hall20", (P(1), P(1)), {"S": "c", "E": "e"}, props=COL8P),
                R("Q", "box12", (P(1), P(0)), {"N": "d"}, props=COL2S),
                R("U", "corr18", (P(2), P(1)), {"S": "f"},
                  props=[("locker", 5.0, 3.2, 180.0)]),
                R("G", "hall20", (P(3), P(2)), {"S": "g"}, props=VENT)],
         spawn=(0.0, 2.0, 270.0), goal=(P(3), P(2) + 2.6),
         doors=["a", "b", "c", "d", "e", "f", "g", "h"],
         room_of=dict(a="S", b="T", c="P", d="Q", e="P", f="U", g="G", h="S"),
         budget=3, start="S", goalRoom="G",
         lightcol=(1.0, 0.30, 0.22), intensity=4.0,
         # 引き。出口に寄ってから、部屋ごと引いて全体を突き放す
         cine=[("G", (0.0, 2.0, -4.0), "G", (0.0, 1.5, 2.6), 1.2),
               ("G", (0.0, 5.5, -8.6), "G", (0.0, 1.2, 2.6), 2.6),
               ("S", (6.5, 1.7, 0.0), "S", (-8.6, 1.6, 0.0), 1.6)]),
]


if __name__ == "__main__":
    for st in STAGES:
        # 部屋の中心と形の索引(cine のローカル->ワールド変換と assert に使う)
        centers = {r["id"]: (r["at"][0], r["at"][1], r["shape"]) for r in st["rooms"]}
        for did, rid in st["room_of"].items():
            if rid not in centers:
                raise SystemExit("%s: ドア %s の部屋 %s が無い" % (st["name"], did, rid))
        d = scene(st)
        # assert 用に拾い直す。★pfx は【什器だけ】。衝立は意図して助走路に立てるので
        #   check_lanes の対象から外し、check_blockers の方で別の掟を当てる。
        pfx, fx = {}, {}
        for r in st["rooms"]:
            props([], r["id"], r["at"][0], r["at"][1], SHAPES[r["shape"]]["h"],
                  r.get("props", ()), None, pfx)
        for rid, v in pfx.items():
            fx[rid] = list(v)
        for r in st["rooms"]:
            blockers([], r["id"], r["at"][0], r["at"][1], r.get("blocks", ()), None, fx)
        check_lanes(st, pfx)
        check_blockers(st)
        check_cine(st, centers, fx)
        st["_cine"] = cine_world(st, centers)
        p = os.path.normpath(os.path.join(OUT, st["name"] + ".json"))
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print("wrote", p, len(d["entities"]), "entities,",
              len(st["_cine"]), "cine shots")

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
        lua.append('        spawn = { %.1f, 1.7, %.1f, %.1f }, timed = %s, teach = %s,'
                   % (st["spawn"][0], st["spawn"][1], st["spawn"][2],
                      "true" if st.get("timed", True) else "false",
                      ('"%s"' % st["teach"]) if st.get("teach") else "nil"))
        # cine = { { ex,ey,ez, tx,ty,tz, dur }, ... }(ワールド座標)
        lua.append('        cine = {')
        for c in st["_cine"]:
            lua.append('            { %.2f, %.2f, %.2f, %.2f, %.2f, %.2f, %.2f },' % c)
        lua.append('        } },')
    lp = os.path.normpath(os.path.join(OUT, "..", "components", "Junction.lua"))
    src = open(lp, encoding="utf-8").read()
    A, B = "-- >>>STAGES", "-- <<<STAGES"
    ia, ib = src.index(A), src.index(B)
    src = src[:ia] + A + " (source/gen_stages.py が自動生成)\n" + "\n".join(lua) + "\n    " + src[ib:]
    open(lp, "w", encoding="utf-8").write(src)
    print("patched", lp, len(STAGES), "stages")
