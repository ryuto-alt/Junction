# -*- coding: utf-8 -*-
"""JUNCTION の内装キットを Blender で組んで glTF へ書き出す。
BlenderMCP の execute_blender_code から
    exec(open(r"...\\source\\blender_kit.py", encoding="utf-8").read())
で叩く。

★寸法は source/gen_stages.py と【必ず一致】させること(下の定数)。
★Blender の -Y = エンジンの +Z。壁は「部屋の内側 = エンジン +Z」を向かせたいので
  Blender では法線 -Y で作る。床は +Z(= エンジン +Y)。
★エンジンは baseColorFactor を読まない = 単色マテリアルは真っ白。全部 col テクスチャを貼る。
★エクスポータは use_selection=False だと .blend の【全シーン】を書き出す。
  毎回 全部 deselect → 対象だけ select → use_selection=True。
"""
import bpy, os, math, shutil, tempfile

# ★リポジトリの場所は機械によって違う。exec で叩くので __file__ が無い =
#   実在する方を選ぶ。JX_ROOT をグローバルに入れてから exec すれば上書きできる。
ROOT = globals().get("JX_ROOT") or next(
    p for p in (r"C:\Users\ryuto\Documents\dev\game\Junction",
                r"C:\Users\GSuser\Documents\10days\Junction") if os.path.isdir(p))
TEX = os.path.join(ROOT, "assets", "models", "tex")
OUT = os.path.join(ROOT, "assets", "models")

# ---- 寸法。gen_stages.py と【必ず一致】させる。★変えるな、増やせ ----
WALLT = 0.3     # 壁の厚み(gen_stages.py の WALLT)
SPAN  = 12.3    # box12 の壁の全長 = 内寸 12 + WALLT
WALLH = 4.0
DOORW = 2.0     # ★1.5 から拡張。開口を行き先の数だけ縦の帯に割るので、
                #   4 出口でも帯が 0.5m 残る幅が要る(1.5 だと 0.375m でプレイヤー直径 0.7m に対し狭すぎた)。
                #   ついでに「人が通る扉」でなく「門・ゲート」に見える。
DOORH = 2.6
WINW  = 6.0     # 窓の開口(第1面の「見えているのに行けない」)
WINY0 = 1.0
WINY1 = 3.0

# 部屋の形。SPAN は「内寸 + WALLT」= 隣の壁と角で噛み合う長さ。
#   (内寸X, 内寸Z, 天井高)。box12 は既存の floor/ceiling/wall/wall_door がこれ。
FOOTPRINTS = {
    "box12":  (12.0, 12.0, 4.0),
    "hall20": (20.0, 20.0, 7.0),
    "corr18": (18.0,  8.0, 3.2),
    "cell8":  ( 8.0,  8.0, 3.0),
}


def E(x, y, z):
    """エンジン座標(x=右, y=上, z=前) -> Blender 座標。
    エクスポータの export_yup がちょうどこの逆(blender x,y,z -> gltf x,z,-y)をやるので、
    ここを通して置いた物は【エンジンで見た通りの向き】で出る。
    ★新しい部品はこれを使って「エンジンの座標で」考えること。壁/床の既存コードだけは
      昔ながらの生 Blender 座標(法線 -Y)のまま。"""
    return (x, -z, y)

def tex_mirror():
    """★エクスポータは export_texture_dir へ画像を【コピー】する。読み込み元が
    そのコピー先そのものだと「自分を自分に上書き」になり、Blender 5.2 は
    OSError [Errno 22] で落ちる(5.1 は素通りしていた)。
    だから画像は tex/ のミラーから読む。書き出される tex/*.png は中身が同じ。"""
    d = os.path.join(tempfile.gettempdir(), "jx_tex_src")
    if os.path.isdir(d):
        shutil.rmtree(d)
    shutil.copytree(TEX, d)
    return d


TEXSRC = tex_mirror()


