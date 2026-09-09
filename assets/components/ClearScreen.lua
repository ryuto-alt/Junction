-- JUNCTION クリア画面。本編(stagedemo3)が白へ抜けきった【その白を受け取って】始まる。
-- scenes/clear_demo.json 用。
--
-- ★見せる物 ―― 文字は 1 文字も出さない(題名の画だけは、タイトルで使った物なので使う):
--
--   [0] 真っ白        本編の白飛びから継ぎ目なく渡ってくる。ここで切れて見えたら負け
--   [1] 白が引く      白の中から【タイトルで最初に見たあの部屋】が現れる。
--                     ★カメラはタイトルと寸分同じ位置・同じ画角。
--                       違うのは「灯りが 3 本とも点いている」ことと「扉が無い」こと。
--                       タイトルでは閉じていた扉が開いていて、その向こうが白い。
--                       ★戸口の穴は wall_door.gltf の実測で x -1.0〜1.0 / y 0〜2.6。
--                         白い板(ClearDoorGlow)はそれより一回り大きく作って
--                         【壁の裏】(z 6.12)へ回し、穴のふちで壁に切り取らせている。
--                         手前へ置くと縁が浮くし、隙間から空が覗く。
--                       ―― 出口の白い部屋が、最初の部屋の扉の向こうに繋がっている。
--                       始まりと終わりが同じ部屋になる = 円環。
--   [2] ただ見せる    何も起きない時間。ここを削ると「余韻」が「演出」になる
--   [3] 灯りが落ちる  奥 → 手前 の順に消えて、【真ん中の 1 本だけ】が残る。
--                     ★タイトルで病気みたいに明滅していたのが、この真ん中の灯り。
--                       ここでは明滅しない。建物はもう落ち着いている
--   [4] 題名          上下の半身は【最初から合わさっている】。もう割れない。
--                     合わせ目には、タイトルとまったく同じ金の線が点く
--   [5] 継ぎ目が消える 線がゆっくり落ちて、無くなる。
--                     ★この作品でいちばん言いたいこと ―― 継ぎ目が無くなった。
--                       文字にしないのは、文字にした瞬間に嘘になるから
--   [6] 待つ          画面の下に金の線が 1 本だけ引かれる。押せる、という合図
--   [7] 去る          その線が画面幅まで伸びて、黒へ。タイトルへ戻る
--
-- ★曲(audio/bgm/title.mp3)はタイトル曲をそのまま戻す。円環にするため。
--   ★止める経路は 2 本とも用意してある:
--     ・タイトルへ戻る … TitleMenu.lua が「同じ曲が既に鳴っていれば playBGM を呼ばない」
--       ので、曲は【切れずに】タイトルへ渡る(音量も向こうが 0.55 へ戻す)。
--       その先はロード画面が 0 まで下げ、StageMusic.lua が本編で stopBGM する。
--     ・終了 … quit()。
--   ★本編の曲(stage*.mp3)は OnStart で必ず stopBGM して殺す。放っておくと重なる。
--
-- ★★描画順の罠(何度も踏んだ所):
--   retained UI(UICanvas ツリー)が先、即時 ui:* があと ＝ 即時のほうが【手前】。
--   だから白も黒も【即時 ui:rect】で敷いている。retained の板でやると題名の下に潜る。
--   post.* は 3D にしか掛からないので、白飛びを post だけでやると UI が白の上に残る。
--
-- ★フェードさせる retained UI は色のアルファだけでは枠/縁取りが残る。
--   用が済んだら scene:setUiVisible(e, false) で要素ごと消すこと。

-- ================================================================ 詰める値はここ
-- ★実機で耳と目で合わせるならこの塊だけ触ればいい。他所に散らしていない。

