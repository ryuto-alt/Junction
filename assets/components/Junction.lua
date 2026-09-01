-- ============================================================================
-- JUNCTION / 継ぎ目 — ゲームロジック本体。シーンに 1 つだけ置く空エンティティに付ける。
-- エンティティ名 "Logic_Stage_1" .. "Logic_Stage_8" でステージ設定を引く。
--
-- ★2026-09-01(3) 全面改修: 【文字でルールを説明しない】
--   出す文字は操作キー(WASD/E/Q/R)だけ。ルールは
--     ① 開幕のカメラワーク  ② ドア固有色  ③ 床の色レーンと柱  ④ 案内の光(Pilot)
--   で教える。以前の objective 行 / 下段の解説パネル / [H] のルール全文は全部消した。
--   面をまたぐ進行も文字なし(クリア→白フェード→次の面へ自動で進む)。
--
-- ★教え方の設計(1 面につき新しい事は 1 つだけ):
--   1 触れて繋いで通る(候補1枚・失敗しようがない) / 2 3枚合流と角度 /
--   3 予算と繋ぎ直し / 4 二つの出口(GDD の面) / 5 遠近の錯覚 /
--   6 四枚合流(40°) / 7 五枚合流(30°) / 8 一棟
--
-- ★カメラ演出は task.spawn + wait のコルーチンで書く(time.after の入れ子は読めない)。
--   演出中は saveNum("cineLock",1) で FreeLook の入力を止め、位置は
--   physics:setPosition で毎フレーム押し込む(スクリプトは物理より前に走るので
--   transform へ書くだけでは CharacterController の同期に上書きされる)。
--
-- ★角度は【WASD の押し方向】で測る。カメラの向きでも実速度でもない:
--   ・カメラの向き … 歩きながら見回すだけで行き先が変わってしまう
--   ・実速度       … ドア際で壁ズリすると自分の意図と違う向きになる
--   FreeLook.lua が saveNum("moveX"/"moveZ") へ書く。書き手はあそこ 1 箇所。
--
-- ★エンティティ名の規約(source/gen_stages.py と対。片方だけ変えると無言で壊れる):
--     Door_<id> / Void_<id> / VoidLight_<id> / Frame_<id>_*
--     Mark_<id>_1..5   合流点の刻印
--     Slice_<id>_1..6  角度の境界線
--     Lane_<id>_1..5   助走レーン(行き先の色)
--     Post_<id>_1..5   レーンの先に立つ柱(行き先の色)
--     Proxy_1..8       虚無に浮かぶ候補。全ドアで使い回す
--     Pilot / PilotLight  案内の光
-- ============================================================================

local STAGES = {
-- >>>STAGES (source/gen_stages.py が自動生成)
    ["Logic_Stage_1"] = { n = 1, scene = "scenes/stage1.json", next = "scenes/stage2.json",
        doors = { "a", "g" },
        room = { a = "S", g = "G" },
        budget = 1, start = "S", goalRoom = "G",
        spawn = { 0.0, 1.7, -3.5, 0.0 }, timed = false, teach = "connect" },
    ["Logic_Stage_2"] = { n = 2, scene = "scenes/stage2.json", next = "scenes/stage3.json",
        doors = { "a", "d", "g" },
        room = { a = "S", d = "A", g = "G" },
        budget = 3, start = "S", goalRoom = "G",
        spawn = { 0.0, 1.7, -3.5, 0.0 }, timed = false, teach = "angle" },
    ["Logic_Stage_3"] = { n = 3, scene = "scenes/stage3.json", next = "scenes/stage4.json",
        doors = { "a", "b", "g" },
        room = { a = "S", b = "A", g = "G" },
        budget = 3, start = "S", goalRoom = "G",
        spawn = { 0.0, 1.7, -3.5, 0.0 }, timed = true, teach = nil },
    ["Logic_Stage_4"] = { n = 4, scene = "scenes/stage4.json", next = "scenes/stage5.json",
        doors = { "a", "b", "c", "d" },
        room = { a = "S", b = "P", c = "Q", d = "G" },
        budget = 2, start = "S", goalRoom = "G",
        spawn = { 0.0, 1.7, -3.5, 0.0 }, timed = true, teach = nil },
    ["Logic_Stage_5"] = { n = 5, scene = "scenes/stage5.json", next = "scenes/stage6.json",
        doors = { "a", "b", "c", "d", "g" },
        room = { a = "S", b = "P", c = "Q", d = "R", g = "G" },
        budget = 3, start = "S", goalRoom = "G",
        spawn = { 0.0, 1.7, -3.5, 0.0 }, timed = true, teach = nil },
    ["Logic_Stage_6"] = { n = 6, scene = "scenes/stage6.json", next = "scenes/stage7.json",
        doors = { "a", "b", "c", "d", "g" },
        room = { a = "S", b = "P", c = "Q", d = "R", g = "G" },
        budget = 4, start = "S", goalRoom = "G",
        spawn = { 0.0, 1.7, -3.5, 0.0 }, timed = true, teach = nil },
    ["Logic_Stage_7"] = { n = 7, scene = "scenes/stage7.json", next = "scenes/stage8.json",
        doors = { "a", "b", "c", "d", "e", "f", "g" },
        room = { a = "S", b = "T", c = "P", d = "Q", e = "T", f = "U", g = "G" },
        budget = 4, start = "S", goalRoom = "G",
        spawn = { 0.0, 1.7, -3.5, 0.0 }, timed = true, teach = nil },
    ["Logic_Stage_8"] = { n = 8, scene = "scenes/stage8.json", next = nil,
        doors = { "a", "b", "c", "d", "e", "f", "g", "h" },
        room = { a = "S", b = "T", c = "P", d = "Q", e = "P", f = "U", g = "G", h = "S" },
        budget = 3, start = "S", goalRoom = "G",
        spawn = { 0.0, 1.7, -3.5, 0.0 }, timed = true, teach = nil },
    -- <<<STAGES
}

