-- ============================================================================
-- JUNCTION / 継ぎ目 v5 — ゲームロジック本体。シーンに 1 つだけ置く空エンティティに付ける。
-- エンティティ名 "Logic_Stage_1" .. "Logic_Stage_8" でステージ設定を引く。契約書は docs/V5.md。
--
-- ★v5(2026-09-02 夜): 世界はひと続き。テレポートも覗き箱も無い。
--   継ぎ目 = 壁の中のトンネル。入口と出口の大きさが違い、中の【線】を越えると
--   向こう側の大きさになる。ここがやるのは:
--     1. 先細りの廊下の中で縮尺を連続的に変える(v6)。体(Body_0..4)は口の手前で入れ替える
--     2. 音も無い。廊下は自己相似なので変化は見えない
--     3. 溝に落ちたら直前の継ぎ目(か始点)に戻す
--     4. 出口の扉に触れたらクリア
--     5. 案内の光(hint 経路)・開幕カメラ・操作キーの表示
--
-- ★エンジンの地雷(README):
--   ・シーンを開いた時点で存在しない entity は描画されない → 実行時の物は JSON に置いて床下
--   ・CharacterController の寸法は実行時に変えられない → 大きさごとに Body_0..4
--   ・Play 直後に書いた transform は復元に上書きされる → 1 秒押し込む
-- ============================================================================

local STAGES = {
-- >>>STAGES (source/gen_stages.py が自動生成)
    ["Logic_Demo_1"] = { n = 1, scene = "scenes/stagedemo1.json", next = "scenes/stagedemo2.json",
        tunnels = {
            { id = "Z", ax = 2.200, az = 6.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 2.000, sb = 0.500, wa = 4.00, wb = 1.00, y0 = 0.00 },
            { id = "Q", ax = -1.000, az = 6.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 0.500, sb = 0.500, wa = 1.00, wb = 1.00, y0 = 0.00 },
            { id = "R", ax = -3.500, az = 6.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 0.500, sb = 0.500, wa = 1.00, wb = 1.00, y0 = 0.00 },
        },
        warps = {
        },
        morphs = {
        },
        plugs = {
        },
        ports = {
        },
        links = {
        },
        watchers = {
        },
        creeps = {
        },
        rolls = {
        },
        gates = {
        },
        pairs = {
        },
        plates = {
        },
        guide = {
        },
        marks = {
        },
        tilts = {
        },
        fovramps = {
        },
        breakers = {
        },
        power = nil,
        aligns = {
        },
        blinds = {
        },
        mirrors = {
        },
        turnts = {
        },
        dynprops = { { ent = "A_crate_2", off = 0.375 } },
        anchors = {
        },
        dolly = {
        },
        carries = {
        },
        sizegates = {
        },
        hint = { { 2.20, 4.80 }, { 2.20, 11.20 }, { 0.00, -1.00 }, { 0.00, -4.80 } },
        startScale = 1.000,
        start = "A", goalRoom = "A",
        spawn = { 2.0, 4.5, 180.0 }, teach = "walk",
        cine = {
            { 3.00, 2.40, 4.00, 0.00, 1.40, -4.80, 2.40 },
            { 2.00, 1.70, 4.50, 0.00, 1.20, -4.80, 1.60 },
            { 2.00, 1.70, 4.50, 2.00, 1.70, -3.50, 1.40 },
        } },
    ["Logic_Demo_2"] = { n = 2, scene = "scenes/stagedemo2.json", next = "scenes/stagedemo3.json",
        tunnels = {
            { id = "t1", ax = 0.000, az = 10.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 1.000, sb = 1.000, wa = 2.00, wb = 2.00, y0 = 0.00 },
            { id = "t2", ax = 10.000, az = 0.000, nx = 1.000, nz = 0.000, L = 4.00, sa = 1.000, sb = 0.500, wa = 2.00, wb = 1.00, y0 = 0.00 },
            { id = "t5", ax = -10.000, az = 5.000, nx = -1.000, nz = 0.000, L = 4.00, sa = 2.000, sb = 2.000, wa = 4.00, wb = 4.00, y0 = 0.00 },
            { id = "t3", ax = -10.000, az = 0.000, nx = -1.000, nz = 0.000, L = 4.00, sa = 0.500, sb = 2.000, wa = 1.00, wb = 4.00, y0 = 0.00 },
        },
        warps = {
        },
        morphs = {
        },
        plugs = {
        },
        ports = {
        },
        links = {
        },
        watchers = {
        },
        creeps = {
        },
        rolls = {
        },
        gates = {
        },
        pairs = {
        },
        plates = {
        },
        guide = {
        },
        marks = {
        },
        tilts = {
        },
        fovramps = {
        },
        breakers = {
        },
        power = nil,
        aligns = {
        },
        blinds = {
        },
        mirrors = {
        },
        turnts = {
        },
        dynprops = {  },
        anchors = {
            { ent = "Anchor_0", x = -7.000, z = 18.000, k = 0.550, d0 = 14.000 },
        },
        field = { axis = "x", a = 0.00, b = -9.00, s0 = 1.000, s1 = 0.500, x0 = -9.50, x1 = 0.50, z0 = 13.50, z1 = 22.50 },
        dolly = {
            { x = 0.000, z = -5.000, r = 5.50, fov = 52.0 },
        },
        carries = {
            { ent = "Carry_0", col = "CarryC_0", x = 3.000, z = 18.000, yaw = 0.0, h = 0.70 },
        },
        sizegates = {
        },
        hint = { { -8.80, 5.00 }, { -15.20, 0.00 }, { 0.00, -4.00 }, { 0.00, -8.00 } },
        startScale = 1.000,
        start = "H", goalRoom = "H",
        spawn = { 4.0, 3.0, 180.0 }, teach = "walk",
        cine = {
            { 4.00, 2.60, 5.00, -2.00, 1.40, -2.00, 2.40 },
            { 4.00, 1.70, 3.00, -2.00, 1.30, -2.00, 1.60 },
            { 4.00, 1.70, 3.00, 4.00, 1.70, -5.00, 1.40 },
        } },
    ["Logic_Demo_3"] = { n = 3, scene = "scenes/stagedemo3.json", next = nil,
        tunnels = {
        },
        warps = {
        },
        morphs = {
        },
        plugs = {
        },
        ports = {
        },
        links = {
        },
        watchers = {
        },
        creeps = {
        },
        rolls = {
        },
        gates = {
            { id = "m2", ent = "Gate_m2", mem = "GateM_m2", light = "GateL_m2", x = 12.000, z = -12.000, y0 = 0.00, nx = -1.000, nz = 0.000, alx = -0.000, alz = -1.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.240, cg = 0.820, cb = 1.000, hue = 0.530, needs = "" },
            { id = "g1", ent = "Gate_g1", mem = "GateM_g1", light = "GateL_g1", x = 28.000, z = -12.000, y0 = 0.00, nx = -1.000, nz = 0.000, alx = -0.000, alz = -1.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.240, cg = 0.820, cb = 1.000, hue = 0.530, needs = "" },
            { id = "m4", ent = "Gate_m4", mem = "GateM_m4", light = "GateL_m4", x = -12.000, z = -10.000, y0 = 0.00, nx = 1.000, nz = 0.000, alx = -0.000, alz = 1.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.320, cg = 1.000, cb = 0.480, hue = 0.350, needs = "" },
            { id = "d1", ent = "Gate_d1", mem = "GateM_d1", light = "GateL_d1", x = -28.000, z = -10.000, y0 = 0.00, nx = 1.000, nz = 0.000, alx = -0.000, alz = 1.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.320, cg = 1.000, cb = 0.480, hue = 0.350, needs = "" },
            { id = "m5", ent = "Gate_m5", mem = "GateM_m5", light = "GateL_m5", x = -8.000, z = -12.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 1.000, cg = 0.320, cb = 0.280, hue = 0.990, needs = "" },
            { id = "b1", ent = "Gate_b1", mem = "GateM_b1", light = "GateL_b1", x = -8.000, z = -27.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 1.000, cg = 0.320, cb = 0.280, hue = 0.990, needs = "" },
            { id = "g2", ent = "Gate_g2", mem = "GateM_g2", light = "GateL_g2", x = 36.000, z = -20.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.720, cg = 0.460, cb = 1.000, hue = 0.760, needs = "" },
            { id = "h1", ent = "Gate_h1", mem = "GateM_h1", light = "GateL_h1", x = 36.000, z = -30.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.720, cg = 0.460, cb = 1.000, hue = 0.760, needs = "" },
            { id = "d2", ent = "Gate_d2", mem = "GateM_d2", light = "GateL_d2", x = -46.000, z = -10.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 1.000, cg = 0.420, cb = 0.660, hue = 0.920, needs = "" },
            { id = "n2", ent = "Gate_n2", mem = "GateM_n2", light = "GateL_n2", x = -46.000, z = -33.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 1.000, cg = 0.420, cb = 0.660, hue = 0.920, needs = "" },
            { id = "t1", ent = "Gate_t1", mem = "GateM_t1", light = "GateL_t1", x = -37.000, z = -4.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.180, cg = 0.950, cb = 0.820, hue = 0.460, needs = "" },
            { id = "t2", ent = "Gate_t2", mem = "GateM_t2", light = "GateL_t2", x = -37.000, z = -22.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.180, cg = 0.950, cb = 0.820, hue = 0.460, needs = "" },
            { id = "m3", ent = "Gate_m3", mem = "GateM_m3", light = "GateL_m3", x = 8.000, z = -9.500, y0 = 0.00, nx = 0.000, nz = -1.000, alx = 1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.380, cg = 0.520, cb = 1.000, hue = 0.620, needs = "pw" },
            { id = "n1", ent = "Gate_n1", mem = "GateM_n1", light = "GateL_n1", x = 8.000, z = 12.000, y0 = 0.00, nx = 0.000, nz = -1.000, alx = 1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.380, cg = 0.520, cb = 1.000, hue = 0.620, needs = "pw" },
        },
        pairs = {
            { a = 1, b = 2, both = 1, needs = "" },
            { a = 3, b = 4, both = 1, needs = "" },
            { a = 5, b = 6, both = 1, needs = "" },
            { a = 7, b = 8, both = 1, needs = "" },
            { a = 9, b = 10, both = 1, needs = "" },
            { a = 11, b = 12, both = 1, needs = "" },
            { a = 13, b = 14, both = 1, needs = "pw" },
        },
        plates = {
            { id = "p1", ent = "Plate_p1", light = "PlateL_p1", x = 45.000, z = -3.000, y0 = 0.00, r = 1.30, pin = 1, cr = 1.000, cg = 0.450, cb = 0.200, watch = {  } },
            { id = "p2", ent = "Plate_p2", light = "PlateL_p2", x = 27.000, z = -21.000, y0 = 0.00, r = 1.30, pin = 1, cr = 1.000, cg = 0.450, cb = 0.200, watch = {  } },
            { id = "q1", ent = "Plate_q1", light = "PlateL_q1", x = -45.000, z = -50.000, y0 = 0.00, r = 1.45, pin = 0, cr = 1.000, cg = 0.450, cb = 0.200, watch = { "Mir_w1_b0" } },
            { id = "q2", ent = "Plate_q2", light = "PlateL_q2", x = -29.000, z = -50.000, y0 = 0.00, r = 1.45, pin = 0, cr = 1.000, cg = 0.450, cb = 0.200, watch = { "Mir_w1_b1" } },
        },
        guide = {
            { x = 12.00, z = -12.00, need = "cross:m2" },
            { x = 36.00, z = -1.00, need = "brk:k1" },
            { x = 36.00, z = -20.00, need = "cross:g2" },
            { x = 40.00, z = -44.60, need = "brk:k4" },
            { x = -12.00, z = -10.00, need = "cross:m4" },
            { x = -37.00, z = -2.00, need = "cross:t1" },
            { x = -41.50, z = -23.60, need = "brk:k2" },
            { x = -46.00, z = -8.00, need = "cross:d2" },
            { x = -37.00, z = -31.00, need = "brk:k5" },
            { x = -8.00, z = -12.00, need = "cross:m5" },
            { x = -11.00, z = -29.00, need = "align:a1" },
            { x = 13.00, z = -36.00, need = "brk:k3" },
            { x = 8.00, z = -11.00, need = "cross:m3" },
            { x = 0.00, z = 18.60, need = "" },
        },
        marks = {
            { ent = "MarkL_m2", light = "MarkLi_m2", x = 9.000, z = -12.000, cr = 0.240, cg = 0.820, cb = 1.000 },
            { ent = "MarkL_m3", light = "MarkLi_m3", x = 8.000, z = -12.500, cr = 0.380, cg = 0.520, cb = 1.000 },
        },
        tilts = {
            { x = 36.000, y = 0.000, z = -12.000, deg = 6.50, ents = { { "G_Floor", 36.000, -0.250, -12.000 }, { "G_FloorM", 36.000, 0.005, -12.000 }, { "G_TWall_0", 31.000, 0.375, -10.000 }, { "G_TWall_1", 41.000, 0.375, -14.000 }, { "G_TWall_2", 39.000, 0.375, -4.000 }, { "G_TWall_3", 33.000, 0.375, -20.000 }, { "G_locker_2", 25.400, 0.000, -1.400 }, { "G_bench_3", 46.600, 0.000, -22.600 }, { "Gate_g1", 28.000, 0.000, -12.000 }, { "GateB_g1", 28.000, 0.050, -12.000 }, { "GateM_g1", 28.000, 0.020, -12.000 }, { "GateL_g1", 28.500, 2.236, -12.000 }, { "Gate_g2", 36.000, 0.000, -20.000 }, { "GateB_g2", 36.000, 0.050, -20.000 }, { "GateM_g2", 36.000, 0.020, -20.000 }, { "GateL_g2", 36.000, 2.236, -20.500 }, { "Plate_p1", 45.000, 0.000, -3.000 }, { "PlateL_p1", 45.000, 0.500, -3.000 }, { "Plate_p2", 27.000, 0.000, -21.000 }, { "PlateL_p2", 27.000, 0.500, -21.000 }, { "Brk_k1", 36.000, 0.000, -1.000 }, { "BrkL_k1", 36.000, 1.310, -0.980 }, { "BrkP_k1", 36.000, 0.860, -1.245 }, { "BrkGL_k1", 36.000, 1.500, -1.900 } }, extra = {  } },
        },
        fovramps = {
            { axis = "z", a = -10.00, b = 10.00, f0 = 74.0, f1 = 54.0, x0 = -17.00, x1 = 17.00, z0 = -48.00, z1 = -24.00 },
        },
        breakers = {
            { id = "k1", ent = "Brk_k1", lever = "BrkL_k1", lamp = "BrkP_k1", light = "BrkGL_k1", x = 36.000, y = 0.000, z = -1.000, yaw = 180.0, cr = 0.240, cg = 0.820, cb = 1.000, needs = { "p1", "p2" } },
            { id = "k2", ent = "Brk_k2", lever = "BrkL_k2", lamp = "BrkP_k2", light = "BrkGL_k2", x = -41.500, y = 0.000, z = -23.600, yaw = 0.0, cr = 0.320, cg = 1.000, cb = 0.480, needs = {  } },
            { id = "k3", ent = "Brk_k3", lever = "BrkL_k3", lamp = "BrkP_k3", light = "BrkGL_k3", x = 13.000, y = 0.000, z = -36.000, yaw = 270.0, cr = 1.000, cg = 0.320, cb = 0.280, needs = {  } },
            { id = "k4", ent = "Brk_k4", lever = "BrkL_k4", lamp = "BrkP_k4", light = "BrkGL_k4", x = 40.000, y = 0.000, z = -44.600, yaw = 180.0, cr = 0.720, cg = 0.460, cb = 1.000, needs = {  } },
            { id = "k5", ent = "Brk_k5", lever = "BrkL_k5", lamp = "BrkP_k5", light = "BrkGL_k5", x = -37.000, y = 0.000, z = -31.000, yaw = 180.0, cr = 1.000, cg = 0.420, cb = 0.660, needs = { "q1", "q2" } },
        },
        power = { lamps = { "PwLamp1", "PwLamp2", "PwLamp3", "PwLamp4", "PwLamp5" }, light = "PwLight", x = -11.500, y = 0.000, z = 19.000, doors = { { ent = "ExitL", x = 1.995, y = 0.000, z = 19.600, dx = 4.085, dz = 0.000 }, { ent = "ExitR", x = -1.995, y = 0.000, z = 19.600, dx = -4.085, dz = -0.000 } } },
        aligns = {
            { id = "a1", ex = -11.000, ey = 1.700, ez = -29.000, tol = 3.00, hold = 0.50, bridge = "Bridge_a1", bx = 0.000, by = 0.020, bz = -36.000, segs = { { x0 = -9.800, x1 = -6.200, yb = 2.600, yt = 3.560, z = -33.200 }, { x0 = 0.200, x1 = 8.600, yb = 3.800, yt = 6.040, z = -38.800 }, { x0 = 0.900, x1 = 6.000, yb = 2.975, yt = 4.335, z = -34.950 } }, shards = { "Shard_a1_0", "Shard_a1_1", "Shard_a1_2" } },
        },
        blinds = {
            { ent = "Blind_s0", x = 35.000, z = -33.000, yUp = -0.560, yDn = -4.760, cone = 34.0, rng = 27.0 },
            { ent = "Blind_s1", x = 36.400, z = -34.800, yUp = -0.560, yDn = -4.760, cone = 34.0, rng = 27.0 },
            { ent = "Blind_s2", x = 38.200, z = -36.200, yUp = -0.560, yDn = -4.760, cone = 34.0, rng = 27.0 },
            { ent = "Blind_s3", x = 40.200, z = -37.400, yUp = -0.560, yDn = -4.760, cone = 34.0, rng = 27.0 },
            { ent = "Blind_s4", x = 42.200, z = -38.600, yUp = -0.560, yDn = -4.760, cone = 34.0, rng = 27.0 },
            { ent = "Blind_s5", x = 43.600, z = -40.400, yUp = -0.560, yDn = -4.760, cone = 34.0, rng = 27.0 },
            { ent = "Blind_s6", x = 43.200, z = -42.600, yUp = -0.560, yDn = -4.760, cone = 34.0, rng = 27.0 },
        },
        mirrors = {
            { id = "w1", axis = "z", c = -44.000, rows = { { a = "Mir_w1_a0", b = "Mir_w1_b0" }, { a = "Mir_w1_a1", b = "Mir_w1_b1" } }, mem = { "MirM_w1_0", "MirM_w1_1", "MirM_w1_2", "MirM_w1_3", "MirM_w1_4", "MirM_w1_5", "MirM_w1_6", "MirM_w1_7", "MirM_w1_8", "MirM_w1_9", "MirM_w1_10", "MirM_w1_11", "MirM_w1_12", "MirM_w1_13" } },
        },
        turnts = {
            { id = "r1", ent = "Turn_r1", gate = 12, x = -37.000, y = 0.000, z = -22.000, k = -1.00, base = 48.0, r = 2.20 },
        },
        dynprops = { { ent = "A_drum_2", off = 0.440 }, { ent = "A_drum_3", off = 0.440 }, { ent = "A_crate_7", off = 0.375 }, { ent = "A_drum_9", off = 0.440 }, { ent = "A_crate_10", off = 0.375 }, { ent = "A_drum_15", off = 0.440 }, { ent = "G_ball_0", off = 0.360 }, { ent = "G_ball_1", off = 0.360 }, { ent = "D_drum_2", off = 0.440 }, { ent = "D_drum_3", off = 0.440 }, { ent = "D_crate_4", off = 0.375 }, { ent = "D_crate_7", off = 0.375 }, { ent = "B_drum_3", off = 0.440 }, { ent = "B_crate_4", off = 0.375 }, { ent = "H_drum_4", off = 0.440 }, { ent = "H_crate_5", off = 0.375 }, { ent = "M_crate_4", off = 0.375 }, { ent = "Mir_w1_a0", off = 0.440 }, { ent = "Mir_w1_a1", off = 0.440 } },
        anchors = {
        },
        dolly = {
        },
        carries = {
        },
        sizegates = {
        },
        hint = { { 12.00, -12.00 } },
        startScale = 1.000,
        start = "A", goalRoom = "A",
        spawn = { 0.0, -18.0, 0.0 }, teach = nil,
        cine = {
            { 14.00, 9.00, -18.50, -4.00, 3.40, 18.00, 3.20 },
            { 0.00, 2.70, -18.60, 0.00, 2.60, 12.00, 1.80 },
            { 0.00, 1.70, -18.00, 0.00, 1.70, -10.00, 1.40 },
        } },
    -- <<<STAGES
}

