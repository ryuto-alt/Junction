-- JUNCTION の一人称プレイヤー。★MainCamera(Camera だけ。CharacterController は無い)に付ける。
--
-- ★2026-09-02 v3「大きさ」への作り直し(docs/SCALE.md)。
--   CharacterController の 半径/高さ/段差 は実行時に変えられない
--   (physics:addCharacterController は get-or-create。実測で確認済み)。
--   そこで大きさごとに Body_0..4 をシーンに置いてあり、Junction.lua が
--   使う 1 体だけを地上へ出す。ここはその【今の体】を歩かせ、
--   カメラを「体の位置 + 目の高さ(0.8 x 大きさ)」へ毎フレーム置くだけ。
--
--   ★カメラが体と別実体なので、physics が transform を上書きしない = ここで
--     position を書けばそのまま効く(旧版のように押し合いにならない)。
--
-- ★大きさの手がかりは【同時に全部動かす】(調査: 1 つでも矛盾すると "バグった" に見える):
--     目の高さ / 歩く速さ / 歩幅(ヘッドボブの周期) / 足音のピッチ
--   数字は 1 つも出さない。
--
-- ★カメラの transform.rotation.x は「正 = 下を向く」(pitchL = -rotation.x)。
-- ★テレポート後の向きは Junction.lua が saveNum("tpSeq"/"tpYaw") で渡す。
local SPEED   = 3.4     -- 大きさ 1 の歩く速さ [m/s]
local FAST    = 1.3     -- Shift 中の倍率。★1.6 だと大きさ 1 の走り跳びが溝を越えてしまう(gen_stages.py の JD_K と対)
local SENS    = 0.09
local TURNK   = 110
local SHIFT   = KEY_SHIFT or 0x10
local BODY_H  = 1.8
local SCALES  = { 0.125, 0.25, 0.5, 1.0, 2.0 }   -- Body_0..4(gen_stages.py と一致)
local EYE_H   = 1.7
local EYE_OFF = EYE_H - BODY_H * 0.5    -- 体の中心から目まで(大きさ 1 のとき 0.8)

local BOB_AMP, BOB_ROLL, BOB_FREQ, BOB_BLEND = 0.42, 0.36, 1.75, 8.0

-- ★歩く速さは大きさに比例させたいが、0.125 倍だと 0.43 m/s で遊べない。
--   s^0.6 にすると 0.125 -> 0.29倍(1.0 m/s) / 2 -> 1.52倍(5.2 m/s) で、
--   「小さいと世界が広い」は伝わるのに操作は死なない。
local function speedOf(s)
    return SPEED * (s ^ 0.6)
end

local function body(self)
    local i = math.floor(loadNum("bodyIdx", 2) + 0.5)
    local e = scene:findEntity("Body_" .. i)
    if e and e:isValid() then return e end
    return nil
end

function OnStart(self)
    self.yaw = self.transform.rotation.y
    self.pitch = -self.transform.rotation.x
    self.bobPhase, self.bobW, self.tpSeen = 0, 0, 0
    self.stepT = 0
    input:setMouseCapture(true)
end

