# -*- coding: utf-8 -*-
"""v13「観測が世界を確定させる」の部品。★blender_kit.py の名前空間で exec される前提
(Build / mat / export / math / E がそこから来る)。単体では動かない。

★原点の規約(docs/V13.md §5 と一致。ここを間違えると gen_stages.py の座標が全部ずれる):
  ・lockplate  … 原点 = 【床の中心】。+Z を向く(= 門の枠と同じ向き)。落ちる = 解放
  ・falls      … 原点 = 【床の中心】。+Z を向く。y は 0..6、x は -6..+6
  ・fallsrail  … 原点 = 【左端の柱の足元】。+X へ 12m(cable と同じ流儀)
  ・redpanel   … 原点 = 【床の中心】。+Z を向く。y は 0..3.6、x は -3.2..+3.2
  ・redmark_*  … 原点 = 【印の中心】。+Z を向く。redpanel の前 0.10 くらいに置く
  ・busplug    … 原点 = 【握り】。+Z が挿す向き。z は -0.35(ケーブル) .. +0.55(ピン先)
  ・bussocket_*… 原点 = 【面の中心】。+Z を向く。本体は原点より奥(-Z)

★寸法の物差し(既存): ベンチ 0.95 / ドラム缶 0.88 / ロッカー 1.95 / 棚 2.40 /
  継電器 1.45 / 配電盤 4.6x2.82。新しい物もこの中に収める。

★falls だけは【メッシュ全体が 1 マテリアル・1 UV 系】でなければならない。
  scene:setMeshUvScroll はメッシュ単位で UV をずらすので、枠や庇を同じメッシュに
  入れると【枠まで流れる】。だから falls は樋の水面そのものだけ。手すり(fallsrail)と
  周りの造作は別モデルに切ってある。
  V は 1m = 1タイル ちょうど(高さ 6m = 6 タイル)。整数でないと巻き戻りで縞が飛ぶ。
"""


