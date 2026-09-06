# -*- coding: utf-8 -*-
"""リミナル空間の内装テクスチャ。出力は assets/models/tex/lm_*.png。

★実行(numpy が要るので Blender 同梱の python):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" source/gen_liminal_tex.py

★設計の決まり(踏んだ罠から):
  ・**法線マップは作らない**。高タイリングの床/壁に貼ると grazing 角で N·L が符号反転して
    面が黒い斑点で消える([[dx12-shading-traps]])。凹凸は albedo の陰影だけで描く。
  ・1024px = 2m(512 texel/m)。シーン側は uvTiling = 実寸/2 で貼ること。
  ・全部タイル可能(周期ノイズ)。継ぎ目が出ると「同じ模様の繰り返し」がバレて安っぽくなる。
  ・色は sRGB で決めて lin() でリニアへ落とす(write_png が srgb() を掛け直す)。
    リミナルの肝は【彩度の低い黄緑と、蛍光灯の白の対比】。原色を使わない。
"""
import os, zlib, struct
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "assets", "models", "tex")
N = 1024
rng = np.random.default_rng(20260905)
yy, xx = np.mgrid[0:N, 0:N] / N


def write_png(path, arr):
    a = np.clip(arr, 0.0, 1.0)
    b = (a * 255.0 + 0.5).astype(np.uint8)
    h, w, _ = b.shape
    rows = np.zeros((h, w * 3 + 1), np.uint8)
    rows[:, 1:] = b.reshape(h, w * 3)
    raw = rows.tobytes()

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    print("wrote", os.path.basename(path))


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def lin(r, g, b):
    """sRGB 0..255 -> リニア。色はこれで決める。"""
    c = np.array([r, g, b], dtype=np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def vnoise(freq, seed=None):
    r = np.random.default_rng(seed) if seed is not None else rng
    g = r.random((freq, freq))
    idx = np.arange(N) * freq / N
    i0 = np.floor(idx).astype(int) % freq
    i1 = (i0 + 1) % freq
    t = idx - np.floor(idx)
    t = t * t * (3 - 2 * t)
    a = g[np.ix_(i0, i0)] * (1 - t)[:, None] + g[np.ix_(i1, i0)] * t[:, None]
    b = g[np.ix_(i0, i1)] * (1 - t)[:, None] + g[np.ix_(i1, i1)] * t[:, None]
    return a * (1 - t)[None, :] + b * t[None, :]


def fbm(base, octaves=5, gain=0.5, seed=0):
    out, amp, f, norm = 0.0, 1.0, base, 0.0
    for k in range(octaves):
        out = out + amp * vnoise(f, seed + k * 977)
        norm += amp
        amp *= gain
        f *= 2
    return out / norm


def grid_mask(per, width):
    """per 個/タイル の格子。返り値 1 = 目地の芯。"""
    gx = np.abs(((xx * per) % 1.0) - 0.5) * 2
    gy = np.abs(((yy * per) % 1.0) - 0.5) * 2
    g = np.maximum(gx, gy)
    return np.clip((g - (1.0 - width)) / width, 0, 1)


def cell_id(per, seed):
    """per 個/タイル の格子の、セルごとに 0..1 の乱数。"""
    ix = np.floor(xx * per).astype(int) % per
    iy = np.floor(yy * per).astype(int) % per
    r = np.random.default_rng(seed).random((per, per))
    return r[iy, ix]


def out(name, col):
    write_png(os.path.join(OUT, name), srgb(col))


# ================================================================ 壁紙(主役)
def wallpaper():
    """バックルームの黄ばんだ壁紙。縦の極薄ストライプ + 水染み + 腰高の擦れ。
    ★『リミナルらしさ』の 8 割はこの色。彩度を上げすぎない(黄土色ではなく、褪せた芥子)。"""
    base = lin(206, 191, 132)
    stripe = 0.5 + 0.5 * np.cos(xx * 2 * np.pi * 16)          # 12.5cm ピッチ
    v = 1.0 - 0.026 * stripe
    v = v * (1.0 - 0.075 * (fbm(4, 5, 0.55, 11) - 0.5))       # 大きなムラ
    # 水染み(上から垂れる)。縦に伸ばした fbm を閾値で切る
    drip = fbm(3, 4, 0.62, 401)
    drip = drip * (0.55 + 0.75 * (1.0 - yy))                  # 上ほど濃い
    stain = np.clip(drip - 0.60, 0, 1) * 2.2
    col = base[None, None, :] * v[..., None]
    col = col * (1.0 - stain[..., None] * lin(150, 120, 70)[None, None, :] * 0.9)
    # 腰から下の擦れ(靴と椅子が当たる帯)
    scuff = np.clip(1.0 - np.abs(yy - 0.10) / 0.09, 0, 1) * (0.35 + 0.65 * fbm(24, 3, 0.5, 77))
    col = col * (1.0 - 0.16 * scuff[..., None])
    col = col + (rng.random((N, N, 1)) - 0.5) * 0.014
    out("lm_wall_col.png", col)


def wall_pale():
    """区画を変えるための第2の壁。褪せたミントグレー(90年代の官公庁)。
    ★同じ壁紙が延々続くと『広いのに単調』になる。色だけ変えて模様は同じにする
      = 同じ建物の別区画に見える(別の建物に見せてはいけない)。"""
    base = lin(176, 186, 172)
    stripe = 0.5 + 0.5 * np.cos(xx * 2 * np.pi * 16)
    v = 1.0 - 0.022 * stripe
    v = v * (1.0 - 0.070 * (fbm(4, 5, 0.55, 311) - 0.5))
    stain = np.clip(fbm(3, 4, 0.62, 907) - 0.63, 0, 1) * 2.0
    col = base[None, None, :] * v[..., None]
    col = col * (1.0 - stain[..., None] * lin(120, 130, 120)[None, None, :])
    col = col + (rng.random((N, N, 1)) - 0.5) * 0.012
    out("lm_wall2_col.png", col)


# ================================================================ 床
def carpet():
    """オフィス絨毯。踏み跡のムラと細かい斑。★彩度を落として『掃除されていない』色に。"""
    base = lin(122, 108, 66)
    speck = rng.random((N, N))
    fleck = np.where(speck > 0.88, 1.0, 0.0) * (0.30 + 0.5 * rng.random((N, N)))
    dark = np.where(speck < 0.13, 1.0, 0.0) * 0.26
    weave = np.sin((xx + yy) * 2 * np.pi * 10) * np.sin((xx - yy) * 2 * np.pi * 10)
    v = 1.0 + 0.09 * weave + 0.45 * fleck - dark
    v = v * (1.0 - 0.24 * (fbm(3, 4, 0.6, 909) - 0.5))
    col = base[None, None, :] * v[..., None]
    col = col + fleck[..., None] * lin(70, 62, 40)[None, None, :] * 0.5
    out("lm_carpet_col.png", col)


def vinyl():
    """上階の廊下の長尺塩ビ。斑点入りのグレージュ + 2m ごとの継ぎ目。
    ★絨毯と足音の材質を変えたい所に使う(音は Lua 側で分ける)。"""
    base = lin(150, 145, 131)
    speck = rng.random((N, N))
    v = 1.0 + 0.16 * (speck - 0.5)
    v = v * (1.0 - 0.10 * (fbm(5, 4, 0.55, 1301) - 0.5))
    seam = np.clip(1.0 - np.abs(yy - 0.5) / 0.004, 0, 1)      # 2m ごとの継ぎ目
    v = v * (1.0 - 0.30 * seam)
    # 擦り傷(細い弧)
    scratch = np.clip(fbm(96, 2, 0.5, 51) - 0.62, 0, 1) * 3.0
    v = v * (1.0 + 0.10 * scratch)
    col = base[None, None, :] * v[..., None]
    out("lm_vinyl_col.png", col)


def tile_floor():
    """プールルームの床タイル。16.7cm 角(2m に 12 枚) + 目地 + 濡れムラ。"""
    per = 12
    joint = grid_mask(per, 0.055)
    cid = cell_id(per, 5501)
    base = lin(170, 197, 191)
    grout = lin(132, 143, 138)
    v = 1.0 + 0.055 * (cid - 0.5)                              # タイルごとの色差
    v = v * (1.0 - 0.05 * (fbm(6, 4, 0.55, 71) - 0.5))
    col = base[None, None, :] * v[..., None]
    col = col * (1 - joint[..., None]) + joint[..., None] * grout[None, None, :]
    # 濡れて暗くなった所
    wet = np.clip(fbm(3, 4, 0.6, 173) - 0.52, 0, 1) * 2.0
    col = col * (1.0 - 0.38 * wet[..., None])
    out("lm_tilefloor_col.png", col)


def tile_wall():
    """プールルームの壁タイル。10cm 角(2m に 20 枚)。床より白く、目地は細い。"""
    per = 20
    joint = grid_mask(per, 0.05)
    cid = cell_id(per, 991)
    base = lin(206, 221, 215)
    grout = lin(163, 172, 167)
    v = 1.0 + 0.040 * (cid - 0.5) - 0.04 * (fbm(8, 4, 0.5, 133) - 0.5)
    col = base[None, None, :] * v[..., None]
    col = col * (1 - joint[..., None]) + joint[..., None] * grout[None, None, :]
    drip = np.clip(fbm(4, 4, 0.6, 613) * (0.5 + 0.8 * (1 - yy)) - 0.58, 0, 1) * 1.6
    col = col * (1.0 - 0.22 * drip[..., None])
    out("lm_tilewall_col.png", col)


# ================================================================ 天井・照明
def ceiling():
    """落とし天井。60cm 角(2m に 3.33 枚)の T バー + 吸音孔 + 雨漏り。"""
    per = 3.0
    gx = np.abs(((xx * per) % 1.0) - 0.5) * 2
    gy = np.abs(((yy * per) % 1.0) - 0.5) * 2
    g = np.maximum(gx, gy)
    bar = np.clip((g - 0.955) / 0.045, 0, 1)                   # T バー(明るい金属)
    holes = rng.random((N, N))
    perf = np.where(holes > 0.905, 1.0, 0.0) * 0.5
    base = lin(214, 211, 197)
    v = 1.0 - perf * 0.30
    v = v * (1.0 - 0.075 * (fbm(4, 4, 0.6, 55) - 0.5))
    stain = np.clip(fbm(2, 4, 0.62, 313) - 0.62, 0, 1) * 2.6
    col = base[None, None, :] * v[..., None]
    col = col * (1.0 - stain[..., None] * lin(150, 125, 80)[None, None, :])
    col = col * (1 - bar[..., None]) + bar[..., None] * lin(196, 194, 186)[None, None, :]
    out("lm_ceil_col.png", col)


def lamp():
    """蛍光灯の乳白カバー。★これは【光っているように見せる板】。
    ライトは別に置くので、ここは『白いが完全な白ではない』程度に留める
    (真っ白にすると露出が振られて部屋全体が暗くなる)。"""
    base = lin(247, 246, 236)
    prism = 0.5 + 0.5 * np.cos(xx * 2 * np.pi * 40) * np.cos(yy * 2 * np.pi * 40)
    v = 1.0 - 0.05 * prism - 0.02 * (fbm(8, 3, 0.5, 77) - 0.5)
    dust = np.clip(fbm(3, 3, 0.6, 1907) - 0.66, 0, 1) * 1.4     # 虫と埃の影
    v = v * (1.0 - 0.22 * dust)
    col = base[None, None, :] * v[..., None]
    out("lm_lamp_col.png", col)


# ================================================================ その他
def concrete():
    """穴の底と外周。暗く、ざらつく。"""
    base = lin(96, 94, 89)
    v = 1.0 - 0.26 * (fbm(5, 6, 0.55, 213) - 0.5)
    pit = np.where(rng.random((N, N)) > 0.986, 0.55, 1.0)
    col = base[None, None, :] * (v * pit)[..., None]
    out("lm_conc_col.png", col)


def paintwall():
    """扉・幅木・枠の塗装。刷毛目とわずかな黄ばみ。"""
    base = lin(196, 190, 175)
    brush = 0.5 + 0.5 * np.sin(yy * 2 * np.pi * 120 + fbm(16, 3, 0.5, 21) * 9)
    v = 1.0 - 0.034 * brush - 0.06 * (fbm(5, 4, 0.55, 63) - 0.5)
    col = base[None, None, :] * v[..., None] + (rng.random((N, N, 1)) - 0.5) * 0.010
    out("lm_paint_col.png", col)


def door():
    """フラッシュ戸。塗装 + 上下の framing の陰。★2m = 1タイルなので
    扉(1.0 x 2.1)には uvTiling 0.5 x 1.05 で貼る = 模様が縦に 1 枚だけ乗る。"""
    base = lin(178, 172, 156)
    v = 1.0 - 0.05 * (fbm(6, 4, 0.55, 401) - 0.5)
    brush = 0.5 + 0.5 * np.sin(yy * 2 * np.pi * 160)
    v = v * (1.0 - 0.020 * brush)
    edge = np.clip(1.0 - np.minimum(xx, 1 - xx) / 0.03, 0, 1)
    v = v * (1.0 - 0.20 * edge)
    col = base[None, None, :] * v[..., None]
    out("lm_door_col.png", col)


def rust():
    """金属(手すり・配管・扉の枠)。塗装が剥げて錆が出ている。"""
    base = lin(120, 122, 118)
    v = 1.0 - 0.16 * (fbm(6, 5, 0.55, 131) - 0.5) - 0.05 * (rng.random((N, N)) - 0.5)
    r = np.clip(fbm(4, 4, 0.6, 787) - 0.66, 0, 1) * 2.6
    col = base[None, None, :] * v[..., None]
    col = col * (1 - r[..., None]) + r[..., None] * lin(110, 68, 40)[None, None, :]
    out("lm_metal_col.png", col)


def exitsign():
    """非常口の標識。緑地に白のピクトと矢印。★この作品で緑は出口にしか使わない。"""
    base = lin(30, 130, 74)
    v = 1.0 - 0.05 * (fbm(6, 3, 0.5, 4801) - 0.5)
    col = base[None, None, :] * v[..., None]
    u, w = xx, yy
    e = np.minimum(np.minimum(u, 1 - u), np.minimum(w, 1 - w))
    frame = (e < 0.060) & (e > 0.028)
    # 走る人(簡略ピクト): 胴と脚と頭
    head = ((u - 0.36) ** 2 + (w - 0.72) ** 2) < 0.0042
    body = (np.abs((u - 0.40) - (w - 0.50) * 0.22) < 0.055) & (w > 0.36) & (w < 0.68)
    leg1 = (np.abs((u - 0.34) + (w - 0.36) * 0.55) < 0.045) & (w > 0.20) & (w < 0.40)
    leg2 = (np.abs((u - 0.50) - (w - 0.36) * 0.75) < 0.045) & (w > 0.20) & (w < 0.42)
    arm = (np.abs((u - 0.52) - (w - 0.58) * 0.9) < 0.040) & (w > 0.44) & (w < 0.64)
    # 右向きの矢印
    ah = (u > 0.66) & (u < 0.90) & (np.abs(w - 0.45) < (0.90 - u) * 0.85)
    ash = (u > 0.56) & (u <= 0.70) & (np.abs(w - 0.45) < 0.055)
    ink = frame | head | body | leg1 | leg2 | arm | ah | ash
    col = np.where(ink[..., None], lin(238, 246, 238)[None, None, :], col)
    # ★箱の -Z 面は u が -x 向き = 画像が左右反転して貼られる。標識は必ず -Z 側から
    #   見るので、ここで先に反転させておく(実物で正しい向きになる)。
    out("lm_exit_col.png", col[:, ::-1, :])


def edge():
    """継ぎ目の線に貼る無地(ReconnectInk を使わない箇所の保険)。"""
    v = 0.96 - 0.02 * (fbm(8, 3, 0.5, 1301) - 0.5)
    out("lm_plain_col.png", np.repeat(v[..., None], 3, -1))


if __name__ == "__main__":
    wallpaper(); wall_pale()
    carpet(); vinyl(); tile_floor(); tile_wall()
    ceiling(); lamp()
    concrete(); paintwall(); door(); rust(); exitsign(); edge()
    print("LIMINAL TEX DONE")
