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
            { id = "m1", x = 0.000, z = -10.000, wx = 0.000, wz = 0.000, r = 15.00, delay = 1.2, light = { 0.93, 0.93, 1.00 }, light0 = { 0.98, 0.96, 0.88 },
              room = "A", seal = {  }, unseal = {  },
              rows = { { "MorphA_m1_0", 12.00, 0.00, 9.00, "A" }, { "MorphA_m1_1", -6.00, 0.00, 8.60, "A" }, { "MorphB_m1_0", -12.50, 0.00, 9.60, "B" }, { "MorphB_m1_1", 7.00, 0.00, 12.00, "B" } } },
        },
        plugs = {
        },
        ports = {
        },
        links = {
        },
        watchers = {
            { ent = "W1", x = -4.000, y = 0.000, z = -44.000, step = 1.40, near = 3.20, rng = 34.0, wait = 1.00, turn = 1 },
            { ent = "W2", x = 3.000, y = 0.000, z = -43.000, step = 1.20, near = 3.60, rng = 34.0, wait = 1.30, turn = 1 },
            { ent = "W3", x = 7.000, y = 0.000, z = -45.000, step = 1.10, near = 4.00, rng = 34.0, wait = 1.60, turn = 1 },
        },
        creeps = {
        },
        rolls = {
            { axis = "x", a = -12.00, b = 14.00, d0 = 0.00, d1 = 8.00, x0 = -19.00, x1 = 19.00, z0 = -34.00, z1 = -23.00 },
        },
        gates = {
            { id = "s1", ent = "Gate_s1", mem = "GateM_s1", light = "GateL_s1", x = 6.000, z = -15.500, y0 = 0.00, nx = 0.000, nz = -1.000, alx = 1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 1.000, cg = 0.620, cb = 0.180, hue = 0.090, needs = "" },
            { id = "m1", ent = "Gate_m1", mem = "GateM_m1", light = "GateL_m1", x = 6.000, z = -10.000, y0 = 0.00, nx = 0.000, nz = -1.000, alx = 1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 1.000, cg = 0.620, cb = 0.180, hue = 0.090, needs = "" },
            { id = "m2", ent = "Gate_m2", mem = "GateM_m2", light = "GateL_m2", x = 12.000, z = -10.000, y0 = 0.00, nx = -1.000, nz = 0.000, alx = -0.000, alz = -1.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.240, cg = 0.820, cb = 1.000, hue = 0.530, needs = "" },
            { id = "g1", ent = "Gate_g1", mem = "GateM_g1", light = "GateL_g1", x = 26.000, z = -10.000, y0 = 0.00, nx = -1.000, nz = 0.000, alx = -0.000, alz = -1.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.240, cg = 0.820, cb = 1.000, hue = 0.530, needs = "" },
            { id = "m3", ent = "Gate_m3", mem = "GateM_m3", light = "GateL_m3", x = 0.000, z = -9.500, y0 = 0.00, nx = 0.000, nz = -1.000, alx = 1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.380, cg = 0.520, cb = 1.000, hue = 0.620, needs = "p1" },
            { id = "n1", ent = "Gate_n1", mem = "GateM_n1", light = "GateL_n1", x = 0.000, z = 12.000, y0 = 0.00, nx = 0.000, nz = -1.000, alx = 1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.380, cg = 0.520, cb = 1.000, hue = 0.620, needs = "p1" },
            { id = "m4", ent = "Gate_m4", mem = "GateM_m4", light = "GateL_m4", x = -12.000, z = -10.000, y0 = 0.00, nx = 1.000, nz = 0.000, alx = -0.000, alz = 1.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.320, cg = 1.000, cb = 0.480, hue = 0.350, needs = "" },
            { id = "d1", ent = "Gate_d1", mem = "GateM_d1", light = "GateL_d1", x = -26.000, z = -10.000, y0 = 0.00, nx = 1.000, nz = 0.000, alx = -0.000, alz = 1.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.320, cg = 1.000, cb = 0.480, hue = 0.350, needs = "" },
            { id = "s2", ent = "Gate_s2", mem = "GateM_s2", light = "GateL_s2", x = -14.000, z = -18.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 1.000, cg = 0.320, cb = 0.280, hue = 0.990, needs = "" },
            { id = "b1", ent = "Gate_b1", mem = "GateM_b1", light = "GateL_b1", x = -14.000, z = -27.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 1.000, cg = 0.320, cb = 0.280, hue = 0.990, needs = "" },
            { id = "b2", ent = "Gate_b2", mem = "GateM_b2", light = "GateL_b2", x = 0.000, z = -30.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.720, cg = 0.460, cb = 1.000, hue = 0.760, needs = "" },
            { id = "h1", ent = "Gate_h1", mem = "GateM_h1", light = "GateL_h1", x = 0.000, z = -39.000, y0 = 0.00, nx = 0.000, nz = 1.000, alx = -1.000, alz = 0.000, hw = 1.00, hh = 2.60, size = 1.00, cr = 0.720, cg = 0.460, cb = 1.000, hue = 0.760, needs = "" },
        },
        pairs = {
            { a = 1, b = 2, both = 1, needs = "" },
            { a = 3, b = 4, both = 1, needs = "" },
            { a = 5, b = 6, both = 1, needs = "p1" },
            { a = 7, b = 8, both = 1, needs = "" },
            { a = 9, b = 10, both = 1, needs = "" },
            { a = 11, b = 12, both = 1, needs = "" },
        },
        plates = {
            { id = "p1", ent = "Plate_p1", light = "PlateL_p1", x = 32.000, z = -11.500, y0 = 0.00, r = 1.50, cr = 0.380, cg = 0.520, cb = 1.000 },
        },
        guide = {
            { x = 6.00, z = -18.10, need = "cross:s1" },
            { x = 9.00, z = -10.00, need = "cross:m2" },
            { x = 32.00, z = -10.00, need = "plate:p1" },
            { x = 27.60, z = -10.00, need = "cross:g1" },
            { x = 0.00, z = -12.50, need = "cross:m3" },
            { x = 0.00, z = 17.00, need = "" },
        },
        marks = {
            { ent = "MarkL_s1", light = "MarkLi_s1", x = 6.000, z = -18.100, cr = 1.000, cg = 0.620, cb = 0.180 },
            { ent = "MarkL_m2", light = "MarkLi_m2", x = 9.000, z = -10.000, cr = 0.240, cg = 0.820, cb = 1.000 },
            { ent = "MarkL_m3", light = "MarkLi_m3", x = 0.000, z = -12.500, cr = 0.380, cg = 0.520, cb = 1.000 },
        },
        tilts = {
            { x = 32.000, y = 0.000, z = -10.000, deg = 6.50, ents = { { "G_Floor", 32.000, -0.250, -10.000 }, { "G_FloorM", 32.000, 0.005, -10.000 }, { "G_TWall_0", 32.000, 0.275, -12.200 }, { "G_TWall_1", 29.700, 0.275, -11.000 }, { "G_TWall_2", 34.300, 0.275, -11.000 }, { "G_locker_1", 25.400, 0.000, -3.400 }, { "G_bench_2", 25.600, 0.000, -15.600 } }, extra = { "Plate_p1", "PlateL_p1" } },
        },
        fovramps = {
            { axis = "x", a = -14.00, b = 14.00, f0 = 74.0, f1 = 46.0, x0 = -19.00, x1 = 19.00, z0 = -34.00, z1 = -23.00 },
        },
        dynprops = { { ent = "A_drum_2", off = 0.440 }, { ent = "A_drum_3", off = 0.440 }, { ent = "A_crate_7", off = 0.375 }, { ent = "A_drum_9", off = 0.440 }, { ent = "A_crate_10", off = 0.375 }, { ent = "A_drum_15", off = 0.440 }, { ent = "G_ball_0", off = 0.360 }, { ent = "D_drum_6", off = 0.440 }, { ent = "D_drum_7", off = 0.440 }, { ent = "D_crate_8", off = 0.375 }, { ent = "B_drum_6", off = 0.440 }, { ent = "B_crate_7", off = 0.375 }, { ent = "H_drum_6", off = 0.440 }, { ent = "H_crate_7", off = 0.375 } },
        anchors = {
            { ent = "Anchor_0", x = 16.500, z = -28.500, k = 1.000, d0 = 31.000 },
        },
        dolly = {
            { x = 0.000, z = -8.500, r = 5.00, fov = 54.0 },
        },
        carries = {
        },
        sizegates = {
        },
        hint = { { 6.00, -18.10 } },
        startScale = 1.000,
        start = "A", goalRoom = "A",
        spawn = { 6.0, -19.2, 0.0 }, teach = nil,
        cine = {
            { 11.00, 7.50, -18.00, 0.00, 2.20, 14.00, 3.00 },
            { 6.00, 2.70, -18.60, 6.00, 2.50, 10.00, 1.80 },
            { 6.00, 1.70, -19.20, 6.00, 1.70, -11.20, 1.40 },
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
        -- ★重ねた事を 1.2 秒覚える(枠に寄ると自分が正面から外れて判定が切れるため)
        for i = 1, #gates do
            if self.gLink[i] then
                self.gHold[i] = { to = self.gLink[i], t = 1.2, s = self.gStr[i] }
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
            for _, dp in ipairs(self.cfg.dynprops or {}) do
                local e = ent(dp.ent)
                if e then
                    local q = e.transform.position
                    if math.sqrt((q.x - pl.x) ^ 2 + (q.z - pl.z) ^ 2) < pl.r
                       and math.abs(q.y - pl.y0) < 1.3 then
                        self.plateDone[pl.id] = true
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
            e.transform.rotation = Vec3.new(tl._a, 0, tl._c)
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
