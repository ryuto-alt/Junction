-- JUNCTION タイトル。二段構え:
--
--   [1] 選択画面  黒 → 奥の部屋が浮き上がる → 継ぎ目の線が点く
--                 → 題名の上下の半身が寄って合わさる → START / EXIT が出る
--   [2] START の後の導入  黒 → エリア写真 4 枚 → 1 枚目がぼけて戻る → ピントが合う
--                 → 写真が溶けて奥の実際の部屋が現れる → ロード画面へ
--
-- ★[2] は前から動いているものをそのまま活かしてある。変えたのは
--   「起動と同時に始まる」を「START を押したら始まる」にしたところだけ。
--
-- ★題名の字について:
--   assets/ にフォントが無いので ui:text の素の字では題名にならない。
--   字は SVG から焼いた PNG(assets/ui/logo/)を UIImage で置いている。
--   版下は source/ui_icons/logo_glyphs.js、組みは gen_logo_svg.js、
--   焼きは build_logo.js。JUNCTION = 継ぎ目 なので、題名は 1 本の水平線で
--   上下に断ち割ってあり、【上半分 junction_top.png】と【下半分 junction_bottom.png】の
--   2 枚に分かれている。線そのものは焼いていない ―― この Lua が ui:rect で引く。
--   同じ「1 本の線」がロード画面(蛍光灯が痩せて線になる)と場面転換(カーテンの
--   合わせ目)にも出てくる。作品を通して線は 1 本しかない、という作り。
--
-- ★描画順のメモ: retained UI(UICanvas ツリー)を先に描き、即時 ui:* をそのあとに描く。
--   つまり即時 ui:* のほうが手前。写真・題名・選択肢は retained(UIImage)側へ置いて
--   scene:setUiColor のアルファで濃淡を作り、線と縁の減光は即時 ui:* で上に重ねる。
--
-- ★ポストプロセス(post.*)は 3D にしか掛からない。UI は post のあとに描かれるので
--   写真のピンぼけを post の DoF で作ることはできない。そこで写真のほうは
--   「同じ絵を 13 枚わずかにずらして重ね、その散らばりを縮める」= ボケ円の離散近似で作り、
--   奥の 3D 部屋のほうは本物の DoF(dofFocusDist)で合わせる。両方が同時に合焦する。
--
-- ★フェードする UI は色のアルファだけでは枠/縁取りが残る。写真・題名の UIImage には
--   outlineWidth を持たせず(シーン JSON で 0)、用が済んだら
--   scene:setUiVisible(e, false) で要素ごと消す。
--
-- ★マウスでは押せない。理由:
--   ・即時 ui:button は ImGui の素のボタン枠がそのまま出る(灰色の四角が見える)。
--     隠すには不透明な板を上から被せるしかなく、静かな絵作りに板は足したくない。
--   ・retained の uiButton を付けると、エンジンのフォーカス移動が自動で働いて
--     【水色の角丸フォーカスリング】(UISystem.cpp の IM_COL32(120,180,255,235))が
--     描かれてしまう。色も形も Lua からは変えられない。
--   ・Lua にマウス座標/クリックを読む口は無い(input:* は捕捉の on/off と差分だけ)。
--   どうしてもマウスを付けるなら「不透明な板 + 即時 ui:button + 即時 ui:image」の
--   組み合わせになる。板が要る、という一点を飲めるかどうかの話。

local N_SHOT  = 4
local N_GHOST = 13          -- 中心 1 + 内リング 6 + 外リング 6
local R_IN    = 13.0        -- 内リング半径(キャンバスpx)。シーン JSON の生成値と一致させること
local R_OUT   = 29.0        -- 外リング半径

-- ---------------------------------------------------------------- 時間割(秒)
-- [2] 導入(START のあと)
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

-- [1] 選択画面
local T_ROOM  = 1.70        -- 黒 → 奥の部屋が薄く見えるまで
local T_SEAM  = 0.45        -- 継ぎ目の線が点き始める時刻
local D_SEAM  = 0.55        -- 線が伸びきるまで
local T_HALF  = 1.05        -- 題名の上下が寄り始める時刻
local D_HALF  = 1.20        -- 寄りきるまで
local T_MENU  = 2.35        -- 選択肢が出る時刻
local D_MENU  = 0.75
local FILM_A  = 0.46        -- 選択画面で部屋に掛ける暗幕の濃さ
local LEAVE_LEN = 0.90      -- START を押してから導入が始まるまで
local BYE_LEN   = 0.85      -- EXIT を押してから終了するまで

