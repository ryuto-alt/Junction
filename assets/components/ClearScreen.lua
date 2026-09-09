-- JUNCTION クリア画面。本編(stagedemo3)を抜けたあとに読む scenes/clear_demo.json 用。
--
-- タイトルの導入と対になる作り: あちらは「これから行く 4 つの場所」を見せてから
-- ピントを合わせて出発した。こちらは同じ 4 枚を、もう誰も居ない明るさで、
-- 一度だけ静かに返してから黒へ落とす。
--
-- ★描画順: retained UI(UICanvas)が先、即時 ui:* があと = 即時が手前。
--   写真は retained(UIImage)のアルファ、縁の減光と作品名は即時で上に重ねる。
-- ★フェードさせる UI は色のアルファだけでは枠/縁取りが残るので、
--   使い終わったら scene:setUiVisible(e, false) で要素ごと消すこと。

local N_SHOT = 4

local LEAD_LEN      = 1.20   -- 何も無い黒
local SHOT_FADE_IN  = 0.80
local SHOT_HOLD     = 0.70
local SHOT_FADE_OUT = 0.60
local SHOT_GAP      = 0.30
local SHOT_LEN      = SHOT_FADE_IN + SHOT_HOLD + SHOT_FADE_OUT + SHOT_GAP
local SHOT_MAX      = 0.55   -- 行きより暗く返す(もう歩く場所ではない、という濃さ)

local NAME_IN    = 1.60      -- 作品名が浮き上がるまで
local AUTO_BACK  = 11.0      -- 誰も触らなければタイトルへ戻るまでの時間(名前が出てから)
local BACK_SCENE = "scenes/title_demo.json"
local BACK_FADE  = 1.40

local function clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end

local function shotAlpha(t)
    if t < SHOT_FADE_IN then return t / SHOT_FADE_IN end
    if t < SHOT_FADE_IN + SHOT_HOLD then return 1 end
    local o = t - SHOT_FADE_IN - SHOT_HOLD
    if o < SHOT_FADE_OUT then return 1 - o / SHOT_FADE_OUT end
    return 0
end

local function grab(name)
    local e = scene:findEntity(name)
    if e and e:isValid() then return e end
    logWarn("ClearScreen: エンティティが見つかりません: " .. name)
    return nil
end

-- 画面の縁を落とす(post の vignette は UI に掛からないので自前で敷く)
local function edgeShade()
    local steps = 10
    local mw, mh = SCREEN_W * 0.14, SCREEN_H * 0.17
    for i = 1, steps do
        local bw = mw * (i / steps)
        local bh = mh * (i / steps)
        ui:rect(0, 0, SCREEN_W, bh, 0, 0, 0, 0.028, 0)
        ui:rect(0, SCREEN_H - bh, SCREEN_W, bh, 0, 0, 0, 0.028, 0)
        ui:rect(0, 0, bw, SCREEN_H, 0, 0, 0, 0.028, 0)
        ui:rect(SCREEN_W - bw, 0, bw, SCREEN_H, 0, 0, 0, 0.028, 0)
    end
end

local function enterShot(self, i)
    self.shot = i
    self.st = 0
    local e = self.shots[i]
    if not e then return end
    scene:setUiVisible(e, true)
    scene:setUiColor(e, 1, 1, 1, 0)
    -- 行きと同じ、ごく僅かな寄りだけ
    scene:tweenUi(e, { scale = 1.025, duration = SHOT_LEN, easing = "linear" })
    pcall(function() audio:playSFXId("audio/lm/tick.wav", false, 0.12) end)
end

local function leaveShot(self)
    local e = self.shots[self.shot]
    if e then scene:setUiVisible(e, false) end
end

local function goBack(self)
    if self.leaving then return end
    self.leaving = true
    fadeToScene(BACK_SCENE, BACK_FADE)
end

