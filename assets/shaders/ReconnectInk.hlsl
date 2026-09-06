// Physical guide ink with per-instance color. No flashing or post effects.
cbuffer PerObjectConstants:register(b0){float4x4 mvp;float4x4 model;float effectValue;float3 reserved;float4 shaderParams;};
struct V{float3 p:POSITION;float3 n:NORMAL;float4 c:COLOR;float2 uv:TEXCOORD0;float4 t:TANGENT;uint4 bi:BLENDINDICES;float4 bw:BLENDWEIGHT;};
struct P{float4 p:SV_POSITION;};
P VSMain(V v){P o;o.p=mul(float4(v.p,1),mvp);return o;}
float4 PSMain(P p):SV_TARGET{return float4(shaderParams.rgb*shaderParams.w,1);}
