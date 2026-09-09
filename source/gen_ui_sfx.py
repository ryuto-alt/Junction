# -*- coding: utf-8 -*-
"""メニューの操作音と決定音を作る。出力は assets/audio/ui/{nav,enter}.wav。

★なぜ gen_sfx.py に足さないのか:
  gen_sfx.py は numpy を使う ＝ Blender 同梱の python でしか走らない。
  この 2 音は数千サンプルしかないので、標準ライブラリ(wave / math / random)だけで
  書ける。手元の python-embed でそのまま回せるほうが、あとで耳で詰めるときに速い。
  実行:  ~/dev/tools/python-embed/python.exe source/gen_ui_sfx.py

★作りの方針は gen_sfx.py と同じにしてある(あちらの 11 個と並べて聞くため):
  ・44100Hz / 16bit / モノラル
  ・先頭と末尾を余弦で寝かせてクリックを殺す
  ・倍音は非整数比。【音程を持たせない】── 明るいチャイムにした瞬間に
    「無人の廃墟」が「ゲームのメニュー」になる
  ・減衰は速く、余韻は乾いた小部屋の残響だけ

★既存の音との棲み分け(assets/audio/ui/ の 11 個を実際に開いて決めた):
    detent 24ms/-9dB  高いカチッ。回る筒の【当たり】の音として本編で意味が付いている
    pin    150ms      金属の打点。破片が刺さる音
    pass   300ms      空気が抜ける。扉をくぐる音
    open   400ms      上昇ノイズ。虚無が開く音
  どれも【世界の中で意味を持っている】ので、メニューへ流用すると意味が二重になる。
  そこで「機械のスイッチ」という同じ質感のまま、意味の空いている 2 音を新しく作る。

★操作音と決定音は【はっきり別物】にする:
    nav    45ms  1650Hz を芯にした乾いた接点の音。体はほとんど無い
    enter  300ms 104Hz の体 + 低い金属 + 小部屋の残響。低く・長く・重い
  ピークは nav が -9dBFS(何十回も鳴るので detent と同じ扱い)、
  enter が -5dBFS(1 回しか鳴らないので少しだけ前に出す)。
"""
import math
import os
import random
import wave

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "audio", "ui")
rng = random.Random(20260909)


# ---------------------------------------------------------------- 土台
def n_of(dur):
    return int(round(dur * SR))


def zeros(n):
    return [0.0] * n


def noise(n):
    return [rng.gauss(0.0, 1.0) for _ in range(n)]


def svf(x, fc, q=1.0, mode="bp"):
    """Chamberlin の state variable filter。gen_sfx.py の svf と同じ式。
    ★安定域は fc < SR/4。ここは掃引しないのでスカラだけ受ける。"""
    f = 2.0 * math.sin(math.pi * min(max(fc, 10.0), SR * 0.24) / SR)
    damp = 1.0 / max(q, 0.5)
    low = band = 0.0
    out = zeros(len(x))
    for i, xi in enumerate(x):
        low += f * band
        high = xi - low - damp * band
        band += f * high
        out[i] = low if mode == "lp" else (band if mode == "bp" else high)
    return out


def room(x, wet=0.22):
    """乾いたコンクリの小箱。畳み込みは標準ライブラリだと重いので、
    互いに素な長さの櫛形遅延 3 本 + 減衰で済ませる。
    ★狙いは「残響」ではなく【箱の中で鳴った】という手触りだけ。"""
    taps = ((int(0.0131 * SR), 0.36), (int(0.0197 * SR), 0.27), (int(0.0289 * SR), 0.19))
    n = len(x)
    y = list(x)
    for d, g in taps:
        buf = zeros(n)
        lp = 0.0
        for i in range(n):
            v = y[i] + (buf[i - d] if i >= d else 0.0) * g
            lp += (v - lp) * 0.42          # 反射のたびに高域が減る
            buf[i] = lp
        for i in range(n):
            y[i] = y[i] * (1 - wet) + buf[i] * wet
    return y