-- 奥の 3D 部屋の合焦距離(m)。0.35 だと部屋が丸ごとぼけ、8.0 で奥の壁まで合う。
local DOF_NEAR = 0.35
local DOF_MID  = 2.20
local DOF_FAR  = 8.00

-- ---------------------------------------------------------------- 音
-- ★題名曲はタイトル → ロード画面まで一続きで鳴らし、本編が開く所で消える。
--   止めているのは 2 か所:
--     ・LoadingScreen.lua … 幕が閉じるあいだに BGM の音量を 0 まで落とす
--     ・StageMusic.lua    … 本編の OnStart で無条件に stopBGM()
--   ★どちらか片方だけだと「本編まで曲が鳴り続ける」か「ぶつ切り」になる。
-- ★耳で詰める値はこの 3 つ。
local TITLE_BGM = "audio/bgm/title.mp3"
local TITLE_VOL = 0.55      -- 題名曲の音量。控えめに敷く
local HUM_VOL   = 0.10      -- 部屋の唸り。曲を敷いたぶん元の 0.20 から半分に落とした

-- ★★メニューの手応え。ここの 2 音だけで選択画面の操作感が決まる。耳で詰めるならここ。
--   nav   = 選択が 1 つ動いた。45ms の乾いた接点の音(source/gen_ui_sfx.py で合成)
--   enter = 決めた。300ms、nav より【低く・長く・重い】。押した本人にだけ分かる濃さ
--   ★lock.wav は「決定音」ではなく【決めたあとに起きること】(題名の継ぎ目が外れる)の
--     音。enter を先に鳴らして、その結果として lock が続く、という順にしてある。
local SFX_NAV     = "audio/ui/nav.wav"
local SFX_ENTER   = "audio/ui/enter.wav"
local NAV_VOL     = 0.34    -- 選択の移動。何度も鳴るので控えめに
local ENTER_VOL   = 0.50    -- START の決定
local ENTER_BYE   = 0.40    -- EXIT の決定。去る側なので一段落とす

-- ---------------------------------------------------------------- 画面配置
-- uiCanvas の基準は 1600x900・StretchToFill。即時 ui:* は【実ピクセル】なので、
-- retained 側の矩形と揃えるには必ずこの 2 つを通して換算すること。
local REF_W, REF_H = 1600, 900
local function sx(v) return v * SCREEN_W / REF_W end
local function sy(v) return v * SCREEN_H / REF_H end

-- 題名の継ぎ目。シーン JSON の Title_Logo_Top/Bot の矩形から出した値
-- (矩形の上端 152 + 高さ 178 * 0.4758)。矩形を動かしたらここも直すこと。
local SEAM_REF_Y = 236.7
local SEAM_HALF  = 616      -- 継ぎ目の線の半幅(ref px)。題名より少しはみ出す長さ
local SLIDE      = 34       -- 題名の上下の半身が寄る距離(ref px)。JSON の初期位置とセット

-- 床の印・破片の輪郭と同じ金。作品を通してこの色しか使わない
local GOLD = { 1.00, 0.84, 0.52 }

-- 選択肢。矩形はシーン JSON の Title_Menu_* と一致させること
local MENU = {
    { ent = "Title_Menu_Start", x0 = 738, y0 = 548, x1 = 862, y1 = 588 },
    { ent = "Title_Menu_Exit",  x0 = 760, y0 = 616, x1 = 840, y1 = 656 },
}

-- 蛍光灯の点灯。段付きのまま(イージングを掛けない)= 機械が点いているだけの見え方
local SEAM_STRIKE = {
    { 0.00, 0.00 }, { 0.04, 0.90 }, { 0.08, 0.05 }, { 0.20, 0.60 }, { 0.25, 0.03 },
    { 0.44, 1.00 }, { 0.50, 0.20 }, { 0.60, 0.85 }, { 0.70, 1.00 },
}

local function clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end

local function stepped(tbl, t)
    local v = 0
    for i = 1, #tbl do
        if t >= tbl[i][1] then v = tbl[i][2] else break end
    end
    return v
end

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

-- ---------------------------------------------------------------- 線 1 本
-- ロード画面(LoadingScreen.lua)の蛍光灯とまったく同じ描き方。
-- にじみ 2 枚を敷いてから芯を 1 枚。ぼかしが無いので枚数で代用している。
local function rule(cx, cy, half, thick, r, g, b, a)
    if a <= 0.002 or half <= 0.5 then return end
    ui:rect(cx - half - 10, cy - thick * 3.2, half * 2 + 20, thick * 6.4, r, g, b, a * 0.05, 0)
    ui:rect(cx - half - 4,  cy - thick * 1.7, half * 2 + 8,  thick * 3.4, r, g, b, a * 0.10, 0)
    ui:rect(cx - half,      cy - thick * 0.5, half * 2,      thick,       r, g, b, a * 0.92, 0)
