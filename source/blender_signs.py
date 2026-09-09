# -*- coding: utf-8 -*-
"""第1幕「入口の廊下」に貼る【文字の無い案内板】の額縁を Blender で組む。

    書き出し先: assets/models/props/sign_guide.gltf (+ .bin)
    実行:       source/run_signs.py を Blender から回す(BlenderMCP なら execute_blender_code)

★何を作るか:
    壁から 3cm 浮いた金属の額縁と、四隅の留め具だけ。
    【絵そのものは作らない】。絵は source/ui_icons/svg_signs/*.svg を焼いた
    assets/ui/signs/*.png で、gen_liminal.py 側が薄い箱に貼って
    この額縁の開口へ落とし込む。額縁と絵を分けてあるので、
    絵を描き直しても Blender を開き直さなくてよい。

★寸法(エンジン座標。原点 = 壁の面の中心、-Z が廊下側 = 見る側):
        開口      0.98 x 0.64      … 絵の板(1.00 x 0.66)を 1cm ずつ噛む
        外形      1.12 x 0.78
        奥行き    0 〜 -0.088      … スペーサ 3cm + 額縁 4.5cm + 留め具 1.3cm
    gen_liminal.py 側の A_sign* と【必ず一致】させること。片方だけ変えると
    絵が額縁からはみ出すか、隙間から壁が見える。

★向き: 額縁は -Z を向いて建てる。壁へ貼る時は箱の -Z 面を回す既存の作法
    (source/gen_liminal.py の exit_sign_x)と同じで、
        東の壁(x=+1.5, 面は -X を向く) … yaw = +90
        西の壁(x=-1.5, 面は +X を向く) … yaw = -90
    絵の板の回し方と揃っていないと、絵だけ裏を向く。

★エンジンは baseColorFactor を読まない = 単色マテリアルは真っ白。
    必ず col テクスチャを貼る(ここでは lm_metal_col.png)。

★この作品は「誰も居ない建物」なので、額縁は【派手にしない】。
    面取りも装飾も入れず、事務用品のように角張らせる。
"""
import os, re, shutil, tempfile

import bpy  # noqa: F401  (Blender の中でだけ動く)

# 道具は blender_kit.py の名前空間から借りる(Build / mat / make / E / TEXSRC)。
# run_signs.py が先に exec しているので、ここでは globals() に居るはず。
Build = globals()["Build"]
mat = globals()["mat"]
OUT = globals()["OUT"]


def export_sign(ob, fname, sub="props"):
    """blender_kit.export() と同じ手順。ただし置き場所を引数で決める。

    ★blender_kit.dest_of() は知らない名前で例外を投げる作りなので、
      あちらを書き換えずに済むよう、ここへ写してある(手順は 1 行も変えていない)。
    ★書き出しは一旦 temp へ。エクスポータは export_texture_dir の PNG を
      勝手に再エンコードして上書きするので、assets/models/tex を直接指すと
      gen_liminal_tex.py が描いたテクスチャが焼き直されてしまう。
    """
    for sc in bpy.data.scenes:
        for o in sc.objects:
            o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    tmp = os.path.join(tempfile.gettempdir(), "jx_export_signs")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    bpy.ops.export_scene.gltf(filepath=os.path.join(tmp, fname),
                              export_format='GLTF_SEPARATE',
                              use_selection=True, export_texture_dir='tex',
                              export_yup=True, export_apply=True)
    stem = fname[:-5]
    dstdir = os.path.join(OUT, *sub.split("/"))
    os.makedirs(dstdir, exist_ok=True)
    up = "../" * (sub.count("/") + 1)          # props/ から assets/models/tex/ まで
    for ext in (".gltf", ".bin"):
        src = os.path.join(tmp, stem + ext)
        if not os.path.exists(src):
            continue
        dst = os.path.join(dstdir, stem + ext)
        if ext == ".gltf":
            with open(src, encoding="utf-8") as f:
                txt = f.read()
            txt = re.sub(r'("uri"\s*:\s*")tex/', r"\g<1>" + up + "tex/", txt)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(txt)
        else:
            shutil.copyfile(src, dst)
    print("exported", os.path.join(dstdir, fname))


# ---------------------------------------------------------------- 寸法
OPEN_W, OPEN_H = 0.98, 0.64        # 開口(絵の板 1.00x0.66 を 1cm ずつ噛む)
OUT_W,  OUT_H = 1.12, 0.78         # 外形
GAP = 0.030                        # 壁から額縁の裏までの隙間(浮かせる量)
BEZ = 0.045                        # 額縁そのものの厚み
CAP = 0.013                        # 留め具の頭の出


def build_sign_guide():
    b = Build()
    M = [mat("jx_signmetal", "lm_metal_col.png", rough=0.45, metal=0.55)]

    z0 = -GAP                       # 額縁の裏
    z1 = -(GAP + BEZ)               # 額縁の表
    zc = (z0 + z1) / 2

    tb = (OUT_H - OPEN_H) / 2       # 上下の桟の幅 0.07
    sb = (OUT_W - OPEN_W) / 2       # 左右の桟の幅 0.07

    # 上下の桟は全幅。左右の桟は開口の高さぶんだけ(角で二重にしない)
    for sgn in (+1, -1):
        b.ebox((0.0, sgn * (OPEN_H / 2 + tb / 2), zc), (OUT_W, tb, BEZ), 0)
        b.ebox((sgn * (OPEN_W / 2 + sb / 2), 0.0, zc), (sb, OPEN_H, BEZ), 0)

    # 壁と額縁の間のスペーサ(四隅)。壁の中へ 1cm 潜らせて継ぎ目を消す
    for sx in (+1, -1):
        for sy in (+1, -1):
            b.ebox((sx * (OPEN_W / 2 - 0.01), sy * (OPEN_H / 2 - 0.01), -GAP / 2 + 0.005),
                   (0.055, 0.055, GAP + 0.010), 0)

    # 四隅の留め具(丸頭)。額縁の表からわずかに出る
    for sx in (+1, -1):
        for sy in (+1, -1):
            b.etube([(0.0, 0.021), (CAP, 0.021)], 0, axis="z",
                    origin=(sx * (OUT_W / 2 - sb / 2), sy * (OUT_H / 2 - tb / 2), z1 - CAP),
                    seg=10)

    export_sign(b.make("jx_sign_guide", M), "sign_guide.gltf")


def build_signs():
    build_sign_guide()
    print("SIGNS DONE")
