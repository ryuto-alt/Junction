// @group 水
// ============================================================================
// OceanPro.hlsl — 外洋。物理から出した波と、折り畳みから出した白波
//
// テンプレの Ocean.hlsl との違いは「式が現象から来ていること」。
//   ・波長ごとの速度を深水波の分散関係 ω=sqrt(gk) で決める
//     → 長いうねりが速く、細波が遅い。手打ち速度の「全部が同じ速さで流れる」感が消える
//   ・法線を【ピクセルごとに解析微分で作り直す】(∂P/∂x × ∂P/∂z)
//     → 頂点法線の補間をやめたので、三角形の折れ目＝稜線のギザギザが出ない
//   ・白波を「峰」ではなくヤコビアン（水平変位による面の圧縮率）で判定
//     → 波が尖って潰れる場所にだけ泡が乗る。峰判定のような縞にならない
//   ・空の反射をエンジンの手続きスカイと同じ式で作る
//     （dx12 本体 src/core/ApplicationScene.cpp の ProceduralSkySample と一対一）
//     → 水平線で背景と反射の色が一致し、境目そのものが消える
//
// ■ 帯域の分け方（ここが絵の綺麗さを決めている）
//   頂点で動かすのは kSwell（波長 14m 以上）だけ。それより短い波を頂点で動かすと、
//   頂点間隔（size/subdiv）で標本化しきれず、波の稜線が階段になる。【実際にそうなった】
//   短い波は kRipple として PS で法線にだけ足す。位置は動かないが、
//   海の細かさは全部法線が担っているので見た目は落ちない。
//   さらに各波は「そのピクセルが海面に落とす足跡」より短くなったら寄与を切る＝
//   遠景で解像できない帯域が消え、チリチリしたエイリアスが原理的に出ない。
//
// ■ 使い方
//   1. 平面を size 1600 / subdivisions 600 程度で置く（頂点間隔が kSwell 最短波長の
//      1/4 以下＝約 3.5m 以下になっていること）
//   2. Shader にこれを割り当てる。アルファブレンドは OFF のまま（海は不透明）
//   3. Skybox は __procedural_sky__ のまま使う。差し替えたら SkyProcedural() も直すこと
//
// ■ パラメータ
//   effectValue      @range(0,1)   海況（0=凪、0.5=そこそこ、1=時化）。波高・白波・粗さが連動
//   shaderParams.x   @range(0.3,3) うねりの規模（小さいほど波長が長い＝広い外洋）
//   shaderParams.y   @range(0,2)   時間の速さ（1=実時間）
//   shaderParams.z   @range(0,2)   大気の霞（水平線の溶かし方）
//   shaderParams.w   @range(0,2)   白波の量
//   shaderParamsB.x  @range(0,360) 風向（度）。うねりの向きが全部これを基準に回る
//   shaderParamsB.y  @range(0,1)   水の色（0=外洋の紺、1=沿岸のエメラルド）
//   shaderParamsB.z  @range(0,3)   太陽の道（サングリッター）の強さ
//
// ■ 既知の割り切り
//   屈折で背後を歪ませることはできない（カスタムシェーダーから深度もシーン色も読めない）。
//   海底が透けるべき浅瀬は Water.hlsl の担当。
// ============================================================================
#include "UnoCustom.hlsli"

static const float kPI      = 3.14159265359;
static const float kGravity = 9.81;

// 頂点で動かすうねり。x=波長(m) / y=振幅(m, 海況 0.5 基準) / z=風向からの角度(度)
// ★波長は約 1.6 倍ずつ離す。整数倍で並べると干渉が周期的になり、
//   海面に「同じ模様の格子」が見えてしまう。
// ★最短を 14m で止めているのは頂点間隔の都合（上の「帯域の分け方」参照）。
static const float3 kSwell[4] = {
    float3( 96.0, 1.900, -12.0),
    float3( 59.0, 1.250,  22.0),
    float3( 37.0, 0.820, -33.0),
    float3( 23.0, 0.520,  41.0)
};

