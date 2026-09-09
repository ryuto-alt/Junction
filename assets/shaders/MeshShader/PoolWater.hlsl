// カスタムシェーダー: PoolWater
// 波・反射・屈折・Fresnel・Specular・Foamを使用した室内プール向け水面

Texture2D g_albedo : register(t0);
Texture2D g_sceneColor : register(t1);
Texture2D g_reflection : register(t2);

SamplerState g_sampler : register(s0);

cbuffer PerObjectConstants : register(b0)
{
    float4x4 mvp;
    float4x4 model;

    float effectValue;      // @range(0,1) 反射の強さ
    float waveStrength;     // @range(0,0.05) 波の高さ
    float waveSpeed;        // @range(0,2) 波の速度
    float transparency;     // @range(0,1) 透明度
    float4 waterColor;      // @color 水の色
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
    float4 color : COLOR;
    float2 texCoord : TEXCOORD0;
    float3 localPos : TEXCOORD1;
    float4 clipPos : TEXCOORD2;
};

float WaveHeight(float2 positionXZ)
{
    const float PI = 3.14159265f;

    float2 direction1 = normalize(float2(1.0f, 0.30f));
    float2 direction2 = normalize(float2(-0.60f, 1.0f));
    float2 direction3 = normalize(float2(0.80f, -0.70f));

    float wavelength1 = 2.8f;
    float wavelength2 = 1.7f;
    float wavelength3 = 0.9f;

    float k1 = 2.0f * PI / wavelength1;
    float k2 = 2.0f * PI / wavelength2;
    float k3 = 2.0f * PI / wavelength3;

    float phase1 = k1 * dot(direction1, positionXZ) - time * waveSpeed * 0.45f;
    float phase2 = k2 * dot(direction2, positionXZ) - time * waveSpeed * 0.30f;
    float phase3 = k3 * dot(direction3, positionXZ) - time * waveSpeed * 0.20f;

    // 3方向の異なる波を合成して規則的すぎない水面を作る
    float wave1 = sin(phase1) * waveStrength;
    float wave2 = sin(phase2) * waveStrength * 0.35f;
    float wave3 = sin(phase3) * waveStrength * 0.15f;

    return wave1 + wave2 + wave3;
}

float3 CalculateWaveNormal(float2 positionXZ)
{
    const float sampleDistance = 0.025f;

    float heightL = WaveHeight(positionXZ - float2(sampleDistance, 0.0f));
    float heightR = WaveHeight(positionXZ + float2(sampleDistance, 0.0f));
    float heightD = WaveHeight(positionXZ - float2(0.0f, sampleDistance));
    float heightU = WaveHeight(positionXZ + float2(0.0f, sampleDistance));

    float dx = (heightR - heightL) / (2.0f * sampleDistance);
    float dz = (heightU - heightD) / (2.0f * sampleDistance);

    return normalize(float3(-dx, 1.0f, -dz));
}

float FoamNoise(float2 uv)
{
    float n1 = sin(uv.x * 31.0f + time * 0.55f);
    float n2 = sin(uv.y * 37.0f - time * 0.45f);
    float n3 = sin((uv.x + uv.y) * 23.0f + time * 0.30f);

    float noise = (n1 + n2 + n3) / 3.0f;

    return noise * 0.5f + 0.5f;
}

float2 GetScreenUV(float4 clipPos)
{
    float2 ndc = clipPos.xy / max(clipPos.w, 0.00001f);

    // クリップ空間からDirectXテクスチャ用の0～1 UVへ変換する
    float2 uv = float2(ndc.x * 0.5f + 0.5f, -ndc.y * 0.5f + 0.5f);

    return saturate(uv);
}

PSInput VSMain(VSInput input)
{
    PSInput output;

    float3 position = input.position;

    // 高密度Gridの頂点を実際に変位させて波形を作る
    position.y += WaveHeight(position.xz);

    float3 localNormal = CalculateWaveNormal(position.xz);
    float4 clipPosition = mul(float4(position, 1.0f), mvp);

    output.positionSV = clipPosition;
    output.clipPos = clipPosition;
    output.worldNormal = normalize(mul(localNormal, (float3x3)model));
    output.color = input.color;
    output.texCoord = input.texCoord;
    output.localPos = position;

    return output;
}