-- ★gen_stages.py の DOOR_COLORS と必ず一致させること
local DOOR_COLOR = {
    a = { 0.20, 0.85, 0.55 }, b = { 1.00, 0.55, 0.12 }, c = { 0.95, 0.25, 0.45 },
    d = { 0.30, 0.60, 1.00 }, e = { 0.80, 0.40, 1.00 }, f = { 0.20, 0.90, 0.95 },
    g = { 1.00, 0.82, 0.15 }, h = { 1.00, 0.45, 0.72 },
}

local MAX_JUNCTION = 5      -- 合流点の上限。6 枚目で崩壊
local FAN_DEG      = 60.0   -- ドア正面 ±この角度を等分する
local TIME_LIMIT   = 180.0
local REACH        = 3.2    -- ドアに触れられる距離
local ENTER_DIST   = 1.05
local ENTER_LAT    = 0.85
local ENTER_DOT    = 0.30
local HIDE_Y       = -200.0
local FADE_TIME    = 0.20
local LINE_LEN     = 3.6
local POST_DIST    = 3.5    -- 柱を立てる距離(レーンの先端)

local C_BOUND     = { 0.42, 0.44, 0.42 }
local C_BOUND_HOT = { 0.85, 0.90, 0.85 }
local C_KEY       = { 0.95, 0.99, 0.94 }
local C_DIM       = { 0.55, 0.60, 0.56 }

-- ---------------------------------------------------------------- 小道具

local atan2 = math.atan2 or function(y, x) return math.atan(y, x) end

local function rot2(vx, vz, deg)
    -- (x,z) 平面の回転。正の deg = プレイヤーから見て【左】
    -- 検算: rot((0,1), -90) = (1,0) = yaw0 の右。これが崩れると左右が入れ替わる
    local c, s = math.cos(math.rad(deg)), math.sin(math.rad(deg))
    return vx * c - vz * s, vx * s + vz * c
end

local function signedAngle(ox, oz, dx, dz)
    return math.deg(atan2(ox * dz - oz * dx, ox * dx + oz * dz))
end

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

-- ★白い虚無の上では淡い色が全部おなじ「くすんだ黄土」に見える(橙と黄が判別不能だった)。
--   無彩色ぶん(min チャンネル)を抜いて彩度を上げてから塗る。虚無の中でだけ使う。
local function vivid(c)
    local mn = math.min(c[1], c[2], c[3]) * 0.9
    local r, g, b = c[1] - mn, c[2] - mn, c[3] - mn
    local mx = math.max(r, g, b, 0.001)
    return { r / mx, g / mx, b / mx }
end

local function tint(name, c, k)
    local e = ent(name)
    if e then
        k = k or 1
        scene:setColor(e, c[1] * k, c[2] * k, c[3] * k)
    end
end

-- ---------------------------------------------------------------- カメラ演出
-- 演出中は self.cam(位置と向き)が正。OnUpdate が毎フレーム押し込む。

local function camApply(self)
    local pl = ent("MainCamera")
    if not pl then return end
    local c = self.cam
    physics:setPosition(pl, Vec3.new(c.x, c.y, c.z))
    pl.transform.position = Vec3.new(c.x, c.y, c.z)   -- 同フレームの見た目用
    pl.transform.rotation = Vec3.new(-c.pitch, c.yaw, 0)
end

local function camSet(self, x, y, z, yaw, pitch)
    local c = self.cam
    c.x, c.y, c.z, c.yaw, c.pitch = x, y, z, yaw, pitch
end

-- 現在地から目標へ滑らかに。task.spawn の中からだけ呼ぶ(wait を使うため)
local function camGo(self, x, y, z, yaw, pitch, dur)
    local c = self.cam
    local sx, sy, sz, sw, sp = c.x, c.y, c.z, c.yaw, c.pitch
    local dw = ((yaw - sw + 180) % 360) - 180     -- yaw は最短方向で回す
    local t = 0
    while t < dur do
        t = t + time.dt()
        local k = math.min(1, t / dur)
        k = k * k * (3 - 2 * k)                   -- smoothstep(緩急)
        c.x, c.y, c.z = sx + (x - sx) * k, sy + (y - sy) * k, sz + (z - sz) * k
        c.yaw, c.pitch = sw + dw * k, sp + (pitch - sp) * k
        wait(0)
    end
    camSet(self, x, y, z, yaw, pitch)
end

-- p から q を見る yaw/pitch
local function lookAt(px, py, pz, qx, qy, qz)
    local dx, dy, dz = qx - px, qy - py, qz - pz
    local flat = math.sqrt(dx * dx + dz * dz)
    return math.deg(atan2(dx, dz)), math.deg(atan2(dy, math.max(0.001, flat)))
end

local function cineBegin(self)
    self.cine = true
    self.flash = 0
    saveNum("cineLock", 1)
end

local function cineEnd(self)
    -- 演出の最後は必ずプレイヤーの目の高さへ返す
    local c = self.cam
    local pl = ent("MainCamera")
    if pl then physics:setPosition(pl, Vec3.new(c.x, 1.7, c.z)) end
    self.tpSeq = (self.tpSeq or 0) + 1
    saveNum("tpYaw", c.yaw)
    saveNum("tpPitch", 0)
    saveNum("tpSeq", self.tpSeq)
    saveNum("cineLock", 0)
    self.cine = false
    self.cool = 0.4
