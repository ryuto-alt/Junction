-- JUNCTION クリア画面。本編(stagedemo3)が白へ抜けきった【その白を受け取って】始まる。
-- scenes/clear_demo.json 用。
--
-- ★2026-09-09 改修 ―― 「JUNCTION と出るだけで、何がどうなったのか分からない」を直した。
--   それまでは題名の画しか出さなかった(文字を 1 文字も出さない作りだった)。
--   静かさは守りつつ、【クリアした】【何を成したか】【次にどこへ行けるか】の
--   3 つを必ず伝える。伝わらない寡黙は失敗、という判断でこうしてある。
--   ★ただし出す物は増やしていない ―― 使うのは今までと同じ
--     「金の線」と「無彩色の字」だけ。ファンファーレも色も足していない。
--
-- ★見せる物(段取り):
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
--                     ★この作品でいちばん言いたいこと ―― 継ぎ目が無くなった
--   [6] ★成績        ここが今回足した山。題名の下に、遊んだ人がやったことが【数字だけ】出る:
--                       ・金の細い線が【蛍光灯と同じ点き方】で点く(タイトルの線と同じ手つき)
--                       ・幕      23 本の短い金の線が、五幕ぶんに区切られて左から点いていく。
--                                 幕がひとつ埋まるたびに、継ぎ目が確定する音(lock.wav)が鳴る
--                       ・継ぎ目  その数が 0 から数え上がる
--                       ・時間    本編にかかった時間
--                     ★「線を点けていく」のは、本編で継ぎ目を 1 本ずつ確定させた
--                       あの手つきをそのままなぞっている。棒グラフではない。
--                     ★★ここに【文章を足さないこと】。
--                       一度「すべての継ぎ目が、つながった。」という一行を入れたが、
--                       2026-09-09 に作者から「エンディングのセリフはいらない。
--                       リザルトだけ出して終わりでいい」と指示があって落とした。
--                       出すのは やり遂げた事実の数字 だけ。物語を語る文は 1 行も出さない。
--   [7] 選択          「タイトルへ戻る」/「終わる」。マウス・キーボード・パッドのどれでも押せる
--   [8] 去る          線が画面幅まで伸びて、黒へ。タイトルへ戻る か、終了
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
--   ★記録の字も線も全部【即時】で描いている。題名(retained)より手前に出したいのと、
--     見た目を全部この 1 ファイルで詰められるようにするため。
--
-- ★フェードさせる retained UI は色のアルファだけでは枠/縁取りが残る。
--   用が済んだら scene:setUiVisible(e, false) で要素ごと消すこと。
--
-- ★★マウスの罠(2026-09-09 に調べ直した結論):
--   Lua にはマウス座標も左クリックも来ない(input:* は捕捉の on/off と差分だけ)。
--   即時 ui:button は ImGui の素のボタン枠(角丸の灰色)がそのまま出るので使えない。
--   → 選択肢は【retained の uiButton を当たり判定だけに使い、絵は即時で描く】。
--      設定パネル(source/hud_layout.json)が既に採っているのと同じやり方。
--   ★uiButton を付けるとエンジンのフォーカスナビが働き、選ばれた要素の周りに
--     【水色の角丸フォーカスリング】(UISystem.cpp の IM_COL32(120,180,255,235))が出る。
--     色も形も Lua からは変えられない。そこで毎フレーム setUiFocus(FOCUS_NONE) で
--     フォーカスを entt::null へ捨てて、リングが出ないようにしている。
--     ★副作用: エンジン側の決定(Enter/Space/A)も飛ばなくなる = 二重発火しない。
--       選択と決定はこの Lua が全部自分でやる。
--   ★ホバーの光りは uiButton の hoverColor が UIImage の色に【乗算】される性質を使う。
--     normalColor のアルファ 0 / hoverColor のアルファ 1 にしておくと、
--     「カーソルが乗った行だけ」下地が薄く光る。Lua からホバー状態は読めないので、
--     これが唯一の見えるホバー表現。
--   ★選択肢は出るまで uiRect.visible=false。visible=false の枝はエンジンが
--     丸ごと飛ばす = 当たり判定にもフォーカスにも入らない。早い段階で押されない。

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

-- [6] 成績。★どれも「前の物が落ち着いてから次」。重ねると読めない
local R_IN       = 0.60   -- 成績の面がぼんやり乗るまで(背の暗い帯もこれで濃くなる)
local R_RULE_T   = 0.30   -- 金の線が点き始める時刻
local R_RULE_GROW= 0.55   -- 線が伸びきるまで
local R_ROW_T    = 0.95   -- 幕/継ぎ目の行が出る時刻
local R_ROW_IN   = 0.50   -- その行が出るまで
local R_TALLY    = 1.90   -- 23 本の線が全部点くまで。★ここを速くすると「数えた」に見えない
local R_TIME_T   = 3.10   -- 時間の行が出る時刻
local R_TIME_IN  = 0.60
local R_HOLD     = 0.90   -- 成績が出そろってから選択肢へ渡すまで

