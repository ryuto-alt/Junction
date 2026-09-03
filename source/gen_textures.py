# -*- coding: utf-8 -*-
"""JUNCTION の内装テクスチャを作る。出力は assets/models/tex/*.png。

★エンジンは glTF の baseColorFactor を読まない(テクスチャ無しの単色マテリアルは
  真っ白になる)。だから「白い壁」ですら col テクスチャが要る。

★全部タイル可能(周期ノイズ)。UV は Blender 側で 2m = 1タイル に切ってある。
  1024px / 2m = 512 texel/m。

★numpy は Blender 同梱の python にしか無い。実行(Blender のバージョンは環境で読み替える):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" gen_textures.py

★★【テクスチャを新しく足したら、エディタで必ず dx12_reload_assets を撃つこと】
  エンジンはテクスチャを【パスをキーに、プロセス起動から一生キャッシュする】。
  そして【読めなかった結果も同じようにキャッシュする】。
  つまり、まだ存在しないファイルを一度でも参照してしまったエディタは、
  あとからそのファイルを置いても【真っ黒のまま】になる。scene:setColor は乗算なので
  黒に何を掛けても黒 = 「モデルが壊れている」ようにしか見えない。
  band/lane で実際にこれを踏んだ。切り分け方(推測せずにこれで確定できる):
    同じ PNG のバイト列を【別名でコピー】して参照させる。それで直るなら
    中身ではなくキャッシュ = dx12_reload_assets{force:true} で直る。中身の問題ではない。
"""
import os, zlib, struct
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "assets", "models", "tex")
N = 1024
rng = np.random.default_rng(20260901)


def write_png(path, arr, gray=False):
    """arr: float 0..1, (H,W,3) か (H,W)。PNG を自前で組む。
    ★bpy.data.images.new + save は中身が黒のまま保存されることがあるので使わない。"""
    a = np.clip(arr, 0.0, 1.0)
    if gray:
        a = np.stack([a, a, a], axis=-1)
    b = (a * 255.0 + 0.5).astype(np.uint8)
    h, w, _ = b.shape
    # 各行頭に filter byte 0 が【1バイト】要る。(h,1,3) を concat すると 3 バイト付いて壊れる
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
    print("wrote", os.path.normpath(path), b.shape)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


# ---------------------------------------------------------------- ノイズ
def vnoise(freq, seed=None):
    """周期的な value noise。freq x freq の格子を双線形で N まで拡大(端は巻き戻す)。"""
    r = np.random.default_rng(seed) if seed is not None else rng
    g = r.random((freq, freq))
    idx = np.arange(N) * freq / N
    i0 = np.floor(idx).astype(int) % freq
    i1 = (i0 + 1) % freq
    t = idx - np.floor(idx)
    t = t * t * (3 - 2 * t)                       # smoothstep
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


def normal_from_height(h, strength=1.0):
    """高さ場 -> タンジェント空間ノーマル(OpenGL 系 +Y up)。端は巻き戻す。"""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength * N / 64.0
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength * N / 64.0
    nz = np.ones_like(h)
    L = np.sqrt(dx * dx + dy * dy + nz * nz)
    return np.stack([(-dx / L) * 0.5 + 0.5, (dy / L) * 0.5 + 0.5, (nz / L) * 0.5 + 0.5], -1)


yy, xx = np.mgrid[0:N, 0:N] / N     # 0..1 の UV(タイル1枚ぶん)


# ---------------------------------------------------------------- 壁紙
def wallpaper():
    """リミナルの主役。黄ばんだオフホワイトに、縦の極薄ストライプと染み。"""
    base = np.array([0.847, 0.827, 0.760])          # くすんだクリーム
    stripe = 0.5 + 0.5 * np.cos(xx * 2 * np.pi * 16)   # 2m に 16 本 = 12.5cm ピッチ
    v = 1.0 - 0.022 * stripe
    v = v * (1.0 - 0.055 * (fbm(4, 5, 0.55, 11) - 0.5))       # 大きなムラ
    grain = (rng.random((N, N)) - 0.5) * 0.018
    stain = np.clip(fbm(3, 4, 0.6, 401) - 0.62, 0, 1) * 2.4   # 疎らな染み
    col = base[None, None, :] * v[..., None]
    col = col * (1.0 - stain[..., None] * np.array([0.16, 0.22, 0.30])[None, None, :])
    col = col + grain[..., None]
    write_png(os.path.join(OUT, "wall_col.png"), srgb(col))

    h = 0.5 + 0.06 * stripe + 0.25 * fbm(64, 3, 0.5, 77)
    write_png(os.path.join(OUT, "wall_nrm.png"), normal_from_height(h, 0.35))


