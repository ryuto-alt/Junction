-- JUNCTION ロード画面。タイトルと本編のあいだに挟む無機質なトランジション。
--
-- 出すのは【蛍光灯が 1 本点いて、そのまま細い横線になって走り抜ける】だけ。
-- 進捗バー・スピナー・文字といった「ゲーム UI」らしい物は一切描かない。
-- 本編(stagedemo3)のアセットはタイトル側で preloadScene 済み。ここではもう一度だけ
-- 念のため予約し、決めた尺を使い切ってから読み込みへ移る。

local MIN_HOLD = 2.50        -- この秒数は必ず見せる(遷移が「事故」に見えないように)
local NEXT     = "scenes/stagedemo3.json"

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
local T_HOLD   = 1.40        -- 点き切ってから走り出すまで
local T_SWEEP  = 0.60        -- 横線になって走る
local T_OUT    = 0.40        -- 消える

local function clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end

local function strikeLevel(t)
    local v = 0
    for i = 1, #STRIKE do
        if t >= STRIKE[i][1] then v = STRIKE[i][2] else break end
    end
    return v
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
    preloadScene(NEXT)
end

function OnUpdate(self, dt)
    self.time = self.time + dt
    local t = self.time

    -- 地の黒。ここから下に何もない = 余白しかない画面
    ui:rect(0, 0, SCREEN_W, SCREEN_H, 0.005, 0.006, 0.006, 1, 0)

    -- 蛍光灯 1 本ぶんの明るさ
    local lit = strikeLevel(t - T_STRIKE)
    -- 点いたあとの細かい唸り。目には「安定していない」としか見えない程度
    if t - T_STRIKE > 0.82 then
        lit = lit * (0.96 + math.abs(math.sin(t * 43.0)) * 0.04)
    end

    -- 走り: 横幅が画面いっぱいまで伸び、同時に厚みが 1 本の線まで痩せる
    local sweep = clamp((t - (T_STRIKE + T_HOLD)) / T_SWEEP, 0, 1)
    local fade  = 1 - clamp((t - (T_STRIKE + T_HOLD + T_SWEEP)) / T_OUT, 0, 1)

    local halfW = SCREEN_W * (0.21 + 0.29 * sweep)   -- 0.42 幅 → 画面いっぱい
    local h     = 4.0 - 2.6 * sweep                  -- 4px → 1.4px
    local cx, cy = SCREEN_W * 0.5, SCREEN_H * 0.5
    local a = lit * fade

    if a > 0.001 then
        -- 管のまわりの弱いにじみ。3 枚だけ、ぼかしの代わり
        ui:rect(cx - halfW - 10, cy - h * 3.4, halfW * 2 + 20, h * 6.8, 0.72, 0.78, 0.74, a * 0.05, 0)
        ui:rect(cx - halfW - 4,  cy - h * 1.8, halfW * 2 + 8,  h * 3.6, 0.78, 0.83, 0.79, a * 0.09, 0)
        -- 管そのもの
        ui:rect(cx - halfW, cy - h * 0.5, halfW * 2, h, 0.90, 0.94, 0.90, a * 0.92, 0)
    end

    if not self.moved and t >= MIN_HOLD then
        self.moved = true            -- ★毎フレーム呼ばないよう 1 回で閉じる
        loadScene(NEXT)
    end
end
