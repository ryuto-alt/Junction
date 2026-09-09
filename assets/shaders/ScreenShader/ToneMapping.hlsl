// スクリーンシェーダー: Tone Mapping
// Eye Adaptationで調整されたHDRカラーをACES風に圧縮して表示する

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

float3 ACESFilm(float3 color)
{
    float a = 2.51f;
    float b = 0.03f;
    float c = 2.43f;
    float d = 0.59f;
    float e = 0.14f;

    return saturate(
        (color * (a * color + b)) /
        (color * (c * color + d) + e)
    );
}

float4 PSMain(VSOut i) : SV_TARGET
{
    float3 color = SampleScreen(i.uv);

    // params.xを追加の露出補正値として使用する
    float exposureCompensation = params.x;

    color *= exp2(exposureCompensation);

    color = ACESFilm(color);

    return float4(color, 1.0f);
}