// PS で法線にだけ足す短波。位置は動かさないので頂点密度と無関係。
// 向きは主風向の ±90° 以内に散らす（風下に立たない波は実際には育たない）。
static const float3 kRipple[9] = {
    float3(14.20, 0.5300, -52.0),
    float3( 8.80, 0.2000,  52.0),
    float3( 5.40, 0.1150, -61.0),
    float3( 3.30, 0.0640,  30.0),
    float3( 2.05, 0.0330, -78.0),
    float3( 1.27, 0.0185,  67.0),
    float3( 0.79, 0.0100, -41.0),
    float3( 0.49, 0.0055,  85.0),
    float3( 0.30, 0.0029, -25.0)
};

static const float3 kOpenWater = float3(0.0021, 0.0092, 0.0225);  // 外洋の紺
static const float3 kCoastal   = float3(0.0180, 0.0900, 0.0880);  // 沿岸のエメラルド
static const float3 kSssColor  = float3(0.060, 0.290, 0.235);     // 波が透けるときの緑
static const float3 kFoamColor = float3(0.760, 0.820, 0.865);

// ---------------------------------------------------------------------------
// パラメータ。0 のままでも成立する既定値を持たせる（未設定でいきなり凪にしない）
// ---------------------------------------------------------------------------
struct OceanParams
{
    float  sea;         // 海況 0..1
    float  lenScale;    // 波長の割り算。大きいほど小さい海
    float  ampScale;    // 海況から出した振幅倍率
    float  speed;
    float  haze;
    float  foam;
    float2 wind;
    float  turbidity;
    float  glitter;
    float  swellHeight; // 目安の波高(m)。SSS のマスクに使う
};

OceanParams GetOceanParams()
{
    OceanParams p;
    p.sea       = saturate(effectValue <= 0.0 ? 0.50 : effectValue);
    p.lenScale  = shaderParams.x  <= 0.0 ? 1.0 : shaderParams.x;
    p.speed     = shaderParams.y  <= 0.0 ? 1.0 : shaderParams.y;
    p.haze      = shaderParams.z  <= 0.0 ? 1.0 : shaderParams.z;
    p.foam      = shaderParams.w  <= 0.0 ? 1.0 : shaderParams.w;
    p.turbidity = saturate(shaderParamsB.y);
    p.glitter   = shaderParamsB.z <= 0.0 ? 1.0 : shaderParamsB.z;

    const float a = radians(shaderParamsB.x);
    p.wind = float2(cos(a), sin(a));

    // 海況→振幅。sqrt で立ち上げると、0.5 付近（いちばん使う帯）の分解能が上がる。
    p.ampScale    = lerp(0.10, 1.30, sqrt(p.sea));
    p.swellHeight = 4.49 * p.ampScale / p.lenScale;  // kSwell の振幅合計 × 倍率
    return p;
}

float2 RotateDir(float2 base, float degrees)
{
    const float a = radians(degrees);
    const float s = sin(a), c = cos(a);
    return float2(base.x * c - base.y * s, base.x * s + base.y * c);
}

// ---------------------------------------------------------------------------
// ゲルストナー合成。変位と一緒に ∂P/∂x, ∂P/∂z を貯める。
//   法線   = cross(dPdz, dPdx)
//   泡     = det([dPdx.xz, dPdz.xz])  ＝ 面がどれだけ圧縮されたか（ヤコビアン）
// どちらもこの 2 本のベクトルから出るので、微分を別に取り直す必要がない。
//
//   footprint > 0 なら、そのピクセルが解像できない波長を落とす（PS 用）。
//   VS は変位が要るので 0 を渡して全帯域を使う。
// ---------------------------------------------------------------------------
struct OceanSurface
{
    float3 disp;
    float3 dPdx;
    float3 dPdz;
};

