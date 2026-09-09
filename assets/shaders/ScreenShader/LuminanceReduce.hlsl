// スクリーンシェーダー: Luminance Reduce
// 周囲4点の輝度を平均して、次の縮約パスへ渡す

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

float4 PSMain(VSOut i) : SV_TARGET
{
    float2 texel = resolution.zw;

    // 4サンプルを平均して1段階分の輝度縮約を行う
    float3 c0 = SampleScreen(i.uv + texel * float2(-0.5f, -0.5f));
    float3 c1 = SampleScreen(i.uv + texel * float2( 0.5f, -0.5f));
    float3 c2 = SampleScreen(i.uv + texel * float2(-0.5f,  0.5f));
    float3 c3 = SampleScreen(i.uv + texel * float2( 0.5f,  0.5f));

    float luminance0 = dot(c0, float3(0.2126f, 0.7152f, 0.0722f));
    float luminance1 = dot(c1, float3(0.2126f, 0.7152f, 0.0722f));
    float luminance2 = dot(c2, float3(0.2126f, 0.7152f, 0.0722f));
    float luminance3 = dot(c3, float3(0.2126f, 0.7152f, 0.0722f));

    float averageLuminance =
        (luminance0 + luminance1 + luminance2 + luminance3) * 0.25f;

    return float4(
        averageLuminance,
        averageLuminance,
        averageLuminance,
        1.0f
    );
}