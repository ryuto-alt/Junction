-- ============================================================================
-- JUNCTION / 継ぎ目 — ゲームロジック本体。シーンに 1 つだけ置く空エンティティに付ける。
-- エンティティ名 "Logic_Stage_3" / "Logic_Stage_4" でステージ設定を引く。
--
-- ★このプロトタイプが検証したい 1 点(GDD 09):
--     「同じドアに違う角度で入ると、違う場所に出る」は気持ちいいか。
--
-- ★ポータル描画はしない。ドアの向こうは常に白板(Void_<id>)で塞がっていて、
--   接近したフレームにテレポートする。ステンシル再帰なしでも「繋がっている」感覚が
--   出るか、という賭け。ここが鈍いなら描画を足しても救えない。
--
-- ★角度は【WASD の押し方向】で測る。カメラの向きでも実速度でもない:
--   ・カメラの向き … 歩きながら見回すだけで行き先が変わってしまう
--   ・実速度       … ドア際で壁ズリすると自分の意図と違う向きになる
--   FreeLook.lua が saveNum("moveX"/"moveZ") へ書く。書き手はあそこ 1 箇所。
--
-- ★2026-09-01 「ルールが分かりづらい / 文字がはみ出る」への対処:
--   (1) 色を通し言語にした。ドアごとの固有色で 枠・虚無の候補・床の助走レーン・
--       レーンの先の柱 を塗る。「青い柱から歩けば青いドアに出る」が見れば分かる状態にする。
--       Ⅰ/Ⅱ/Ⅲ の刻印だけでは、どの番号がどの部屋か覚えていられなかった。
--   (2) HUD の文字幅を textW() で見積もってパネルを自動で合わせる。
--       ImGui の即時描画には折り返しも実測幅も無いので、決め打ちの座標だと必ずはみ出る。
--   (3) 今やるべきことを 1 行で常に出す(objective)。[H] で全ルールを読める。
--
-- ★エンティティ名の規約(source/gen_stages.py と対。片方だけ変えると無言で壊れる):
--     Door_<id> / Void_<id> / VoidLight_<id> / Frame_<id>_*
--     Mark_<id>_1..5   合流点の刻印
--     Slice_<id>_1..6  角度の境界線
--     Lane_<id>_1..5   助走レーン(行き先の色)
--     Post_<id>_1..5   レーンの先に立つ柱(行き先の色)
--     Proxy_1..8       虚無に浮かぶ候補。全ドアで使い回す
-- ============================================================================

local STAGES = {
    ["Logic_Stage_3"] = {
        title  = "第3面 / 合流",
        doors  = { "a", "b", "g" },
        room   = { a = "S", b = "A", g = "G" },
        budget = 3,
        goalRoom = "G",
        start  = "S",
        spawn  = { 0.0, 1.7, -3.5, 0.0 },
    },
    ["Logic_Stage_4"] = {
        title  = "第4面 / 二つの出口",
        doors  = { "a", "b", "c", "d" },
        room   = { a = "S", b = "P", c = "Q", d = "G" },
        budget = 2,
        goalRoom = "G",
        start  = "S",
        spawn  = { 0.0, 1.7, -3.5, 0.0 },
    },
}

-- ★gen_stages.py の DOOR_COLORS と必ず一致させること
local DOOR_COLOR = {
    a = { 0.20, 0.85, 0.55 }, b = { 1.00, 0.55, 0.12 }, c = { 0.95, 0.25, 0.45 },
    d = { 0.30, 0.60, 1.00 }, g = { 1.00, 0.82, 0.15 },
}
local DOOR_CNAME = { a = "緑", b = "橙", c = "赤", d = "青", g = "黄" }

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
local C_INK       = { 0.90, 0.94, 0.90 }
local C_SUB       = { 0.60, 0.66, 0.61 }
local C_ACC       = { 0.40, 1.00, 0.72 }

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

