# -*- coding: utf-8 -*-
"""JUNCTION の効果音を作る。出力は assets/audio/{ui,amb}/*.wav。

★外部素材も外部ライブラリも使わない。numpy で波形を合成し、標準ライブラリ
  wave で 16bit PCM / 44100Hz / モノラル を直書きする(gen_textures.py と同じ流儀)。

★世界観は「白い虚無しかない無機質な建物」。明るいピコピコ音は禁止。
  倍音は少なく、減衰は速く、余韻は乾いた小さな残響だけ。喋らせない。

★どの音も先頭 5ms のフェードインと末尾のフェードアウトを入れてクリックを殺す。
  例外は amb/hum.wav。あれは【ループ用】なので、フェードを入れると 4 秒ごとに
  音量が凹んで継ぎ目が聞こえてしまう。代わりに「全成分の周期が長さの約数」に
  なるよう作ってあり(トーンは 0.25Hz の整数倍、ノイズは rfft を逆変換して作った
  完全周期ノイズ)、末尾と先頭が数学的に連続する。

★ピークは -3dBFS に正規化。detent.wav だけ -9dBFS(何百回も鳴るので煩い)。

★numpy は Blender 同梱の python にしか無い。実行:
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" gen_sfx.py
  (5.1 は消えていて 5.2 になっていた)
"""
import os
import wave
import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "audio")
rng = np.random.default_rng(20260901)


# ---------------------------------------------------------------- 土台
def tarr(dur):
    """dur 秒ぶんの時間軸(サンプル境界)。"""
    return np.arange(int(round(dur * SR))) / SR


def noise(n):
    return rng.standard_normal(n)


def fade(x, fin=0.005, fout=0.010):
    """先頭 fin 秒・末尾 fout 秒を余弦で寝かせる。スピーカーのクリック対策。"""
    y = x.copy()
    a = min(int(fin * SR), len(y) // 2)
    b = min(int(fout * SR), len(y) // 2)
    if a > 0:
        y[:a] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))
    if b > 0:
        y[-b:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, b))
    return y


def norm(x, dbfs=-3.0):
    p = np.max(np.abs(x))
    if p < 1e-12:
        return x
    return x * (10.0 ** (dbfs / 20.0)) / p


def svf(x, fc, q=1.0, mode="bp"):
    """Chamberlin の state variable filter。fc はスカラでも配列(掃引)でもよい。
    ★1 サンプルずつ回すが、最長でも 4 秒 = 17 万回なので実用上は一瞬。
      安定域は fc < SR/4。掃引はそこで頭打ちにする。"""
    n = len(x)
    fc = np.broadcast_to(np.asarray(fc, float), (n,))
    f = 2.0 * np.sin(np.pi * np.clip(fc, 10.0, SR * 0.24) / SR)
    damp = 1.0 / max(q, 0.5)
    low = band = 0.0
    out = np.empty(n)
    for i in range(n):
        low += f[i] * band
        high = x[i] - low - damp * band
        band += f[i] * high
        out[i] = {"lp": low, "bp": band, "hp": high}[mode]
    return out


def fftconv(x, h):
    n = len(x) + len(h) - 1
    m = 1 << (n - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(h, m), m)[:n]
    return y


def reverb(x, tail=0.28, tau=0.055, wet=0.35):
    """乾いた小部屋。ノイズを指数で潰しただけの短い IR を畳む。
    コンクリの箱の残響が欲しいだけなので、これで十分(そして安い)。"""
    n = int(tail * SR)
    t = np.arange(n) / SR
    ir = noise(n) * np.exp(-t / tau)
    ir = svf(ir, 2400.0, 0.7, "lp")
    ir[0] += 1.0                      # 直接音
    y = fftconv(x, ir / np.max(np.abs(ir)))
    y = y[:len(x) + n]
    d = np.zeros_like(y)
    d[:len(x)] = x
    return d * (1 - wet) + y * wet