# ---------------------------------------------------------------- マテリアル
def mat(name, tex, rough=0.85, metal=0.0, nrm=None):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    # ★UI が日本語だとノード名も日本語。名前ではなく type で引く
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if tex:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEXSRC, tex), check_existing=True)
        t.location = (-600, 300)
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    if nrm:
        t2 = nt.nodes.new("ShaderNodeTexImage")
        t2.image = bpy.data.images.load(os.path.join(TEXSRC, nrm), check_existing=True)
        t2.image.colorspace_settings.name = 'Non-Color'
        t2.location = (-600, -200)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.location = (-300, -200)
        nt.links.new(t2.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


# ---------------------------------------------------------------- メッシュ組み立て
class Build:
    """verts/faces/uvs/mat_index を貯めて 1 オブジェクトにする。UV は 2m = 1タイル。"""
    K = 0.5   # 1m あたりの UV(= 2m で 1 周)

    def __init__(self):
        self.v, self.f, self.uv, self.mi = [], [], [], []

    def face(self, pts, uvs, m):
        """n 角形。CCW で並べた側が表(法線)。"""
        n = len(self.v)
        self.v += list(pts)
        self.f.append(tuple(range(n, n + len(pts))))
        self.uv.append(list(uvs))
        self.mi.append(m)

    def quad(self, p0, p1, p2, p3, uvs, m):
        self.face([p0, p1, p2, p3], uvs, m)

    def wallquad(self, x0, x1, z0, z1, m, y=0.0):
        """XZ 平面・法線 -Y(= エンジンの +Z)。UV は x,z から。"""
        K = self.K
        self.quad((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1),
                  [(x0 * K, z0 * K), (x1 * K, z0 * K), (x1 * K, z1 * K), (x0 * K, z1 * K)], m)

    def floorquad(self, x0, x1, y0, y1, z, m, down=False):
        K = self.K
        a = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
        u = [(x0 * K, y0 * K), (x1 * K, y0 * K), (x1 * K, y1 * K), (x0 * K, y1 * K)]
        if down:
            a = a[::-1]; u = u[::-1]
        self.quad(a[0], a[1], a[2], a[3], u, m)

    def box(self, c, s, m, k=None):
        """中心 c・全長 s の箱。UV はボックス投影。"""
        K = k if k is not None else self.K
        (cx, cy, cz), (sx, sy, sz) = c, s
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        X = [cx - hx, cx + hx]; Y = [cy - hy, cy + hy]; Z = [cz - hz, cz + hz]
        P = lambda i, j, k2: (X[i], Y[j], Z[k2])
        faces = [
            # (4頂点, UV に使う 2 軸)
            ((P(0,0,1), P(1,0,1), P(1,1,1), P(0,1,1)), (0, 1)),   # +Z
            ((P(0,1,0), P(1,1,0), P(1,0,0), P(0,0,0)), (0, 1)),   # -Z
            ((P(0,0,0), P(1,0,0), P(1,0,1), P(0,0,1)), (0, 2)),   # -Y
            ((P(1,1,0), P(0,1,0), P(0,1,1), P(1,1,1)), (0, 2)),   # +Y
            ((P(1,0,0), P(1,1,0), P(1,1,1), P(1,0,1)), (1, 2)),   # +X
            ((P(0,1,0), P(0,0,0), P(0,0,1), P(0,1,1)), (1, 2)),   # -X
        ]
        for pts, (a, b) in faces:
            self.quad(pts[0], pts[1], pts[2], pts[3],
                      [(p[a] * K, p[b] * K) for p in pts], m)

    # ------------------------------------------------ エンジン座標で置く版
    def ebox(self, c, s, m, k=None):
        """エンジン座標の軸並行な箱。中心 c=(x,y,z)・全長 s=(x,y,z)。"""
        self.box(E(*c), (s[0], s[2], s[1]), m, k)

    def eprism(self, pts, y0, y1, m, k=None):
        """エンジンの床平面(XZ)の多角形 pts=[(x,z),...] を、高さ y0..y1 に押し出す。
        ★向きは自動で揃える(上面の法線が必ずエンジン +Y)。凸多角形で渡すこと
          (凹んだ n 角形は三角形化で崩れることがある。針は 2 個に割ってある)。"""
        K = k if k is not None else self.K
        P = [(x, -z) for (x, z) in pts]                 # エンジン XZ -> Blender XY
        n = len(P)
        area = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
        if area < 0:
            P = P[::-1]                                  # Blender XY で CCW = 上面が +Y
        top = [(x, y, y1) for (x, y) in P]
        bot = [(x, y, y0) for (x, y) in P]
        uv = [(x * K, y * K) for (x, y) in P]
        self.face(top, uv, m)
        self.face(bot[::-1], uv[::-1], m)
        d = 0.0
        for i in range(n):
            j = (i + 1) % n
            e = math.hypot(P[j][0] - P[i][0], P[j][1] - P[i][1])
            self.face([bot[i], bot[j], top[j], top[i]],
                      [(d * K, y0 * K), ((d + e) * K, y0 * K),
                       ((d + e) * K, y1 * K), (d * K, y1 * K)], m)
            d += e

    def eface(self, pts, uvs, m):
        """エンジン座標の点列で 1 面。★表裏は【エンジン座標のまま】考えてよい
        (E() は回転なので、法線の向きから見て CCW に並べれば表になる)。
        UV を自分で渡せるのが quad/box との違い = 帯とレーンの模様を 0..1 で貼るために要る。"""
        self.face([E(*p) for p in pts], uvs, m)

    def eslab(self, x0, x1, y0, y1, z0, z1, m, uvfn):
        """エンジン軸並行の直方体を【6 面を自分で並べて】作る。box() と違い
        面ごとに UV を決められる = 帯とレーンの模様を 0..1 で貼るために要る。
        uvfn(面の名前, 4点) -> 4 つの UV。面の名前は "+z" のように軸と符号。"""
        F = [
            ("+z", [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
            ("-z", [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)]),
            ("+x", [(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)]),
            ("-x", [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)]),
            ("+y", [(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)]),
            ("-y", [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]),
        ]
        for name, pts in F:
            self.eface(pts, uvfn(name, pts), m)

    def etube(self, profile, m, axis="z", origin=(0, 0, 0), seg=14, k=None):
        """回転体。profile=[(軸方向の位置 t, 半径 r), ...]。r=0 の端は尖る(=円錐の先)。
        axis はエンジンの軸。ピン(z)・配管(x)・手すりの柱(y) に使う。"""
        K = k if k is not None else self.K
        def pt(t, r, a):
            c, s = r * math.cos(a), r * math.sin(a)
            # ★角度の回り方は右手系のまま(軸の正の側から見て CCW)。ここを崩すと裏返る
            w = {"x": (t, c, s), "y": (s, t, c), "z": (c, s, t)}[axis]
            return E(w[0] + origin[0], w[1] + origin[1], w[2] + origin[2])
        A = [2 * math.pi * i / seg for i in range(seg)]
        for q in range(len(profile) - 1):
            (t0, r0), (t1, r1) = profile[q], profile[q + 1]
            for i in range(seg):
                a0, a1 = A[i], A[(i + 1) % seg]
                u0, u1 = i / seg, (i + 1) / seg
                if r0 <= 1e-6:                            # 先端(三角形)
                    self.face([pt(t0, 0.0, a0), pt(t1, r1, a0), pt(t1, r1, a1)],
                              [(u0, t0), (u0, t1), (u1, t1)], m)
                elif r1 <= 1e-6:
                    self.face([pt(t0, r0, a0), pt(t0, r0, a1), pt(t1, 0.0, a1)],
                              [(u0, t0), (u1, t0), (u1, t1)], m)
                else:
                    self.face([pt(t0, r0, a0), pt(t0, r0, a1), pt(t1, r1, a1), pt(t1, r1, a0)],
                              [(u0, t0 * K), (u1, t0 * K), (u1, t1 * K), (u0, t1 * K)], m)
        # 端の蓋(半径が残っている側だけ)
        for (t, r), rev in ((profile[0], True), (profile[-1], False)):
            if r <= 1e-6:
                continue
            ring = [pt(t, r, a) for a in A]
            uv = [(0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)) for a in A]
            if rev:
                ring = ring[::-1]; uv = uv[::-1]
            self.face(ring, uv, m)

    def make(self, name, mats):
        # ★同名のオブジェクトだけでなく【メッシュ datablock も】消す。
        #   残っていると Blender が jx_wall.001 → .002 と名前をずらし、
        #   出力の gltf に毎回 意味の無い差分が出る(何も変えていないのに diff が出る)。
        for o in list(bpy.data.objects):
            if o.name == name:
                bpy.data.objects.remove(o, do_unlink=True)
        for old in list(bpy.data.meshes):
            if old.name == name or old.name.startswith(name + "."):
                bpy.data.meshes.remove(old, do_unlink=True)
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        for m in mats:
            ob.data.materials.append(m)
        uvl = me.uv_layers.new(name="UVMap")
        for pi, poly in enumerate(me.polygons):
            poly.material_index = self.mi[pi]
            for k, li in enumerate(poly.loop_indices):
                uvl.data[li].uv = self.uv[pi][k]
        me.shade_flat()
        return ob