local T_OPT_IN   = 0.85   -- 選択肢が出るまで
local AUTO_BACK  = 150.0  -- 誰も触らなければタイトルへ戻るまで(選択肢が出てから)
                          -- ★昔は 30 秒だった。記録を読む時間が要るので延ばしてある
local LEAVE_LEN  = 1.30   -- 押してから黒くなりきるまで

-- ---- 絵
local BLOW       = 2.60   -- 白飛びの exposure。★exposure は【乗算・中立 1.0】
local EXP_END    = 1.02   -- 落ち着いたときの exposure
local GOLD       = { 1.00, 0.84, 0.52 }   -- 床の印・破片の輪郭と同じ金。他の色は使わない
local INK        = { 0.93, 0.94, 0.90 }   -- 字。題名と同じ骨色
local SUB        = { 0.72, 0.71, 0.66 }   -- 添え字。HUD の sub と同じ
local SEAM_REF_Y = 236.7  -- 合わせ目の高さ(ref px)。題名の矩形 152 + 178*0.4758
local SEAM_HALF  = 616    -- 合わせ目の線の半幅(ref px)
local LOGO_A     = 0.86   -- 題名の濃さ。タイトル(1.0)より一段控える
-- ★記録を出すあいだ、部屋に暗幕を掛ける。掛けないと戸口の【真っ白】の上に
--   骨色の字が乗って一文字も読めない(戸口は画面の ど真ん中 x722-878 / y394-559 を占める)。
--   ★濃さは実機で詰めた 0.60。タイトル(TitleMenu.lua の FILM_A)は 0.46 だが、
--     あちらは扉が閉じていて部屋が暗い。こちらは灯りが残っていて壁も床も白いので、
--     同じ濃さだと成績の下半分(選択肢)が床の明るさに負けて読めない。
-- ★★暗幕は【retained の板 Clear_Black(order 0)】でやること。即時 ui:rect でやると
--   retained の題名(order 60/61)より手前に乗ってしまい、題名まで一緒に暗くなる。
--   タイトルが Title_Black でやっているのとまったく同じ作り。
local FILM_A     = 0.60
local FILM_IN    = 1.30   -- 暗幕が乗りきるまで(秒)

-- 成績の版面(ref px / 1600x900 基準)。★字は全部この座標で置いている。
-- ★文章は 1 行も置かない。置くのは【見出し】と【数字】と【線】だけ。
local RULE_Y     = 438    -- 成績の上に引く金の線(ここから下が成績、という区切り)
local RULE_HALF  = 342    -- ★表の左端(見出し 469)〜右端(短い線の終わり 1142)にぴたり合わせる
local LABEL_X    = 540    -- 行の見出しの【右端】(右寄せ)
local VALUE_X    = 592    -- 値と線の【左端】(左寄せ)
local LABEL_SZ   = 21
local VALUE_SZ   = 28     -- ★数字が主役なので見出しより一段大きく置く
local ROW_ACT_Y  = 468    -- 幕の行(短い線の並び)の上端
local TICK_H     = 22     -- 短い線 1 本の高さ
local TICK_W     = 6      -- 太さ
local TICK_GAP   = 14     -- 同じ幕の中の間隔
local ACT_GAP    = 40     -- 幕と幕のあいだ
local ACT_NUM_Y  = 500    -- 一 二 三 四 五 の上端
local ACT_NUM_SZ = 16
local ROW_SEAM_Y = 540    -- 継ぎ目の行
local ROW_TIME_Y = 588    -- 時間の行
local OPT_RULE_Y = 664    -- 選択肢の上の細い線
local OPT_RULE_HALF = 46
local OPT_Y      = { 700, 752 }   -- 選択肢の字の上端
local OPT_SZ     = 26
local OPT_TRACK  = 6
local HINT_X     = 1090   -- 押し方の添え字の【右端】。★選択中の金の目印(右端 961)を避ける
local HINT_SZ    = 15
local BAND_Y0    = 392    -- 成績の背に敷く暗い帯(上端 / 下端 / いちばん濃い所)。
local BAND_Y1    = 668    -- ★ふちの 48px は薄い ―― 字の行が全部【濃い所】に入るよう外へ広げてある
local BAND_Y1_OPT= 818    -- 選択肢が出たら、帯もそこまで伸びる(選択肢も床の明るさに負けるため)
local BAND_A     = 0.34