float4 PSMain(PSInput input) : SV_TARGET
{
    float3 N = normalize(input.worldNormal);
    float3 L = normalize(-lightDir);

    float ndotl = saturate(dot(N, L));

    // ----------------------------
    // Screen UV
    // ----------------------------

    float2 screenUV = GetScreenUV(input.clipPos);

    // ----------------------------
    // Base Water Color
    // ----------------------------

    float3 minimumWaterColor = float3(0.04f, 0.18f, 0.24f);
    float3 baseWaterColor = max(waterColor.rgb, minimumWaterColor);

    float lightAmount = 0.82f + ndotl * 0.18f;
    baseWaterColor *= lightAmount;

    // ----------------------------
    // Fresnel
    // ----------------------------

    float3 viewNormal = normalize(mul(N, (float3x3)view));

    float fresnel = pow(1.0f - saturate(abs(viewNormal.z)), 5.0f);
    fresnel = saturate(fresnel * effectValue);

    // ----------------------------
    // Reflection / Refraction Distortion
    // ----------------------------

    float2 waveDistortion = viewNormal.xy * 0.012f;

    float2 reflectionUV = saturate(screenUV + waveDistortion);
    float2 refractionUV = saturate(screenUV - waveDistortion * 0.65f);

    // 波の法線を使って実際の反射画像を歪ませる
    float3 reflectionColor = g_reflection.Sample(g_sampler, reflectionUV).rgb;

    // 水越しに見えるシーンも逆方向へ少し歪ませる
    float3 refractionColor = g_sceneColor.Sample(g_sampler, refractionUV).rgb;

    // ----------------------------
    // Water Absorption
    // ----------------------------

    float absorption = 0.20f;

    float3 tintedRefraction = lerp(refractionColor, baseWaterColor, absorption);

    // 正面では屈折を多く、斜めでは反射を多くする
    float reflectionAmount = saturate(fresnel * 0.85f + 0.08f);
    float3 color = lerp(tintedRefraction, reflectionColor, reflectionAmount);

    // ----------------------------
    // Specular
    // ----------------------------

    float3 lightView = normalize(mul(L, (float3x3)view));
    float3 viewDirection = float3(0.0f, 0.0f, 1.0f);
    float3 H = normalize(lightView + viewDirection);

    float ndoth = saturate(dot(viewNormal, H));

    float specularWide = pow(ndoth, 48.0f);
    float specularSharp = pow(ndoth, 256.0f);

    // 広い光沢と鋭いハイライトを重ねて水面らしい反射を作る
    color += lightColor * specularWide * 0.30f;
    color += lightColor * specularSharp * 1.50f;

    // ----------------------------
    // Moving Highlight
    // ----------------------------

    float movingHighlight1 = sin(input.localPos.x * 8.0f + input.localPos.z * 5.0f + time * 0.65f);
    float movingHighlight2 = sin(input.localPos.x * -4.0f + input.localPos.z * 10.0f - time * 0.40f);

    float movingHighlight = movingHighlight1 + movingHighlight2;
    movingHighlight = saturate(movingHighlight * 0.25f + 0.5f);

    float highlightMask = pow(movingHighlight, 8.0f);

    color += float3(0.65f, 0.82f, 0.95f) * highlightMask * fresnel * 0.18f;

    // ----------------------------
    // Foam
    // ----------------------------

    float2 uv = input.texCoord;

    float distanceLeft = uv.x;
    float distanceRight = 1.0f - uv.x;
    float distanceTop = uv.y;
    float distanceBottom = 1.0f - uv.y;

    float edgeDistance = min(min(distanceLeft, distanceRight), min(distanceTop, distanceBottom));

    float edgeFoam = 1.0f - smoothstep(0.008f, 0.035f, edgeDistance);

    float slope = 1.0f - saturate(N.y);

    // プールでは海のような波頭泡をほとんど出さない
    float crestFoam = smoothstep(0.12f, 0.22f, slope);

    float foamNoise = FoamNoise(uv);

    edgeFoam *= lerp(0.60f, 1.00f, foamNoise);
    crestFoam *= lerp(0.40f, 1.00f, foamNoise);

    float foam = saturate(edgeFoam * 0.35f + crestFoam * 0.03f);

    float3 foamColor = float3(0.92f, 0.97f, 1.00f);

    color = lerp(color, foamColor, foam * 0.35f);

    // ----------------------------
    // Alpha
    // ----------------------------

    float alpha = saturate(1.0f - transparency + fresnel * 0.18f + foam * 0.08f);

    return float4(color, alpha);
}