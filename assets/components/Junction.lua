-- ============================================================================
-- JUNCTION / 継ぎ目 — ゲームロジック本体。シーンに 1 つだけ置く空エンティティに付ける。
-- エンティティ名 "Logic_Stage_1" .. "Logic_Stage_8" でステージ設定を引く。
--
-- ★2026-09-01(4) 作り直し: 【条件と角度を "撃つ前に" 見せる】
--   前回(文字を消してカメラと色で教える)は「条件が全く分からない/角度の説明が無い」で
--   失敗した。原因は docs/REDESIGN.md 冒頭。今回はこの 4 本で直している:
--     A 結線ビュー(TAB)  … このゲームはグラフパズルなのにグラフが一度も見えなかった
--     B 羅針(床の扇+針)  … 今の入射角がどの出口を指しているかの【実時間表示】。
--                          ★決定打は「ドアの中の虚無が行き先の色に染まる」。
--                            ストレイフすると目の前のドアの色が変わる = 通る前に分かる
--     C 接続ピン         … 予算を画面の隅の錠剤ではなく【世界に残る物】で示す
--     E 音               … 因果を伝える最速の channel(触れた/開いた/カチッ/繋いだ/通った)
--   角度の授業カメラ(teachAngle)は廃止した。角度は幾何とレベルデザインで教える。
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
--     Proxy_1..8       虚無に浮かぶ候補。全ドアで使い回す
--     Pilot / PilotLight  案内の光
--   ★Lua が実行時に scene:spawn する物(生成側は置かない。Mark_/Slice_/Lane_/Post_ の後継):
--     W_<id>_<k>  扇のスライス板 models/wedge120|60|40|30.gltf
--     Needle      入射角の針     models/needle.gltf (シーンに 1 本だけ)
--     Pin_<n>     刺さった接続ピン models/pin.gltf
--   ★scene:spawn / scene:remove は Play 中でも効く(2026-09-01 に実測で確認済み)。
--     モデルが無い時は spawn が【無効な entity を返すだけ】で落ちない = 揃うまで出ないだけ。
--   ★★ただしエンジンの落とし穴が 1 つある(実測):
--     【シーンを開いた時点で読み込まれていないモデルは、spawn しても "絵が出ない"】。
--     entity は valid、MeshRenderer も付く、AABB も正しい。ただ描画されないだけなので
--     Lua 側は一切エラーにならず、原因が絶対に分からない類のやつ。
--     (dx12_reload_assets を撃つと一斉に出る = GPU へのアップロードがシーン読み込み時にしか
--      走っていない。Editor でも Play でも同じなので Lua 側では回避できない。)
--     → wedge120/60/40/30 / needle / pin は【シーン JSON がどこかで 1 個参照している】必要がある。
--       gen_stages.py 側で床下(y=-200)にダミーを 1 個ずつ置いてもらうこと。
--       置かれるまでは扇・針・ピンだけが無言で出ない(それ以外は全部動く)。
-- ============================================================================