end

local function setLogoAlpha(self, a)
    if self.logoT then scene:setUiColor(self.logoT, 0.92, 0.93, 0.89, a) end
    if self.logoB then scene:setUiColor(self.logoB, 0.92, 0.93, 0.89, a) end
end

local function setFilm(self, a)
    if self.black then scene:setUiColor(self.black, 0.006, 0.008, 0.007, a) end
end

local function hideTitleArt(self)
    if self.logoT then scene:setUiVisible(self.logoT, false) end
    if self.logoB then scene:setUiVisible(self.logoB, false) end
    for i = 1, #MENU do
        if self.menu[i] then scene:setUiVisible(self.menu[i], false) end
    end
end

-- ---------------------------------------------------------------- 導入の局面
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

-- ---------------------------------------------------------------- 選択画面
local function beginIntro(self)
    -- 導入へ渡す。題名と選択肢は用済みなので【要素ごと】消す(枠が残らないように)
    hideTitleArt(self)
    self.stage = "intro"
    setFilm(self, 1)
    post.set("dofFocusDist", DOF_NEAR)
    setPhase(self, 0)
end

local function confirm(self)
    if self.selection == 1 then
        self.stage = "leave"
        self.lt = 0
        -- 上下の半身が離れる = せっかく合わせた継ぎ目がまた外れる。
        -- 「ここから先は継ぎ目の向こう側」という送り出しにしている。
        if self.logoT then scene:tweenUi(self.logoT, { dy = -58, duration = LEAVE_LEN, easing = "in" }) end
        if self.logoB then scene:tweenUi(self.logoB, { dy = 58, duration = LEAVE_LEN, easing = "in" }) end
        sfx(SFX_ENTER, ENTER_VOL)          -- 決めた
        sfx("audio/lm/lock.wav", 0.22)     -- その結果、継ぎ目が外れていく
    else
        self.stage = "bye"
        self.lt = 0
        sfx(SFX_ENTER, ENTER_BYE)
    end
end

local function menuInput(self, dt)
    -- 出そろう前に押されたら、入場を飛ばして選べる状態にする
    local ready = self.mt >= T_MENU + D_MENU * 0.55
    local pressed = keyPressed("ENTER") or keyPressed("SPACE")
                 or padPressed("A") or padPressed("START")
    if not ready then
        if pressed or keyPressed("DOWN") or keyPressed("UP") or keyPressed("W") or keyPressed("S") then
            self.mt = T_MENU + D_MENU
        end
        return
    end

    if keyPressed("DOWN") or keyPressed("S") or padPressed("DPAD_DOWN") then
        if self.selection ~= 2 then self.selection = 2; sfx(SFX_NAV, NAV_VOL) end
    end
    if keyPressed("UP") or keyPressed("W") or padPressed("DPAD_UP") then
        if self.selection ~= 1 then self.selection = 1; sfx(SFX_NAV, NAV_VOL) end
    end
    -- ESC は「終わる」ではなく「EXIT を選ぶ」。誤爆で落ちないように一段挟む
    if keyPressed("ESC") and self.selection ~= 2 then
        self.selection = 2
        sfx(SFX_NAV, NAV_VOL)
    end

    -- 左スティック。倒しっぱなしで送り続けないよう、中立へ戻るまで 1 回だけ効かせる
    local _, stickY = padStick("left")
    local dir = 0
    if stickY > 0.65 then dir = 1 elseif stickY < -0.65 then dir = -1 end
    if dir ~= 0 and self.stickDir == 0 then
        local want = (dir > 0) and 1 or 2
        if self.selection ~= want then self.selection = want; sfx(SFX_NAV, NAV_VOL) end
    end
    self.stickDir = dir

    if pressed then confirm(self) end
end