-- ---- 時間割(秒)
local T_WHITE    = 1.10   -- 真っ白のまま持たせる。本編の白から渡ってくる継ぎ目
local T_EMERGE   = 5.40   -- 白が引いて部屋が出るまで。★急ぐと「切り替わった」に見える
local T_LOOK     = 4.20   -- 部屋をただ見せる時間
local FALL_GAP   = 2.40   -- 灯りが 1 本落ちてから次が落ちるまで
local FALL_DUR   = 1.70   -- 1 本が落ちきるまで
local T_LOGO_IN  = 2.40   -- 題名が浮かび上がるまで
local T_SEAM_HOLD= 1.40   -- 合わせ目の線が点いたまま止まる時間
local T_SEAM_OUT = 2.80   -- 線が消えきるまで。★ここが山。速いと何も伝わらない
local T_PROMPT   = 1.10   -- 下の合図の線が引かれるまで
local AUTO_BACK  = 30.0   -- 誰も触らなければタイトルへ戻るまで(合図が出てから)
local LEAVE_LEN  = 1.30   -- 押してから黒くなりきるまで

-- ---- 絵
local BLOW       = 2.60   -- 白飛びの exposure。★exposure は【乗算・中立 1.0】
local EXP_END    = 1.02   -- 落ち着いたときの exposure
local GOLD       = { 1.00, 0.84, 0.52 }   -- 床の印・破片の輪郭と同じ金。他の色は使わない
local SEAM_REF_Y = 236.7  -- 合わせ目の高さ(ref px)。題名の矩形 152 + 178*0.4758
local SEAM_HALF  = 616    -- 合わせ目の線の半幅(ref px)
local PROMPT_Y   = 782    -- 下の合図の線の高さ(ref px)
local PROMPT_HALF= 46     -- その半幅(ref px)
local LOGO_A     = 0.86   -- 題名の濃さ。タイトル(1.0)より一段控える

-- ---- 音
local BACK_SCENE = "scenes/title_demo.json"
local TITLE_BGM  = "audio/bgm/title.mp3"
local BGM_VOL    = 0.50   -- タイトル曲。向こう(0.55)より気持ち下げて置く
local HUM_VOL    = 0.09   -- 部屋の唸り
local SFX_LAMP   = "audio/ui/touch.wav"    -- 灯りが 1 本落ちる。低くて短い
local SFX_NAV    = "audio/ui/nav.wav"      -- 合図の線が引かれた
local SFX_ENTER  = "audio/ui/enter.wav"    -- 決めた。タイトルと同じ決定音
local LAMP_VOL   = 0.13
local NAV_VOL    = 0.20
local ENTER_VOL  = 0.45

-- 落ちる順。奥(扉のそば) → 手前。★真ん中(ClearLight_2)は【残す】ので入れない
local FALL_ORDER = { "ClearLight_3", "ClearLight_1" }

-- 合わせ目の線の点き方。タイトル(TitleMenu.lua の SEAM_STRIKE)と同じ段付き。
-- イージングを掛けない = 蛍光灯が点いているだけの見え方。
local SEAM_STRIKE = {
    { 0.00, 0.00 }, { 0.04, 0.90 }, { 0.08, 0.05 }, { 0.20, 0.60 }, { 0.25, 0.03 },
    { 0.44, 1.00 }, { 0.50, 0.20 }, { 0.60, 0.85 }, { 0.70, 1.00 },
}

-- ================================================================ 下ごしらえ
local REF_W, REF_H = 1600, 900
local function sx(v) return v * SCREEN_W / REF_W end
local function sy(v) return v * SCREEN_H / REF_H end

local function clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end

local function stepped(tbl, t)
    local v = 0
    for i = 1, #tbl do
        if t >= tbl[i][1] then v = tbl[i][2] else break end
    end
    return v
end

local function grab(name)
    local e = scene:findEntity(name)
    if e and e:isValid() then return e end
    logWarn("ClearScreen: エンティティが見つかりません: " .. name)
    return nil
end

local function sfx(path, volume)
    pcall(function() audio:playSFXId(path, false, volume) end)
end

