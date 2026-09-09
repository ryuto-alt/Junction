-- JUNCTION ロード画面。タイトルと本編のあいだに挟む無機質なトランジション。
--
-- 出すのは【線 1 本】と、下に置いた細い読み込みの帯だけ。スピナーや飾り文字は描かない。
--
--   蛍光灯が 1 本点く
--     → その 1 本が【読み込みの進み具合ぶんだけ】横へ伸びる  ← ここが読み込み中
--     → 読み終わって画面幅いっぱいの細い線になり、静止する    ← 「線一つになった」状態
--     → 両端が中心へ引き、代わりに中心に【縦の継ぎ目】が立ち上がる
--     → その継ぎ目から画面が左右へ開き、隙間の向こうに本編が現れる
--
-- ★★2026-09-09【非同期化】。それまでの作りはこうなっていた:
--     工程表を 1 フレームに 1 つずつ進め、3 番目で preloadScene(NEXT) を呼ぶ。
--   preloadScene は【同期】＝参照アセットを 1 フレームで全部読み終わるまで戻ってこない。
--   その十数秒はメッセージポンプごと止まるので、
--     ・帯は 20% で止まったまま動かない（描いても Present されない）
--     ・絵も止まる。Windows は「応答していません」を出す
--     ・読み終わった瞬間に 85% へ飛ぶ
--   という、遊ぶ側からは完全なハングにしか見えない画面になっていた。
--   エンジンに preloadSceneAsync / scenePreloadProgress を足して直してある
--   （1 フレーム 10ms ずつしか読まないので、読んでいる間も OnUpdate と描画が回る）。
--   ★同期版の preloadScene も互換のため残っているが、この画面からは絶対に呼ばないこと。
--
-- ★★2026-09-09 の別の罠（こちらは残っている地雷）:
--   preloadScene を【OnStart に置くと】この画面が 1 フレームも描かれる前に十数秒止まり、
--   「タイトルの絵のまま固まる」になる。非同期版でも読み始めは OnUpdate に置く。
--   肝は今も同じ ──【重い呼び出しの前に必ず 1 枚描いて出す】。
--   描き終えたフレームが画面に出てから止まれば「読み込み中に止まっている」＝正常に見え、
--   出る前に止まると「前の絵のまま固まった」＝故障に見える。同じ待ち時間でも別物。
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
local T_HOLD   = 1.10        -- 点き切ってから伸び始めるまで
local T_SWEEP  = 0.60        -- 横へ伸びるのに【最低でも】かける時間
-- ★★1 本の線で静止している時間。1.60 → 0.85 に戻した。
--   1.60 まで伸ばしてあったのは「先読みの取りこぼしがあれば、この静止のあいだに
--   読み終わってくれ」という保険だった。読み込みが非同期になり、伸び切る条件が
--   【進捗 100%】そのものになったので、この保険は要らない（読み終わっていなければ
--   線はまだ伸び切っていない）。長い静止はただの待ち時間なので短くする。
local T_LINE   = 0.85        -- 1 本の線のまま静止する(ここが「線一つ」の見せ場)
local T_TURN   = 0.45        -- 横線が中心へ引き、縦の継ぎ目が立つ
local T_OPEN   = 1.80        -- カーテンの「閉じる → 開く」の合計秒

-- 伸び切ってからの節目(self.t1 からの相対秒)。足し算を 1 か所にまとめる。
local U_TURN = T_LINE                 -- 引き始め
local U_OPEN = T_LINE + T_TURN        -- 継ぎ目が立った = ここで開き始める

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

-- エンジンに非同期先読みの口があるか。無い版でも本編へは行けるようにしておく。
local ASYNC = (type(preloadSceneAsync)   == "function")
          and (type(scenePreloadProgress) == "function")

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

