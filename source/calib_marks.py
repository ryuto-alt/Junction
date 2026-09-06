# -*- coding: utf-8 -*-
"""床の目印(擦れ跡)・lock・破片のずらし量を、確定域を実測して決め直す。

    python source/calib_marks.py            結果を表示するだけ
    python source/calib_marks.py --write    gen_liminal.py の LOCKS/SOFT/MARKS を書き換える

なぜ要るか
----------
確定域は「点」ではなく【焦点と対象を結ぶ方向へ伸びた細長い管】(横に敏感・奥行きに鈍感)。
そこへ四角い印を被せると、印の上に立っているのに繋がらない。実際に

    継ぎ目2 (第一幕の斜めの橋)  1.6m 四方の印のうち 当たっていたのは 11%
    継ぎ目20(二つ同時)          1.5m 四方の印のうち  6%
    継ぎ目17(最後の階段)        島の印 1.5m 四方のうち 10〜19%

という状態だった。lock を触るたびに手で測り直すのは無理なので機械にやらせる。

決め方
------
「印の上ならどこに立っても繋がる」を絶対の条件にして、2 つの軸で探す:

  soft … 破片のずらし量。k' = 1 - (1-k)*soft。1 へ寄せるほど勾配がなだらかになり、
         【lock を緩めずに】確定域が広がる。浮き方は控えめになる。
  lock … 許容角。緩めると確定域は広がるが、確定時の見た目のズレも増える。

soft を先に使い、それでも足りない時だけ lock を緩める(見た目のズレを最後まで小さく保つ)。
★soft は shard() の破片にだけ効く。shard_display(多義 7/8)と shard_free(触れる 19)は
  k から実体を逆算するので、触ると実体の位置ごと動いてしまう ＝ 除外。
"""
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sim_liminal as S
import gen_liminal as G

BOUNDS = (-10.0, -12.0, 90.0, 256.0)
MIN_MARK = 0.55 * 0.85           # 人が「その上に立った」と思える最小の擦れ跡(m2)
# ★弱めすぎない。0.7 より下げると『破片が浮いて見える』というこの作品の絵が死ぬ
#   (継ぎ目5 の k=0.16 は soft 0.4 で 0.66 になり、極小に見えなくなる)。
SOFTS = (1.0, 0.85, 0.72)
LOCKS_TRY = (0.9, 1.1, 1.3, 1.6, 2.0, 2.4, 2.9, 3.4, 4.0, 4.6, 5.2)
MIN_W, MIN_L, MAX_W, MAX_L = 0.26, 0.38, 1.50, 3.20
PAD = 0.06                       # 見つけた長方形をこのぶん縮めて安全側に寄せる
# 実体を k から逆算している継ぎ目(7/8/19)と、ずらし量そのものが仕掛けの継ぎ目(5)は触らない
NO_SOFT = {7, 8, 19}
ISL = {0: "A", 1: "D", 2: "C", 3: "B"}


def focus_of(c, only):
    return (c.shards[only].get("focus") or c.focus) if only is not None else list(c.focus)


def eye_at(c, flat, F, x, z):
    k = (round(x / S.CELL), round(z / S.CELL))
    if k not in flat:
        return None
    if abs(flat[k] + S.EYE - F[1]) > 0.4:
        return None
    eye = (x, flat[k] + S.EYE, z)
    if c.touch:
        m = [(c.touch["a"][q] + c.touch["b"][q]) / 2 for q in range(3)]
        dm = math.dist(eye, tuple(m))
        if dm < c.touch.get("near", 1.5) or dm > c.touch.get("far", 13.0):
            return None
    elif math.dist(eye, tuple(F)) > S.FOCUS_LOCK:
        return None
    return eye


def region(c, flat, only, lock, half=4.0):
    """確定域を「マスの集合」で返す。以後の探索は集合の照合だけで済む(速い)。"""
    F = focus_of(c, only)
    good, pts = set(), []
    n = int(half / S.CELL)
    for iz in range(-n, n + 1):
        for ix in range(-n, n + 1):
            x, z = F[0] + ix * S.CELL, F[2] + iz * S.CELL
            eye = eye_at(c, flat, F, x, z)
            if eye and S.conn_error(c, eye, only) < lock:
                good.add((round(x / S.CELL), round(z / S.CELL)))
                pts.append((x, z))
    return good, pts, F


def axis_of(pts):
    if len(pts) < 3:
        return 0.0
    mx = sum(p[0] for p in pts) / len(pts)
    mz = sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts) / len(pts)
    szz = sum((p[1] - mz) ** 2 for p in pts) / len(pts)
    sxz = sum((p[0] - mx) * (p[1] - mz) for p in pts) / len(pts)
    ang = 0.5 * math.atan2(2 * sxz, sxx - szz)
    return math.degrees(math.atan2(math.cos(ang), math.sin(ang))) % 180.0