-- 線 1 本。TitleMenu.lua / LoadingScreen.lua とまったく同じ描き方。
-- ぼかしが無いので、にじみ 2 枚を敷いてから芯を 1 枚で代用する。
local function rule(cx, cy, half, thick, r, g, b, a)
    if a <= 0.002 or half <= 0.5 then return end
    ui:rect(cx - half - 10, cy - thick * 3.2, half * 2 + 20, thick * 6.4, r, g, b, a * 0.05, 0)
    ui:rect(cx - half - 4,  cy - thick * 1.7, half * 2 + 8,  thick * 3.4, r, g, b, a * 0.10, 0)
    ui:rect(cx - half,      cy - thick * 0.5, half * 2,      thick,       r, g, b, a * 0.92, 0)
end

-- 画面の縁を落とす(post の vignette は UI に掛からないので自前で敷く)。
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

local function setLogoAlpha(self, a)
    if a <= 0.004 then
        if self.logoT then scene:setUiVisible(self.logoT, false) end
        if self.logoB then scene:setUiVisible(self.logoB, false) end
        return
    end
    for _, e in ipairs({ self.logoT, self.logoB }) do
        if e then
            scene:setUiVisible(e, true)
            scene:setUiColor(e, 0.93, 0.94, 0.90, a)
        end
    end
end

local function lampIntensity(self, name, v)
    local rec = self.lamps[name]
    if rec and rec.l then rec.l.intensity = v end
end

-- 局面を進める。★入場の処理はここに 1 か所だけ置く(飛ばされても必ず通る)
local function setPhase(self, p)
    self.phase = p
    self.pt = 0
    if p == 3 then
        self.fell = 0
    elseif p == 6 then
        self.promptRung = false
    end
end

-- 飛ばす。★一気に終端(6)まで送る。押した人は「もう見た」ので、
--   途中で止めるとかえって焦らしになる。落とす物は全部落とし切ってから渡す。
local function skipToEnd(self)
    for i = 1, #FALL_ORDER do lampIntensity(self, FALL_ORDER[i], 0.0) end
    -- ★白飛びの exposure を戻し忘れると、飛ばした人だけ真っ白のまま終わる
    post.set("exposure", EXP_END)
    self.whiteA = 0
    self.seamA  = 0
    self.logoA  = 1
    setPhase(self, 6)
end

-- ================================================================ 本体
function OnStart(self)
    self.time  = 0
    self.pt    = 0
    self.phase = 0
    self.fell  = 0
    self.whiteA = 1         -- 一番手前に敷く白(本編から受け取った白)
    self.seamA = 0          -- 合わせ目の線の濃さ
    self.logoA = 0          -- 題名の濃さ
    self.promptA = 0        -- 下の合図の線の伸び(0..1)
    self.blackA = 0         -- 去るときの黒
    self.leaving = false
    self.promptRung = false
    input:setMouseCapture(false)

    self.logoT = grab("Clear_Logo_Top")
    self.logoB = grab("Clear_Logo_Bot")
    setLogoAlpha(self, 0)

    -- 灯り。素の明るさを控えてから触る(0 にした後で戻せなくなるのを防ぐ)
    self.lamps = {}
    for _, n in ipairs({ "ClearLight_1", "ClearLight_2", "ClearLight_3" }) do
        local e = scene:findEntity(n)
        if e and e:isValid() and e:light() then
            self.lamps[n] = { l = e:light(), base = e:light().intensity }
        end
    end

    -- ★brightness は【加算】で中立 0.0(1.05 を入れて画面が飛んだ事故がある)。
    --   exposure/contrast/saturation は【乗算】で中立 1.0。白飛びは exposure でやる。
    post.setMany{
        dofOn = false,
        exposureOn = true, exposure = BLOW,
        brightnessOn = true, brightness = -0.02,
        contrastOn = true, contrast = 1.03,
        saturationOn = true, saturation = 0.84,
        vignetteOn = true, vignette = 0.42,
        vignetteRadius = 0.70, vignetteSoftness = 0.52,
        bloomOn = true, bloom = 0.26, bloomThreshold = 0.95,
        grainOn = true, grain = 0.085, grainSize = 1.5,
    }

    -- 音。★本編の曲(stage*.mp3)は必ず殺してから題名曲を置く。重なると台無し
    pcall(function() audio:stopBGM() end)
    pcall(function()
        audio:setBGMVolume(0.0)
        audio:playBGM(TITLE_BGM)
    end)
    pcall(function() audio:playSFXId("audio/amb/hum.wav", true, HUM_VOL) end)