-- 線の上を往復する明るい節。★これが「読み込み中も絵が動いている」の担当。
--   進捗は 1 件ずつしか進まないので、重いアセットに当たると帯は数フレーム止まる。
--   そのあいだも【必ず動いている物】を 1 つ置いておかないと、また「固まった」に見える。
--   時計は self.time なので、進捗が止まっていても動き続ける。
local function scanner(cx, cy, half, h, c, a, phase)
    if a <= 0.002 or half <= 2.0 then return end
    local w    = math.max(12.0, half * 0.14)
    local span = math.max(0.0, half * 2 - w)
    local x    = cx - half + w * 0.5 + span * phase
    ui:rect(x - w * 0.5, cy - h * 2.4, w, h * 4.8, c[1], c[2], c[3], a * 0.10, 0)
    ui:rect(x - w * 0.5, cy - h * 0.5, w, h,       c[1], c[2], c[3], a * 0.80, 0)
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
    -- ★読み込みは OnUpdate 側。ここに置くと 1 フレームも描かれないまま止まる(冒頭参照)。
    self.frames = 0
    self.raw    = 0.0      -- エンジンが返した進捗(0..1)。単調増加させる
    self.prog   = 0.0      -- 表示している進み具合(rawへ寄せる)
    self.mark   = -1       -- ログに出した 10% 刻みの段
    -- 読み込み中のフレームごとの実測値。読み終わりに 1 行だけ吐く。
    -- ★「滑らかに動いていた」を目で判断すると、動いているつもりで通してしまう。
    --   1 フレームごとの数字が残っていれば、刻まれたのか一段で飛んだのか一目で分かる。
    self.trace  = {}
end

