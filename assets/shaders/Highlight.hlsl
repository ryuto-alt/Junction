// カスタムシェーダー: Highlight
// チュートリアル対象を自己発光させて見やすくする

Texture2D    g_albedo  : register(t0);
SamplerState g_sampler : register(s0);

cbuffer PerObjectConstants : register(b0)
{
    float4x4 mvp;
    float4x4 model;

    float  effectValue;
    float3 _reserved;
    float4 shaderParams;
};

cbuffer PerFrameConstants : register(b1)
{
    float4x4 view;
    float4x4 proj;
    float3   lightDir;   float time;
    float3   lightColor; float ambientStrength;
};

struct VSInput
{
    float3 position    : POSITION;
    float3 normal      : NORMAL;
    float4 color       : COLOR;
    float2 texCoord    : TEXCOORD0;
    float4 tangent     : TANGENT;
    uint4  boneIndices : BLENDINDICES;
    float4 boneWeights : BLENDWEIGHT;
};

struct PSInput
{
    float4 positionSV  : SV_POSITION;
    float3 worldPos    : TEXCOORD1;
    float3 localPos    : TEXCOORD2;
    float3 worldNormal : NORMAL;
    float4 color       : COLOR;
    float2 texCoord    : TEXCOORD0;
};

PSInput VSMain(VSInput input)
{
    PSInput output;

    float4 worldPos = mul(float4(input.position, 1.0f), model);

    // XYZ方向の発光アニメーション用にローカル座標も渡す
    output.positionSV = mul(float4(input.position, 1.0f), mvp);
    output.worldPos = worldPos.xyz;
    output.localPos = input.position;
    output.worldNormal = normalize(mul(input.normal, (float3x3)model));
    output.color = input.color;
    output.texCoord = input.texCoord;

    return output;
}

float4 PSMain(PSInput input) : SV_TARGET
{
    float4 albedo = g_albedo.Sample(g_sampler, input.texCoord) * input.color;

    float3 emissiveColor = shaderParams.rgb;
    float emissiveStrength = 6.0f;

    // effectValueで発光ラインの移動方向を選択する
    int direction = (int)round(effectValue);

    float coordinate = input.localPos.y;

    if (direction == 1)
    {
        coordinate = input.localPos.x;
    }
    else if (direction == 2)
    {
        coordinate = input.localPos.y;
    }
    else if (direction == 3)
    {
        coordinate = input.localPos.z;
    }

    float speed = 0.8f;
    float width = 0.15f;
    float repeatDistance = 2.0f;

    float movingPos = frac(time * speed);

    float normalizedPosition = frac(coordinate / repeatDistance);

    float distanceToLine = abs(normalizedPosition - movingPos);

    distanceToLine = min(distanceToLine, 1.0f - distanceToLine);

    float movingGlow = 1.0f - smoothstep(width, width * 2.0f, distanceToLine);

    float3 baseGlow = emissiveColor * emissiveStrength * 0.15f;
    float3 movingEmission = emissiveColor * emissiveStrength * movingGlow;
    float3 color = baseGlow + movingEmission;

    return float4(color, albedo.a);
}