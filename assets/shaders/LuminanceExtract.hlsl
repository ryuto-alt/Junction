// スクリーンシェーダー: Luminance Extract
// 画面カラーから輝度を抽出してグレースケール表示する

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
    float3 color = SampleScreen(i.uv);

    // 人間の視覚感度を考慮したRGBから輝度への変換
    float luminance = dot(
        color,
        float3(0.2126f, 0.7152f, 0.0722f)
    );

    return float4(
        luminance,
        luminance,
        luminance,
        1.0f
    );
}