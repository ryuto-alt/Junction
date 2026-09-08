-- JUNCTION / stagedemo3 「見たものが、そうなる」
-- ★このファイルが編集元。assets/components/Liminal.lua は gen_liminal.py が書き出す複製。
--
-- 仕組みはひとつだけ:
--   建物の破片は、焦点 F から見たときだけ【本物と同じ形に重なる】ように置いてある
--   (F 中心の相似変換 P' = F + k(P-F))。プレイヤーの目がその位置へ来ると、対応点への
--   視線の角度差が 0 に近づく。lock 度未満まで詰めて【見て】いれば、破片は本物になる。
-- ★押すボタンは無い。歩いて、見る。それだけ。
--
-- ★★2026-09-06 改訂「しれっとつながる」:
--   つながる演出を全部やめた。環(HUD)・近づく合図の音・確定音・粒子・継ぎ目の光の増減・
--   ドローンの音程 — 全部削除。合い具合を伝えるのは【破片そのものの重なり】だけ。
--   確定の瞬間は k を 1 へ【一瞬で】飛ばす。焦点から見た投影は元々一致しているので、
--   この飛びは画面上まったく見えない(＝合った瞬間には何も起きない)。
--   目に見える変化(扉が開く・塞ぎ板が消える・標識が点く)は 2 通りに分ける:
--     ・その継ぎ目が【視界の外】なら … 一度に置く。どうせ見えないので一番きれい
--       (振り返るともう開いている ＝ 変化の見落とし change blindness)
--     ・【見られている】なら       … 0.5 秒後からイージングで動かす。
--       音も光も粒子も足さない。扉は扉の速さで、静かに開くだけ。
--   ★どちらの道でも【待たせない・カクッとさせない】のが条件。
--     待たせると「解いたのに開かない」、瞬間移動させると板に体を押しつけたまま消えて
--     前へつんのめる。2026-09-06 に実際に両方やらかした。

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
local PERI_IN = 24.0          -- 【直視しない】規則: これより内側だと成立しない
local PERI_OUT= 62.0          -- 【直視しない】規則: これより外だと視界の外
local SWEEP_CONE = 4.0        -- 【なぞる】規則: 照準がこの角度内を通った節だけ溶接される
local TRAIL_R    = 0.95       -- 【踏んでなぞる】規則: 擦れ跡を踏んだと認める半径(m)
local RELAY_BACK = 1.60       -- 【送り】規則: 間に合わなかった時、機械が休みへ戻る時間(秒)
local DWELL   = 0.36          -- 合った状態を保つ時間(★歩き抜けで暴発しない長さ)
local STILL   = 1.10          -- この速さ以下でないと確定しない(通りすがりで決まらない)
-- ★★「くっついたのがすぐ分かる」対策 = 変化の見落とし(change blindness)の実装。
--   破片を実体へ寄せるのは【視線が動いている / 歩いている / 視界の端】のどれかが
--   成立した瞬間。人間はその間の局所的な変化をほぼ検出できない(サッカード抑制)。
--   どれも来なければ WELD_WAIT で諦めて、WELD_T のイージングで静かに寄せる。
local WELD_WAIT = 0.45        -- マスクを待つ上限
local WELD_T    = 0.18        -- 寄せる時間
local MASK_TURN = 55.0        -- 視線の角速度(度/秒)。これ以上ならマスクが効く
local MASK_MOVE = 1.20        -- 歩く速さ(m/s)。これ以上ならマスクが効く
local DARK_PERIOD = 3.60      -- 明滅する部屋の周期
local DARK_LEN    = 1.05      -- そのうち「暗」の長さ
-- ★目に見える変化を「視界の外」でやるための角度と、見ている時に動き出すまでの間。
-- ★fov 72(縦)・16:9 の画面の端はちょうど 52 度。60 度なら【確実に画面の外】
-- ★★FORCE_T は【6 秒にしてはいけない】。扉へ向かって歩く間ずっと扉を見ているので
--   away が溜まらず、6 秒間ドアが開かない＝「解いたのに開かない」になる。
--   しかも待たされた末に瞬間移動するので、板に体を押しつけた状態で消えて【前へつんのめる】。
--   0.5 秒で動き出し、あとはイージングで開く(見ていなければ一度に置く)。
local AWAY    = 60.0          -- これより外に出たら『見ていない』
local AWAY_T  = 0.12          -- 視界の外に居続ける時間(端でチラつかせない)
local FORCE_T = 0.50          -- 見ていても、この秒数で動き出す(イージングで)
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
-- (smooth は補間用だった。つながる演出を全部やめたので、いま使うのは昇降床だけ)
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

-- 規則F「かくれて合わせる」: 指定した点が【何かの陰に隠れている】か。
-- ★偽物が見えている限り決まらない継ぎ目に使う。目 -> 点 の線分が遮蔽箱を通れば「隠れた」。
--   机上検査(sim_liminal.occluded)と必ず同じ式にしておくこと。
local function hidden(occl, ex, ey, ez)
    local p = occl.p
    local o = {ex, ey, ez}
    local d = {p[1] - ex, p[2] - ey, p[3] - ez}
    for i = 1, #occl.boxes do
        local b = occl.boxes[i]
        local t0, t1, ok = 0.0, 1.0, true
        for a = 1, 3 do
            if math.abs(d[a]) < 1e-9 then
                if o[a] < b[a] or o[a] > b[a + 3] then ok = false break end
            else
                local ta = (b[a] - o[a]) / d[a]
                local tb = (b[a + 3] - o[a]) / d[a]
                if ta > tb then ta, tb = tb, ta end
                if ta > t0 then t0 = ta end
                if tb < t1 then t1 = tb end
                if t0 > t1 then ok = false break end
            end
        end
        if ok then return true end
    end
    return false
end

-- 2 点が【画面上で重なって見えるか】の角度差(度)。「触れる」規則で使う。
-- ★これは焦点を使わない。見えている 2 つの物を一直線に並べるだけなので、
--   隠された焦点を探す規則よりずっと読みやすい ＝ 別の考え方の puzzle になる。
local function pairAngle(ex, ey, ez, a, b)
    local ax, ay, az = a[1] - ex, a[2] - ey, a[3] - ez
    local bx, by, bz = b[1] - ex, b[2] - ey, b[3] - ez
    local cx = ay * bz - az * by
    local cy = az * bx - ax * bz
    local cz = ax * by - ay * bx
    return math.deg(atan2(math.sqrt(cx * cx + cy * cy + cz * cz),
                          ax * bx + ay * by + az * bz))
end

-- u = 0 で【浮遊姿勢】、u = 1 で【実体】。
--   通常の破片は焦点まわりの相似変換(k -> 1)。
--   disp を持つ破片(「触れる」規則用)は、相似の縛りが無い自由な浮遊姿勢からの補間。
local function applyShard(sh, u, ox, oy, oz)
    ox, oy, oz = ox or 0, oy or 0, oz or 0
    if sh.disp then
        local w = 1.0 - u
        local sc = 1.0 + (sh.dk - 1.0) * w
        for i = 1, #sh.ents do
            local r = sh.ents[i]
            if r.e then
                r.e.transform.position = V(r.p[1] + sh.disp[1] * w + ox,
                                           r.p[2] + sh.disp[2] * w + oy,
                                           r.p[3] + sh.disp[3] * w + oz)
                r.e.transform.scale = V(r.s[1] * sc, r.s[2] * sc, r.s[3] * sc)
            end
        end
        return
    end
    local F = sh.F
    local kk = sh.k + (1.0 - sh.k) * u
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

-- 継ぎ目の輪郭線。★合い具合では【絶対に動かさない】(動かした瞬間に「演出」になる)。
--   壁より少し明るい金色の線として最初に一度だけ点け、以後そのまま。
--   これは信号ではなく「破片の形を読ませるための線」＝建物の一部という扱い。
local GLOW_BASE = 1.25
local function setGlow(c, power)
    for i = 1, #c.glowE do
        scene:setMeshParams(c.glowE[i], 1.0, 0.84, 0.52, power)
    end
end

function OnStart(self)
    self.body = find("LM_Player")
    self.cam  = find("LM_Camera")
    local r = scene:findEntity("LM_Ring")       -- ★環は廃止。古いシーンでも落ちないように
    self.ring = (r and r:isValid()) and r or nil
    self.hint = find("LM_Hint")
    self.endt = find("LM_End")

    self.yaw, self.pitch = 0.0, 0.0
    self.vx, self.vz = 0.0, 0.0
    self.t, self.cp, self.stepT = 0.0, 1, 0.0
    self.done, self.doneT = false, 0.0
    self.lockedIds = {}
    self.pending = {}          -- 確定はしたが【まだ目に見える変化を出していない】継ぎ目
    self.tweens = {}           -- 塞ぎ板が沈む / シャッターが巻き上がる(イージング)
    self.swings = {}           -- 扉が丁番でひらく(イージング)
    self.lamps  = {}           -- 標識が点く(イージング)

    -- 継ぎ目のテーブルを実体化(entity をここで 1 回だけ引く)
    self.conns = {}
    for i = 1, #CONNS do
        local d = CONNS[i]
        local c = { id = d.id, F = d.focus, lock = d.lock, warn = d.warn, center = d.center,
                    note = d.note, shards = {}, glowE = {}, solids = d.solids, movers = d.movers,
                    lights = d.lights, hinges = d.hinges or {}, excl = d.excl or {},
                    shines = d.shines or {}, hides = d.hides or {}, needs = d.needs or {},
                    anti = d.anti or false, minY = d.minY, maxY = d.maxY,
                    -- 新しい規則
                    perShard = d.perShard or false,   -- 破片を 1 つずつ、別の場所から
                    sweep    = d.sweep or false,      -- 【なぞる】端から端へ視線を流して溶接する
                    -- 【踏んでなぞる】床の擦れ跡を順に踏む。照準を一切使わない
                    trail    = d.trail, trailR = d.trailR or TRAIL_R, step = 0,
                    -- 【送り】東で合わせると機械が動き出す。動いている間だけ西が決まる
                    relay    = d.relay, armed = false, relayT = 0.0,
                    occl     = d.occl,                -- 【かくれて合わせる】陰に隠す
                    peri     = d.peri or false,       -- 【直視しない】周辺視でだけ合う
                    dark     = d.dark or false,       -- 暗くなった一瞬だけ合わせられる
                    touch    = d.touch,               -- 2 点が画面上で重なったら成立
                    darkLights = d.darkLights or {},
                    locked = false, cancelled = false,
                    a = 0.0, err = 999.0, hold = 0.0 }
        for s = 1, #d.shards do
            local sd = d.shards[s]
            -- ★焦点は【破片ごと】に持てる。これで新しい 2 つの規則が作れる:
            --   ・巡る    … 破片ごとに別の立ち位置。1 つずつ実体化していく
            --   ・二重拘束… 別々の焦点を【同時に】満たす 1 点を探す
            local sh = { k = sd.k, pts = sd.pts, F = sd.focus or d.focus, osc = sd.osc,
                         disp = sd.disp, dk = sd.dk or 1.0, ents = {},
                         done = false, hold = 0.0, anim = -1 }
            local lo, hi = { 1e9, 1e9, 1e9 }, { -1e9, -1e9, -1e9 }
            for j = 1, #sd.ents do
                local r = sd.ents[j]
                local e = find(r.n)
                sh.ents[#sh.ents + 1] = { e = e, p = r.p, s = r.s }
                for q = 1, 3 do
                    if r.p[q] < lo[q] then lo[q] = r.p[q] end
                    if r.p[q] > hi[q] then hi[q] = r.p[q] end
                end
            end
            sh.center = { (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2, (lo[3] + hi[3]) / 2 }
            applyShard(sh, 0.0)
            c.shards[#c.shards + 1] = sh
        end
        for g = 1, #d.glows do
            local e = find(d.glows[g])
            if e then c.glowE[#c.glowE + 1] = e end
        end
        setGlow(c, GLOW_BASE)
        self.conns[#self.conns + 1] = c
    end

    -- 明滅する部屋の灯り(継ぎ目が「暗の一瞬だけ」成立するために自分で振る)。
    -- ★troffer は <名前>_l が点光源、<名前>_p が乳白カバー。両方落とさないと
    --   ライトだけ消えてカバーが光ったままになり、暗くならない
    self.darkE = {}
    for i = 1, #self.conns do
        for j = 1, #self.conns[i].darkLights do
            local n = self.conns[i].darkLights[j]
            local le = scene:findEntity(n .. "_l")
            local pe = scene:findEntity(n .. "_p")
            local rec = {}
            if le and le:isValid() then
                rec.l = le:light()
                rec.base = rec.l and rec.l.intensity or 0.0
            end
            if pe and pe:isValid() then rec.p = pe end
            if rec.l or rec.p then self.darkE[#self.darkE + 1] = rec end
        end
    end

    -- 音: 部屋の唸りだけ。★合い具合のドローンは廃止(音程が上がる = つながる演出そのもの)
    self.hum = {}
    for _, p in ipairs({ { 0, 2.4, 1 }, { 0, 2.4, 13 }, { -4.5, 3.0, 20.6 }, { 0, 3.0, 28.8 },
                         { 4.9, 5.6, 55.5 }, { 6.1, 6.0, 68.5 },
                         { 1.5, 8.5, 89.0 }, { 6.0, 6.4, 106.4 }, { 6.0, 6.9, 112.0 },
                         { 17.0, 8.4, 127.0 }, { 17.5, 8.6, 145.0 },
                         -- 第三幕
                         { 22.0, 8.4, 173.2 }, { 17.0, 8.6, 179.0 }, { 25.0, 8.6, 194.0 },
                         { 43.4, 10.7, 198.6 }, { 51.6, 10.5, 195.4 }, { 63.5, 12.5, 203.0 } }) do
        self.hum[#self.hum + 1] = audio:playSpatialId("audio/lm/buzz.wav", p[1], p[2], p[3],
                                                      2.0, 13.0, 0.30, true)
    end

    -- ★蛍光灯の明滅。1 部屋に 1 本だけ。全部やると「演出」になって嘘くさくなる
    for _, n in ipairs({ "A_tr+09_l", "B_tr9_29_l", "C_tr14_56_l",
                         "T1_tr6_112_l", "M1_tr17_138_l",
                         "W1_tr_l", "T3_tr59_l", "T3d_tr53_203_l", "X3_tr209_l" }) do
        local e = scene:findEntity(n)
        if e and e:isValid() then
            local l = e:light()
            if l then Flicker(l, "fluorescent") end
        end
    end

    -- ★MCP 検証用フックは Play のたびに必ず落とす(前回の値が残ると
    --   人が遊んだときに勝手に歩き出す)
    self.sweepT, self.sweepId = 0.0, -1
    saveNum("lm_auto", 0); saveNum("lm_test", 0); saveNum("lm_warp", 0); saveNum("lm_tp", 0)
    saveNum("lm_sweep", 0)
    for i = 1, 24 do saveNum(string.format("lm_c%d", i), 0) end
    saveNum("lm_clear", 0)

    -- ★環(合い具合のHUD)は廃止。画面の中央は最後まで完全に空のまま。
    if self.ring then scene:setUiVisible(self.ring, false) end
    scene:setUiText(self.endt, "")
    scene:setUiColor(self.endt, 0.94, 0.93, 0.86, 0.0)
    input:setMouseCapture(true)
    saveNum("lm_locked", 0)
    -- ★【送り】規則の錘。休み位置をここで 1 回だけ覚える(動かした後の戻り先)
    for i = 1, #self.conns do
        local c = self.conns[i]
        if c.relay then
            local e = scene:findEntity(c.relay.weight)
            if e and e:isValid() then
                local p = e.transform.position
                c.wRest = { p.x, p.y, p.z }
                c.wDown = { p.x + c.relay.drop[1], p.y + c.relay.drop[2], p.z + c.relay.drop[3] }
            end
        end
    end

    log("LIMINAL: " .. #self.conns .. " joints. look, and it becomes.")
end

-- ================================================================ 扉(Door)
-- ★丁番まわりの回転。エンジンの yaw は行ベクトル系なので
--     (x,z) -> (x cos + z sin, -x sin + z cos)。符号を間違えると扉が壁側へ開く。
-- ★★以前の版はここで【生成時に焼き込んだ座標】を使っていた。ところが扉板は破片でもあり、
--   その座標は shard() が縮めた後の値だった ＝ 開くと同時に扉が 3m 手前へ飛んでから回る、
--   という壊れ方をしていた(これが「ドアの開閉がおかしい」の正体)。
--   直し方は【焼き込みを使わず、その場の transform を読む】こと。
--   確定時点で破片は既に k=1 へ戻っているので、これが常に正しい閉扉姿勢になる。
--   基準回転も足し込む(壁向きの扉は yaw=90 を持っているので、上書きすると横を向く)。
local function openDoor(e, piv, deg)
    local p, r = e.transform.position, e.transform.rotation
    local dx, dz = p.x - piv[1], p.z - piv[3]
    local th = math.rad(deg)
    local c_, s_ = math.cos(th), math.sin(th)
    e.transform.position = V(piv[1] + dx * c_ + dz * s_, p.y, piv[3] - dx * s_ + dz * c_)
    e.transform.rotation = V(r.x, r.y + deg, r.z)
end

-- ---------------------------------------------------------------- 機構の補間
-- ★これは「つながる演出」ではない。音も光も粒子も足さない。
--   ただ【瞬間移動でカクッとさせない】ためだけにある。扉は扉の速さで開く。
local function easeTo(self, e, to, dur, delay)
    self.tweens[#self.tweens + 1] = { e = e, from = nil, to = to,
                                      dur = math.max(dur or 1.1, 0.05), t = -(delay or 0.0) }
end

local function easeSwing(self, e, piv, deg, dur, delay)
    self.swings[#self.swings + 1] = { e = e, piv = piv, deg = deg, from = nil, base = nil,
                                      dur = math.max(dur or 1.3, 0.05), t = -(delay or 0.0) }
end

local function easeLamp(self, name, to, dur, delay)
    self.lamps[#self.lamps + 1] = { n = name, to = to,
                                    dur = math.max(dur or 0.8, 0.05), t = -(delay or 0.0) }
end

local function cancelTweens(self, name)
    local i = 1
    while i <= #self.tweens do
        if self.tweens[i].e and self.tweens[i].e:isValid()
           and self.tweens[i].e.name == name then
            table.remove(self.tweens, i)
        else
            i = i + 1
        end
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
                -- ★当たり判定は【動き出す瞬間】に外す。先に外すと閉じた板をすり抜け、
                --   最後まで残すと板に体を押しつけたまま消えて【前へつんのめる】
                physics:removeRigidBody(w.e)
            end
            local u = smooth(w.t / w.dur)
            w.e.transform.position = V(w.from[1] + (w.to[1] - w.from[1]) * u,
                                       w.from[2] + (w.to[2] - w.from[2]) * u,
                                       w.from[3] + (w.to[3] - w.from[3]) * u)
        end
        if w.t >= w.dur then table.remove(self.tweens, i) else i = i + 1 end
    end
end

local function runSwings(self, dt)
    local i = 1
    while i <= #self.swings do
        local w = self.swings[i]
        w.t = w.t + dt
        if w.t >= 0 then
            if not w.from then
                -- ★焼き込みではなく【その場の姿勢】を掴む(これが扉の飛びを直した肝)
                local p, r = w.e.transform.position, w.e.transform.rotation
                w.from = { p.x, p.y, p.z }
                w.base = { r.x, r.y, r.z }
            end
            local u = smooth(w.t / w.dur)
            local th = math.rad(w.deg * u)
            local dx, dz = w.from[1] - w.piv[1], w.from[3] - w.piv[3]
            local c_, s_ = math.cos(th), math.sin(th)
            w.e.transform.position = V(w.piv[1] + dx * c_ + dz * s_, w.from[2],
                                       w.piv[3] - dx * s_ + dz * c_)
            w.e.transform.rotation = V(w.base[1], w.base[2] + w.deg * u, w.base[3])
        end
        if w.t >= w.dur then table.remove(self.swings, i) else i = i + 1 end
    end
end

local function runLamps(self, dt)
    local i = 1
    while i <= #self.lamps do
        local w = self.lamps[i]
        w.t = w.t + dt
        if w.t >= 0 then
            local u = smooth(w.t / w.dur)
            local v = 0.36 + (w.to - 0.36) * u          -- 消灯時の板の色から立ち上げる
            local e = scene:findEntity(w.n)
            if e and e:isValid() then scene:setColor(e, v, v, v) end
            local le = scene:findEntity(w.n .. "_l")
            if le and le:isValid() then
                local lt = le:light()
                if lt then lt.intensity = 0.35 * u end
            end
        end
        if w.t >= w.dur then table.remove(self.lamps, i) else i = i + 1 end
    end
end

-- ---------------------------------------------------------------- 確定
-- 見えない変化(当たり判定)だけを、確定した瞬間に無音で入れる。
local function applySilent(self, c)
    for i = 1, #c.solids do
        local e = find(c.solids[i].n)
        if e then
            physics:removeRigidBody(e)
            e.transform.position = V(c.solids[i].p[1], c.solids[i].p[2], c.solids[i].p[3])
            physics:addRigidBody(e, 0, 1)
        end
    end
end

-- 目に見える変化。音も光の増減も足さない。
--   instant=true (継ぎ目が視界の外) … 一度に置く。どうせ見えないので一番きれい
--   instant=false(見られている)     … イージングで動かす。カクッとさせない
local function applyVisible(self, c, instant)
    for i = 1, #c.movers do
        local m = c.movers[i]
        local e = find(m.n)
        if e then
            if instant then
                physics:removeRigidBody(e)
                e.transform.position = V(m.to[1], m.to[2], m.to[3])
            else
                easeTo(self, e, m.to, m.dur, m.delay)
            end
        end
    end
    for i = 1, #c.lights do
        local l = c.lights[i]
        if instant then
            local e = find(l.n)
            if e then scene:setColor(e, l.to, l.to, l.to) end
            local le = scene:findEntity(l.n .. "_l")
            if le and le:isValid() then
                local lt = le:light()
                if lt then lt.intensity = 0.35 end
            end
        else
            easeLamp(self, l.n, l.to, l.dur, l.delay)
        end
    end
    for i = 1, #c.hinges do
        local h = c.hinges[i]
        local e = find(h.n)
        if e then
            if instant then openDoor(e, h.piv, h.deg)
            else easeSwing(self, e, h.piv, h.deg, h.dur, h.delay) end
        end
    end
    for i = 1, #c.shines do
        local sh = c.shines[i]
        local e = find(sh.n)
        if e then scene:setMeshParams(e, sh.c[1], sh.c[2], sh.c[3], sh.c[4]) end
    end
    -- 消える物(負の継ぎ目で塞がれた道の反対側 / 多義で選ばれなかった方)
    for i = 1, #c.hides do
        local e = find(c.hides[i])
        if e then
            physics:removeRigidBody(e)
            local p = e.transform.position
            e.transform.position = V(p.x, p.y - 400.0, p.z)
        end
    end
end

-- 破片を「決めた」ことにする。実際に寄せるのはマスクが来てから(下の runShards)
local function decideShard(sh)
    if sh.decided then return end
    sh.decided = true
    sh.queued = true
    sh.qt = 0.0
end

-- 決まった破片を、マスクが効いた瞬間に静かに寄せる
local function runShards(self, dt, masked)
    for i = 1, #self.conns do
        local c = self.conns[i]
        for s = 1, #c.shards do
            local sh = c.shards[s]
            if sh.queued then
                sh.qt = sh.qt + dt
                if masked or sh.qt >= WELD_WAIT then
                    sh.queued = false
                    sh.anim = 0.0
                end
            elseif sh.anim >= 0.0 then
                sh.anim = sh.anim + dt / WELD_T
                local u = smooth(sh.anim)
                local ox, oy, oz = shardOffset(sh, self.t)
                applyShard(sh, u, ox * (1 - u), oy * (1 - u), oz * (1 - u))
                if sh.anim >= 1.0 then
                    sh.anim = -1.0
                    sh.done = true
                    applyShard(sh, 1.0)
                end
            end
        end
    end
end

local function resolve(self, c)
    for s = 1, #c.shards do decideShard(c.shards[s]) end
    applySilent(self, c)
    c.locked = true
    self.lockedIds[c.id] = true
    self.pending[#self.pending + 1] = { c = c, t = 0.0, away = 0.0 }
    -- ★同じ破片を取り合う継ぎ目(多義)。片方が決まったら、もう片方は永久に成立しない。
    --   「どちらの世界にするか」をプレイヤーが選んだ、という事にする
    for i = 1, #c.excl do
        for j = 1, #self.conns do
            local o = self.conns[j]
            if o.id == c.excl[i] and not o.locked then
                o.locked = true
                o.cancelled = true
                log("LIMINAL joint " .. o.id .. " (" .. o.note .. ") is now impossible")
            end
        end
    end
    local n = 0
    for i = 1, #self.conns do if self.conns[i].locked then n = n + 1 end end
    saveNum("lm_locked", n)
    saveNum(string.format("lm_c%d", c.id), 1)
    log("LIMINAL joint " .. c.id .. " (" .. c.note .. ") resolved")
end

-- ================================================================ 通し検証(lm_sweep)
-- ★「印に立って中心を見る」を機械にやらせるだけ。判定は一切いじらない。
--   だから【これで解ければ人にも解ける】(逆は言えない ── 読めるかどうかは別)。
local function sweepStep(self, dt)
    -- 次に解くべき継ぎ目を選ぶ: 未確定・打ち切られていない・負でない・needs 充足
    local c = nil
    for i = 1, #self.conns do
        local q = self.conns[i]
        if (not q.locked) and (not q.cancelled) and (not q.anti) then
            local ok = true
            for j = 1, #q.needs do
                if not self.lockedIds[q.needs[j]] then ok = false end
            end
            if ok then c = q break end
        end
    end
    if not c then
        saveNum("lm_sweep", 0)
        saveNum("lm_sweep_done", 1)
        for i = 1, #self.conns do
            local q = self.conns[i]
            if not q.locked then
                local miss = ""
                for j = 1, #q.needs do
                    if not self.lockedIds[q.needs[j]] then
                        miss = miss .. tostring(q.needs[j]) .. " "
                    end
                end
                log("LIMINAL sweep: joint " .. q.id .. " left out (cancelled="
                    .. tostring(q.cancelled) .. " anti=" .. tostring(q.anti)
                    .. " needs-missing=[" .. miss .. "])")
            end
        end
        log("LIMINAL sweep: nothing left to solve")
        return
    end
    if c.id ~= self.sweepId then
        self.sweepId = c.id
        self.sweepT = 0.0
        log("LIMINAL sweep -> joint " .. c.id .. " (" .. c.note .. ")")
    end
    self.sweepT = self.sweepT + dt

    -- 立つ点と見る点
    local F, C = c.F, c.center
    if c.perShard then
        for s2 = 1, #c.shards do
            local sh = c.shards[s2]
            if not sh.decided then F = sh.F; C = sh.center break end
        end
    elseif c.touch then
        C = { (c.touch.a[1] + c.touch.b[1]) * 0.5,
              (c.touch.a[2] + c.touch.b[2]) * 0.5,
              (c.touch.a[3] + c.touch.b[3]) * 0.5 }
    end
    physics:setPosition(self.body, V(F[1], F[2] - EYE_OFF, F[3]))
    local dx, dy, dz = C[1] - F[1], C[2] - F[2], C[3] - F[3]
    local yaw = math.deg(atan2(dx, dz))
    -- ★規則D(直視しない)は正面に据えると絶対に決まらない。45 度ずらして見る
    if c.peri then yaw = yaw + 45.0 end
    self.yaw = yaw
    self.pitch = math.deg(math.atan(dy / math.max(math.sqrt(dx * dx + dz * dz), 0.001)))
    self.vx, self.vz = 0.0, 0.0
    -- ★暗の一瞬(E)と揺れ(osc)は【待つ時間】が要る。周期の 1.5 倍以上見ておくこと
    --   (v11 の実機検証で、400 フレーム = 2.9 秒しか回さずに「解けない」と誤判定した)
    if self.sweepT > 14.0 then
        saveNum("lm_sweep", 0)
        saveNum("lm_sweep_stuck", c.id)
        log("LIMINAL sweep STUCK at joint " .. c.id .. " (" .. c.note .. ")")
    end
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
        if loadNum("lm_sweep", 0) > 0.5 then
            -- 下の sweepStep が毎フレーム self.yaw / self.pitch を決める
        elseif loadNum("lm_test", 0) > 0.5 then
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
    -- ★z のしきい値ではなく【半径】で進める。第三幕は東へ折れるので z 単調ではない
    for i = self.cp + 1, #CHECKS do
        local ck = CHECKS[i]
        local dx, dz = p.x - ck.x, p.z - ck.z
        if dx * dx + dz * dz < ck.r * ck.r and math.abs(p.y - ck.y) < 2.0 then self.cp = i end
    end
    -- ★sweep 中は落下復帰を止める。焦点は到達点より 2m 以上低いことがあり、
    --   そのままだと置いた瞬間に引き戻されて 1 本も解けない
    if p.y < CHECKS[self.cp].y - 2.0 and not self.done and loadNum("lm_sweep", 0) < 0.5 then
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
    -- 見ているか(角度差の度)
    local function offAxis(px, py, pz)
        local dx, dy, dz = px - ex, py - ey, pz - ez
        local dl = math.max(math.sqrt(dx * dx + dy * dy + dz * dz), 0.001)
        return math.deg(math.acos(clamp((dx * fx_ + dy * fy_ + dz * fz_) / dl, -1, 1)))
    end
    -- ★変化を隠すマスク: 視線が動いている / 歩いている
    local turnSpd = (math.abs(((self.yaw - (self.pyaw or self.yaw) + 180) % 360) - 180)
                     + math.abs(self.pitch - (self.ppitch or self.pitch))) / math.max(dt, 1e-4)
    self.pyaw, self.ppitch = self.yaw, self.pitch
    local moveSpd = math.sqrt(self.vx * self.vx + self.vz * self.vz)
    local masked = (turnSpd > MASK_TURN) or (moveSpd > MASK_MOVE)
    local still = moveSpd < STILL
    -- 明滅する部屋の位相(暗の一瞬だけ合わせられる継ぎ目のため)
    self.darkNow = ((self.t % DARK_PERIOD) < DARK_LEN)
    for i = 1, #self.darkE do
        local d = self.darkE[i]
        if d.l then d.l.intensity = self.darkNow and 0.0 or d.base end
        if d.p then scene:setMeshParams(d.p, 1.0, 0.96, 0.86, self.darkNow and 0.06 or 1.35) end
    end

    if loadNum("lm_sweep", 0) > 0.5 then sweepStep(self, dt) end

    for i = 1, #self.conns do
        local c = self.conns[i]
        if not c.locked then
            -- 前提の継ぎ目(連鎖)と、暗の一瞬
            -- ★「止まっている」条件だけは分けて持つ。踏んでなぞる規則は【歩いている
            --   最中にしか進まない】ので、still を掛けると 1 歩も進まなくなる
            local gateB = ((not c.dark) or self.darkNow)
            for q = 1, #c.needs do
                if not self.lockedIds[c.needs[q]] then gateB = false end
            end
            -- ★目の高さの窓。「何段目に立つか」を問う継ぎ目はここで足切りする
            if c.minY and ey < c.minY then gateB = false end
            if c.maxY and ey > c.maxY then gateB = false end
            -- ★規則F: 偽物が柱の陰に入っていない間は、いくら合っていても決まらない
            if c.occl and not hidden(c.occl, ex, ey, ez) then gateB = false end
            local gate = gateB and still

            if c.relay then
                -- ---- 規則I「送り」: 東で合わせると機械が動き出す。その間だけ西が決まる ----
                --   ★この作品で唯一【時間に追われる】規則。ただし東で合わせた時点では
                --     何も確定させない ── 開くのは【窓】だけ。間に合わなくても失うものは
                --     無く、機械が休みへ戻るだけ(「確定した物は元へ戻さない」を守る)。
                --   ★見えている合図は錘が降りることそのもの。光も音も足していない。
                local function errOf(sh)
                    local ox, oy, oz = shardOffset(sh, self.t)
                    local fd = math.sqrt((sh.F[1] - ex) ^ 2 + (sh.F[2] - ey) ^ 2
                                         + (sh.F[3] - ez) ^ 2)
                    if fd > FOCUS_LOCK then return 999.0 end
                    return alignError(ex, ey, ez, sh.F, sh.k, sh.pts, ox, oy, oz)
                end
                local shA, shB = c.shards[1], c.shards[2]
                if not c.armed then
                    local e1 = errOf(shA)
                    c.err = e1
                    c.a = clamp(1.0 - e1 / c.warn, 0, 1)
                    if gate and e1 < c.lock
                       and offAxis(shA.center[1], shA.center[2], shA.center[3]) < CONE then
                        c.hold = c.hold + dt
                        if c.hold >= DWELL then
                            c.armed = true
                            c.relayT = c.relay.secs
                            c.hold = 0.0
                            if c.wDown then
                                cancelTweens(self, c.relay.weight)
                                easeTo(self, find(c.relay.weight), c.wDown, c.relay.secs, 0.0)
                            end
                            log("LIMINAL joint " .. c.id .. " armed for "
                                .. string.format("%.1f", c.relay.secs) .. "s")
                        end
                    else
                        c.hold = 0.0
                    end
                else
                    c.relayT = c.relayT - dt
                    local e2 = errOf(shB)
                    c.err = e2
                    c.a = clamp(1.0 - e2 / c.warn, 0, 1)
                    if gate and e2 < c.lock
                       and offAxis(shB.center[1], shB.center[2], shB.center[3]) < CONE then
                        c.hold = c.hold + dt
                        if c.hold >= DWELL then resolve(self, c) end
                    else
                        c.hold = 0.0
                    end
                    if not c.locked and c.relayT <= 0.0 then
                        c.armed = false
                        c.hold = 0.0
                        if c.wRest then
                            cancelTweens(self, c.relay.weight)
                            easeTo(self, find(c.relay.weight), c.wRest, RELAY_BACK, 0.0)
                        end
                        log("LIMINAL joint " .. c.id .. " relay window closed")
                    end
                end
                saveNum(string.format("lm_e%d", c.id), c.err)
                saveNum(string.format("lm_a%d", c.id), c.armed and c.relayT or 0.0)

            elseif c.trail then
                -- ---- 規則H「踏んでなぞる」: 床の擦れ跡を順に踏む ----
                --   この作品で唯一【照準を使わない】規則。目をつぶっても解ける。
                --   跡を 1 つ踏むごとに破片が 1 つ落ちるので、歩いた自分の後ろで
                --   物が組み上がっていく ＝ 見て決めるのではなく、歩いて決める。
                -- ★戻れない事はしない。踏み外しても跡は消えない(この作品の作法どおり、
                --   確定した物は絶対に元へ戻さない)。難しさは順序と道のりで出す。
                local n = #c.trail
                if gateB and c.step < n then
                    local w = c.trail[c.step + 1]
                    local dx, dz = w[1] - ex, w[2] - ez
                    if dx * dx + dz * dz < c.trailR * c.trailR then
                        c.step = c.step + 1
                        if c.shards[c.step] then decideShard(c.shards[c.step]) end
                        log("LIMINAL joint " .. c.id .. " trail " .. c.step .. "/" .. n)
                    end
                end
                c.err = (c.step >= n) and 0.0 or 99.0
                c.a = c.step / math.max(n, 1)
                saveNum(string.format("lm_n%d", c.id), n - c.step)
                if c.step >= n then resolve(self, c) end

            elseif c.touch then
                -- ---- 規則B「触れる」: 2 つの物が画面の上で重なったら成立 ----
                --   焦点は無い。見えている 2 点を一直線に並べるだけなので、
                --   奥行きには寛容で【向き】に厳しい ＝ 今までと真逆の手触りになる
                local mx = (c.touch.a[1] + c.touch.b[1]) * 0.5
                local my = (c.touch.a[2] + c.touch.b[2]) * 0.5
                local mz = (c.touch.a[3] + c.touch.b[3]) * 0.5
                local err = pairAngle(ex, ey, ez, c.touch.a, c.touch.b)
                c.err = err
                c.a = clamp(1.0 - err / c.warn, 0, 1)
                -- ★★遠ざかると 2 点の見かけの間隔も縮むので、【遠くから勝手に揃う】。
                --   相似規則で FOCUS_LOCK を入れたのと同じ罠。触れる規則にも上限が要る
                --   (入れ忘れて、ステージの反対側 240m 先から継ぎ目19 が確定した)。
                local d2 = math.sqrt((mx - ex) ^ 2 + (my - ey) ^ 2 + (mz - ez) ^ 2)
                if gate and offAxis(mx, my, mz) < CONE and err < c.lock
                   and d2 > (c.touch.near or 1.5) and d2 < (c.touch.far or 13.0) then
                    c.hold = c.hold + dt
                    if c.hold >= DWELL then resolve(self, c) end
                else
                    c.hold = 0.0
                end
                saveNum(string.format("lm_e%d", c.id), err)

            elseif c.sweep then
                -- ---- 規則G「なぞる」: 大まかに合った所から、端から端へ視線を流して溶接する ----
                --   今までの規則は全部「立ち止まって一点を探し、そこで待つ」だった。
                --   これは【首を振り切る】のが動詞。節は照準が通った瞬間に決まる(DWELL 無し)
                --   ので、正しい所に立って待っていても 1 節も進まない。
                local worst, left = 0.0, 0
                local fd = math.sqrt((c.F[1] - ex) ^ 2 + (c.F[2] - ey) ^ 2 + (c.F[3] - ez) ^ 2)
                for s = 1, #c.shards do
                    local sh = c.shards[s]
                    if not sh.decided then
                        left = left + 1
                        local ox, oy, oz = shardOffset(sh, self.t)
                        if sh.osc then applyShard(sh, 0.0, ox, oy, oz) end
                        local err = alignError(ex, ey, ez, sh.F, sh.k, sh.pts, ox, oy, oz)
                        if err > worst then worst = err end
                        if gate and err < c.lock and fd < FOCUS_LOCK
                           and offAxis(sh.center[1], sh.center[2], sh.center[3]) < SWEEP_CONE then
                            decideShard(sh)
                            left = left - 1
                            log("LIMINAL joint " .. c.id .. " slat " .. s .. " welded")
                        end
                    end
                end
                c.err = worst
                c.a = clamp(1.0 - worst / c.warn, 0, 1)
                saveNum(string.format("lm_e%d", c.id), worst)
                saveNum(string.format("lm_n%d", c.id), left)
                if left == 0 then resolve(self, c) end

            elseif c.perShard then
                -- ---- 規則C「巡る」: 破片ごとに別の立ち位置。1 つずつ実体化する ----
                local worst, left = 999.0, 0
                for s = 1, #c.shards do
                    local sh = c.shards[s]
                    if not sh.decided then
                        left = left + 1
                        local ox, oy, oz = shardOffset(sh, self.t)
                        if sh.osc then applyShard(sh, 0.0, ox, oy, oz) end
                        local fd = math.sqrt((sh.F[1] - ex) ^ 2 + (sh.F[2] - ey) ^ 2
                                             + (sh.F[3] - ez) ^ 2)
                        local err = 999.0
                        if fd < FOCUS_WARN then
                            err = alignError(ex, ey, ez, sh.F, sh.k, sh.pts, ox, oy, oz)
                        end
                        if err < worst then worst = err end
                        if gate and err < c.lock and fd < FOCUS_LOCK
                           and offAxis(sh.center[1], sh.center[2], sh.center[3]) < CONE then
                            sh.hold = sh.hold + dt
                            if sh.hold >= DWELL then
                                decideShard(sh)
                                left = left - 1
                                log("LIMINAL joint " .. c.id .. " piece " .. s .. " placed")
                            end
                        else
                            sh.hold = 0.0
                        end
                    end
                end
                c.err = worst
                c.a = clamp(1.0 - worst / c.warn, 0, 1)
                saveNum(string.format("lm_e%d", c.id), worst)
                saveNum(string.format("lm_n%d", c.id), left)
                if left == 0 then resolve(self, c) end

            else
                -- ---- 規則A(既定): 焦点まわりの相似。破片ごとに別の焦点も持てる ----
                local err, n, fdmax = 0.0, 0, 0.0
                for s = 1, #c.shards do
                    local sh = c.shards[s]
                    local ox, oy, oz = shardOffset(sh, self.t)
                    if sh.osc then applyShard(sh, 0.0, ox, oy, oz) end
                    local fd = math.sqrt((sh.F[1] - ex) ^ 2 + (sh.F[2] - ey) ^ 2
                                         + (sh.F[3] - ez) ^ 2)
                    if fd > fdmax then fdmax = fd end
                    -- ★k>1 の破片(遠くの巨大 → 手元の小)も必ず評価すること
                    if math.abs(sh.k - 1.0) > 0.001 or sh.osc then
                        local e2 = alignError(ex, ey, ez, sh.F, sh.k, sh.pts, ox, oy, oz)
                        if e2 > err then err = e2 end
                        n = n + 1
                    end
                end
                -- ★遠すぎる継ぎ目は評価しない。ここで err を 0 のままにすると
                --   「遠くから覗いただけで確定」になるので、必ず 999 を入れること
                if n == 0 or fdmax > FOCUS_WARN then err = 999.0 end
                c.err = err
                c.a = clamp(1.0 - err / c.warn, 0, 1)
                local off = offAxis(c.center[1], c.center[2], c.center[3])
                -- ★規則D「直視しない」: 周辺視でだけ成立する。正面で見ると絶対に決まらない
                local looking = c.peri and (off > PERI_IN and off < PERI_OUT) or
                                (not c.peri and off < CONE)
                if looking and gate and err < c.lock and fdmax < FOCUS_LOCK then
                    c.hold = c.hold + dt
                    if c.hold >= DWELL then resolve(self, c) end
                else
                    c.hold = 0.0
                end
                saveNum(string.format("lm_e%d", c.id), err)
                saveNum(string.format("lm_a%d", c.id), c.a)
            end
        end
    end
    runShards(self, dt, masked)

    -- ------------------------------------------------ しれっと変える
    -- ★確定した継ぎ目の【目に見える変化】は、視界から外れてから無音で一度に入れる。
    --   だから合った瞬間には何も起きない。振り返ると、もう開いている。
    do
        local i = 1
        while i <= #self.pending do
            local q = self.pending[i]
            local c = q.c
            q.t = q.t + dt
            local dx, dy, dz = c.center[1] - ex, c.center[2] - ey, c.center[3] - ez
            local dl = math.max(math.sqrt(dx * dx + dy * dy + dz * dz), 0.001)
            local cosv = (dx * fx_ + dy * fy_ + dz * fz_) / dl
            if cosv < math.cos(math.rad(AWAY)) then
                q.away = q.away + dt
            else
                q.away = 0.0
            end
            -- ★★破片が実体へ寄り切るまで、目に見える変化を始めてはいけない。
            --   先に始めると塞ぎ板やシャッターが【浮遊姿勢のまま】動き出して、
            --   「急にでっかくなって変な所へ飛ぶ」ように見える(実際にそう見えた)。
            local ready = true
            for s2 = 1, #c.shards do
                if not c.shards[s2].done then ready = false end
            end
            -- 視界の外なら一度に置く(見えないので一番きれい)。
            -- 見られているなら FORCE_T でイージング開始 ＝ 待たせないし、カクッともしない
            if ready and q.away >= AWAY_T then
                applyVisible(self, c, true)
                table.remove(self.pending, i)
            elseif ready and q.t >= FORCE_T then
                applyVisible(self, c, false)
                table.remove(self.pending, i)
            else
                i = i + 1
            end
        end
    end

    -- ------------------------------------------------ HUD
    -- ★環も、合い具合のドローンも無い。画面中央は最後まで空。
    --   合っているかどうかは【破片が重なって見えるか】だけで判断する。
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
    runLamps(self, dt)
    -- 検証用: いま動いている機構の数(0 なら止まっている)と、適用待ちの継ぎ目の数
    saveNum("lm_anim", #self.tweens + #self.swings + #self.lamps)
    -- 検証用: いま【実体へ寄せている最中 / マスク待ち】の破片の数
    local wq = 0
    for i = 1, #self.conns do
        for s2 = 1, #self.conns[i].shards do
            local sh = self.conns[i].shards[s2]
            if sh.queued or sh.anim >= 0.0 then wq = wq + 1 end
        end
    end
    saveNum("lm_weld", wq)
    saveNum("lm_pend", #self.pending)
    saveNum("lm_px", p.x); saveNum("lm_py", p.y); saveNum("lm_pz", p.z)
    saveNum("lm_yawr", self.yaw)
end
