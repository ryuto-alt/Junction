-- JUNCTION / stagedemo3 「見たものが、そうなる」
-- ★このファイルが編集元。assets/components/Liminal.lua は gen_liminal.py が書き出す複製。
--
-- 仕組みはひとつだけ:
--   建物の破片は、焦点 F から見たときだけ【本物と同じ形に重なる】ように置いてある
--   (F 中心の相似変換 P' = F + k(P-F))。プレイヤーの目がその位置へ来ると、対応点への
--   視線の角度差が 0 に近づく。lock 度未満まで詰めて【見て】いれば、破片は本物になる。
-- ★押すボタンは無い。歩いて、見る。それだけ。
-- ★画面に文字を出さない。合い具合は中央の環・継ぎ目の光・音の高さで伝える。

-- >>>DATA (gen_liminal.py が書く。手で触らない)
CONNS = {}
CHECKS = {}
GOAL = {}
-- <<<DATA

local EYE_OFF = 0.80          -- 体の中心から目まで
local SPEED   = 3.05
local ACCEL   = 13.0
local SENS    = 0.082
local CONE    = 26.0          -- 「見ている」と認める視野角(度)
local DWELL   = 0.28          -- 合った状態を保つ時間
-- ★★焦点からの距離で足切りする。これが無いと【遠くから勝手に揃う】。
--   角度差は対象までの距離に反比例して小さくなるので、30m 離れると
--   焦点の線から外れていても lock を割ってしまう(実機の通しで踏んだ)。
local FOCUS_WARN = 9.0        -- ここから環と光が反応する
local FOCUS_LOCK = 7.0        -- ここまで近づかないと確定しない

local function V(x, y, z) return Vec3.new(x, y, z) end
local function find(n)
    local e = scene:findEntity(n)
    if not (e and e:isValid()) then logWarn("Liminal: missing " .. n) return nil end
    return e
end
local function clamp(v, a, b) if v < a then return a elseif v > b then return b end return v end
local function smooth(t) t = clamp(t, 0, 1) return t * t * (3 - 2 * t) end

-- 対応点への視線の角度差(度)の最大値。atan2 版で 0 付近も安定して出る
-- ★Lua 5.4 は math.atan2 が消えて math.atan(y,x) になった。両方で動くようにする
local atan2 = math.atan2 or math.atan
local function alignError(ex, ey, ez, F, k, pts, ox, oy, oz)
    local worst = 0.0
    ox, oy, oz = ox or 0, oy or 0, oz or 0
    for i = 1, #pts do
        local p = pts[i]
        local ax, ay, az = p[1] - ex, p[2] - ey, p[3] - ez
        local bx = F[1] + k * (p[1] - F[1]) + ox - ex
        local by = F[2] + k * (p[2] - F[2]) + oy - ey
        local bz = F[3] + k * (p[3] - F[3]) + oz - ez
        local cx = ay * bz - az * by
        local cy = az * bx - ax * bz
        local cz = ax * by - ay * bx
        local cross = math.sqrt(cx * cx + cy * cy + cz * cz)
        local dot = ax * bx + ay * by + az * bz
        local d = math.deg(atan2(cross, dot))
        if d > worst then worst = d end
    end
    return worst
end

local function applyShard(sh, kk, ox, oy, oz)
    local F = sh.F
    ox, oy, oz = ox or 0, oy or 0, oz or 0
    for i = 1, #sh.ents do
        local r = sh.ents[i]
        if r.e then
            r.e.transform.position = V(F[1] + kk * (r.p[1] - F[1]) + ox,
                                       F[2] + kk * (r.p[2] - F[2]) + oy,
                                       F[3] + kk * (r.p[3] - F[3]) + oz)
            r.e.transform.scale = V(r.s[1] * kk, r.s[2] * kk, r.s[3] * kk)
        end
    end
end

-- 揺れる破片。★合う姿勢(o=0)で【速度も 0 になる】式にすること。
--   ここが最速だと「合う瞬間」が一瞬すぎて理不尽になる。(1-cos)/2 なら端で止まる。
local function shardOffset(sh, t)
    local o = sh.osc
    if not o then return 0, 0, 0 end
    local w = (1.0 - math.cos(2 * math.pi * ((t / o[4]) % 1.0))) * 0.5
    return o[1] * w, o[2] * w, o[3] * w
end

local function setGlow(c, power)
    for i = 1, #c.glowE do
        scene:setMeshParams(c.glowE[i], 1.0, 0.84, 0.52, power)
    end
end

function OnStart(self)
    self.body = find("LM_Player")
    self.cam  = find("LM_Camera")
    self.ring = find("LM_Ring")
    self.hint = find("LM_Hint")
    self.endt = find("LM_End")

    self.yaw, self.pitch = 0.0, 0.0
    self.vx, self.vz = 0.0, 0.0
    self.t, self.cp, self.stepT = 0.0, 1, 0.0
    self.done, self.doneT = false, 0.0
    self.tweens = {}
    self.swings = {}
    self.lockedIds = {}
    self.ringA, self.ringF = 0.0, 0.0

    -- 継ぎ目のテーブルを実体化(entity をここで 1 回だけ引く)
    self.conns = {}
    for i = 1, #CONNS do
        local d = CONNS[i]
        local c = { id = d.id, F = d.focus, lock = d.lock, warn = d.warn, center = d.center,
                    note = d.note, shards = {}, glowE = {}, solids = d.solids, movers = d.movers,
                    lights = d.lights, hinges = d.hinges or {}, excl = d.excl or {},
                    shines = d.shines or {},
                    locked = false, cancelled = false, anim = -1,
                    a = 0.0, err = 999.0, hold = 0.0, tick = 0 }
        for s = 1, #d.shards do
            local sd = d.shards[s]
            local sh = { k = sd.k, pts = sd.pts, F = d.focus, osc = sd.osc, ents = {} }
            for j = 1, #sd.ents do
                local r = sd.ents[j]
                local e = find(r.n)
                sh.ents[#sh.ents + 1] = { e = e, p = r.p, s = r.s }
            end
            applyShard(sh, sd.k)
            c.shards[#c.shards + 1] = sh
        end
        for g = 1, #d.glows do
            local e = find(d.glows[g])
            if e then c.glowE[#c.glowE + 1] = e end
        end
        setGlow(c, 1.25)
        self.conns[#self.conns + 1] = c
    end

    -- 音: 部屋の唸りと、合い具合のドローン(音量 0 から始める)
    self.drone = audio:playSFXId("audio/lm/drone.wav", true, 0.0)
    self.hum = {}
    for _, p in ipairs({ { 0, 2.4, 1 }, { 0, 2.4, 13 }, { -4.5, 3.0, 20.6 }, { 0, 3.0, 28.8 },
                         { 4.9, 5.6, 55.5 }, { 6.1, 6.0, 68.5 },
                         { 1.5, 8.5, 89.0 }, { 6.0, 6.4, 106.4 }, { 6.0, 6.9, 112.0 },
                         { 17.0, 8.4, 127.0 }, { 17.5, 8.6, 145.0 } }) do
        self.hum[#self.hum + 1] = audio:playSpatialId("audio/lm/buzz.wav", p[1], p[2], p[3],
                                                      2.0, 13.0, 0.30, true)
    end

    -- ★蛍光灯の明滅。1 部屋に 1 本だけ。全部やると「演出」になって嘘くさくなる
    for _, n in ipairs({ "A_tr+09_l", "B_tr9_29_l", "C_tr14_56_l",
                         "T1_tr6_112_l", "M1_tr17_138_l" }) do
        local e = scene:findEntity(n)
        if e and e:isValid() then
            local l = e:light()
            if l then Flicker(l, "fluorescent") end
        end
    end

    -- ★MCP 検証用フックは Play のたびに必ず落とす(前回の値が残ると
    --   人が遊んだときに勝手に歩き出す)
    saveNum("lm_auto", 0); saveNum("lm_test", 0); saveNum("lm_warp", 0); saveNum("lm_tp", 0)
    for i = 1, 12 do saveNum(string.format("lm_c%d", i), 0) end
    saveNum("lm_clear", 0)

    scene:setUiColor(self.ring, 1.0, 0.86, 0.55, 0.0)
    scene:setUiFill(self.ring, 0.0)
    scene:setUiText(self.endt, "")
    scene:setUiColor(self.endt, 0.94, 0.93, 0.86, 0.0)
    input:setMouseCapture(true)
    saveNum("lm_locked", 0)
    log("LIMINAL: " .. #self.conns .. " joints. look, and it becomes.")
end

local function tweenTo(self, e, to, dur, delay)
    self.tweens[#self.tweens + 1] = { e = e, from = nil, to = to, dur = dur, t = -(delay or 0) }
end

-- 丁番まわりの回転。★エンジンの yaw は行ベクトル系なので
--   (x,z) -> (x cos + z sin, -x sin + z cos)。符号を間違えると扉が壁側へ開く
local function runSwings(self, dt)
    local i = 1
    while i <= #self.swings do
        local w = self.swings[i]
        w.t = w.t + dt
        if w.t >= 0 then
            local u = smooth(w.t / w.dur)
            local th = math.rad(w.deg * u)
            local dx, dz = w.p[1] - w.piv[1], w.p[3] - w.piv[3]
            local c_, s_ = math.cos(th), math.sin(th)
            w.e.transform.position = V(w.piv[1] + dx * c_ + dz * s_, w.p[2],
                                       w.piv[3] - dx * s_ + dz * c_)
            w.e.transform.rotation = V(0, w.deg * u, 0)
        end
        if w.t >= w.dur then table.remove(self.swings, i) else i = i + 1 end
    end
end


local function runTweens(self, dt)
    local i = 1
    while i <= #self.tweens do
        local w = self.tweens[i]
        w.t = w.t + dt
        if w.t >= 0 then
            if not w.from then
                local p = w.e.transform.position
                w.from = { p.x, p.y, p.z }
            end
            local u = smooth(w.t / w.dur)
            w.e.transform.position = V(w.from[1] + (w.to[1] - w.from[1]) * u,
                                       w.from[2] + (w.to[2] - w.from[2]) * u,
                                       w.from[3] + (w.to[3] - w.from[3]) * u)
        end
        if w.t >= w.dur then
            table.remove(self.tweens, i)
        else
            i = i + 1
        end
    end
end

local function beginLock(self, c)
    c.anim = 0.0
    audio:playSFX("audio/lm/lock.wav")
    fx:burst{ x = c.center[1], y = c.center[2], z = c.center[3], kind = "glow", count = 26,
              size = 0.30, sizeEnd = 0.0, life = 0.9, speed = 1.6, spread = 1.0,
              r = 1.0, g = 0.86, b = 0.55, intensity = 2.0, drag = 1.4 }
    log("LIMINAL joint " .. c.id .. " (" .. c.note .. ") resolved")
end

local function finishLock(self, c)
    for i = 1, #c.solids do
        local e = find(c.solids[i].n)
        if e then
            physics:removeRigidBody(e)
            e.transform.position = V(c.solids[i].p[1], c.solids[i].p[2], c.solids[i].p[3])
            physics:addRigidBody(e, 0, 1)
        end
    end
    for i = 1, #c.movers do
        local m = c.movers[i]
        local e = find(m.n)
        if e then
            physics:removeRigidBody(e)
            tweenTo(self, e, m.to, m.dur, m.delay)
        end
    end
    for i = 1, #c.lights do
        local l = c.lights[i]
        local e = find(l.n)
        if e then scene:setColor(e, l.to, l.to, l.to) end
        local le = scene:findEntity(l.n .. "_l")
        if le and le:isValid() then
            local lt = le:light()
            if lt then lt.intensity = 0.35 end
        end
    end
    for i = 1, #c.hinges do
        local h = c.hinges[i]
        local e = find(h.n)
        if e then
            self.swings[#self.swings + 1] = { e = e, p = h.p, piv = h.piv, deg = h.deg,
                                              dur = h.dur, t = -(h.delay or 0) }
        end
    end
    for i = 1, #(c.shines or {}) do
        local sh = c.shines[i]
        local e = find(sh.n)
        if e then scene:setMeshParams(e, sh.c[1], sh.c[2], sh.c[3], sh.c[4]) end
    end
    if #c.movers > 0 then audio:playSFX("audio/lm/reveal.wav") end
    c.locked = true
    self.lockedIds[c.id] = true
    -- ★同じ破片を取り合う継ぎ目(多義)。片方が決まったら、もう片方は永久に成立しない。
    --   「どちらの世界にするか」をプレイヤーが選んだ、という事にする
    for i = 1, #c.excl do
        for j = 1, #self.conns do
            local o = self.conns[j]
            if o.id == c.excl[i] and not o.locked then
                o.locked = true
                o.cancelled = true
                o.anim = -1
                log("LIMINAL joint " .. o.id .. " (" .. o.note .. ") is now impossible")
            end
        end
    end
    local n = 0
    for i = 1, #self.conns do if self.conns[i].locked then n = n + 1 end end
    saveNum("lm_locked", n)
    saveNum(string.format("lm_c%d", c.id), 1)
end

function OnUpdate(self, dt)
    dt = math.min(dt, 0.06)
    self.t = self.t + dt
    -- Play 直後はシーン復元が transform を書き戻すので体を押し込む
    if self.t < 0.55 then
        physics:setPosition(self.body, V(CHECKS[1].x, CHECKS[1].y, CHECKS[1].z))
    end

    if keyPressed("ESC") then input:setMouseCapture(not input:isMouseCaptured()) end

    -- ------------------------------------------------ 視点
    if not self.done then
        if loadNum("lm_test", 0) > 0.5 then
            self.yaw = loadNum("lm_yaw", self.yaw)
            self.pitch = loadNum("lm_pitch", self.pitch)
        elseif input:isMouseCaptured() then
            self.yaw = self.yaw + input:getMouseDeltaX() * SENS
            self.pitch = self.pitch - input:getMouseDeltaY() * SENS
        end
        if keyDown("LEFT") then self.yaw = self.yaw - 90 * dt end
        if keyDown("RIGHT") then self.yaw = self.yaw + 90 * dt end
        if keyDown("UP") then self.pitch = self.pitch + 70 * dt end
        if keyDown("DOWN") then self.pitch = self.pitch - 70 * dt end
    end
    self.yaw = self.yaw % 360
    self.pitch = clamp(self.pitch, -78, 78)

    -- ------------------------------------------------ 移動
    local yr = math.rad(self.yaw)
    local wx, wz = 0.0, 0.0
    if not self.done then
        if keyDown("W") then wx = wx + math.sin(yr); wz = wz + math.cos(yr) end
        if keyDown("S") then wx = wx - math.sin(yr); wz = wz - math.cos(yr) end
        if keyDown("D") then wx = wx + math.cos(yr); wz = wz - math.sin(yr) end
        if keyDown("A") then wx = wx - math.cos(yr); wz = wz + math.sin(yr) end
    end
    -- ★MCP からの自動テスト用: 目的地(lm_gx, lm_gz)へ歩く。
    --   キー入力より後に上書きするので、人が遊ぶ時は一切影響しない(lm_auto=0)。
    if loadNum("lm_auto", 0) > 0.5 and not self.done then
        local q = self.body.transform.position
        local gx, gz = loadNum("lm_gx", q.x), loadNum("lm_gz", q.z)
        local dx, dz = gx - q.x, gz - q.z
        local d = math.sqrt(dx * dx + dz * dz)
        if d > 0.16 then
            wx, wz = dx / d, dz / d
            if loadNum("lm_test", 0) < 0.5 then self.yaw = math.deg(atan2(dx, dz)) end
        else
            wx, wz = 0, 0
        end
        saveNum("lm_gd", d)
    end
    local len = math.sqrt(wx * wx + wz * wz)
    local tx, tz = 0.0, 0.0
    if len > 0 then tx, tz = wx / len * SPEED, wz / len * SPEED end
    local f = clamp(ACCEL * dt, 0, 1)
    self.vx = self.vx + (tx - self.vx) * f
    self.vz = self.vz + (tz - self.vz) * f
    physics:move(self.body, self.vx, self.vz)

    local p = self.body.transform.position
    local ex, ey, ez = p.x, p.y + EYE_OFF, p.z
    self.cam.transform.position = V(ex, ey, ez)
    self.cam.transform.rotation = V(-self.pitch, self.yaw, 0)
    audio:setListener(ex, ey, ez)

    -- 足音(絨毯とタイルで替える)
    local moving = (self.vx * self.vx + self.vz * self.vz) > 1.2
    if moving then
        self.stepT = self.stepT + dt
        if self.stepT > 0.47 then
            self.stepT = 0.0
            local tile = (p.z > 40.5 and p.z < 62.0 and p.y < 2.0)
            audio:playSFX(tile and "audio/lm/step_hard.wav" or "audio/lm/step_soft.wav")
        end
    else
        self.stepT = 0.32
    end

    -- 到達点の更新と落下復帰
    for i = self.cp + 1, #CHECKS do
        if p.z > CHECKS[i].at then self.cp = i end
    end
    if p.y < CHECKS[self.cp].y - 2.0 and not self.done then
        local c = CHECKS[self.cp]
        physics:setPosition(self.body, V(c.x, c.y, c.z))
        self.vx, self.vz = 0, 0
    end
    -- デバッグ移動(MCP 検証用)
    local tp = loadNum("lm_tp", 0)
    if tp > 0.5 then
        local c = CHECKS[math.floor(tp)]
        if c then
            physics:setPosition(self.body, V(c.x, c.y, c.z))
            self.body.transform.position = V(c.x, c.y, c.z)
            self.cp = math.floor(tp)
        end
        saveNum("lm_tp", 0)
    end
    local warp = loadNum("lm_warp", 0)
    if warp > 0.5 then
        physics:setPosition(self.body, V(loadNum("lm_wx", p.x), loadNum("lm_wy", p.y), loadNum("lm_wz", p.z)))
        saveNum("lm_warp", 0)
    end

    -- ------------------------------------------------ 継ぎ目
    local fx_, fy_, fz_ = math.sin(yr) * math.cos(math.rad(self.pitch)),
                          math.sin(math.rad(self.pitch)),
                          math.cos(yr) * math.cos(math.rad(self.pitch))
    local best, bestC = 0.0, nil
    for i = 1, #self.conns do
        local c = self.conns[i]
        if c.anim >= 0 then
            -- 溶接中: k を 1 へ。揺れも同時に 0 へ寄せる
            c.anim = c.anim + dt / 0.85
            local u = smooth(c.anim)
            for s = 1, #c.shards do
                local sh = c.shards[s]
                local ox, oy, oz = shardOffset(sh, self.t)
                applyShard(sh, sh.k + (1.0 - sh.k) * u, ox * (1 - u), oy * (1 - u), oz * (1 - u))
            end
            setGlow(c, 5.2 * (1.0 - u) + 0.85)
            if c.anim >= 1.0 then
                c.anim = -1
                for s = 1, #c.shards do applyShard(c.shards[s], 1.0) end
                finishLock(self, c)
            end
        elseif c.locked then
            if not c.cancelled then
                setGlow(c, math.max(0.55, 0.85 - (self.t - (c.doneAt or self.t)) * 0.25))
            end
        else
            local dx, dy, dz = c.center[1] - ex, c.center[2] - ey, c.center[3] - ez
            local dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            local fdx, fdy, fdz = c.F[1] - ex, c.F[2] - ey, c.F[3] - ez
            local fdist = math.sqrt(fdx * fdx + fdy * fdy + fdz * fdz)
            local err, n = 0.0, 0
            -- ★遠すぎる継ぎ目は評価しない。ここで err を 0 のままにすると
            --   「遠くから覗いただけで確定」になるので、必ず 999 を入れること
            if fdist < FOCUS_WARN then
                for s = 1, #c.shards do
                    local sh = c.shards[s]
                    local ox, oy, oz = shardOffset(sh, self.t)
                    if sh.osc then applyShard(sh, sh.k, ox, oy, oz) end   -- 揺れる破片
                    if sh.k < 0.999 or sh.osc then
                        local e2 = alignError(ex, ey, ez, sh.F, sh.k, sh.pts, ox, oy, oz)
                        if e2 > err then err = e2 end
                        n = n + 1
                    end
                end
            end
            if n == 0 then err = 999.0 end
            c.err = err
            local a = clamp(1.0 - err / c.warn, 0, 1)
            -- 見ているか(視線と継ぎ目の中心の角度)
            local dl = math.max(dist, 0.001)
            local cosv = (dx * fx_ + dy * fy_ + dz * fz_) / dl
            local looking = cosv > math.cos(math.rad(CONE))
            c.a = a
            if a > best and looking then best = a; bestC = c end
            setGlow(c, 1.25 + 4.4 * a * a * a)
            if looking and err < c.lock and fdist < FOCUS_LOCK then
                c.hold = c.hold + dt
                if c.hold >= DWELL then beginLock(self, c); c.doneAt = self.t end
            else
                c.hold = 0.0
            end
            -- 近づいた合図(段階が上がった時だけ)
            local step = (a > 0.92 and 3) or (a > 0.75 and 2) or (a > 0.5 and 1) or 0
            if looking and step > c.tick then audio:playSFX("audio/lm/tick.wav") end
            c.tick = step
            saveNum(string.format("lm_e%d", c.id), err)
            saveNum(string.format("lm_a%d", c.id), a)
        end
    end

    -- ------------------------------------------------ HUD(環ひとつ)
    local ta = best
    self.ringA = self.ringA + (ta - self.ringA) * clamp(9.0 * dt, 0, 1)
    self.ringF = self.ringF + (ta - self.ringF) * clamp(14.0 * dt, 0, 1)
    scene:setUiColor(self.ring, 1.0, 0.86, 0.55, 0.86 * self.ringA ^ 0.8)
    scene:setUiFill(self.ring, self.ringF)
    if self.drone then
        audio:setVoiceVolume(self.drone, 0.34 * self.ringA ^ 1.4)
        audio:setVoicePitch(self.drone, 0.70 + 0.68 * self.ringA)
    end
    -- 操作の案内は 9 秒で消える(以後、画面に文字は出ない)
    local ha = clamp((11.0 - self.t) / 2.0, 0, 1) * 0.55
    if ha <= 0.005 then
        scene:setUiVisible(self.hint, false)      -- ★alpha 0 でも縁取りは残る。要素ごと消す
    else
        scene:setUiColor(self.hint, 0.92, 0.91, 0.85, ha)
    end

    -- ------------------------------------------------ 終わり
    if not self.done and self.lockedIds[GOAL.need]
       and p.z > GOAL.z and math.abs(p.x - GOAL.x) < GOAL.r and p.y > GOAL.y - 1.2 then
        self.done = true
        self.doneT = 0.0
        input:setMouseCapture(false)
        audio:playSFX("audio/lm/clear.wav")
        scene:setUiText(self.endt, "つながった")
        saveNum("lm_clear", 1)
        log("LIMINAL: complete")
    end
    if self.done then
        self.doneT = self.doneT + dt
        -- ★白く飛ばしっぱなしにすると UI もポストを浴びて文字が消える。
        --   閃光 -> 落ち着く、の 2 段にして、文字は落ち着いてから出す。
        local flash = clamp(self.doneT / 0.7, 0, 1)
        local settle = clamp((self.doneT - 0.7) / 1.3, 0, 1)
        post.set("exposure", 1.06 + 0.70 * flash - 0.45 * settle)
        local ta = clamp((self.doneT - 1.1) / 1.0, 0, 1)
        scene:setUiColor(self.endt, 0.12, 0.12, 0.11, ta)
        scene:setUiColor(self.ring, 1, 1, 1, 0)
        scene:setUiVisible(self.hint, self.doneT > 2.4)
        if self.doneT > 2.4 then
            if not self.endHint then
                self.endHint = true
                scene:setUiText(self.hint, "Enter")   -- setUiText は毎フレーム呼ばない
            end
            scene:setUiColor(self.hint, 0.20, 0.20, 0.18, 0.5)
        end
        if self.doneT > 2.6 and keyPressed("ENTER") then loadScene("scenes/stagedemo3.json") end
    end

    runTweens(self, dt)
    runSwings(self, dt)
    saveNum("lm_px", p.x); saveNum("lm_py", p.y); saveNum("lm_pz", p.z)
    saveNum("lm_yawr", self.yaw)
end