end

-- ---------------------------------------------------------------- 状態

-- ★前方宣言。resetRun は refreshDoors より先に書いてあるので、これが無いと
--   local の上位値ではなくグローバル(=nil)を引いて OnStart で必ず落ちる。
local refreshDoors
local introCine

local function resetRun(self)
    if self.task then task.cancel(self.task); self.task = nil end
    self.group = {}          -- doorId -> gid
    self.groups = {}         -- gid -> { doorId, ... }  (順番 = 合流点に入った順)
    self.nextGid = 1
    self.budget = self.cfg.budget
    self.timeLeft = TIME_LIMIT
    self.room = self.cfg.start
    self.mode = "play"
    self.connectDoor = nil
    self.fade = 0
    self.flash = 0
    self.cool = 0.35
    self.moveX, self.moveZ = 0, 1
    self.taught = false
    self.showKeys = 7.0      -- 開幕だけ操作キーを出す秒数
    self.hint = 0
    -- ★残り30秒で落とした照明を戻す。ここを忘れると [R] で再開した面が暗いままになる
    scene:setAmbient(0.035)

    local p = self.cfg.spawn
    camSet(self, p[1], p[2], p[3], p[4], 0)
    local pl = ent("MainCamera")
    if pl then
        physics:setPosition(pl, Vec3.new(p[1], p[2], p[3]))
        self.tpSeq = (self.tpSeq or 0) + 1
        saveNum("tpYaw", p[4]); saveNum("tpPitch", 0); saveNum("tpSeq", self.tpSeq)
    end
    refreshDoors(self)
    -- ★開幕演出はここで task.spawn しない。OnStart は OnPlayStart の中で走るので、
    --   その後に走るタスク機構のクリアで【黙って消される】(開幕カメラが出なかった)。
    --   次の OnUpdate で仕掛ける。
    self.pendingIntro = true
end

function OnStart(self)
    self.cfg = STAGES[self.name]
    if not self.cfg then
        logError("Junction: 未知のステージ名 " .. tostring(self.name))
        return
    end
    self.cam = { x = 0, y = 1.7, z = 0, yaw = 0, pitch = 0 }
    self.doors = {}
    for _, id in ipairs(self.cfg.doors) do
        local e = ent("Door_" .. id)
        if not e then
            logError("Junction: Door_" .. id .. " が無い")
        else
            local p, yaw = e.transform.position, e.transform.rotation.y
            local ix, iz = math.sin(math.rad(yaw)), math.cos(math.rad(yaw))
            self.doors[id] = {
                x = p.x, z = p.z, yaw = yaw,
                inX = ix, inZ = iz,        -- 部屋の内側
                outX = -ix, outZ = -iz,    -- 抜ける向き
                rgX = math.cos(math.rad(yaw)), rgZ = -math.sin(math.rad(yaw)),
            }
        end
    end
    self.goal = ent("Goal")

    -- ★蛍光灯の明滅。リミナルの匂いはここが 8 割。1 部屋に 1 本だけ壊れている
    local n = 0
    for _, id in ipairs(self.cfg.doors) do
        local L = ent(self.cfg.room[id] .. "_Light_1")
        n = n + 1
        if L and L:light() and n % 2 == 1 then
            Flicker(L:light(), n % 4 == 1 and "broken" or "fluorescent")
        end
    end

    resetRun(self)
    log("JUNCTION stage " .. self.cfg.n .. " / doors=" .. #self.cfg.doors ..
        " budget=" .. self.cfg.budget)
end