local SCALES   = { 0.125, 0.25, 0.5, 1.0, 2.0 }
local BODY_H   = 1.8
local EYE_H    = 1.7
local HIDE_Y   = -200.0
local GROW_TIME = 0.35
local LIGHT_FADE = 3.0   -- ★照明の色が混ざりきるまでの秒数(背中側にある間だけ進む)
local FALL_Y   = -3.0
local C_KEY = { 0.95, 0.99, 0.94 }

local atan2 = math.atan2 or function(y, x) return math.atan(y, x) end

local function ent(name)
    local e = scene:findEntity(name)
    if e and e:isValid() then return e end
    return nil
end

local function hide(name)
    local e = ent(name)
    if e then
        local p = e.transform.position
        e.transform.position = Vec3.new(p.x, HIDE_Y, p.z)
    end
end

local function place(name, x, y, z, yaw, sx, sy, sz)
    local e = ent(name)
    if not e then return nil end
    e.transform.position = Vec3.new(x, y, z)
    if yaw then e.transform.rotation = Vec3.new(0, yaw, 0) end
    if sx then e.transform.scale = Vec3.new(sx, sy, sz) end
    return e
end

local function sfx(name, pitch, vol)
    pcall(function()
        if pitch then
            local id = audio:playSFXId("audio/ui/" .. name .. ".wav", false, vol or 1.0)
            if id then audio:setVoicePitch(id, pitch) end
        else
            audio:playSFX("audio/ui/" .. name .. ".wav")
        end
    end)
end

-- ---------------------------------------------------------------- 段階チュートリアル
local NEED = { move = 1, jump = 2 }
local function learned(n) return loadNum("jx_lv_" .. n, 0) >= (NEED[n] or 1) end
local function learn(n)
    if not learned(n) then saveNum("jx_lv_" .. n, loadNum("jx_lv_" .. n, 0) + 1) end
end

local function uiAnim(self, id, want, dt, speed)
    local a = self.ui[id] or 0
    a = a + ((want and 1 or 0) - a) * (1 - math.exp(-(speed or 9) * dt))
    if a < 0.002 then a = 0 elseif a > 0.998 then a = 1 end
    self.ui[id] = a
    return a
end

-- ---------------------------------------------------------------- 体の入れ替え
local function bodyIndexOf(s)
    for i, v in ipairs(SCALES) do if math.abs(v - s) < 1e-4 then return i - 1 end end
    return 3
end

local function useBody(self, s, x, z, hold, floorY)
    local idx = bodyIndexOf(s)
    floorY = floorY or 0.0
    for i = 0, #SCALES - 1 do
        local e = ent("Body_" .. i)
        if e then
            -- ★床の高さを足す。高い口(敷居 0.9)のトンネルの中で入れ替えると、床下に置いて落ちる
            local y = (i == idx) and (floorY + BODY_H * 0.5 * s + 0.02) or (HIDE_Y - i * 4)
            physics:setPosition(e, Vec3.new(x, y, z))
            e.transform.position = Vec3.new(x, y, z)
        end
    end
    self.scale = s
    self.bodyIdx = idx
    self.anchor = { x = x, z = z, y0 = floorY }
    -- ★Play 直後は CC が物理世界に未登録で setPosition が黙って効かない。押し込む
    self.placeT = hold or 1.0
    saveNum("bodyIdx", idx)
end

local function bodyEnt(self) return ent("Body_" .. (self.bodyIdx or 3)) end

local function bodyPos(self)
    local b = bodyEnt(self)
    if b then return b.transform.position end
    return Vec3.new(self.cfg.spawn[1], 0, self.cfg.spawn[2])
end

-- ---------------------------------------------------------------- カメラ演出
local function lookAt(px, py, pz, qx, qy, qz)
    local dx, dy, dz = qx - px, qy - py, qz - pz
    local yaw = math.deg(atan2(dx, dz))
    local pitch = math.deg(atan2(dy, math.sqrt(dx * dx + dz * dz)))
    return yaw, pitch
end

local function camApply(self)
    local pl = ent("MainCamera")
    if not pl then return end
    local c = self.cam
    pl.transform.position = Vec3.new(c.x, c.y, c.z)
    pl.transform.rotation = Vec3.new(-c.pitch, c.yaw, 0)
end

local function camSet(self, x, y, z, yaw, pitch)
    local c = self.cam
    c.x, c.y, c.z, c.yaw, c.pitch = x, y, z, yaw, pitch
    c.tx, c.ty, c.tz = nil, nil, nil
end

local function camSetAt(self, ex, ey, ez, tx, ty, tz)
    local c = self.cam
    c.x, c.y, c.z = ex, ey, ez
    c.tx, c.ty, c.tz = tx, ty, tz
    c.yaw, c.pitch = lookAt(ex, ey, ez, tx, ty, tz)
end

-- 動き出しだけ ease-in、最後だけ ease-out、間は等速(区間ごとに止めると「がく」になる)
local function shape(k, ein, eout)
    if ein and eout then return k * k * (3 - 2 * k) end
    if ein then return k * k end
    if eout then return 1 - (1 - k) * (1 - k) end
    return k
end

