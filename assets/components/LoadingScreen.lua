-- JUNCTION ロード画面。タイトルと本編のあいだに挟む無機質なトランジション。
--
-- 出すのは【線 1 本】だけ。進捗バー・スピナー・文字といった「ゲーム UI」らしい物は
-- 一切描かない。本編(stagedemo3)のアセットはタイトル側で preloadScene 済み。
--
--   蛍光灯が 1 本点く
--     → 痩せて画面幅の細い横線になって走る
--     → その 1 本のまま静止する            ← ここが「線一つになった」状態
--     → 両端が中心へ引き、代わりに中心に【縦の継ぎ目】が立ち上がる
--     → その継ぎ目から画面が左右へ開き、隙間の向こうに本編が現れる
--
-- ★最後の「開く」はエンジンのシーントランジション(curtain)にやらせている。
--   なぜ自前で描かないか:
--     開いた隙間に見えるのは【次のシーン(本編)】でなければ意味がない。ところが
--     Lua の ui:* が描けるのは「今のシーン」の上だけで、シーンをまたいで演出を
--     続ける手段が無い(スクリプトはシーン切替で消える)。
--   エンジンの transitionToScene は「閉じる → 中間点でロード → 開く」を
--   面倒を見てくれる唯一の口で、curtain は【左右の幕が中央で合わさる / 開く】型。
--   ここが効いている:
--     ・閉じる半分は真っ黒の画面に真っ黒の幕なので【見えない】。
--       見えているのは中心に立てた縦の継ぎ目だけで、幕はその継ぎ目に向かって
--       両側から寄ってくる = 継ぎ目が消えずに引き継がれる。
--     ・幕の合わせ目にはエンジン側が細い暖色の光を乗せる
--       (TransitionCurtain.hlsli の type==10。float3(0.45,0.40,0.35))。
--       閉じ切った瞬間、その光はちょうど画面中心 = こちらが立てた継ぎ目の位置に来る。
--     ・開く半分で、その光った合わせ目が左右へ割れて本編が出てくる。
--   → 「線 → 継ぎ目 → 割れて本編」が 1 本の線のまま繋がる。
--   本編側(Liminal.lua / stagedemo3.json)には一切触っていない。
--
-- ★エディタの Play で見ると、ロードしている数フレームだけ幕が消える。
--   ApplicationRender.cpp が「エディタではロード中にトランジションを描かない
--   (エディタ自前のローディング UI が前に出るため)」としているだけで、
--   ゲーム単体(ビルド後)では出っぱなしになる。

local NEXT = "scenes/stagedemo3.json"

-- 点灯の段取り(秒, 明るさ)。放電で何度か瞬いてから点く。
-- ★イージングは掛けない。段付きのまま = 機械が点いているだけの見え方にする。
local STRIKE = {
    { 0.00, 0.00 },
    { 0.05, 0.85 },
    { 0.09, 0.04 },
    { 0.26, 0.55 },
    { 0.31, 0.02 },
    { 0.55, 0.95 },
    { 0.61, 0.18 },
    { 0.72, 0.80 },
    { 0.82, 1.00 },
}

local T_STRIKE = 0.35        -- 暗いまま待つ時間
local T_HOLD   = 1.10        -- 点き切ってから走り出すまで
local T_SWEEP  = 0.60        -- 横線になって走る
-- ★★1 本の線で静止している時間。0.55 → 1.60 に伸ばした。
--   見せ場としてここが一番効く所でもあるが、実利の方が大きい ── タイトルの
--   起動時に本編を先読みしてあるとはいえ、取りこぼしがあれば幕の途中で読み込みが
--   走って固まる。【絵が動いていない静止の間】を長く取っておけば、そこで
--   読み終わる余地ができるし、仮に止まってもただの静止画に見える。
local T_LINE   = 1.60        -- 1 本の線のまま静止する(ここが「線一つ」の見せ場)
local T_TURN   = 0.45        -- 横線が中心へ引き、縦の継ぎ目が立つ
local T_OPEN   = 1.80        -- カーテンの「閉じる → 開く」の合計秒

-- 節目の時刻(足し算を 1 か所にまとめる)
local TS0 = T_STRIKE + T_HOLD              -- 走り出し
local TS1 = TS0 + T_SWEEP                  -- 走り終わり = 1 本の線になった
local TL1 = TS1 + T_LINE                   -- 静止おわり
local TT1 = TL1 + T_TURN                   -- 継ぎ目が立った = ここで開き始める

local GOLD_W = { 0.90, 0.94, 0.90 }        -- 蛍光灯の白(わずかに緑)
local SEAM   = { 1.00, 0.86, 0.58 }        -- 継ぎ目の色。幕の合わせ目の暖色に寄せてある