function OnStart(self)
    self.time    = 0
    self.pt      = 0
    self.st      = 0
    self.phase   = 0          -- 0=黒 1=4 枚を返す 2=作品名 3=退場待ち
    self.shot    = 0
    self.leaving = false
    self.dip     = 0
    input:setMouseCapture(false)

    self.black = grab("Clear_Black")
    self.shots = {}
    for i = 1, N_SHOT do self.shots[i] = grab("Clear_Shot_" .. i) end

    for i = 1, N_SHOT do
        if self.shots[i] then scene:setUiVisible(self.shots[i], false) end
    end
    if self.black then
        scene:setUiVisible(self.black, true)
        scene:setUiColor(self.black, 0.005, 0.006, 0.006, 1)
    end

    -- ★brightness は【加算】で中立 0.0。exposure/contrast/saturation は【乗算】で中立 1.0。
    post.setMany{
        dofOn = false,
        exposureOn = true, exposure = 1.0,
        brightnessOn = false,
        contrastOn = true, contrast = 1.02,
        saturationOn = true, saturation = 0.78,
        vignetteOn = false,
        grainOn = true, grain = 0.08, grainSize = 1.5,
    }
    pcall(function() audio:playSFXId("audio/amb/hum.wav", true, 0.14) end)
end

function OnUpdate(self, dt)
    self.time = self.time + dt
    self.pt   = self.pt + dt

    if keyPressed("ESC") then quit() return end
    local confirm = keyPressed("ENTER") or keyPressed("SPACE")
                    or padPressed("A") or padPressed("START")

    if self.phase == 0 then
        if self.pt >= LEAD_LEN then
            self.phase, self.pt = 1, 0
            enterShot(self, 1)
        end

    elseif self.phase == 1 then
        self.st = self.st + dt
        local e = self.shots[self.shot]
        if e then scene:setUiColor(e, 1, 1, 1, shotAlpha(self.st) * SHOT_MAX) end
        if self.st >= SHOT_LEN then
            leaveShot(self)
            if self.shot >= N_SHOT then
                self.phase, self.pt = 2, 0
            else
                enterShot(self, self.shot + 1)
            end
        end
        if confirm then                 -- 振り返りは飛ばせる
            leaveShot(self)
            for i = 1, N_SHOT do
                if self.shots[i] then scene:setUiVisible(self.shots[i], false) end
            end
            self.phase, self.pt = 2, 0
        end

    elseif self.phase == 2 then
        if self.pt >= NAME_IN then self.phase, self.pt = 3, 0 end

    elseif self.phase == 3 then
        if confirm or self.pt >= AUTO_BACK then goBack(self) end
    end

    edgeShade()

    -- 蛍光灯のちらつき。タイトルと同じ濃さで、部屋がまだ生きていることだけ伝える。
    if math.random() < 0.02 then self.dip = 0.06 end
    self.dip = math.max(0, self.dip - dt * 0.9)
    local flick = 0.012 + math.abs(math.sin(self.time * 1.7)) * 0.008 + self.dip
    ui:rect(0, 0, SCREEN_W, SCREEN_H, 0, 0, 0, flick, 0)

    -- 作品名と、その下の細い線 1 本。文字はこれ以上増やさない。
    if self.phase >= 2 then
        local a = (self.phase == 2) and clamp(self.pt / NAME_IN, 0, 1) or 1
        local cx, cy = SCREEN_W * 0.5, SCREEN_H * 0.5
        local txt, size = "JUNCTION", 30
        local x = cx - #txt * size * 0.29
        ui:text(x + 1, cy - size * 0.5 + 1, txt, size, 0.02, 0.02, 0.02, a * 0.55)
        ui:text(x, cy - size * 0.5, txt, size, 0.88, 0.90, 0.86, a * 0.46)
        local lw = SCREEN_W * 0.10 * a
        ui:rect(cx - lw, cy + size * 1.15, lw * 2, 1.4, 0.86, 0.89, 0.85, a * 0.30, 0)
    end
end