OceanSurface EvalSwell(float2 p, OceanParams pr, float t, float footprint)
{
    OceanSurface s;
    s.disp = float3(0, 0, 0);
    s.dPdx = float3(1, 0, 0);   // 平らなときの接ベクトル。ここに波の寄与を足していく
    s.dPdz = float3(0, 0, 1);

    // うねりの位相を非常に緩いノイズでずらす。直線の稜線が蛇行して、定規で引いた
    // ような波の列にならない。空間周波数が低いので法線への影響は無視できる。
    // ★ここを値ノイズでやると、格子セル（数百 m）の継ぎ目が矩形の段差として
    //   海面に出る【実際に出た】。低周波の正弦を重ねれば滑らかに繋がる。
    const float swellJitter = sin(dot(p, float2( 0.0091, 0.0063)) + t * 0.031) * 2.2
                            + sin(dot(p, float2(-0.0052, 0.0117)) - t * 0.019) * 1.6;

    // 波群（七つ波）。実際の海は波が束で来て、束と束の間は凪ぐ。
    // これが無いと同じ大きさの波が一面に並び、それだけで CG に見える。
    // 波群は本来「近い波長どうしの干渉」なので、正弦の重ね合わせで作るのが素直。
    const float2 gdA   = RotateDir(pr.wind,   9.0);
    const float2 gdB   = RotateDir(pr.wind, -37.0);
    const float  group = 0.72 + 0.32 * (sin(dot(gdA, p) * 0.0121 - t * 0.10) * 0.55
                                      + sin(dot(gdB, p) * 0.0074 - t * 0.07) * 0.45);

    [unroll]
    for (int i = 0; i < 4; ++i)
    {
        const float L = kSwell[i].x / pr.lenScale;
        const float w = (footprint <= 0.0) ? 1.0 : saturate(1.0 - footprint / (L * 0.75));
        if (w <= 0.0)
            continue;

        const float  A = kSwell[i].y * pr.ampScale * group / pr.lenScale;  // 波長を縮めたら振幅も。傾斜を保つ
        const float2 d = RotateDir(pr.wind, kSwell[i].z);

        const float k  = 6.283185307 / L;
        const float om = sqrt(kGravity * k);     // 深水波の分散関係。長い波ほど速い
        const float Q  = min(A * k, 0.92) * w;   // steepness。1 を超えると波が自分と交差する
        const float a  = Q / k;

        const float f = k * dot(d, p) - om * t + float(i) * 1.7 + swellJitter;  // 位相をずらして周期性を殺す
        float sn, cs;
        sincos(f, sn, cs);

        s.disp += float3(d.x * a * cs, a * sn, d.y * a * cs);
        s.dPdx += float3(-d.x * d.x * Q * sn, d.x * Q * cs, -d.x * d.y * Q * sn);
        s.dPdz += float3(-d.x * d.y * Q * sn, d.y * Q * cs, -d.y * d.y * Q * sn);
    }
    return s;
}

// 短波の勾配（∂h/∂x, ∂h/∂z）。変位しないので高さ場として扱う。
float2 RippleGradient(float2 p, OceanParams pr, float t, float footprint)
{
    // 位相を緩いノイズで乱す。乱さないと短波だけが定規で引いた縞に見える。
    const float jitter = sin(dot(p, float2( 0.071,  0.049))) * 3.0
                       + sin(dot(p, float2(-0.038,  0.086))) * 2.2
                       + sin(dot(p, float2( 0.152, -0.113))) * 1.4;
    const float amp    = 0.15 + 0.45 * pr.sea;

    float2 g = float2(0, 0);
    [unroll]
    for (int i = 0; i < 9; ++i)
    {
        const float L = kRipple[i].x / pr.lenScale;
        const float w = saturate(1.0 - footprint / (L * 0.75));
        if (w <= 0.0)
            continue;

        const float  A  = kRipple[i].y * amp / pr.lenScale;
        const float2 d  = RotateDir(pr.wind, kRipple[i].z);
        const float  k  = 6.283185307 / L;
        const float  om = sqrt(kGravity * k);
        const float  f  = k * dot(d, p) - om * t + jitter + float(i) * 2.3;

        g += d * (A * k * cos(f)) * w;
    }
    return g;
}

