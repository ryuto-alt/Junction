// カスタムシェーダー: Repair
// 指定した接合面だけを発光させ、修復演出に使う

Texture2D g_albedo : register(t0);
SamplerState g_sampler : register(s0);

cbuffer PerObjectConstants : register(b0)
{
    float4x4 mvp;
    float4x4 model;

    float effectValue;     // @range(0,1) 現在の発光量
    float edgeWidth;       // @range(0.001,0.25) 傷口の幅
    float glowStrength;    // @range(0,12) 発光強度
    float repairAxis;      // @range(0,2) 0:X 1:Y 2:Z

    float3 repairColor;    // @color 修復光の色
    float repairSide;      // @range(0,1) 0:- 1:+
};

cbuffer PerFrameConstants : register(b1)
{
    float4x4 view;
    float4x4 proj;
    float3 lightDir; float time;
    float3 lightColor; float ambientStrength;
};

struct VSInput
{
    float3 position : POSITION;
    float3 normal : NORMAL;
    float4 color : COLOR;
    float2 texCoord : TEXCOORD0;
    float4 tangent : TANGENT;
    uint4 boneIndices : BLENDINDICES;
    float4 boneWeights : BLENDWEIGHT;
};

struct PSInput
{
    float4 positionSV : SV_POSITION;
    float3 localPos : TEXCOORD1;
    float3 worldNormal : NORMAL;
    float4 color : COLOR;
    float2 texCoord : TEXCOORD0;
};

PSInput VSMain(VSInput input)
{
    PSInput output;

    // 接合面判定に使うためローカル座標をPSへ渡す
    output.positionSV = mul(float4(input.position, 1.0f), mvp);
    output.localPos = input.position;
    output.worldNormal = normalize(mul(input.normal, (float3x3)model));
    output.color = input.color;
    output.texCoord = input.texCoord;

    return output;
}

float GetRepairCoordinate(float3 localPos, int axis, int side)
{
    float coordinate = 0.0f;

    if (axis == 0)
    {
        coordinate = localPos.x;
    }
    else if (axis == 1)
    {
        coordinate = localPos.y;
    }
    else
    {
        coordinate = localPos.z;
    }

    if (side == 0)
    {
        return coordinate + 0.5f;
    }

    return 0.5f - coordinate;
}

float4 PSMain(PSInput input) : SV_TARGET
{
    float4 albedo = g_albedo.Sample(g_sampler, input.texCoord) * input.color;

    float3 N = normalize(input.worldNormal);
    float3 L = normalize(-lightDir);
    float ndotl = max(dot(N, L), 0.0f);

    float3 baseColor = albedo.rgb * (lightColor * ndotl + ambientStrength);

    int axis = (int)round(repairAxis);
    int side = (int)round(repairSide);

    float coord = GetRepairCoordinate(input.localPos, axis, side);
    float width = max(edgeWidth, 0.001f);
    float strength = max(glowStrength, 0.0f);
    float3 glowColor = repairColor.rgb;

    float edgeDistance = abs(coord);
    float edgeMask = 1.0f - smoothstep(width, width * 2.0f, edgeDistance);

    float progress = saturate(effectValue);

    // 修復の後半で最大発光し、修復完了時には消える
    float peak = 1.0f - abs(progress - 0.75f) / 0.25f;
    peak = saturate(peak);
    peak = peak * peak;

    float glow = edgeMask * peak;

    float3 color = baseColor;
    color += glowColor * glow * strength;

    return float4(color, albedo.a);
}