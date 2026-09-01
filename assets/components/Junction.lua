-- ============================================================================
-- JUNCTION / 継ぎ目 — ゲームロジック本体。シーンに 1 つだけ置く空エンティティに付ける。
-- エンティティ名 "Logic_Stage_3" / "Logic_Stage_4" でステージ設定を引く。
--
-- ★このプロトタイプが検証したい 1 点だけを実装してある(GDD 09):
--     「同じドアに違う角度で入ると、違う場所に出る」は気持ちいいか。
--   条1(触れて・見て・選ぶ) / 条2(接続予算) / 条3(合流点) / 条4(入射角) / 条5(3分)。
--   白の侵食とスコアは入れていない。
--
-- ★ポータル描画はしない。ドアの向こうは常に白板(Void_<id>)で塞がっていて、
--   接近したフレームにテレポートする。GDD の実装方針(3D酔い対策=1〜2フレームのフェード)
--   をそのまま採ると、ステンシル再帰なしでも「繋がっている」感覚は出る、という賭け。
--   ここが鈍いなら描画を足しても救えない。
--
-- ★角度は【WASD の押し方向】で測る。カメラの向きでも実速度でもない:
--   ・カメラの向き … 歩きながら見回すだけで行き先が変わってしまう
--   ・実速度       … ドア際で壁ズリすると自分の意図と違う向きになる
--   FreeLook.lua が saveNum("moveX"/"moveZ") へ書く。書き手はあそこ 1 箇所。
--
-- ★エンティティ名の規約(source/gen_stages.py と対。片方だけ変えると無言で壊れる):
--     Door_<id>        … ドアの印。transform だけを読む。rotation.y の forward = 部屋の内側
--     Void_<id>        … 白い虚無の板。接続モード中は奥へ飛ばして「背景」にする
--     VoidLight_<id>   … 白板を白飛びさせる灯り
--     Mark_<id>_1..5   … 合流点の刻印 Ⅰ/Ⅱ/Ⅲ。既定は床下に隠してある
--     Slice_<id>_1..6  … 床の角度分割線。同上
--     Proxy_1..8       … 虚無に浮かぶドアの候補。全ドアで使い回す
-- ============================================================================

local STAGES = {
    ["Logic_Stage_3"] = {
        title  = "03 / 合流",
        doors  = { "a", "b", "g" },
        room   = { a = "S", b = "A", g = "G" },
        budget = 3,               -- 1 本余る。試行錯誤を許す教育面
        goalRoom = "G",
        start  = "S",
        spawn  = { 0.0, 1.7, -3.5, 0.0 },
        hint   = "3枚を1つの合流点にまとめ、入る角度で行き先を選ぶ",
    },
    ["Logic_Stage_4"] = {
        title  = "04 / 二つの出口",
        doors  = { "a", "b", "c", "d" },
        room   = { a = "S", b = "P", c = "Q", d = "G" },
        budget = 2,               -- ぴったり。c に触れた瞬間に詰む
        goalRoom = "G",
        start  = "S",
        spawn  = { 0.0, 1.7, -3.5, 0.0 },
        hint   = "予算は2本。ドアは4枚ある",
    },
}

local MAX_JUNCTION = 5      -- 合流点の上限。6 枚目で崩壊
local FAN_DEG      = 60.0   -- ドア正面 ±この角度を等分する
local TIME_LIMIT   = 180.0  -- 3 分
local REACH        = 3.2    -- ドアに触れられる距離
local ENTER_DIST   = 1.05   -- この距離まで詰めたら通過判定
local ENTER_LAT    = 0.85   -- 開口の横幅の許容
local ENTER_DOT    = 0.30   -- 入る意思(移動方向と外向き法線の内積)
local HIDE_Y       = -200.0
local FADE_TIME    = 0.20
local LINE_LEN     = 3.6

local COL_SLICE      = { 0.10, 0.55, 0.38 }
local COL_SLICE_HOT  = { 0.35, 1.00, 0.72 }
local COL_PROXY      = { 0.26, 0.28, 0.26 }
local COL_PROXY_AIM  = { 0.12, 0.85, 0.55 }

-- ---------------------------------------------------------------- 小道具

-- math.atan の 2 引数版は 5.3 以降。5.1 系(math.atan2)でも動くようにここで吸収する
local atan2 = math.atan2 or function(y, x) return math.atan(y, x) end

