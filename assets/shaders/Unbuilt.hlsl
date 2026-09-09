// @group 継ぎ手
// ============================================================================
// Unbuilt.hlsl — まだ実体でない破片。
//
// ★★何のためにあるか(2026-09-09)
//   破片は「焦点から見ると本物に見える」のが仕掛けなので、材質も形も本物と同じに
//   してあった。その結果【歩ける物と歩けない物が見分けられず】、
//   同じ階段でも当たり判定があったり無かったりして、バグにしか見えなくなっていた。
//   ここでは未実体の破片を【半透明の幽霊】にする。透けている物には乗れない、と
//   一目で分かる ＝ 当たり判定の有無と見た目が必ず一致する。
//
// ★これは合図(ヒント)ではない。近づいても、狙っても、何も変わらない。
//   「まだ無い物はこう見える」という材質の決まりごとでしかない。
//   合っているかどうかは今までどおり【破片の重なり】だけで判断させる。
//
//   effectValue = 0 … 幽霊(半透明)。確定前
//   effectValue = 1 … 本物(不透明)。確定後。Lua: scene:setMeshEffect(e, 1)
//
// ★輪郭(フレネル)を明るくしてある。重ねる遊びで一番見たいのは【縁】なので、
//   透けさせるほど縁が立つ方が、むしろ合わせやすくなる。
// ============================================================================
Texture2D    g_albedo  : register(t0);
SamplerState g_sampler : register(s0);

cbuffer PerObjectConstants : register(b0)
{
    float4x4 mvp;
    float4x4 model;
    float  effectValue;    // @range(0,1) 0=幽霊 / 1=本物
    float3 _reserved;      // shaderParamsB(未使用)
    float4 shaderParams;   // xyz=色味 / w=幽霊のときの不透明度
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
    float3 normal   : NORMAL;
    float4 color    : COLOR;
    float2 texCoord : TEXCOORD0;
    float4 tangent  : TANGENT;
    uint4  boneIndices : BLENDINDICES;
    float4 boneWeights : BLENDWEIGHT;
};

struct PSInput
{
    float4 pos      : SV_POSITION;
    float3 worldPos : TEXCOORD1;
    float3 normal   : TEXCOORD2;
    float2 uv       : TEXCOORD0;
};

PSInput VSMain(VSInput v)
{
    PSInput o;
    o.pos      = mul(float4(v.position, 1.0f), mvp);
    o.worldPos = mul(float4(v.position, 1.0f), model).xyz;
    o.normal   = normalize(mul(float4(v.normal, 0.0f), model).xyz);
    o.uv       = v.texCoord;
    return o;
}

float4 PSMain(PSInput i) : SV_TARGET
{
    float3 N = normalize(i.normal);
    float3 L = normalize(-lightDir);

    // ★見え方は素の前方描画に寄せる。実体になった時に隣の壁と material が
    //   食い違って見えると「作り物」に見えてしまう。
    float3 albedo = g_albedo.Sample(g_sampler, i.uv).rgb * shaderParams.rgb;
    float  ndotl  = saturate(dot(N, L));
    float3 lit    = albedo * (ambientStrength + lightColor * ndotl * 0.85f);

    // 視線とのなす角。縁ほど 1 に近づく
    float3 V = normalize(-mul(float4(i.worldPos, 1.0f), view).xyz);
    float3 Nv = normalize(mul(N, (float3x3)view));
    float  fres = pow(1.0f - saturate(abs(dot(Nv, float3(0, 0, 1)))), 2.2f);

    // 幽霊のとき: 面はほとんど消して、縁だけを残す。本物のとき: ただの不透明
    // ★面を薄くするほど「まだ無い物」に見えるが、薄くしすぎると何の形か読めない。
    //   読ませるのは【縁】の仕事なので、面を落とすぶん縁を強くして釣り合わせる。
    float  ghostA = saturate(shaderParams.w + pow(fres, 0.85f) * 0.62f);
    float  a      = lerp(ghostA, 1.0f, effectValue);

    // ★縁の明るさは幽霊のときだけ。実体になったら足さない(白く浮いて見える)
    float3 col = lit + (1.0f - effectValue) * fres * 0.40f * float3(1.0f, 0.97f, 0.90f);

    return float4(col, a);
}