# ---------------------------------------------------------------- 絨毯
def carpet():
    """オフィス/ホテルの絨毯。くすんだ辛子色に、細かい斑と菱形の織り。"""
    base = np.array([0.300, 0.246, 0.138])
    speck = rng.random((N, N))
    fleck = np.where(speck > 0.86, 1.0, 0.0) * (0.35 + 0.5 * rng.random((N, N)))
    dark = np.where(speck < 0.12, 1.0, 0.0) * 0.30
    # 菱形の織り(2m に 8 目)
    weave = (np.sin((xx + yy) * 2 * np.pi * 8) * np.sin((xx - yy) * 2 * np.pi * 8))
    v = 1.0 + 0.10 * weave + 0.55 * fleck - dark
    v = v * (1.0 - 0.20 * (fbm(3, 4, 0.6, 909) - 0.5))        # 踏まれたムラ
    col = base[None, None, :] * v[..., None]
    col = col + fleck[..., None] * np.array([0.06, 0.05, 0.02])[None, None, :]
    write_png(os.path.join(OUT, "carpet_col.png"), srgb(col))

    h = 0.5 + 0.30 * (speck - 0.5) + 0.10 * weave
    write_png(os.path.join(OUT, "carpet_nrm.png"), normal_from_height(h, 1.5))


# ---------------------------------------------------------------- 天井
def ceiling():
    """吸音板の落とし天井。2m に 3.33 枚(=60cm 角)の目地と細かい孔。"""
    per = 3.0                                       # 2m に 3 枚 = 66cm 角
    gx = np.abs(((xx * per) % 1.0) - 0.5) * 2
    gy = np.abs(((yy * per) % 1.0) - 0.5) * 2
    grid = np.maximum(gx, gy)                        # 1 = 目地
    joint = np.clip((grid - 0.955) / 0.045, 0, 1)    # 目地のマスク

    holes = rng.random((N, N))
    perf = np.where(holes > 0.90, 1.0, 0.0) * 0.55   # 吸音孔
    v = 0.94 - perf * 0.35
    v = v * (1.0 - 0.06 * (fbm(4, 4, 0.6, 55) - 0.5))
    stain = np.clip(fbm(2, 4, 0.62, 313) - 0.66, 0, 1) * 3.0   # 雨漏りの染み
    base = np.array([0.885, 0.880, 0.850])
    col = base[None, None, :] * v[..., None]
    col = col * (1.0 - stain[..., None] * np.array([0.20, 0.26, 0.34])[None, None, :])
    col = col * (1.0 - joint[..., None] * 0.55)      # 目地は影
    write_png(os.path.join(OUT, "ceiling_col.png"), srgb(col))

    h = 0.55 - joint * 0.45 - perf * 0.15
    write_png(os.path.join(OUT, "ceiling_nrm.png"), normal_from_height(h, 0.9))


# ---------------------------------------------------------------- 塗装(枠・幅木)
def paint():
    """ドア枠と幅木の白塗装。刷毛目とわずかな黄ばみ。"""
    base = np.array([0.905, 0.893, 0.860])
    brush = 0.5 + 0.5 * np.sin(yy * 2 * np.pi * 130 + fbm(16, 3, 0.5, 21) * 9)
    v = 1.0 - 0.030 * brush - 0.05 * (fbm(5, 4, 0.55, 63) - 0.5)
    col = base[None, None, :] * v[..., None] + (rng.random((N, N, 1)) - 0.5) * 0.012
    write_png(os.path.join(OUT, "paint_col.png"), srgb(col))


# ---------------------------------------------------------------- 金属(通気口・照明)
def metal():
    """薄汚れた塗装金属。通気口・照明の枠に使う。"""
    base = np.array([0.560, 0.565, 0.555])
    v = 1.0 - 0.14 * (fbm(6, 5, 0.55, 131) - 0.5) - 0.06 * (rng.random((N, N)) - 0.5)
    rust = np.clip(fbm(4, 4, 0.6, 787) - 0.70, 0, 1) * 3.0
    col = base[None, None, :] * v[..., None]
    col = col * (1 - rust[..., None]) + rust[..., None] * np.array([0.28, 0.18, 0.11])[None, None, :]
    write_png(os.path.join(OUT, "metal_col.png"), srgb(col))


