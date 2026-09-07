# -*- coding: utf-8 -*-
"""リミナル版ステージの音。出力は assets/audio/lm/*.wav。

★実行: "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" source/gen_liminal_sfx.py

★方針(このステージは文字を出さないので、音が案内の半分を担う):
  ・drone … 継ぎ目の合い具合を【ピッチと音量】で伝える唯一の連続量。ループの継ぎ目が
    聞こえると台無しなので、全成分の周期を長さの約数にする(4.0 秒 = 0.25Hz の整数倍)。
  ・buzz  … 蛍光灯。空間音として灯の位置に置く。これがあるだけで『無人の建物』になる。
  ・lock  … 確定。褒めない。低い衝撃 + 短い金属の余韻だけ。
  ・step  … 絨毯とタイルで別。足音があると『自分がそこに居る』感じが出る。
"""
import os, wave
import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "audio", "lm")
rng = np.random.default_rng(20260905)


def tarr(dur):
    return np.arange(int(round(dur * SR))) / SR


def noise(n):
    return rng.standard_normal(n)


def periodic_noise(dur, lo, hi):
    """長さちょうどで完全に周期する帯域ノイズ(ループの継ぎ目が鳴らない)。"""
    n = int(round(dur * SR))
    spec = np.zeros(n // 2 + 1, complex)
    f = np.fft.rfftfreq(n, 1 / SR)
    band = (f >= lo) & (f <= hi)
    ph = rng.random(band.sum()) * 2 * np.pi
    spec[band] = np.exp(1j * ph)
    y = np.fft.irfft(spec, n)
    return y / (np.max(np.abs(y)) + 1e-9)


def fade(x, fin=0.005, fout=0.010):
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
    return x if p < 1e-12 else x * (10.0 ** (dbfs / 20.0)) / p


def svf(x, fc, q=1.0, mode="bp"):
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
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(h, m), m)[:n]


def reverb(x, tail=0.35, tau=0.070, wet=0.30):
    n = int(tail * SR)
    t = np.arange(n) / SR
    ir = noise(n) * np.exp(-t / tau)
    ir = svf(ir, 2600.0, 0.7, "lp")
    ir[0] += 1.0
    y = fftconv(x, ir / np.max(np.abs(ir)))
    d = np.zeros_like(y)
    d[:len(x)] = x
    return d * (1 - wet) + y * wet


def write(path, x, dbfs=-3.0, do_fade=True, fin=0.005, fout=0.012):
    y = fade(x, fin, fout) if do_fade else x.copy()
    y = norm(y, dbfs)
    pcm = np.clip(np.round(y * 32767.0), -32768, 32767).astype("<i2")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote %-22s %5.2f s" % (os.path.basename(path), len(pcm) / SR))


# ---------------------------------------------------------------- ループ音
def drone():
    """継ぎ目が合ってくると鳴る音。ピッチを 0.8〜1.7 倍に振って使う。
    ★4.0 秒ちょうどで周期する: 全部 0.25Hz の整数倍 + AM も 0.25Hz の整数倍。"""
    D = 4.0
    t = tarr(D)
    y = np.zeros_like(t)
    for f, a in ((110.0, 1.00), (220.0, 0.42), (330.0, 0.20), (440.0, 0.09)):
        y += a * np.sin(2 * np.pi * f * t)
    y *= 1.0 + 0.18 * np.sin(2 * np.pi * 0.5 * t)            # ゆっくりうねる
    y += 0.05 * periodic_noise(D, 400, 2400)                  # 息づかい
    write(os.path.join(OUT, "drone.wav"), y, -10.0, do_fade=False)


def buzz():
    """蛍光灯のバラスト。100Hz の唸り + 高域のちりちり。とても小さく鳴らす。"""
    D = 2.0
    t = tarr(D)
    y = 0.0
    for f, a in ((100.0, 1.0), (200.0, 0.55), (300.0, 0.22), (500.0, 0.08)):
        y = y + a * np.sin(2 * np.pi * f * t + f * 0.01)
    crack = periodic_noise(D, 2000, 9000)
    gate = (0.5 + 0.5 * np.sin(2 * np.pi * 100.0 * t)) ** 6   # 山の頂点だけ通す
    y = y * 0.5 + crack * gate * 0.55
    write(os.path.join(OUT, "buzz.wav"), y, -14.0, do_fade=False)