local function rot2(vx, vz, deg)
    -- (x,z) 平面の回転。正の deg = プレイヤーから見て【左】
    -- 検算: rot((0,1), -90) = (1,0) = yaw0 の右。これが崩れると左右が入れ替わる
    local c, s = math.cos(math.rad(deg)), math.sin(math.rad(deg))
    return vx * c - vz * s, vx * s + vz * c
end

local function signedAngle(ox, oz, dx, dz)
    -- o から d への符号付き角度(度)。正 = 左
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

local function interactPressed()
    return loadNum("playerInteractPressed", 0) > 0.5
end

local function cancelPressed()
    return loadNum("playerCancelPressed", 0) > 0.5
end

local function drawReticle(W, H, active)
    local cx, cy = W * 0.5, H * 0.5
    local size = active and 7 or 5
    local r, g, b = active and 0.12 or 0.95, active and 1.0 or 0.95, active and 0.58 or 0.95
    ui:rect(cx - size * 0.5 - 2, cy - size * 0.5 - 2, size + 4, size + 4, 0, 0, 0, 0.58)
    ui:rect(cx - size * 0.5,     cy - size * 0.5,     size,     size,     r, g, b, active and 0.96 or 0.78)
end

local function tint(name, c)
    local e = ent(name)
    if e then scene:setColor(e, c[1], c[2], c[3]) end
end

-- ---------------------------------------------------------------- 状態

-- ★前方宣言。resetRun は refreshDoors より先に書いてあるので、これが無いと
--   local の上位値ではなくグローバル(=nil)を引いて OnStart で必ず落ちる。
local refreshDoors

local function resetRun(self, why)
    self.group = {}          -- doorId -> gid
    self.groups = {}         -- gid -> { doorId, ... }  (順番 = 刻印 Ⅰ Ⅱ Ⅲ の順)
    self.nextGid = 1
    self.budget = self.cfg.budget
    self.timeLeft = TIME_LIMIT
    self.room = self.cfg.start
    self.mode = "play"
    self.connectDoor = nil
    self.msg, self.msgT = why or "", why and 2.6 or 0
    self.fade = 0
    self.cool = 0.35
    self.moveX, self.moveZ = 0, 1
    self.touched = false

    local p = self.cfg.spawn
    local pl = ent("MainCamera")
    if pl then
        physics:setPosition(pl, Vec3.new(p[1], p[2], p[3]))
        self.tpSeq = (self.tpSeq or 0) + 1
        saveNum("tpYaw", p[4])
        saveNum("tpPitch", 0)
        saveNum("tpSeq", self.tpSeq)
    end
    refreshDoors(self)
end

function OnStart(self)
    self.cfg = STAGES[self.name]
    if not self.cfg then
        logError("Junction: 未知のステージ名 " .. tostring(self.name))
        return
    end
    -- ドアの静的情報を 1 回だけ引く。名前引きは毎フレームやるには重い
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
                inX = ix,  inZ = iz,      -- 部屋の内側
                outX = -ix, outZ = -iz,   -- 抜ける向き
                rgX = math.cos(math.rad(yaw)), rgZ = -math.sin(math.rad(yaw)),  -- 右
            }
        end
    end
    self.goal = ent("Goal")
    resetRun(self)
    log("JUNCTION " .. self.cfg.title .. " / doors=" .. #self.cfg.doors ..
        " budget=" .. self.cfg.budget)
end

-- 合流点の見た目(刻印と床の分割線)を全ドアぶん引き直す。
-- 接続/崩壊/リセットの直後にだけ呼ぶ。毎フレームは回さない。
function refreshDoors(self)
    for _, id in ipairs(self.cfg.doors) do
        local d = self.doors[id]
        local gid = self.group[id]
        local list = gid and self.groups[gid] or nil
        local n = list and #list or 0

        -- ---- 刻印 Ⅰ Ⅱ Ⅲ …(合流点に属する順番) ----
        for k = 1, 5 do hide("Mark_" .. id .. "_" .. k) end
        if n >= 2 then
            local idx = 1
            for i, m in ipairs(list) do if m == id then idx = i end end
            for k = 1, idx do
                local off = (k - (idx + 1) * 0.5) * 0.17
                place("Mark_" .. id .. "_" .. k,
                      d.x + d.rgX * off + d.inX * 0.26, 2.84, d.z + d.rgZ * off + d.inZ * 0.26,
                      d.yaw, 0.09, 0.24, 0.05)
            end
        end

        -- ---- 床の角度分割線(出口が 2 つ以上ある時だけ) ----
        for k = 1, 6 do hide("Slice_" .. id .. "_" .. k) end
        if n >= 3 then
            local bounds = n - 1 + 1            -- 出口 n-1 個 → 境界 n 本
            local step = (FAN_DEG * 2) / (n - 2 + 1)
            for k = 1, bounds do
                local ang = FAN_DEG - step * (k - 1)
                local dx, dz = rot2(d.outX, d.outZ, ang)
                -- ドアから【部屋の内側へ】伸ばす(助走の経路そのもの)
                local cx = d.x - dx * LINE_LEN * 0.5
                local cz = d.z - dz * LINE_LEN * 0.5
                place("Slice_" .. id .. "_" .. k, cx, 0.012, cz,
                      math.deg(atan2(dx, dz)), 0.055, 0.02, LINE_LEN)
                tint("Slice_" .. id .. "_" .. k, COL_SLICE)
            end
        end
    end