# ---------------------------------------------------------------- コンクリ(柱)
def concrete():
    base = np.array([0.470, 0.470, 0.455])
    v = 1.0 - 0.22 * (fbm(5, 6, 0.55, 213) - 0.5)
    pit = np.where(rng.random((N, N)) > 0.985, 0.55, 1.0)
    col = base[None, None, :] * (v * pit)[..., None]
    write_png(os.path.join(OUT, "concrete_col.png"), srgb(col))
    h = 0.5 + 0.4 * (fbm(64, 3, 0.5, 999) - 0.5) - (1 - pit) * 0.5
    write_png(os.path.join(OUT, "concrete_nrm.png"), normal_from_height(h, 0.8))


# ---------------------------------------------------------------- 無地(羅針・ピン)
def plain():
    """★羅針の扇/針とピンの頭に貼る無地。色は Lua の scene:setColor が【乗算】で乗せるので、
    模様を入れると色が濁って「どのスライスが行き先か」が読めなくなる。
    ほぼ白のまま、のっぺり見えない程度の粒だけ残す。"""
    v = 0.955 - 0.012 * (fbm(8, 3, 0.5, 1301) - 0.5) + (rng.random((N, N)) - 0.5) * 0.006
    write_png(os.path.join(OUT, "plain_col.png"), srgb(np.repeat(v[..., None], 3, -1)))


# ---------------------------------------------------------------- 木(木箱)
def wood():
    """木箱の板。部屋の識別に効くのは「他と material が違う」ことなので、
    内装(壁紙/絨毯/金属/コンクリ)のどれとも似ていない暖色を持たせる。"""
    base = np.array([0.365, 0.230, 0.120])
    # 2m に 5 枚の板。板ごとに明度をずらす
    plank = np.floor(yy * 5.0)
    shift = (np.sin(plank * 12.9898) * 43758.5453) % 1.0
    grain = fbm(3, 5, 0.55, 71) * 0.5 + 0.5 * np.sin((xx * 26.0 + fbm(4, 3, 0.5, 73) * 7.0) * np.pi)
    gap = np.clip(1.0 - np.abs(((yy * 5.0) % 1.0) - 0.0) * 60.0, 0, 1)   # 板の継ぎ目
    v = 1.0 + 0.22 * (shift - 0.5) + 0.16 * (grain - 0.5)
    v = v * (1.0 - 0.55 * gap)
    col = base[None, None, :] * v[..., None] + (rng.random((N, N, 1)) - 0.5) * 0.010
    write_png(os.path.join(OUT, "wood_col.png"), srgb(col))


# ---------------------------------------------------------------- 門の色帯 / 床のレーン
def gate():
    """★どちらも Lua の scene:setColor が【乗算】で行き先の色を乗せる。
    だから模様も境目もグラデーションも【明度だけ】で描く。色を持たせると行き先の色が濁る。

    band … 開口に立つ縦板。3 枚並べたときに【境目が読める】ことが要件なので、
           左右の縁に暗い線を入れる。帯は最小 0.5m まで細くなる(scale)ので、
           線は UV の割合で置く = 細い帯でも同じ割合で残る。
    lane … 床のレーン。先端(+Z 側 = 帯に接する側)が一番明るく、手前へ向かって暗くなる。
           「ここから入る道」に見せるための唯一の手掛かり。
    ★UV の縦は Blender -> glTF で反転する。lane は uv v=0(画像の【上】)が手前、
      v=1(画像の【下】)が帯側。だから yy が大きいほど明るくする。"""
    u = xx
    edge = np.minimum(u, 1.0 - u)                    # 0=縁, 0.5=中央

    # 縁: 芯の暗い線(片側 0.030) + その外の 0.10 までの緩い落ち込み。
    # ★線だけだと帯が細いときに 1cm 未満になって消える。落ち込みが「溝」として残る。
    core = np.clip(1.0 - edge / 0.030, 0, 1)         # 1 -> 0
    soft = np.clip(1.0 - edge / 0.110, 0, 1)
    seam = 1.0 - 0.62 * core - 0.20 * soft ** 2

    grain = 1.0 - 0.020 * (fbm(8, 3, 0.5, 2207) - 0.5) + (rng.random((N, N)) - 0.5) * 0.006
    brush = 1.0 - 0.022 * (0.5 + 0.5 * np.cos(yy * 2 * np.pi * 90))   # 縦板のヘアライン

    band = np.clip(0.965 * seam * grain * brush, 0, 1)
    # 足元と頭を少しだけ締める(板として自立して見える)
    band = band * (1.0 - 0.28 * np.clip(1.0 - yy / 0.022, 0, 1)
                       - 0.18 * np.clip(1.0 - (1.0 - yy) / 0.018, 0, 1))
    write_png(os.path.join(OUT, "band_col.png"), srgb(np.repeat(band[..., None], 3, -1)))

    # レーン: yy=1(帯側)で 1.0、yy=0(手前)で 0.30。手前ほど暗い = 淡く消えていく。
    g = 0.30 + 0.70 * (yy ** 1.35)
    # 帯に接する 3% は帯と同じ明るさで揃える(地続きに見せる継ぎ目)
    g = np.maximum(g, np.clip((yy - 0.97) / 0.03, 0, 1) * 0.98)
    lane = np.clip(0.965 * seam * g * grain, 0, 1)
    write_png(os.path.join(OUT, "lane_col.png"), srgb(np.repeat(lane[..., None], 3, -1)))