def write_wav(path, x, dbfs=-3.0, do_fade=True, fin=0.005, fout=0.010):
    y = fade(x, fin, fout) if do_fade else x.copy()
    y = norm(y, dbfs)
    pcm = np.clip(np.round(y * 32767.0), -32768, 32767).astype("<i2")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote %-40s %6d frames  %5.2f s" % (os.path.basename(path), len(pcm), len(pcm) / SR))


# ---------------------------------------------------------------- 各音
def s_touch():
    """射程に入った。ごく短い低いトーン(80ms)。
    「気づかせる」だけで「褒めない」。倍音は 2 倍音を薄く乗せるだけ。"""
    t = tarr(0.080)
    env = np.exp(-t * 34.0)
    y = np.sin(2 * np.pi * 128.0 * t) * env
    y += 0.22 * np.sin(2 * np.pi * 256.0 * t) * np.exp(-t * 60.0)
    return y


def s_open():
    """虚無が開いた。息を吸うような上昇ノイズ(400ms)。
    バンドパスを 180→2600Hz へ掃引し、音量も一緒に持ち上げて最後だけ引く。"""
    t = tarr(0.400)
    u = t / t[-1]
    fc = 180.0 * (2600.0 / 180.0) ** (u ** 1.3)
    y = svf(noise(len(t)) * 0.5, fc, 3.2, "bp")
    y += 0.25 * svf(noise(len(t)) * 0.5, fc * 0.5, 1.4, "bp")
    env = u ** 1.6
    env *= np.clip((1.0 - u) / 0.18, 0, 1) ** 0.6      # 末尾 18% ですっと止める
    return y * env


def s_detent():
    """扇の境界をまたいだ。カチッ(24ms)。ダイヤルの手応え。
    ★何百回も鳴るので -9dBFS。長いと連打で濁るので、減衰は極端に速くする。"""
    t = tarr(0.024)
    imp = np.zeros(len(t))
    imp[0] = 1.0
    imp[:6] += noise(6) * 0.35
    y = svf(imp, 2300.0, 6.0, "bp") * np.exp(-t * 260.0)
    y += 0.4 * svf(imp, 4700.0, 5.0, "bp") * np.exp(-t * 420.0)
    return y


def s_connect():
    """接続成立。2 音の上昇 + 短い残響(600ms)。
    ★完全 5 度(147→220Hz)。長 3 度を使うと途端に「明るいゲーム」の顔になる。"""
    n = int(0.600 * SR)
    y = np.zeros(n)
    for k, (f0, at) in enumerate([(147.0, 0.00), (220.0, 0.085)]):
        i = int(at * SR)
        t = np.arange(n - i) / SR
        e = np.exp(-t * 11.0) * (1 - np.exp(-t * 900.0))
        v = np.sin(2 * np.pi * f0 * t) + 0.30 * np.sin(2 * np.pi * f0 * 2 * t)
        v += 0.10 * np.sin(2 * np.pi * f0 * 3.01 * t)
        y[i:] += v * e * (0.8 + 0.2 * k)
    return reverb(y, 0.30, 0.05, 0.30)[:n]


def s_pin():
    """ピンが刺さった。金属の打点(150ms)。
    非整数倍の部分音を 5 本重ねる = 板を叩いた音。頭に短いノイズの当たりを付ける。"""
    t = tarr(0.150)
    y = np.zeros(len(t))
    for f, a, d in [(1180., 1.00, 26.), (1723., 0.62, 34.), (2410., 0.44, 46.),
                    (3390., 0.28, 60.), (5120., 0.16, 85.)]:
        y += a * np.sin(2 * np.pi * f * t + rng.random() * 6.28) * np.exp(-t * d)
    k = int(0.004 * SR)
    y[:k] += noise(k) * np.linspace(1.0, 0.0, k) * 1.4
    y += 0.35 * np.sin(2 * np.pi * 190.0 * t) * np.exp(-t * 55.0)   # 打った体
    return y