-- 題名曲(title.mp3)はタイトルから鳴りっぱなしでここへ来る。
-- ★本編まで持ち込むと台無しになるので、ここで消す。消し方は【幕が閉じるのと同じ速さ】。
--   線が縦の継ぎ目になり、幕が中央で合わさり切ったとき、ちょうど無音になる。
--   そのあと幕が開いて本編が出る = 本編は静けさから始まる。
-- ★このスクリプトはシーンが入れ替わった時点で消えるので、下げ切る前に途切れる可能性がある。
--   最後の止めは本編側(StageMusic.lua の OnStart の stopBGM)が受け持っている。
-- ★BGM の音量つまみは全体に効く。0 にしたまま置いていくので、
--   タイトル側(TitleMenu.lua)と本編側で必ず戻すこと。
local BGM_VOL  = 0.55                      -- TitleMenu.lua の TITLE_VOL と同じ値にすること
local BGM_FADE = 0.90                      -- 消えるまでの秒数(= T_OPEN の閉じる半分)

local function clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end

local function strikeLevel(t)
    local v = 0
    for i = 1, #STRIKE do
        if t >= STRIKE[i][1] then v = STRIKE[i][2] else break end
    end
    return v
end

-- 横 1 本。にじみ 2 枚を敷いてから芯を 1 枚(ぼかしが無いので枚数で代用する)
local function hrule(cx, cy, half, h, c, a)
    if a <= 0.002 or half <= 0.5 then return end
    ui:rect(cx - half - 10, cy - h * 3.4, half * 2 + 20, h * 6.8, c[1], c[2], c[3], a * 0.05, 0)
    ui:rect(cx - half - 4,  cy - h * 1.8, half * 2 + 8,  h * 3.6, c[1], c[2], c[3], a * 0.09, 0)
    ui:rect(cx - half,      cy - h * 0.5, half * 2,      h,       c[1], c[2], c[3], a * 0.92, 0)
end

-- 縦 1 本。横のものを 90 度倒しただけ(同じ線に見せたいので作りも同じにする)
local function vrule(cx, cy, half, w, c, a)
    if a <= 0.002 or half <= 0.5 then return end
    ui:rect(cx - w * 3.4, cy - half - 10, w * 6.8, half * 2 + 20, c[1], c[2], c[3], a * 0.05, 0)
    ui:rect(cx - w * 1.8, cy - half - 4,  w * 3.6, half * 2 + 8,  c[1], c[2], c[3], a * 0.09, 0)
    ui:rect(cx - w * 0.5, cy - half,      w,       half * 2,      c[1], c[2], c[3], a * 0.92, 0)
end

function OnStart(self)
    self.time  = 0
    self.moved = false
    input:setMouseCapture(false)
    -- 中立値のまま。★brightness は加算で中立 0.0（1.0 を入れると真っ白に飛ぶ）
    post.setMany{
        dofOn = false,
        vignetteOn = false,
        grainOn = false,
        brightnessOn = false,
        contrastOn = false,
        saturationOn = false,
        exposureOn = true, exposure = 1.0,
    }
    -- ★★2026-09-09「タイトルからシーン遷移するとき画面フリーズする」の【本体】。
    --   ここに preloadScene(NEXT) があった。OnStart は【この画面が 1 フレームも
    --   描かれる前】に走るので、読み込みの十数秒はまるごと「タイトルの絵のまま
    --   固まっている」時間になっていた。Windows に「応答していません」と
    --   言われるのも当然で、遊ぶ側からは完全にハングに見える。
    --   ★読み込みは OnUpdate 側へ移した。ロード画面を先に出し切ってから読む。
    self.prog   = 0.0      -- 表示している進み具合 0..1
    self.step   = 0        -- 済んだ工程の数
    self.frames = 0
end

-- 工程表。{ ここまで進んだと見せる割合, その工程でやること }
-- ★重い呼び出しの【前に必ず 1 枚描いて出す】ことだけが肝。描き終えたフレームが
--   画面に出てから止まれば、遊ぶ側には「読み込み中に止まっている」＝正常に見える。
--   出る前に止まると「前の絵のまま固まった」＝故障に見える。同じ待ち時間でも別物。
local STEPS = {
    { 0.10, nil },                                      -- まずロード画面を出し切る
    { 0.20, nil },                                      -- もう 1 枚。確実に出す
    { 0.85, function() preloadScene(NEXT) end },        -- ここが重い(十数秒)
    { 1.00, nil },                                      -- 100% を 1 枚出してから開く
}