local function camGoTo(self, ex, ey, ez, tx, ty, tz, dur, ein, eout)
    local c = self.cam
    local sx, sy, sz = c.x, c.y, c.z
    local ox, oy, oz = c.tx or tx, c.ty or ty, c.tz or tz
    local t = 0
    while t < dur do
        t = t + time.dt()
        local k = shape(math.min(1, t / dur), ein, eout)
        camSetAt(self, sx + (ex - sx) * k, sy + (ey - sy) * k, sz + (ez - sz) * k,
                 ox + (tx - ox) * k, oy + (ty - oy) * k, oz + (tz - oz) * k)
        wait(0)
    end
    camSetAt(self, ex, ey, ez, tx, ty, tz)
end

local function cineBegin(self)
    self.cine = true; self.flash = 0; saveNum("cineLock", 1)
end

local function cineEnd(self)
    local c = self.cam
    c.tx, c.ty, c.tz = nil, nil, nil
    self.tpSeq = (self.tpSeq or 0) + 1
    saveNum("tpYaw", c.yaw); saveNum("tpPitch", 0); saveNum("tpSeq", self.tpSeq)
    saveNum("cineLock", 0)
    self.cine = false
    self.cool = 0.4
end

local function introCine(self)
    local sp = self.cfg.spawn
    cineBegin(self)
    local cine = self.cfg.cine
    self.task = task.spawn(function()
        if cine and #cine > 0 then
            local n = #cine
            for i, c in ipairs(cine) do
                if i == 1 then
                    camSetAt(self, c[1], c[2], c[3], c[4], c[5], c[6])
                    self.flash = 1.0
                    wait(c[7] or 1.5)
                else
                    camGoTo(self, c[1], c[2], c[3], c[4], c[5], c[6], c[7] or 2.0, i == 2, i == n)
                end
            end
        end
        cineEnd(self)
    end)
end

-- ---------------------------------------------------------------- 状態
local function resetRun(self)
    if self.task then task.cancel(self.task); self.task = nil end
    self.flash, self.cool = 0, 0.35
    self.ui = self.ui or {}
    self.walkT, self.noAct = 0, 0
    self.mode = "play"
    self.endSfx = false
    self.shownScale = self.cfg.startScale or 1.0
    self.side = {}
    self.hintIdx = 1
    self.warpLeft = {}
    for i, w in ipairs(self.cfg.warps or {}) do self.warpLeft[i] = w.loops end
    self.warpSide = {}
    self.warpIdx = {}
    self.sgSide = {}
    self.tunId, self.tunFrom, self.tunEnter = nil, nil, nil
    self.held, self.carryNear = nil, nil
    self.fovNow = self.fov0
    do local c = ent("MainCamera"); if c and self.fov0 then c:setFov(self.fov0) end end
    for _, c in ipairs(self.cfg.carries or {}) do    -- 運べる物を初期位置へ
        place(c.ent, c.x, 0.0, c.z, c.yaw)
        place(c.col, c.x, c.h * 0.5, c.z)
    end
    -- ---- v11: 枠 / 重量板 / 傾く床 / 動く剛体 / 案内 ----
    self.gLink, self.gStr, self.gShow, self.gFwd, self.gHold = {}, {}, {}, {}, {}
    self.bound, self.crossed = {}, {}
    self.gCool, self.warpT, self.warpFov, self.warpRoll = 0, 0, 0, 0
    self.gi, self.memNear, self.gBlock = 1, 0, 0
    self.inTilt, self.fxOn = false, false
    self.plateDone = {}
    -- ---- v12: 配電盤。継電器 5 台 -> 灯り 5 つ -> 出口の扉 ----
    self.brkOn, self.brkA = {}, {}
    self.alignDone, self.alignT, self.alignErr = {}, {}, {}
    self.blindY, self.doorK, self.pinned = {}, 0, {}
    -- ★動く剛体の「原点 -> コライダー中心」の高さ表。写しを置き直す時に要る。
    --   physics:setPosition は【コライダーの中心】を指すので、原点をそのまま渡すと埋まる。
    self.offOf = {}
    for _, dp in ipairs(self.cfg.dynprops or {}) do self.offOf[dp.ent] = dp.off end
    for _, bk in ipairs(self.cfg.breakers or {}) do
        self.brkA[bk.id] = 0
        local lv = ent(bk.lever)
        if lv then lv.transform.rotation = Vec3.new(0, bk.yaw, 0) end
        local lp = ent(bk.lamp)
        if lp then pcall(function() scene:setColor(lp, 0.16, 0.17, 0.19) end) end
        local L = ent(bk.light)
        if L and L:light() then
            L:light():setColor(0.55, 0.58, 0.62)
            L:light().intensity = 0.8
        end
    end
    for i, al in ipairs(self.cfg.aligns or {}) do
        self.alignT[i] = 0
        local e = ent(al.bridge)
        if e then e.transform.position = Vec3.new(al.bx, al.by + HIDE_Y, al.bz) end
    end
    for i, bl in ipairs(self.cfg.blinds or {}) do
        self.blindY[i] = bl.yUp
        place(bl.ent, bl.x, bl.yUp, bl.z)
    end
    -- ★枠の【もとの向き】を覚える。回転台に載った枠はここから毎フレーム回す
    for _, g in ipairs(self.cfg.gates or {}) do
        g.bnx, g.bnz = g.bnx or g.nx, g.bnz or g.nz
        g.nx, g.nz = g.bnx, g.bnz
        g.alx, g.alz = -g.bnz, g.bnx
    end
    for _, pl in ipairs(self.cfg.plates or {}) do
        local L = ent(pl.light)
        if L and L:light() then
            L:light():setColor((pl.cr or 1) * 0.5, (pl.cg or 0.45) * 0.5, (pl.cb or 0.2) * 0.5)
            L:light().intensity = 2.0
        end
    end
    for _, mk in ipairs(self.cfg.marks or {}) do
        place(mk.ent, mk.x, 0.02, mk.z)
        local e = ent(mk.ent)
        -- ★床の印は対の色で塗る(白いままだと「ただの塗装」に見えて意味が伝わらない)
        if e then pcall(function() scene:setColor(e, mk.cr or 1, mk.cg or 1, mk.cb or 1) end) end
    end
    -- ★動く剛体は【やり直しで元の位置へ戻す】。速度も殺さないと落ちた勢いが残る
    self.dynBase = self.dynBase or {}
    for _, dp in ipairs(self.cfg.dynprops or {}) do
        local e = ent(dp.ent)
        if e then
            if not self.dynBase[dp.ent] then
                local q = e.transform.position
                self.dynBase[dp.ent] = { q.x, q.y, q.z }
            end
            local b = self.dynBase[dp.ent]
            pcall(function()
                physics:setVelocity(e, Vec3.new(0, 0, 0))
                -- ★★physics:setPosition は【コライダーの中心】を指す。
                --   原点(足元)をそのまま渡すと、半径ぶん地面へ埋まる(指摘の「玉が埋まってる」)。
                physics:setPosition(e, Vec3.new(b[1], b[2] + dp.off + 0.03, b[3]))
            end)
            e.transform.rotation = Vec3.new(0, 0, 0)
        end
    end
    self.tiltBase = self.tiltBase or {}
    for _, tl in ipairs(self.cfg.tilts or {}) do
        tl._c, tl._a, tl._amt, tl._dx, tl._dz = 0, 0, 0, 0, 1
        for _, nm in ipairs(tl.extra or {}) do
            local e = ent(nm)
            if e and not self.tiltBase[nm] then
                local q = e.transform.position
                self.tiltBase[nm] = { q.x, q.y, q.z }
            end
        end
    end
    for i, w in ipairs(self.cfg.watchers or {}) do
        self.watchS = self.watchS or {}
        self.watchS[i] = { x = w.x, z = w.z, t = 0 }
        place(w.ent, w.x, w.y, w.z)
        local e = ent(w.ent)
        if e then pcall(function() scene:setColor(e, 0.17, 0.18, 0.21) end) end
    end
    self.rollNow = 0
    saveNum("camRoll", 0)
    hide("WarpVeil")
    pcall(function()
        post.setMany{ vignette = 0.26, grain = 0.045, bloom = 0.42, exposure = 0.82 }
    end)
    self.plugT = {}
    self.plugDone = {}
    self.morphT = {}
    self.morphDone = {}
    self.morphLitT = {}      -- ★灯りごとの混ざり具合(0..1)。背中側にある間だけ進む
    self.plugPos = {}
    for _, pg in ipairs(self.cfg.plugs or {}) do
        self.plugPos[pg.id] = { pg.x, pg.y, pg.z }
    end
    for i, pg in ipairs(self.cfg.plugs or {}) do
        local e = ent("Plug_" .. pg.id)
        if e then
            e.transform.position = Vec3.new(pg.x, (pg.mode == "seal") and HIDE_Y or pg.y, pg.z)
        end
    end
    self.plugInit = 1.0   -- ★Play 直後はシーン復元が transform を上書きするので押し込み直す
    self.falls = 0
    self.fallT = 0
    local p = self.cfg.spawn
    -- ★始まりの部屋の縮尺。v8 は「1 面目は必ず x1 の部屋から」という前提で 1.0 を直書きして
    --   いたので、x2 の大広間から始める面(第3面)では 3.6m の部屋に 1.8m の体で立ってしまい、
    --   柵も溝も敷居も判定が全部ずれた。gen_stages.py が部屋から出す。
    local s0 = self.cfg.startScale or 1.0
    self.checkpoint = { x = p[1], z = p[2], s = s0, yaw = p[3], y0 = 0.0 }
    hide("Pilot"); hide("PilotLight")
    -- ★環境光。ここが 0.035 のままだったせいで、v8 で 0.16 に上げたはずの値が
    --   【Play のたびに上書きで戻されて】いた(シーン JSON の 0.16 が効くのは Editor だけ)。
    --   点光源は castShadows=false なので、灯りと平行な面(全開の扉板の裏)が真っ黒になる。
    scene:setAmbient(0.16)
    useBody(self, s0, p[1], p[2], 1.0)
    saveNum("pscale", s0)
    self.shownScale = s0
    camSet(self, p[1], EYE_H * s0, p[2], p[3], 0)
    self.tpSeq = (self.tpSeq or 0) + 1
    saveNum("tpYaw", p[3]); saveNum("tpPitch", 0); saveNum("tpSeq", self.tpSeq)
    self.pendingIntro = true
end