def export(ob, fname):
    """★書き出しは【一旦 temp へ】。エクスポータは export_texture_dir に PNG を
    自前で【再エンコードして上書き】するので、assets/models へ直接書くと
    gen_textures.py が描いた tex/*.png が Blender の再圧縮版に化ける
    (ノーマルマップが Non-Color のまま焼き直されるので実害がある)。
    欲しいのは .gltf と .bin だけ。uri は "tex/xxx.png" の相対なのでそのまま通る。"""
    for sc in bpy.data.scenes:
        for o in sc.objects:
            o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    tmp = os.path.join(tempfile.gettempdir(), "jx_export")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    bpy.ops.export_scene.gltf(filepath=os.path.join(tmp, fname),
                              export_format='GLTF_SEPARATE',
                              use_selection=True, export_texture_dir='tex',
                              export_yup=True, export_apply=True)
    for ext in (".gltf", ".bin"):
        src = os.path.join(tmp, fname[:-5] + ext)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(OUT, fname[:-5] + ext))
    print("exported", os.path.join(OUT, fname))


# ---------------------------------------------------------------- 壁(寸法パラメータ化)
def baseboard(b, x0, x1):
    b.box(((x0 + x1) / 2, -0.02, 0.07), (x1 - x0, 0.05, 0.14), 1, 0.5)