# ---------------------------------------------------------------- 単発
def lock():
    """継ぎ目が確定した瞬間。低い衝撃 + 木と金属の中間の余韻。褒め音にしない。"""
    t = tarr(1.30)
    thud = np.sin(2 * np.pi * (58.0 * np.exp(-t * 1.6)) * t) * np.exp(-t * 7.0)
    clack = svf(noise(len(t)) * np.exp(-t * 90.0), 1800.0, 2.2, "bp")
    ring = np.zeros_like(t)
    for f, a, d in ((196.0, 0.55, 3.2), (294.0, 0.34, 4.0), (392.0, 0.20, 5.2)):
        ring += a * np.sin(2 * np.pi * f * t) * np.exp(-t * d)
    y = thud * 1.0 + clack * 0.55 + ring * 0.45
    write(os.path.join(OUT, "lock.wav"), reverb(y, 0.40, 0.08, 0.28), -4.0)


def tick():
    """近づいた合図。40ms。控えめ(何度も鳴る)。"""
    t = tarr(0.045)
    y = np.sin(2 * np.pi * 880.0 * t) * np.exp(-t * 90.0)
    y += 0.3 * np.sin(2 * np.pi * 1320.0 * t) * np.exp(-t * 150.0)
    write(os.path.join(OUT, "tick.wav"), y, -18.0)


def reveal():
    """壁板が落ちる/階段が組み上がる。低い擦れとゴロゴロ。"""
    t = tarr(1.9)
    body = svf(noise(len(t)), 140.0 + 90.0 * np.exp(-t * 1.2), 1.1, "lp")
    body *= np.clip(1.0 - np.abs(t - 0.55) / 0.9, 0, 1) ** 1.5
    grit = svf(noise(len(t)), 2600.0, 1.4, "bp") * np.exp(-t * 2.4) * 0.35
    thud = np.sin(2 * np.pi * 44.0 * t) * np.exp(-np.maximum(t - 1.15, 0) * 9.0) * (t > 1.15)
    y = body * 1.0 + grit + thud * 0.8
    write(os.path.join(OUT, "reveal.wav"), reverb(y, 0.5, 0.10, 0.30), -5.0)


def step_carpet():
    t = tarr(0.16)
    y = svf(noise(len(t)) * np.exp(-t * 26.0), 380.0, 0.9, "lp")
    y += 0.25 * np.sin(2 * np.pi * 92.0 * t) * np.exp(-t * 30.0)
    write(os.path.join(OUT, "step_soft.wav"), y, -20.0)


def step_tile():
    t = tarr(0.22)
    y = svf(noise(len(t)) * np.exp(-t * 44.0), 1500.0, 1.6, "bp")
    y += 0.5 * svf(noise(len(t)) * np.exp(-t * 90.0), 4200.0, 1.2, "bp")
    y += 0.20 * np.sin(2 * np.pi * 120.0 * t) * np.exp(-t * 40.0)
    write(os.path.join(OUT, "step_hard.wav"), reverb(y, 0.30, 0.06, 0.35), -18.0)


def clear():
    """終わり。長く、暖かく、しかし大袈裟にしない。"""
    t = tarr(3.2)
    y = np.zeros_like(t)
    for f, a in ((98.0, 0.9), (147.0, 0.6), (196.0, 0.45), (294.0, 0.25), (392.0, 0.14)):
        y += a * np.sin(2 * np.pi * f * t) * (1 - np.exp(-t * 6.0)) * np.exp(-t * 0.55)
    y += 0.12 * svf(noise(len(t)), 3000.0, 1.0, "bp") * np.exp(-t * 1.4)
    write(os.path.join(OUT, "clear.wav"), reverb(y, 0.7, 0.16, 0.30), -5.0)


if __name__ == "__main__":
    drone(); buzz(); lock(); tick(); reveal(); step_carpet(); step_tile(); clear()
    print("LIMINAL SFX DONE")