-- ---- 音
local BACK_SCENE = "scenes/title_demo.json"
local TITLE_BGM  = "audio/bgm/title.mp3"
local BGM_VOL    = 0.50   -- タイトル曲。向こう(0.55)より気持ち下げて置く
local HUM_VOL    = 0.09   -- 部屋の唸り
local SFX_LAMP   = "audio/ui/touch.wav"    -- 灯りが 1 本落ちる。低くて短い
local SFX_NAV    = "audio/ui/nav.wav"      -- 選び直した
local SFX_ENTER  = "audio/ui/enter.wav"    -- 決めた。タイトルと同じ決定音
local SFX_LOCK   = "audio/lm/lock.wav"     -- ★幕がひとつ埋まった。本編で継ぎ目が確定する音そのもの
local SFX_ROW    = "audio/ui/detent.wav"   -- 記録の行が 1 つ置かれた
local LAMP_VOL   = 0.13
local NAV_VOL    = 0.20
local ENTER_VOL  = 0.45
local LOCK_VOL   = 0.15
local ROW_VOL    = 0.13

-- 落ちる順。★真ん中(ClearLight_2)は【残す】ので入れない
local FALL_ORDER = { "ClearLight_3", "ClearLight_1" }

-- 合わせ目の線の点き方。タイトル(TitleMenu.lua の SEAM_STRIKE)と同じ段付き。
-- イージングを掛けない = 蛍光灯が点いているだけの見え方。
local SEAM_STRIKE = {
    { 0.00, 0.00 }, { 0.04, 0.90 }, { 0.08, 0.05 }, { 0.20, 0.60 }, { 0.25, 0.03 },
    { 0.44, 1.00 }, { 0.50, 0.20 }, { 0.60, 0.85 }, { 0.70, 1.00 },
}

-- ================================================================ 記録の元データ
-- ★継ぎ目の【正】は source/gen_liminal.py が書き出す CONNS(assets/components/Liminal.lua の
--   >>>DATA ブロック)。ここに置いてあるのは「見せ方」のための写しなので、
--   幕の区切りや多義の組を変えたら、ここも直すこと。数え方は下の readRecord() を読む。
--
--   幕の区切り(README「5 幕」と同じ):
--     一 事務所棟 1..4 / 二 別棟 5..10 / 三 立坑 11..16 / 四 大展示室 17..21 / 五 環の間 22..25
local ACTS = {
    { num = "一", lo = 1,  hi = 4  },
    { num = "二", lo = 5,  hi = 10 },
    { num = "三", lo = 11, hi = 16 },
    { num = "四", lo = 17, hi = 21 },
    { num = "五", lo = 22, hi = 25 },
}

-- ★多義(どちらか一方しか成立しない継ぎ目)の組。CONNS の excl と同じ。
--   片方が確定した瞬間にもう片方は永久に成立しない ―― だから
--   【継ぎ目は 25 本あるが、1 回の遊びで繋げられるのは 23 本】。
--   分母を 25 にすると、全部やり切った人が 23/25 と出て「取りこぼした」に見える。
local EXCL_PAIRS = { { 7, 8 }, { 15, 16 } }

-- ================================================================ 下ごしらえ
local REF_W, REF_H = 1600, 900
local function sx(v) return v * SCREEN_W / REF_W end
local function sy(v) return v * SCREEN_H / REF_H end

local FOCUS_NONE = 4294967295   -- ★entt::null。setUiFocus に渡すとフォーカスが外れる

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

