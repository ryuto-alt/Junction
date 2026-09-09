# -*- coding: utf-8 -*-
"""第三幕「立坑」の部品。★blender_kit.py の名前空間で exec される前提
(Build / mat / export / math / E がそこから来る)。単体では動かない。

第三幕は小部屋 6 個をやめて、58 x 44m・深さ 28m の【立坑 1 本】に作り替える。
その中心に立っているのが回転ドラム。箱プリミティブでは絶対に作れない形なので、
ここだけモデルにする(この作品は原則「テクスチャを貼った箱」で組んである)。

★原点の規約(ここを間違えると gen_liminal.py の座標が全部ずれる):
  ・sh_drum   … 原点 = 【底面の中心】。+Y へ 16.0m。半径 7.0m
                 縦リブ 24 本が【回転の位相を読ませる】唯一の手がかりなので、
                 リブは深く(0.30m)・影が出る角度で付ける
  ・sh_col    … 原点 = 【底面の中心】。水から生える柱。頭は平ら(足場になる)
  ・sh_canopy … 原点 = 【壁に付く面の下端の中心】。+Z へ 5.0m 張り出す片持ちの庇

★寸法の物差し(既存): ベンチ 0.95 / ドラム缶 0.88 / ロッカー 1.95 / 棚 2.40。
  立坑の部品はこの 10 倍の世界なので、【人の寸法の物】を必ず 1 つ添えること
  (庇の手すり 1.10 / 柱の頭の縁 0.12)。これが無いと巨大さが読めない。
"""