function OnUpdate(self, dt)
    local e = scene:findEntity(self.name)
    if not (e and e:isValid()) then return end
    local s = loadNum("pscale", 1.0)
    if s <= 0.001 then s = 1.0 end
    local b = body(self)

    -- ★カメラ演出中は入力も追従も止める。位置も向きも Junction.lua が押し込んでいる。
    if loadNum("cineLock", 0) > 0.5 then
        if b then physics:move(b, 0, 0) end
        saveNum("moving", 0)
        return
    end

    -- ---- テレポート後の向きの受け取り(Junction.lua が唯一の書き手) ----
    local seq = loadNum("tpSeq", 0)
    if seq ~= self.tpSeen then
        self.tpSeen = seq
        self.yaw = loadNum("tpYaw", self.yaw)
        self.pitch = loadNum("tpPitch", 0)
        self.bobW = 0
    end

    if keyPressed("ESC") then input:setMouseCapture(not input:isMouseCaptured()) end
    -- ★検証用: saveNum("dbg_lockYaw",1) でマウスを無視する(MCP から歩かせて測る時に使う)
    if input:isMouseCaptured() and loadNum("dbg_lockYaw", 0) < 0.5 then
        self.yaw = self.yaw + input:getMouseDeltaX() * SENS
        self.pitch = self.pitch - input:getMouseDeltaY() * SENS
    end
    if keyDown("LEFT")  then self.yaw = self.yaw - TURNK * dt end
    if keyDown("RIGHT") then self.yaw = self.yaw + TURNK * dt end
    if keyDown("UP")    then self.pitch = self.pitch + TURNK * dt end
    if keyDown("DOWN")  then self.pitch = self.pitch - TURNK * dt end
    self.yaw = self.yaw % 360
    self.pitch = math.max(-85, math.min(85, self.pitch))

    local f = math.rad(self.yaw)
    local fx, fz = math.sin(f), math.cos(f)
    local mx, mz = 0, 0
    if keyDown("W") then mx, mz = mx + fx, mz + fz end
    if keyDown("S") then mx, mz = mx - fx, mz - fz end
    if keyDown("A") then mx, mz = mx - fz, mz + fx end
    if keyDown("D") then mx, mz = mx + fz, mz - fx end

    local len = math.sqrt(mx * mx + mz * mz)
    local run = input:isKeyDown(SHIFT)
    if b then
        if len > 0 then
            local sp = speedOf(s) * (run and FAST or 1) / len
            physics:move(b, mx * sp, mz * sp)
            saveNum("moveX", mx / len); saveNum("moveZ", mz / len); saveNum("moving", 1)
        else
            physics:move(b, 0, 0)
            saveNum("moving", 0)
        end
    end
    -- ---- ジャンプ。★跳べる高さは体ごとに違う(CharacterController.jumpSpeed に焼いてある) ----
    --   大きさ 1 で 0.9m、2 で 1.46m。柵(1.15m)を越えられるかがそのまま謎解きになる。
    -- ★keyPressed ではなく keyDown。押しっぱなしで連続ジャンプできる方が
--   プラットフォーマーとして素直で、失敗のやり直しが軽い。
    if b and keyDown("SPACE") and physics:isGrounded(b) then
        physics:jump(b)
        saveNum("jumped", 1)
        pcall(function()
            local id = audio:playSFXId("audio/ui/step.wav", false, 0.5)
            if id then audio:setVoicePitch(id, 0.85) end   -- ★大きさで変えない(教えてしまう)
        end)
    end

    saveNum("camYaw", self.yaw)
    saveNum("camPitch", self.pitch)

    -- ---- ヘッドボブ。★周期は大きさに反比例(大きい生き物ほどゆっくり歩く) ----
    local blend = 1 - math.exp(-BOB_BLEND * dt)
    self.bobW = self.bobW + ((len > 0 and 1 or 0) - self.bobW) * blend
    local frq = BOB_FREQ * (run and 1.3 or 1) / (s ^ 0.5)
    if self.bobW > 0.001 then
        self.bobPhase = (self.bobPhase + dt * frq * 2 * math.pi) % (4 * math.pi)
    end
    local w = self.bobW
    local bobPitch = math.sin(self.bobPhase) * BOB_AMP * w
    local bobRoll  = math.sin(self.bobPhase * 0.5) * BOB_ROLL * w

    -- ---- 足音。★ピッチとテンポで大きさを鳴らす(一番安くて一番効く聴覚キュー) ----
    if self.bobW > 0.35 then
        self.stepT = (self.stepT or 0) + dt * frq
        if self.stepT >= 0.5 then
            self.stepT = self.stepT - 0.5
            pcall(function()
                local id = audio:playSFXId("audio/ui/step.wav", false, 0.35)
                if id then audio:setVoicePitch(id, 1.0) end   -- ★大きさで変えない(教えてしまう)
            end)
        end
    else
        self.stepT = 0
    end

    -- ---- カメラを体の上へ ----
    if b then
        local p = b.transform.position
        -- ★目の高さは【体の足元 + 1.7 x 見た目の縮尺】。廊下の中では体(当たり判定)と
        --   見た目の縮尺が違う(体は 5 種しか無い)ので、体の中心からの固定オフセットでは狂う
        local sb = SCALES[math.floor(loadNum("bodyIdx", 3) + 0.5) + 1] or 1.0
        e.transform.position = Vec3.new(p.x, p.y - BODY_H * 0.5 * sb + EYE_H * s, p.z)
    end
    e.transform.rotation = Vec3.new(-(self.pitch + bobPitch), self.yaw, bobRoll)

    -- 通常時は白いドット。Door.lua が照準内の扉を検出した時だけ上から緑に置き換える。
    local rx, ry = SCREEN_W * 0.5, SCREEN_H * 0.5
    ui:rect(rx - 7, ry - 7, 14, 14, 0.0, 0.0, 0.0, 0.90, 7)
    ui:rect(rx - 4, ry - 4, 8, 8, 1.0, 1.0, 1.0, 1.0, 4)
end
