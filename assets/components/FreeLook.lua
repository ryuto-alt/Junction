-- JUNCTION の一人称プレイヤー。MainCamera(CharacterController + Camera)に付ける。
-- WASD 移動 / マウス視点 / ESC でマウス解放(エディタの Stop を押したい時)。
--
-- ★このゲームの入力は【移動方向そのものが解答】。ドアへ入った角度で行き先が変わるので、
--   Junction.lua が読む「最後に押していた WASD のワールド方向」をここが唯一の出所として
--   saveNum へ書き出す。カメラの向きではなく WASD の向きを使うのが肝で、これなら
--   壁ズリで速度が曲がっても「自分が歩こうとした向き」が保たれる。
-- ★カメラの transform.rotation.x は「正 = 下を向く」(ApplicationScene.cpp: pitchL = -rotation.x)。
--   内部 pitch(正 = 上)を書き込む時に必ず符号を反転する。
-- ★テレポート後の向きは Junction.lua が saveNum("tpSeq"/"tpYaw") で渡す。
--   ここで yaw を書き換えないと、出口から出た瞬間に元の向きへ引き戻される。
local SPEED = 3.4    -- m/s
local FAST  = 1.75   -- Shift 中の倍率
local SENS  = 0.09   -- マウス感度(度/カウント)
local TURNK = 110    -- 矢印キーで回す速さ(度/秒)。マウス解放中用
local SHIFT = KEY_SHIFT or 0x10

local BOB_AMP  = 0.42
local BOB_ROLL = 0.36
local BOB_FREQ = 1.75
local BOB_BLEND = 8.0

function OnStart(self)
    self.yaw = self.transform.rotation.y
    self.pitch = -self.transform.rotation.x
    self.bobPhase = 0
    self.bobW = 0
    self.tpSeen = 0
    input:setMouseCapture(true)
end

function OnUpdate(self, dt)
    local e = scene:findEntity(self.name)
    if not (e and e:isValid()) then return end

    -- ★カメラ演出中は入力を殺す。位置も向きも Junction.lua が押し込んでいるので、
    --   ここで physics:move や rotation を書くと演出が痙攣する。
    if loadNum("cineLock", 0) > 0.5 then
        physics:move(e, 0, 0)
        saveNum("moving", 0)
        return
    end

    -- ---- テレポート後の向きの受け取り(Junction.lua が唯一の書き手) ----
    local seq = loadNum("tpSeq", 0)
    if seq ~= self.tpSeen then
        self.tpSeen = seq
        self.yaw = loadNum("tpYaw", self.yaw)
        -- ★出口から出た瞬間は目線を水平へ戻す。上を向いたまま通過すると
        --   出た先が天井で、どこに出たのか一瞬わからなくなる(酔いの元)
        self.pitch = loadNum("tpPitch", 0)
        self.bobW = 0
    end

    if keyPressed("ESC") then input:setMouseCapture(not input:isMouseCaptured()) end

    if input:isMouseCaptured() then
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
    if len > 0 then
        local sp = SPEED * (run and FAST or 1) / len
        physics:move(e, mx * sp, mz * sp)
        -- ★入った角度の一次情報源。0 のフレームは書かない(直前の向きを Junction が保つ)
        saveNum("moveX", mx / len)
        saveNum("moveZ", mz / len)
        saveNum("moving", 1)
    else
        physics:move(e, 0, 0)
        saveNum("moving", 0)
    end
    saveNum("camYaw", self.yaw)
    saveNum("camPitch", self.pitch)

    -- ---- ヘッドボブ(回転だけ。position は CC が毎フレーム書き戻すので効かない) ----
    local blend = 1 - math.exp(-BOB_BLEND * dt)
    self.bobW = self.bobW + ((len > 0 and 1 or 0) - self.bobW) * blend
    if self.bobW > 0.001 then
        local frq = BOB_FREQ * (run and 1.3 or 1)
        self.bobPhase = (self.bobPhase + dt * frq * 2 * math.pi) % (4 * math.pi)
    end
    local w = self.bobW
    local bobPitch = math.sin(self.bobPhase) * BOB_AMP * w
    local bobRoll  = math.sin(self.bobPhase * 0.5) * BOB_ROLL * w

    self.transform.rotation = Vec3.new(-(self.pitch + bobPitch), self.yaw, bobRoll)
end