-- 選択画面の絵。retained 側(題名・選択肢)の濃さを決めて、線だけ即時で引く。
local function drawMenu(self)
    local t = self.mt

    -- 暗幕: 真っ黒 → 奥の部屋がうっすら見える濃さへ
    setFilm(self, 1 - (1 - FILM_A) * clamp(t / T_ROOM, 0, 1))

    -- 題名。上下の半身の寄りは tweenUi(OnStart で予約済み)、濃さはここ
    setLogoAlpha(self, clamp((t - T_HALF) / D_HALF, 0, 1))

    -- 選択肢
    local ma = clamp((t - T_MENU) / D_MENU, 0, 1)
    for i = 1, #MENU do
        local e = self.menu[i]
        if e then
            local on = (self.selection == i)
            scene:setUiColor(e, 0.94, 0.95, 0.91, ma * (on and 1.0 or 0.40))
        end
    end

    -- 継ぎ目の線。蛍光灯と同じ点き方をして、そのまま題名の間に居座る
    local st = t - T_SEAM
    local lit = stepped(SEAM_STRIKE, st)
    if st > 0.70 then
        lit = lit * (0.955 + math.abs(math.sin(self.time * 37.0)) * 0.045)
    end
    local grow = clamp(st / D_SEAM, 0, 1)
    rule(SCREEN_W * 0.5, sy(SEAM_REF_Y), sx(SEAM_HALF) * grow,
         math.max(1.0, sy(3.0)), GOLD[1], GOLD[2], GOLD[3], lit)

    -- 選んでいる側に短い金の目印を左右へ 1 本ずつ。線しか使わない
    if ma > 0.02 then
        local it = MENU[self.selection]
        local cy = sy((it.y0 + it.y1) * 0.5)
        local th = math.max(1.0, sy(3.0))
        local len = sx(30)
        local gap = sx(26)
        local a = ma * (0.80 + math.sin(self.time * 2.4) * 0.12)
        ui:rect(sx(it.x0) - gap - len, cy - th * 0.5, len, th, GOLD[1], GOLD[2], GOLD[3], a, 0)
        ui:rect(sx(it.x1) + gap,       cy - th * 0.5, len, th, GOLD[1], GOLD[2], GOLD[3], a, 0)
    end
end

-- START のあと: 題名が割れて離れ、線だけが画面幅まで伸びて、黒へ沈む。
-- 線が伸びるのはロード画面の「痩せて走る線」への布石。
local function drawLeave(self)
    local k = clamp(self.lt / LEAVE_LEN, 0, 1)
    setLogoAlpha(self, (1 - k) * (1 - k))
    for i = 1, #MENU do
        local e = self.menu[i]
        if e then
            local br = (i == self.selection) and 1.0 or 0.40
            scene:setUiColor(e, 0.94, 0.95, 0.91, clamp(1 - self.lt / 0.28, 0, 1) * br)
        end
    end
    setFilm(self, FILM_A + (1 - FILM_A) * k)
    post.set("dofFocusDist", DOF_FAR + (DOF_NEAR - DOF_FAR) * k)

    local half = sx(SEAM_HALF) + (SCREEN_W * 0.5 - sx(SEAM_HALF)) * (k * k)
    rule(SCREEN_W * 0.5, sy(SEAM_REF_Y), half,
         math.max(1.0, sy(3.0)) * (1 - k * 0.55),
         GOLD[1], GOLD[2], GOLD[3], 1 - k * k * k)

    if k >= 1 then beginIntro(self) end
end

-- EXIT のあと: 線が中心へ縮んで消え、真っ黒になってから閉じる。
-- ★quit() は Application が窓へ WM_CLOSE を投げる(ScriptEngine.cpp の lua["quit"])。
--   エディタの Play 中に押すと【エディタごと閉じる】ので、確認用に押すときは注意。
--   万一 quit() が効かない環境でも、画面は真っ黒のまま止まる = 事故に見えない。
local function drawBye(self)
    local k = clamp(self.lt / BYE_LEN, 0, 1)
    setLogoAlpha(self, (1 - k) * (1 - k))
    for i = 1, #MENU do
        local e = self.menu[i]
        if e then
            local br = (i == self.selection) and 1.0 or 0.40
            scene:setUiColor(e, 0.94, 0.95, 0.91, clamp(1 - self.lt / 0.30, 0, 1) * br)
        end
    end
    setFilm(self, FILM_A + (1 - FILM_A) * k)
    rule(SCREEN_W * 0.5, sy(SEAM_REF_Y), sx(SEAM_HALF) * (1 - k),
         math.max(1.0, sy(3.0)), GOLD[1], GOLD[2], GOLD[3], 1 - k)

    if k >= 1 and not self.quitting then
        self.quitting = true
        hideTitleArt(self)
        quit()
    end
end