def build_v13():
    M_METAL = mat("jx_metal", "metal_col.png", 0.45, 0.6)
    M_PAINT = mat("jx_paint", "paint_col.png", 0.55)
    M_DARK = mat("jx_dark", "dark_col.png", 0.98)
    M_PLAIN = mat("jx_plain", "plain_col.png", 0.55)
    M_FALLS = mat("jx_falls", "falls_col.png", 0.24, 0.0)   # 濡れている = 粗さを落とす

    def ebar(b, a, c, w, z0, z1, m, k=0.5):
        """垂直面(エンジン XY)の中で【斜めに置ける】角材。ebox は軸並行しか作れないので、
        格子の筋交いと、差込口に彫る三角/十字の印のために要る。
        a,c=(x,y) の 2 点を結ぶ幅 w の板。奥行きは z0..z1。"""
        (ax, ay), (cx, cy) = a, c
        dx, dy = cx - ax, cy - ay
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return
        px, py = -dy / L * w * 0.5, dx / L * w * 0.5
        P = [(ax - px, ay - py), (cx - px, cy - py), (cx + px, cy + py), (ax + px, ay + py)]
        uv = lambda pts: [(p[0] * k, p[1] * k) for p in pts]
        fr = [(x, y, z1) for (x, y) in P]
        bk = [(x, y, z0) for (x, y) in P]
        b.eface(fr, uv(P), m)                       # 前(法線 +Z)
        b.eface(bk[::-1], uv(P[::-1]), m)           # 後
        for i in range(4):                          # 側面 4 枚
            j = (i + 1) % 4
            b.eface([bk[i], bk[j], fr[j], fr[i]],
                    [(0, z0 * k), (w * k, z0 * k), (w * k, z1 * k), (0, z1 * k)], m)

    # ======================= lockplate(錠) 2.4 x 3.2 =======================
    # ★未解放の門に【被さっている】重い鉄格子。原点 = 床の中心、+Z を向く。
    #   継電器が入ると Lua が落として消す = 「開いた」を文字なしで伝える唯一の合図。
    #   だから「取り外せる物」に見えないといけない → 蝶番と閂を必ず持たせる。
    W, H, T = 2.40, 3.20, 0.14
    b = Build()
    b.ebox((0.0, 0.07, 0.0), (W, 0.14, T + 0.06), 0, 1.0)                 # 下枠(床に当たる)
    b.ebox((0.0, H - 0.07, 0.0), (W, 0.14, T + 0.06), 0, 1.0)             # 上枠
    for sx in (-1, 1):
        b.ebox((sx * (W * 0.5 - 0.07), H * 0.5, 0.0), (0.14, H, T + 0.06), 0, 1.0)
    for i in range(5):                                                    # 縦の格子
        b.ebox((-0.80 + i * 0.40, H * 0.5, 0.0), (0.09, H - 0.28, 0.10), 0, 1.0)
    for gy in (0.72, 1.60, 2.48):                                         # 横の桟
        b.ebox((0.0, gy, 0.0), (W - 0.28, 0.10, 0.12), 1, 1.0)
        for i in range(5):                                                # 交点のリベット
            b.ebox((-0.80 + i * 0.40, gy, 0.075), (0.10, 0.10, 0.05), 0, 1.0)
    for sx in (-1, 1):                                                    # 筋交い(重さを出す)
        ebar(b, (sx * 0.94, 0.30), (0.0, 1.60), 0.085, -0.05, 0.03, 1)
        ebar(b, (sx * 0.94, 2.90), (0.0, 1.60), 0.085, -0.05, 0.03, 1)
    for hy in (0.46, 1.60, 2.74):                                         # 蝶番(左端)
        b.ebox((-W * 0.5 - 0.04, hy, 0.0), (0.22, 0.34, 0.16), 0, 1.0)
        b.etube([(hy - 0.20, 0.075), (hy + 0.20, 0.075)], 0, axis="y",
                origin=(-W * 0.5 - 0.13, 0.0, 0.0), seg=10)
    b.ebox((0.06, 1.34, 0.13), (W + 0.22, 0.17, 0.17), 0, 1.0)            # 閂(横に貫く)
    b.ebox((W * 0.5 + 0.02, 1.34, 0.13), (0.26, 0.30, 0.26), 1, 1.0)      # 受け(右)
    b.ebox((-W * 0.5 - 0.02, 1.34, 0.13), (0.26, 0.30, 0.26), 1, 1.0)     # 受け(左)
    b.ebox((0.62, 1.34, 0.21), (0.34, 0.42, 0.16), 0, 1.0)                # 錠前の箱
    b.etube([(0.21, 0.055), (0.27, 0.055)], 0, axis="z",
            origin=(0.62, 1.34, 0.0), seg=12)                             # 鍵穴の座
    b.ebox((0.0, 2.04, 0.13), (0.72, 0.16, 0.04), 3, 1.0)                 # 銘板
    export(b.make("jx_lockplate", [M_METAL, M_PAINT, M_DARK, M_PLAIN]), "lockplate.gltf")

    # ======================= falls(滝の樋) 幅 12 x 高 6 =======================
    # ★1 マテリアル・1 UV 系だけ(冒頭の注意)。UV は u = 2m/タイル、v = 1m/タイル。
    #   面は平らではなく【樋】: 中央がへこみ、両端が手前へ反り返る。こうすると
    #   同じ縞でも中央と端で明るさが変わり、縞が「面」ではなく「流れ」に見える。
    FW, FH, NX, NY = 12.0, 6.0, 16, 20
    b = Build()

    def fz(x, y):
        t = x / (FW * 0.5)
        curl = max(0.0, abs(t) - 0.84)
        return (-0.34 * t * t + 12.0 * curl * curl        # 樋のへこみ + 端の反り
                + 0.028 * math.sin(y * 2.3 + x * 0.62))   # 水面のうねり

    for i in range(NX):
        x0 = -FW * 0.5 + FW * i / NX
        x1 = -FW * 0.5 + FW * (i + 1) / NX
        for j in range(NY):
            y0 = FH * j / NY
            y1 = FH * (j + 1) / NY
            b.eface([(x0, y0, fz(x0, y0)), (x1, y0, fz(x1, y0)),
                     (x1, y1, fz(x1, y1)), (x0, y1, fz(x0, y1))],
                    [(x0 * 0.5, y0), (x1 * 0.5, y0), (x1 * 0.5, y1), (x0 * 0.5, y1)], 0)
    export(b.make("jx_falls", [M_FALLS]), "falls.gltf")

    # ======================= fallsrail(手すり) 長 12 =======================
    # ★原点 = 【左端の柱の足元】。+X へ 12m(cable と同じ流儀)。
    #   仕事は「ここで立ち止まって滝を見ろ」を体で言う事。だから腰の高さ(1.06)で、
    #   越えられない = 進めない事も同時に伝える。
    RL, RH = 12.0, 1.06
    b = Build()
    b.etube([(0.0, 0.048), (RL, 0.048)], 0, axis="x", origin=(0, RH, 0), seg=12)
    b.etube([(0.0, 0.036), (RL, 0.036)], 0, axis="x", origin=(0, RH - 0.44, 0), seg=10)
    b.ebox((RL * 0.5, 0.12, 0.0), (RL, 0.20, 0.035), 1, 1.0)              # 幅木
    for i in range(9):
        x = RL * i / 8.0
        b.etube([(0.0, 0.052), (RH, 0.052)], 0, axis="y", origin=(x, 0, 0), seg=10)
        b.ebox((x, 0.02, 0.0), (0.26, 0.04, 0.26), 1, 1.0)                # 台座
        for sz in (-1, 1):
            b.ebox((x, 0.045, sz * 0.09), (0.07, 0.05, 0.07), 0, 1.0)     # アンカーボルト
        b.ebox((x, RH, 0.0), (0.12, 0.06, 0.12), 0, 1.0)                  # 柱頭の座
    for x in (0.0, RL):                                                    # 端の返し
        b.etube([(RH - 0.30, 0.048), (RH, 0.048)], 0, axis="y", origin=(x, 0, 0), seg=12)
    export(b.make("jx_fallsrail", [M_METAL, M_PAINT]), "fallsrail.gltf")

    # ======================= redpanel(赤面) 6.4 x 3.6 =======================
    # ★原点 = 床の中心。板は plain(白)で作る = 実行時 scene:setColor で
    #   (0.86,0.05,0.05) に塗り、20 秒後に白へ戻す。塗り分けはエンジン側の仕事なので
    #   モデルは【素の白い大面 + 金属の枠】だけ。印は別オブジェクト(redmark_*)。
    PW, PH = 6.40, 3.60
    b = Build()
    b.ebox((0.0, PH * 0.5, 0.0), (PW, PH, 0.12), 0, 0.25)                 # 発光面(白)
    for sy in (0.08, PH - 0.08):                                          # 枠(上下)
        b.ebox((0.0, sy, 0.02), (PW + 0.24, 0.16, 0.22), 1, 1.0)
    for sx in (-1, 1):                                                    # 枠(左右)
        # ★下は床(y=0)で止める。中心に置くと 0.12 だけ床へめり込む
        b.ebox((sx * (PW * 0.5 + 0.04), (PH + 0.12) * 0.5, 0.02),
               (0.16, PH + 0.12, 0.22), 1, 1.0)
        b.ebox((sx * (PW * 0.5 + 0.04), PH * 0.5, -0.16), (0.14, PH - 0.60, 0.24), 1, 1.0)
        b.etube([(0.30, 0.06), (PH - 0.30, 0.06)], 1, axis="y",
                origin=(sx * (PW * 0.5 + 0.16), 0.0, -0.10), seg=10)      # 側面の電線管
        for sy2 in (0.60, PH - 0.60):                                     # 壁への腕
            b.ebox((sx * (PW * 0.5 - 0.30), sy2, -0.24), (0.70, 0.14, 0.30), 1, 1.0)
        b.ebox((sx * (PW * 0.5 - 0.40), 0.05, -0.10), (0.50, 0.10, 0.44), 1, 1.0)  # 足
    export(b.make("jx_redpanel", [M_PLAIN, M_METAL]), "redpanel.gltf")

    # ======================= redmark_*(赤面に抜く印) 0.9 =======================
    # ★原点 = 印の中心。redpanel の前 0.10 くらいに置く。dark(炭)で作ってあるので
    #   そのままで【黒く抜けている】ように見える。scene:setColor で個別に塗り替えられる。
    #   Fin_M0 / Fin_M1 / Fin_M2 の 3 体に、丸/三角/十字のどれかを割り当てて使う。
    MS, MT = 0.45, 0.03                                # 半径 0.45 / 厚み 0.03
    b = Build()
    b.etube([(-MT, MS), (MT, MS)], 0, axis="z", origin=(0, 0, 0), seg=32)
    export(b.make("jx_redmark_circle", [M_DARK]), "redmark_circle.gltf")

    b = Build()
    # ★頂点は【+Z から見て CCW】に並べる(左下 -> 右下 -> 上)。逆にすると裏返る
    V = [(-MS * 0.866, -MS * 0.5), (MS * 0.866, -MS * 0.5), (0.0, MS)]
    b.eface([(V[0][0], V[0][1], MT), (V[1][0], V[1][1], MT), (V[2][0], V[2][1], MT)],
            [(0.0, 0.0), (0.5, 0.0), (0.25, 0.5)], 0)                     # 前(法線 +Z)
    b.eface([(V[2][0], V[2][1], -MT), (V[1][0], V[1][1], -MT), (V[0][0], V[0][1], -MT)],
            [(0.25, 0.5), (0.5, 0.0), (0.0, 0.0)], 0)                     # 後
    for i in range(3):                                                    # 側面
        (x0, y0), (x1, y1) = V[i], V[(i + 1) % 3]
        b.eface([(x0, y0, -MT), (x1, y1, -MT), (x1, y1, MT), (x0, y0, MT)],
                [(0, 0), (1, 0), (1, 1), (0, 1)], 0)
    export(b.make("jx_redmark_triangle", [M_DARK]), "redmark_triangle.gltf")

    # 十字。★同一平面に重なる面を作ると z ファイティングするので、
    #   縦 1 本 + 左右 2 本に割って【重ねない】。
    b = Build()
    CW = 0.26
    b.ebox((0.0, 0.0, 0.0), (CW, MS * 2, MT * 2), 0, 1.0)
    for sx in (-1, 1):
        b.ebox((sx * (CW * 0.5 + (MS - CW * 0.5) * 0.5), 0.0, 0.0),
               (MS - CW * 0.5, CW, MT * 2), 0, 1.0)
    export(b.make("jx_redmark_cross", [M_DARK]), "redmark_cross.gltf")

    # ======================= busplug(プラグ) 長 0.9 =======================
    # ★原点 = 【握り】。+Z が挿す向き。z = -0.35(ケーブルの端) .. +0.55(ピンの先) = 0.90。
    #   差込口の内径 0.30 に対して胴が 0.26 = 「入る」が目で分かる太さ。
    b = Build()
    b.etube([(-0.35, 0.055), (-0.27, 0.075), (-0.23, 0.075)], 0, axis="z",
            origin=(0, 0, 0), seg=14)                                     # ケーブル
    b.etube([(-0.23, 0.090), (-0.20, 0.105)], 1, axis="z", origin=(0, 0, 0), seg=14)
    b.etube([(-0.20, 0.115), (-0.06, 0.130), (0.06, 0.130), (0.13, 0.118)], 1,
            axis="z", origin=(0, 0, 0), seg=18)                           # 握り(ゴム)
    for zz in (-0.14, -0.07, 0.0, 0.07):                                  # 滑り止めの畝
        b.etube([(zz - 0.012, 0.138), (zz + 0.012, 0.138)], 1, axis="z",
                origin=(0, 0, 0), seg=18)
    b.etube([(0.13, 0.148), (0.17, 0.148)], 2, axis="z", origin=(0, 0, 0), seg=18)  # 鍔
    b.etube([(0.17, 0.130), (0.44, 0.130), (0.46, 0.118)], 2, axis="z",
            origin=(0, 0, 0), seg=18)                                     # 胴(金属)
    b.ebox((0.0, 0.138, 0.30), (0.06, 0.05, 0.24), 2, 1.0)                # 誤挿し止めの鍵
    for i in range(3):                                                    # ピン 3 本
        a = 2 * math.pi * i / 3 + math.pi * 0.5
        b.etube([(0.46, 0.024), (0.53, 0.024), (0.55, 0.0)], 2, axis="z",
                origin=(math.cos(a) * 0.062, math.sin(a) * 0.062, 0.0), seg=10)
    export(b.make("jx_busplug", [M_DARK, M_PAINT, M_METAL]), "busplug.gltf")

    # ======================= bussocket_*(差込口) 直径 0.7 =======================
    # ★原点 = 【面の中心】(z=0 が鍔の前面)。本体は原点より奥(-Z)へ 0.30。
    #   3 つ並べ、印(丸/三角/十字)を鍔に彫る。プラグを挿すと隠れない位置 =
    #   内径(r=0.15)の【外側】に印を置く。補色残像で読んだ形と照合する物なので、
    #   暗い部屋でも輪郭だけで判別できる形にしてある。
    def socket(mark, fname):
        b = Build()
        b.etube([(-0.30, 0.0), (-0.30, 0.30), (-0.07, 0.30), (-0.07, 0.35),
                 (0.0, 0.35), (0.0, 0.15), (-0.26, 0.15), (-0.26, 0.0)], 0,
                axis="z", origin=(0, 0, 0), seg=28)                       # 鍔 + 穴
        b.etube([(-0.26, 0.0), (-0.26, 0.13)], 1, axis="z", origin=(0, 0, 0), seg=20)
        for i in range(4):                                                # 取り付けボルト
            a = 2 * math.pi * i / 4 + math.pi * 0.25
            b.etube([(0.0, 0.030), (0.022, 0.030)], 0, axis="z",
                    origin=(math.cos(a) * 0.295, math.sin(a) * 0.295, 0.0), seg=8)
        b.etube([(-0.34, 0.075), (-0.30, 0.075)], 0, axis="z", origin=(0, 0, 0), seg=10)
        if mark == "circle":
            b.etube([(0.0, 0.235), (0.012, 0.242), (0.012, 0.292), (0.0, 0.30)], 2,
                    axis="z", origin=(0, 0, 0), seg=28)
        elif mark == "triangle":
            P = [(math.cos(2 * math.pi * i / 3 + math.pi * 0.5) * 0.29,
                  math.sin(2 * math.pi * i / 3 + math.pi * 0.5) * 0.29) for i in range(3)]
            for i in range(3):
                ebar(b, P[i], P[(i + 1) % 3], 0.052, 0.0, 0.012, 2)
        else:                                                             # cross
            for i in range(4):
                a = math.pi * 0.5 * i
                ebar(b, (math.cos(a) * 0.19, math.sin(a) * 0.19),
                     (math.cos(a) * 0.31, math.sin(a) * 0.31), 0.052, 0.0, 0.012, 2)
        export(b.make("jx_bussocket_" + mark, [M_METAL, M_DARK, M_PAINT]), fname)

    socket("circle", "bussocket_circle.gltf")
    socket("triangle", "bussocket_triangle.gltf")
    socket("cross", "bussocket_cross.gltf")