-- ★文字幅の見積もり。ImGui の即時描画は折り返しも実測幅も無いので、
--   決め打ちの座標で中央寄せ/パネル幅を書くと必ずはみ出る(実際にはみ出した)。
--   フォントは 17px で読み込まれ AddText でスケールされる。ASCII の送りは約 0.5em、
--   日本語は 1em。UTF-8 の先頭バイトで判別して足すだけで十分な精度が出る。
local function textW(s, size)
    local n, i = 0, 1
    while i <= #s do
        local b = s:byte(i)
        if b < 0x80 then n = n + 0.50; i = i + 1
        elseif b < 0xC0 then i = i + 1                 -- 継続バイト(通常ここには来ない)
        elseif b < 0xE0 then n = n + 0.55; i = i + 2
        elseif b < 0xF0 then n = n + 1.00; i = i + 3
        else n = n + 1.00; i = i + 4 end
    end
    return n * size * 1.03    -- 3% の余裕
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

local function tint(name, c, k)
    local e = ent(name)
    if e then
        k = k or 1
        scene:setColor(e, c[1] * k, c[2] * k, c[3] * k)
    end
end

-- ---- HUD の下請け ----
local function panel(x, y, w, h, a)
    ui:rect(x, y, w, h, 0.02, 0.045, 0.03, a or 0.66, 5)
end

local function label(x, y, s, size, c, a)
    ui:text(x, y, s, size, c[1], c[2], c[3], a or 1)
end

local function labelC(cx, y, s, size, c, a)
    ui:text(cx - textW(s, size) * 0.5, y, s, size, c[1], c[2], c[3], a or 1)
end

-- ---------------------------------------------------------------- 状態

-- ★前方宣言。resetRun は refreshDoors より先に書いてあるので、これが無いと
--   local の上位値ではなくグローバル(=nil)を引いて OnStart で必ず落ちる。
local refreshDoors