// ---------------------------------------------------------------------------
// 空。dx12 本体の ProceduralSkySample と同じ式（表示基準の色を最後にリニアへ）。
// ★ここを勝手に「それっぽい色」にすると、水平線で背景の空と反射の色が食い違い、
//   海と空の境に一本の線が出る。合わせてあることが水平線の説得力そのもの。
// ---------------------------------------------------------------------------
float3 SkyProcedural(float3 dir)
{
    const float3 zenith  = float3(0.29, 0.48, 0.80);
    const float3 horizon = float3(0.80, 0.86, 0.93);
    const float3 ground  = float3(0.33, 0.32, 0.31);

    float3 c;
    if (dir.y >= 0.0)
    {
        c = lerp(horizon, zenith, pow(saturate(dir.y), 0.45));
    }
    else
    {
        const float t = saturate(-dir.y / 0.35);
        c = lerp(horizon, ground, t * t * (3.0 - 2.0 * t));
    }
    return pow(c, 2.2);
}

// 反射に使う空。手続きスカイは太陽を焼き込んでいない（IBL がちらつくため）ので、
// 反射側でだけ太陽を足す。海面で目を引くのはこの一点なので、無いと嘘に見える。
float3 SkyReflected(float3 dir, float3 sunDir, float3 tint)
{
    float3 sky = SkyProcedural(dir);
    const float sd = saturate(dot(dir, sunDir));
    sky += tint * pow(sd, 6.0)   * 0.26;   // 太陽まわりの広いハロ
    sky += tint * pow(sd, 900.0) * 7.00;   // 本体のにじみ
    return sky;
}

// ---------------------------------------------------------------------------
struct OceanV2P
{
    float4 positionSV : SV_POSITION;
    float3 worldPos   : TEXCOORD0;
    float2 basePos    : TEXCOORD1;   // 変位する【前】の水平位置。PS の波の評価はこれを使う
};

OceanV2P VSMain(VSInput i)
{
    const OceanParams pr = GetOceanParams();

    // ★波はワールド座標で作る。ローカルで作ると板を並べたとき継ぎ目が出る。
    const float3 base = UnoLocalToWorld(i.position);
    const OceanSurface s = EvalSwell(base.xz, pr, time * pr.speed, 0.0);

    OceanV2P o;
    o.positionSV = UnoWorldToClip(base + s.disp);
    o.worldPos   = base + s.disp;
    o.basePos    = base.xz;   // 法線は PS で作り直すので、ここでは渡すだけ
    return o;
}