def wall_mesh(L, H, op=None):
    """壁 1 枚。★原点は【壁の中央・床の高さ】、法線 -Y(= エンジン +Z = 部屋の内側)。
    L は壁の全長 = 部屋の内寸 + WALLT(角で隣の壁と噛み合うぶん)。
    op=(開口の幅, 下端, 上端)。None なら無開口。
    ★この規約は gen_stages.py が全部の壁を同じ式で置く前提。長さと高さ以外は変えないこと。"""
    b = Build()
    h = L / 2
    if op is None:
        b.wallquad(-h, h, 0.0, H, 0)
        baseboard(b, -h, h)
        return b
    w, y0, y1 = op
    d = w / 2
    b.wallquad(-h, -d, 0.0, H, 0)               # 左
    b.wallquad(d, h, 0.0, H, 0)                 # 右
    if y1 < H - 1e-6:
        b.wallquad(-d, d, y1, H, 0)             # まぐさ
    if y0 > 1e-6:
        b.wallquad(-d, d, 0.0, y0, 0)           # 腰壁(窓の下)
    baseboard(b, -h, -d); baseboard(b, d, h)
    if y0 > 1e-6:
        baseboard(b, -d, d)
    cw, cd = 0.13, 0.045                        # ケーシングの幅/出っ張り
    pz0 = y0 - cw if y0 > 1e-6 else 0.0         # 縦枠は開口の上下に cw ぶん回り込む
    pz1 = y1 + cw
    for s in (-1, +1):
        b.box((s * (d + cw / 2), -cd / 2, (pz0 + pz1) / 2), (cw, cd, pz1 - pz0), 1, 0.5)
    b.box((0.0, -cd / 2, y1 + cw / 2), (w, cd, cw), 1, 0.5)         # 上枠
    if y0 > 1e-6:
        b.box((0.0, -cd / 2, y0 - cw / 2), (w, cd, cw), 1, 0.5)     # 下枠(窓台)
    return b


