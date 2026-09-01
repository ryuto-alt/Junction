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
import bpy, os, math

HERE = os.path.dirname(bpy.path.abspath("//")) if False else None
ROOT = r"C:\Users\GSuser\Documents\10days\Junction"
TEX = os.path.join(ROOT, "assets", "models", "tex")
OUT = os.path.join(ROOT, "assets", "models")

SPAN  = 12.3    # 壁の全長 = HALF*2 + WALLT
WALLH = 4.0
DOORW = 1.5
DOORH = 2.6

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
        t.image = bpy.data.images.load(os.path.join(TEX, tex), check_existing=True)
        t.location = (-600, 300)
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    if nrm:
        t2 = nt.nodes.new("ShaderNodeTexImage")
        t2.image = bpy.data.images.load(os.path.join(TEX, nrm), check_existing=True)
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

    def quad(self, p0, p1, p2, p3, uvs, m):
        n = len(self.v)
        self.v += [p0, p1, p2, p3]
        self.f.append((n, n + 1, n + 2, n + 3))
        self.uv.append(uvs)
        self.mi.append(m)

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

    def make(self, name, mats):
        for o in list(bpy.data.objects):
            if o.name == name:
                bpy.data.objects.remove(o, do_unlink=True)
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
    for sc in bpy.data.scenes:
        for o in sc.objects:
            o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    p = os.path.join(OUT, fname)
    bpy.ops.export_scene.gltf(filepath=p, export_format='GLTF_SEPARATE',
                              use_selection=True, export_texture_dir='tex',
                              export_yup=True, export_apply=True)
    print("exported", p)


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
    def baseboard(b, x0, x1):
        b.box(((x0 + x1) / 2, -0.02, 0.07), (x1 - x0, 0.05, 0.14), 1, 0.5)

    b = Build()
    b.wallquad(-H, H, 0.0, WALLH, 0)
    baseboard(b, -H, H)
    export(b.make("jx_wall", [M_WALL, M_PAINT]), "wall.gltf")

    # ---- 開口付きの壁 + ケーシング(枠の飾り) ----
    b = Build()
    dw = DOORW / 2
    b.wallquad(-H, -dw, 0.0, WALLH, 0)          # 左
    b.wallquad(dw, H, 0.0, WALLH, 0)            # 右
    b.wallquad(-dw, dw, DOORH, WALLH, 0)        # まぐさ
    baseboard(b, -H, -dw); baseboard(b, dw, H)
    cw, cd = 0.13, 0.045                        # ケーシングの幅/出っ張り
    b.box((-dw - cw / 2, -cd / 2, (DOORH + cw) / 2), (cw, cd, DOORH + cw), 1, 0.5)
    b.box((dw + cw / 2, -cd / 2, (DOORH + cw) / 2), (cw, cd, DOORH + cw), 1, 0.5)
    b.box((0.0, -cd / 2, DOORH + cw / 2), (DOORW, cd, cw), 1, 0.5)
    export(b.make("jx_wall_door", [M_WALL, M_PAINT]), "wall_door.gltf")

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


build_all()
