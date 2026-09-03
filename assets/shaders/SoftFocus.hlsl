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