local STAGES = {
-- >>>STAGES (source/gen_stages.py が自動生成)
    ["Logic_Stage_1"] = { n = 1, scene = "scenes/stage1.json", next = "scenes/stage2.json",
        doors = { "a", "g" },
        room = { a = "S", g = "G" },
        budget = 1, start = "S", goalRoom = "G",
        spawn = { 0.0, 1.7, -4.2, 0.0 }, timed = false, teach = "connect",
        cine = {
            { -3.20, 1.90, -2.20, 12.60, 1.60, 2.60, 1.60 },
            { 3.00, 1.75, 0.40, 12.60, 1.70, 2.60, 2.40 },
            { 0.00, 1.70, -3.50, 0.00, 1.50, 6.00, 1.80 },
        } },
    ["Logic_Stage_2"] = { n = 2, scene = "scenes/stage2.json", next = "scenes/stage3.json",
        doors = { "a", "d", "g" },
        room = { a = "S", d = "A", g = "G" },
        budget = 3, start = "S", goalRoom = "G",
        spawn = { -3.0, 1.7, -3.6, 15.0 }, timed = false, teach = "angle",
        cine = {
            { 4.50, 3.20, 55.50, 0.00, 1.40, 46.00, 2.20 },
            { 0.00, 1.70, -3.50, 0.00, 1.50, 6.00, 0.02 },
            { 0.00, 1.70, -3.50, 0.00, 1.50, 6.00, 1.40 },
        } },
    ["Logic_Stage_3"] = { n = 3, scene = "scenes/stage3.json", next = "scenes/stage4.json",
        doors = { "a", "d", "g" },
        room = { a = "S", d = "A", g = "G" },
        budget = 3, start = "S", goalRoom = "G",
        spawn = { 7.2, 1.7, 0.0, 270.0 }, timed = true, teach = nil,
        cine = {
            { 0.00, 6.40, 68.00, 0.00, 0.40, 52.00, 1.20 },
            { 0.00, 2.40, 64.00, 0.00, 1.30, 51.00, 2.40 },
            { 7.00, 1.70, 0.00, -8.50, 1.60, 0.00, 0.02 },
            { 7.00, 1.70, 0.00, -8.50, 1.60, 0.00, 1.60 },
        } },
    ["Logic_Stage_4"] = { n = 4, scene = "scenes/stage4.json", next = "scenes/stage5.json",
        doors = { "a", "b", "c", "d" },
        room = { a = "S", b = "P", c = "Q", d = "G" },
        budget = 2, start = "S", goalRoom = "G",
        spawn = { 3.4, 1.7, -4.0, 340.0 }, timed = true, teach = nil,
        cine = {
            { 0.00, 2.20, 49.40, 0.00, 1.20, 53.00, 0.90 },
            { 52.00, 2.20, -2.60, 52.00, 1.20, 1.00, 0.02 },
            { 52.00, 2.20, -2.60, 52.00, 1.20, 1.00, 0.90 },
            { 52.00, 4.00, 44.00, 52.00, 1.40, 54.60, 0.02 },
            { 52.00, 4.00, 44.00, 52.00, 1.40, 54.60, 1.60 },
            { 0.00, 1.70, -3.50, 0.00, 1.50, 6.00, 0.02 },
            { 0.00, 1.70, -3.50, 0.00, 1.50, 6.00, 1.40 },
        } },
    ["Logic_Stage_5"] = { n = 5, scene = "scenes/stage5.json", next = "scenes/stage6.json",
        doors = { "a", "b", "c", "d", "g" },
        room = { a = "S", b = "P", c = "Q", d = "R", g = "G" },
        budget = 3, start = "S", goalRoom = "G",
        spawn = { 0.0, 1.7, 0.0, 90.0 }, timed = true, teach = nil,
        cine = {
            { 208.00, 3.20, 148.00, 208.00, 1.40, 158.60, 1.60 },
            { -7.60, 1.60, 0.00, 8.60, 1.50, 0.00, 0.02 },
            { -7.60, 1.60, 0.00, 8.60, 1.50, 0.00, 1.00 },
            { 2.00, 1.60, 0.00, 8.60, 1.50, 0.00, 2.60 },
        } },
    ["Logic_Stage_6"] = { n = 6, scene = "scenes/stage6.json", next = "scenes/stage7.json",
        doors = { "a", "b", "c", "d", "g" },
        room = { a = "S", b = "P", c = "Q", d = "R", g = "G" },
        budget = 4, start = "S", goalRoom = "G",
        spawn = { 3.0, 1.7, 2.0, 270.0 }, timed = true, teach = nil,
        cine = {
            { 46.00, 2.40, 51.00, 52.00, 1.30, 42.50, 1.60 },
            { 58.00, 2.40, 51.00, 52.00, 1.30, 42.50, 2.80 },
            { 3.00, 1.70, 3.00, -6.00, 1.60, 0.00, 0.02 },
            { 3.00, 1.70, 3.00, -6.00, 1.60, 0.00, 1.50 },
        } },
    ["Logic_Stage_7"] = { n = 7, scene = "scenes/stage7.json", next = "scenes/stage8.json",
        doors = { "a", "b", "c", "d", "e", "f", "g" },
        room = { a = "S", b = "T", c = "P", d = "Q", e = "T", f = "U", g = "G" },
        budget = 4, start = "S", goalRoom = "G",
        spawn = { -3.0, 1.7, -2.0, 80.0 }, timed = true, teach = nil,
        cine = {
            { -7.00, 0.90, 52.00, 8.60, 2.40, 52.00, 1.40 },
            { 0.00, 0.90, 52.00, 8.60, 2.40, 52.00, 2.40 },
            { 0.00, 1.70, -3.00, 6.00, 1.60, 0.00, 0.02 },
            { 0.00, 1.70, -3.00, 6.00, 1.60, 0.00, 1.40 },
        } },
    ["Logic_Stage_8"] = { n = 8, scene = "scenes/stage8.json", next = nil,
        doors = { "a", "b", "c", "d", "e", "f", "g", "h" },
        room = { a = "S", b = "T", c = "P", d = "Q", e = "P", f = "U", g = "G", h = "S" },
        budget = 3, start = "S", goalRoom = "G",
        spawn = { 0.0, 1.7, 2.0, 270.0 }, timed = true, teach = nil,
        cine = {
            { 156.00, 2.00, 100.00, 156.00, 1.50, 106.60, 1.20 },
            { 156.00, 5.50, 95.40, 156.00, 1.20, 106.60, 2.60 },
            { 6.50, 1.70, 0.00, -8.60, 1.60, 0.00, 0.02 },
            { 6.50, 1.70, 0.00, -8.60, 1.60, 0.00, 1.60 },
        } },
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
local COMPASS_DIST = 7.0    -- 羅針(扇と針)が床に出る距離
local FAN_R        = 3.6    -- 扇の半径。wedge*.gltf は半径 1.0 に正規化されている
-- 出口数 1..4 に対する開き角。FAN_DEG*2 / nex と必ず一致する(120/60/40/30)
local WEDGE_MODEL  = { "models/wedge120.gltf", "models/wedge60.gltf",
                       "models/wedge40.gltf",  "models/wedge30.gltf" }

local C_WHITE     = { 1.0, 1.0, 1.0 }
local C_KEY       = { 0.95, 0.99, 0.94 }

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

-- ★音は別担当が同時に作っている。まだ無いファイルでも【落ちない】ように必ずここを通す。
--   因果(触れた/開いた/カチッ/繋いだ/刺さった/通った)を伝える最速の channel なので、
--   鳴らす場所を増やす時もこの 1 関数だけを呼ぶこと。
local function sfx(name)
    pcall(function() audio:playSFX("audio/ui/" .. name .. ".wav") end)
end

-- ---------------------------------------------------------------- 段階チュートリアル
-- ★キーの表示は「まだ覚えていない操作」だけ。規定回数やったら二度と出さない。
--   saveNum はメモリのみ = 面をまたいで持ち越し、アプリを閉じると忘れる
--   (次に遊ぶ人には、また最初の数回だけ出る)。
local NEED = { move = 1, touch = 2, pick = 2, cancel = 1, map = 1 }

local function learned(name)
    return loadNum("jx_lv_" .. name, 0) >= (NEED[name] or 1)
end

local function learn(name)
    if not learned(name) then
        saveNum("jx_lv_" .. name, loadNum("jx_lv_" .. name, 0) + 1)
    end
end

-- UI の出入り。id ごとに 0..1 を持って want へ寄せるだけ。
-- ★ぱっと出て ぱっと消えるのが一番しつこく見えるので、必ずこれを通して描く。
local function uiAnim(self, id, want, dt, speed)
    local a = self.ui[id] or 0
    a = a + ((want and 1 or 0) - a) * (1 - math.exp(-(speed or 9) * dt))
    if a < 0.002 then a = 0 elseif a > 0.998 then a = 1 end
    self.ui[id] = a
    return a
end

-- ---------------------------------------------------------------- カメラ演出
-- 演出中は self.cam(位置と向き)が正。OnUpdate が毎フレーム押し込む。

-- p から q を見る yaw/pitch
local function lookAt(px, py, pz, qx, qy, qz)
    local dx, dy, dz = qx - px, qy - py, qz - pz
    local flat = math.sqrt(dx * dx + dz * dz)
    return math.deg(atan2(dx, dz)), math.deg(atan2(dy, math.max(0.001, flat)))
end

-- ★開幕カメラが柱や壁に刺さる問題(REDESIGN D-4)。
--   目→注視点を毎フレーム raycast して、遮られていたら目を【上へ最大 +2.5m】逃がす。
--   それでも駄目なら注視点へ寄せる(近づけば必ず何かの手前に出る)。
--   ★RaycastHit は h.hit / h.distance の【プロパティ】。h.hit() は実行時エラー。
local function blocked(x, y, z, tx, ty, tz)
    local dx, dy, dz = tx - x, ty - y, tz - z
    local L = math.sqrt(dx * dx + dy * dy + dz * dz)
    if L < 0.4 then return false end
    local h = physics:raycast(Vec3.new(x, y, z), Vec3.new(dx / L, dy / L, dz / L), L - 0.30)
    return h.hit and h.distance < L - 0.30
end

local function clearEye(ex, ey, ez, tx, ty, tz)
    if not blocked(ex, ey, ez, tx, ty, tz) then return ex, ey, ez end
    for i = 1, 10 do                                   -- 0.25m 刻みで +2.5m まで
        local y = ey + i * 0.25
        if not blocked(ex, y, ez, tx, ty, tz) then return ex, y, ez end
    end
    for i = 1, 8 do                                    -- 上が駄目なら注視点へ寄る
        local k = i / 10
        local x, y, z = ex + (tx - ex) * k, ey + (ty - ey) * k, ez + (tz - ez) * k
        if not blocked(x, y, z, tx, ty, tz) then return x, y, z end
    end
    return ex, ey + 2.5, ez
end

local function camApply(self)
    local pl = ent("MainCamera")
    if not pl then return end
    local c = self.cam
    local x, y, z, yaw, pitch = c.x, c.y, c.z, c.yaw, c.pitch
    -- 注視点を持っている演出は、遮蔽を避けた目の位置から向きを引き直す
    if c.tx then
        x, y, z = clearEye(x, y, z, c.tx, c.ty, c.tz)
        yaw, pitch = lookAt(x, y, z, c.tx, c.ty, c.tz)
    end
    physics:setPosition(pl, Vec3.new(x, y, z))
    pl.transform.position = Vec3.new(x, y, z)   -- 同フレームの見た目用
    pl.transform.rotation = Vec3.new(-pitch, yaw, 0)
end

local function camSet(self, x, y, z, yaw, pitch)
    local c = self.cam
    c.x, c.y, c.z, c.yaw, c.pitch = x, y, z, yaw, pitch
    c.tx, c.ty, c.tz = nil, nil, nil
end

-- 目と注視点をセットで置く(カット)。以後 camApply が遮蔽を見てくれる
local function camSetAt(self, ex, ey, ez, tx, ty, tz)
    local c = self.cam
    c.x, c.y, c.z = ex, ey, ez
    c.tx, c.ty, c.tz = tx, ty, tz
    c.yaw, c.pitch = lookAt(ex, ey, ez, tx, ty, tz)
end

-- 目と注視点の両方を補間する版。cine 表と開幕演出はこちらを使う
-- (yaw/pitch を直接補間すると、遮蔽を避けて目がずれた時に注視点が飛ぶ)
local function camGoTo(self, ex, ey, ez, tx, ty, tz, dur)
    local c = self.cam
    local sx, sy, sz = c.x, c.y, c.z
    local ox, oy, oz = c.tx or tx, c.ty or ty, c.tz or tz
    local t = 0
    while t < dur do
        t = t + time.dt()
        local k = math.min(1, t / dur)
        k = k * k * (3 - 2 * k)                   -- smoothstep(緩急)
        camSetAt(self,
                 sx + (ex - sx) * k, sy + (ey - sy) * k, sz + (ez - sz) * k,
                 ox + (tx - ox) * k, oy + (ty - oy) * k, oz + (tz - oz) * k)
        wait(0)
    end
    camSetAt(self, ex, ey, ez, tx, ty, tz)
end

local function cineBegin(self)
    self.cine = true
    self.flash = 0
    saveNum("cineLock", 1)
end

local function cineEnd(self)
    -- 演出の最後は必ずプレイヤーの目の高さへ返す
    local c = self.cam
    c.tx, c.ty, c.tz = nil, nil, nil
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
    self.ui = self.ui or {}  -- UI の出入りアニメの現在値
    self.walkT = 0           -- 歩いた累計(WASD を覚えたかの判定)
    self.noAct = 0           -- 何も操作していない時間(詰まった人への出し直し)
    self.hint = 0
    self.lastHot, self.lastHotDoor = nil, nil
    self.touchNear = nil
    self.pinDeny = 0
    self.mapKeyT = 0
    self.endSfx = false
    -- 刺したピンを全部抜く([R] でやり直したのに前回のピンが残っていると嘘になる)。
    -- 扇と同じ理由で名前の総当たり(self を作り直されても置き去りにしない)
    for i = 1, 64 do
        local e = ent("Pin_" .. i)
        if e then scene:remove(e) end
    end
    self.pinN, self.pinOn = 0, {}
    -- ★虚無は【全ドア】白へ戻す。self.tinted だけ見ていると、ホットリロードや
    --   通過直後に染まったままのドアが残って「色が嘘をつく」
    self.tinted = nil
    for _, id in ipairs(self.cfg.doors) do
        tint("Void_" .. id, C_WHITE)
        local vl = ent("VoidLight_" .. id)
        if vl then local L = vl:light(); if L then L:setColor(1, 1, 1) end end
    end
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

    -- ★過渡期の後始末: 廃止した Mark_/Slice_/Lane_/Post_ は gen_stages.py 側が
    --   出力をやめるまでシーンに残っている。参照はしないが、床に置き去りの棒が
    --   散らかったままだと扇が読めないので、開幕で 1 回だけ床下へ落としておく。
    --   生成側が消したあとは hide() が空振りするだけなので、そのまま置いていて害はない。
    for _, id in ipairs(self.cfg.doors) do
        for k = 1, 6 do
            hide("Mark_" .. id .. "_" .. k);  hide("Slice_" .. id .. "_" .. k)
            hide("Lane_" .. id .. "_" .. k);  hide("Post_" .. id .. "_" .. k)
        end
    end

    -- ★BGM(蛍光灯のハム)はシーンをまたいで鳴らし続ける。playBGM は同じパスでも
    --   必ず頭出しするので、既に鳴っていたら呼び直さない(面が変わるたび途切れる)。
    pcall(function()
        if audio:getCurrentBGM() ~= "audio/amb/hum.wav" then
            audio:playBGM("audio/amb/hum.wav")
        end
    end)

    -- ★結線ビューのレイアウトは【部屋のワールド XZ】から作る。
    --   別にレイアウト表を持つと生成側と二重管理になって必ずズレる。
    do
        local acc = {}
        for _, id in ipairs(self.cfg.doors) do
            local r, d = self.cfg.room[id], self.doors[id]
            if d then
                local v = acc[r]
                if not v then v = { x = 0, z = 0, n = 0 }; acc[r] = v end
                v.x, v.z, v.n = v.x + d.x, v.z + d.z, v.n + 1
            end
        end
        self.rooms = {}
        local minx, maxx, minz, maxz = 1e9, -1e9, 1e9, -1e9
        for r, v in pairs(acc) do
            local x, z = v.x / v.n, v.z / v.n
            self.rooms[r] = { x = x, z = z }
            if x < minx then minx = x end
            if x > maxx then maxx = x end
            if z < minz then minz = z end
            if z > maxz then maxz = z end
        end
        self.gmin  = { x = minx, z = minz }
        self.gspan = { x = math.max(1.0, maxx - minx), z = math.max(1.0, maxz - minz) }
    end

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

-- ---------------------------------------------------------------- 羅針(扇と針)
-- 合流点の扇(スライス板)を全ドアぶん作り直す。
-- ★接続/崩壊/リセットの直後にだけ呼ぶ。毎フレーム spawn しない(spawn は安くない)。
-- ★以前の Mark_/Slice_/Lane_/Post_(細い線と柱)は廃止した。線では「今どの出口を
--   指しているか」が読めず、角度ルールがまったく伝わっていなかったので、
--   出口ごとに【面で塗った扇】を出して、狙っている 1 枚だけを明るくする。
function refreshDoors(self)
    -- 前の扇を消す。scene:remove は Play 中でも効く(実測済み)。
    -- ★消す対象は self に覚えた名前ではなく【名前を総当たり】する。Lua のホットリロードや
    --   OnStart のやり直しで self が作り直されると、覚えていた名前が消えて
    --   床に扇が置き去りになる(実際に踏んだ)。名前は規約なので総当たりで足りる。
    for _, id in ipairs(self.cfg.doors) do
        for k = 1, 4 do
            local e = ent("W_" .. id .. "_" .. k)
            if e then scene:remove(e) end
        end
    end
    self.fan = {}
    self.shownDoor = nil

    for _, id in ipairs(self.cfg.doors) do
        local d = self.doors[id]
        local exits = exitsOf(self, id)
        local nex = #exits
        if nex >= 1 then
            local w = (FAN_DEG * 2) / nex
            local model = WEDGE_MODEL[nex]
            local slices = {}
            for k = 1, nex do
                -- スライス k の中心角。判定(sliceIndex)と同じ式であることが命
                local ang = FAN_DEG - w * (k - 0.5)
                local dx, dz = rot2(d.outX, d.outZ, ang)
                -- 扇は【助走してくる向き】へ開く = ドアから部屋の中へ伸びる
                local yaw = math.deg(atan2(-dx, -dz))
                local nm  = "W_" .. id .. "_" .. k
                local col = vivid(DOOR_COLOR[exits[k]] or { 1, 1, 1 })
                if model then
                    -- 出るまでは床下に置いておく(近づいた時に place で持ち上げる)
                    local e = scene:spawn(nm, model, Vec3.new(d.x, HIDE_Y, d.z),
                                          Vec3.new(0, yaw, 0), Vec3.new(FAN_R, 1.0, FAN_R))
                    if e and e:isValid() then scene:setColor(e, col[1], col[2], col[3]) end
                end
                slices[k] = { yaw = yaw, col = col, name = nm }
            end
            self.fan[id] = slices
        end
    end
end

-- 扇を床へ出す。狙っている 1 枚だけ明るく、他は 0.35 倍に落とす
local function showFan(self, id, hot)
    local slices = self.fan and self.fan[id]
    if not slices then return end
    local d = self.doors[id]
    for k, sl in ipairs(slices) do
        place(sl.name, d.x, 0.015, d.z, sl.yaw, FAN_R, 1.0, FAN_R)
        tint(sl.name, sl.col, (k == hot) and 1.0 or 0.35)
    end
end

local function hideFan(self, id)
    local slices = self.fan and self.fan[id]
    if not slices then return end
    for _, sl in ipairs(slices) do hide(sl.name) end
end

-- 針。シーンに 1 本だけ spawn して、アクティブなドアの足元へ移す。
-- ★向きは【今の WASD の押し方向】。カメラの向きでも実速度でもない(README の掟)。
local function needle(self, id)
    if self.hasNeedle == nil then
        local e = scene:spawn("Needle", "models/needle.gltf",
                              Vec3.new(0, HIDE_Y, 0), Vec3.new(0, 0, 0), Vec3.new(1, 1, 1))
        self.hasNeedle = (e ~= nil and e:isValid())
    end
    if not self.hasNeedle then return end
    if not id then hide("Needle"); return end
    local d = self.doors[id]
    place("Needle", d.x, 0.05, d.z, math.deg(atan2(self.moveX, self.moveZ)))
end

-- ★決定打: ドアの中の虚無を、いま狙っている行き先のドア色に染める。
--   ストレイフすると【目の前のドアの色が変わる】ので、通る前に、文字なしで
--   「入り方で行き先が変わる」が分かる。合流していない時は必ず白へ戻す。
local function tintVoid(self, id, col)
    tint("Void_" .. id, col)
    local vl = ent("VoidLight_" .. id)
    if vl then
        local L = vl:light()
        if L then L:setColor(col[1], col[2], col[3]) end
    end
end

local function clearVoidTint(self)
    if self.tinted then
        tintVoid(self, self.tinted, C_WHITE)
        self.tinted = nil
    end
end

-- ---------------------------------------------------------------- 動きの演出

-- 繋がったドアの色枠を一瞬焚く(どのドアと繋がったのかを色で名乗らせる)
local function flashFrame(self, id)
    local c = DOOR_COLOR[id] or { 1, 1, 1 }
    task.spawn(function()
        local t = 0
        while t < 0.6 do
            t = t + time.dt()
            local k = 1.0 + 1.4 * math.sin(math.pi * math.min(1, t / 0.6))
            tint("Frame_" .. id .. "_-1", c, k)
            tint("Frame_" .. id .. "_1", c, k)
            tint("Frame_" .. id .. "_top", c, k)
            wait(0)
        end
        tint("Frame_" .. id .. "_-1", c); tint("Frame_" .. id .. "_1", c)
        tint("Frame_" .. id .. "_top", c)
    end)
end

-- 通過した瞬間の画角の突き上げ。白フェードだけだと「切り替わった」だけで
-- 「くぐった」感じが出ない
local function fovKick()
    task.spawn(function()
        local t = 0
        while t < 0.34 do
            t = t + time.dt()
            local pl = scene:findEntity("MainCamera")
            if pl and pl:isValid() then
                pl:setFov(74 + 10 * math.sin(math.pi * math.min(1, t / 0.34)))
            end
            wait(0)
        end
        local pl = scene:findEntity("MainCamera")
        if pl and pl:isValid() then pl:setFov(74) end
    end)
end

-- ---------------------------------------------------------------- 演出本体

-- 開幕: 出口の部屋を見せてから、開始の部屋のドアへ寄る。
-- 「あの緑の柱まで行け」「使えるのはこのドア」を文字なしで渡すのが目的。
-- ★式で決め打ちすると柱や壁に刺さる(REDESIGN D-4)。目と注視点の【両方】を持って
--   camApply の遮蔽逃がしに任せる。ステージ側に cine(手で書いた段取り)があればそれを使う。
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
    local cine = self.cfg.cine
    self.task = task.spawn(function()
        if cine and #cine > 0 then
            -- cine = { { ex,ey,ez, tx,ty,tz, dur }, ... }(ワールド座標。gen_stages.py が流し込む)
            for i, c in ipairs(cine) do
                if i == 1 then
                    -- 最初の 1 手はカット(瞬間移動 + 白フラッシュ)
                    camSetAt(self, c[1], c[2], c[3], c[4], c[5], c[6])
                    self.flash = 1.0
                    wait(c[7] or 1.5)
                else
                    camGoTo(self, c[1], c[2], c[3], c[4], c[5], c[6], c[7] or 2.0)
                end
            end
        else
            -- ① 出口の部屋。緑の柱をゆっくり寄って見せる
            if g then
                camSetAt(self, g.x + 5.0, 3.4, g.z - 5.2, g.x, 1.2, g.z)
                self.flash = 1.0
                camGoTo(self, g.x + 2.2, 2.0, g.z - 2.6, g.x, 1.2, g.z, 2.2)
                wait(0.25)
            end
            -- ② 開始の部屋。引きで部屋全体 → ドアへ寄る
            camSetAt(self, sp[1] - 4.0, 3.2, sp[3] - 2.0, d.x, 1.5, d.z)
            self.flash = 1.0
            camGoTo(self, sp[1], 2.6, sp[3] - 1.0, d.x, 1.5, d.z, 2.6)
            -- ③ プレイヤーの目線へ降りる
            camGoTo(self, sp[1], 1.7, sp[3], d.x, 1.7, d.z, 1.0)
        end
        cineEnd(self)
    end)
end

-- ---------------------------------------------------------------- 接続の実行

-- 接続した証としてピンをドア枠に刺す。予算を使ったことが【世界に残る】。
-- ★原点が針の先端なので、+Z が部屋の内側を向くように置くと枠へ刺さって見える。
local function stickPin(self, id)
    local d = self.doors[id]
    self.pinN  = (self.pinN or 0) + 1
    self.pinOn = self.pinOn or {}
    local k    = (self.pinOn[id] or 0) + 1
    self.pinOn[id] = k
    -- 1 枚のドアは何度も合流点に加わる。左右の枠柱へ交互・下へ段々に刺していく
    local side = (k % 2 == 1) and 1 or -1
    local row  = math.floor((k - 1) / 2)
    local nm   = "Pin_" .. self.pinN
    -- 枠柱は横 0.93m / 部屋側へ 0.24m。+Z が部屋の内側を向くと枠へ刺さって見える
    local e = scene:spawn(nm, "models/pin.gltf",
              Vec3.new(d.x + d.rgX * 0.93 * side + d.inX * 0.24, 1.70 - row * 0.34,
                       d.z + d.rgZ * 0.93 * side + d.inZ * 0.24),
              Vec3.new(0, math.deg(atan2(d.inX, d.inZ)), 0), Vec3.new(1, 1, 1))
    if e and e:isValid() then
        local c = DOOR_COLOR[id] or { 1, 1, 1 }
        scene:setColor(e, c[1], c[2], c[3])
    end
    sfx("pin")
end

local function connect(self, from, to)
    if self.budget <= 0 then
        self.hint = 0.8
        self.pinDeny = 0.55       -- 結線ビューのピン置き場が赤く弾ける
        sfx("deny")
        return
    end
    self.budget = self.budget - 1
    self.pipFlash = 0.45

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
        sfx("deny")               -- 合流点の崩壊。予算は戻らない
        clearVoidTint(self)
        refreshDoors(self)
        return
    end

    table.insert(list, to)
    self.group[to] = gid
    self.cool = 0.5   -- 繋いだ直後の 1 歩で通過しない猶予
    self.noAct = 0
    learn("pick")
    local td = self.doors[to]
    local c = DOOR_COLOR[to] or { 1, 1, 1 }
    fx:burst{ x = td.x, y = 1.4, z = td.z, kind = "glow", count = 14, size = 0.35,
              r = c[1], g = c[2], b = c[3] }
    clearVoidTint(self)
    refreshDoors(self)
    flashFrame(self, to)
    flashFrame(self, from)
    sfx("connect")
    stickPin(self, from)
    stickPin(self, to)

    -- ★TAB(結線ビュー)のキーキャップは、第1面で初めて接続が成立した瞬間に 1 回だけ。
    --   繋いだ直後こそ「今どこが繋がったのか」を見たい瞬間なので、ここで教える。
    if not learned("map") then
        learn("map")
        self.mapKeyT = 5.0
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
    if #cand == 0 then self.hint = 0.8; sfx("deny"); return end
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
    self.pxT = 0        -- 候補が順番に現れる演出の時計
    self.pxS = {}       -- 候補の基準スケール(毎フレームここから作る)
    self.noAct = 0
    learn("touch")
    sfx("open")
    -- 虚無を飛ばす前に色を白へ戻す(羅針の染めが残ると候補の色が読めない)
    clearVoidTint(self)

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
        self.pxS[i] = { 0.85 * s, 1.75 * s }
        place("Proxy_" .. i,
              d.x + d.outX * 2.25 + prX * (t * span), 1.42,
              d.z + d.outZ * 2.25 + prZ * (t * span), d.yaw, 0.001, 0.001, 0.07)
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
    if id then tintVoid(self, id, C_WHITE) end
    self.tinted = nil
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
    fovKick()
    sfx("pass")
    clearVoidTint(self)
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
    local s = 0.20 + 0.035 * math.sin(t * 4.3)      -- 呼吸するように脈打つ
    local e = place("Pilot", tx, y, tz, nil, s, s, s)
    place("PilotLight", tx, y, tz)
    local pl = ent("PilotLight")
    if pl then
        local L = pl:light()
        if L then L.intensity = 2.2 + 1.1 * (0.5 + 0.5 * math.sin(t * 4.3)) end
    end
end

-- ---------------------------------------------------------------- HUD
-- ★出す文字は操作キーだけ。ルールの説明文は 1 行も出さない。

local function capW(s, size)
    return #s * size * 0.62 + size * 0.7
end

-- a=0..1 で出入りする。中心 x 指定・ふわっと上下する。
local function keyCap(cx, y, s, size, a, bob)
    if a <= 0.02 then return end
    local sz = size * (0.80 + 0.20 * a)
    local w, h = capW(s, sz), sz * 1.45
    local x = cx - w * 0.5
    local yy = y + (bob and math.sin(time.now() * 4.0) * 2.6 or 0) + (1 - a) * 8
    ui:rect(x, yy, w, h, 0.03, 0.06, 0.04, 0.74 * a, 5)
    ui:rect(x + 1, yy + 1, w - 2, h - 2, 0.60, 0.68, 0.62, 0.30 * a, 5)
    ui:text(x + sz * 0.35, yy + sz * 0.22, s, sz, C_KEY[1], C_KEY[2], C_KEY[3], a)
end

local function worldKey(W, H, wx, wy, wz, s, a)
    -- ワールド座標の上にキーを出す。
    -- ★ camera:project は「:」で呼ぶ(Camera の userdata メソッド)。「.」だと
    --   第1引数が数値になって "expected userdata" で OnUpdate ごと落ちる。
    -- ★ドアに張り付くと的が画面の外へ出る(ドアの上端は目線より遥か上)。
    --   その時は照準の少し上へ逃がす。出ないのが一番困る。
    if a <= 0.02 then return end
    local u, v, vis = camera:project(wx, wy, wz)
    if not vis or u < 70 or u > W - 70 or v < 60 or v > H - 90 then
        u, v = W * 0.5, H * 0.5 - 62
    end
    keyCap(u, v - 18, s, 24, a, true)
end

-- ---------------------------------------------------------------- 結線ビュー(A)
-- ★このゲームはグラフパズルなのに、グラフが一度も見えないのが最大の欠陥だった。
--   部屋は 52m 離れた閉じた箱で、どこと繋がったか・自分が今どこかを知る手段が無い。
--   TAB 押しっぱなしで、文字のないノードグラフを重ねる。
-- ★レイアウトは【部屋のワールド XZ を画面へ正規化するだけ】。別のレイアウト表を持つと
--   生成側(gen_stages.py)と二重管理になって必ずズレる。
-- ★文字・数字は 1 つも置かない(REDESIGN の原則)。
local function drawGraph(self, W, H, a, t)
    if a <= 0.02 or not self.rooms then return end
    ui:rect(0, 0, W, H, 0.02, 0.03, 0.02, 0.60 * a)

    local gw = math.min(W, H) * 0.52
    local cx, cy = W * 0.5, H * 0.44
    local hw, hh = 42, 28
    local function P(x, z)
        local u = (x - self.gmin.x) / self.gspan.x - 0.5
        local v = (z - self.gmin.z) / self.gspan.z - 0.5
        return cx + u * gw, cy - v * gw            -- +Z を画面の上へ
    end
    -- ドアの点は「部屋の箱の縁」に置く。どっち側のドアかが形で分かる
    local function doorPt(id)
        local d, rp = self.doors[id], self.rooms[self.cfg.room[id]]
        if not (d and rp) then return nil end
        local bx, by = P(rp.x, rp.z)
        local dx, dy = P(d.x, d.z)
        local sx, sy = dx - bx, dy - by
        local L = math.sqrt(sx * sx + sy * sy)
        if L < 0.001 then return bx, by - hh end
        sx, sy = sx / L, sy / L
        local k = 1 / math.max(math.abs(sx) / hw, math.abs(sy) / hh)
        return bx + sx * k, by + sy * k
    end

    -- ---- 部屋。今いる部屋だけ塗り、他は輪郭だけ。出口の部屋は緑の枠 ----
    for r, rp in pairs(self.rooms) do
        local bx, by = P(rp.x, rp.z)
        local isGoal, isHere = (r == self.cfg.goalRoom), (r == self.room)
        if isHere then
            ui:rect(bx - hw, by - hh, hw * 2, hh * 2, 0.93, 0.97, 0.93, 0.90 * a, 8)
        end
        local c = isGoal and { 0.28, 0.95, 0.55 } or { 0.60, 0.66, 0.60 }
        local bw = isGoal and 3 or 2
        ui:rect(bx - hw, by - hh, hw * 2, bw, c[1], c[2], c[3], 0.9 * a, 1)
        ui:rect(bx - hw, by + hh - bw, hw * 2, bw, c[1], c[2], c[3], 0.9 * a, 1)
        ui:rect(bx - hw, by - hh, bw, hh * 2, c[1], c[2], c[3], 0.9 * a, 1)
        ui:rect(bx + hw - bw, by - hh, bw, hh * 2, c[1], c[2], c[3], 0.9 * a, 1)
        if isGoal then
            ui:rect(bx - 5, by - 5, 10, 10, 0.28, 0.95, 0.55, 0.95 * a, 5)
        end
    end

    -- ---- 接続。そのドアの色の点線。点は流れる(生きている感じ) ----
    for _, list in pairs(self.groups) do
        for i = 1, #list do
            for j = i + 1, #list do
                local ax, ay = doorPt(list[i])
                local bx, by = doorPt(list[j])
                if ax and bx then
                    local ca = DOOR_COLOR[list[i]] or C_WHITE
                    local cb = DOOR_COLOR[list[j]] or C_WHITE
                    local L = math.sqrt((bx - ax) ^ 2 + (by - ay) ^ 2)
                    local n = math.max(3, math.floor(L / 12))
                    local ph = (t * 0.5) % 1
                    for k = 0, n do
                        local u = (k + ph) / (n + 1)
                        if u <= 1 then
                            local c = (u < 0.5) and ca or cb
                            ui:rect(ax + (bx - ax) * u - 2, ay + (by - ay) * u - 2,
                                    4, 4, c[1], c[2], c[3], 0.85 * a, 2)
                        end
                    end
                end
            end
        end
    end

    -- ---- ドアの点(線より上に打つ) ----
    for _, id in ipairs(self.cfg.doors) do
        local x, y = doorPt(id)
        if x then
            local c = DOOR_COLOR[id] or C_WHITE
            local on = self.group[id] ~= nil
            ui:rect(x - 6, y - 6, 12, 12, 0, 0, 0, 0.55 * a, 6)
            ui:rect(x - 4, y - 4, 8, 8, c[1], c[2], c[3], (on and 1.0 or 0.45) * a, 4)
        end
    end

    -- ---- 未使用の接続予算をピンの形で並べる(右上の錠剤 HUD は廃止した) ----
    local n = self.cfg.budget
    local pw, gap = 10, 18
    local x0 = W * 0.5 - (n * pw + (n - 1) * gap) * 0.5
    local py = H * 0.84                     -- グラフと重ならないよう画面下に固定
    local dn = self.pinDeny or 0
    for i = 1, n do
        local on = i <= self.budget
        local x  = x0 + (i - 1) * (pw + gap)
        local c, al, g = { 0.93, 0.97, 0.93 }, 0.95 * a, 0
        if not on then c, al = { 0.32, 0.36, 0.32 }, 0.42 * a end
        -- 予算 0 で E を撃った = ピン置き場が赤く弾ける
        if dn > 0 then
            c  = { 1.0, 0.24, 0.20 }
            al = a * (0.45 + 0.55 * math.abs(math.sin(t * 30)))
            g  = 7 * (dn / 0.55)
        end
        ui:rect(x - g * 0.5, py - 12 - g, pw + g, pw + g, c[1], c[2], c[3], al, 3)
        ui:rect(x + pw * 0.5 - 1.5, py - 2, 3, 19, c[1], c[2], c[3], al * 0.85, 1)
    end
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
    -- 段階チュートリアルの計測。歩き続けたら「歩き方は覚えた」
    if loadNum("moving", 0) > 0.5 then
        self.walkT = self.walkT + dt
        if self.walkT > 1.2 then learn("move") end
    end
    self.noAct = self.noAct + dt

    if loadNum("moving", 0) > 0.5 then
        self.moveX, self.moveZ = loadNum("moveX", 0), loadNum("moveZ", 1)
    end

    -- ================================ クリア / 失敗 ================================
    -- ★文字は出さない。クリアは白へ抜けて次の面、失敗は白へ還ってやり直し(GDD 条5)。
    if self.mode == "clear" or self.mode == "fail" then
        if not self.endSfx then
            self.endSfx = true
            sfx(self.mode == "clear" and "clear" or "fail")
        end
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
            self.mode = "fail"; self.flash = 0; self.endSfx = false
            log("JUNCTION FAIL: timeout")
            return
        end
    end

    -- ================================ 出口 ================================
    if self.goal and self.goal:isValid() then
        local g = self.goal.transform.position
        if (p.x - g.x) ^ 2 + (p.z - g.z) ^ 2 < 2.0 ^ 2 then
            self.mode = "clear"; self.flash = 0; self.endSfx = false
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

    -- ドアが射程に入った瞬間だけ鳴らす(入りっぱなしで鳴り続けない)
    do
        local inReach = (self.mode == "play") and near and nearD < REACH and near or nil
        if inReach and self.touchNear ~= inReach then sfx("touch") end
        self.touchNear = inReach
    end

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
        -- ★候補は【基準スケールから毎フレーム作り直す】。
        --   以前は狙いが変わるたびに現在値へ 1.18 を掛けたり割ったりしていて、
        --   丸め誤差が溜まって少しずつ痩せていった。
        --   ・開いた瞬間は左から順にポンと現れる(自分が開けた、という因果)
        --   ・狙っている 1 枚だけ大きく、ゆっくり脈打つ
        --     (白い虚無の中では色の明るさだけでは見分けが付かない)
        self.pxT = (self.pxT or 0) + dt
        for i = 1, #self.cand do
            local e = ent("Proxy_" .. i)
            local bs = self.pxS and self.pxS[i]
            if e and bs then
                local pop = math.max(0, math.min(1, (self.pxT - (i - 1) * 0.055) / 0.20))
                pop = 1 - (1 - pop) * (1 - pop)
                local k = pop * ((i == best)
                          and (1.18 + 0.05 * math.sin(t * 5.0)) or 1.0)
                e.transform.scale = Vec3.new(bs[1] * k, bs[2] * k, 0.07)
            end
            tint("Proxy_" .. i, vivid(DOOR_COLOR[self.cand[i]] or { 1, 1, 1 }),
                 (i == best) and 1.15 or 0.55)
        end
        self.aim = best

        if keyPressed("Q") then learn("cancel"); closeConnect(self) end
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

        -- ================================ 羅針 ================================
        -- ★合流点のドアへ 7m 以内で近づいたら、床に扇と針を出す。
        --   判定(通過先)と表示(明るいスライス)は sliceIndex に一本化してあるので、
        --   ここを触る時も必ず sliceIndex を通すこと(ズレたら嘘の照準になる)。
        local shown = nil
        if near and nearD < COMPASS_DIST then
            local exits = exitsOf(self, near)
            if #exits >= 1 then
                local d = self.doors[near]
                local th = signedAngle(d.outX, d.outZ, self.moveX, self.moveZ)
                hotExit = sliceIndex(th, #exits)
                shown = near
                showFan(self, near, hotExit)
                needle(self, near)
                -- ★決定打。目の前のドアの中の白が、今の入り方で出る先の色になる
                if self.tinted and self.tinted ~= near then clearVoidTint(self) end
                tintVoid(self, near, vivid(DOOR_COLOR[exits[hotExit]] or { 1, 1, 1 }))
                self.tinted = near
            end
        end
        if self.shownDoor and self.shownDoor ~= shown then hideFan(self, self.shownDoor) end
        self.shownDoor = shown
        if not shown then
            needle(self, nil)
            clearVoidTint(self)
        end

        -- ★スライスの境界をまたいだフレームだけ「カチッ」と鳴らす(ダイヤルの手応え)。
        --   これが無いと境界がどこか分からない。毎フレーム鳴らさないこと。
        if shown then
            if self.lastHotDoor == shown and self.lastHot and self.lastHot ~= hotExit then
                sfx("detent")
            end
            self.lastHot, self.lastHotDoor = hotExit, shown
        else
            self.lastHot, self.lastHotDoor = nil, nil
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
            self.mode = "fail"; self.flash = 0; self.endSfx = false
            log("JUNCTION FAIL: isolated")
            return
        end
    end

    -- ================================ HUD ================================
    -- ---- 結線ビュー(TAB 押しっぱなし) ----
    do
        local on = input:isKeyDown(KEY_TAB or 9)
        if on then self.mapKeyT = 0; self.noAct = 0 end
        if (self.mapKeyT or 0) > 0 then self.mapKeyT = self.mapKeyT - dt end
        if (self.pinDeny or 0) > 0 then self.pinDeny = self.pinDeny - dt end
        drawGraph(self, W, H, uiAnim(self, "map", on, dt, 14), t)
    end

    -- 照準点。白い虚無の上でも見えるように、暗い縁を敷いてから白い点を打つ。
    -- ★触れるドアが射程に入ると、点のまわりに輪が開く。これが「E が押せる」の
    --   常設の合図で、文字の [E] は覚えるまでの補助輪でしかない。
    do
        local reach = (self.mode ~= "connect") and near and nearD < REACH
        local r = uiAnim(self, "ring", reach or self.mode == "connect", dt, 12)
        if r > 0.02 then
            local rad, a = 5 + 9 * r, 0.6 * r
            ui:rect(W * 0.5 - rad - 6, H * 0.5 - 1, 6, 2, 1, 1, 1, a, 1)
            ui:rect(W * 0.5 + rad,     H * 0.5 - 1, 6, 2, 1, 1, 1, a, 1)
            ui:rect(W * 0.5 - 1, H * 0.5 - rad - 6, 2, 6, 1, 1, 1, a, 1)
            ui:rect(W * 0.5 - 1, H * 0.5 + rad,     2, 6, 1, 1, 1, a, 1)
        end
    end
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

    -- ★接続の残り(予算)は右上の錠剤をやめ、結線ビューの下のピン置き場へ移した。
    --   隅の無地の図形は「何なのか」が最後まで伝わらなかった(REDESIGN の診断 2)。

    -- ================================ 段階チュートリアル ================================
    -- ★出すのは【まだ覚えていない操作 1 つだけ】。規定回数やったら二度と出さない。
    --   ただし 20 秒何もしていない人には、覚えた事でも 1 回だけ出し直す(詰まり救済)。
    --   [H] を押している間はいつでも全部見られるので、忘れても困らない。
    local help = keyDown("H")
    local stuck = self.noAct > 20
    local canTouch = near and nearD < REACH
    local nearExits = canTouch and #exitsOf(self, near) or 0
    local canJoin = canTouch and (nearExits == 0
                    or (self.budget > 0 and nearExits < MAX_JUNCTION - 1))

    if self.mode == "connect" then
        -- ② 候補を狙って決める
        local a = uiAnim(self, "pick", self.aim ~= nil
                         and (help or stuck or not learned("pick")), dt, 11)
        if a > 0 and self.aim then
            local e = ent("Proxy_" .. self.aim)
            if e then
                local q = e.transform.position
                worldKey(W, H, q.x, q.y + 1.15, q.z, "E", a)
            end
        end
        -- ③ やめる
        keyCap(W * 0.5, H - 96, "Q", 22,
               uiAnim(self, "cancel", help or stuck or not learned("cancel"), dt, 8))
    else
        self.ui.pick, self.ui.cancel = 0, 0
        -- ① ドアに触れる
        local a = uiAnim(self, "touch", canJoin
                         and (help or stuck or not learned("touch")), dt, 11)
        if a > 0 and near then
            local d = self.doors[near]
            worldKey(W, H, d.x + d.inX * 0.25, 3.05, d.z + d.inZ * 0.25, "E", a)
        end
    end

    -- ⓪ 歩く。歩き出したら消えて、二度と出ない
    keyCap(W * 0.5, H - 62, "W A S D", 22,
           uiAnim(self, "move", help or not learned("move"), dt, 6))

    -- ★TAB(結線ビュー)。初めて接続が成立した瞬間に 1 回だけ出す。
    --   「今どこが繋がったのか」を一番見たい瞬間に渡すのが狙い。
    keyCap(W * 0.5, H - 130, "TAB", 22,
           uiAnim(self, "mapkey", help or (self.mapKeyT or 0) > 0, dt, 8))

    -- ---- 通過フェード(白) ----
    if self.fade > 0 then
        ui:rect(0, 0, W, H, 1, 1, 1, self.fade / FADE_TIME)
    end
end