# ---------------------------------------------------------------- 部品
def build_all():
    M_WALL = mat("jx_wall", "wall_col.png", 0.88, 0.0, "wall_nrm.png")
    M_PAINT = mat("jx_paint", "paint_col.png", 0.55)
    M_CARPET = mat("jx_carpet", "carpet_col.png", 0.95, 0.0, "carpet_nrm.png")
    # ★天井はノーマルマップ無し(見た目が変わらないのに 1 枚増えるだけだった)
    M_CEIL = mat("jx_ceiling", "ceiling_col.png", 0.92)
    M_METAL = mat("jx_metal", "metal_col.png", 0.45, 0.6)
    M_CONC = mat("jx_concrete", "concrete_col.png", 0.90, 0.0, "concrete_nrm.png")
    M_DIFF = mat("jx_diffuser", "paint_col.png", 0.25)

    H = SPAN / 2

    # ---- 床(原点=部屋の中心・上向き) ----
    b = Build(); b.floorquad(-H, H, -H, H, 0.0, 0)
    export(b.make("jx_floor", [M_CARPET]), "floor.gltf")

    # ---- 天井(下向き。原点=天井面) ----
    b = Build(); b.floorquad(-H, H, -H, H, 0.0, 0, down=True)
    export(b.make("jx_ceiling", [M_CEIL]), "ceiling.gltf")

    # ---- 壁(原点=壁の中央・床の高さ。法線 -Y = エンジン +Z) ----
    export(wall_mesh(SPAN, WALLH).make("jx_wall", [M_WALL, M_PAINT]), "wall.gltf")

    # ---- 開口付きの壁 + ケーシング(枠の飾り) ----
    export(wall_mesh(SPAN, WALLH, (DOORW, 0.0, DOORH)).make(
        "jx_wall_door", [M_WALL, M_PAINT]), "wall_door.gltf")

    # ---- 窓付きの壁(第1面。出口の部屋が【見えているのに歩いては行けない】) ----
    # ★腰高 1.0m が残るので通り抜けられない = ガラスを入れずに済む(半透明描画を回避)。
    #   「見た目の先」と「繋いだ先」が違う、というこのゲームの核を無言で渡す装置。
    export(wall_mesh(SPAN, WALLH, (WINW, WINY0, WINY1)).make(
        "jx_wall_window", [M_WALL, M_PAINT]), "wall_window.gltf")

    # ---- 埋め込み照明(原点=天井面。下へ 0.09 出る) ----
    b = Build()
    b.box((0, 0, -0.05), (1.30, 0.70, 0.10), 0, 1.0)          # 枠
    # ★カバーは枠の【下面より下】に出す。同じ高さだと枠の底面(暗い金属)に隠れる
    b.floorquad(-0.56, 0.56, -0.28, 0.28, -0.104, 1, down=True)  # 乳白カバー
    export(b.make("jx_troffer", [M_METAL, M_DIFF]), "troffer.gltf")

    # ---- 通気口(法線 -Y。壁に貼る) ----
    b = Build()
    b.box((0, -0.015, 0), (0.62, 0.03, 0.36), 0, 1.0)
    for i in range(5):
        z = -0.13 + i * 0.065
        b.box((0, -0.045, z), (0.54, 0.03, 0.030), 0, 1.0)    # ルーバー
    export(b.make("jx_vent", [M_METAL]), "vent.gltf")

    # ---- 角柱(原点=床) ----
    b = Build()
    b.box((0, 0, WALLH / 2), (0.62, 0.62, WALLH), 0, 0.5)
    b.box((0, 0, 0.09), (0.72, 0.72, 0.18), 1, 0.5)           # 沓石
    export(b.make("jx_column", [M_CONC, M_PAINT]), "column.gltf")

    # ---- 長椅子(初期ステージの目印。部屋の識別性を上げる) ----
    b = Build()
    b.box((0, 0, 0.44), (1.70, 0.50, 0.08), 0, 0.5)           # 座面
    b.box((0, 0.21, 0.72), (1.70, 0.08, 0.48), 0, 0.5)        # 背
    for sx in (-0.72, 0.72):
        b.box((sx, 0, 0.20), (0.08, 0.44, 0.40), 1, 1.0)      # 脚
    export(b.make("jx_bench", [M_PAINT, M_METAL]), "bench.gltf")

    print("KIT DONE")


