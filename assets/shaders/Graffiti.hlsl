// @group 継ぎ手
// ============================================================================
// Graffiti.hlsl — 壁に直接なぐり書きした【落書き】。
//
// ★★何のためにあるか(2026-09-09)
//   第四幕・第五幕の 9 継ぎ目には案内が何も無い。額縁つきの案内板
//   (models/props/sign_guide.gltf + assets/ui/signs/*.png)は【施設が用意した掲示物】に
//   見えるので、終盤の「先に来た誰かの書き置き」には使えない。
//   ここでは背景透過の PNG(assets/ui/graffiti/gf_*.png)を、壁から 4.5cm 浮かせた
//   薄い箱へ貼り、線の所だけを描く。下地の板が無いので、壁の汚れの上に
//   そのまま線が乗る ＝ 落書きに見える。
//
// ★★灯りに依らない(ReconnectInk と同じ)。理由:
//   このエンジンのカスタムメッシュ経路には【点光源が届かない】。b1 に来るのは
//   平行光と環境光だけで、この作品の太陽は intensity=0(屋内)。素直に陰影を付けると
//   落書きは常にほぼ真っ黒になり、暗い区画では一文字も読めない。
//   落書きは「読めること」が唯一の仕事なので、明るさは shaderParams.rgb で固定する。
//   ★そのぶん【明るくしすぎない】こと。0.75 を超えると自分で光っているように見えて、
//     リミナル空間の明暗の縞(この作品の絵そのもの)を壊す。0.60〜0.72 で使っている。
//
// ★b0 の並びはエンジン側で決まっている(gen_liminal.py の water() のコメント参照):
//     effectValue(1)  ← shaderEffectValue
//     _reserved(3)    ← shaderParamsB
//     shaderParams(4) ← shaderParams
//   宣言順がこの並びと 1 つでもずれると、値が別の変数へ入る。
//   ★コンパイルに失敗しても【直前の有効なバイトコードを維持】して黙って動くので、
//     直したら必ず dx12_engine.log を grep すること。
//
// ★擦れ(むら)は【低い周波数の正弦】で作る。ハッシュ乱数のような高周波にすると
//   FXAA と相性が悪く、歩くたびに線がちらつく。
// ============================================================================
Texture2D    g_albedo  : register(t0);
SamplerState g_sampler : register(s0);

cbuffer PerObjectConstants : register(b0)
{
    float4x4 mvp;
    float4x4 model;
    float  effectValue;    // @range(0,1) 擦れ具合。0=まっさら / 1=かなり掠れる
    float  scuffScale;     // @range(2,40) 擦れのむらの細かさ(shaderParamsB.x)
    float  edgeFade;       // @range(0,0.30) 板の四辺で消える幅(shaderParamsB.y)
    float  haloLevel;      // @range(0,0.40) 縁取りの暗さ(shaderParamsB.z)
    float4 shaderParams;   // @color rgb=チョークの色 / w=全体の濃さ
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
    // ★★裏の面を捨てる(2026-09-09。実機で最初に出た不具合)
    //   落書きは箱プリミティブなので、絵は -Z 面と +Z 面の【両方】に貼られる。
    //   このエンジンのカスタムシェーダー経路は裏面を切っていないので、
    //   奥の +Z 面に貼られた【左右反転した同じ絵】が手前の絵に重なって描かれ、
    //   絵が鏡像と二重写しになった(左右対称な別の絵に見えて意味が壊れる)。
    //   ★SV_IsFrontFace は巻き方とラスタライザの設定に依存して当てにならないので、
    //     視点空間で【面の向きと視線の向き】を直接比べる(座標系の左右手に依らない):
    //       Pv = カメラから面へのベクトル / Nv = 面の法線
    //       手前を向いている面だけ dot(Nv, Pv) < 0
    float3 Pv = mul(float4(i.worldPos, 1.0f), view).xyz;
    float3 Nv = mul(i.normal, (float3x3)view);
    clip(-dot(normalize(Nv), normalize(Pv)) - 0.02f);

    // ★PNG の中身(source/blender_graffiti.py が 2 度描いて焼いたもの):
    //     アルファ … 太らせた【縁取り】ごとの覆い(線 + その外周 11mm ほど)
    //     赤       … 1 なら【芯】(素の太さの線) / 0 なら縁取りの部分
    //   ここで  色 = lerp(暗い縁, チョーク, 芯)  に組み直す。
    // ★★なぜ縁取りが要るか(実機で確認して足した)
    //   白い線だけだと【明るい壁で消える】。第五幕の踊り場は明滅バンクの真下で
    //   壁がほぼ白く、白いチョークがまったく読めなかった。かといって暗い線にすると
    //   今度は柱や暗い区画で消える。縁取りを付ければ、明るい壁では暗い縁が、
    //   暗い壁では白い芯が形を出す ＝ どちらでも読める。
    float4 t = g_albedo.Sample(g_sampler, i.uv);
    float  core = saturate(t.r);
    float3 halo = float3(haloLevel, haloLevel * 0.96f, haloLevel * 0.90f);

    // 擦れ。滑らかなむらを掛けて、線の所々を薄くする
    float s = sin(i.uv.x * scuffScale + 1.7f) * sin(i.uv.y * scuffScale * 1.31f - 0.6f)
            + 0.55f * sin(i.uv.x * scuffScale * 2.13f - 2.1f)
                    * sin(i.uv.y * scuffScale * 1.87f + 1.2f);
    s = saturate(s * 0.5f + 0.5f);

    // 板の四辺で消す。四角く切れていると「貼った物」に見えてしまう
    float e = min(min(i.uv.x, 1.0f - i.uv.x), min(i.uv.y, 1.0f - i.uv.y));
    float fade = (edgeFade > 0.0001f) ? smoothstep(0.0f, edgeFade, e) : 1.0f;

    // ★縁取りは芯より少しだけ薄く乗せる(0.88)。薄くしすぎると明るい壁で形が消える
    //   (0.62 で試したら、明滅バンクの真下の白い壁でほとんど読めなかった)。
    float a = t.a * shaderParams.w * lerp(0.88f, 1.0f, core)
              * lerp(1.0f, s, saturate(effectValue)) * fade;

    // ★透明な所は書き込まない。板ごしに向こうが二重に見える事故を防ぐ
    clip(a - 0.012f);

    return float4(lerp(halo, shaderParams.rgb, core), a);
}