-- ---------------------------------------------------------------- 字
-- ★ImGui の実寸は Lua から測れない。字を 1 文字ずつ置いて字間を作りたいので、
--   幅は「全角 1.0em / 半角 0.5em 前後」の見当で持つ。多少ずれても
--   中央寄せ・右寄せの位置が数 px 動くだけで、字そのものは崩れない。
local function utf8chars(s)
    local out, i = {}, 1
    while i <= #s do
        local b = s:byte(i)
        local n = (b < 0xC0) and 1 or ((b < 0xE0) and 2 or ((b < 0xF0) and 3 or 4))
        out[#out + 1] = s:sub(i, i + n - 1)
        i = i + n
    end
    return out
end

local function advEm(ch)
    if ch:byte(1) >= 0x80 then return 1.00 end      -- 全角
    if ch == " " then return 0.30 end
    if ch == ":" or ch == "." or ch == "/" then return 0.30 end
    if ch >= "0" and ch <= "9" then return 0.52 end
    return 0.54
end

-- ref px での幅。size / track も ref px で渡す
local function measure(s, size, track)
    local cs = utf8chars(s)
    local w = 0
    for i = 1, #cs do
        w = w + advEm(cs[i]) * size
        if i < #cs then w = w + track end
    end
    return w
end

-- 字を置く。x は align で意味が変わる(0=左端 1=中央 2=右端)。座標は ref px。
-- ★ui:text は毎フレーム積んでよい(即時モード)。retained の setUiText とは別物。
local function put(x, y, s, size, track, align, col, a)
    if a <= 0.004 or s == "" then return 0 end
    local w = measure(s, size, track)
    local left = x
    if align == 1 then left = x - w * 0.5 elseif align == 2 then left = x - w end
    local cs = utf8chars(s)
    local cx = left
    for i = 1, #cs do
        -- ★字の背に薄い影を敷く。明るい壁でも暗い床でも読めるようにするため。
        --   縁取りではなく影 1 枚 ―― 縁取りは「UI らしさ」が出て世界から浮く
        ui:text(sx(cx) + sy(1.2), sy(y) + sy(1.2), cs[i], sy(size), 0.02, 0.02, 0.02, a * 0.55)
        ui:text(sx(cx), sy(y), cs[i], sy(size), col[1], col[2], col[3], a)
        cx = cx + advEm(cs[i]) * size + track
    end
    return w
end

-- 線 1 本。TitleMenu.lua / LoadingScreen.lua とまったく同じ描き方。
-- ぼかしが無いので、にじみ 2 枚を敷いてから芯を 1 枚で代用する。
local function rule(cx, cy, half, thick, r, g, b, a)
    if a <= 0.002 or half <= 0.5 then return end
    ui:rect(cx - half - 10, cy - thick * 3.2, half * 2 + 20, thick * 6.4, r, g, b, a * 0.05, 0)
    ui:rect(cx - half - 4,  cy - thick * 1.7, half * 2 + 8,  thick * 3.4, r, g, b, a * 0.10, 0)
    ui:rect(cx - half,      cy - thick * 0.5, half * 2,      thick,       r, g, b, a * 0.92, 0)
end

-- 記録の背に敷く、ふちの柔らかい暗い帯。
-- ★暗幕(Clear_Black)だけでは足りない ―― 戸口の【真っ白】が画面のど真ん中に居座っていて、
--   記録の字と線がちょうどそこを横切る。かといって帯の端を切り落とすと「板を貼った」に
--   見えるので、edgeShade と同じ「幅の違う帯を入れ子に重ねる」やり方でふちをぼかす。
local function softBand(y0, y1, peak)
    if peak <= 0.004 then return end
    local n, soft = 7, 48
    for i = 1, n do
        local ins = soft * (i - 1) / n
        local top, bot = y0 + ins, y1 - ins
        if bot > top then
            ui:rect(0, sy(top), SCREEN_W, sy(bot - top), 0, 0, 0, peak / n, 0)
        end
    end
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

-- ---------------------------------------------------------------- 記録を読む
-- ★本編から渡ってくるのは saveNum の値。saveNum のストアは【シーンをまたいでも残る】
--   (エンジンが消すのは Play を押し直した時だけ / ApplicationScene.cpp)。
--   だから loadScene("scenes/clear_demo.json") で渡ってきた側でそのまま読める。
--     lm_clear    … 1 = 本編を最後まで行った
--     lm_c<id>    … 1 = その継ぎ目を【自分で】確定させた(多義で打ち切られた側は 0 のまま)
--     lm_time     … 本編にかかった秒(source/liminal_runtime.lua の「終わり方」の節で保存)
-- ★シーンを単体で開いた時(エディタで clear_demo.json を直接 Play した時)は
--   lm_clear が立っていない。その時は【満点の見本】を出す ―― 0/23 と出て
--   壊れているように見えるより、見た目を確かめられるほうが大事。
local function readRecord()
    local demo = loadNum("lm_clear", 0) < 0.5
    local rec = { acts = {}, done = 0, total = 0, demo = demo }
    for i = 1, #ACTS do
        local a = ACTS[i]
        local n = a.hi - a.lo + 1
        for _, pr in ipairs(EXCL_PAIRS) do
            -- 組の【両方】がこの幕に入っているなら、その幕で繋げられるのは 1 本ぶん少ない
            if pr[1] >= a.lo and pr[1] <= a.hi and pr[2] >= a.lo and pr[2] <= a.hi then
                n = n - 1
            end
        end
        local d = 0
        if demo then
            d = n
        else
            for id = a.lo, a.hi do
                if loadNum(string.format("lm_c%d", id), 0) > 0.5 then d = d + 1 end
            end
            if d > n then d = n end   -- 数えすぎの保険(データを直した時に破綻させない)
        end
        rec.acts[i] = { num = a.num, total = n, done = d }
        rec.total = rec.total + n
        rec.done  = rec.done + d
    end
    local t = loadNum("lm_time", -1)
    if demo then t = -1 end
    rec.time = (t >= 0) and t or nil
    -- ★「全部つないだか」は数字(done / total)がそのまま言っているので、
    --   ここで真偽を作って文章を出し分けたりはしない。文章は 1 行も出さない。
    return rec
end

local function fmtTime(sec)
    local s = math.floor(sec + 0.5)
    local h = math.floor(s / 3600)
    local m = math.floor((s % 3600) / 60)
    local q = s % 60
    if h > 0 then return string.format("%d:%02d:%02d", h, m, q) end
    return string.format("%d:%02d", m, q)
end

-- ================================================================ 局面
-- 局面を進める。★入場の処理はここに 1 か所だけ置く(飛ばされても必ず通る)
local function setPhase(self, p)
    self.phase = p
    self.pt = 0
    if p == 3 then
        self.fell = 0
    elseif p == 6 then
        self.actRung = 0
        self.rowRung = 0
    elseif p == 7 then
        self.optRung = false
        -- ★ここで初めて押せるようにする。visible=false のあいだは
        --   当たり判定にもフォーカスにも入らない = 誤爆しない
        for i = 1, #self.opts do
            if self.opts[i] then scene:setUiVisible(self.opts[i], true) end
        end
    end
end

-- 成績を全部出しきった状態にする(選択肢へ渡す時に使う)
local function fillRecord(self)
    self.recA  = 1
    self.ruleA = 1
    self.ruleK = 1
    self.rowA  = 1
    self.tally = 1
    self.timeA = 1
end

-- 飛ばす。★[5] までを一気に畳んで [6](成績)の頭へ送る。
--   ★成績は飛ばさない ―― 「何がどうなったか」を見せるのが今回の目的なので、
--     ここを飛ばしたら元の「JUNCTION と出るだけ」に戻ってしまう。
local function skipToRecord(self)
    for i = 1, #FALL_ORDER do lampIntensity(self, FALL_ORDER[i], 0.0) end
    -- ★白飛びの exposure を戻し忘れると、飛ばした人だけ真っ白のまま終わる
    post.set("exposure", EXP_END)
    self.whiteA = 0
    self.seamA  = 0
    self.logoA  = 1
    setPhase(self, 6)
end

-- 選択肢を消す。★アルファ 0 では縁取り/枠が残るので【要素ごと】消す。
--   消えた枝はエンジンが丸ごと飛ばすので、フォーカスリングも一緒に消える。
local function hideOpts(self)
    for i = 1, #self.opts do
        if self.opts[i] then scene:setUiVisible(self.opts[i], false) end
    end
end

local function chooseNow(self, i)
    if self.phase >= 8 then return end
    self.selection = i
    sfx(SFX_ENTER, ENTER_VOL)
    hideOpts(self)
    setPhase(self, 8)
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
    self.blackA = 0         -- 去るときの黒
    self.leaving = false
    -- 成績の出方(0..1)。recA は面ぜんたいの濃さ(背の暗い帯もこれで濃くなる)
    self.recA, self.ruleA, self.ruleK, self.rowA, self.tally, self.timeA = 0, 0, 0, 0, 0, 0
    self.actRung, self.rowRung = 0, 0
    self.filmA = 0          -- 部屋に掛ける暗幕(成績を読ませるため)
    self.optA = 0
    self.optRung = false
    self.selection = 1      -- 1 = タイトルへ戻る / 2 = 終わる
    self.stickDir = 0
    input:setMouseCapture(false)

    self.rec = readRecord()
    log(string.format("ClearScreen: 継ぎ目 %d/%d  時間 %s%s",
        self.rec.done, self.rec.total,
        self.rec.time and fmtTime(self.rec.time) or "-",
        self.rec.demo and "  (記録が無いので見本)" or ""))

    self.logoT = grab("Clear_Logo_Top")
    self.logoB = grab("Clear_Logo_Bot")
    self.black = grab("Clear_Black")   -- 記録を読ませるための暗幕。題名より【下】の板
    if self.black then scene:setUiColor(self.black, 0.006, 0.008, 0.007, 0.0) end
    setLogoAlpha(self, 0)

    -- 選択肢の当たり判定(絵は即時で描く。ここは押せる矩形とホバーの下地だけ)
    self.opts = { grab("Clear_Opt_Back"), grab("Clear_Opt_Quit") }
    for i = 1, #self.opts do
        if self.opts[i] then scene:setUiVisible(self.opts[i], false) end
    end
    events:on("clear_back", function() chooseNow(self, 1) end)
    events:on("clear_quit", function() chooseNow(self, 2) end)

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

-- ---------------------------------------------------------------- 入力
-- 選択肢が出ている時だけの操作。マウスは uiButton → events(clear_back/clear_quit)。
local function optInput(self)
    local move = 0
    if keyPressed("DOWN") or keyPressed("S") or padPressed("DPAD_DOWN") then move = 1 end
    if keyPressed("UP")   or keyPressed("W") or padPressed("DPAD_UP")   then move = -1 end
    -- 左スティック。倒しっぱなしで送り続けないよう、中立へ戻るまで 1 回だけ効かせる
    local _, stickY = padStick("left")
    local dir = 0
    if stickY > 0.65 then dir = -1 elseif stickY < -0.65 then dir = 1 end
    if dir ~= 0 and self.stickDir == 0 then move = dir end
    self.stickDir = dir

    if move ~= 0 then
        local want = (self.selection == 1) and 2 or 1
        if want ~= self.selection then
            self.selection = want
            sfx(SFX_NAV, NAV_VOL)
        end
    end

    -- ★ESC / B は「終わる」を【選ぶ】だけ。もう一度押したら終わる。
    --   タイトル(TitleMenu.lua)と同じ手つき。誤爆で落ちないように一段挟む
    if keyPressed("ESC") or padPressed("B") then
        if self.selection ~= 2 then
            self.selection = 2
            sfx(SFX_NAV, NAV_VOL)
        else
            chooseNow(self, 2)
        end
        return
    end
    if keyPressed("ENTER") or keyPressed("SPACE") or padPressed("A") or padPressed("START") then
        chooseNow(self, self.selection)
    end
end

function OnUpdate(self, dt)
    self.time = self.time + dt
    self.pt   = self.pt + dt

    -- ★毎フレーム、エンジンのフォーカスを捨てる。
    --   これをやらないと選択肢に【水色のフォーカスリング】が出る(冒頭の罠を読むこと)。
    pcall(function() setUiFocus(FOCUS_NONE) end)

    local confirm = keyPressed("ENTER") or keyPressed("SPACE")
                    or padPressed("A") or padPressed("START")
    -- ★白が引く前の ESC は効かせない(渡ってきた直後の誤爆で終わらせない)
    local escape = (self.phase >= 2) and (keyPressed("ESC") or padPressed("B"))

    -- ---------------------------------------------------------- 局面
    if self.phase == 0 then                       -- 真っ白
        if confirm or self.pt >= T_WHITE then setPhase(self, 1) end

    elseif self.phase == 1 then                   -- 白が引いて部屋が出る
        local k = clamp(self.pt / T_EMERGE, 0, 1)
        -- ★白は【遅く抜き始めて、あとから一気に】。等速だと「暗転の逆」にしか見えない
        self.whiteA = (1 - k) ^ 0.65
        post.set("exposure", EXP_END + (BLOW - EXP_END) * (1 - k) ^ 0.85)
        if confirm or escape then skipToRecord(self)
        elseif self.pt >= T_EMERGE then setPhase(self, 2) end

    elseif self.phase == 2 then                   -- ただ見せる
        if confirm or escape then skipToRecord(self)
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
        if confirm or escape then skipToRecord(self)
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
        if confirm or escape then skipToRecord(self)
        elseif self.pt >= T_LOGO_IN + T_SEAM_HOLD then setPhase(self, 5) end

    elseif self.phase == 5 then                   -- ★継ぎ目が消える
        self.logoA = 1
        local k = clamp(self.pt / T_SEAM_OUT, 0, 1)
        -- 三乗で落とす = 最後まで薄く残ってから、無くなる
        self.seamA = (1 - k) ^ 3
        if confirm or escape then skipToRecord(self)
        elseif self.pt >= T_SEAM_OUT then setPhase(self, 6) end

    elseif self.phase == 6 then                   -- ★成績
        self.logoA = 1
        self.seamA = 0
        local t = self.pt
        self.recA = clamp(t / R_IN, 0, 1)
        -- 金の線。★蛍光灯と同じ点き方(SEAM_STRIKE)。この作品の線は全部この点き方をする
        local rt = t - R_RULE_T
        self.ruleA = stepped(SEAM_STRIKE, rt)
        if rt > 0.70 then
            self.ruleA = self.ruleA * (0.955 + math.abs(math.sin(self.time * 37.0)) * 0.045)
        end
        self.ruleK = clamp(rt / R_RULE_GROW, 0, 1)
        self.rowA  = clamp((t - R_ROW_T) / R_ROW_IN, 0, 1)
        -- 短い線が左から点いていく。0..1
        self.tally = clamp((t - R_ROW_T) / R_TALLY, 0, 1)
        self.timeA = clamp((t - R_TIME_T) / R_TIME_IN, 0, 1)

        -- 幕がひとつ埋まるたびに、継ぎ目が確定する音を鳴らす。★1 本ごとに鳴らすと
        --   機関銃になるので【幕の切れ目でだけ】鳴らす = 5 回
        local litN = math.floor(self.tally * self.rec.done + 0.0001)
        local acc, filled = 0, 0
        for i = 1, #self.rec.acts do
            acc = acc + self.rec.acts[i].done
            if litN >= acc and acc > 0 then filled = i end
        end
        if filled > self.actRung then
            self.actRung = filled
            sfx(SFX_LOCK, LOCK_VOL)
        end
        -- 行が置かれる音(継ぎ目の行 → 時間の行 の 2 回)
        local rows = 0
        if self.rowA  >= 1 then rows = 1 end
        if self.timeA >= 1 and self.rec.time then rows = 2 end
        if rows > self.rowRung then
            self.rowRung = rows
            sfx(SFX_ROW, ROW_VOL)
        end

        -- ★押されても成績は【飛ばさない】。押したら「出しきる」まで早送りして、
        --   出しきった姿を R_HOLD ぶん見せてから選択肢へ渡す。
        --   ここを素通しにすると、押した人だけ元の「JUNCTION と出るだけ」に戻ってしまう。
        if t >= R_TIME_T + R_TIME_IN + R_HOLD then
            setPhase(self, 7)
        elseif confirm or escape then
            self.pt = R_TIME_T + R_TIME_IN
        end

    elseif self.phase == 7 then                   -- 選択
        self.logoA = 1
        fillRecord(self)
        self.optA = clamp(self.pt / T_OPT_IN, 0, 1)
        if not self.optRung and self.optA >= 1 then
            self.optRung = true
            sfx(SFX_NAV, NAV_VOL)
        end
        if self.optA >= 0.55 then optInput(self) end
        -- 誰も触らないまま置き去りにされた時の保険。タイトルへ戻す
        if self.pt >= T_OPT_IN + AUTO_BACK then
            self.selection = 1
            hideOpts(self)
            setPhase(self, 8)
        end

    elseif self.phase == 8 then                   -- 去る
        local k = clamp(self.pt / LEAVE_LEN, 0, 1)
        self.blackA = k * k
        self.logoA = (1 - k) * (1 - k)
        self.optA  = (1 - k) * (1 - k)
        self.recA  = self.optA
        self.rowA  = self.optA
        self.timeA = self.optA
        self.ruleA = self.optA
        if k >= 1 and not self.leaving then
            self.leaving = true
            setLogoAlpha(self, 0)                 -- ★要素ごと消す。縁取りが残らないように
            hideOpts(self)
            if self.selection == 2 then
                -- ★quit() は Application が窓へ WM_CLOSE を投げる。
                --   エディタの Play 中に押すと【エディタごと閉じる】ので確認時は注意。
                quit()
            else
                -- 既に真っ黒なので、遷移側の演出は【極短】でいい。
                -- 白 → 黒 → クリア画面 のような二段の暗転を作らないための短さ。
                fadeToScene(BACK_SCENE, 0.55)
            end
        end
    end

    -- ---------------------------------------------------------- 曲
    -- 白が引くあいだに、ゆっくり戻ってくる。★去るときは触らない ――
    --   TitleMenu.lua が 0.55 へ戻すので、曲は切れずにタイトルへ渡る
    if self.phase >= 1 and self.phase < 8 then
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

    -- ★暗幕(retained の Clear_Black)。記録が始まったらゆっくり乗せる。
    --   これが無いと戸口の真っ白の上に字が乗って読めない。冒頭の★を読むこと。
    if self.phase >= 6 then
        self.filmA = math.min(FILM_A, self.filmA + dt * (FILM_A / FILM_IN))
    end
    if self.black then scene:setUiColor(self.black, 0.006, 0.008, 0.007, self.filmA) end

    -- 合わせ目の線。★題名の上下の【あいだ】に引く。タイトルとまったく同じ位置・同じ太さ
    if self.seamA > 0.002 then
        rule(SCREEN_W * 0.5, sy(SEAM_REF_Y), sx(SEAM_HALF),
             math.max(1.0, sy(3.0)), GOLD[1], GOLD[2], GOLD[3], self.seamA)
    end

    local rec = self.rec
    local th  = math.max(1.0, sy(3.0))

    -- ------------------------------------------------ 成績の背
    -- ★選択肢が出るのに合わせて帯も下へ伸びる。床は明るいので、
    --   伸ばさないと「終わる」と押し方の添え字が地に溶けて読めない。
    softBand(BAND_Y0, BAND_Y1 + (BAND_Y1_OPT - BAND_Y1) * self.optA,
             self.recA * BAND_A)

    -- ------------------------------------------------ 成績の上の金の線
    -- ★ここから下が成績、という区切りの 1 本。文章の代わりにこの線が置いてある。
    if self.ruleA > 0.002 then
        rule(SCREEN_W * 0.5, sy(RULE_Y), sx(RULE_HALF) * self.ruleK, th,
             GOLD[1], GOLD[2], GOLD[3], self.ruleA)
    end

    -- ------------------------------------------------ 幕 ―― 短い線の並び
    if self.rowA > 0.004 then
        local a = self.rowA
        put(LABEL_X, ROW_ACT_Y - 1, "幕", LABEL_SZ, 4, 2, SUB, a * 0.95)

        local litN = self.tally * rec.done      -- 点いている本数(小数)
        local x = VALUE_X
        local onSeen = 0                        -- ★【繋いだ本だけ】を数える
        local acc = 0                           -- ここまでの幕で繋いだ本数の累計
        for i = 1, #rec.acts do
            local act = rec.acts[i]
            acc = acc + act.done
            for k = 1, act.total do
                local on = (k <= act.done)      -- そもそも繋いだ本か
                -- 「点いていく」演出。左から順に、まだ来ていない線は薄いまま。
                -- ★数えるのは繋いだ本だけ。全部の枠で数えると、取りこぼしがある人の
                --   終盤の線が【永久に点かない】(litN が本数ぶんしか伸びないため)。
                --   繋げなかった枠は薄いまま置いておく = 通らなかった道が見える
                local lit = 0
                if on then
                    onSeen = onSeen + 1
                    lit = clamp(litN - (onSeen - 1), 0, 1)
                end
                local aa  = a * (on and (0.14 + 0.86 * lit) or 0.10)
                ui:rect(sx(x), sy(ROW_ACT_Y), math.max(1.0, sx(TICK_W)), sy(TICK_H),
                        GOLD[1], GOLD[2], GOLD[3], aa * 0.92, 0)
                -- 点いた線には、にじみを 1 枚だけ足す(蛍光灯の光り方に揃える)
                if on and lit > 0.02 then
                    ui:rect(sx(x) - sx(3), sy(ROW_ACT_Y) - sy(3),
                            math.max(1.0, sx(TICK_W)) + sx(6), sy(TICK_H) + sy(6),
                            GOLD[1], GOLD[2], GOLD[3], a * lit * 0.10, 0)
                end
                x = x + TICK_W + ((k < act.total) and TICK_GAP or 0)
            end
            -- 幕の番号。★その幕の線が全部点きおわった瞬間に濃くなる = 幕が埋まった合図
            local gw = act.total * TICK_W + (act.total - 1) * TICK_GAP
            local full = (act.done >= act.total) and (litN >= acc)
            put(x - gw * 0.5, ACT_NUM_Y, act.num, ACT_NUM_SZ, 0, 1, SUB,
                a * (full and 0.95 or 0.35))
            x = x + ((i < #rec.acts) and ACT_GAP or 0)
        end

        -- ------------------------------------------------ 継ぎ目 ―― 数
        put(LABEL_X, ROW_SEAM_Y, "継ぎ目", LABEL_SZ, 4, 2, SUB, a * 0.95)
        local n = math.floor(litN + 0.0001)
        local w = put(VALUE_X, ROW_SEAM_Y - 2, string.format("%d", n), VALUE_SZ, 2, 0, INK, a)
        put(VALUE_X + w + 10, ROW_SEAM_Y + 1, string.format("/ %d", rec.total),
            LABEL_SZ, 2, 0, SUB, a * 0.85)
    end

    -- ------------------------------------------------ 時間
    if self.timeA > 0.004 and rec.time then
        local a = self.timeA
        put(LABEL_X, ROW_TIME_Y, "時間", LABEL_SZ, 4, 2, SUB, a * 0.95)
        put(VALUE_X, ROW_TIME_Y - 2, fmtTime(rec.time), VALUE_SZ, 2, 0, INK, a)
    end

    -- ------------------------------------------------ 選択肢
    if self.optA > 0.004 then
        local a = self.optA
        -- 上に細い線を 1 本。★昔ここにあった「押せる合図の線」をそのまま残してある
        rule(SCREEN_W * 0.5, sy(OPT_RULE_Y), sx(OPT_RULE_HALF) * a, th,
             GOLD[1], GOLD[2], GOLD[3], a * 0.75)

        local LABELS = { "タイトルへ戻る", "終わる" }
        local HINTS  = { "Enter / A", "Esc / B" }
        for i = 1, 2 do
            local on = (self.selection == i)
            local y  = OPT_Y[i]
            -- ★選んでいない側も【読める濃さ】で置く。薄くしすぎると
            --   「もう一つ選べる」ことに気づかれない ―― 今回直したかったのはそこ
            local w  = put(REF_W * 0.5, y, LABELS[i], OPT_SZ, OPT_TRACK, 1, INK,
                           a * (on and 1.0 or 0.50))
            put(HINT_X, y + 6, HINTS[i], HINT_SZ, 2, 2, SUB, a * (on and 0.80 or 0.36))
            -- 選んでいる側に短い金の目印を左右へ 1 本ずつ。★タイトルとまったく同じ作法
            if on then
                local cy = sy(y + OPT_SZ * 0.5)
                local len, gap = sx(28), sx(24)
                local ma = a * (0.80 + math.sin(self.time * 2.4) * 0.12)
                ui:rect(sx(REF_W * 0.5 - w * 0.5) - gap - len, cy - th * 0.5, len, th,
                        GOLD[1], GOLD[2], GOLD[3], ma, 0)
                ui:rect(sx(REF_W * 0.5 + w * 0.5) + gap, cy - th * 0.5, len, th,
                        GOLD[1], GOLD[2], GOLD[3], ma, 0)
            end
            -- ホバーの下地(retained)。★normalColor のアルファが 0 なので
            --   カーソルが乗っている行だけ光る。乗っていなければ何も出ない
            if self.opts[i] then
                scene:setUiColor(self.opts[i], GOLD[1], GOLD[2], GOLD[3], a * 0.11)
            end
        end
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