def fade(x, fin=0.004, fout=0.012):
    y = list(x)
    a = min(n_of(fin), len(y) // 2)
    b = min(n_of(fout), len(y) // 2)
    for i in range(a):
        y[i] *= 0.5 - 0.5 * math.cos(math.pi * i / a)
    for i in range(b):
        y[len(y) - b + i] *= 0.5 + 0.5 * math.cos(math.pi * i / b)
    return y


def norm(x, dbfs):
    p = max(abs(v) for v in x)
    if p < 1e-12:
        return x
    k = (10.0 ** (dbfs / 20.0)) / p
    return [v * k for v in x]


def write_wav(name, x, dbfs):
    y = norm(fade(x), dbfs)
    pcm = bytearray()
    for v in y:
        s = int(round(v * 32767.0))
        s = -32768 if s < -32768 else (32767 if s > 32767 else s)
        pcm += (s & 0xFFFF).to_bytes(2, "little")
    p = os.path.join(OUT, name)
    os.makedirs(OUT, exist_ok=True)
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(pcm))
    print("wrote %-12s %6d frames  %5.3f s" % (name, len(y), len(y) / SR))
    return p


# ---------------------------------------------------------------- 各音
def s_nav():
    """メニューの操作音。選択が 1 つ動いた(45ms)。

    リレーの接点が離れて次の段に噛む音。detent(2300Hz)より一段低い 1650Hz を芯に、
    下に 820Hz、上に薄い 3100Hz。低音(118Hz)は【当たりの気配】程度にしか入れない ──
    ここを鳴らすと決定音と区別が付かなくなる(実測: 0.07 でもう低音が主役になった。
    共振の減衰は Q が決めるので、掛けたつもりの exp() では低音を抑えられない)。
    """
    n = n_of(0.045)
    imp = zeros(n)
    imp[0] = 1.0
    nz = noise(5)
    for i in range(5):
        imp[i] += nz[i] * 0.30
    a = svf(imp, 1650.0, 5.5, "bp")
    b = svf(imp, 3100.0, 4.5, "bp")
    c = svf(imp, 820.0, 7.0, "bp")
    y = zeros(n)
    for i in range(n):
        t = i / SR
        y[i] = (a[i] * math.exp(-t * 150.0)
                + b[i] * 0.36 * math.exp(-t * 300.0)
                + c[i] * 0.55 * math.exp(-t * 190.0)
                + 0.018 * math.sin(2 * math.pi * 118.0 * t) * math.exp(-t * 200.0))
    return y


def s_enter():
    """決定音。選んだものが噛み合った(300ms)。

    配電盤の刃形スイッチを倒した音。操作音より【低く・長く・重い】。
      ・接点の当たり ── 3ms のノイズを 1100Hz で帯域制限
      ・金属の鳴り   ── 640 / 934 / 1417Hz。比は 1.459 / 2.214 の非整数
                        (完全 5 度や長 3 度を入れると途端に「音楽」になる)
      ・体           ── 104Hz が 92Hz へわずかに垂れる。これが「重さ」
      ・小部屋の残響 ── コンクリの箱の中で鳴ったことだけ伝える
    """
    n = n_of(0.300)
    k = n_of(0.003)
    imp = zeros(n)
    imp[0] = 1.0
    nz = noise(k)
    for i in range(k):
        imp[i] += nz[i] * (1.0 - i / k) * 0.9
    hit = svf(imp, 1100.0, 2.2, "bp")

    y = zeros(n)
    ph = [rng.random() * 6.28318 for _ in range(3)]
    for i in range(n):
        t = i / SR
        # 金属の部分音(非整数比)
        m = (1.00 * math.sin(2 * math.pi * 640.0 * t + ph[0]) * math.exp(-t * 30.0)
             + 0.50 * math.sin(2 * math.pi * 934.0 * t + ph[1]) * math.exp(-t * 42.0)
             + 0.26 * math.sin(2 * math.pi * 1417.0 * t + ph[2]) * math.exp(-t * 58.0))
        # 体。104 → 92Hz へ 0.12 秒かけて垂れる。
        # ★位相は周波数の【積分】で作る。f を直に sin へ入れると段差でブツッと鳴る。
        #   f(t) = 104 - 12*t/0.12  (t<0.12) なので ∫ = 104t - 50t^2、以降は 92t + 0.72。
        bph = 2 * math.pi * ((104.0 * t - 50.0 * t * t) if t < 0.12 else (92.0 * t + 0.72))
        body = math.sin(bph) * math.exp(-t * 21.0)
        y[i] = hit[i] * 0.55 + m * 0.34 + body * 0.62
    return room(y, 0.22)


# ---------------------------------------------------------------- 検証
def verify(paths):
    print("\n--- verify ------------------------------------------------------")
    ok = True
    for p, want in paths:
        with wave.open(p, "rb") as w:
            ch, sw, sr, nf = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(nf)
        xs = [int.from_bytes(raw[i:i + 2], "little", signed=True) / 32768.0
              for i in range(0, len(raw), 2)]
        peak = max(abs(v) for v in xs)
        db = 20 * math.log10(peak)
        bad = []
        if (ch, sw, sr) != (1, 2, SR):
            bad.append("format")
        if nf == 0 or nf != len(xs):
            bad.append("frames")
        if abs(db - want) > 0.35:
            bad.append("peak%.2f" % db)
        if abs(xs[0]) > 0.02 or abs(xs[-1]) > 0.02:
            bad.append("edge")
        print("%-14s ch%d %dbit %dHz  %5d fr %5.3fs  peak %6.2f dBFS  head %.4f tail %.4f  %s"
              % (os.path.basename(p), ch, sw * 8, sr, nf, nf / sr, db,
                 abs(xs[0]), abs(xs[-1]), "OK" if not bad else "NG " + ",".join(bad)))
        ok &= not bad
    print("--- %s" % ("all OK" if ok else "FAILED"))
    return ok


if __name__ == "__main__":
    out = [(write_wav("nav.wav", s_nav(), -9.0), -9.0),
           (write_wav("enter.wav", s_enter(), -5.0), -5.0)]
    raise SystemExit(0 if verify(out) else 1)