# ---------------------------------------------------------------- 部屋の形(D-1)
def build_rooms():
    """box12 以外のフットプリント。★同じ 12m 角の箱が 8 面続くと「新しい事を足しても
    画面が同じなので新しく見えない」= 今回の最大の指摘。形そのものを変える。
    壁は【長さと天井高だけ】が違う。原点・向き・開口の位置は box12 と完全に同じ規約。"""
    M_WALL = mat("jx_wall", "wall_col.png", 0.88, 0.0, "wall_nrm.png")
    M_PAINT = mat("jx_paint", "paint_col.png", 0.55)
    M_CARPET = mat("jx_carpet", "carpet_col.png", 0.95, 0.0, "carpet_nrm.png")
    M_CEIL = mat("jx_ceiling", "ceiling_col.png", 0.92)

    def slab(sx, sz, name, fn, down):
        b = Build()
        b.floorquad(-sx / 2, sx / 2, -sz / 2, sz / 2, 0.0, 0, down=down)
        export(b.make(name, [M_CEIL if down else M_CARPET]), fn)

    # 床/天井。原点は部屋の中心(床は床面、天井は天井面)。スパン = 内寸 + WALLT
    for tag, fx, fz in (("20", 20.0, 20.0), ("18x8", 18.0, 8.0), ("8", 8.0, 8.0)):
        sx, sz = fx + WALLT, fz + WALLT
        slab(sx, sz, "jx_floor_" + tag, "floor%s.gltf" % tag, False)
        slab(sx, sz, "jx_ceil_" + tag, "ceiling%s.gltf" % tag, True)

    # 壁。(ファイル接頭辞, 全長, 天井高)
    #   ★wall8 は corr18(3.2) の高さで出し、cell8(3.0) にも流用する。
    #     0.2m ぶん天井より上に伸びるが、天井モデルが蓋をするので中からは見えない。
    for tag, L, H in (("20", 20.0 + WALLT, 7.0),
                      ("18", 18.0 + WALLT, 3.2),
                      ("8", 8.0 + WALLT, 3.2)):
        export(wall_mesh(L, H).make("jx_wall_" + tag, [M_WALL, M_PAINT]),
               "wall%s.gltf" % tag)
        export(wall_mesh(L, H, (DOORW, 0.0, DOORH)).make(
            "jx_wall_%s_door" % tag, [M_WALL, M_PAINT]), "wall%s_door.gltf" % tag)


