// @group 継ぎ手
// ============================================================================
// Membrane.hlsl — 継ぎ手の膜。主題は【つなぐ】。
//
//   膜は左半分と右半分が【別々の場所の表面】で、互いに逆へ流れている。
//   真ん中の縫い目(ファスナーの歯)だけが、その二枚を留めている。
//
//   繋がっていない (effectValue=0) … 歯が固く噛み合った 1 本の細い線。膜は不透明
//   繋がった       (effectValue=1) … 歯が左右へ開き、間に【向こうへ抜けた裂け目】が空く
//   くぐる瞬間     (_Cross)        … 裂け目から衝撃波。暗転しないので「破って通った」に見える
//
// ★明るさは控えめにしてある。ブルームが乗ると一瞬で白く飛んで何も読めなくなる(実測)。
// ============================================================================
Texture2D    g_albedo  : register(t0);
SamplerState g_sampler : register(s0);

cbuffer PerObjectConstants : register(b0)
{
    float4x4 mvp;
    float4x4 model;
    float  effectValue;   // @range(0,1)  繋がり具合。Lua: scene:setMeshEffect
    float  _Cross;        // @range(0,1)  くぐった瞬間の衝撃
    float2 _reserved;
    float4 shaderParams;  // x=個体の種 y=光の強さ z=呼吸の速さ w=くぐった瞬間
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
    float3 worldNormal : NORMAL;
    float3 worldPos    : TEXCOORD1;
    float2 texCoord    : TEXCOORD0;
};

PSInput VSMain(VSInput input)
{
    PSInput o;
    // ★膜は呼吸する。繋がると【吸い込む向き】へ反転する
    float2 c   = input.texCoord - 0.5;
    float  r   = saturate(1.0 - dot(c, c) * 4.0);
    float  br  = sin(time * (1.1 + shaderParams.z) + shaderParams.x * 6.283) * 0.5 + 0.5;
    float  amp = lerp(0.018 * br, -0.060 - 0.03 * br, effectValue);
    float3 p   = input.position + input.normal * (amp * r * r);

    o.positionSV  = mul(float4(p, 1.0), mvp);
    o.worldNormal = normalize(mul(input.normal, (float3x3)model));
    o.worldPos    = mul(float4(p, 1.0), model).xyz;
    o.texCoord    = input.texCoord;
    return o;
}

float hash21(float2 p)
{
    p = frac(p * float2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return frac(p.x * p.y);
}

float vnoise(float2 p)
{
    float2 i = floor(p), f = frac(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash21(i), b = hash21(i + float2(1, 0));
    float c = hash21(i + float2(0, 1)), d = hash21(i + float2(1, 1));
    return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
}

float fbm(float2 p)
{
    float s = 0.0, a = 0.5;
    for (int i = 0; i < 4; ++i) { s += vnoise(p) * a; p *= 2.03; a *= 0.5; }
    return s;
}

float4 PSMain(PSInput input) : SV_TARGET
{
    float2 uv   = input.texCoord;
    float2 c    = uv - 0.5;
    float  link = saturate(effectValue);
    float  seed = shaderParams.x;
    float  side = (uv.x < 0.5) ? -1.0 : 1.0;

    // ---- 左右は別の場所の表面。流れる向きが違う ----
    float2 flow = float2(0.0, time * 0.045 * side);
    float2 skew = float2(side * 0.16, 0.0);
    float  film = fbm((uv + skew) * float2(4.5, 3.0) + flow + seed * 11.0);
    film       += 0.30 * fbm((uv - skew) * float2(12.0, 8.0) - flow * 1.6 + seed * 5.0);

    // ---- 裂け目。★繋がるほど【左右へ開く】。歯は開口の縁に付いて離れていく ----
    float ease  = link * link * (3.0 - 2.0 * link);
    float gap   = 0.010 + 0.235 * ease;          // 開口の半幅(UV)
    float lens  = smoothstep(0.03, 0.16, uv.y) * smoothstep(0.03, 0.16, 1.0 - uv.y);
    float dEdge = abs(c.x) - gap * lens;         // <0 = 裂け目の内側
    float edge  = exp(-abs(dEdge) * 42.0);       // 縁の光
    float inside= smoothstep(0.004, -0.010, dEdge) * ease;

    // ★歯。開口の縁に沿って上下へ流れる楔。噛み合いが外れて【ずれていく】
    float teethY = uv.y * 30.0 + time * (0.20 + 1.5 * ease) * side;
    float tooth  = abs(frac(teethY) - 0.5) * 2.0;
    float bite   = smoothstep(0.62, 0.10, tooth) * exp(-abs(dEdge) * 26.0);

    // ---- くぐる瞬間の衝撃波 ----
    float cw   = saturate(max(_Cross, shaderParams.w));
    float ring = smoothstep(0.11, 0.0, abs(length(c) - (0.04 + cw * 0.80))) * cw;

    // ---- 色 ----
    // ★shaderParams.y = 【対の色】の色相。同じ色の枠どうしだけが繋がる、を膜でも言う。
    //   -1 は「電源が無い」= 灰色の死んだ膜。
    float  hue  = shaderParams.y;
    float3 tint;
    if (hue < 0.0)
    {
        tint = float3(0.42, 0.44, 0.48);
    }
    else
    {
        float h = frac(hue + side * 0.035);
        tint = saturate(abs(frac(h + float3(0.0, 0.6667, 0.3333)) * 6.0 - 3.0) - 1.0);
        tint = lerp(float3(0.75, 0.78, 0.82), tint, 0.85);
    }

    float3 col  = float3(0.070, 0.078, 0.098);
    col += film * 0.085 * float3(0.62, 0.70, 0.84);
    float fres = pow(1.0 - saturate(abs(input.worldNormal.y)), 3.0);
    col += 0.030 * fres * float3(sin(film * 8.0) * 0.5 + 0.5,
                                 sin(film * 8.0 + 2.1) * 0.5 + 0.5,
                                 sin(film * 8.0 + 4.2) * 0.5 + 0.5);

    // 裂け目の中は【向こう側】= ほぼ真っ黒。ここが「抜けている」ことの全て
    col  = lerp(col, float3(0.008, 0.010, 0.016), inside);
    col += edge * lerp(float3(0.10, 0.12, 0.16), tint * 0.85, ease) * (0.55 + 0.9 * ease);
    col += bite * tint * (0.16 + 0.45 * ease);
    col += ring * float3(1.0, 0.94, 0.86) * 1.3;

    // ---- 不透明度。裂け目だけが透ける ----
    float a = 0.95 - 0.55 * inside;
    a = max(a, edge * 0.85 + ring);
    return float4(col, saturate(a));
}