function OnUpdate(self, dt)
    self.time = self.time + dt
    local t = self.time
    local cx, cy = SCREEN_W * 0.5, SCREEN_H * 0.5

    -- 地の黒。ここから下に何もない = 余白しかない画面
    ui:rect(0, 0, SCREEN_W, SCREEN_H, 0.005, 0.006, 0.006, 1, 0)

    -- ---------------------------------------------------------- 読み込みの帯
    -- ★飾らない。ユーザーの指示は「100% まで行くやつ。とくにこだわらなくていい」。
    --   この画面だけは【文字を出さない】規則の外に置く。作品の中ではなく、
    --   起動を待たせている間の機械の表示なので、数字が出ている方が正しい。
    self.frames = self.frames + 1
    -- 帯は目標値へ滑らかに寄せる(工程は飛び飛びに進むので、そのままだと段になる)
    local goal = (self.step > 0) and STEPS[self.step][1] or 0.0
    self.prog = self.prog + (goal - self.prog) * math.min(1.0, dt * 6.0)

    -- ★読み終わったら帯は速やかに消す。ここから先は「線 1 本」の見せ場なので、
    --   数字が残っていると台無しになる。
    local ba = self.t0 and clamp(1 - (self.time - self.t0) / 0.35, 0, 1) or 1.0
    if ba > 0.002 then
        local bw, bh = SCREEN_W * 0.26, 2.0
        local bx, by = cx - bw * 0.5, SCREEN_H * 0.80
        ui:rect(bx, by, bw, bh, 0.22, 0.22, 0.21, ba, 0)                          -- 溝
        ui:rect(bx, by, bw * self.prog, bh, SEAM[1], SEAM[2], SEAM[3], ba * 0.95, 0)
        ui:text(bx + bw + 14, by - 7, string.format("%3d%%", math.floor(self.prog * 100 + 0.5)),
                13, SEAM[1], SEAM[2], SEAM[3], ba * 0.62)
    end

    -- ★工程は 1 フレームに 1 つだけ進める。重い呼び出しの前に必ず描画が出る。
    if self.step < #STEPS then
        self.step = self.step + 1
        local fn = STEPS[self.step][2]
        if fn then pcall(fn) end
        if self.step < #STEPS then return end   -- 読み込みが終わるまで演出は始めない
    end
    if self.prog < 0.999 then return end        -- 100% を出し切ってから演出へ
    t = t - (self.t0 or 0.0)
    if not self.t0 then self.t0 = self.time; t = 0.0 end

    -- 蛍光灯 1 本ぶんの明るさ
    local lit = strikeLevel(t - T_STRIKE)
    -- 点いたあとの細かい唸り。目には「安定していない」としか見えない程度
    if t - T_STRIKE > 0.82 then
        lit = lit * (0.96 + math.abs(math.sin(t * 43.0)) * 0.04)
    end

    -- 走り: 横幅が画面いっぱいまで伸び、同時に厚みが 1 本の線まで痩せる
    local sweep = clamp((t - TS0) / T_SWEEP, 0, 1)
    -- 引き: 両端が中心へ戻り、入れ替わりに縦の継ぎ目が立ち上がる
    local turn  = clamp((t - TL1) / T_TURN, 0, 1)

    local halfW = SCREEN_W * (0.21 + 0.29 * sweep) * (1 - turn) * (1 - turn)
    local h     = 4.0 - 2.6 * sweep                  -- 4px → 1.4px
    hrule(cx, cy, halfW, h, GOLD_W, lit)

    -- 幕が閉じ切るまで継ぎ目を出しておく。閉じ切った先はエンジン側の
    -- 合わせ目の光が同じ位置を引き継ぐので、こちらはそこで消えてよい。
    local seamA = lit * turn
    if self.moved then
        seamA = seamA * clamp(1 - (t - TT1) / (T_OPEN * 0.5), 0, 1)
        -- 題名曲も継ぎ目と一緒に引く(同じ時計・同じ長さ。絵と音を別々に動かさない)
        pcall(function() audio:setBGMVolume(BGM_VOL * clamp(1 - (t - TT1) / BGM_FADE, 0, 1)) end)
    end
    -- 立ち上がりは速く、最後だけ詰める(機械が「カチ」と噛み合う速さ)
    local grow = turn ^ 0.6
    vrule(cx, cy, SCREEN_H * 0.5 * grow, 3.0, SEAM, seamA)

    if not self.moved and t >= TT1 then
        self.moved = true            -- ★毎フレーム呼ばないよう 1 回で閉じる
        -- 型は文字列 ID で渡す(番号は enum 直結で覚えられない)。
        -- 使える ID は dx12 の renderer/TransitionPresets.h にある。
        if type(transitionToScene) == "function" then
            transitionToScene(NEXT, "curtain", T_OPEN)
        else
            loadScene(NEXT)          -- 万一この口が無い版でも本編へは行けるように
        end
    end
end