# ---------------------------------------------------------------- 門(GATE)
def build_gate():
    """開口の色帯と床のレーンとピン。
    ★選択装置を「歩く向き(角度)」から「開口のどこを通ったか(場所)」へ変えた。
      床の扇(wedge*)と入射角の針(needle)は【廃止】= 一人称では自分の向きが見えないので、
      どれだけ丁寧に描いても「表示を読む作業」にしかならなかった。
      代わりに、改札と同じ「どのゲートを通ったか」を物として置く。
    ★Lua が scene:setColor で【乗算】して色を乗せるので、テクスチャは無彩色。
      色を持たせると行き先の色が濁る。境目は【明度だけ】で描く。
    ★帯もレーンも 幅 1.0 で作り、Lua が transform.scale で実寸(帯幅)へ伸ばす。"""
    M_BAND = mat("jx_band", "band_col.png", 0.45)
    M_LANE = mat("jx_lane", "lane_col.png", 0.70)
    M_PLAIN = mat("jx_plain", "plain_col.png", 0.55)
    M_METAL = mat("jx_metal", "metal_col.png", 0.45, 0.6)

    # ---- 色帯(原点=底面の中心。幅 1.0 / 高さ 1.0 / 厚み 0.06。板の面は ±Z) ----
    # ★scale で 幅=帯幅・高さ=DOORH に伸ばされる。厚みは伸びない = 常に 0.06。
    #   UV は面の 0..1 に貼るので、帯を細くしても【縁の暗い線は同じ割合で残る】。
    T = 0.03
    def uv_band(name, pts):
        if name in ("+z", "-z"):                       # 表裏: u=幅方向, v=高さ
            return [((p[0] + 0.5), 1.0 - p[1]) for p in pts]
        return [(0.008, 1.0 - p[1]) for p in pts]      # 側面/上下は縁の色(暗い)で塗る
    b = Build()
    b.eslab(-0.5, 0.5, 0.0, 1.0, -T, T, 0, uv_band)
    export(b.make("jx_band", [M_BAND]), "band.gltf")

    # ---- 床のレーン(原点=【手前端】の中心。幅 1.0 / 長さ 1.0 / 厚み 0.02。+Z へ伸びる) ----
    # ★帯と地続きに見えることが全て。先端(+Z 側 = 帯に接する側)が一番明るく、
    #   手前(原点側)へ向かって明度が落ちる。色は乗算で乗るので明度だけで作る。
    LT = 0.02
    def uv_lane(name, pts):
        if name == "+y":                               # 上面: u=幅, v=長さ(0=手前, 1=帯側)
            return [((p[0] + 0.5), 1.0 - p[2]) for p in pts]
        if name in ("+x", "-x"):                       # 長辺の小口も長さで暗くする
            return [(0.008, 1.0 - p[2]) for p in pts]
        return [(0.008, 1.0 - p[2]) for p in pts]
    b = Build()
    b.eslab(-0.5, 0.5, 0.0, LT, 0.0, 1.0, 0, uv_lane)
    export(b.make("jx_lane", [M_LANE]), "lane.gltf")

    # ---- 接続ピン(原点=針の先端。針は -Z 側へ、頭は +Z 側) ----
    # ★壁に刺した点が原点になる = Lua は刺さった座標にそのまま置ける。
    #   ドアの forward(部屋の内側)を向けて置くと、頭が部屋側に出る。
    b = Build()
    b.etube([(0.0, 0.0), (0.020, 0.006), (0.120, 0.010), (0.156, 0.010)], 1, seg=12)  # 針
    b.etube([(0.150, 0.014), (0.158, 0.046), (0.195, 0.048), (0.220, 0.030)], 0, seg=18)  # 頭
    export(b.make("jx_pin", [M_PLAIN, M_METAL]), "pin.gltf")


# ---------------------------------------------------------------- 仕切り / 衝立
def build_divider():
    """腰高の板。原点=底面の中心。長さ方向は X、板の面は ±Z。
    divider(4.0m) … 第2面の間仕切り。
    blocker(1.2m) … ★ドアの【正面】を塞ぐ衝立。真っ直ぐ入れないので左右どちらかへ回る
      = どの帯を通るかを必ず【選ぶ】ことになる。(4) までは仕切りがドアの中心線上に立っていて
      「塞ぐべき中央を開け、開けるべき左右を塞ぐ」逆をやっていた。"""
    M_PAINT = mat("jx_paint", "paint_col.png", 0.55)
    M_METAL = mat("jx_metal", "metal_col.png", 0.45, 0.6)

    def plate(L, H=1.15, T=0.14):
        b = Build()
        b.ebox((0, (H - 0.07) / 2, 0), (L, H - 0.07, T), 0, 0.5)              # 板
        b.ebox((0, H - 0.035, 0), (L, 0.07, 0.20), 1, 1.0)                    # 手すりの帯
        for sx in (-1, +1):
            b.ebox((sx * (L / 2 - 0.06), (H - 0.07) / 2, 0), (0.12, H - 0.07, T + 0.02), 1, 1.0)
        b.ebox((0, 0.04, 0), (L, 0.08, T + 0.02), 1, 0.5)                     # 蹴込み
        return b

    export(plate(4.0).make("jx_divider", [M_PAINT, M_METAL]), "divider.gltf")
    export(plate(1.2).make("jx_blocker", [M_PAINT, M_METAL]), "blocker.gltf")


