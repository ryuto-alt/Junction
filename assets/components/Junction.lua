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
    ["Logic_Stage_1"] = { n = 1, scene = "scenes/stage1.json", next = "scenes/stage2.json",
        tunnels = {
            { id = "t1", ax = 6.000, az = -2.000, nx = 1.000, nz = 0.000, L = 4.00, sa = 1.000, sb = 0.500, wa = 2.00, wb = 1.00, y0 = 0.00 },
            { id = "t2", ax = 15.000, az = 3.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 0.500, sb = 2.000, wa = 1.00, wb = 4.00, y0 = 0.00 },
        },
        warps = {
        },
        morphs = {
            { id = "m1", x = 0.000, z = 7.600, wx = 0.000, wz = 0.000, r = 2.60, delay = 0.5, light = { 1.00, 0.62, 0.30 }, light0 = { 0.98, 0.96, 0.88 },
              room = "S", seal = {  }, unseal = { "t1a" },
              rows = { { "MorphA_m1_0", 5.40, 0.00, 2.60, "A" }, { "MorphB_m1_0", -5.20, 0.00, 3.00, "B" }, { "MorphB_m1_1", 4.60, 0.00, 1.00, "B" } } },
            { id = "m2", x = 14.300, z = 1.100, wx = 13.000, wz = 0.000, r = 3.00, delay = 0.8, light = { 0.62, 0.80, 1.00 }, light0 = { 0.98, 0.96, 0.88 },
              room = "B", seal = { "t1b" }, unseal = {  },
              rows = { { "MorphA_m2_0", 14.70, 0.00, -2.30, "A" }, { "MorphB_m2_0", 11.50, 0.00, 1.70, "B" } } },
        },
        plugs = {
            { id = "t1a", x = 6.500, y = 1.300, z = -2.000, mode = "appear", delay = 2.0, auto = true },
            { id = "t1b", x = 9.500, y = 0.650, z = -2.000, mode = "seal", delay = 2.0, auto = true },
        },
        hint = { { 4.80, -2.00 }, { 15.00, 1.80 }, { 11.00, 19.00 }, { 5.00, 19.00 } },
        start = "S", goalRoom = "C",
        spawn = { 2.0, -4.6, 0.0 }, teach = "walk",
        cine = {
            { 4.00, 2.20, -4.50, 0.00, 1.60, 5.80, 2.40 },
            { 2.00, 1.70, -4.60, 2.00, 1.60, 5.00, 1.40 },
            { 2.00, 1.70, -4.60, 2.00, 1.70, 3.40, 1.40 },
        } },
    ["Logic_Stage_2"] = { n = 2, scene = "scenes/stage2.json", next = "scenes/stage3.json",
        tunnels = {
            { id = "s1", ax = 4.000, az = 6.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 1.000, sb = 2.000, wa = 2.00, wb = 4.00, y0 = 0.00 },
            { id = "s2", ax = 6.000, az = -2.000, nx = 1.000, nz = 0.000, L = 4.00, sa = 1.000, sb = 0.500, wa = 2.00, wb = 1.00, y0 = 0.00 },
        },
        warps = {
        },
        morphs = {
        },
        plugs = {
        },
        hint = { { 4.00, 4.80 }, { -5.00, 22.00 }, { -9.00, 22.00 } },
        start = "A", goalRoom = "P",
        spawn = { 3.0, -4.0, 0.0 }, teach = "jump",
        cine = {
            { 7.00, 5.00, 13.00, -9.00, 1.20, 22.00, 2.40 },
            { 3.00, 1.70, -4.00, 2.00, 1.60, 6.00, 0.02 },
            { 3.00, 1.70, -4.00, 2.00, 1.60, 6.00, 1.60 },
            { 3.00, 1.70, -4.00, 3.00, 1.70, 4.00, 1.40 },
        } },
    ["Logic_Stage_3"] = { n = 3, scene = "scenes/stage3.json", next = "scenes/stage4.json",
        tunnels = {
            { id = "s1", ax = 0.000, az = 6.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 1.000, sb = 0.500, wa = 2.00, wb = 1.00, y0 = 0.90 },
        },
        warps = {
        },
        morphs = {
            { id = "m1", x = -7.900, z = 0.000, wx = 0.000, wz = 0.000, r = 2.80, delay = 0.6, light = { 0.72, 0.78, 0.98 }, light0 = { 0.98, 0.96, 0.88 },
              room = "A", seal = {  }, unseal = {  },
              rows = { { "MorphA_m1_0", 3.40, 0.00, -4.60, "A" }, { "MorphB_m1_0", -3.00, 0.00, 3.40, "B" }, { "MorphB_m1_1", -4.20, 0.00, -2.00, "B" } } },
            { id = "m2", x = 0.000, z = 14.500, wx = 0.000, wz = 13.000, r = 2.40, delay = 0.9, light = { 1.00, 0.66, 0.34 }, light0 = { 0.98, 0.96, 0.88 },
              room = "B", seal = { "s1b" }, unseal = {  },
              rows = { { "MorphA_m2_0", 0.80, 0.00, 12.50, "A" }, { "MorphB_m2_0", -0.50, 0.00, 11.50, "B" } } },
        },
        plugs = {
            { id = "s1b", x = 0.000, y = 1.550, z = 9.500, mode = "seal", delay = 2.0, auto = true },
        },
        hint = { { 0.00, 4.80 }, { 0.00, 12.00 }, { -1.40, 15.00 } },
        start = "A", goalRoom = "B",
        spawn = { 0.0, 1.0, 0.0 }, teach = nil,
        cine = {
            { 0.00, 2.40, -1.00, 0.00, 1.40, 6.00, 2.40 },
            { 0.00, 1.70, 0.60, 0.00, 1.50, 6.00, 1.60 },
            { 0.00, 1.70, 1.00, 0.00, 1.70, 9.00, 1.40 },
        } },
    ["Logic_Stage_4"] = { n = 4, scene = "scenes/stage4.json", next = "scenes/stage5.json",
        tunnels = {
            { id = "s1", ax = 0.000, az = 6.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 1.000, sb = 2.000, wa = 2.00, wb = 4.00, y0 = 0.00 },
        },
        warps = {
        },
        morphs = {
            { id = "m1", x = 7.900, z = 0.000, wx = 0.000, wz = 0.000, r = 2.80, delay = 0.5, light = { 1.00, 0.60, 0.28 }, light0 = { 0.98, 0.96, 0.88 },
              room = "A", seal = {  }, unseal = { "s1a" },
              rows = { { "MorphA_m1_0", 5.40, 0.00, 2.60, "A" }, { "MorphB_m1_0", -5.20, 0.00, 3.00, "B" }, { "MorphB_m1_1", 4.60, 0.00, 1.00, "B" } } },
            { id = "m2", x = -7.900, z = 0.000, wx = 0.000, wz = 0.000, r = 2.80, delay = 0.5, light = { 0.55, 0.72, 1.00 }, light0 = { 0.98, 0.96, 0.88 },
              room = "A", seal = { "f1" }, unseal = {  },
              rows = { { "MorphA_m2_0", 1.60, 0.00, -1.00, "A" }, { "MorphB_m2_0", -2.00, 0.00, -4.40, "B" } } },
        },
        plugs = {
            { id = "s1a", x = 0.000, y = 1.300, z = 6.500, mode = "appear", delay = 2.0, auto = true },
            { id = "f1", x = 6.500, y = 1.300, z = 0.000, mode = "seal", delay = 2.0, auto = true },
        },
        hint = { { 0.00, 4.80 }, { -5.00, 22.00 }, { -9.00, 22.00 } },
        start = "A", goalRoom = "C",
        spawn = { 0.0, -4.0, 90.0 }, teach = nil,
        cine = {
            { 0.00, 2.40, -4.60, 6.00, 1.60, 0.00, 2.40 },
            { 0.00, 1.70, -4.00, 6.00, 1.60, 0.00, 1.40 },
            { 0.00, 1.70, -4.00, 8.00, 1.70, -4.00, 1.40 },
        } },
    ["Logic_Stage_5"] = { n = 5, scene = "scenes/stage5.json", next = "scenes/stage6.json",
        tunnels = {
            { id = "s1", ax = -6.000, az = -10.000, nx = 0.000, nz = -1.000, L = 4.00, sa = 1.000, sb = 2.000, wa = 2.00, wb = 4.00, y0 = 0.00 },
            { id = "s2", ax = 0.000, az = -54.000, nx = 0.000, nz = -1.000, L = 4.00, sa = 2.000, sb = 0.500, wa = 4.00, wb = 1.00, y0 = 0.90 },
        },
        warps = {
        },
        morphs = {
        },
        plugs = {
        },
        hint = { { -6.00, -8.80 }, { 0.00, -30.00 }, { 0.00, -52.80 }, { 1.25, -61.00 }, { 2.30, -62.50 } },
        start = "H", goalRoom = "T",
        spawn = { -6.0, -6.0, 180.0 }, teach = nil,
        cine = {
            { -10.00, 7.00, -20.00, 0.00, 1.00, -48.00, 2.60 },
            { -4.00, 1.70, -2.00, -6.00, 1.50, -10.00, 0.02 },
            { -4.00, 1.70, -2.00, -6.00, 1.50, -10.00, 1.60 },
            { -6.00, 1.70, -6.00, -6.00, 1.70, -14.00, 1.40 },
        } },
    ["Logic_Stage_6"] = { n = 6, scene = "scenes/stage6.json", next = "scenes/stage7.json",
        tunnels = {
            { id = "s1", ax = 6.000, az = 0.000, nx = 1.000, nz = 0.000, L = 4.00, sa = 1.000, sb = 2.000, wa = 2.00, wb = 4.00, y0 = 0.00 },
            { id = "s2", ax = 22.000, az = 12.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 2.000, sb = 1.000, wa = 4.00, wb = 2.00, y0 = 0.00 },
            { id = "s3", ax = 28.000, az = 22.000, nx = 1.000, nz = 0.000, L = 4.00, sa = 1.000, sb = 0.500, wa = 2.00, wb = 1.00, y0 = 0.00 },
        },
        warps = {
        },
        morphs = {
            { id = "m1", x = 22.000, z = 17.600, wx = 22.000, wz = 22.000, r = 3.40, delay = 1.0, light = { 0.98, 0.94, 0.86 }, light0 = { 0.98, 0.96, 0.88 },
              room = "C", seal = {  }, unseal = {  },
              rows = { { "MorphA_m1_0", 25.40, 0.00, 17.40, "A" }, { "MorphB_m1_0", 19.00, 0.00, 25.00, "B" } } },
        },
        plugs = {
        },
        hint = { { 4.80, 0.00 }, { 22.00, 10.80 }, { 26.80, 22.00 }, { 36.25, 22.00 }, { 37.30, 23.50 } },
        start = "A", goalRoom = "D",
        spawn = { 3.0, -3.0, 0.0 }, teach = nil,
        cine = {
            { 26.00, 1.70, 18.00, 21.00, 1.40, 26.00, 2.20 },
            { 2.00, 1.70, -4.50, 6.00, 1.50, 0.00, 0.02 },
            { 2.00, 1.70, -4.50, 6.00, 1.50, 0.00, 1.60 },
            { 3.00, 1.70, -3.00, 3.00, 1.70, 5.00, 1.40 },
        } },
    ["Logic_Stage_7"] = { n = 7, scene = "scenes/stage7.json", next = "scenes/stage8.json",
        tunnels = {
            { id = "s1", ax = 0.000, az = 6.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 1.000, sb = 2.000, wa = 2.00, wb = 4.00, y0 = 0.00 },
            { id = "s2", ax = -8.800, az = 34.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 2.000, sb = 0.500, wa = 4.00, wb = 1.00, y0 = 0.90 },
            { id = "s3", ax = -7.300, az = 44.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 0.500, sb = 2.000, wa = 1.00, wb = 4.00, y0 = 0.00 },
        },
        warps = {
        },
        morphs = {
            { id = "m1", x = 0.000, z = -8.000, wx = 0.000, wz = 0.000, r = 2.80, delay = 0.5, light = { 0.62, 0.74, 1.00 }, light0 = { 0.98, 0.96, 0.88 },
              room = "A", seal = {  }, unseal = {  },
              rows = { { "MorphA_m1_0", 3.40, 0.00, -4.60, "A" }, { "MorphB_m1_0", -3.00, 0.00, 3.40, "B" }, { "MorphB_m1_1", -4.20, 0.00, -2.00, "B" } } },
        },
        plugs = {
        },
        hint = { { 0.00, 4.80 }, { -7.00, 22.00 }, { -8.80, 32.80 }, { -7.55, 41.00 }, { -7.30, 42.80 }, { -14.30, 60.00 }, { -16.30, 60.00 } },
        start = "A", goalRoom = "E",
        spawn = { 0.0, -4.0, 0.0 }, teach = nil,
        cine = {
            { -9.30, 5.00, 52.00, -16.50, 1.00, 60.00, 2.40 },
            { 0.00, 1.70, -4.40, 0.00, 1.60, 6.00, 0.02 },
            { 0.00, 1.70, -4.40, 0.00, 1.60, 6.00, 1.60 },
            { 0.00, 1.70, -4.00, 0.00, 1.70, 4.00, 1.40 },
        } },
    ["Logic_Stage_8"] = { n = 8, scene = "scenes/stage8.json", next = nil,
        tunnels = {
            { id = "s1", ax = 0.000, az = 6.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 1.000, sb = 2.000, wa = 2.00, wb = 4.00, y0 = 0.00 },
            { id = "s2", ax = 12.000, az = 22.000, nx = 1.000, nz = 0.000, L = 4.00, sa = 2.000, sb = 0.500, wa = 4.00, wb = 1.00, y0 = 0.90 },
            { id = "s3", ax = 20.500, az = 25.000, nx = 0.000, nz = 1.000, L = 4.00, sa = 0.500, sb = 2.000, wa = 1.00, wb = 4.00, y0 = 0.00 },
        },
        warps = {
        },
        morphs = {
            { id = "m1", x = 0.000, z = -8.000, wx = 0.000, wz = 0.000, r = 2.80, delay = 0.5, light = { 1.00, 0.58, 0.26 }, light0 = { 0.98, 0.96, 0.88 },
              room = "A", seal = {  }, unseal = {  },
              rows = { { "MorphA_m1_0", 5.40, 0.00, 2.60, "A" }, { "MorphB_m1_0", -5.20, 0.00, 3.00, "B" }, { "MorphB_m1_1", 4.60, 0.00, 1.00, "B" } } },
            { id = "m2", x = 19.000, z = 20.900, wx = 19.000, wz = 22.000, r = 2.40, delay = 0.9, light = { 0.58, 0.74, 1.00 }, light0 = { 0.98, 0.96, 0.88 },
              room = "C", seal = { "s2b" }, unseal = {  },
              rows = { { "MorphA_m2_0", 20.70, 0.00, 19.70, "A" }, { "MorphB_m2_0", 18.00, 0.00, 23.50, "B" } } },
        },
        plugs = {
            { id = "s2b", x = 15.500, y = 1.550, z = 22.000, mode = "seal", delay = 2.0, auto = true },
        },
        hint = { { 0.00, 4.80 }, { 5.00, 22.00 }, { 10.80, 22.00 }, { 20.25, 22.00 }, { 20.50, 23.80 }, { 25.50, 41.00 }, { 29.00, 41.00 } },
        start = "A", goalRoom = "D",
        spawn = { 0.0, -4.0, 0.0 }, teach = nil,
        cine = {
            { 22.50, 5.00, 33.00, 29.00, 1.00, 41.00, 2.40 },
            { 0.00, 1.70, -4.40, 0.00, 1.60, 6.00, 0.02 },
            { 0.00, 1.70, -4.40, 0.00, 1.60, 6.00, 1.60 },
            { 0.00, 1.70, -4.00, 0.00, 1.70, 4.00, 1.40 },
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
    self.shownScale = 1.0
    self.side = {}
    self.hintIdx = 1
    self.warpLeft = {}
    for i, w in ipairs(self.cfg.warps or {}) do self.warpLeft[i] = w.loops end
    self.warpSide = {}
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
    self.checkpoint = { x = p[1], z = p[2], s = 1.0, yaw = p[3], y0 = 0.0 }
    hide("Pilot"); hide("PilotLight")
    scene:setAmbient(0.035)
    useBody(self, 1.0, p[1], p[2], 1.0)
    saveNum("pscale", 1.0)
    camSet(self, p[1], EYE_H, p[2], p[3], 0)
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
    for i = 1, 9 do
        if keyPressed(tostring(i)) then
            local s = STAGES["Logic_Stage_" .. i]
            if s and s.scene and self.cfg.n ~= i then loadScene(s.scene); return end
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
        if self.flash >= 1 then loadScene(self.cfg.next or "scenes/stage1.json") end
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
                inT = true
                local k = math.max(0, math.min(1, t / tn.L))
                self.shownScale = tn.sa + (tn.sb - tn.sa) * k
                local want
                if t < 0.35 then want = tn.sa
                elseif t > tn.L - 0.35 then want = tn.sb
                else want = math.min(tn.sa, tn.sb) end
                if math.abs(want - self.scale) > 1e-4 then
                    useBody(self, want, p.x, p.z, 0.05, tn.y0)
                    if t > tn.L * 0.5 then
                        self.checkpoint = { x = p.x, z = p.z, s = want, yaw = loadNum("camYaw", 0), y0 = tn.y0 }
                    end
                    log(string.format("JUNCTION body %.3g at tunnel %s t=%.2f", want, tn.id, t))
                end
                break
            end
        end
    end
    self.inTunnel = inT

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
                local b = bodyEnt(self)
                if b then
                    local q = Vec3.new(p.x + w.dx, p.y + w.dy, p.z + w.dz)
                    physics:setPosition(b, q)
                    b.transform.position = q
                    self.anchor = { x = q.x, z = q.z, y0 = (self.anchor.y0 or 0) + w.dy }
                    self.checkpoint = { x = q.x, z = q.z, s = self.scale, yaw = loadNum("camYaw", 0),
                                        y0 = (self.checkpoint.y0 or 0) + w.dy }
                    self.side = {}
                    log(string.format("JUNCTION warp %s (%d left)", w.id, self.warpLeft[i]))
                end
                self.warpSide[i] = nil
                break
            end
            self.warpSide[i] = near and side or nil
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

    local help = keyDown("H")
    local stuck = self.noAct > 12.0
    keyCap(W * 0.5, H - 62, "W A S D", 22,
           uiAnim(self, "move", help or stuck or not learned("move"), dt, 6))
    keyCap(W * 0.5, H - 130, "SPACE", 22,
           uiAnim(self, "jumpkey",
                  help or stuck or (learned("move") and not learned("jump")), dt, 6))
end