local function resetRun(self, why)
    self.group = {}          -- doorId -> gid
    self.groups = {}         -- gid -> { doorId, ... }  (順番 = 合流点に入った順)
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
    self.help = false

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
    resetRun(self)
    log("JUNCTION " .. self.cfg.title .. " / doors=" .. #self.cfg.doors ..
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

local function connect(self, from, to)
    if self.budget <= 0 then
        self.msg, self.msgT = "接続できる回数が残っていない", 2.4
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
        self.msg, self.msgT = "合流点が崩壊した。この合流点の接続を全て失った", 3.6
        fx:pulse(1.0)
        refreshDoors(self)
        return
    end

    table.insert(list, to)
    self.group[to] = gid
    self.touched = true
    self.cool = 0.5   -- 繋いだ直後の 1 歩で通過しない猶予
    self.msg = string.format("%s と %s がつながった（%d枚の合流点）",
                             DOOR_CNAME[from] or from, DOOR_CNAME[to] or to, #list)
    self.msgT = 2.6
    local td = self.doors[to]
    local c = DOOR_COLOR[to] or { 1, 1, 1 }
    fx:burst{ x = td.x, y = 1.4, z = td.z, kind = "glow", count = 14, size = 0.35,
              r = c[1], g = c[2], b = c[3] }
    refreshDoors(self)
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
    if #cand == 0 then
        self.msg, self.msgT = "まだつながっていないドアが もう無い", 2.4
        return
    end
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
        tint("Proxy_" .. i, DOOR_COLOR[o] or { 1, 1, 1 }, 0.5)
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
    self.room = self.cfg.room[out]
    self.cool = 0.45
    self.fade = FADE_TIME
    self.msg = string.format("%+.0f度 で入った -> %s のドアから出た",
                             theta, DOOR_CNAME[out] or out)
    self.msgT = 2.4
end

-- ---------------------------------------------------------------- ヘルプ

local HELP = {
    { "1",  "ドアの向こうは白い虚無。まだ どこにもつながっていない。" },
    { "",   "ドアに近づいて [E]。虚無に「まだつながっていないドア」が浮かぶので、" },
    { "",   "狙って もう一度 [E]。そのドアとつながる。" },
    { "",   "浮かんだドアの大きさは 実際の距離で決まる。遠いものほど小さい。" },
    { "2",  "つなげる回数には上限がある（画面右上）。使い切って出口へ行けなくなると詰み。" },
    { "3",  "つないだドアに もう1枚 つなぐと「合流点」になる。" },
    { "",   "3枚の合流点なら、そのドアから出られる先は 2 つ。" },
    { "4",  "*どの出口に出るかは【ドアに入るときに歩いていた向き】で決まる。" },
    { "",   "合流点のドアの手前に、行き先の色の道と柱が現れる。" },
    { "",   "青い柱の側から助走してドアに入れば、青いドアから出る。" },
    { "5",  "制限時間は 3 分。緑に光る柱（出口）に触れればクリア。" },
}
local KEYS1 = "WASD 歩く / Shift 走る / E 触れる・つなぐ / Q やめる"
local KEYS2 = "R やり直し / 3・4 面を変える / H このヘルプ / ESC マウス解放"

local function drawHelp(self, W, H)
    ui:rect(0, 0, W, H, 0.012, 0.032, 0.022, 0.94)
    -- 一番長い行に合わせて左端を決める(はみ出させない)
    local wmax = textW(KEYS1, 19)
    for _, row in ipairs(HELP) do
        wmax = math.max(wmax, textW(row[2], 21) + 32)
    end
    local x = math.max(24, W * 0.5 - wmax * 0.5)
    local y = math.max(24, H * 0.5 - 265)
    label(x, y, "JUNCTION / 継ぎ目 / ルール", 34, C_INK)
    y = y + 54
    for _, row in ipairs(HELP) do
        if row[1] ~= "" then label(x, y, row[1], 21, C_ACC) end
        label(x + 32, y, row[2], 21, row[1] ~= "" and C_INK or C_SUB)
        y = y + 31
    end
    y = y + 20
    label(x, y, KEYS1, 19, C_SUB); y = y + 26
    label(x, y, KEYS2, 19, C_SUB)
    labelC(W * 0.5, H - 62, "[H] で閉じる", 22, C_ACC)
end

-- 今やるべきこと 1 行。ここが分からないと何も起きないゲームなので常に出す
local function objective(self)
    if self.room == self.cfg.goalRoom then return "緑に光る柱に触れる" end
    local best = 0
    for _, id in ipairs(self.cfg.doors) do
        local list = groupOf(self, id)
        if list and #list > best then best = #list end
    end
    if best == 0 then return "ドアに近づいて [E]。虚無のドアを狙って [E] でつなぐ" end
    if best == 2 then return "同じドアに もう1枚 つないで、合流点を3枚にする" end
    return "床の色の道から助走してドアに入る。その色のドアから出る"
end

-- ---------------------------------------------------------------- 毎フレーム

function OnUpdate(self, dt)
    if not self.cfg then return end
    local W, H = SCREEN_W or 1920, SCREEN_H or 1080

    if keyPressed("H") then self.help = not self.help end
    if keyPressed("R") then resetRun(self, "やり直した") end
    if keyPressed("3") and self.name ~= "Logic_Stage_3" then loadScene("scenes/stage3.json"); return end
    if keyPressed("4") and self.name ~= "Logic_Stage_4" then loadScene("scenes/stage4.json"); return end

    -- ★ヘルプ中は時間を進めない。ルールを読んでいる間に負けるのは理不尽
    if self.help then drawHelp(self, W, H); return end

    local pl = ent("MainCamera")
    if not pl then return end
    local p = pl.transform.position

    if self.msgT > 0 then self.msgT = self.msgT - dt end
    if self.fade > 0 then self.fade = self.fade - dt end
    if self.cool > 0 then self.cool = self.cool - dt end

    if loadNum("moving", 0) > 0.5 then
        self.moveX, self.moveZ = loadNum("moveX", 0), loadNum("moveZ", 1)
    end

    -- ================================ クリア / 失敗 ================================
    if self.mode == "clear" or self.mode == "fail" then
        local ok = (self.mode == "clear")
        ui:rect(0, 0, W, H, ok and 0.03 or 0.16, ok and 0.16 or 0.03, ok and 0.10 or 0.02, 0.86)
        labelC(W * 0.5, H * 0.34, ok and "CLEAR" or "FAILED", 66,
               ok and { 0.35, 1.0, 0.70 } or { 1.0, 0.45, 0.35 })
        labelC(W * 0.5, H * 0.48, self.msg or "", 26, C_INK)
        labelC(W * 0.5, H * 0.58, "[R] やり直す     [3] 第3面     [4] 第4面     [H] ルール",
               22, C_SUB)
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
            self.msg = string.format("残り %.1f 秒 / 使わずに済んだ接続 %d 本",
                                     self.timeLeft, self.budget)
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
                    local base = (i == self.aim) and (1 / 1.18) or 1.0
                    e.transform.scale = Vec3.new(sc.x * base * k, sc.y * base * k, sc.z)
                end
            end
        end
        for i = 1, #self.cand do
            tint("Proxy_" .. i, DOOR_COLOR[self.cand[i]] or { 1, 1, 1 },
                 (i == best) and 1.35 or 0.45)
        end
        self.aim = best

        if keyPressed("Q") then closeConnect(self) end
        if self.holdE <= 0 and keyPressed("E") then
            if best then
                local to, from = self.cand[best], self.connectDoor
                closeConnect(self)
                connect(self, from, to)
            else
                self.msg, self.msgT = "どのドアにも照準が合っていない", 1.8
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
                         (i == hotExit) and 1.3 or 0.55)
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
            self.mode = "fail"
            self.msg = "孤立した。もう出口へ辿り着けない"
            log("JUNCTION FAIL: " .. self.msg)
            return
        end
    end

    -- ================================ HUD ================================
    -- 照準点。白い虚無の上でも見えるように、暗い縁を敷いてから白い点を打つ
    ui:rect(W * 0.5 - 4, H * 0.5 - 4, 8, 8, 0, 0, 0, 0.5, 4)
    ui:rect(W * 0.5 - 2, H * 0.5 - 2, 4, 4, 1, 1, 1, 0.95, 2)

    -- ---- 上段: 面 / 残り時間 / 接続 ----
    panel(0, 0, W, 60, 0.5)
    label(24, 20, self.cfg.title, 21, C_SUB)

    local m = math.floor(self.timeLeft / 60)
    local s = self.timeLeft - m * 60
    local urg = self.timeLeft < 30
    labelC(W * 0.5, 13, string.format("%d:%05.2f", m, s), 33,
           urg and { 1.0, 0.42, 0.32 } or C_INK)

    do
        local gw = self.cfg.budget * 24
        local t = string.format("接続 %d / %d", self.budget, self.cfg.budget)
        label(W - 24 - gw - 14 - textW(t, 20), 20, t, 20, C_SUB)
        for i = 1, self.cfg.budget do
            local on = i <= self.budget
            ui:rect(W - 24 - gw + (i - 1) * 24 + 3, 25, 17, 12,
                    on and 0.20 or 0.28, on and 0.85 or 0.30, on and 0.58 or 0.28,
                    on and 0.95 or 0.45, 2)
        end
    end

    -- ---- 今やること(常に出す) ----
    labelC(W * 0.5, 70, "> " .. objective(self), 21, C_ACC)

    -- ---- 下段: 文脈に応じた案内。幅は実測して自動で合わせる ----
    local lines = {}
    if self.mode == "connect" then
        lines[#lines + 1] = { "白い虚無 / まだつながっていないドアが浮かんでいる（大きい＝近い）", 21, C_INK }
        local parts = {}
        for i, o in ipairs(self.cand) do
            parts[#parts + 1] = (i == self.aim and ">" or "  ") .. (DOOR_CNAME[o] or o)
        end
        lines[#lines + 1] = { "候補（左から）  " .. table.concat(parts, "    "), 23,
                              self.aim and C_ACC or C_SUB }
        lines[#lines + 1] = { "[E] このドアとつなぐ     [Q] やめる", 19, C_SUB }
    elseif near and nearD < REACH then
        local exits = exitsOf(self, near)
        local cn = DOOR_CNAME[near] or near
        if #exits == 0 then
            lines[#lines + 1] = { cn .. "のドア / まだつながっていない。向こうは白い虚無", 21, C_INK }
            lines[#lines + 1] = { "[E] 触れて、つなぐ相手を選ぶ", 21, C_ACC }
        elseif #exits == 1 then
            lines[#lines + 1] = { string.format("%sのドア / 出口は %s の 1 つだけ。角度は関係ない",
                                  cn, DOOR_CNAME[exits[1]] or exits[1]), 21, C_INK }
            lines[#lines + 1] = { "そのまま歩いて入る     [E] さらにつなぐ", 19, C_SUB }
        else
            lines[#lines + 1] = { string.format("%sのドア / %d枚の合流点 / 出口 %d つ",
                                  cn, #exits + 1, #exits), 21, C_INK }
            if hotExit and exits[hotExit] then
                local d = self.doors[near]
                local th = signedAngle(d.outX, d.outZ, self.moveX, self.moveZ)
                -- ★扇は正面 ±60°しかない。それを超えた向きで「行き先」を予測して出すと、
                --   「+150° なのに緑に出る」という意味不明な表示になる(実際に出た)。
                --   範囲外は行き先を出さず、入り直せと言う。
                if math.abs(th) > FAN_DEG + 12 then
                    lines[#lines + 1] = { string.format(
                        "いまの歩く向き %+.0f度 / ドアの正面から外れている。入り直す", th),
                        25, { 1.0, 0.62, 0.30 } }
                else
                    lines[#lines + 1] = { string.format(
                        "いまの歩く向き %+.0f度  ->  %s のドアに出る",
                        th, DOOR_CNAME[exits[hotExit]] or exits[hotExit]), 25,
                        DOOR_COLOR[exits[hotExit]] or C_INK }
                end
            end
            lines[#lines + 1] = { "床の色の道から助走して入る     [E] さらにつなぐ", 19, C_SUB }
        end
    elseif not self.touched then
        lines[#lines + 1] = { "WASD で歩く。ドアに近づいて [E]", 22, C_INK }
        lines[#lines + 1] = { "[H] でルールを読める", 19, C_SUB }
    end

    if #lines > 0 then
        local wmax, htot = 0, 0
        for _, L in ipairs(lines) do
            wmax = math.max(wmax, textW(L[1], L[2]))
            htot = htot + L[2] + 12
        end
        local pad = 24
        local bw = math.min(W - 32, wmax + pad * 2)
        local bx, by = W * 0.5 - bw * 0.5, H - 38 - htot - pad
        panel(bx, by, bw, htot + pad, 0.72)
        local y = by + pad * 0.5
        for _, L in ipairs(lines) do
            label(bx + pad, y, L[1], L[2], L[3])
            y = y + L[2] + 12
        end
    end

    -- ---- メッセージ(中央上寄り。幅は実測してパネルを作る) ----
    if self.msgT > 0 and self.msg and self.msg ~= "" then
        local a = math.min(1, self.msgT / 0.5)
        local size, pad = 26, 20
        local bw = textW(self.msg, size) + pad * 2
        local bx, by = W * 0.5 - bw * 0.5, H * 0.26
        panel(bx, by, bw, size + pad, 0.74 * a)
        label(bx + pad, by + pad * 0.5, self.msg, size, C_INK, a)
    end

    -- ---- 通過フェード(白) ----
    if self.fade > 0 then
        ui:rect(0, 0, W, H, 1, 1, 1, self.fade / FADE_TIME)
    end
end