# ---------------------------------------------------------------- 什器(部屋の識別)
def build_props():
    """★bench/column/vent の 3 種だけだとどの部屋も同じ顔になる。
    「さっきの部屋とは違う」が一目で分かることだけが目的。当たり判定は付かない
    (gen_stages.py が rigidBody を付けない)= 通り抜ける物として置かれる。"""
    M_PAINT = mat("jx_paint", "paint_col.png", 0.55)
    M_METAL = mat("jx_metal", "metal_col.png", 0.45, 0.6)
    M_CONC = mat("jx_concrete", "concrete_col.png", 0.90, 0.0, "concrete_nrm.png")
    M_WOOD = mat("jx_wood", "wood_col.png", 0.80)

    # ---- ロッカー列(原点=底面の中心。扉は +Z 向き) ----
    b = Build()
    b.ebox((0, 0.94, 0), (1.56, 1.84, 0.50), 1, 0.7)                      # 箱
    b.ebox((0, 0.05, 0), (1.60, 0.10, 0.54), 1, 0.7)                      # 台輪
    b.ebox((0, 1.87, 0), (1.60, 0.06, 0.54), 1, 0.7)                      # 天板
    for i in range(4):
        x = -0.585 + i * 0.39
        b.ebox((x, 0.98, 0.262), (0.355, 1.70, 0.030), 0, 1.0)            # 扉
        b.ebox((x + 0.13, 0.95, 0.292), (0.030, 0.17, 0.055), 1, 1.0)     # 取っ手
        for j in range(3):
            b.ebox((x, 1.70 + j * 0.05, 0.286), (0.22, 0.020, 0.020), 1, 1.0)   # 通気
    export(b.make("jx_locker", [M_PAINT, M_METAL]), "locker.gltf")

    # ---- 露出配管(原点=天井面。下へ垂れる。長さ方向は X) ----
    b = Build()
    for (r, dy, dz) in ((0.075, -0.20, -0.13), (0.050, -0.16, 0.07), (0.030, -0.11, 0.21)):
        b.etube([(-3.0, r), (3.0, r)], 0, axis="x", origin=(0, dy, dz), seg=12)
        for x in (-1.5, 1.5):                                            # 継手のカラー
            b.etube([(x - 0.05, r + 0.018), (x + 0.05, r + 0.018)], 0,
                    axis="x", origin=(0, dy, dz), seg=12)
    for x in (-2.3, 0.0, 2.3):                                           # 吊りバンド
        b.ebox((x, -0.10, 0.04), (0.05, 0.21, 0.72), 0, 1.0)
    export(b.make("jx_pipes", [M_METAL]), "pipes.gltf")

    # ---- 手すり(吹き抜けの縁。原点=底面の中心。長さ方向は X) ----
    b = Build()
    b.etube([(-1.5, 0.035), (1.5, 0.035)], 0, axis="x", origin=(0, 1.03, 0), seg=12)
    b.etube([(-1.5, 0.022), (1.5, 0.022)], 0, axis="x", origin=(0, 0.56, 0), seg=10)
    for x in (-1.40, -0.47, 0.47, 1.40):
        b.etube([(0.0, 0.028), (1.03, 0.028)], 0, axis="y", origin=(x, 0, 0), seg=10)
        b.ebox((x, 0.012, 0), (0.13, 0.024, 0.13), 0, 1.0)               # 座金
    export(b.make("jx_railing", [M_METAL]), "railing.gltf")

    # ---- 木箱(原点=底面の中心) ----
    b = Build()
    S, HT = 0.78, 0.70
    b.ebox((0, HT / 2, 0), (S, HT, S), 0, 1.0)
    for sx in (-1, +1):
        for sz in (-1, +1):                                              # 隅の桟
            b.ebox((sx * S / 2, HT / 2, sz * S / 2), (0.07, HT, 0.07), 1, 1.0)
    for y in (0.06, HT - 0.06):                                          # 上下の帯
        b.ebox((0, y, 0), (S + 0.02, 0.06, S + 0.02), 1, 1.0)
    export(b.make("jx_crate", [M_WOOD, M_CONC]), "crate.gltf")


build_all()
build_rooms()
build_gate()
build_divider()
build_props()
print("KIT ALL DONE")