end

function OnUpdate(self, dt)
    self.time = self.time + dt
    self.pt   = self.pt + dt

    local confirm = keyPressed("ENTER") or keyPressed("SPACE")
                    or padPressed("A") or padPressed("START")
    -- ★白が引く前の ESC は効かせない(渡ってきた直後の誤爆で終わらせない)
    if self.phase >= 2 and (keyPressed("ESC") or padPressed("B")) then quit() return end

    -- ---------------------------------------------------------- 局面
    if self.phase == 0 then                       -- 真っ白
        if confirm or self.pt >= T_WHITE then setPhase(self, 1) end

    elseif self.phase == 1 then                   -- 白が引いて部屋が出る
        local k = clamp(self.pt / T_EMERGE, 0, 1)
        -- ★白は【遅く抜き始めて、あとから一気に】。等速だと「暗転の逆」にしか見えない
        self.whiteA = (1 - k) ^ 0.65
        post.set("exposure", EXP_END + (BLOW - EXP_END) * (1 - k) ^ 0.85)
        if confirm then skipToEnd(self)
        elseif self.pt >= T_EMERGE then setPhase(self, 2) end

    elseif self.phase == 2 then                   -- ただ見せる
        if confirm then skipToEnd(self)
        elseif self.pt >= T_LOOK then setPhase(self, 3) end

    elseif self.phase == 3 then                   -- 灯りが落ちる
        -- 落ちるべき本数を時刻から決める(飛ばされても取りこぼさない)
        local want = math.floor(self.pt / FALL_GAP) + 1
        if want > #FALL_ORDER then want = #FALL_ORDER end
        if want > self.fell then
            self.fell = want
            sfx(SFX_LAMP, LAMP_VOL)
        end
        for i = 1, #FALL_ORDER do
            local rec = self.lamps[FALL_ORDER[i]]
            if rec then
                local st = self.pt - (i - 1) * FALL_GAP
                local u = clamp(st / FALL_DUR, 0, 1)
                -- 二乗で落とす = 最後にすっと消える(蛍光灯が切れる向き)
                rec.l.intensity = rec.base * (1 - u) * (1 - u)
            end
        end
        if confirm then skipToEnd(self)
        elseif self.pt >= (#FALL_ORDER - 1) * FALL_GAP + FALL_DUR + 0.9 then
            setPhase(self, 4)
        end

    elseif self.phase == 4 then                   -- 題名が浮かぶ / 合わせ目が点く
        self.logoA = clamp(self.pt / T_LOGO_IN, 0, 1)
        local st = self.pt - T_LOGO_IN * 0.55     -- 題名が半分見えたころに線が点く
        self.seamA = stepped(SEAM_STRIKE, st)
        if st > 0.70 then
            -- 点いたあとの細かい唸り。「安定していない」としか見えない程度
            self.seamA = self.seamA * (0.955 + math.abs(math.sin(self.time * 37.0)) * 0.045)
        end
        if confirm then skipToEnd(self)
        elseif self.pt >= T_LOGO_IN + T_SEAM_HOLD then setPhase(self, 5) end

    elseif self.phase == 5 then                   -- ★継ぎ目が消える
        self.logoA = 1
        local k = clamp(self.pt / T_SEAM_OUT, 0, 1)
        -- 三乗で落とす = 最後まで薄く残ってから、無くなる
        self.seamA = (1 - k) ^ 3
        if confirm then skipToEnd(self)
        elseif self.pt >= T_SEAM_OUT then setPhase(self, 6) end

    elseif self.phase == 6 then                   -- 待つ
        self.logoA = 1
        self.seamA = 0
        self.promptA = clamp(self.pt / T_PROMPT, 0, 1)
        if not self.promptRung and self.promptA >= 1 then
            self.promptRung = true
            sfx(SFX_NAV, NAV_VOL)
        end
        if confirm or self.pt >= T_PROMPT + AUTO_BACK then
            sfx(SFX_ENTER, ENTER_VOL)
            setPhase(self, 7)
        end

    elseif self.phase == 7 then                   -- 去る
        local k = clamp(self.pt / LEAVE_LEN, 0, 1)
        self.blackA = k * k
        self.logoA = (1 - k) * (1 - k)
        if k >= 1 and not self.leaving then
            self.leaving = true
            setLogoAlpha(self, 0)                 -- ★要素ごと消す。縁取りが残らないように
            -- 既に真っ黒なので、遷移側の演出は【極短】でいい。
            -- 白 → 黒 → クリア画面 のような二段の暗転を作らないための短さ。
            fadeToScene(BACK_SCENE, 0.55)
        end
    end

    -- ---------------------------------------------------------- 曲
    -- 白が引くあいだに、ゆっくり戻ってくる。★去るときは触らない ――
    --   TitleMenu.lua が 0.55 へ戻すので、曲は切れずにタイトルへ渡る
    if self.phase >= 1 and self.phase < 7 then
        local up = clamp((self.time - T_WHITE) / (T_EMERGE + T_LOOK * 0.5), 0, 1)
        pcall(function() audio:setBGMVolume(BGM_VOL * up) end)
    end

    -- ---------------------------------------------------------- 絵
    setLogoAlpha(self, self.logoA * LOGO_A)

    edgeShade()

    -- ★タイトルと違い、ここでは【ちらつかせない】。
    --   明滅は「建物がまだ壊れている」ことの合図なので、終わったあとに出してはいけない。
    --   代わりに、ほとんど気づかない濃さのゆっくりした呼吸だけ乗せる。
    local breath = 0.010 + math.abs(math.sin(self.time * 0.55)) * 0.006
    ui:rect(0, 0, SCREEN_W, SCREEN_H, 0, 0, 0, breath, 0)

    -- 合わせ目の線。★題名の上下の【あいだ】に引く。タイトルとまったく同じ位置・同じ太さ
    if self.seamA > 0.002 then
        rule(SCREEN_W * 0.5, sy(SEAM_REF_Y), sx(SEAM_HALF),
             math.max(1.0, sy(3.0)), GOLD[1], GOLD[2], GOLD[3], self.seamA)
    end

    -- 下の合図の線。中心から左右へ引かれて、あとはゆっくり息をする。
    -- ★文字は出さない。この作品で「押せる」を表すのは金の線だけ。
    if self.promptA > 0.002 then
        local half, a, th
        if self.phase == 7 then
            -- 押されたら画面幅まで伸びる。★タイトルで START を押したときと同じ手つき
            local k = clamp(self.pt / LEAVE_LEN, 0, 1)
            half = sx(PROMPT_HALF) + (SCREEN_W * 0.5 - sx(PROMPT_HALF)) * (k * k)
            a    = 1 - k * k * k
            th   = math.max(1.0, sy(3.0)) * (1 - k * 0.55)
        else
            half = sx(PROMPT_HALF) * self.promptA
            a    = self.promptA * (0.62 + math.sin(self.time * 1.5) * 0.16)
            th   = math.max(1.0, sy(3.0))
        end
        rule(SCREEN_W * 0.5, sy(PROMPT_Y), half, th, GOLD[1], GOLD[2], GOLD[3], a)
    end

    -- ---------------------------------------------------------- 一番手前
    -- ★★白も黒も【即時 ui:rect】で、しかも一番最後に描く。
    --   retained UI(題名)より即時のほうが手前なので、これで確実に全部を覆える。
    --   post だけで白飛びさせると UI が白の上に残る ―― この作品で何度も踏んだ罠。
    if self.phase == 0 then
        ui:rect(0, 0, SCREEN_W, SCREEN_H, 1, 1, 1, 1, 0)
    elseif self.phase == 1 and self.whiteA > 0.002 then
        ui:rect(0, 0, SCREEN_W, SCREEN_H, 1, 1, 1, self.whiteA, 0)
    end
    if self.blackA > 0.002 then
        ui:rect(0, 0, SCREEN_W, SCREEN_H, 0.005, 0.006, 0.006, self.blackA, 0)
    end
end