# ---------------------------------------------------------------- 出口(v8)
def exitsign():
    """★出口の標識。緑地に白の下向き矢印と枠。goal.gltf の庇に貼る。
    「ゴールがゴールに見えない(ただの白い枠の彫刻だった)」という指摘への答えで、
    このゲームで唯一【意味を持つ色】が緑。だから緑は出口以外に使わない。
    UV は 0..1 を面いっぱいに張る(Build.face に明示 UV を渡す)。
    ★Blender -> glTF で V が反転するので、画像の【上】が実物の【下】になる。
      矢印は実物で下を向かせたいので、画像では上を向けて描く。"""
    GREEN = np.array([0.055, 0.560, 0.290])
    v = 1.0 - 0.05 * (fbm(6, 3, 0.5, 4801) - 0.5)
    col = GREEN[None, None, :] * v[..., None]
    u, w = xx, yy                # ★実測: 画像の上がそのまま実物の上だった。
    #   下向きの矢印にしたいので、画像でも下を向けて描く(w が小さいほど先端)
    # 外枠(白)
    e = np.minimum(np.minimum(u, 1 - u), np.minimum(yy, 1 - yy))
    frame = (e < 0.055) & (e > 0.022)
    # 矢印(画像の上を向く三角 + 軸)。実物では下向きになる
    cx0 = 0.5
    # ★実測 2 回: 画像の【上】がそのまま実物の上。下向きにするには画像でも下(yy 大)に先端。
    head = (w > 0.58) & (w < 0.90) & (np.abs(u - cx0) < (0.90 - w) * 0.95)
    shaft = (w > 0.14) & (w <= 0.60) & (np.abs(u - cx0) < 0.105)
    ink = frame | head | shaft
    col = np.where(ink[..., None], np.array([0.94, 0.96, 0.94])[None, None, :], col)
    write_png(os.path.join(OUT, "exit_col.png"), srgb(col))


def darkmetal():
    """出口の門の枠。★白い部屋の中で【輪郭が立つ】のが仕事なので、既存の metal(0.56 灰)
    では明るすぎて壁に溶けた(v8 実測)。炭色まで落とす。"""
    base = np.array([0.088, 0.092, 0.100])
    v = 1.0 - 0.30 * (fbm(6, 5, 0.55, 6151) - 0.5) - 0.05 * (rng.random((N, N)) - 0.5)
    write_png(os.path.join(OUT, "dark_col.png"), srgb(base[None, None, :] * v[..., None]))


def glow():
    """出口の敷居と床の矢羽根に貼る、模様の無い明るい緑。"""
    g = np.array([0.045, 0.520, 0.255])
    v = 1.0 - 0.04 * (fbm(8, 3, 0.5, 5303) - 0.5)
    write_png(os.path.join(OUT, "glow_col.png"), srgb(g[None, None, :] * v[..., None]))


if __name__ == "__main__":
    wallpaper(); carpet(); ceiling(); paint(); metal(); concrete()
    plain(); wood(); gate(); exitsign(); glow(); darkmetal()
    print("done")