-- ---------------------------------------------------------------- 本体
function OnStart(self)
    self.time      = 0
    self.stage     = "menu"   -- menu → (leave | bye) → intro
    self.mt        = 0        -- 選択画面の経過
    self.lt        = 0        -- leave / bye の経過
    self.selection = 1
    self.stickDir  = 0
    self.quitting  = false

    self.phase     = 0        -- 0=黒 1=写真 2=ピント 3=静止 4=部屋が出る 5=退場
    self.pt        = 0
    self.st        = 0
    self.shot      = 0
    self.leaving   = false
    self.preloaded = false
    self.dip       = 0        -- 蛍光灯のちらつき用
    input:setMouseCapture(false)

    self.black  = grab("Title_Black")
    self.logoT  = grab("Title_Logo_Top")
    self.logoB  = grab("Title_Logo_Bot")
    self.menu   = {}
    for i = 1, #MENU do self.menu[i] = grab(MENU[i].ent) end
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
    if self.black then scene:setUiVisible(self.black, true) end
    setFilm(self, 1)
    setLogoAlpha(self, 0)
    for i = 1, #MENU do
        if self.menu[i] then scene:setUiColor(self.menu[i], 0.94, 0.95, 0.91, 0) end
    end

    -- 題名の上下の半身を寄せる。シーン JSON では上半分が SLIDE 上・下半分が SLIDE 下に
    -- 置いてあり、ここで寄せて継ぎ目を合わせる。tweenUi は相対移動なので JSON とセット。
    if self.logoT then
        scene:tweenUi(self.logoT, { dy = SLIDE, duration = D_HALF, delay = T_HALF, easing = "quint" })
    end
    if self.logoB then
        scene:tweenUi(self.logoB, { dy = -SLIDE, duration = D_HALF, delay = T_HALF, easing = "quint" })
    end

    -- 選択画面では奥の部屋にピントを合わせておく(START のあとに手前へ落ちてぼける)。
    -- ★brightness は【加算】で中立 0.0。ここに 1.0 を入れると画面が真っ白に飛ぶ。
    post.setMany{
        dofOn = true, dofFocusDist = DOF_FAR, dofAperture = 1.4,
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
    -- 部屋の唸り。★題名曲を敷いたぶん半分まで落とす(消しはしない。唸りが無くなると
    --   奥の部屋が「絵」になってしまい、曲だけが浮く)
    pcall(function() audio:playSFXId("audio/amb/hum.wav", true, HUM_VOL) end)

    -- 題名曲。★ここからロード画面まで【切らずに】鳴らし続ける。
    --   ・playBGM は同じパスでも必ず頭出しするので、既に鳴っているなら呼ばない。
    --     (タイトルへ戻ってきたときに曲が飛ぶのを防ぐ)
    --   ・BGM の音量つまみはロード画面が幕を閉じながら 0 まで下げていく。
    --     戻ってきた場合に無音のままにならないよう、ここで必ず戻しておく。
    --   ・止めるのは本編側(StageMusic.lua の OnStart)。ここでは止めない。
    pcall(function()
        audio:setBGMVolume(TITLE_VOL)
        if audio:getCurrentBGM() ~= TITLE_BGM or not audio:isBGMPlaying() then
            audio:playBGM(TITLE_BGM)
        end
    end)
end

function OnUpdate(self, dt)
    self.time = self.time + dt

    -- ---------------------------------------------------------- [1] 選択画面
    if self.stage == "menu" then
        self.mt = self.mt + dt
        menuInput(self, dt)
        drawMenu(self)

    elseif self.stage == "leave" then
        self.lt = self.lt + dt
        drawLeave(self)

    elseif self.stage == "bye" then
        self.lt = self.lt + dt
        drawBye(self)
    end

    -- ---------------------------------------------------------- [2] 導入
    if self.stage == "intro" then
        self.pt = self.pt + dt

        if keyPressed("ENTER") or keyPressed("SPACE") or keyPressed("ESC")
           or padPressed("A") or padPressed("START") then
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

        -- ぼけた絵は黒から浮き上がらせる(写真の重ねは不透明なので即時 ui:rect で覆う)
        if self.phase == 2 and self.pt < FOCUS_IN then
            ui:rect(0, 0, SCREEN_W, SCREEN_H, 0.006, 0.008, 0.007, 1 - self.pt / FOCUS_IN, 0)
        end
    end

    -- ---------------------------------------------------------- 上に重ねるもの
    edgeShade()

    -- 蛍光灯のちらつき。ほとんど気づかない濃さで、ときどき 1 フレームだけ落とす。
    if math.random() < 0.02 then self.dip = 0.06 end
    self.dip = math.max(0, self.dip - dt * 0.9)
    local flick = 0.012 + math.abs(math.sin(self.time * 1.7)) * 0.008 + self.dip
    ui:rect(0, 0, SCREEN_W, SCREEN_H, 0, 0, 0, flick, 0)

    -- 導入の最後、ピントが合ったところに小さく作品名。題名は既に見せてあるので
    -- ここは「署名」くらいの大きさ・薄さにとどめる。
    if self.stage == "intro" then
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
end
