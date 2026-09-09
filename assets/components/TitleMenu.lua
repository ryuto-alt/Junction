-- JUNCTION タイトル。無人で流れる導入:
--   黒 → エリア写真 4 枚 → 1 枚目がぼけた状態で戻る → ピントが合う
--   → 写真が溶けて奥の実際の部屋が現れる → ロード画面へ
--
-- ★描画順のメモ: retained UI(UICanvas ツリー)を先に描き、即時 ui:* をそのあとに描く。
--   つまり即時 ui:* のほうが手前。写真は retained(UIImage)側へ置いて
--   scene:setUiColor のアルファで濃淡を作り、縁の減光と作品名は即時 ui:* で上に重ねる。
--
-- ★ポストプロセス(post.*)は 3D にしか掛からない。UI は post のあとに描かれるので
--   写真のピンぼけを post の DoF で作ることはできない。そこで写真のほうは
--   「同じ絵を 13 枚わずかにずらして重ね、その散らばりを縮める」= ボケ円の離散近似で作り、
--   奥の 3D 部屋のほうは本物の DoF(dofFocusDist)で合わせる。両方が同時に合焦する。
--
-- ★フェードする UI は色のアルファだけでは枠/縁取りが残る。写真の UIImage には
--   outlineWidth を持たせず(シーン JSON で未指定=0)、用が済んだら
--   scene:setUiVisible(e, false) で要素ごと消す。

local N_SHOT  = 4
local N_GHOST = 13          -- 中心 1 + 内リング 6 + 外リング 6
local R_IN    = 13.0        -- 内リング半径(キャンバスpx)。シーン JSON の生成値と一致させること
local R_OUT   = 29.0        -- 外リング半径

-- ---------------------------------------------------------------- 時間割(秒)
local LEAD_LEN      = 0.80  -- 何も無い黒
local SHOT_FADE_IN  = 0.85
local SHOT_HOLD     = 1.10
local SHOT_FADE_OUT = 0.75
local SHOT_GAP      = 0.30  -- 次の 1 枚までの黒
local SHOT_LEN      = SHOT_FADE_IN + SHOT_HOLD + SHOT_FADE_OUT + SHOT_GAP
local FOCUS_LEN     = 3.60  -- ぼけ → ピント
local FOCUS_IN      = 0.70  -- ぼけた絵が黒から浮き上がるまで
local HOLD_LEN      = 1.20  -- ピントが合ったまま止める
local MERGE_LEN     = 1.30  -- 写真が消えて奥の部屋が出る
local EXIT_LEN      = 1.00  -- ロード画面へのフェード

-- 奥の 3D 部屋の合焦距離(m)。0.35 だと部屋が丸ごとぼけ、8.0 で奥の壁まで合う。
local DOF_NEAR = 0.35
local DOF_MID  = 2.20
local DOF_FAR  = 8.00

local function clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end

-- 1 枚の写真の濃さ。イージングは掛けない(無機質に、機械が切り替えている速さで)
local function shotAlpha(t)
    if t < SHOT_FADE_IN then return t / SHOT_FADE_IN end
    if t < SHOT_FADE_IN + SHOT_HOLD then return 1 end
    local o = t - SHOT_FADE_IN - SHOT_HOLD
    if o < SHOT_FADE_OUT then return 1 - o / SHOT_FADE_OUT end
    return 0
end

-- i 枚目のずらし量。シーン JSON を作った生成スクリプトと同じ式で並べてある。
local function ghostOffset(i)
    if i <= 1 then return 0, 0 end
    if i <= 7 then
        local a = ((i - 2) / 6) * math.pi * 2
        return math.cos(a) * R_IN, math.sin(a) * R_IN
    end
    local a = ((i - 8) / 6) * math.pi * 2 + math.pi / 6
    return math.cos(a) * R_OUT, math.sin(a) * R_OUT
end

local function grab(name)
    local e = scene:findEntity(name)
    if e and e:isValid() then return e end
    logWarn("TitleMenu: エンティティが見つかりません: " .. name)
    return nil
end

local function sfx(path, volume)
    pcall(function() audio:playSFXId(path, false, volume) end)
end

-- ---------------------------------------------------------------- 局面の入口
local function enterShot(self, i)
    self.shot = i
    self.st = 0
    local e = self.shots[i]
    if not e then return end
    scene:setUiVisible(e, true)
    scene:setUiColor(e, 1, 1, 1, 0)
    -- ごく僅かな寄り。easing は linear = 等速でしか動かさない。
    scene:tweenUi(e, { scale = 1.035, duration = SHOT_LEN, easing = "linear" })
    sfx("audio/lm/tick.wav", 0.14)