-- 合流点の見た目(刻印・境界線・助走レーン・柱)を全ドアぶん引き直す。
-- 接続/崩壊/リセットの直後にだけ呼ぶ。毎フレームは回さない。
function refreshDoors(self)
    for _, id in ipairs(self.cfg.doors) do
        local d = self.doors[id]
        local gid = self.group[id]
        local list = gid and self.groups[gid] or nil
        local n = list and #list or 0

        for k = 1, 5 do hide("Mark_" .. id .. "_" .. k) end
        for k = 1, 6 do hide("Slice_" .. id .. "_" .. k) end
        for k = 1, 5 do hide("Lane_" .. id .. "_" .. k); hide("Post_" .. id .. "_" .. k) end

        if n >= 2 then
            -- ---- 刻印(この枠が合流点の何番目か) ----
            local idx = 1
            for i, m in ipairs(list) do if m == id then idx = i end end
            for k = 1, idx do
                local off = (k - (idx + 1) * 0.5) * 0.17
                place("Mark_" .. id .. "_" .. k,
                      d.x + d.rgX * off + d.inX * 0.26, 2.90, d.z + d.rgZ * off + d.inZ * 0.26,
                      d.yaw, 0.09, 0.24, 0.05)
            end

            -- ---- 出口ごとの助走レーンと柱(行き先のドア色) ----
            local exits = {}
            for _, m in ipairs(list) do if m ~= id then exits[#exits + 1] = m end end
            local nex = #exits
            local w = (FAN_DEG * 2) / nex

            -- 境界線は nex+1 本。色は付けない(色はレーンが持つ)
            for k = 1, nex + 1 do
                local ang = FAN_DEG - w * (k - 1)
                local dx, dz = rot2(d.outX, d.outZ, ang)
                place("Slice_" .. id .. "_" .. k,
                      d.x - dx * LINE_LEN * 0.5, 0.012, d.z - dz * LINE_LEN * 0.5,
                      math.deg(atan2(dx, dz)), 0.05, 0.02, LINE_LEN)
                tint("Slice_" .. id .. "_" .. k, C_BOUND)
            end

            -- レーン中心線 + 柱。スライス k の中心角は FAN_DEG - w*(k-0.5)
            for k = 1, nex do
                local col = DOOR_COLOR[exits[k]] or { 1, 1, 1 }
                local ang = FAN_DEG - w * (k - 0.5)
                local dx, dz = rot2(d.outX, d.outZ, ang)
                place("Lane_" .. id .. "_" .. k,
                      d.x - dx * LINE_LEN * 0.5, 0.02, d.z - dz * LINE_LEN * 0.5,
                      math.deg(atan2(dx, dz)), 0.13, 0.02, LINE_LEN)
                tint("Lane_" .. id .. "_" .. k, col, 0.75)
                place("Post_" .. id .. "_" .. k,
                      d.x - dx * POST_DIST, 0.58, d.z - dz * POST_DIST,
                      math.deg(atan2(dx, dz)), 0.15, 1.15, 0.15)
                tint("Post_" .. id .. "_" .. k, col)
            end
        end
    end
end

-- ---------------------------------------------------------------- 接続

local function groupOf(self, id)
    local gid = self.group[id]
    return gid and self.groups[gid] or nil
end

local function exitsOf(self, id)
    local list = groupOf(self, id)
    local out = {}
    if list then
        for _, m in ipairs(list) do if m ~= id then out[#out + 1] = m end end
    end
    return out
end

-- ---------------------------------------------------------------- 演出本体

-- 開幕: 出口の部屋を見せてから、開始の部屋のドアへ寄る。
-- 「あの緑の柱まで行け」「使えるのはこのドア」を文字なしで渡すのが目的。
function introCine(self)
    local sp = self.cfg.spawn
    -- 開始の部屋にあるドア(最初の 1 枚)
    local first
    for _, id in ipairs(self.cfg.doors) do
        if self.cfg.room[id] == self.cfg.start and not first then first = id end
    end
    local d = self.doors[first]
    local g = self.goal and self.goal.transform.position or nil

    cineBegin(self)
    self.task = task.spawn(function()
        -- ① 出口の部屋。緑の柱をゆっくり寄って見せる
        if g then
            local y1, p1 = lookAt(g.x + 5.0, 3.4, g.z - 5.2, g.x, 1.2, g.z)
            camSet(self, g.x + 5.0, 3.4, g.z - 5.2, y1, p1)
            self.flash = 1.0
            camGo(self, g.x + 2.2, 2.0, g.z - 2.6, y1, p1 - 4, 2.2)
            wait(0.25)
        end
        -- ② 開始の部屋。引きで部屋全体 → ドアへ寄る
        local y2, p2 = lookAt(sp[1], 3.2, sp[3] - 1.0, d.x, 1.5, d.z)
        camSet(self, sp[1] - 4.0, 3.2, sp[3] - 2.0, y2 - 38, 2)
        self.flash = 1.0
        camGo(self, sp[1], 2.6, sp[3] - 1.0, y2, p2, 2.6)
        -- ③ プレイヤーの目線へ降りる
        camGo(self, sp[1], 1.7, sp[3], y2, 0, 1.0)
        cineEnd(self)
    end)
end

-- 角度の授業: 合流点が 3 枚以上になった最初の 1 回だけ。
-- ドアの真上から扇を見下ろし、色レーンを 1 本ずつ舐める。文字は 1 文字も出さない。
local function teachAngle(self, id)
    local d = self.doors[id]
    local exits = exitsOf(self, id)
    if #exits < 2 then return end
    local px, pz = self.cam.x, self.cam.z
    local w = (FAN_DEG * 2) / #exits

    cineBegin(self)
    self.task = task.spawn(function()
        -- ① ドアの真上へ上がって扇全体を見下ろす
        local ax, az = d.x - d.outX * 4.5, d.z - d.outZ * 4.5
        local y1, p1 = lookAt(ax, 7.0, az, d.x, 0.2, d.z)
        camGo(self, ax, 7.0, az, y1, p1, 1.5)
        wait(0.5)
        -- ② レーンを 1 本ずつ。柱の真上から、ドアの方を見る
        for k = 1, #exits do
            local ang = FAN_DEG - w * (k - 0.5)
            local dx, dz = rot2(d.outX, d.outZ, ang)
            local lx, lz = d.x - dx * (POST_DIST + 0.6), d.z - dz * (POST_DIST + 0.6)
            local y2, p2 = lookAt(lx, 2.4, lz, d.x, 1.3, d.z)
            camGo(self, lx, 2.4, lz, y2, p2, 1.1)
            -- 見ているレーンだけ強く光らせる
            for j = 1, #exits do
                tint("Lane_" .. id .. "_" .. j, DOOR_COLOR[exits[j]] or { 1, 1, 1 },
                     (j == k) and 1.6 or 0.30)
                tint("Post_" .. id .. "_" .. j, DOOR_COLOR[exits[j]] or { 1, 1, 1 },
                     (j == k) and 1.6 or 0.30)
            end
            -- そのレーンから助走したら出るドアを、色の弾で示す
            local od = self.doors[exits[k]]
            local c = DOOR_COLOR[exits[k]] or { 1, 1, 1 }
            fx:burst{ x = d.x + d.inX * 0.4, y = 1.4, z = d.z + d.inZ * 0.4, kind = "glow",
                      count = 20, size = 0.4, r = c[1], g = c[2], b = c[3] }
            wait(0.85)
        end
        for j = 1, #exits do
            tint("Lane_" .. id .. "_" .. j, DOOR_COLOR[exits[j]] or { 1, 1, 1 }, 0.75)
            tint("Post_" .. id .. "_" .. j, DOOR_COLOR[exits[j]] or { 1, 1, 1 }, 1.0)
        end
        -- ③ 元居た場所へ戻す
        local y3, p3 = lookAt(px, 1.7, pz, d.x, 1.4, d.z)
        camGo(self, px, 1.7, pz, y3, 0, 1.0)
        cineEnd(self)
    end)
end

-- ---------------------------------------------------------------- 接続の実行

local function connect(self, from, to)
    if self.budget <= 0 then
        self.hint = 0.8
        return
    end
    self.budget = self.budget - 1

    local gid = self.group[from]
    if not gid then
        gid = self.nextGid
        self.nextGid = self.nextGid + 1
        self.groups[gid] = { from }
        self.group[from] = gid
    end
    local list = self.groups[gid]

    -- ---- 上限 5 枚。6 枚目で合流点そのものが崩壊し、予算は戻らない ----
    if #list + 1 > MAX_JUNCTION then
        for _, m in ipairs(list) do self.group[m] = nil end
        self.groups[gid] = nil
        fx:pulse(1.0)
        local fd = self.doors[from]
        fx:burst{ x = fd.x, y = 1.4, z = fd.z, kind = "smoke", count = 40, size = 0.7,
                  r = 0.9, g = 0.2, b = 0.15 }
        refreshDoors(self)
        return
    end

    table.insert(list, to)
    self.group[to] = gid
    self.cool = 0.5   -- 繋いだ直後の 1 歩で通過しない猶予
    local td = self.doors[to]
    local c = DOOR_COLOR[to] or { 1, 1, 1 }
    fx:burst{ x = td.x, y = 1.4, z = td.z, kind = "glow", count = 14, size = 0.35,
              r = c[1], g = c[2], b = c[3] }
    refreshDoors(self)

    -- ★角度の授業は「3 枚合流が初めてできた瞬間」に 1 回だけ
    if not self.taught and #list >= 3 and self.cfg.teach == "angle" then
        self.taught = true
        teachAngle(self, from)
    end
end

-- 出口までの到達可能性(孤立の即時判定)。部屋 -> 部屋を合流点で辿るだけ
local function reachable(self)
    local seen = { [self.room] = true }
    local changed = true
    while changed do
        changed = false
        for _, id in ipairs(self.cfg.doors) do
            if seen[self.cfg.room[id]] then
                local list = groupOf(self, id)
                if list then
                    for _, m in ipairs(list) do
                        local r = self.cfg.room[m]
                        if not seen[r] then seen[r] = true; changed = true end
                    end
                end
            end
        end
    end
    return seen[self.cfg.goalRoom] == true
end

-- ---------------------------------------------------------------- 接続モード

local function openConnect(self, id)
    local cand = {}
    for _, o in ipairs(self.cfg.doors) do
        if o ~= id and not self.group[o] then cand[#cand + 1] = o end
    end
    if #cand == 0 then self.hint = 0.8; return end
    local d = self.doors[id]
    table.sort(cand, function(p, q)
        return signedAngle(d.outX, d.outZ, self.doors[p].x - d.x, self.doors[p].z - d.z)
             > signedAngle(d.outX, d.outZ, self.doors[q].x - d.x, self.doors[q].z - d.z)
    end)

    self.mode = "connect"
    self.connectDoor = id
    self.cand = cand
    self.aim = nil
    self.holdE = 0.28   -- 開いた同じ E で確定しないための不感時間

    -- 白板を奥へ飛ばして「虚無の背景」にする。11x8 だと開口の縁から部屋の外(素の黒)が
    -- 覗いて白い虚無が黒い額縁に見えるので、±70° を覆う大きさが要る
    place("Void_" .. id, d.x + d.outX * 13.0, 3.0, d.z + d.outZ * 13.0, nil, 64.0, 48.0, 8.0)
    local vl = ent("VoidLight_" .. id)
    if vl then
        vl.transform.position = Vec3.new(d.x + d.outX * 4.2, 1.9, d.z + d.outZ * 4.2)
        local L = vl:light()
        if L then L.intensity = 90.0; L.range = 22.0 end
    end

    -- ★横並びは【プレイヤーから見た左右】で置く。ドアの right はドア自身の
    --   forward(部屋の内側)基準なので、向き合うプレイヤーからは左右が反転している
    local prX, prZ = -d.rgX, -d.rgZ
    local span = 1.5
    for i, o in ipairs(cand) do
        local t = (#cand == 1) and 0 or ((i - 1) / (#cand - 1) * 2 - 1)
        local od = self.doors[o]
        local dist = math.sqrt((od.x - d.x) ^ 2 + (od.z - d.z) ^ 2)
        -- 見かけの大きさは実距離で決まる(条1の錯覚)。ただし遠い物が点になると
        -- 「選べない」だけになるので sqrt で潰し、下限を切ってある
        local s = math.max(0.42, math.min(1.10, 4.5 / math.sqrt(dist)))
        place("Proxy_" .. i,
              d.x + d.outX * 2.25 + prX * (t * span), 1.42,
              d.z + d.outZ * 2.25 + prZ * (t * span), d.yaw, 0.85 * s, 1.75 * s, 0.07)
        tint("Proxy_" .. i, vivid(DOOR_COLOR[o] or { 1, 1, 1 }), 0.62)
    end
    for i = #cand + 1, 8 do hide("Proxy_" .. i) end
end

local function closeConnect(self)
    local id = self.connectDoor
    if id then
        local d = self.doors[id]
        local zAxis = math.abs(d.inZ) > 0.5
        place("Void_" .. id, d.x, 1.3, d.z, nil,
              zAxis and 1.5 or 0.10, 2.6, zAxis and 0.10 or 1.5)
        local vl = ent("VoidLight_" .. id)
        if vl then
            vl.transform.position = Vec3.new(d.x + d.inX * 0.55, 1.35, d.z + d.inZ * 0.55)
            local L = vl:light()
            if L then L.intensity = 5.2; L.range = 3.2 end
        end
    end
    for i = 1, 8 do hide("Proxy_" .. i) end
    self.mode = "play"
    self.connectDoor = nil
    self.cand = nil
    self.aim = nil
end

-- ---------------------------------------------------------------- 通過

-- 入射角 theta から何番目の出口に出るか。表示と判定でズレないよう 1 箇所に集約する
local function sliceIndex(theta, nex)
    if nex <= 1 then return 1 end
    local w = (FAN_DEG * 2) / nex
    local t = math.max(-FAN_DEG + 0.001, math.min(FAN_DEG - 0.001, theta))
    local k = math.floor((FAN_DEG - t) / w) + 1
    if k < 1 then return 1 elseif k > nex then return nex end
    return k
end

local function traverse(self, id, theta)
    local exits = exitsOf(self, id)
    local out = exits[sliceIndex(theta, #exits)]
    local od = self.doors[out]

    -- 入射角を鏡映して射出。勢いと向きが素直に繋がる
    local dx, dz = rot2(od.inX, od.inZ, theta)
    local pl = ent("MainCamera")
    if pl then
        physics:setPosition(pl, Vec3.new(od.x + od.inX * 1.55, 1.7, od.z + od.inZ * 1.55))
        self.tpSeq = (self.tpSeq or 0) + 1
        saveNum("tpYaw", math.deg(atan2(dx, dz)))
        saveNum("tpPitch", 0)
        saveNum("tpSeq", self.tpSeq)
    end
    camSet(self, od.x + od.inX * 1.55, 1.7, od.z + od.inZ * 1.55,
           math.deg(atan2(dx, dz)), 0)
    self.room = self.cfg.room[out]
    self.cool = 0.45
    self.fade = FADE_TIME
    -- 出た先のドア色を一瞬焚く(どのドアから出たかを色で名乗らせる)
    local c = DOOR_COLOR[out] or { 1, 1, 1 }
    fx:burst{ x = od.x + od.inX * 0.5, y = 1.5, z = od.z + od.inZ * 0.5, kind = "glow",
              count = 10, size = 0.3, r = c[1], g = c[2], b = c[3] }
end

-- ---------------------------------------------------------------- 案内の光
-- 文字を出さない代わりに「次に触る物」の上をふわふわ漂う。teach 指定の面だけ。

local function pilot(self, t)
    if not self.cfg.teach or self.mode ~= "play" then
        hide("Pilot"); hide("PilotLight"); return
    end
    local tx, ty, tz
    if self.room == self.cfg.goalRoom and self.goal then
        local g = self.goal.transform.position
        tx, ty, tz = g.x, 2.6, g.z
    else
        -- この部屋にある、まだ繋がっていないドア
        for _, id in ipairs(self.cfg.doors) do
            if self.cfg.room[id] == self.room and not self.group[id] then
                local d = self.doors[id]
                tx, ty, tz = d.x + d.inX * 0.9, 2.15, d.z + d.inZ * 0.9
                break
            end
        end
    end
    if not tx then hide("Pilot"); hide("PilotLight"); return end
    local y = ty + math.sin(t * 2.1) * 0.16
    place("Pilot", tx, y, tz)
    place("PilotLight", tx, y, tz)
end

-- ---------------------------------------------------------------- HUD
-- ★出す文字は操作キーだけ。ルールの説明文は 1 行も出さない。

local function keyCap(x, y, s, size, hot)
    -- キーの見た目(角丸の箱 + 文字)。size は文字の高さ
    local w = #s * size * 0.62 + size * 0.7
    local h = size * 1.45
    ui:rect(x, y, w, h, 0.03, 0.06, 0.04, hot and 0.85 or 0.55, 5)
    ui:rect(x + 1, y + 1, w - 2, h - 2, 0.55, 0.62, 0.56, hot and 0.5 or 0.22, 5)
    local c = hot and C_KEY or C_DIM
    ui:text(x + size * 0.35, y + size * 0.22, s, size, c[1], c[2], c[3], 1)
    return w
end

local function worldKey(self, wx, wy, wz, s)
    -- ワールド座標の上にキーを出す。camera.project は画面外だと visible=false
    -- ★ camera:project は「:」で呼ぶ(Camera の userdata メソッド)。「.」だと
    --   第1引数が数値になって "expected userdata" で OnUpdate ごと落ちる
    local u, v, vis = camera:project(wx, wy, wz)
    if not vis then return end
    keyCap(u - 16, v - 18, s, 24, true)
end

-- ---------------------------------------------------------------- 毎フレーム

function OnUpdate(self, dt)
    if not self.cfg then return end
    local W, H = SCREEN_W or 1920, SCREEN_H or 1080
    local t = time.now()

    if self.pendingIntro then
        self.pendingIntro = false
        introCine(self)
        return
    end

    if keyPressed("R") then resetRun(self); return end
    for i = 1, 8 do
        if keyPressed(tostring(i)) then
            local s = STAGES["Logic_Stage_" .. i]
            if s and s.scene and self.cfg.n ~= i then loadScene(s.scene); return end
        end
    end

    -- ============================ カメラ演出中 ============================
    if self.cine then
        camApply(self)
        if self.flash > 0 then self.flash = math.max(0, self.flash - dt * 3.2) end
        ui:rect(0, 0, W, H, 1, 1, 1, self.flash)
        -- 上下の黒帯(ここは演出です、という合図。文字は出さない)
        ui:rect(0, 0, W, H * 0.085, 0, 0, 0, 1)
        ui:rect(0, H - H * 0.085, W, H * 0.085, 0, 0, 0, 1)
        return
    end

    local pl = ent("MainCamera")
    if not pl then return end
    local p = pl.transform.position
    self.cam.x, self.cam.z = p.x, p.z
    self.cam.yaw = loadNum("camYaw", self.cam.yaw)

    if self.fade > 0 then self.fade = self.fade - dt end
    if self.cool > 0 then self.cool = self.cool - dt end
    if self.hint > 0 then self.hint = self.hint - dt end
    if self.showKeys > 0 then self.showKeys = self.showKeys - dt end

    if loadNum("moving", 0) > 0.5 then
        self.moveX, self.moveZ = loadNum("moveX", 0), loadNum("moveZ", 1)
    end

    -- ================================ クリア / 失敗 ================================
    -- ★文字は出さない。クリアは白へ抜けて次の面、失敗は白へ還ってやり直し(GDD 条5)。
    if self.mode == "clear" or self.mode == "fail" then
        self.flash = math.min(1, (self.flash or 0) + dt * 1.9)
        ui:rect(0, 0, W, H, 1, 1, 1, self.flash)
        if self.flash >= 1 then
            if self.mode == "clear" then
                -- 最終面をクリアしたら第1面へ戻す(同じ面をもう一度始めると
                -- 「クリアできていない」ように見える)
                loadScene(self.cfg.next or "scenes/stage1.json")
            else
                resetRun(self)
            end
        end
        return
    end

    if self.cfg.timed then
        self.timeLeft = self.timeLeft - dt
        -- ★残り 30 秒で照明が落ちる(GDD 04)。時計を読ませずに焦らせる
        if self.timeLeft < 30 then
            local k = 0.35 + 0.65 * (self.timeLeft / 30)
            scene:setAmbient(0.035 * k)
        end
        if self.timeLeft <= 0 then
            self.mode = "fail"; self.flash = 0
            log("JUNCTION FAIL: timeout")
            return
        end
    end

    -- ================================ 出口 ================================
    if self.goal and self.goal:isValid() then
        local g = self.goal.transform.position
        if (p.x - g.x) ^ 2 + (p.z - g.z) ^ 2 < 2.0 ^ 2 then
            self.mode = "clear"; self.flash = 0
            fx:burst{ x = g.x, y = 1.6, z = g.z, kind = "star", count = 60, size = 0.6,
                      r = 0.4, g = 1.0, b = 0.7 }
            log("JUNCTION CLEAR: stage " .. self.cfg.n)
            return
        end
    end

    pilot(self, t)

    -- ================================ 一番近いドア ================================
    local near, nearD, nearS, nearLat = nil, 1e9, 0, 0
    for _, id in ipairs(self.cfg.doors) do
        local d = self.doors[id]
        local vx, vz = p.x - d.x, p.z - d.z
        local s = vx * d.outX + vz * d.outZ            -- 外向きの符号付き距離(部屋の中は負)
        local lat = vx * d.rgX + vz * d.rgZ
        local dist = math.sqrt(vx * vx + vz * vz)
        if dist < nearD then near, nearD, nearS, nearLat = id, dist, s, lat end
    end

    local hotExit = nil

    -- ================================ 接続モード ================================
    if self.mode == "connect" then
        if self.holdE > 0 then self.holdE = self.holdE - dt end

        -- 照準はカメラの向き。虚無の中では歩いても近づけないので視線で選ぶ
        local cy, cp = math.rad(loadNum("camYaw", 0)), math.rad(loadNum("camPitch", 0))
        local fx_, fy_, fz_ = math.sin(cy) * math.cos(cp), math.sin(cp), math.cos(cy) * math.cos(cp)

        local best, bestDot = nil, 0.927   -- 約 22°。狭いと「狙えない」だけの失敗が増える
        for i = 1, #self.cand do
            local e = ent("Proxy_" .. i)
            if e then
                local q = e.transform.position
                local vx, vy, vz = q.x - p.x, q.y - p.y, q.z - p.z
                local L = math.sqrt(vx * vx + vy * vy + vz * vz)
                if L > 0.01 then
                    local dp = (vx * fx_ + vy * fy_ + vz * fz_) / L
                    if dp > bestDot then best, bestDot = i, dp end
                end
            end
        end
        -- ★狙っている候補は【色の明るさだけ】では見分けが付かない(白い虚無の中では
        --   どれも同じくらい明るく見える)。少し大きくして輪郭を変える
        if best ~= self.aim then
            for i = 1, #self.cand do
                local e = ent("Proxy_" .. i)
                if e then
                    local sc = e.transform.scale
                    local k = (i == best) and 1.18 or 1.0
                    local bs = (i == self.aim) and (1 / 1.18) or 1.0
                    e.transform.scale = Vec3.new(sc.x * bs * k, sc.y * bs * k, sc.z)
                end
            end
        end
        for i = 1, #self.cand do
            tint("Proxy_" .. i, vivid(DOOR_COLOR[self.cand[i]] or { 1, 1, 1 }),
                 (i == best) and 1.15 or 0.55)
        end
        self.aim = best

        if keyPressed("Q") then closeConnect(self) end
        if self.holdE <= 0 and keyPressed("E") then
            if best then
                local to, from = self.cand[best], self.connectDoor
                closeConnect(self)
                connect(self, from, to)
            else
                self.hint = 0.6
            end
        end
        if nearD > REACH + 2.0 or near ~= self.connectDoor then closeConnect(self) end

    -- ================================ 通常 ================================
    else
        if near and nearD < REACH and keyPressed("E") then openConnect(self, near) end

        -- ---- 助走中のスライス。判定と表示は sliceIndex に一本化してある ----
        if near and nearD < 7.0 then
            local exits = exitsOf(self, near)
            if #exits >= 2 then
                local d = self.doors[near]
                local th = signedAngle(d.outX, d.outZ, self.moveX, self.moveZ)
                hotExit = sliceIndex(th, #exits)
                for i = 1, 6 do
                    tint("Slice_" .. near .. "_" .. i,
                         (i == hotExit or i == hotExit + 1) and C_BOUND_HOT or C_BOUND)
                end
                for i = 1, #exits do
                    tint("Lane_" .. near .. "_" .. i, DOOR_COLOR[exits[i]] or { 1, 1, 1 },
                         (i == hotExit) and 1.4 or 0.5)
                end
            end
        end

        -- ---- 通過判定 ----
        -- ★「いま歩いている」ことを必須にする。直前の向きだけで見ると、ドアに
        --   張り付いたまま接続した瞬間に(まだ歩いていないのに)吸い込まれる
        if self.cool <= 0 and near then
            local d = self.doors[near]
            local list = groupOf(self, near)
            if list and #list >= 2
               and loadNum("moving", 0) > 0.5
               and nearS > -ENTER_DIST and nearS < 0.4
               and math.abs(nearLat) < ENTER_LAT
               and (self.moveX * d.outX + self.moveZ * d.outZ) > ENTER_DOT then
                traverse(self, near, signedAngle(d.outX, d.outZ, self.moveX, self.moveZ))
            end
        end

        -- ---- 孤立の即時判定(詰みに気づかせず歩かせない) ----
        if self.budget <= 0 and not reachable(self) then
            self.mode = "fail"; self.flash = 0
            log("JUNCTION FAIL: isolated")
            return
        end
    end

    -- ================================ HUD ================================
    -- 照準点。白い虚無の上でも見えるように、暗い縁を敷いてから白い点を打つ
    ui:rect(W * 0.5 - 4, H * 0.5 - 4, 8, 8, 0, 0, 0, 0.5, 4)
    ui:rect(W * 0.5 - 2, H * 0.5 - 2, 4, 4, 1, 1, 1, 0.95, 2)

    -- ---- 残り時間。数字ではなく細い帯(読ませない。減っていくのを感じさせる) ----
    if self.cfg.timed then
        local k = math.max(0, self.timeLeft / TIME_LIMIT)
        local bw = W * 0.34
        ui:rect(W * 0.5 - bw * 0.5, 16, bw, 5, 0.05, 0.07, 0.05, 0.55, 2)
        local urg = self.timeLeft < 30
        ui:rect(W * 0.5 - bw * 0.5, 16, bw * k, 5,
                urg and 1.0 or 0.82, urg and 0.35 or 0.88, urg and 0.28 or 0.80,
                0.95, 2)
    end

    -- ---- 接続の残り(点灯した錠剤。文字なし) ----
    do
        local n = self.cfg.budget
        local cw, gap = 22, 8
        local x0 = W - 26 - (n * cw + (n - 1) * gap)
        for i = 1, n do
            local on = i <= self.budget
            local a = self.hint > 0 and (0.4 + 0.6 * math.abs(math.sin(t * 22))) or 1
            ui:rect(x0 + (i - 1) * (cw + gap), 22, cw, 11,
                    on and 0.25 or 0.30, on and 0.92 or 0.32, on and 0.62 or 0.30,
                    (on and 0.95 or 0.35) * a, 3)
        end
    end

    -- ---- 世界の上に出るキー(操作方法のみ) ----
    if self.mode == "connect" then
        if self.aim then
            local e = ent("Proxy_" .. self.aim)
            if e then
                local q = e.transform.position
                worldKey(self, q.x, q.y + 1.15, q.z, "E")
            end
        end
        keyCap(W * 0.5 - 90, H - 78, "Q", 22, false)
    elseif near and nearD < REACH then
        local d = self.doors[near]
        local exits = exitsOf(self, near)
        if #exits == 0 or (self.budget > 0 and #exits < MAX_JUNCTION - 1) then
            worldKey(self, d.x + d.inX * 0.25, 3.05, d.z + d.inZ * 0.25, "E")
        end
    end

    -- ---- 開幕だけ操作キーを並べる。ルール説明は一切しない ----
    if self.showKeys > 0 or keyDown("H") then
        local a = math.min(1, self.showKeys > 0 and self.showKeys or 1)
        local x, y = 30, H - 62
        if a > 0.05 then
            x = x + keyCap(x, y, "W A S D", 20, false) + 14
            x = x + keyCap(x, y, "E", 20, false) + 14
            x = x + keyCap(x, y, "Q", 20, false) + 14
            keyCap(x, y, "R", 20, false)
        end
    end

    -- ---- 通過フェード(白) ----
    if self.fade > 0 then
        ui:rect(0, 0, W, H, 1, 1, 1, self.fade / FADE_TIME)
    end
end