function OnStart(self)
    self.cfg = STAGES[self.name]
    if not self.cfg then
        logError("Junction: 未知のステージ名 " .. tostring(self.name)); return
    end
    self.cam = { x = 0, y = EYE_H, z = 0, yaw = 0, pitch = 0 }
    do  -- ★シーンが持っている FOV を基準として控える(ドリーズームの戻り先)
        local c = ent("MainCamera")
        self.fov0 = (c and c:getFov()) or 74.0
    end
    self.goal = ent("Goal")
    pcall(function()
        if audio:getCurrentBGM() ~= "audio/amb/hum.wav" then
            audio:playBGM("audio/amb/hum.wav")
        end
    end)
    -- 蛍光灯の明滅は【4 灯以上ある部屋】の 1 灯だけ。1 灯しか無い小部屋で明滅させると
    --   部屋ごと真っ暗になる瞬間があり、継ぎ目の前後で光が変わったように見える(実測)
    local n = 0
    for _, nm in ipairs({ "A", "B", "C", "D", "E", "G", "H", "S", "T", "V", "F" }) do
        local L = ent(nm .. "_Light_1")
        if L and L:light() and ent(nm .. "_Light_4") then
            n = n + 1
            if n % 2 == 1 then Flicker(L:light(), "fluorescent") end
        end
    end
    resetRun(self)
    log("JUNCTION v6 stage " .. self.cfg.n .. " / tunnels=" .. #self.cfg.tunnels)
end

-- ---------------------------------------------------------------- 案内の光
-- ★文字を出さない代わりに、これが「次に行く所」の上をふわふわ漂う。
--   序盤(teach 指定のある面)は常に、それ以降も【12 秒何もしていない人】には出す。
--   行き先は gen_stages.py のシミュレーションが出した最短手順(hint)。
local function pilot(self, t, p)
    -- ★★v11: 案内は【光の玉】。次にやる事の上に浮く。文字は出さない。
    --   進む条件を明示してあるので(cross:<枠> / plate:<板> / 空=近づく)、
    --   継ぎ手で飛んでも狂わない。
    local gd = self.cfg.guide or {}
    if #gd > 0 then
        self.gi = self.gi or 1
        while self.gi <= #gd do
            local st = gd[self.gi]
            local ok = false
            if st.need == "" then
                ok = math.sqrt((p.x - st.x) ^ 2 + (p.z - st.z) ^ 2) < 2.2
            elseif st.need:sub(1, 6) == "cross:" then
                ok = (self.crossed or {})[st.need:sub(7)] == true
            elseif st.need:sub(1, 6) == "plate:" then
                ok = (self.plateDone or {})[st.need:sub(7)] == true
            elseif st.need:sub(1, 4) == "brk:" then
                ok = (self.brkOn or {})[st.need:sub(5)] == true
            elseif st.need:sub(1, 6) == "align:" then
                ok = (self.alignDone or {})[st.need:sub(7)] == true
            end
            if ok then self.gi = self.gi + 1 else break end
        end
        if self.gi > #gd then hide("Pilot"); hide("PilotLight"); return end
        local st = gd[self.gi]
        local y = 1.25 + math.sin(t * 2.1) * 0.16
        local sc = 0.22 + 0.04 * math.sin(t * 4.3)
        place("Pilot", st.x, y, st.z, nil, sc, sc, sc)
        place("PilotLight", st.x, y, st.z)
        local pl = ent("PilotLight")
        if pl and pl:light() then
            pl:light().intensity = 2.6 + 1.4 * (0.5 + 0.5 * math.sin(t * 4.3))
        end
        return
    end
    local hint = self.cfg.hint or {}
    -- 通過した経由点は進める
    while self.hintIdx < #hint do
        local h = hint[self.hintIdx]
        local d = math.sqrt((p.x - h[1]) ^ 2 + (p.z - h[2]) ^ 2)
        if d < 1.6 + 0.8 * self.scale then self.hintIdx = self.hintIdx + 1 else break end
    end
    local want = self.cfg.teach ~= nil or self.noAct > 12.0
    if not want or #hint == 0 then hide("Pilot"); hide("PilotLight"); return end
    local h = hint[self.hintIdx]
    local ty = 1.1 + 0.6 * self.shownScale
    local y = ty + math.sin(t * 2.1) * 0.16
    local sc = 0.20 + 0.035 * math.sin(t * 4.3)
    place("Pilot", h[1], y, h[2], nil, sc, sc, sc)
    place("PilotLight", h[1], y, h[2])
    local pl = ent("PilotLight")
    if pl then
        local L = pl:light()
        if L then L.intensity = 2.2 + 1.1 * (0.5 + 0.5 * math.sin(t * 4.3)) end
    end
end

-- ---------------------------------------------------------------- HUD
local function capW(s, size) return #s * size * 0.62 + size * 0.7 end

local function keyCap(cx, y, s, size, a)
    if a <= 0.02 then return end
    local sz = size * (0.80 + 0.20 * a)
    local w, h = capW(s, sz), sz * 1.45
    local x = cx - w * 0.5
    local yy = y + (1 - a) * 8
    ui:rect(x, yy, w, h, 0.03, 0.06, 0.04, 0.74 * a, 5)
    ui:rect(x + 1, yy + 1, w - 2, h - 2, 0.60, 0.68, 0.62, 0.30 * a, 5)
    ui:text(x + sz * 0.35, yy + sz * 0.22, s, sz, C_KEY[1], C_KEY[2], C_KEY[3], a)
end

-- ================================ 毎フレーム ================================
function OnUpdate(self, dt)
    if not self.cfg then return end
    local W, H = SCREEN_W or 1920, SCREEN_H or 1080
    local t = time.now()

    -- 体を地面に固定し直す(登録待ち + 落下の保険)
    do
        local b = bodyEnt(self)
        if b and (self.placeT or 0) > 0 then
            self.placeT = self.placeT - dt
            physics:setPosition(b, Vec3.new(self.anchor.x, (self.anchor.y0 or 0) + BODY_H * 0.5 * self.scale + 0.02, self.anchor.z))
        end
    end

    if self.pendingIntro then
        self.pendingIntro = false
        introCine(self)
        return
    end

    if (self.plugInit or 0) > 0 then
        self.plugInit = self.plugInit - dt
        for i, pg in ipairs(self.cfg.plugs or {}) do
            if not self.plugDone[i] and not self.morphDone[i] then
                local e = ent("Plug_" .. pg.id)
                if e then e.transform.position = Vec3.new(pg.x, (pg.mode == "seal") and HIDE_Y or pg.y, pg.z) end
            end
        end
    end

    if keyPressed("R") then resetRun(self); return end
    -- ★検証用フック(MCP から): saveNum("dbg_size", 2) で今の場所のまま大きさを変える
    do
        local ds = loadNum("dbg_size", 0)
        if ds > 0 then
            saveNum("dbg_size", 0)
            local q = bodyPos(self)
            useBody(self, ds, q.x, q.z, 0.12)
            self.shownScale = ds
        end
    end
    -- ★数字キーは【今いる系統の中で】面を選ぶ。本編なら Logic_Stage_i、
    --   実験台(stagedemo)なら Logic_Demo_i。デモを見比べるのに毎回シーンを
    --   開き直さなくて済む。
    do
        local pre = self.name:match("^(Logic_%a+_)") or "Logic_Stage_"
        for i = 1, 9 do
            if keyPressed(tostring(i)) then
                local s = STAGES[pre .. i]
                if s and s.scene and self.cfg.n ~= i then loadScene(s.scene); return end
            end
        end
    end

    if not self.inTunnel then  -- 廊下の外では見た目の縮尺 = 体の縮尺
        local k = 1 - math.exp(-(1 / math.max(0.05, GROW_TIME)) * 4.0 * dt)
        self.shownScale = self.shownScale + (self.scale - self.shownScale) * k
        if math.abs(self.shownScale - self.scale) < 0.002 then self.shownScale = self.scale end
    end
    saveNum("pscale", self.shownScale)

    if self.cine then
        camApply(self)
        if self.flash > 0 then self.flash = math.max(0, self.flash - dt * 2.2) end
        ui:rect(0, 0, W, H, 1, 1, 1, self.flash)
        local bar = uiAnim(self, "bars", true, dt, 7) * H * 0.085
        ui:rect(0, 0, W, bar, 0, 0, 0, 1)
        ui:rect(0, H - bar, W, bar, 0, 0, 0, 1)
        return
    end
    do
        local bar = uiAnim(self, "bars", false, dt, 7) * H * 0.085
        if bar > 0.5 then
            ui:rect(0, 0, W, bar, 0, 0, 0, 1)
            ui:rect(0, H - bar, W, bar, 0, 0, 0, 1)
        end
    end

    local p = bodyPos(self)
    if self.cool > 0 then self.cool = self.cool - dt end
    if loadNum("moving", 0) > 0.5 then
        self.walkT = self.walkT + dt
        if self.walkT > 1.2 then learn("move") end
        self.noAct = 0
    end
    if loadNum("jumped", 0) > 0.5 then saveNum("jumped", 0); learn("jump"); self.noAct = 0 end
    self.noAct = self.noAct + dt

    -- ================================ クリア ================================
    if self.mode == "clear" then
        if not self.endSfx then self.endSfx = true; sfx("clear") end
        self.flash = math.min(1, (self.flash or 0) + dt * 1.9)
        ui:rect(0, 0, W, H, 1, 1, 1, self.flash)
        -- ★次の面が無ければ今の面をやり直す。廃止した scenes/stage1.json を
        --   直書きしていたので、クリアすると無いシーンを読みに行っていた。
        if self.flash >= 1 then loadScene(self.cfg.next or self.cfg.scene) end
        return
    end
    if self.goal and self.goal:isValid() then
        local g = self.goal.transform.position
        local rr = 0.70 + 0.45 * self.scale
        if (p.x - g.x) ^ 2 + (p.z - g.z) ^ 2 < rr * rr and math.abs(p.y - g.y) < 3.0 then
            self.mode = "clear"; self.flash = 0; self.endSfx = false
            fx:burst{ x = g.x, y = 1.4, z = g.z, kind = "star", count = 70, size = 0.6,
                      r = 0.4, g = 1.0, b = 0.7 }
            log("JUNCTION CLEAR: stage " .. self.cfg.n)
            return
        end
    end

    -- ================================ 溝に落ちた ================================
    if self.fallT > 0 then
        self.fallT = self.fallT - dt
        local a = math.min(1, self.fallT / 0.35)
        ui:rect(0, 0, W, H, 1, 1, 1, a)
    elseif p.y < FALL_Y and (self.placeT or 0) <= 0 then
        local c = self.checkpoint
        useBody(self, c.s, c.x, c.z, 0.3, c.y0)
        self.shownScale = c.s
        self.fallT = 0.5
        self.falls = self.falls + 1
        sfx("fail", 0.9, 0.6)
        log("JUNCTION fell -> checkpoint")
    end

    -- ================================ 廊下(先細り)の中 ================================
    -- ★廊下の中では縮尺が【連続的に】変わる(位置 t/L で線形)。廊下は自己相似なので
    --   歩いても絵は変わらない = 変化は見えない。体(当たり判定)は 5 種しか無いので
    --   廊下の中は小さい方の体を使い、口の手前 0.35m で部屋の体に入れ替える。目の高さは連続。
    local inT = false
    if (self.placeT or 0) <= 0 then
        for i, tn in ipairs(self.cfg.tunnels) do
            local t = (p.x - tn.ax) * tn.nx + (p.z - tn.az) * tn.nz
            local lat = -(p.x - tn.ax) * tn.nz + (p.z - tn.az) * tn.nx
            local hw = math.max(tn.wa, tn.wb) * 0.5 + 0.3
            local by = p.y - BODY_H * 0.5 * self.scale
            if t > -0.05 and t < tn.L + 0.05 and math.abs(lat) <= hw and math.abs(by - tn.y0) < 1.6 then
                -- ★「運んでいる間は大きさが変わらない」規則は撤去した(v9.2)。
                --   持ったまま廊下へ入っても縮まないので【何が起きているのか分からない】
                --   という指摘。廊下の仕事は「出る側の口の大きさへ変える」の一つだけにする。
                --   物は絶対寸法なので、自分が縮めば手の中の箱が勝手に巨大になる ──
                --   それだけで「運ぶ」の面白さは足りている。
                inT = true
                -- ★★廊下に入った瞬間に【入った時の大きさ】と【どちらの口から入ったか】を覚える。
                --   v9 までは t<0.35 で「入口の口の大きさ」へ問答無用で作り替えていたので、
                --   小さいまま大きい口へ入り直すと元の大きさへ戻され、仕掛けが消えていた。
                --   正しい規則は【出る側の口の大きさへ、今の大きさから連続で変える】。
                --   これで「同じ戸でも行きと帰りで結果が違う」= 仕掛けそのものになる。
                if self.tunId ~= tn.id then
                    self.tunId = tn.id
                    self.tunFrom = (t < tn.L * 0.5) and 1 or 0   -- 1 = a 側から入った
                    self.tunEnter = self.scale
                end
                local e = self.tunEnter or tn.sa
                local far = (self.tunFrom == 1) and tn.sb or tn.sa
                local k = math.max(0, math.min(1, t / tn.L))
                if self.tunFrom == 0 then k = 1 - k end          -- 入った口からの進み具合
                self.shownScale = e + (far - e) * k
                local want
                if k < 0.10 then want = e
                elseif k > 0.90 then want = far
                else want = math.min(e, far) end                 -- 途中は細い方に合わせる
                if math.abs(want - self.scale) > 1e-4 then
                    -- ★押し込み(placeT)は 0。ここを 0.05 にしていたせいで、体を入れ替えた
                    --   直後の数フレームだけ【この廊下の走査そのものが飛ばされ】(下の
                    --   placeT ガード)、inTunnel が false に落ちて shownScale が体の縮尺へ
                    --   飛ぶ = 目の高さが一瞬跳ねていた。廊下の中では 1 回置けば足りる。
                    useBody(self, want, p.x, p.z, 0, tn.y0)
                    if k > 0.5 then
                        self.checkpoint = { x = p.x, z = p.z, s = want, yaw = loadNum("camYaw", 0), y0 = tn.y0 }
                    end
                    log(string.format("JUNCTION body %.3g at tunnel %s t=%.2f", want, tn.id, t))
                end
                break
            end
        end
    end
    if not inT then self.tunId = nil end     -- 出たら覚え直す
    self.inTunnel = inT

    -- ================================ 連続スケール場(field) ================================
    -- ★これまで大きさは【廊下の中でだけ】変わった。だからプレイヤーは
    --   「トンネルを通ると何か変わる」と学習してしまい、以降は驚かなくなる。
    --   場にすると変化点が消える = どこで変わったのか指させない。
    --   歩幅も歩く速さも目の高さも連続して変わるので、気づく手がかりが無い。
    -- ★見た目(shownScale)は連続。当たり判定の体は 5 種しか無いので一番近い物へ寄せる。
    --   目の高さは「体の足元 + EYE_H x shownScale」で出しているため、体が飛んでも視点は跳ねない。
    if not inT and self.cfg.field and (self.placeT or 0) <= 0 then
        local f = self.cfg.field
        if p.x >= f.x0 and p.x <= f.x1 and p.z >= f.z0 and p.z <= f.z1 then
            local u = (f.axis == "x") and p.x or p.z
            local t = (u - f.a) / (f.b - f.a)
            t = math.max(0, math.min(1, t))
            self.shownScale = f.s0 + (f.s1 - f.s0) * t
            -- ★体の乗り換えには履歴(ヒステリシス)を入れる。境目でパタパタ入れ替えると
            --   useBody が毎フレーム体を置き直して落下速度が消え、跳べなくなる。
            local g = self.shownScale
            if g < self.scale * 0.70 or g > self.scale * 1.45 then
                local want, bd = self.scale, 1e9
                for _, v in ipairs(SCALES) do
                    local dd = math.abs(v - g)
                    if dd < bd then bd = dd; want = v end
                end
                if math.abs(want - self.scale) > 1e-4 then
                    useBody(self, want, p.x, p.z, 0, self.anchor.y0 or 0)
                    log(string.format("JUNCTION field body %.3g (shown %.2f)", want, g))
                end
            end
        end
    end

    -- ================================ 黙って転送する面(warp) ================================
    -- ★同じ見た目の廊下の中で、ひとつ前の廊下へ戻す。前後の絵が同じなので気づけない
    --   (Antichamber / Stanley Parable の無限廊下)。loops 回で止まる = 抜けられる。
    if (self.placeT or 0) <= 0 then
        for i, w in ipairs(self.cfg.warps or {}) do
            local fwd = (p.x - w.px) * w.nx + (p.z - w.pz) * w.nz
            local lat = -(p.x - w.px) * w.nz + (p.z - w.pz) * w.nx
            local near = math.abs(fwd) < 1.2 and math.abs(lat) <= w.hw
            local side = fwd >= 0 and 1 or -1
            local prev = self.warpSide[i]
            if near and prev == -1 and side == 1 and (self.warpLeft[i] or 0) > 0 then
                self.warpLeft[i] = self.warpLeft[i] - 1
                local qx, qz = p.x + w.dx, p.z + w.dz
                local y0 = (self.anchor.y0 or 0) + w.dy
                -- ★★ここが「つなぎを使うと世界が変わる」の本体。
                --   運ぶ先は【同じ部屋の反対側の口】なので、プレイヤーは同じ部屋へ戻る。
                --   戻った時に体の大きさだけが変わっているので、部屋そのものが
                --   大きくなった / 小さくなったようにしか見えない。
                --   scales は巡回する(1 周ぶんの手順を輪にする)。
                local ns = self.scale
                if w.scales and #w.scales > 0 then
                    self.warpIdx = self.warpIdx or {}
                    self.warpIdx[i] = ((self.warpIdx[i] or 0) % #w.scales) + 1
                    ns = w.scales[self.warpIdx[i]]
                end
                -- hold=0。廊下の中なので押し込むと横移動が止まって「がくん」と見える
                useBody(self, ns, qx, qz, 0, y0)
                self.checkpoint = { x = qx, z = qz, s = ns, yaw = loadNum("camYaw", 0), y0 = y0 }
                self.side = {}
                log(string.format("JUNCTION warp %s -> size %.3g (%d left)", w.id, ns, self.warpLeft[i]))
                self.warpSide[i] = nil
                break
            end
            self.warpSide[i] = near and side or nil
        end
    end

    -- ================================ v11: 継ぎ手の枠(gate) ================================
    -- ★★【手前の枠の開口の中に、向こうの枠が見えている時だけ繋がる】。
    --   どこへ出るかは通る前に見えている。同じ色の枠どうしだけが組。
    do
        local gates, prs = self.cfg.gates or {}, self.cfg.pairs or {}
        local cam = ent("MainCamera")
        local eye = cam and cam.transform.position or p
        self.memNear, self.gBlock = 0, 0
        for i = 1, #gates do self.gLink[i] = nil; self.gStr[i] = 0 end

        -- ★線の上に立っている物があると繋がらない。見張りはこれを狙って動く
        local function blocked(a, b)
            for _, w in ipairs(self.cfg.watchers or {}) do
                local e = ent(w.ent)
                if e then
                    local q = e.transform.position
                    local dx, dz = b.x - a.x, b.z - a.z
                    local L2 = dx * dx + dz * dz
                    if L2 > 1e-4 then
                        local u = ((q.x - a.x) * dx + (q.z - a.z) * dz) / L2
                        if u > 0.02 and u < 0.98 then
                            local px, pz = a.x + dx * u, a.z + dz * u
                            if math.sqrt((q.x - px) ^ 2 + (q.z - pz) ^ 2) < 0.75 then return true end
                        end
                    end
                end
            end
            return false
        end

        local function seeThrough(a, b)
            local bx, bz = eye.x - b.x, eye.z - b.z
            if bx * b.nx + bz * b.nz < 0.15 then return 0 end
            local ax, az = eye.x - a.x, eye.z - a.z
            local fa = ax * a.nx + az * a.nz
            if fa < 0.30 then return 0 end
            local da = math.sqrt(ax * ax + az * az)
            local db = math.sqrt(bx * bx + bz * bz)
            if db < da + 1.0 or da > 14.0 then return 0 end
            local best = 0
            for _, tt0 in ipairs({ 0.32, 0.55, 0.82 }) do
                local by = b.y0 + b.hh * tt0
                local dx, dy, dz = b.x - eye.x, by - eye.y, b.z - eye.z
                local den = dx * a.nx + dz * a.nz
                if math.abs(den) > 1e-4 then
                    local tt = -fa / den
                    if tt > 0.02 and tt < 1.0 then
                        local px, py, pz = eye.x + dx * tt, eye.y + dy * tt, eye.z + dz * tt
                        local lat = (px - a.x) * a.alx + (pz - a.z) * a.alz
                        local u = math.abs(lat) / a.hw
                        local v = math.abs((py - a.y0) - a.hh * 0.5) / (a.hh * 0.5)
                        local m = math.max(u, v)
                        if m < 1.0 and (1.0 - m) > best then best = 1.0 - m end
                    end
                end
            end
            return best
        end

        for _, pr in ipairs(prs) do
            if (pr.needs == "") or self.plateDone[pr.needs] then
                local cand = { { pr.a, pr.b } }
                if pr.both == 1 then cand[2] = { pr.b, pr.a } end
                for _, c in ipairs(cand) do
                    local a, b = gates[c[1]], gates[c[2]]
                    local sN = seeThrough(a, b)
                    if sN > 0 and blocked(a, b) then self.gBlock = 1; sN = 0 end
                    if sN > self.gStr[c[1]] then
                        self.gStr[c[1]] = sN
                        self.gLink[c[1]] = c[2]
                    end
                    if sN > self.gStr[c[2]] then self.gStr[c[2]] = sN * 0.85 end
                end
            end
        end

        -- ★一度繋いだ組は【繋がったまま】。これが無いと向こうで枠の裏に立って帰れない
        for i = 1, #gates do
            if self.bound[i] and not self.gLink[i] then
                local g = gates[i]
                if (g.needs == "") or self.plateDone[g.needs] then
                    self.gLink[i] = self.bound[i]
                    self.gStr[i] = math.max(self.gStr[i], 1.0)
                end
            end
        end
        -- ★重ねた事を 3 秒覚える(枠に寄ると自分が正面から外れて判定が切れるため)。
        --   ★3 秒要る理由: 継の間の回転台は【横を向いた時だけ】繋がる。
        --   繋げてから向き直って歩いてくぐるまでに 1.5〜2 秒かかるので、1.2 秒では届かない。
        for i = 1, #gates do
            if self.gLink[i] then
                self.gHold[i] = { to = self.gLink[i], t = 3.0, s = self.gStr[i] }
            elseif self.gHold[i] then
                self.gHold[i].t = self.gHold[i].t - dt
                if self.gHold[i].t <= 0 then
                    self.gHold[i] = nil
                else
                    self.gLink[i] = self.gHold[i].to
                    self.gStr[i] = math.max(self.gStr[i], self.gHold[i].s * 0.9)
                end
            end
        end

        -- 膜と灯り。★色相 = 対の色。電源の無い枠は灰色の死んだ膜 + 消灯
        for i, g in ipairs(gates) do
            local live = (g.needs == "") or self.plateDone[g.needs]
            local now = self.gShow[i] or 0
            local e = ent(g.mem)
            if e then
                now = now + ((live and self.gStr[i] or 0) - now) * (1 - math.exp(-9.0 * dt))
                self.gShow[i] = now
                local hue = live and (g.hue or 0.53) or -1.0
                pcall(function()
                    scene:setMeshEffect(e, now)
                    scene:setMeshParams(e, (i * 0.137) % 1.0, hue, 0.35, 0.0)
                end)
            end
            local L = ent(g.light)
            if L and L:light() then
                local li = L:light()
                if live then
                    li.intensity = 2.2 + 3.4 * now + 0.5 * (0.55 + 0.45 * math.sin(t * 3.0 + i))
                    li:setColor(g.cr or 0.6, g.cg or 0.76, g.cb or 0.95)
                else
                    li.intensity = 0.55
                    li:setColor(0.55, 0.16, 0.14)
                end
            end
            local dd = math.sqrt((p.x - g.x) ^ 2 + (p.z - g.z) ^ 2)
            local nk = now * math.max(0, 1.0 - dd / 5.0)
            if nk > self.memNear then self.memNear = nk end
        end

        -- ★繋がっている間、二つの枠の間に光の帯(壁を突き抜けて見える)
        self.beamT = (self.beamT or 0) - dt
        if self.beamT <= 0 then
            self.beamT = 0.09
            for i, g in ipairs(gates) do
                if self.gLink[i] and (self.gStr[i] or 0) > 0.25 then
                    local d = gates[self.gLink[i]]
                    pcall(function()
                        fx:beam{ x0 = g.x, y0 = g.y0 + g.hh * 0.55, z0 = g.z,
                                 x1 = d.x, y1 = d.y0 + d.hh * 0.55, z1 = d.z,
                                 width = 0.05 + 0.07 * self.gStr[i], kind = "energy",
                                 r = g.cr or 0.6, g = g.cg or 0.8, b = g.cb or 1.0,
                                 intensity = 1.6, life = 0.13 }
                    end)
                end
            end
        end

        -- ---- くぐる。★正面からでも裏からでも通れる(一度繋いだ組なら) ----
        if (self.gCool or 0) > 0 then self.gCool = self.gCool - dt end
        if (self.placeT or 0) <= 0 and self.mode == "play" and (self.gCool or 0) <= 0 then
            for i, g in ipairs(gates) do
                local fwd = (p.x - g.x) * g.nx + (p.z - g.z) * g.nz
                local lat = (p.x - g.x) * g.alx + (p.z - g.z) * g.alz
                local foot = p.y - BODY_H * 0.5 * self.scale
                local ins = math.abs(lat) <= g.hw + 0.05 and math.abs(foot - g.y0) < 2.2
                local prev = self.gFwd[i]
                local goIn  = (prev and prev > 0 and fwd <= 0)
                local goOut = (prev and prev < 0 and fwd >= 0 and self.bound[i] ~= nil)
                if ins and (goIn or goOut) and self.gLink[i] then
                    local d = gates[self.gLink[i]]
                    local dy = math.deg(atan2(d.nx, d.nz)) - math.deg(atan2(g.nx, g.nz))
                    dy = (dy + 180) % 360 - 180
                    local c, sn = math.cos(math.rad(dy)), math.sin(math.rad(dy))
                    local rlx = g.alx * c + g.alz * sn
                    local rlz = g.alz * c - g.alx * sn
                    local side = goIn and -1.0 or 1.0
                    local qx = d.x + d.nx * 1.05 * side + rlx * lat
                    local qz = d.z + d.nz * 1.05 * side + rlz * lat
                    useBody(self, self.scale, qx, qz, 0, d.y0)
                    self.tpSeq = (self.tpSeq or 0) + 1
                    local ny = (loadNum("camYaw", 0) + dy) % 360
                    saveNum("tpYaw", ny); saveNum("tpPitch", loadNum("camPitch", 0))
                    saveNum("tpSeq", self.tpSeq)
                    self.checkpoint = { x = qx, z = qz, s = self.scale, yaw = ny, y0 = d.y0 }
                    self.gFwd = {}
                    self.gCool = 0.35
                    self.warpT = 1.0
                    self.warpSign = (i % 2 == 0) and 1 or -1
                    self.crossed[g.id] = true
                    self.bound[i] = self.gLink[i]
                    self.bound[self.gLink[i]] = i
                    sfx("connect", 0.72, 0.8)
                    log(string.format("JUNCTION gate %s -> %s", g.id, d.id))
                    break
                end
                self.gFwd[i] = ins and fwd or nil
            end
        end
    end

    -- ================================ v11: くぐった瞬間の演出 ================================
    -- ★暗転しない。【膜そのものがカメラの前を通り過ぎる】。閉じた膜が顔を覆い、
    --   そこから縫い目が裂けて向こう側が現れる。+ 画角の伸縮と視界のねじれ。
    do
        local w = self.warpT or 0
        if w > 0.0005 then self.warpT = math.max(0, w - dt * 1.5) end
        local k = self.warpT or 0
        local e1 = k * k
        local veil = ent("WarpVeil")
        if veil then
            if k > 0.001 then
                local cam = ent("MainCamera")
                local cp = cam and cam.transform.position or p
                local yaw = math.rad(loadNum("camYaw", 0))
                local fx0, fz0 = math.sin(yaw), math.cos(yaw)
                local sc = 1.75
                veil.transform.position = Vec3.new(cp.x + fx0 * 0.48, cp.y - 1.28 * sc + 0.02,
                                                   cp.z + fz0 * 0.48)
                veil.transform.rotation = Vec3.new(0, math.deg(yaw), 0)
                veil.transform.scale = Vec3.new(sc, sc, sc)
                pcall(function()
                    scene:setMeshEffect(veil, math.max(0.0, math.min(1.0, (0.92 - k) * 1.45)))
                    scene:setMeshParams(veil, 0.61, 0.9, 2.2, math.max(0.0, (k - 0.45) * 1.8))
                end)
            else
                local q = veil.transform.position
                if q.y > HIDE_Y + 50 then
                    veil.transform.position = Vec3.new(q.x, HIDE_Y, q.z)
                end
            end
        end
        if e1 > 0.0005 or self.fxOn then
            self.fxOn = (e1 > 0.0005)
            pcall(function()
                post.setMany{ bloomOn = true, bloom = 0.42 + 1.10 * e1,
                              vignetteOn = true, vignette = 0.26 + 0.50 * e1,
                              grainOn = true, grain = 0.045 + 0.26 * e1,
                              exposure = 0.82 * (1.0 + 0.34 * e1) }
            end)
        end
        self.warpFov  = 30.0 * math.sin(k * 3.14159)
        self.warpRoll = (self.warpSign or 1) * 12.0 * math.sin(k * 3.14159) * k
    end

    -- ================================ v11: 重量板(plate) ================================
    for _, pl in ipairs(self.cfg.plates or {}) do
        if not self.plateDone[pl.id] then
            -- ★見る物: 動く剛体ぜんぶ + この板が名指しした物(膜の向こうの写し等)
            local look = {}
            for _, dp in ipairs(self.cfg.dynprops or {}) do look[#look + 1] = dp.ent end
            for _, nm in ipairs(pl.watch or {}) do look[#look + 1] = nm end
            for _, nm2 in ipairs(look) do
                local e = ent(nm2)
                if e then
                    local q = e.transform.position
                    if math.sqrt((q.x - pl.x) ^ 2 + (q.z - pl.z) ^ 2) < pl.r
                       and math.abs(q.y - pl.y0) < 1.3 then
                        self.plateDone[pl.id] = true
                        -- ★受け皿(pin)は玉をそこへ留める。留めないと、次の玉を運ぶ間の
                        --   傾きで転がり出てしまい【二つ同時に入れる】が運任せになる
                        if (pl.pin or 0) > 0 then
                            self.pinned[nm2] = { x = pl.x, y = pl.y0 + (self.offOf[nm2] or 0.36) + 0.02,
                                                 z = pl.z }
                        end
                        local L = ent(pl.light)
                        if L and L:light() then
                            L:light():setColor(pl.cr or 0.3, pl.cg or 1.0, pl.cb or 0.5)
                            L:light().intensity = 5.0
                        end
                        for _, gg in ipairs(self.cfg.gates or {}) do
                            if gg.needs == pl.id then
                                pcall(function()
                                    fx:beam{ x0 = pl.x, y0 = pl.y0 + 0.3, z0 = pl.z,
                                             x1 = gg.x, y1 = gg.y0 + gg.hh * 0.5, z1 = gg.z,
                                             width = 0.16, kind = "energy",
                                             r = gg.cr or 1, g = gg.cg or 1, b = gg.cb or 1,
                                             intensity = 3.0, life = 1.1 }
                                end)
                            end
                        end
                        sfx("clear", 0.85, 0.7)
                        fx:burst{ x = pl.x, y = pl.y0 + 0.3, z = pl.z, kind = "spark",
                                  count = 40, size = 0.35, r = 0.4, g = 1.0, b = 0.6 }
                        log("JUNCTION plate " .. pl.id .. " pressed")
                        break
                    end
                end
            end
        end
    end

    -- ================================ v12: 配電盤(5 つの継電器) ================================
    -- ★出口の扉には電気が要る。5 つの部屋に 1 台ずつ継電器があり、その部屋の仕掛けを
    --   解いてから【触る】と腕が倒れる。動詞が 1 つしか無いので説明が要らない。
    do
        local on = 0
        local nb = #(self.cfg.breakers or {})
        for _, bk in ipairs(self.cfg.breakers or {}) do
            local ready = true
            for _, need in ipairs(bk.needs or {}) do
                if not self.plateDone[need] then ready = false end
            end
            if not self.brkOn[bk.id] then
                local d = math.sqrt((p.x - bk.x) ^ 2 + (p.z - bk.z) ^ 2)
                if ready and d < 2.3 and math.abs(p.y - bk.y) < 3.0 then
                    self.brkOn[bk.id] = true
                    sfx("connect", 0.95, 0.62)
                    fx:burst{ x = bk.x, y = bk.y + 1.5, z = bk.z, kind = "spark",
                              count = 60, size = 0.4, r = bk.cr, g = bk.cg, b = bk.cb }
                    log("JUNCTION breaker " .. bk.id .. " ON")
                end
            end
            if self.brkOn[bk.id] then on = on + 1 end
            -- 腕。倒れる先は【筐体の正面】(yaw を掛けた +Z 方向)
            local want = self.brkOn[bk.id] and 78.0 or (ready and 3.5 * math.sin(t * 3.0) or 0.0)
            local a = self.brkA[bk.id] or 0
            a = a + (want - a) * (1 - math.exp(-7.0 * dt))
            self.brkA[bk.id] = a
            local lv = ent(bk.lever)
            if lv then lv.transform.rotation = Vec3.new(a, bk.yaw, 0) end
            local lp = ent(bk.lamp)
            if lp then
                local k2 = self.brkOn[bk.id] and 1.0 or (ready and (0.45 + 0.35 * math.sin(t * 5.0)) or 0.0)
                pcall(function()
                    scene:setColor(lp, 0.16 + bk.cr * k2, 0.17 + bk.cg * k2, 0.19 + bk.cb * k2)
                end)
            end
            local L = ent(bk.light)
            if L and L:light() then
                if self.brkOn[bk.id] then
                    L:light():setColor(bk.cr, bk.cg, bk.cb)
                    L:light().intensity = 4.6
                elseif ready then
                    L:light():setColor(bk.cr, bk.cg, bk.cb)
                    L:light().intensity = 1.4 + 0.9 * math.sin(t * 5.0)
                end
            end
        end
        -- ★「5 つ揃った」は板と同じ扱いにする。こうすると青い枠の needs = "pw" が
        --   既存の plateDone の仕組みだけで動く(枠側のコードを一行も足さなくていい)
        self.plateDone["pw"] = (nb > 0 and on >= nb)
        self.pwOn = on

        local pw = self.cfg.power
        if pw then
            for i, nm in ipairs(pw.lamps or {}) do
                local e = ent(nm)
                if e then
                    local lit = (i <= on)
                    local f = lit and (0.85 + 0.15 * math.sin(t * 2.0 + i)) or 0.0
                    pcall(function()
                        scene:setColor(e, 0.13 + 0.30 * f, 0.14 + 1.05 * f, 0.16 + 0.55 * f)
                    end)
                end
            end
            local L = ent(pw.light)
            if L and L:light() then
                L:light():setColor(0.35 + 0.2 * on / math.max(1, nb), 0.55 + 0.45 * on / math.max(1, nb), 0.7)
                L:light().intensity = 1.2 + 1.4 * on / math.max(1, nb)
            end
            -- 扉。5 つ揃うと左右へ開く
            local want = self.plateDone["pw"] and 1.0 or 0.0
            self.doorK = (self.doorK or 0) + (want - (self.doorK or 0)) * (1 - math.exp(-1.5 * dt))
            for _, d in ipairs(pw.doors or {}) do
                local e = ent(d.ent)
                if e then
                    e.transform.position = Vec3.new(d.x + d.dx * self.doorK, d.y,
                                                    d.z + d.dz * self.doorK)
                end
            end
        end
    end

    -- ================================ v12: 受け皿に入った玉を留める ================================
    -- ★留めないと、二つ目を運んでいる間の傾きで一つ目が転がり出る = 運任せになる
    for nm, q in pairs(self.pinned or {}) do
        local e = ent(nm)
        if e then
            pcall(function()
                physics:setVelocity(e, Vec3.new(0, 0, 0))
                physics:setPosition(e, Vec3.new(q.x, q.y, q.z))
            end)
        end
    end

    -- ================================ v12: 三枚の欠片(アナモルフォーシス) ================================
    -- ★天井から吊るした 3 枚は、【或る一点から見た時だけ】輪郭が繋がって 1 本のトラス橋になる。
    --   欠片は目からの直線の上に、距離の倍率ぶんだけ縮めて吊ってある(gen_stages.py が計算)。
    --   繋がった = 「隣り合う欠片の継ぎ目が、目から見て同じ方向にある」。
    --   一歩ずれると角度がずれて、三枚はばらばらの板に戻る。
    do
        local ex, ey, ez = p.x, p.y + BODY_H * 0.5 * self.scale * 0.62, p.z
        local cam = ent("MainCamera")
        if cam then local q = cam.transform.position; ex, ey, ez = q.x, q.y, q.z end
        local function ang(ax, ay, az, bx, by, bz)
            local ux, uy, uz = ax - ex, ay - ey, az - ez
            local vx, vy, vz = bx - ex, by - ey, bz - ez
            local lu = math.sqrt(ux * ux + uy * uy + uz * uz)
            local lv = math.sqrt(vx * vx + vy * vy + vz * vz)
            if lu < 1e-4 or lv < 1e-4 then return 180.0 end
            local c = (ux * vx + uy * vy + uz * vz) / (lu * lv)
            return math.deg(math.acos(math.max(-1, math.min(1, c))))
        end
        for i, al in ipairs(self.cfg.aligns or {}) do
            if not self.alignDone[al.id] then
                local d0 = math.sqrt((ex - al.ex) ^ 2 + (ez - al.ez) ^ 2)
                local err = 99.0
                if d0 < 26.0 and #al.segs > 1 then
                    err = 0.0
                    for j = 1, #al.segs - 1 do
                        local A, B = al.segs[j], al.segs[j + 1]
                        err = err + ang(A.x1, A.yt, A.z, B.x0, B.yt, B.z)
                        err = err + ang(A.x1, A.yb, A.z, B.x0, B.yb, B.z)
                    end
                    err = err / (2 * (#al.segs - 1))
                end
                self.alignErr[i] = err
                if err < al.tol then
                    self.alignT[i] = (self.alignT[i] or 0) + dt
                else
                    self.alignT[i] = math.max(0, (self.alignT[i] or 0) - dt * 1.6)
                end
                -- ★近づいてくると欠片が色づく + 唸る。文字を出さずに「今それだ」を言う唯一の手段。
                --   ここが無いと、正解の立ち位置は 34m の部屋のどこにでもある点になってしまう。
                local k2 = math.max(0.0, 1.0 - err / (al.tol * 6.0))
                for _, nm in ipairs(al.shards or {}) do
                    local e = ent(nm)
                    if e then
                        pcall(function()
                            scene:setColor(e, 0.62 + 0.55 * k2 * k2, 0.62 + 0.28 * k2 * k2,
                                           0.62 - 0.30 * k2 * k2)
                        end)
                    end
                end
                if err < al.tol * 3.0 and (self.alignSfx or 0) <= 0 then
                    self.alignSfx = 0.38 - 0.24 * k2
                    sfx("connect", 0.22 + 0.5 * k2, 0.5 + 0.9 * k2)
                end
                if (self.alignT[i] or 0) >= al.hold then
                    self.alignDone[al.id] = true
                    self.alignDrop = self.alignDrop or {}
                    self.alignDrop[al.id] = 1.0          -- 上から降りてくる
                    sfx("clear", 1.0, 0.55)
                    for j = 1, #al.segs do
                        local A = al.segs[j]
                        fx:burst{ x = (A.x0 + A.x1) * 0.5, y = (A.yb + A.yt) * 0.5, z = A.z,
                                  kind = "spark", count = 45, size = 0.4,
                                  r = 1.0, g = 0.86, b = 0.42 }
                    end
                    log("JUNCTION align " .. al.id .. " locked")
                end
            end
        end
        self.alignSfx = (self.alignSfx or 0) - dt
        -- 降下。幻の桁の高さから、渡れる高さへ落ちてくる
        for _, al in ipairs(self.cfg.aligns or {}) do
            local k3 = (self.alignDrop or {})[al.id]
            if k3 then
                k3 = math.max(0.0, k3 - dt * 0.9)
                self.alignDrop[al.id] = k3
                local e = ent(al.bridge)
                if e then
                    e.transform.position = Vec3.new(al.bx, al.by + 5.4 * k3 * k3, al.bz)
                end
                if k3 <= 0 then self.alignDrop[al.id] = nil end
            end
        end
    end

    -- ================================ v12: 見ていない時だけ在る段板 ================================
    -- ★視界の【真ん中】に入れると沈む。目の端に置いたままなら迫り上がる。
    --   だから道を正面から見ずに、横目に入れたまま横歩きで渡ることになる。
    --   立っている板だけは沈めない(足元が消えるのは理不尽なので)。
    do
        local yawc = math.rad(loadNum("camYaw", 0))
        local fx0, fz0 = math.sin(yawc), math.cos(yawc)
        for i, bl in ipairs(self.cfg.blinds or {}) do
            local dx, dz = bl.x - p.x, bl.z - p.z
            local d = math.sqrt(dx * dx + dz * dz)
            local seen = false
            if d > 0.001 and d < bl.rng then
                seen = ((dx * fx0 + dz * fz0) / d) > math.cos(math.rad(bl.cone))
            end
            if d < 2.1 then seen = false end                  -- 足元は消さない
            local tgt = seen and bl.yDn or bl.yUp
            local tau = seen and 0.9 or 0.55                  -- 沈むのは少しゆっくり
            local y = self.blindY[i] or bl.yUp
            y = y + (tgt - y) * (1 - math.exp(-dt / tau))
            self.blindY[i] = y
            place(bl.ent, bl.x, y, bl.z)
        end
    end

    -- ================================ v12: 膜の向こうの写し ================================
    -- ★こちらで押した物が、向こうで【鏡の位置】へ動く。南北が逆になるので
    --   「板へ寄せたい向き」と「押す向き」が食い違う。ここが頭のねじれ。
    for _, mi in ipairs(self.cfg.mirrors or {}) do
        local near = 0.0
        for _, row in ipairs(mi.rows or {}) do
            local ea, eb = ent(row.a), ent(row.b)
            if ea and eb then
                local q = ea.transform.position
                local bx, bz = q.x, q.z
                if mi.axis == "z" then bz = 2.0 * mi.c - q.z else bx = 2.0 * mi.c - q.x end
                -- ★写しは KINEMATIC。KINEMATIC は【transform を書く】のが正しい道。
                --   physics:setPosition(= body を直に置く)は動的剛体にしか効かず、
                --   書いても次のフレームに transform から上書きされて戻る(実測)。
                --   transform 経由ならコライダーのオフセットはエンジンが足すので不要。
                eb.transform.position = Vec3.new(bx, q.y, bz)
                local r = ea.transform.rotation
                eb.transform.rotation = Vec3.new(-r.x, -r.y, r.z)
                for _, pl in ipairs(self.cfg.plates or {}) do
                    for _, nm in ipairs(pl.watch or {}) do
                        if nm == row.b then
                            local dd = math.sqrt((bx - pl.x) ^ 2 + (bz - pl.z) ^ 2)
                            near = math.max(near, math.max(0.0, 1.0 - dd / 9.0))
                        end
                    end
                end
            end
        end
        for _, nm in ipairs(mi.mem or {}) do
            local e = ent(nm)
            if e then
                pcall(function()
                    scene:setMeshEffect(e, 0.16 + 0.70 * near)
                    scene:setMeshParams(e, 0.5, 0.46, 0.30 + 1.5 * near, 0.0)
                end)
            end
        end
    end

    -- ================================ v12: 首を振ると回る枠(回転台) ================================
    -- ★奥の枠は回転台に載っていて、こちらが首を振ると【逆向きに】回る。
    --   枠が自分の方を向いていて、かつ手前の枠の開口の中に見える角度は【正面ではない】。
    --   横を向いたまま、横歩きでくぐることになる。
    for _, tn in ipairs(self.cfg.turnts or {}) do
        local g = (self.cfg.gates or {})[tn.gate]
        if g then
            local a = math.rad(tn.base + tn.k * loadNum("camYaw", 0))
            local c, s2 = math.cos(a), math.sin(a)
            g.nx = (g.bnx or 0) * c + (g.bnz or 1) * s2
            g.nz = -(g.bnx or 0) * s2 + (g.bnz or 1) * c
            g.alx, g.alz = -g.nz, g.nx
            local yaw2 = math.deg(atan2(g.nx, g.nz))
            for _, nm in ipairs({ tn.ent, g.ent, g.mem, "GateB_" .. g.id }) do
                local e = ent(nm)
                if e then e.transform.rotation = Vec3.new(0, yaw2, 0) end
            end
            -- 枠の柱(見えない当たり判定)も一緒に回す
            for s3 = 0, 1 do
                local e3 = ent(string.format("GateJ_%s_%d", g.id, s3))
                local sg = (s3 == 1) and 1.0 or -1.0
                if e3 then
                    local q = e3.transform.position
                    e3.transform.position = Vec3.new(g.x + g.alx * sg * (g.hw + 0.16 * g.size), q.y,
                                                     g.z + g.alz * sg * (g.hw + 0.16 * g.size))
                    e3.transform.rotation = Vec3.new(0, yaw2, 0)
                end
            end
            local Lg = ent(g.light)
            if Lg then
                Lg.transform.position = Vec3.new(g.x - g.nx * 0.5, g.y0 + g.hh * 0.86,
                                                 g.z - g.nz * 0.5)
            end
        end
    end

    -- ================================ v11: 歩くと傾く床 ================================
    -- ★★ボタンは要らない。【歩いている間だけ】進む向きへ床が下がる。止まれば水平へ戻る。
    --   歩いて玉を追えば床が前へ傾いて玉が逃げる = 玉を追い立てる感覚。
    --   什器(ロッカー等)も床にくっついて一緒に上下する(KINEMATIC にしてある)。
    for _, tl in ipairs(self.cfg.tilts or {}) do
        local dx0, dz0 = p.x - tl.x, p.z - tl.z
        local near = (dx0 * dx0 + dz0 * dz0) < 15.0 * 15.0
        local mvx, mvz = loadNum("moveX", 0), loadNum("moveZ", 0)
        local mv = (loadNum("moving", 0) > 0.5) and near
        local yaw = math.rad(loadNum("camYaw", 0))
        local gx, gz = math.sin(yaw), math.cos(yaw)
        local L0 = math.sqrt(mvx * mvx + mvz * mvz)
        local dxw, dzw = gx, gz
        if L0 > 0.1 then
            dxw, dzw = (mvx / L0) * 0.72 + gx * 0.28, (mvz / L0) * 0.72 + gz * 0.28
            local L1 = math.sqrt(dxw * dxw + dzw * dzw)
            if L1 > 1e-4 then dxw, dzw = dxw / L1, dzw / L1 end
        end
        tl._amt = (tl._amt or 0) + ((mv and 1.0 or 0.0) - (tl._amt or 0)) * (1 - math.exp(-3.4 * dt))
        if tl._amt > 0.02 then tl._dx, tl._dz = dxw, dzw end
        self.inTilt = near
        local th = math.rad(tl.deg * (tl._amt or 0))
        -- ★下り坂は【法線の水平成分の向き】。逆にすると玉が反対へ転がる
        local wc = math.deg(math.asin(math.max(-0.6, math.min(0.6, -(tl._dx or 0) * math.sin(th)))))
        local wa = math.deg(math.asin(math.max(-0.6, math.min(0.6, (tl._dz or 1) * math.sin(th)))))
        tl._c = (tl._c or 0) + (wc - (tl._c or 0)) * (1 - math.exp(-4.0 * dt))
        tl._a = (tl._a or 0) + (wa - (tl._a or 0)) * (1 - math.exp(-4.0 * dt))
        local cc, sc2 = math.cos(math.rad(tl._c)), math.sin(math.rad(tl._c))
        local ca2, sa2 = math.cos(math.rad(tl._a)), math.sin(math.rad(tl._a))
        local function place3(nm, bx, by, bz)
            local e = ent(nm)
            if not e then return end
            local x, y, z = bx - tl.x, by - tl.y, bz - tl.z
            local X = x * cc - y * sc2
            local Y = x * sc2 + y * cc
            e.transform.position = Vec3.new(tl.x + X, tl.y + (Y * ca2 - z * sa2),
                                            tl.z + (Y * sa2 + z * ca2))
            -- ★継電器の腕だけは向きを床に任せない。床と一緒に上下はするが、
            --   倒れた角度(rotation.x)を毎フレーム 0 に戻されると【入ったのに戻る】。
            --   実測: 傾く部屋の継電器が入っているのに腕が立ったままだった。
            if nm:sub(1, 5) ~= "BrkL_" then
                e.transform.rotation = Vec3.new(tl._a, 0, tl._c)
            end
        end
        for _, row in ipairs(tl.ents) do place3(row[1], row[2], row[3], row[4]) end
        for _, nm in ipairs(tl.extra or {}) do
            local b = self.tiltBase[nm]
            if b then place3(nm, b[1], b[2], b[3]) end
        end
        -- ★★玉が床へ沈むのを直す。KINEMATIC を毎フレーム transform で置き直しているので
        --   Jolt から見ると「速度ゼロの板が瞬間移動」= 押し戻しが効かずめり込む。
        --   床は平面なので高さは式で出る。沈んだぶんだけ持ち上げる。
        local nx, ny, nz = -sc2, cc * ca2, cc * sa2
        if math.abs(ny) > 1e-3 then
            for _, dp in ipairs(self.cfg.dynprops or {}) do
                local e = ent(dp.ent)
                if e then
                    local q = e.transform.position
                    local ddx, ddz = q.x - tl.x, q.z - tl.z
                    if ddx * ddx + ddz * ddz < 14.0 * 14.0 then
                        local surf = tl.y - (nx * ddx + nz * ddz) / ny
                        if q.y < surf - 0.02 then
                            local v = physics:getVelocity(e)
                            -- ★ここも【コライダー中心】を渡す。足元を渡すと埋まる
                            physics:setPosition(e, Vec3.new(q.x, surf + dp.off + 0.01, q.z))
                            if v and v.y < 0 then physics:setVelocity(e, Vec3.new(v.x, 0, v.z)) end
                        end
                    end
                end
            end
        end
    end

    -- ================================ v11: 見張り(watchers) ================================
    -- ★視界に入っている間は 1mm も動かない。目を離すと枠と枠を結ぶ線の上へ寄ってくる。
    --   34kg の剛体なので押しのけられる。
    do
        local yaw = math.rad(loadNum("camYaw", 0))
        local fx0, fz0 = math.sin(yaw), math.cos(yaw)
        for i, w in ipairs(self.cfg.watchers or {}) do
            local st = self.watchS and self.watchS[i]
            if st then
                local dx, dz = st.x - p.x, st.z - p.z
                local d = math.sqrt(dx * dx + dz * dz)
                local seen = (d < w.rng) and ((dx * fx0 + dz * fz0) / math.max(0.01, d) > 0.34)
                if (not seen) and d > w.near and d < w.rng then
                    st.t = st.t + dt
                    if st.t >= w.wait then
                        st.t = 0
                        local k = math.min(w.step, d - w.near) / d
                        st.x, st.z = st.x - dx * k, st.z - dz * k
                    end
                else
                    st.t = 0
                end
                place(w.ent, st.x, w.y, st.z,
                      (w.turn == 1) and math.deg(atan2(p.x - st.x, p.z - st.z)) or nil)
            end
        end
    end

    -- ================================ v11: 視界の傾き(rolls) ================================
    do
        local want = 0
        for _, q in ipairs(self.cfg.rolls or {}) do
            if p.x >= q.x0 and p.x <= q.x1 and p.z >= q.z0 and p.z <= q.z1 then
                local u = (((q.axis == "x") and p.x or p.z) - q.a) / (q.b - q.a)
                u = math.max(0, math.min(1, u))
                want = q.d0 + (q.d1 - q.d0) * u
            end
        end
        self.rollNow = (self.rollNow or 0) + (want - (self.rollNow or 0)) * (1 - math.exp(-2.2 * dt))
        saveNum("camRoll", self.rollNow + (self.warpRoll or 0))
    end

    -- ======================= 角度固定(anchors) / ドリーズーム(dolly) =======================
    -- ★(1) 角度固定: 毎フレーム scale を【カメラからの距離に比例】させる。
    --   相似三角形なので投影サイズが数学的に不変 = 近づいても画面上の大きさが 1px も変わらない。
    --   実測: カメラを 9.4m -> 3.8m(2.5 倍近づく)まで詰めても、その物だけ幅が変わらなかった。
    --   これを廊下の奥の扉に仕込むと【歩いても永遠に着かない扉】になる(実際には着く)。
    do
        local c = ent("MainCamera")
        if c then
            local q = c.transform.position
            for _, a in ipairs(self.cfg.anchors or {}) do
                local e = ent(a.ent)
                if e then
                    local d = math.sqrt((q.x - a.x) ^ 2 + (q.z - a.z) ^ 2)
                    local sc = math.max(0.03, a.k * d / a.d0)
                    e.transform.scale = Vec3.new(sc, sc, sc)
                end
            end
        end
    end

    -- ★(3) ドリーズーム: 注視点の見かけの大きさを保ったまま FOV を動かすと、
    --   【自分は動いていないのに部屋だけが伸びる】。ヒッチコックのめまいショット。
    --   ★FOV は毎フレーム絶対値で書かないと翌フレームに戻る(エンジンの仕様)。
    do
        local want = self.fov0 or 74.0
        -- ★v11: 歩く位置で画角を連続的に絞る帯。絞ると【近づいても大きくならない】ので、
        --   36m の廊下を歩いても奥の壁がいつまでも同じ大きさ = 永遠に着かない。
        for _, q in ipairs(self.cfg.fovramps or {}) do
            if p.x >= q.x0 and p.x <= q.x1 and p.z >= q.z0 and p.z <= q.z1 then
                local u = (((q.axis == "x") and p.x or p.z) - q.a) / (q.b - q.a)
                u = math.max(0, math.min(1, u))
                want = q.f0 + (q.f1 - q.f0) * u
            end
        end
        for _, d in ipairs(self.cfg.dolly or {}) do
            local dx, dz = p.x - d.x, p.z - d.z
            if dx * dx + dz * dz < d.r * d.r then want = d.fov end
        end
        self.fovNow = (self.fovNow or want) + (want - (self.fovNow or want)) * (1 - math.exp(-2.6 * dt))
        local c = ent("MainCamera")
        if c then c:setFov(self.fovNow + (self.warpFov or 0)) end
    end

    -- ================================ 運ぶ ================================
    -- ★E で拾う / 置く。物は【絶対寸法】なので、自分が縮むと相対的に巨大になる。
    --   木箱(天端 0.70m)は 大きさ1 なら踏み台になる(0.70 + climb_h(1)=1.15 → 1.85 > 柵1.7)が、
    --   大きさ0.5 では climb_h=0.575 < 0.70 なので【箱に登れない】= 役に立たない。
    --   「同じ箱なのに、自分の大きさで道具になったりガラクタになったりする」。
    self.carryNear = nil
    if (self.placeT or 0) <= 0 and self.mode == "play" then
        local yaw = math.rad(loadNum("camYaw", 0))
        local fx, fz = math.sin(yaw), math.cos(yaw)
        if not self.held then                      -- 近くの物を探す(拾える印を出すため)
            local bd = 1.6 + 1.4 * self.scale
            for i, c in ipairs(self.cfg.carries or {}) do
                local e = ent(c.ent)
                if e and e.transform.position.y > HIDE_Y + 50 then
                    local q = e.transform.position
                    local d = math.sqrt((q.x - p.x) ^ 2 + (q.z - p.z) ^ 2)
                    if d < bd then bd = d; self.carryNear = i end
                end
            end
        end
        if keyPressed("E") then
            if self.held then
                local c = self.cfg.carries[self.held]
                local d = 0.75 * self.scale + 0.55
                local gy = self.anchor.y0 or 0
                place(c.ent, p.x + fx * d, gy, p.z + fz * d)
                place(c.col, p.x + fx * d, gy + c.h * 0.5, p.z + fz * d)
                self.held = nil
                sfx("detent", 0.9, 0.5)
            elseif self.carryNear then
                self.held = self.carryNear
                self.carryNear = nil
                sfx("touch", 1.1, 0.5)
            end
        end
        if self.held then                          -- 目の前に抱える。当たり判定は消す
            local c = self.cfg.carries[self.held]
            local d = 0.50 * self.scale + 0.50
            local hy = (p.y - BODY_H * 0.5 * self.scale) + 0.80 * self.scale
            place(c.ent, p.x + fx * d, hy, p.z + fz * d)
            place(c.col, 0, HIDE_Y, 0)
        end
    end
    if (self.carryNear or self.held) and not self.cine then
        keyCap(W * 0.5, H * 0.70, "E", math.floor(H * 0.028), 1.0)
    end

    -- ================================ 大きさの門(sizegates) ================================
    -- ★床に立った枠(seam.gltf)。くぐると【その場で】大きさが変わる。移動は一切しない。
    --   「同じ部屋・同じ場所なのに、つなぎを通ると世界の見え方が変わる」を、
    --   移動を挟まずに直接見せるための装置。前から入れば sf、後ろから入れば sb。
    if (self.placeT or 0) <= 0 then
        self.sgSide = self.sgSide or {}
        for i, g in ipairs(self.cfg.sizegates or {}) do
            local fwd = (p.x - g.x) * g.nx + (p.z - g.z) * g.nz
            local lat = -(p.x - g.x) * g.nz + (p.z - g.z) * g.nx
            local near = math.abs(fwd) < 2.5 and math.abs(lat) <= g.hw
            local side = fwd >= 0 and 1 or -1
            local prev = self.sgSide[i]
            if near and prev ~= nil and prev ~= side then
                local ns = (side == 1) and g.sf or g.sb
                if ns > 0 and math.abs(ns - self.scale) > 1e-4 then
                    useBody(self, ns, p.x, p.z, 0, self.anchor.y0 or 0)
                    sfx("grow", 1.0, 0.45)
                    log(string.format("JUNCTION sizegate %s -> %.3g", g.id, ns))
                end
            end
            self.sgSide[i] = near and side or nil
        end
    end

    -- ================================ 背後改変(morph) ================================
    -- ★P.T. と同じ。プレイヤーが【部屋に背を向けている間だけ】部屋そのものを書き換える。
    --   偽の廊下の突き当りを見ている間(部屋の中心が背中側)に、家具を入れ替え、光の色を変え、
    --   壁だった所の栓を抜く。振り返った瞬間、世界が違う。音は鳴らさない。
    do
        local yaw = math.rad(loadNum("camYaw", 0))
        local fx, fz = math.sin(yaw), math.cos(yaw)
        for i, mo in ipairs(self.cfg.morphs or {}) do
            if not self.morphDone[i] then
                local dx, dz = mo.x - p.x, mo.z - p.z
                local d = math.sqrt(dx * dx + dz * dz)
                local wx, wz = mo.wx - p.x, mo.wz - p.z
                local wd = math.sqrt(wx * wx + wz * wz)
                local dot = (wx * fx + wz * fz) / math.max(0.01, wd)
                if d < mo.r and dot < -0.2 then
                    self.morphT[i] = (self.morphT[i] or 0) + dt
                    if self.morphT[i] > mo.delay then
                        for _, rw in ipairs(mo.rows) do
                            local e = ent(rw[1])
                            if e then
                                local yy = (rw[5] == "A") and HIDE_Y or rw[3]
                                e.transform.position = Vec3.new(rw[2], yy, rw[4])
                            end
                        end
                        for _, id in ipairs(mo.seal or {}) do
                            local q = self.plugPos[id]
                            local e = ent("Plug_" .. id)
                            if e and q then e.transform.position = Vec3.new(q[1], q[2], q[3]) end
                        end
                        for _, id in ipairs(mo.unseal or {}) do
                            local q = self.plugPos[id]
                            local e = ent("Plug_" .. id)
                            if e and q then e.transform.position = Vec3.new(q[1], HIDE_Y, q[3]) end
                        end
                        -- ★照明はここでは触らない。下の「1 灯ずつ」に任せる(v8)
                        self.morphDone[i] = true
                        log("JUNCTION morph " .. mo.id)
                    end
                else
                    self.morphT[i] = 0
                end
            end
            -- ★★照明の切り替え(v8)。指摘:「変わったことに気づいてしまう」。
            --   原因は 2 つあった。(a) 部屋の灯りを【全部同時に】差し替えていた、
            --   (b) 点光源は castShadows=false なので【壁を透けて】手前の面を照らす。
            --   直し方: 部屋単位ではなく【1 灯ずつ】、その灯りが自分の背中側にある間だけ、
            --   LIGHT_FADE 秒かけて混ぜる。振り向いた瞬間その灯りは止まり、また背を向けると続く。
            --   結果、色は「変わる瞬間」を持たない = 変わったことに気づけない(変化盲)。
            if self.morphDone[i] and mo.light then
                local pr = self.morphLitT[i]
                if not pr then pr = {}; self.morphLitT[i] = pr end
                local c0 = mo.light0 or { 0.98, 0.96, 0.88 }
                for n = 1, 9 do
                    local t = pr[n] or 0
                    if t < 1 then
                        local L = ent(mo.room .. "_Light_" .. n)
                        if not L or not L:light() then
                            pr[n] = 1
                        else
                            local q = L.transform.position
                            local ax, az = q.x - p.x, q.z - p.z
                            local ad = math.sqrt(ax * ax + az * az)
                            if (ax * fx + az * fz) / math.max(0.01, ad) < -0.30 then
                                t = math.min(1.0, t + dt / LIGHT_FADE)
                                pr[n] = t
                                L:light():setColor(c0[1] + (mo.light[1] - c0[1]) * t,
                                                   c0[2] + (mo.light[2] - c0[2]) * t,
                                                   c0[3] + (mo.light[3] - c0[3]) * t)
                            end
                        end
                    end
                end
            end
        end
    end

    -- ================================ 栓(見ていない間に変わる) ================================
    -- ★変化盲。プレイヤーが背を向けている間だけ動かす(P.T. / Layers of Fear)。
    --   appear: 壁に塞がれた扉が、目を離すと開いている。 seal: 来た道が、目を離すと塞がっている。
    do
        local yaw = math.rad(loadNum("camYaw", 0))
        local fx, fz = math.sin(yaw), math.cos(yaw)
        for i, pg in ipairs(self.cfg.plugs or {}) do
            if not self.plugDone[i] and not pg.auto then   -- auto = morph が動かす
                local vx, vz = pg.x - p.x, pg.z - p.z
                local d = math.sqrt(vx * vx + vz * vz)
                local dot = (vx * fx + vz * fz) / math.max(0.01, d)
                local closeY = math.abs((p.y - BODY_H * 0.5 * self.scale) - (pg.y - 1.3)) < 3.0
                if d < 9.0 and closeY then
                    self.plugT[i] = (self.plugT[i] or 0) + dt
                    if self.plugT[i] > pg.delay and dot < -0.3 and d > 2.5 then
                        local e = ent("Plug_" .. pg.id)
                        if e then
                            if pg.mode == "appear" then
                                e.transform.position = Vec3.new(pg.x, HIDE_Y, pg.z)
                            else
                                e.transform.position = Vec3.new(pg.x, pg.y, pg.z)
                            end
                        end
                        self.plugDone[i] = true
                        log("JUNCTION plug " .. pg.id .. " " .. pg.mode)
                    end
                end
            end
        end
    end

    pilot(self, t, p)

    -- ================================ HUD ================================
    ui:rect(W * 0.5 - 4, H * 0.5 - 4, 8, 8, 0, 0, 0, 0.5, 4)
    ui:rect(W * 0.5 - 2, H * 0.5 - 2, 4, 4, 1, 1, 1, 0.95, 2)

    -- ★v11: 重なり具合。文字は出さない。照準の真下の細い線 1 本だけ。
    --   枠の正面に立つと出て、動くと伸び縮みする = 手探りで正しい立ち位置を探せる。
    do
        local gates = self.cfg.gates or {}
        local best, bi = 0.0, nil
        for i, g in ipairs(gates) do
            local ax, az = p.x - g.x, p.z - g.z
            local fa = ax * g.nx + az * g.nz
            local lat = math.abs(ax * g.alx + az * g.alz)
            local d = math.sqrt(ax * ax + az * az)
            if fa > 0.2 and d < 9.0 and lat < g.hw + 2.6 then
                local sc2 = (1.0 - d / 9.0) * (1.0 - math.min(1.0, lat / (g.hw + 2.6)))
                if sc2 > best then best, bi = sc2, i end
            end
        end
        if bi then
            local g = gates[bi]
            local live = (g.needs == "") or self.plateDone[g.needs]
            local str = self.gStr[bi] or 0
            local bw, bx, by = 96, W * 0.5 - 48, H * 0.5 + 26
            if live then
                ui:rect(bx, by, bw, 3, 0.10, 0.11, 0.13, 0.55, 2)
                if str > 0.01 then
                    ui:rect(bx, by, bw * math.min(1, str), 3,
                            g.cr or 0.7, g.cg or 0.8, g.cb or 1.0, 0.95, 2)
                end
            else
                ui:rect(bx, by, bw, 3, 0.42, 0.10, 0.09, 0.6, 2)
            end
        end
    end

    local help = keyDown("H")
    local stuck = self.noAct > 12.0
    keyCap(W * 0.5, H - 62, "W A S D", 22,
           uiAnim(self, "move", help or stuck or not learned("move"), dt, 6))
    keyCap(W * 0.5, H - 130, "SPACE", 22,
           uiAnim(self, "jumpkey",
                  help or stuck or (learned("move") and not learned("jump")), dt, 6))
end