end

-- ---------------------------------------------------------------- 接続

local function groupOf(self, id)
    local gid = self.group[id]
    return gid and self.groups[gid] or nil
end

local function connect(self, from, to)
    if self.budget <= 0 then
        self.msg, self.msgT = "接続予算が無い", 2.2
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

    -- ---- 条3: 上限 5 枚。6 枚目で合流点そのものが崩壊し、予算は戻らない ----
    if #list + 1 > MAX_JUNCTION then
        for _, m in ipairs(list) do self.group[m] = nil end
        self.groups[gid] = nil
        self.msg, self.msgT = "合流点が崩壊した（接続を全て失った）", 3.4
        fx:pulse(1.0)
        refreshDoors(self)
        return
    end

    table.insert(list, to)
    self.group[to] = gid
    self.touched = true
    self.cool = 0.5   -- 繋いだ直後の 1 歩で通過しない猶予
    self.msg = string.format("%s - %s を接続（%d枚の合流点）", from, to, #list)
    self.msgT = 2.4
    fx:burst{ x = self.doors[to].x, y = 1.4, z = self.doors[to].z,
              kind = "glow", count = 14, size = 0.35, r = 0.2, g = 0.95, b = 0.6 }
    refreshDoors(self)
end

-- 出口までの到達可能性(条: 孤立の即時判定)。部屋 -> 部屋を合流点で辿るだけ
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
    -- 候補 = まだ どの合流点にも属していない全てのドア
    local cand = {}
    for _, o in ipairs(self.cfg.doors) do
        if o ~= id and not self.group[o] then table.insert(cand, o) end
    end
    if #cand == 0 then
        self.msg, self.msgT = "繋げるドアがもう無い", 2.2
        return
    end
    local d = self.doors[id]
    -- 見かけの大きさは【実距離】で決まる。虚無には遠近の手がかりが他に無い(条1の錯覚)
    table.sort(cand, function(p, q)
        return signedAngle(d.outX, d.outZ, self.doors[p].x - d.x, self.doors[p].z - d.z)
             > signedAngle(d.outX, d.outZ, self.doors[q].x - d.x, self.doors[q].z - d.z)
    end)

    self.mode = "connect"
    self.connectDoor = id
    self.cand = cand
    self.aim = nil
    self.holdE = 0.28   -- 開いた同じ E で確定しないための不感時間

    -- 白板を奥へ飛ばして「虚無の背景」にする + 灯りを強くして白飛びさせる。
    -- ★でかくする。11x8 だと開口の縁からドアの外(=部屋の外は素の黒)が覗いて
    --   「白い虚無」が黒い額縁に見える。近い面が ±70° を覆う大きさが要る。
    place("Void_" .. id, d.x + d.outX * 13.0, 3.0, d.z + d.outZ * 13.0, nil, 64.0, 48.0, 8.0)
    local vl = ent("VoidLight_" .. id)
    if vl then
        vl.transform.position = Vec3.new(d.x + d.outX * 4.2, 1.9, d.z + d.outZ * 4.2)
        local L = vl:light()
        if L then L.intensity = 90.0; L.range = 22.0 end
    end

    -- ★横並びは【プレイヤーから見た左右】で置く。ドアの right(d.rgX/rgZ) は
    --   ドア自身の forward(=部屋の内側)基準なので、ドアに向き合うプレイヤーからは
    --   左右が反転している。ここを間違えると「左の候補が右に出る」。
    local prX, prZ = -d.rgX, -d.rgZ
    local span = 1.5
    for i, o in ipairs(cand) do
        local t = (#cand == 1) and 0 or ((i - 1) / (#cand - 1) * 2 - 1)
        local od = self.doors[o]
        local dist = math.sqrt((od.x - d.x) ^ 2 + (od.z - d.z) ^ 2)
        -- 見かけの大きさは実距離で決まる(条1の錯覚)。ただし遠い物が点になると
        -- 「選べない」だけになるので sqrt で潰し、下限を切ってある
        local s = math.max(0.42, math.min(1.10, 4.5 / math.sqrt(dist)))
        local px = d.x + d.outX * 2.25 + prX * (t * span)
        local pz = d.z + d.outZ * 2.25 + prZ * (t * span)
        place("Proxy_" .. i, px, 1.42, pz, d.yaw, 0.85 * s, 1.75 * s, 0.07)
        tint("Proxy_" .. i, COL_PROXY)
    end
    for i = #cand + 1, 8 do hide("Proxy_" .. i) end
end

local function closeConnect(self)
    local id = self.connectDoor
    if id then
        local d = self.doors[id]
        place("Void_" .. id, d.x, 1.3, d.z, nil,
              math.abs(d.inZ) > 0.5 and 1.5 or 0.10, 2.6,
              math.abs(d.inZ) > 0.5 and 0.10 or 1.5)
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

local function traverse(self, id, theta)
    local list = groupOf(self, id)
    local exits = {}
    for _, m in ipairs(list) do if m ~= id then table.insert(exits, m) end end
    local n = #exits

    local k = 1
    if n > 1 then
        -- 条4: 正面 ±60° を n 等分。左端が Ⅰ 側
        local w = (FAN_DEG * 2) / n
        local t = math.max(-FAN_DEG + 0.001, math.min(FAN_DEG - 0.001, theta))
        k = math.floor((FAN_DEG - t) / w) + 1
        if k < 1 then k = 1 elseif k > n then k = n end
    end
    local out = exits[k]
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
    self.room = self.cfg.room[out]
    self.cool = 0.45
    self.fade = FADE_TIME
    self.lastAngle = theta
    self.msg = string.format("%s → %s   入射 %+.0f°", id, out, theta)
    self.msgT = 2.0
end

-- ---------------------------------------------------------------- 毎フレーム

function OnUpdate(self, dt)
    if not self.cfg then return end
    local W, H = SCREEN_W or 1920, SCREEN_H or 1080

    -- ---- デバッグ/進行キー ----
    if keyPressed("R") then resetRun(self, "やり直し") end
    if keyPressed("3") and self.name ~= "Logic_Stage_3" then loadScene("scenes/stage3.json"); return end
    if keyPressed("4") and self.name ~= "Logic_Stage_4" then loadScene("scenes/stage4.json"); return end

    local pl = ent("MainCamera")
    if not pl then return end
    local p = pl.transform.position

    if self.msgT > 0 then self.msgT = self.msgT - dt end
    if self.fade > 0 then self.fade = self.fade - dt end
    if self.cool > 0 then self.cool = self.cool - dt end

    -- ---- 移動方向(角度の一次情報源)。押していないフレームは直前を保つ ----
    if loadNum("moving", 0) > 0.5 then
        self.moveX, self.moveZ = loadNum("moveX", 0), loadNum("moveZ", 1)
    end

    -- ================================ クリア / 失敗 ================================
    if self.mode == "clear" or self.mode == "fail" then
        local a = (self.mode == "clear") and 0.55 or 0.72
        local c = (self.mode == "clear") and { 0.05, 0.28, 0.19 } or { 0.30, 0.06, 0.03 }
        ui:rect(0, 0, W, H, c[1], c[2], c[3], a)
        local t = (self.mode == "clear") and "CLEAR" or "FAILED"
        ui:text(W * 0.5 - 90, H * 0.42, t, 54, 1, 1, 1, 1)
        ui:text(W * 0.5 - 150, H * 0.52, self.msg or "", 22, 0.85, 0.90, 0.86, 1)
        ui:text(W * 0.5 - 110, H * 0.60, "[R] やり直す   [3][4] 面を変える", 20, 0.8, 0.85, 0.8, 1)
        return
    end

    self.timeLeft = self.timeLeft - dt
    if self.timeLeft <= 0 then
        self.mode = "fail"
        self.msg = "時間切れ。建物が白に還った"
        log("JUNCTION FAIL: " .. self.msg)
        return
    end

    -- ================================ 出口 ================================
    if self.goal and self.goal:isValid() then
        local g = self.goal.transform.position
        if (p.x - g.x) ^ 2 + (p.z - g.z) ^ 2 < 2.0 ^ 2 then
            self.mode = "clear"
            self.msg = string.format("残り %.1f 秒 / 未使用の接続 %d 本", self.timeLeft, self.budget)
            log("JUNCTION CLEAR: " .. self.msg)
            return
        end
    end

    -- ================================ 一番近いドア ================================
    local near, nearD, nearS, nearLat = nil, 1e9, 0, 0
    for _, id in ipairs(self.cfg.doors) do
        local d = self.doors[id]
        local vx, vz = p.x - d.x, p.z - d.z
        local s = vx * d.outX + vz * d.outZ            -- 外向きの符号付き距離(部屋の中は負)
        local lat = vx * d.rgX + vz * d.rgZ            -- 開口の横ずれ
        local dist = math.sqrt(vx * vx + vz * vz)
        if dist < nearD then near, nearD, nearS, nearLat = id, dist, s, lat end
    end

    -- ================================ 接続モード ================================
    if self.mode == "connect" then
        if self.holdE > 0 then self.holdE = self.holdE - dt end
        local d = self.doors[self.connectDoor]

        -- 照準は【カメラの向き】。虚無の中では歩いても近づけないので視線で選ぶ
        local yaw, pitch = loadNum("camYaw", 0), loadNum("camPitch", 0)
        local cy, cp = math.rad(yaw), math.rad(pitch)
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
        for i = 1, #self.cand do
            tint("Proxy_" .. i, (i == best) and COL_PROXY_AIM or COL_PROXY)
        end
        self.aim = best

        if cancelPressed() then closeConnect(self) end
        if self.holdE <= 0 and interactPressed() then
            if best then
                local to = self.cand[best]
                local from = self.connectDoor
                closeConnect(self)
                connect(self, from, to)
            else
                self.msg, self.msgT = "どのドアも狙えていない", 1.6
            end
        end
        -- ドアから離れたら閉じる
        if nearD > REACH + 2.0 or near ~= self.connectDoor then closeConnect(self) end

    -- ================================ 通常 ================================
    else
        if near and nearD < REACH and interactPressed() then
            openConnect(self, near)
        end

        -- ---- 通過判定 ----
        if self.cool <= 0 and near then
            local d = self.doors[near]
            local list = groupOf(self, near)
            -- ★「いま歩いている」ことを必須にする。直前の向きだけで判定すると、
            --   ドアに張り付いたまま接続した瞬間に(まだ W を押していないのに)
            --   吸い込まれる。通過はプレイヤーが自分の足で入る行為でなければならない。
            if list and #list >= 2
               and loadNum("moving", 0) > 0.5
               and nearS > -ENTER_DIST and nearS < 0.4
               and math.abs(nearLat) < ENTER_LAT
               and (self.moveX * d.outX + self.moveZ * d.outZ) > ENTER_DOT then
                traverse(self, near, signedAngle(d.outX, d.outZ, self.moveX, self.moveZ))
            end
        end

        -- ---- 助走中の分割線を光らせる(自分がどのスライスに乗っているか) ----
        if near and nearD < 6.0 then
            local list = groupOf(self, near)
            local n = list and #list or 0
            if n >= 3 then
                local d = self.doors[near]
                local th = signedAngle(d.outX, d.outZ, self.moveX, self.moveZ)
                local nex = n - 1
                local w = (FAN_DEG * 2) / nex
                local t = math.max(-FAN_DEG + 0.001, math.min(FAN_DEG - 0.001, th))
                local k = math.floor((FAN_DEG - t) / w) + 1
                for i = 1, 6 do
                    tint("Slice_" .. near .. "_" .. i,
                         (i == k or i == k + 1) and COL_SLICE_HOT or COL_SLICE)
                end
                self.hotExit = k
            else
                self.hotExit = nil
            end
        else
            self.hotExit = nil
        end

        -- ---- 孤立の即時判定(GDD の禁止事項: 詰みに気づかせず歩かせない) ----
        if self.budget <= 0 and not reachable(self) then
            self.mode = "fail"
            self.msg = "孤立。出口へ辿り着けなくなった"
            log("JUNCTION FAIL: " .. self.msg)
            return
        end
    end

    -- ================================ HUD ================================
    -- 中央レティクル(酔い止めの固定点 兼 照準)
    drawReticle(W, H, (self.mode == "connect" and self.aim ~= nil) or (near and nearD < REACH))

    -- 時間
    local m = math.floor(self.timeLeft / 60)
    local s = self.timeLeft - m * 60
    local urg = self.timeLeft < 30
    ui:text(W * 0.5 - 44, 26, string.format("%d:%05.2f", m, s), 30,
            urg and 1 or 0.92, urg and 0.35 or 0.94, urg and 0.28 or 0.90, 0.95)

    -- 接続予算
    ui:text(40, 30, "接続", 15, 0.65, 0.70, 0.66, 0.9)
    for i = 1, self.cfg.budget do
        local on = i <= self.budget
        ui:rect(40 + (i - 1) * 26, 52, 20, 8,
                on and 0.20 or 0.30, on and 0.85 or 0.32, on and 0.58 or 0.30, on and 0.95 or 0.5)
    end
    ui:text(40, 70, self.cfg.title, 15, 0.55, 0.60, 0.56, 0.8)

    -- ドアの案内
    if self.mode == "connect" then
        ui:rect(0, H - 128, W, 128, 0.02, 0.05, 0.03, 0.55)
        ui:text(40, H - 108, "虚無 — まだ繋がっていないドアが浮かんでいる", 20, 0.9, 0.95, 0.9, 1)
        local names = {}
        for i, o in ipairs(self.cand) do
            names[#names + 1] = (i == self.aim) and ("[" .. o .. "]") or (" " .. o .. " ")
        end
        ui:text(40, H - 78, "候補: " .. table.concat(names, "  "), 22, 0.75, 0.95, 0.85, 1)
        ui:text(40, H - 48, "[E]/[X] 繋ぐ    [Q]/[B] やめる    ※見かけの大きさは実距離できまる", 17,
                0.6, 0.66, 0.62, 0.95)
    elseif near and nearD < REACH then
        local list = groupOf(self, near)
        local n = list and #list or 0
        local y = H - 92
        ui:rect(0, y - 16, W, 108, 0.02, 0.05, 0.03, 0.45)
        if n >= 2 then
            local exits = {}
            for _, o in ipairs(list) do if o ~= near then exits[#exits + 1] = o end end
            local line = "ドア " .. near .. " — " .. n .. "枚の合流点 / 出口 " .. #exits .. " つ"
            ui:text(40, y, line, 20, 0.85, 0.95, 0.9, 1)
            if self.hotExit and exits[self.hotExit] then
                local d = self.doors[near]
                local th = signedAngle(d.outX, d.outZ, self.moveX, self.moveZ)
                ui:text(40, y + 28, string.format("いま歩いている向き %+.0f°  →  出口 %s",
                        th, exits[self.hotExit]), 22, 0.4, 1.0, 0.72, 1)
            elseif #exits == 1 then
                ui:text(40, y + 28, "出口は 1 つ。角度は関係ない  →  " .. exits[1], 20,
                        0.7, 0.9, 0.8, 1)
            end
            ui:text(40, y + 58, "[E] さらに繋ぐ", 17, 0.6, 0.66, 0.62, 0.95)
        else
            ui:text(40, y, "ドア " .. near .. " — 未接続。向こうは白い虚無", 20, 0.85, 0.9, 0.86, 1)
            ui:text(40, y + 30, "[E] 触れて繋ぐ", 19, 0.6, 0.9, 0.75, 1)
        end
    end

    -- 開幕の操作説明。ドアに触れるまで消えない(ここが分からないと何も起きないゲーム)
    if not self.touched then
        ui:rect(W * 0.5 - 330, H - 190, 660, 46, 0.02, 0.05, 0.03, 0.5)
        ui:text(W * 0.5 - 312, H - 178,
                "WASD/LS 移動 / SPACE/A ジャンプ / SHIFT/RB ダッシュ / E/X 調べる / " .. self.cfg.hint, 19, 0.85, 0.95, 0.9, 1)
    end

    -- メッセージ
    if self.msgT > 0 and self.msg and self.msg ~= "" then
        local a = math.min(1, self.msgT / 0.5)
        ui:text(W * 0.5 - 200, H * 0.32, self.msg, 24, 1, 1, 1, a)
    end

    -- 通過フェード(白)。1〜2 フレームでは足りないが、0.2 秒でも酔いはほぼ消える
    if self.fade > 0 then
        ui:rect(0, 0, W, H, 1, 1, 1, self.fade / FADE_TIME)
    end
end