def build_shaft():
    M_METAL = mat("jx_metal", "metal_col.png", 0.45, 0.6)
    M_CONC = mat("jx_conc", "concrete_col.png", 0.92, 0.0, "concrete_nrm.png")
    M_DARK = mat("jx_dark", "dark_col.png", 0.98)
    K = 0.5

    def ring(r, y, i, n):
        a = 2.0 * math.pi * i / n
        return E(r * math.cos(a), y, r * math.sin(a))

    def band(b, r, y0, y1, n, m, uo=0.0, skip=None, inward=False):
        """半径 r の筒の側面。skip=(i0,i1) の区間は開ける(スリット)。
        inward=True で法線を内向きにする(中を見せる筒に要る)。

        ★skip は【区間のリスト】も受ける: skip=[(0,6), (28,34)] で 2 本開く。
          2026-09-09、回る筒の判定を「時間の窓」から「空間の窓」へ変えたのに伴い、
          スリットを 180 度対称に 2 本開けるために足した。
          どちらか一方が常にこちらを向くので、筒は回っているのに
          中の破片はいつでも覗ける ＝ 立ち位置を直した結果が即座に分かる。"""
        cuts = skip if (skip and isinstance(skip[0], (tuple, list))) else ([skip] if skip else [])
        for i in range(n):
            if any(c[0] <= i < c[1] for c in cuts):
                continue
            j = (i + 1) % n
            u0 = (2.0 * math.pi * r * i / n) * K + uo
            u1 = (2.0 * math.pi * r * (i + 1) / n) * K + uo
            q = [ring(r, y0, i, n), ring(r, y0, j, n), ring(r, y1, j, n), ring(r, y1, i, n)]
            uv = [(u0, y0 * K), (u1, y0 * K), (u1, y1 * K), (u0, y1 * K)]
            if inward:
                q = q[::-1]; uv = uv[::-1]
            b.face(q, uv, m)

    def cap(b, r, y, n, m, up=True):
        """円板(上向き or 下向き)。三角扇。"""
        c = E(0.0, y, 0.0)
        for i in range(n):
            j = (i + 1) % n
            p0, p1 = ring(r, y, i, n), ring(r, y, j, n)
            a0 = 2.0 * math.pi * i / n
            a1 = 2.0 * math.pi * j / n
            u0 = (r * math.cos(a0) * K, r * math.sin(a0) * K)
            u1 = (r * math.cos(a1) * K, r * math.sin(a1) * K)
            tri = [c, p0, p1] if up else [c, p1, p0]
            uvs = [(0.0, 0.0), u0, u1] if up else [(0.0, 0.0), u1, u0]
            b.face(tri, uvs, m)

    def radial_box(b, ang, r0, r1, y0, y1, half_w, m):
        """筒の外側へ突き出す角材(縦リブ)。ang は radian、half_w は接線方向の半幅。"""
        ca, sa = math.cos(ang), math.sin(ang)
        tx, tz = -sa, ca                     # 接線
        def P(r, y, s):
            return E(r * ca + tx * s, y, r * sa + tz * s)
        for (s0, s1) in ((-half_w, half_w),):
            # 外面
            b.face([P(r1, y0, s0), P(r1, y0, s1), P(r1, y1, s1), P(r1, y1, s0)],
                   [(0, y0 * K), (2 * half_w * K, y0 * K),
                    (2 * half_w * K, y1 * K), (0, y1 * K)], m)
            # 側面 2 枚
            b.face([P(r0, y0, s1), P(r1, y0, s1), P(r1, y1, s1), P(r0, y1, s1)],
                   [(0, y0 * K), ((r1 - r0) * K, y0 * K),
                    ((r1 - r0) * K, y1 * K), (0, y1 * K)], m)
            b.face([P(r1, y0, s0), P(r0, y0, s0), P(r0, y1, s0), P(r1, y1, s0)],
                   [(0, y0 * K), ((r1 - r0) * K, y0 * K),
                    ((r1 - r0) * K, y1 * K), (0, y1 * K)], m)
            # 上下の口
            b.face([P(r0, y1, s0), P(r0, y1, s1), P(r1, y1, s1), P(r1, y1, s0)],
                   [(0, 0), (2 * half_w * K, 0),
                    (2 * half_w * K, (r1 - r0) * K), (0, (r1 - r0) * K)], m)
            b.face([P(r1, y0, s0), P(r1, y0, s1), P(r0, y0, s1), P(r0, y0, s0)],
                   [(0, 0), (2 * half_w * K, 0),
                    (2 * half_w * K, (r1 - r0) * K), (0, (r1 - r0) * K)], m)

    # ======================= sh_drum  半径 7.0 x 高さ 16.0 =======================
    # ★リブが 24 本なのは【15 度ごと】だから。回転の位相を目で読ませるのがこの
    #   ドラムの唯一の仕事なので、本数は「数えられて、かつ細かすぎない」ことが要る。
    # ★スリット付きの【中空の筒】。一周に一度だけ中が見える ＝ 回転が仕掛けになる。
    #   SL0..SL1 の区間だけ壁もリブも帯も開ける。中を見せるので内側の面も張る。
    R, H, N, NR = 7.0, 16.0, 56, 24
    SL0, SL1 = 0, 6                                            # 6/56 = 38.6 度のスリット
    # ★180 度反対側にも同じ幅で 1 本。判定側(liminal_runtime.lua の throughSlot)も
    #   2 本前提で書いてある。絵と判定は必ず一致させること
    #   ── 以前 モデル 38.6 度 / 判定 34 度 とずれていて、
    #      「スリット越しに見えているのに繋がらない」帯が 1 周 0.13 秒あった。
    SLOTS = [(SL0, SL1), (SL0 + N // 2, SL1 + N // 2)]
    SLA0, SLA1 = 2.0 * math.pi * SL0 / N, 2.0 * math.pi * SL1 / N
    b = Build()
    band(b, R, 0.0, H, N, 1, skip=SLOTS)                  # 外壁(コンクリ)
    band(b, R - 0.34, 0.0, H, N, 1, skip=SLOTS, inward=True)   # 内壁(中が見える)
    cap(b, R, H, N, 0, up=True)                                # 天面(金属・足場になる)
    # スリットの小口(壁の厚みを見せる。無いと紙のように見える)
    for aa in (SLA0, SLA1):
        ca, sa = math.cos(aa), math.sin(aa)
        p0 = E(R * ca, 0.0, R * sa)
        p1 = E((R - 0.34) * ca, 0.0, (R - 0.34) * sa)
        p2 = E((R - 0.34) * ca, H, (R - 0.34) * sa)
        p3 = E(R * ca, H, R * sa)
        q = [(0, 0), (0.34 * K, 0), (0.34 * K, H * K), (0, H * K)]
        b.face([p0, p1, p2, p3] if aa == SLA0 else [p3, p2, p1, p0], q, 0)
    for i in range(NR):
        a = 2.0 * math.pi * i / NR
        if SLA0 - 0.05 <= a <= SLA1 + 0.05:
            continue                                           # スリットの前は開けておく
        radial_box(b, a, R - 0.05, R + 0.30, 0.35, H - 0.35, 0.22, 0)
    for y in (4.2, 8.4, 12.6):                                 # 水平の帯(高さを読ませる)
        band(b, R + 0.16, y, y + 0.42, N, 0, skip=SLOTS)
        cap(b, R + 0.16, y + 0.42, N, 0, up=True)
        cap(b, R + 0.16, y, N, 0, up=False)
    # 天面の縁(人の寸法の物 = 巨大さの物差し)
    band(b, R, H, H + 0.12, N, 0)
    cap(b, R, H + 0.12, N, 0, up=True)
    export(b.make("sh_drum", [M_METAL, M_CONC, M_DARK]), "sh_drum.gltf")

    # ======================= sh_col  水から生える柱 =======================
    # ★頭が平ら(足場)。原点 = 底面の中心。高さ 9.0 / 半径 1.15
    CR, CH, CN = 1.15, 9.0, 20
    b = Build()
    band(b, CR, 0.0, CH - 0.34, CN, 1)
    band(b, CR + 0.22, CH - 0.34, CH, CN, 0)                   # 頭の張り出し(柱頭)
    cap(b, CR + 0.22, CH, CN, 0, up=True)
    cap(b, CR + 0.22, CH - 0.34, CN, 0, up=False)
    for i in range(8):                                          # 縦の目地(高さが読める)
        radial_box(b, 2.0 * math.pi * i / 8, CR - 0.04, CR + 0.07, 0.2, CH - 0.5, 0.06, 2)
    export(b.make("sh_col", [M_METAL, M_CONC, M_DARK]), "sh_col.gltf")

    # ======================= sh_canopy  片持ちの庇 =======================
    # ★原点 = 壁に付く面の下端の中心。+Z へ 5.0m 張り出す。幅 6.0m
    #   手すり 1.10m を必ず付ける(これが無いと 5m なのか 50m なのか読めない)
    CW, CD, CT = 6.0, 5.0, 0.34
    b = Build()

    def slab(x0, x1, y0, y1, z0, z1, m):
        p = [E(x0, y0, z0), E(x1, y0, z0), E(x1, y1, z0), E(x0, y1, z0),
             E(x0, y0, z1), E(x1, y0, z1), E(x1, y1, z1), E(x0, y1, z1)]
        q = [(0, 0), ((x1 - x0) * K, 0), ((x1 - x0) * K, (y1 - y0) * K), (0, (y1 - y0) * K)]
        b.face([p[4], p[5], p[6], p[7]], q, m)                 # +Z
        b.face([p[1], p[0], p[3], p[2]], q, m)                 # -Z
        b.face([p[0], p[4], p[7], p[3]], q, m)                 # -X
        b.face([p[5], p[1], p[2], p[6]], q, m)                 # +X
        b.face([p[3], p[7], p[6], p[2]], q, m)                 # +Y
        b.face([p[0], p[1], p[5], p[4]], q, m)                 # -Y

    slab(-CW / 2, CW / 2, 0.0, CT, 0.0, CD, 1)                 # 踏面
    for sx in (-CW / 2 + 0.10, CW / 2 - 0.10):                 # 手すり(1.10m = 人の寸法)
        slab(sx - 0.05, sx + 0.05, CT, CT + 1.10, 0.0, 0.10, 0)
        slab(sx - 0.05, sx + 0.05, CT, CT + 1.10, CD - 0.10, CD, 0)
        slab(sx - 0.04, sx + 0.04, CT + 1.00, CT + 1.10, 0.0, CD, 0)
    def beam(a, c, w, h, m):
        """a→c を結ぶ角材。★斜材を「小さい箱を階段状に並べる」で作ってはいけない。
        実際にやったら、庇の下に瓦礫が散らばっているようにしか見えなかった。"""
        ax, ay, az = a
        cx, cy, cz = c
        dx, dy, dz = cx - ax, cy - ay, cz - az
        L = math.sqrt(dx * dx + dy * dy + dz * dz)
        ux, uy, uz = dx / L, dy / L, dz / L
        sx_, sy_, sz_ = -uz, 0.0, ux                       # u x (0,1,0)
        sl = math.sqrt(sx_ * sx_ + sz_ * sz_) or 1.0
        sx_, sz_ = sx_ / sl, sz_ / sl
        nx = sy_ * uz - sz_ * uy                            # s x u
        ny = sz_ * ux - sx_ * uz
        nz = sx_ * uy - sy_ * ux
        def P(t, ss, nn):
            return E(ax + dx * t + sx_ * ss + nx * nn,
                     ay + dy * t + sy_ * ss + ny * nn,
                     az + dz * t + sz_ * ss + nz * nn)
        q = [(0, 0), (w * K, 0), (w * K, L * K), (0, L * K)]
        A = [P(0, -w / 2, -h / 2), P(0, w / 2, -h / 2), P(0, w / 2, h / 2), P(0, -w / 2, h / 2)]
        B = [P(1, -w / 2, -h / 2), P(1, w / 2, -h / 2), P(1, w / 2, h / 2), P(1, -w / 2, h / 2)]
        for i in range(4):
            j = (i + 1) % 4
            b.face([A[i], A[j], B[j], B[i]], q, m)
        b.face([A[3], A[2], A[1], A[0]], q, m)
        b.face([B[0], B[1], B[2], B[3]], q, m)

    for sx in (-CW / 2 + 0.55, 0.0, CW / 2 - 0.55):            # 斜材(片持ちに見せる)
        beam((sx, 0.02, 0.30), (sx, -2.10, CD - 0.35), 0.24, 0.24, 0)
    export(b.make("sh_canopy", [M_METAL, M_CONC, M_DARK]), "sh_canopy.gltf")

    print("SHAFT_MODELS_OK")