end

local function leaveShot(self)
    local e = self.shots[self.shot]
    if e then scene:setUiVisible(e, false) end
end

local function enterFocus(self)
    -- 13 枚を出し、下から 1, 1/2, 1/3 … の順で重ねる。
    -- こう積むと全タップが等しい重み(1/13)の平均になる = ボケ円のムラが出ない。
    for i = 1, N_GHOST do
        local e = self.ghosts[i]
        if e then
            scene:setUiVisible(e, true)
            scene:setUiColor(e, 1, 1, 1, 1 / i)
            if i > 1 then
                local ox, oy = ghostOffset(i)
                -- 散らばりを中心へ畳む = ボケ円が縮む = ピントが合っていく
                scene:tweenUi(e, { dx = -ox, dy = -oy, duration = FOCUS_LEN, easing = "inOut" })
            end
        end
    end
    -- 本編はここから先に読み始める(ロード画面が出る頃には大半が乗っている)
    if not self.preloaded then
        self.preloaded = true
        preloadScene("scenes/stagedemo3.json")
    end
    sfx("audio/lm/drone.wav", 0.16)
end

local function enterMerge(self)
    -- 重ねを 1 枚に落とす。全タップが中心へ寄り切っているので絵は変わらない
    -- (途中で飛ばされた場合はここで一気に合焦する)。
    for i = 2, N_GHOST do
        local e = self.ghosts[i]
        if e then scene:setUiVisible(e, false) end
    end
    local g1 = self.ghosts[1]
    if g1 then
        scene:setUiVisible(g1, true)
        scene:setUiColor(g1, 1, 1, 1, 1)
    end
    for i = 1, N_SHOT do
        if self.shots[i] then scene:setUiVisible(self.shots[i], false) end
    end
end

local function setPhase(self, p)
    self.phase = p
    self.pt = 0
    if p == 1 then
        enterShot(self, 1)
    elseif p == 2 then
        enterFocus(self)
    elseif p == 3 then
        sfx("audio/lm/lock.wav", 0.18)
    elseif p == 4 then
        enterMerge(self)
    elseif p == 5 then
        if not self.leaving then
            self.leaving = true
            if self.black then scene:setUiVisible(self.black, false) end
            if self.ghosts[1] then scene:setUiVisible(self.ghosts[1], false) end
            fadeToScene("scenes/loading_demo.json", EXIT_LEN)
        end
    end
end

-- 飛ばす: 写真の途中なら合焦へ、合焦中なら出発へ。一度に二段以上は飛ばさない。
local function skipAhead(self)
    if self.phase <= 1 then
        if self.shot > 0 then leaveShot(self) end
        setPhase(self, 2)
    elseif self.phase < 4 then
        setPhase(self, 4)
    end
end

-- 画面の縁を落とす(post の vignette は UI に掛からないので、ここで自前で敷く)。
-- 幅の違う帯を入れ子に重ねると、縁ほど枚数が乗って自然な減光になる。
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

-- ---------------------------------------------------------------- 本体
function OnStart(self)
    self.time      = 0
    self.phase     = 0        -- 0=黒 1=写真 2=ピント 3=静止 4=部屋が出る 5=退場
    self.pt        = 0
    self.st        = 0
    self.shot      = 0
    self.leaving   = false
    self.preloaded = false
    self.dip       = 0        -- 蛍光灯のちらつき用
    input:setMouseCapture(false)

    self.black  = grab("Title_Black")
    self.shots  = {}
    for i = 1, N_SHOT do self.shots[i] = grab("Title_Shot_" .. i) end
    self.ghosts = {}
    for i = 1, N_GHOST do self.ghosts[i] = grab(string.format("Title_Focus_%02d", i)) end

    -- 写真はいったん全部消す。★アルファ 0 だけでは枠が残るので要素ごと消すこと。
    for i = 1, N_SHOT do
        if self.shots[i] then scene:setUiVisible(self.shots[i], false) end
    end
    for i = 1, N_GHOST do
        if self.ghosts[i] then scene:setUiVisible(self.ghosts[i], false) end
    end
    if self.black then
        scene:setUiVisible(self.black, true)
        scene:setUiColor(self.black, 0.006, 0.008, 0.007, 1)
    end

    -- 奥の 3D 部屋は最初から丸ごとぼかしておく。写真が溶けたあとに合焦して現れる。
    -- ★brightness は【加算】で中立 0.0。ここに 1.0 を入れると画面が真っ白に飛ぶ。
    post.setMany{
        dofOn = true, dofFocusDist = DOF_NEAR, dofAperture = 1.4,
        dofBlurSize = 30.0, dofFocalLength = 0.0,
        vignetteOn = true, vignette = 0.45,
        vignetteRadius = 0.66, vignetteSoftness = 0.50,
        saturationOn = true, saturation = 0.86,
        contrastOn = true, contrast = 1.03,
        brightnessOn = true, brightness = -0.02,
        grainOn = true, grain = 0.09, grainSize = 1.5,
    }

    -- 部屋の真ん中の灯りだけがちらつく(手前と奥は点けたまま = 部屋が読める)
    local flickerLight = scene:findEntity("TitleLight_2")
    if flickerLight and flickerLight:isValid() and flickerLight:light() then
        Flicker(flickerLight:light(), "fluorescent")
    end
    pcall(function() audio:playSFXId("audio/amb/hum.wav", true, 0.20) end)