function OnUpdate(self, dt)
    self.time = self.time + dt
    local t = self.time
    local cx, cy = SCREEN_W * 0.5, SCREEN_H * 0.5

    -- 地の黒。ここから下に何もない = 余白しかない画面
    ui:rect(0, 0, SCREEN_W, SCREEN_H, 0.005, 0.006, 0.006, 1, 0)

    -- ------------------------------------------------------------ 読み込み
    -- ★1 フレーム目は【描くだけ】。2 フレーム目から読み始める。
    --   preloadSceneAsync 自体は要求を積むだけで軽いが、エンジンはその次のフレームで
    --   シーン JSON(1.4MB)の走査に入る。ロード画面を先に 1 枚出し切ってからにする。
    self.frames = self.frames + 1
    if self.frames >= 2 and not self.started then
        self.started = true
        self.tReq    = self.time
        if ASYNC then
            -- 毎フレーム呼んでも安全だが、1 回で足りるので 1 回だけ呼ぶ
            preloadSceneAsync(NEXT)
        else
            -- 非同期の口が無い版。ここは固まるが、少なくとも本編へは行ける
            pcall(function() preloadScene(NEXT) end)
            self.raw = 1.0
        end
    end

    if self.started and ASYNC then
        -- ★エンジンは「未要求」と「完了」のどちらでも 1 を返す。要求済みでしか読まない、
        --   かつ単調増加させることで、取りこぼしても帯が巻き戻らないようにする。
        self.raw = math.max(self.raw, scenePreloadProgress())
    end

    -- 帯は目標値へ滑らかに寄せる(1 件ずつ進むので、そのままだと段になる)
    self.prog = self.prog + (self.raw - self.prog) * math.min(1.0, dt * 6.0)
    if self.raw >= 1.0 and self.prog > 0.995 then self.prog = 1.0 end
    if self.prog >= 1.0 and not self.tFull then self.tFull = self.time end

    -- 10% 刻みでログに残す。★見た目だけだと「動いているつもり」で通してしまうので、
    --   実測が本当に進んでいるかは必ずここで確かめること(dx12_get_log で拾える)。
    local mark = math.floor(self.raw * 10)
    if mark > self.mark then
        self.mark = mark
        local cur = (type(scenePreloadCurrent) == "function") and scenePreloadCurrent() or ""
        log(string.format("LoadingScreen: %3d%%  t=%.2fs  %s",
                          mark * 10, self.time - (self.tReq or 0), cur or ""))
    end
    -- フレームごとの実測値を溜める(読み込みが終わるまで。上限つき)
    if self.started and not self.traceDone and #self.trace < 400 then
        self.trace[#self.trace + 1] = math.floor(self.raw * 100 + 0.5)
        if self.raw >= 1.0 then
            self.traceDone = true
            log("LoadingScreen trace(%/frame): " .. table.concat(self.trace, ","))
        end
    end

    -- ---------------------------------------------------------- 読み込みの帯
    -- ★飾らない。ユーザーの指示は「100% まで行くやつ。とくにこだわらなくていい」。
    --   この画面だけは【文字を出さない】規則の外に置く。作品の中ではなく、
    --   起動を待たせている間の機械の表示なので、数字が出ている方が正しい。
    -- ★100% を出し切ってから消す。tFull(=表示が 100% に届いた時刻)から引くので、
    --   「87% のまま消えた」にはならない。
    local ba = self.tFull and clamp(1 - (self.time - self.tFull) / 0.35, 0, 1) or 1.0
    if ba > 0.002 then
        local bw, bh = SCREEN_W * 0.26, 2.0
        local bx, by = cx - bw * 0.5, SCREEN_H * 0.80
        ui:rect(bx, by, bw, bh, 0.22, 0.22, 0.21, ba, 0)                          -- 溝
        ui:rect(bx, by, bw * self.prog, bh, SEAM[1], SEAM[2], SEAM[3], ba * 0.95, 0)
        ui:text(bx + bw + 14, by - 7, string.format("%3d%%", math.floor(self.prog * 100 + 0.5)),
                13, SEAM[1], SEAM[2], SEAM[3], ba * 0.62)
    end

    -- ------------------------------------------------------------ 蛍光灯
    -- 蛍光灯 1 本ぶんの明るさ
    local lit = strikeLevel(t - T_STRIKE)
    -- 点いたあとの細かい唸り。目には「安定していない」としか見えない程度
    if t - T_STRIKE > 0.82 then
        lit = lit * (0.96 + math.abs(math.sin(t * 43.0)) * 0.04)
    end

    -- 伸び: 横幅が画面いっぱいまで伸び、同時に厚みが 1 本の線まで痩せる。
    -- ★伸びる量は【進捗そのもの】。ただし読み込みが一瞬で終わっても線が瞬間移動しないよう、
    --   時間の傾斜でも頭を押さえる(min)。どちらか遅い方に律速される。
    local ramp  = clamp((t - (T_STRIKE + T_HOLD)) / T_SWEEP, 0, 1)
    local sweep = math.min(self.prog, ramp)
    -- 引き: 両端が中心へ戻り、入れ替わりに縦の継ぎ目が立ち上がる
    local u     = self.t1 and (self.time - self.t1) or -1.0
    local turn  = (u >= 0) and clamp((u - U_TURN) / T_TURN, 0, 1) or 0.0

    local halfW = SCREEN_W * (0.21 + 0.29 * sweep) * (1 - turn) * (1 - turn)
    local h     = 4.0 - 2.6 * sweep                  -- 4px → 1.4px
    hrule(cx, cy, halfW, h, GOLD_W, lit)

    -- 読み込み中だけ、線の上を明るい節が往復する(進捗が止まっても絵は動き続ける)
    if not self.t1 then
        local ph = math.abs(((t * 0.62) % 2.0) - 1.0)      -- 0→1→0 の往復
        scanner(cx, cy, halfW, h, GOLD_W, lit * 0.9, ph)
    end

    -- 伸び切った瞬間を覚える。ここから先は今までどおりの固定の段取り。
    -- ★sweep は self.prog に律速されるので、ここへ来た時点で表示は必ず 100%。
    if not self.t1 and sweep >= 0.999 and lit > 0.5 then
        self.t1 = self.time
    end
    if not self.t1 then return end

    -- 幕が閉じ切るまで継ぎ目を出しておく。閉じ切った先はエンジン側の
    -- 合わせ目の光が同じ位置を引き継ぐので、こちらはそこで消えてよい。
    local seamA = lit * turn
    if self.moved then
        seamA = seamA * clamp(1 - (u - U_OPEN) / (T_OPEN * 0.5), 0, 1)
        -- 題名曲も継ぎ目と一緒に引く(同じ時計・同じ長さ。絵と音を別々に動かさない)
        pcall(function() audio:setBGMVolume(BGM_VOL * clamp(1 - (u - U_OPEN) / BGM_FADE, 0, 1)) end)
    end
    -- 立ち上がりは速く、最後だけ詰める(機械が「カチ」と噛み合う速さ)
    local grow = turn ^ 0.6
    vrule(cx, cy, SCREEN_H * 0.5 * grow, 3.0, SEAM, seamA)

    if not self.moved and u >= U_OPEN then
        self.moved = true            -- ★毎フレーム呼ばないよう 1 回で閉じる
        log(string.format("LoadingScreen: 本編へ (読み込み %.2fs / 画面ぜんぶで %.2fs)",
                          (self.tFull or self.time) - (self.tReq or 0), self.time))
        -- 型は文字列 ID で渡す(番号は enum 直結で覚えられない)。
        -- 使える ID は dx12 の renderer/TransitionPresets.h にある。
        if type(transitionToScene) == "function" then
            transitionToScene(NEXT, "curtain", T_OPEN)
        else
            loadScene(NEXT)          -- 万一この口が無い版でも本編へは行けるように
        end
    end
end