def s_deny():
    """予算切れ / 狙い外し。低い鈍い音(200ms)。
    ★ブザーにしない。ピッチをわずかに落として「潰れた」感じだけ残す。"""
    t = tarr(0.200)
    u = t / t[-1]
    ph = 2 * np.pi * (78.0 * t - 0.5 * 26.0 * t * t / t[-1])        # 78→52Hz
    y = np.sin(ph) + 0.35 * np.sin(2 * ph)
    y = y * np.exp(-t * 16.0)
    y += 0.5 * svf(noise(len(t)), 150.0, 0.8, "lp") * np.exp(-t * 30.0)
    return y * (1 - 0.15 * u)


def s_pass():
    """ドアを通過。空気が抜ける短いホワイトノイズ(300ms)。
    バンドパスを 5200→320Hz へ落とす = 圧が抜けていく向き。"""
    t = tarr(0.300)
    u = t / t[-1]
    fc = 5200.0 * (320.0 / 5200.0) ** (u ** 0.75)
    y = svf(noise(len(t)) * 0.5, fc, 1.1, "bp")
    y += 0.30 * svf(noise(len(t)) * 0.5, 900.0, 0.7, "lp")
    env = (1 - np.exp(-t * 260.0)) * np.exp(-t * 9.0)
    return y * env


def s_clear():
    """クリア。澄んだ 3 音(1.2s)。
    ★ファンファーレにしない。完全 4/5 度だけの空虚な 3 音を、正弦に近い音色で。"""
    n = int(1.200 * SR)
    y = np.zeros(n)
    for k, f0 in enumerate([293.66, 440.0, 587.33]):                # D4 - A4 - D5
        i = int(k * 0.22 * SR)
        t = np.arange(n - i) / SR
        e = np.exp(-t * 4.2) * (1 - np.exp(-t * 500.0))
        v = np.sin(2 * np.pi * f0 * t) + 0.16 * np.sin(2 * np.pi * f0 * 2 * t)
        y[i:] += v * e * (1.0 - 0.12 * k)
    return reverb(y, 0.45, 0.10, 0.34)[:n]


def s_fail():
    """失敗。落ちる 1 音(1.0s)。建物が白に還るところに敷く。
    指数で 210→48Hz まで滑り落ちる。位相を積分で作らないと段差でブツッと鳴る。"""
    t = tarr(1.000)
    u = t / t[-1]
    f = 210.0 * (48.0 / 210.0) ** (u ** 0.8)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.30 * np.sin(2 * ph) * np.exp(-t * 3.0)
    y = y * np.exp(-t * 2.3)
    y += 0.22 * svf(noise(len(t)), 320.0, 0.8, "lp") * np.exp(-t * 5.0)
    return y


