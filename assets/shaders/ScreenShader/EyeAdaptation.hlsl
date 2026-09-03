// スクリーンシェーダー: Eye Adaptation
// 現在の平均輝度から目標露出を求め、明順応・暗順応の速度差を再現する

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
    float n = cameraParams.x;
    float f = cameraParams.y;

    return (n * f) / max(f - d * (f - n), 1e-6f);
}

struct VSOut
{
    float4 pos : SV_POSITION;
    float2 uv  : TEXCOORD0;
};

VSOut VSMain(uint vid : SV_VertexID)
{
    VSOut o;

    // エンジン標準のフルスクリーントライアングルを生成する
    o.uv = float2((vid << 1) & 2, vid & 2);
    o.pos = float4(
        o.uv * float2(2.0f, -2.0f) + float2(-1.0f, 1.0f),
        0.0f,
        1.0f
    );

    return o;
}

float GetLuminance(float3 color)
{
    return dot(
        color,
        float3(0.2126f, 0.7152f, 0.0722f)
    );
}

float4 PSMain(VSOut i) : SV_TARGET
{
    float3 color = SampleScreen(i.uv);

    float luminance = GetLuminance(color);

    // params.x = 基準輝度
    // params.y = 暗順応速度
    // params.z = 明順応速度
    // params.w = 露出制限
    float keyValue = params.x > 0.0f ? params.x : 0.18f;
    float darkAdaptSpeed = params.y > 0.0f ? params.y : 0.8f;
    float brightAdaptSpeed = params.z > 0.0f ? params.z : 3.0f;
    float maxExposure = params.w > 0.0f ? params.w : 8.0f;

    float targetExposure =
        keyValue / max(luminance, 0.0001f);

    targetExposure = clamp(
        targetExposure,
        0.05f,
        maxExposure
    );

    float currentExposure = 1.0f;

    float adaptSpeed =
        targetExposure > currentExposure
        ? darkAdaptSpeed
        : brightAdaptSpeed;

    float deltaTime = max(timeParams.y, 0.0001f);

    float adaptation =
        1.0f - exp(-adaptSpeed * deltaTime);

    float exposure =
        lerp(
            currentExposure,
            targetExposure,
            adaptation
        );

    color *= exposure;

    return float4(color, 1.0f);
}