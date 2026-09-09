// カスタムシェーダー: Waterfall
// 水路から下方向へ落下する水を表現する

Texture2D g_albedo : register(t0);
SamplerState g_sampler : register(s0);

cbuffer PerObjectConstants : register(b0)
{
    float4x4 mvp;
    float4x4 model;

    float effectValue;     // @range(0,1) ハイライト・反射の強さ
    float fallSpeed;       // @range(0,4) 落下速度
    float swayStrength;    // @range(0,0.1) 横揺れの強さ
    float streakStrength;  // @range(0,2) 縦筋の強さ
    float4 waterColor;     // @color 水の色。Aを透明度に使用
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
    float3 worldNormal : NORMAL;
    float3 worldTangent : TANGENT;
    float4 color : COLOR;
    float2 texCoord : TEXCOORD0;
    float3 localPos : TEXCOORD1;
};

PSInput VSMain(VSInput input)
{
    PSInput output;

    float3 position = input.position;

    // 滝そのものの形は崩さず、見た目の流れはPixel Shader側で作る
    output.positionSV = mul(float4(position, 1.0f), mvp);
    output.worldNormal = normalize(mul(input.normal, (float3x3)model));
    output.worldTangent = normalize(mul(input.tangent.xyz, (float3x3)model));
    output.color = input.color;
    output.texCoord = input.texCoord;
    output.localPos = position;

    return output;
}

float4 PSMain(PSInput input) : SV_TARGET
{
    float2 uv = input.texCoord;

    // --------------------------------
    // Vertical Flow
    // --------------------------------

    // V方向へ高速スクロールさせて水の落下を表現する
    uv.y += time * fallSpeed;

    // --------------------------------
    // Horizontal Sway
    // --------------------------------

    float sway1 = sin(uv.y * 8.0f + time * fallSpeed * 0.35f);
    float sway2 = sin(uv.y * 15.0f - time * fallSpeed * 0.20f + uv.x * 4.0f);

    float sway = (sway1 * 0.70f + sway2 * 0.30f) * swayStrength;

    uv.x += sway;

    // --------------------------------
    // Base Texture
    // --------------------------------

    float4 albedo = g_albedo.Sample(g_sampler, uv) * input.color;

    float3 N = normalize(input.worldNormal);
    float3 T = normalize(input.worldTangent);
    float3 B = normalize(cross(N, T));

    // --------------------------------
    // Flow Normal
    // --------------------------------

    float normalWave1 = sin(uv.y * 11.0f - time * fallSpeed * 0.8f);
    float normalWave2 = sin(uv.y * 19.0f - time * fallSpeed * 1.2f + uv.x * 5.0f);

    float normalX = normalWave1 * swayStrength * 0.8f;
    float normalY = normalWave2 * swayStrength * 0.4f;

    // 流れに合わせて法線を僅かに揺らし、反射にも動きをつける
    N = normalize(N + T * normalX + B * normalY);

    // --------------------------------
    // Water Color
    // --------------------------------

    float3 minimumWaterColor = float3(0.05f, 0.18f, 0.24f);
    float3 baseColor = max(waterColor.rgb, minimumWaterColor);

    float3 L = normalize(-lightDir);
    float ndotl = saturate(dot(N, L));

    float lighting = 0.78f + ndotl * 0.22f;
    float3 color = baseColor * lighting;

    // テクスチャを薄く混ぜて表面のムラを作る
    color *= lerp(float3(1.0f, 1.0f, 1.0f), max(albedo.rgb, 0.55f), 0.12f);

    // --------------------------------
    // Vertical Streaks
    // --------------------------------

    float streak1 = sin(uv.x * 16.0f + uv.y * 2.0f);
    float streak2 = sin(uv.x * 31.0f - uv.y * 1.5f + time * fallSpeed * 0.25f);
    float streak3 = sin(uv.x * 47.0f + time * fallSpeed * 0.40f);

    float streak = streak1 * 0.50f + streak2 * 0.30f + streak3 * 0.20f;
    streak = saturate(streak * 0.5f + 0.5f);
    streak = pow(streak, 7.0f);

    // 縦方向へ伸びる白い水筋を作る
    color += float3(0.72f, 0.90f, 1.0f) * streak * streakStrength * 0.28f;

    // --------------------------------
    // Fresnel
    // --------------------------------

    float3 viewNormal = normalize(mul(N, (float3x3)view));

    float fresnel = pow(1.0f - saturate(abs(viewNormal.z)), 4.0f);
    fresnel = saturate(fresnel * effectValue);

    float3 reflectionColor = float3(0.78f, 0.91f, 1.0f);
    color = lerp(color, reflectionColor, fresnel * 0.45f);

    // --------------------------------
    // Specular
    // --------------------------------

    float3 lightView = normalize(mul(L, (float3x3)view));
    float3 viewDirection = float3(0.0f, 0.0f, 1.0f);
    float3 H = normalize(lightView + viewDirection);

    float ndoth = saturate(dot(viewNormal, H));

    float specularWide = pow(ndoth, 28.0f);
    float specularSharp = pow(ndoth, 128.0f);

    color += lightColor * specularWide * 0.25f;
    color += lightColor * specularSharp * 1.10f;

    // --------------------------------
    // Alpha Variation
    // --------------------------------

    float alphaNoise1 = sin(uv.x * 23.0f + uv.y * 7.0f);
    float alphaNoise2 = sin(uv.x * 41.0f - uv.y * 5.0f + time * fallSpeed * 0.35f);

    float alphaNoise = alphaNoise1 * 0.65f + alphaNoise2 * 0.35f;
    alphaNoise = alphaNoise * 0.5f + 0.5f;

    // 水膜に濃淡を付けて一枚板っぽさを減らす
    float alpha = waterColor.a;
    alpha *= lerp(0.55f, 1.0f, alphaNoise);
    alpha += fresnel * 0.10f;
    alpha += streak * 0.08f;

    return float4(color, saturate(alpha));
}