def s_hum(dur=4.0):
    """蛍光灯のハム + 空調(4.0s、継ぎ目なくループ)。
    ★ループの継ぎ目を消す唯一の方法は「全成分の周期が dur の約数」であること。
      - トーン: 60/120/180/240/300Hz は 1/4.0 = 0.25Hz の整数倍なので OK。
      - ノイズ: rfft の係数にランダム位相を入れて irfft する = 周期 dur の
        完全周期ノイズになる。時間軸で作った白色ノイズだと端が繋がらない。
    だからこの音だけフェードを掛けない(掛けると 4 秒ごとに凹む)。"""
    n = int(round(dur * SR))
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f, a in [(60., 1.00), (120., 0.55), (180., 0.30), (240., 0.14), (300., 0.07)]:
        assert abs(f * dur - round(f * dur)) < 1e-9, "周期が長さの約数でない"
        y += a * np.sin(2 * np.pi * f * t + rng.random() * 6.28)

    # 周期ノイズ(空調)。低域寄りのピンクっぽい傾斜 + 8kHz 以上は落とす
    spec = np.zeros(n // 2 + 1, complex)
    fr = np.fft.rfftfreq(n, 1 / SR)
    amp = np.zeros_like(fr)
    nz = fr > 0
    amp[nz] = (fr[nz] ** -0.9) * np.exp(-(fr[nz] / 5200.0) ** 2)
    spec = amp * np.exp(1j * rng.random(len(fr)) * 2 * np.pi)
    spec[0] = 0.0
    air = np.fft.irfft(spec, n)
    air = air / np.max(np.abs(air))

    # 明滅のうねりも周期の約数(0.25Hz と 0.5Hz)にしておく
    wob = 1.0 + 0.05 * np.sin(2 * np.pi * 0.25 * t) + 0.03 * np.sin(2 * np.pi * 0.5 * t)
    return (y / 2.06 * 0.55 + air * 0.75) * wob


# ---------------------------------------------------------------- 検証
def verify():
    """出した WAV を開き直して確かめる。「たぶん出た」で終わらせない。"""
    print("\n--- verify -------------------------------------------------------")
    ok = True
    for rel in FILES:
        p = os.path.join(OUT, rel)
        sz = os.path.getsize(p)
        with wave.open(p, "rb") as w:
            ch, sw, sr, nf = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            x = np.frombuffer(w.readframes(nf), "<i2").astype(float) / 32768.0
        peak = np.max(np.abs(x))
        db = 20 * np.log10(peak)
        head, tailv = abs(x[0]), abs(x[-1])
        want = -9.0 if "detent" in rel else -3.0
        bad = []
        if (ch, sw, sr) != (1, 2, SR):
            bad.append("format")
        if nf != len(x) or nf == 0:
            bad.append("frames")
        if abs(db - want) > 0.35:
            bad.append("peak%.2f" % db)
        if not (1000 < sz < 2_000_000):
            bad.append("size")
        extra = ""
        if rel.endswith("hum.wav"):
            # ループの継ぎ目: 末尾→先頭の段差が、内部の普通の隣接差と同程度か
            step = abs(x[0] - x[-1])
            typ = np.percentile(np.abs(np.diff(x)), 99)
            extra = "  loop seam=%.5f (p99 step=%.5f)" % (step, typ)
            if step > typ * 3:
                bad.append("seam")
        else:
            if head > 0.02 or tailv > 0.02:
                bad.append("edge")
        print("%-18s %7dB  ch%d %dbit %dHz  %6d fr  peak %6.2f dBFS  "
              "head %.4f tail %.4f%s  %s"
              % (rel, sz, ch, sw * 8, sr, nf, db, head, tailv, extra,
                 "OK" if not bad else "NG " + ",".join(bad)))
        ok &= not bad
    print("--- %s" % ("all OK" if ok else "FAILED"))
    return ok


FILES = ["ui/touch.wav", "ui/open.wav", "ui/detent.wav", "ui/connect.wav",
         "ui/pin.wav", "ui/deny.wav", "ui/pass.wav", "ui/clear.wav",
         "ui/fail.wav", "amb/hum.wav"]


if __name__ == "__main__":
    write_wav(os.path.join(OUT, "ui/touch.wav"), s_touch(), fout=0.012)
    write_wav(os.path.join(OUT, "ui/open.wav"), s_open(), fout=0.030)
    write_wav(os.path.join(OUT, "ui/detent.wav"), s_detent(), -9.0, fin=0.0004, fout=0.003)
    write_wav(os.path.join(OUT, "ui/connect.wav"), s_connect(), fout=0.040)
    write_wav(os.path.join(OUT, "ui/pin.wav"), s_pin(), fout=0.020)
    write_wav(os.path.join(OUT, "ui/deny.wav"), s_deny(), fout=0.025)
    write_wav(os.path.join(OUT, "ui/pass.wav"), s_pass(), fout=0.030)
    write_wav(os.path.join(OUT, "ui/clear.wav"), s_clear(), fout=0.060)
    write_wav(os.path.join(OUT, "ui/fail.wav"), s_fail(), fout=0.060)
    write_wav(os.path.join(OUT, "amb/hum.wav"), s_hum(), do_fade=False)   # ループ用
    raise SystemExit(0 if verify() else 1)
