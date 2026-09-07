# -*- coding: utf-8 -*-
"""継ぎ目 1〜25 の自己採点。「どれが単調か」を数字で出す。

    python source/score_liminal.py

見るのは 4 つ:
  規則      … A 相似 / B 触れる / C 巡る / D 直視しない / E 暗の一瞬 / F かくれる
  結果      … 出来上がる物の見た目の種類(扉・橋・階段・…)
  手触り    … プレイヤーが実際にやること
  反復度    … 「同じ規則 × 同じ結果」が自分より前に何本あるか

★反復度が 2 以上 = 「またこれか」と思われる継ぎ目。ここから直す。
★確定域は机上検査 [3] と同じ measure。狭すぎ(<0.15)は理不尽、広すぎ(>4.0)は歯応えが無い。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_liminal as G
import sim_liminal as S

# 出来上がる物の見た目(手で分類する。名前からは読めない)
RESULT = {
    1: "戸口", 2: "橋", 3: "階段", 4: "扉",
    5: "シャッター", 6: "扉", 7: "橋", 8: "橋", 9: "階段", 10: "戸口",
    11: "細い梁", 12: "ダクト", 13: "鉄骨梁", 14: "壁(負)", 15: "廊下", 16: "ロッカー",
    17: "階段", 18: "橋", 19: "橋", 20: "橋", 21: "橋",
    22: "床", 23: "段", 24: "片持ち段", 25: "壁が割れる",
}
FEEL = {
    1: "印に立って見る", 2: "印に立って見る", 3: "印に立って見る", 4: "印に立って見る",
    5: "極小を極大に重ねる", 6: "振り返る", 7: "二択を選ぶ", 8: "二択を選ぶ",
    9: "揺れが止まるのを待つ", 10: "印に立って見る", 11: "本物を見分ける",
    12: "何段目かを選ぶ", 13: "巨大を手元に重ねる", 14: "見ないで歩く",
    15: "模型を本物に重ねる", 16: "3 台を噛み合わせる", 17: "4 か所を巡る",
    18: "目を逸らしたまま合わせる", 19: "2 点を一直線に並べる", 20: "2 方向を同時に満たす",
    21: "暗くなる 1 秒を待つ", 22: "偽物を柱の陰に隠す", 23: "床の影に重ねる",
    24: "3 つの印から本物を選ぶ", 25: "4 方向同時 + 暗の一瞬",
}


def rule_of(c):
    if c.touch:
        return "B 触れる"
    if c.per_shard:
        return "C 巡る"
    if c.occl:
        return "F かくれる"
    if c.peri:
        return "D 直視しない"
    if c.dark:
        return "E 暗の一瞬"
    return "A 相似"


def main():
    G.build()
    ents, conns = G.ES, G.CONNS
    world = S.World(ents)
    # 確定域は [3] と同じやり方で測る(順路の床が要るので BFS を一度回す)
    tg = {}
    for c in conns:
        tg["F%d" % c.cid] = (c.focus[0], c.focus[2], c.focus[1] - S.EYE)
    for c in conns:
        for sd in c.solids:
            world.enable(sd["n"], sd["p"])
        for m in c.movers:
            world.disable(m["n"])
    _r, _seen, flat = S.walk(world, (0.0, -6.0, 0.0), tg, (-10.0, -12.0, 90.0, 312.0))

    rows = []
    for c in sorted(conns, key=lambda x: x.cid):
        good, _warm, _best, _bp = S.field(c, flat, flat, only=0 if c.per_shard else None)
        area = len(good) * S.CELL * S.CELL
        rows.append(dict(id=c.cid, rule=rule_of(c), res=RESULT.get(c.cid, "?"),
                         feel=FEEL.get(c.cid, "?"), area=area,
                         needs=list(c.needs), anti=c.anti,
                         minmax=(c.min_y is not None)))

    print("=" * 96)
    print("継ぎ目の自己採点  ★反復度 = 自分より前に「同じ規則 x 同じ結果」が何本あったか")
    print("=" * 96)
    print(" #  規則        結果        確定域   反復  手触り")
    print("-" * 96)
    seen_pairs = {}
    dull, unfair, loose = [], [], []
    for r in rows:
        key = (r["rule"], r["res"])
        rep = seen_pairs.get(key, 0)
        seen_pairs[key] = rep + 1
        mark = "  "
        if rep >= 2:
            mark = "<<"
            dull.append(r)
        if r["area"] < 0.15:
            unfair.append(r)
        if r["area"] > 4.0:
            loose.append(r)
        extra = ""
        if r["needs"]:
            extra += " 連鎖%s" % r["needs"]
        if r["anti"]:
            extra += " 負"
        if r["minmax"]:
            extra += " 高さ窓"
        print("%2d  %-10s  %-10s  %5.2fm2  %d %s %s%s"
              % (r["id"], r["rule"], r["res"], r["area"], rep, mark, r["feel"], extra))

    print("-" * 96)
    n_rule = {}
    n_res = {}
    for r in rows:
        n_rule[r["rule"]] = n_rule.get(r["rule"], 0) + 1
        n_res[r["res"]] = n_res.get(r["res"], 0) + 1
    print("規則の内訳: " + " / ".join("%s %d" % (k, v) for k, v in sorted(n_rule.items())))
    print("結果の内訳: " + " / ".join("%s %d" % (k, v) for k, v in
                                      sorted(n_res.items(), key=lambda t: -t[1])))
    print("")
    print("★直す優先度 (反復度 2 以上 = 「またこれか」): "
          + (", ".join("継ぎ目%d(%s/%s)" % (r["id"], r["rule"][0], r["res"]) for r in dull)
             or "なし"))
    print("★理不尽より (確定域 < 0.15m2): "
          + (", ".join("継ぎ目%d(%.2f)" % (r["id"], r["area"]) for r in unfair) or "なし"))
    print("★歯応えが無い (確定域 > 4.0m2): "
          + (", ".join("継ぎ目%d(%.2f)" % (r["id"], r["area"]) for r in loose) or "なし"))
    chained = [r["id"] for r in rows if r["needs"]]
    print("★連鎖している継ぎ目: %s  (%d/%d 本。ここが少ないほど『一問一答』になる)"
          % (chained or "なし", len(chained), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
