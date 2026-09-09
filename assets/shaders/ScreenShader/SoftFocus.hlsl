// ===== SoftFocus ── 遠景ほどぼける被写界深度(スクリーンシェーダー) =====
//
// 画面カラー(t0)と深度(t1)を受け取り、深度が focusNear..focusFar の間で 0->1 に上がる
// ぶんだけ 3x3 のぼかしへ寄せる。手前は素通し、遠くほどぼける。
//
//   params.x = softness    ぼかしの最大の強さ(0..1)。1 で遠景が完全にぼけた絵になる
//   params.y = blurRadius  ぼかし半径(px)。3 くらいでかなり分かる
//   params.z = focusNear   ここより近い所はぼかさない(m)
//   params.w = focusFar    ここより遠い所は softness いっぱいにぼける(m)
//
// ■ 割り当て方(★Lua からは差せない)
//   このエンジンでスクリーンシェーダーを差す口は CameraComponent::screenShaderPath
//   ただ 1 つで、書けるのは (a) エディタの Inspector のカメラ欄へ .hlsl を D&D、
//   (b) シーン JSON の camera.screenShaderPath に "ScreenShader/SoftFocus.hlsl"、
//   (c) MCP の set_component の 3 つだけ。ScriptEngine.cpp の Lua バインドには
//   post / ssao はあってもスクリーンシェーダーの項目が無い(2026-09-09 時点)。
//
// ■ ★JUNCTION 本編(stagedemo3 / Liminal.lua)では【意図的に使っていない】
//   この作品は「遠くの本物の輪郭と、手前の破片の輪郭を見比べて重ねる」遊びなので、
//   遠景をぼかすと照合そのものが成立しない(昔の stage3.json は softness 0.8 /
//   radius 3 / 5m..10m で使っていた ── あの絵では解けない)。
//   さらに「遠くをぼかす」は継ぎ目 21 の blur レンズ(組み込みの dof)の持ち物で、
//   常時掛けるとあの規則の「ピントが外れた」が読めなくなる。
//   ★本編のソフトフォーカスは、像をぼかさず【明るい所だけをにじませる】
//     古典的なやり方(組み込みの bloom)で作ってある。
//     source/liminal_runtime.lua の POST_BASE 上のコメントを参照。

Texture2D    gScreen : register(t0);
Texture2D    gDepth  : register(t1);
SamplerState gLinear : register(s0);
SamplerState gPoint  : register(s1);

cbuffer ScreenShaderCB : register(b0)
{
    float4 resolution;
    float4 timeParams;
    float4 params;
    float4 cameraParams;
    float4 uvOffsetScale;
};

float3 SampleScreen(float2 uv)
{
    return gScreen.Sample(gLinear, uv * uvOffsetScale.zw + uvOffsetScale.xy).rgb;
}

float SampleDepth(float2 uv)
{
    return gDepth.Sample(gPoint, uv * uvOffsetScale.zw + uvOffsetScale.xy).r;
}

float LinearDepth(float d)
{
    float n = cameraParams.x, f = cameraParams.y;
    return (n * f) / max(f - d * (f - n), 1e-6);
}

struct VSOut
{
    float4 pos : SV_POSITION;
    float2 uv  : TEXCOORD0;
};

VSOut VSMain(uint vid : SV_VertexID)
{
    VSOut o;

    // エンジン標準のフルスクリーントライアングルをそのまま使用する
    o.uv  = float2((vid << 1) & 2, vid & 2);
    o.pos = float4(o.uv * float2(2.0, -2.0) + float2(-1.0, 1.0), 0.0, 1.0);

    return o;
}

float4 PSMain(VSOut i) : SV_TARGET
{
    float2 uv = i.uv;

    float softness = saturate(params.x);
    float blurRadius = max(params.y, 0.0);

    // params.z = ぼかし開始距離, params.w = 完全にぼける距離
    float focusNear = max(params.z, 0.0);
    float focusFar = max(params.w, focusNear + 0.001);

    float2 offset = resolution.zw * blurRadius;

    float3 original = SampleScreen(uv);

    float3 blur = 0.0;

    blur += SampleScreen(uv) * 4.0;
    blur += SampleScreen(uv + float2( offset.x, 0.0)) * 2.0;
    blur += SampleScreen(uv + float2(-offset.x, 0.0)) * 2.0;
    blur += SampleScreen(uv + float2(0.0,  offset.y)) * 2.0;
    blur += SampleScreen(uv + float2(0.0, -offset.y)) * 2.0;
    blur += SampleScreen(uv + float2( offset.x,  offset.y));
    blur += SampleScreen(uv + float2(-offset.x,  offset.y));
    blur += SampleScreen(uv + float2( offset.x, -offset.y));
    blur += SampleScreen(uv + float2(-offset.x, -offset.y));

    blur /= 16.0;

    // 深度からカメラとの距離を取得する
    float depth = SampleDepth(uv);
    float distanceToCamera = LinearDepth(depth);

    // 近距離では0、遠距離ほど1になる係数
    float distanceBlur = smoothstep(focusNear, focusFar, distanceToCamera);

    float finalStrength = softness * distanceBlur;

    float3 col = lerp(original, blur, finalStrength);

    return float4(col, 1.0);
}