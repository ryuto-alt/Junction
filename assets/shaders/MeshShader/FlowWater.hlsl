// カスタムシェーダー: FlowWater
// 水路や斜面を一方向へ流れる水を表現する
// 大きめの波 + UVスクロール + Fresnel + Specular + 流れハイライト

Texture2D g_albedo : register(t0);
SamplerState g_sampler : register(s0);

cbuffer PerObjectConstants : register(b0)
{
    float4x4 mvp;
    float4x4 model;

    float effectValue;        // @range(0,1) 反射・ハイライトの強さ
    float flowSpeed;          // @range(-2,2) 流速。負数で逆方向
    float waveStrength;       // @range(0,0.02) 波の高さ
    float distortionStrength; // @range(0,0.05) 横方向の揺らぎ
    float4 waterColor;        // @color 水の色。Aを透明度に使用
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

float FlowWave(float2 uv)
{
    float wave1 = sin(uv.y * 7.0f - time * flowSpeed * 2.2f);
    float wave2 = sin(uv.y * 12.0f - time * flowSpeed * 3.4f + uv.x * 3.0f);

    // 大きめで緩やかな波を2種類だけ重ねる
    return (wave1 * 0.70f + wave2 * 0.30f) * waveStrength;
}

PSInput VSMain(VSInput input)
{
    PSInput output;

    float3 position = input.position;

    float wave = FlowWave(input.texCoord);

    // 水面を少しだけ法線方向へ動かして立体感を加える
    position += input.normal * wave;

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
    // Flow
    // --------------------------------

    // V方向へUVをスクロールして水が流れているように見せる
    uv.y -= time * flowSpeed;

    // 横方向へ少しだけ揺らして直線的すぎる流れを崩す
    float lateral1 = sin(uv.y * 6.0f + time * flowSpeed * 0.8f);
    float lateral2 = sin(uv.y * 10.0f - time * flowSpeed * 0.5f + uv.x * 2.0f);

    float lateralOffset = (lateral1 * 0.70f + lateral2 * 0.30f) * distortionStrength;
    uv.x += lateralOffset;

    // --------------------------------
    // Albedo
    // --------------------------------

    float4 albedo = g_albedo.Sample(g_sampler, uv) * input.color;

    float3 N = normalize(input.worldNormal);
    float3 T = normalize(input.worldTangent);
    float3 B = normalize(cross(N, T));

    // --------------------------------
    // Flow Normal
    // --------------------------------

    float normalWave1 = sin(uv.y * 8.0f - time * flowSpeed * 1.7f);
    float normalWave2 = sin(uv.y * 13.0f - time * flowSpeed * 2.4f + uv.x * 3.0f);

    float normalX = normalWave1 * waveStrength * 2.0f;
    float normalY = normalWave2 * waveStrength * 1.2f;

    // 流れに合わせて法線を少し揺らし、光沢にも動きをつける
    N = normalize(N + T * normalX + B * normalY);

    // --------------------------------
    // Lighting
    // --------------------------------

    float3 L = normalize(-lightDir);
    float ndotl = saturate(dot(N, L));

    float3 minimumWaterColor = float3(0.04f, 0.17f, 0.22f);
    float3 baseColor = max(waterColor.rgb, minimumWaterColor);

    float lighting = 0.82f + ndotl * 0.18f;
    float3 color = baseColor * lighting;

    // アルベドは模様として少しだけ混ぜる
    color *= lerp(float3(1.0f, 1.0f, 1.0f), max(albedo.rgb, 0.60f), 0.10f);

    // --------------------------------
    // Fresnel
    // --------------------------------

    float3 viewNormal = normalize(mul(N, (float3x3)view));

    float fresnel = pow(1.0f - saturate(abs(viewNormal.z)), 5.0f);
    fresnel = saturate(fresnel * effectValue);

    float3 reflectionColor = float3(0.72f, 0.88f, 0.96f);
    color = lerp(color, reflectionColor, fresnel * 0.50f);

    // --------------------------------
    // Specular
    // --------------------------------

    float3 lightView = normalize(mul(L, (float3x3)view));
    float3 viewDirection = float3(0.0f, 0.0f, 1.0f);
    float3 H = normalize(lightView + viewDirection);

    float ndoth = saturate(dot(viewNormal, H));

    float specularWide = pow(ndoth, 32.0f);
    float specularSharp = pow(ndoth, 160.0f);

    // 広い反射と細い反射を重ねる
    color += lightColor * specularWide * 0.22f;
    color += lightColor * specularSharp * 0.95f;

    // --------------------------------
    // Flow Highlight
    // --------------------------------

    float flowLine1 = sin(uv.y * 14.0f + uv.x * 2.0f);
    float flowLine2 = sin(uv.y * 21.0f - uv.x * 3.0f + time * flowSpeed * 0.7f);

    float flowHighlight = flowLine1 * 0.70f + flowLine2 * 0.30f;
    flowHighlight = saturate(flowHighlight * 0.5f + 0.5f);
    flowHighlight = pow(flowHighlight, 10.0f);

    // 流れ方向に沿う細い白い反射を追加する
    color += float3(0.72f, 0.90f, 1.0f) * flowHighlight * effectValue * 0.16f;

    // --------------------------------
    // Alpha
    // --------------------------------

    float alpha = saturate(waterColor.a + fresnel * 0.10f);

    return float4(color, alpha);
}