def inside(good, F, yaw, w, L, step=0.075):
    s_, c_ = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    nu = max(2, int(w / step) + 1)
    nv = max(2, int(L / step) + 1)
    for i in range(nu + 1):
        for j in range(nv + 1):
            u = -w / 2 + w * i / nu
            v = -L / 2 + L * j / nv
            x = F[0] + u * c_ + v * s_
            z = F[2] - u * s_ + v * c_
            if (round(x / S.CELL), round(z / S.CELL)) not in good:
                return False
    return True


def verify(c, flat, only, F, lock, yaw, w, L):
    """最後に本物の誤差で確かめる(マス目の粗さで嘘をつかないように)。"""
    s_, c_ = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    for i in range(13):
        for j in range(13):
            u = -w / 2 + w * i / 12.0
            v = -L / 2 + L * j / 12.0
            x = F[0] + u * c_ + v * s_
            z = F[2] - u * s_ + v * c_
            eye = eye_at(c, flat, F, x, z)
            if eye is None or S.conn_error(c, eye, only) >= lock:
                return False
    return True


def fit(c, flat, only, lock):
    good, pts, F = region(c, flat, only, lock)
    if not good:
        return None, 0.0
    area = len(good) * S.CELL * S.CELL
    yaw0 = axis_of(pts)
    best = None
    for yaw in (yaw0 - 8, yaw0 - 4, yaw0, yaw0 + 4, yaw0 + 8):
        L = MAX_L
        while L >= MIN_L - 1e-6:
            w = min(MAX_W, L)
            while w >= MIN_W - 1e-6:
                if inside(good, F, yaw, w, L):
                    ww, LL = max(w - PAD, MIN_W), max(L - PAD, MIN_L)
                    if verify(c, flat, only, F, lock, yaw, ww, LL):
                        if best is None or ww * LL > best[0]:
                            best = (ww * LL, ww, LL, yaw % 180.0)
                    break
                w -= 0.05
            L -= 0.10
    return best, area


def shard_boxes(c):
    """いまの k での【浮遊姿勢】を、部品ひとつずつの AABB で返す。
    ★破片ごとの外接箱でまとめて見てはいけない。階段のように互い違いに置いた破片は
      外接箱だけなら必ず重なるので、弱めていないのに「重なっている」と誤判定する
      (机上検査 [1] は部品ごとに見ているので、そちらに合わせる)。"""
    out = []
    for si, sh in enumerate(c.shards):
        if sh.get("disp") is not None:
            continue
        F = sh.get("focus") or c.focus
        k = sh["k"]
        for r in sh["ents"]:
            lo = [F[q] + k * (r["p"][q] - F[q]) - abs(r["s"][q]) * k / 2.0 for q in range(3)]
            hi = [F[q] + k * (r["p"][q] - F[q]) + abs(r["s"][q]) * k / 2.0 for q in range(3)]
            out.append((si, r["n"], lo, hi))
    return out


def clashes(c):
    """★soft を効かせすぎると破片どうしが重なって、どれがどれだか読めなくなる。
    机上検査 [1] が落ちるので、較正の段階で弾く。"""
    bs = shard_boxes(c)
    for i in range(len(bs)):
        si, ni, la, ha = bs[i]
        for j in range(i + 1, len(bs)):
            sj, nj, lb, hb = bs[j]
            if si == sj or ni == nj:
                continue                       # 同じ破片の中は重なってよい
            if all(la[q] < hb[q] - 0.02 and lb[q] < ha[q] - 0.02 for q in range(3)):
                return True
    return False


def apply_soft(c, soft, base_k):
    for sh, k0 in zip(c.shards, base_k):
        if sh.get("disp") is None:
            sh["k"] = 1.0 - (1.0 - k0) * soft