float4 PSMain(OceanV2P i) : SV_TARGET
{
    const OceanParams pr = GetOceanParams();

    float3 V = cameraPos - i.worldPos;
    const float dist = length(V);
    V /= max(dist, 1e-4);

    const float3 sunDir = normalize(-lightDir);   // lightDir は光が進む向き
    const float3 tint   = UnoSunTint();           // 強度を落とした「色味」だけ
    const float  t      = time * pr.speed;

    // このピクセルが海面に落とす足跡(m)。浅い角度で見るほど引き伸ばされる。
    // 波長がこれを下回った帯域は、以降どこでも寄与を切る＝エイリアスの発生源を断つ。
    const float footprint = min(dist * 0.0016 / max(abs(V.y), 0.05), 400.0);

    // --- 法線 -------------------------------------------------------------
    // ★頂点法線を補間せず、ピクセルごとに解析微分で作り直す。
    //   補間した法線は三角形の境目で折れ、波の稜線がギザギザに見える。
    const OceanSurface s = EvalSwell(i.basePos, pr, t, footprint);
    float3 N = normalize(cross(s.dPdz, s.dPdx));

    // 短波は勾配で足す。法線同士を足すより素直で、傾きの合成が正しく効く。
    float2 g = -N.xz / max(N.y, 0.15);
    g += RippleGradient(i.basePos, pr, t, footprint);
    N = normalize(float3(-g.x, 1.0, -g.y));

    // 解像しきれずに落とした凹凸は、粗さへ移して面で受ける（NDF フィルタリング）。
    const float bandLoss = saturate(footprint / 40.0);

    const float ndv   = saturate(dot(N, V));
    const float ndl   = saturate(dot(N, sunDir));
    const float rough = saturate(lerp(0.058, 0.165, pr.sea) + bandLoss * 0.32);

    // --- 反射 -------------------------------------------------------------
    float3 R = reflect(-V, N);
    R.y = max(R.y, 0.0);   // 下を向いた反射は海が海を映すことになるので地平へ寝かせる
    const float3 skyRefl = SkyReflected(R, sunDir, tint);

    // 水のフレネル。f0=0.02（屈折率 1.33）。浅い角度でほぼ 1 になるのが海らしさの芯。
    const float F = 0.02 + 0.98 * pow(1.0 - ndv, 5.0);

    // --- 水の中から返ってくる色 -------------------------------------------
    // 天頂の空色。引数が定数なので SkyProcedural を呼ばず畳んである（pow が 3 回減る）。
    const float3 ambSky   = float3(0.0674, 0.1996, 0.6096);
    const float3 waterCol = lerp(kOpenWater, kCoastal, pr.turbidity);
    float3 body = waterCol * (ambSky * 4.5 + tint * 1.0) * (0.45 + ambientStrength * 0.55);

    // 逆光で波の背が透ける（サブサーフェス）。峰ほど薄いので強く出る。
    const float3 Hs    = normalize(sunDir + N * 0.55);
    const float  back  = pow(saturate(dot(V, -Hs)), 3.5);
    const float  hMask = saturate(s.disp.y / max(pr.swellHeight, 0.25) * 1.6 + 0.30);
    body += kSssColor * (back * hMask * (0.35 + pr.sea) * 1.5) * tint;

    float3 col = lerp(body, skyRefl, F * 0.94);

    // --- 太陽の直接反射（GGX） -------------------------------------------
    // 距離で粗さが上がるので、遠くの太陽の道は自然に広がってつながる。
    const float3 H   = normalize(V + sunDir);
    const float  ndh = saturate(dot(N, H));
    const float  a   = max(rough * rough, 0.0016);
    const float  a2  = a * a;
    const float  dd  = ndh * ndh * (a2 - 1.0) + 1.0;
    const float  D   = a2 / (kPI * dd * dd);
    const float  vis = 0.5 / max(ndl * sqrt(ndv * ndv * (1.0 - a2) + a2) +
                                 ndv * sqrt(ndl * ndl * (1.0 - a2) + a2), 1e-4);
    // ★クランプしないと 1px だけ数千 nit になり、TAA 無しではその点が踊る。
    col += min(tint * (D * vis * F * ndl * pr.glitter * 4.0), 90.0);

    // --- 白波 -------------------------------------------------------------
    // 面が圧縮された（＝波が崩れている）ところにだけ乗せる。峰判定と違い縞にならない。
    // ★しきい値は渋く。緩めると海面が白いクリームになる【実際にそうなった】。
    const float J    = s.dPdx.x * s.dPdz.z - s.dPdx.z * s.dPdz.x;
    const float fold = saturate((0.45 - J) * 2.6);

    // 泡の粒。粗いのと細かいのを重ねると、白い塊ではなく筋と粒に割れる。
    const float2 fuv = i.basePos * pr.lenScale;
    const float  fnA = UnoFbm(fuv * 0.09 + pr.wind * (t * 0.04), 2);
    const float  fnB = UnoNoise(fuv * 0.62 - pr.wind * (t * 0.11));
    float foam = fold * fold * saturate(fnA * 1.5 + fnB * 0.7 - 0.35) * pr.foam * 2.2;
    foam = saturate(foam);
    foam *= 1.0 - bandLoss * 0.45;   // 遠景は粒が潰れて薄い白の帯になる

    // 泡は散乱体。鏡のようには光らないので、法線由来の艶をここで殺す。
    const float3 foamCol = kFoamColor * (ambSky * 5.0 + tint * ndl * 1.2);
    col = lerp(col, foamCol, foam);

    // --- 大気遠近 ---------------------------------------------------------
    // 視線方向の「地平線の色」へ指数で寄せる。空と同じ式から取るので水平線が溶ける。
    const float3 hazeCol = SkyProcedural(normalize(float3(-V.x, 0.015, -V.z)));
    const float  fogAmt  = 1.0 - exp(-dist * pr.haze * 0.0012);
    col = lerp(col, hazeCol, fogAmt);

    return float4(col, 1.0);   // 海は不透明。透かすと背後のグリッドが見えて薄膜になる
}