end

function OnUpdate(self, dt)
    self.time = self.time + dt
    self.pt   = self.pt + dt

    if keyPressed("ESC") then quit() return end
    if keyPressed("ENTER") or keyPressed("SPACE") or padPressed("A") or padPressed("START") then
        skipAhead(self)
    end

    if self.phase == 0 then
        if self.pt >= LEAD_LEN then setPhase(self, 1) end

    elseif self.phase == 1 then
        self.st = self.st + dt
        local e = self.shots[self.shot]
        if e then scene:setUiColor(e, 1, 1, 1, shotAlpha(self.st)) end
        if self.st >= SHOT_LEN then
            leaveShot(self)
            if self.shot >= N_SHOT then setPhase(self, 2)
            else enterShot(self, self.shot + 1) end
        end

    elseif self.phase == 2 then
        local k = clamp(self.pt / FOCUS_LEN, 0, 1)
        post.set("dofFocusDist", DOF_NEAR + (DOF_MID - DOF_NEAR) * k)
        if self.pt >= FOCUS_LEN then setPhase(self, 3) end

    elseif self.phase == 3 then
        if self.pt >= HOLD_LEN then setPhase(self, 4) end

    elseif self.phase == 4 then
        local m = clamp(self.pt / MERGE_LEN, 0, 1)
        -- 写真が薄れる → その下の黒はもっと早く抜く(途中で暗く沈み込まないように)
        if self.ghosts[1] then scene:setUiColor(self.ghosts[1], 1, 1, 1, 1 - m) end
        if self.black then
            scene:setUiColor(self.black, 0.006, 0.008, 0.007, clamp(1 - m * 2.2, 0, 1))
        end
        post.set("dofFocusDist", DOF_MID + (DOF_FAR - DOF_MID) * m)
        if self.pt >= MERGE_LEN then setPhase(self, 5) end
    end

    -- ---------------------------------------------------------- 上に重ねるもの
    -- ぼけた絵は黒から浮き上がらせる(写真の重ねは不透明なので即時 ui:rect で覆う)
    if self.phase == 2 and self.pt < FOCUS_IN then
        ui:rect(0, 0, SCREEN_W, SCREEN_H, 0.006, 0.008, 0.007, 1 - self.pt / FOCUS_IN, 0)
    end

    edgeShade()

    -- 蛍光灯のちらつき。ほとんど気づかない濃さで、ときどき 1 フレームだけ落とす。
    if math.random() < 0.02 then self.dip = 0.06 end
    self.dip = math.max(0, self.dip - dt * 0.9)
    local flick = 0.012 + math.abs(math.sin(self.time * 1.7)) * 0.008 + self.dip
    ui:rect(0, 0, SCREEN_W, SCREEN_H, 0, 0, 0, flick, 0)

    -- 作品名。この作品は文字を出さない方針なので、これ 1 つだけ・小さく・薄く。
    local nameA = 0
    if self.phase == 3 then
        nameA = clamp(self.pt / 0.45, 0, 1)
    elseif self.phase == 4 then
        nameA = clamp(1 - self.pt / 0.50, 0, 1)
    end
    if nameA > 0 then
        local txt, size = "JUNCTION", 22
        local x = SCREEN_W * 0.5 - #txt * size * 0.29
        local y = SCREEN_H * 0.885
        ui:text(x + 1, y + 1, txt, size, 0.02, 0.02, 0.02, nameA * 0.50)
        ui:text(x, y, txt, size, 0.88, 0.90, 0.86, nameA * 0.42)
    end
end