def main():
    write = "--write" in sys.argv
    G.build()
    world = S.World(G.ES)
    order = sorted(G.CONNS, key=lambda c: c.solve_order)
    names = {e["name"] for e in G.ES}
    locks, softs, marks, warn = {}, {}, {}, []
    print("=" * 82)
    print("床の目印の較正 ── 「印の上ならどこに立っても繋がる」を条件に決める")
    print("=" * 82)
    print("%-10s %-18s %-9s %-9s %-8s %s" % ("印", "継ぎ目", "soft", "lock", "確定域", "印(幅x長さ @yaw)"))
    for c in order:
        _, seen, flat = S.walk(world, (0.0, -6.0, 0.0), {}, BOUNDS)
        # ★★必ず【元の k】へ戻してから測ること。gen_liminal は既に SOFT を通した形を
        #   作っているので、そのまま測ると「もう弱める必要なし」と誤判定して表が壊れる
        #   (2026-09-07 に実際に壊した。破片が重なる弱め方が残ったまま素通りした)。
        g0 = G.SOFT.get(c.cid, 1.0)
        base_k = [1.0 - (1.0 - sh["k"]) / g0 for sh in c.shards]
        base_lock = c.lock
        slots = list(range(len(c.shards))) if c.per_shard else [None]
        for only in slots:
            nm = ("G1_ib" + ISL[only]) if only is not None else ("C%d_mark" % c.cid)
            if nm not in names:
                continue
            found = None
            softlist = (1.0,) if c.cid in NO_SOFT else SOFTS
            # ★soft を外側に回すこと。破片が浮いて見えることがこの作品の絵なので、
            #   まず「ずらし量そのまま」で lock を振り、どうしても印が置けない時だけ
            #   少しだけ弱める。確定した瞬間の見た目のズレはマスク付きの寄せが隠す。
            for soft in softlist:
                apply_soft(c, soft, base_k)
                if clashes(c):
                    continue                   # 破片が重なる弱め方は採らない
                for lock in LOCKS_TRY:
                    got, area = fit(c, flat, only, lock)
                    if got and got[0] >= MIN_MARK:
                        found = (soft, lock, area, got)
                        break
                if found:
                    break
            if not found:
                # ★人が乗れる大きさに届かない継ぎ目もある(確定域が細い弧になる形)。
                #   その時は lock を最大まで振るのではなく、【一番厳しい lock のまま
                #   小さくても正直な印】を選ぶ。嘘の大きい印より小さい本当の印。
                best = None
                for lock in LOCKS_TRY:
                    for soft in softlist:
                        apply_soft(c, soft, base_k)
                        if clashes(c):
                            continue
                        got, area = fit(c, flat, only, lock)
                        if got and got[0] >= 0.14:
                            if best is None or got[0] > best[3][0]:
                                best = (soft, lock, area, got)
                    if best:
                        break
                if not best:
                    warn.append("%s: 印が置けない(継ぎ目%d)" % (nm, c.cid))
                    apply_soft(c, 1.0, base_k)
                    continue
                found = best
                warn.append("%s: 継ぎ目%d は %.2f x %.2f までしか広がらない(小さいが正直な印)"
                            % (nm, c.cid, best[3][1], best[3][2]))
            soft, lock, area, (_, w, L, yaw) = found
            softs[c.cid] = min(softs.get(c.cid, 1.0), soft)
            locks[c.cid] = max(locks.get(c.cid, 0.0), lock)
            marks[nm] = (round(w, 2), round(L, 2), round(yaw, 1))
            print("%-10s 継ぎ目%-2d %-11s %.2f      %.1f→%-4.1f %5.2fm2  %.2f x %.2f @%5.1f°"
                  % (nm, c.cid, c.note[:11], soft, base_lock, lock, area, w, L, yaw))
            apply_soft(c, 1.0, base_k)
        c.lock = base_lock
        if c.cid == 8 or c.anti:
            continue
        for sd in c.solids:
            world.enable(sd["n"], sd["p"])
        for m in c.movers:
            world.disable(m["n"])

    print()
    for wmsg in warn:
        print("  [!!] " + wmsg)

    lb = "LOCKS = {\n" + "".join("    %d: %.1f,\n" % (k, v) for k, v in sorted(locks.items())) + "}"
    sb = "SOFT = {\n" + "".join("    %d: %.2f,\n" % (k, v)
                                for k, v in sorted(softs.items()) if v < 0.999) + "}"
    mb = "MARKS = {\n" + "".join('    "%s": (%.2f, %.2f, %.1f),\n' % (n, *marks[n])
                                 for n in sorted(marks, key=lambda x: (len(x), x))) + "}"
    print("\n" + lb + "\n\n" + sb + "\n\n" + mb)
    if write:
        p = Path(__file__).resolve().parent / "gen_liminal.py"
        src = p.read_text(encoding="utf-8")
        out = re.sub(r"LOCKS = \{.*?\n\}", lb, src, count=1, flags=re.S)
        out = re.sub(r"SOFT = \{.*?\n\}", sb, out, count=1, flags=re.S)
        out = re.sub(r"MARKS = \{.*?\n\}", mb, out, count=1, flags=re.S)
        assert out != src, "LOCKS / SOFT / MARKS の表が見つからない"
        p.write_text(out, encoding="utf-8")
        print("\n-> gen_liminal.py を書き換えた (LOCKS %d / SOFT %d / MARKS %d)"
              % (len(locks), len([v for v in softs.values() if v < 0.999]), len(marks)))


if __name__ == "__main__":
    main()
