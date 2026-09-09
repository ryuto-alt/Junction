# -*- coding: utf-8 -*-
"""終盤(第四幕・第五幕)の壁へ書く【落書き】の絵を Blender で描いて焼く。

    書き出し先: assets/ui/graffiti/gf_*.png  (背景透過 RGBA・線は真っ白)
    実行:       source/run_graffiti.py  ―― BlenderMCP なら execute_blender_code で
                そのファイルを exec する(read_factory_settings は絶対に撃たない)

--------------------------------------------------------------------------
★何のためにあるか
  第一幕(3 枚)と第三幕(5 枚)には額縁つきの【案内板】がある。終盤の 9 継ぎ目には
  何も無い。しかも第四幕以降は規則が毎回違うので、初見では手掛かりが無い。
  そこで「先に来た誰かが壁に書き残した」体で、解き方の絵だけを壁へ直に書く。
  ★文字・数字・記号文字は 1 つも使わない。語彙は既存の案内板と同じ:
      棒人間 / 目 / 破線の視線 / 足跡 / 実線=本物・破線=まだ無い / × / 矢印

★なぜ案内板(guide_sign)を使わないのか
  額縁つきの掲示物は【施設が用意した物】に見える。終盤の情報は施設の案内ではなく
  「誰かの書き置き」なので、額縁も下地も無い透過の落書きにして、傾け・かすれさせる。

★描かないもの
  答えの座標(何 m の所)・どちらが正解か(24 の 3 つの印は 3 つとも同じに描く)・
  つながった時の演出。描くのは「どこに立ち・どこを見て・何が何に重なるか」だけ。

--------------------------------------------------------------------------
★作りの決まり(踏んだ罠つき)

  1. Grease Pencil は使わない。Blender 5.2 の GPv3 は API が 4.x と別物で、
     bpy から線を積む書き方が通用しない。ここでは【平たいメッシュ】だけで描く:
     線分 = 四角形、線の継ぎ目と端 = 8 角形の円盤。全部 z≒0 の板なので、
     重なっても真っ白どうしで差が出ない ＝ 重ね塗りが破綻しない。
     (曲線 + bevel_depth も試したが端が丸くならず、結局円盤を足すので同じこと)
  2. 面どうしがぴったり同一平面だと z ファイティングでちらつく。図形を 1 つ積むたびに
     z を 3e-5 ずつ足してある。
  3. 手描きの揺らぎは【低い周波数の正弦 3 本】だけ。点ごとに乱数を振ると線が毛羽立ち、
     エンジンの FXAA でちらつく。滑らかな蛇行 + 線ごとの版ずれで済ませる。
  4. 材質は Emission の真っ白 1 種類。色は PNG に持たせず、エンジン側の
     shaderParams(乗算)で「汚れた白 / チョーク色」を作る。
     ★view_transform は必ず 'Standard'。AgX/Filmic のままだと白が 0.9 くらいに
       焼き下げられ、色を掛けた時に思ったより暗くなる。
     ★world を作らずに焼こうとすると EEVEE が落ちる。既定ノードは名前で引かない
       (Blender 5.2 では "Background" というノード名では入っていない)。
  5. ★【180 度回して焼く】。落書きは箱プリミティブの -Z 面へ貼るので、このエンジンでは
     u が -x 向き・v が上下逆 = 見た目 180 度回る。source/ui_icons/build_signs.js の
     ROT180 とまったく同じ理由。ここではカメラを視線まわりに 180 度回して焼く
     (絵の座標は人が読む向きのままでよい)。逆さまに見えたら ROT180 を False にする。
     ★エンジン側(gen_liminal.py)で辻褄を合わせないこと。両方やると元へ戻る。
  6. 焼く大きさは 448px 高。板は実寸 1.0〜1.3m 高なので 350〜450 texel/m。
     案内板(384px / 0.66m = 580 texel/m)より粗いが、落書きは細線が無いので足りる。
     ★BC7 圧縮の時間は画素数に比例する(build_signs.js の冒頭に実測がある)。
       9 枚あるので上げすぎると配布ビルドが目に見えて遅くなる。
  7. 傾きは【絵の側へ焼き込む】。実体の rotation でロールさせると、壁に貼った板の隅が
     壁へ潜って絵が切れる。焼き込みなら板は壁と平行のままでよい。
     ★絵は画布の四辺 60 単位より内側に収めること。焼き込みの傾き 2 度で、
       隅は最大 34 単位動く。

--------------------------------------------------------------------------
★絵の中身(1 枚 = 1 継ぎ目)

  第四幕(大展示室)
    gf_a4_peri   18 直視しない  視野の【真ん中】に据えると × / 視野の【端】で決まる
    gf_a4_touch  19 触れる      柱の頭と板の先端が【画面の上で】重なるまで歩く
    gf_a4_both   20 二つ同時    1 つの立ち位置で、左右 2 方向を同時に満たす
    gf_a4_dark   21 暗の一瞬    明かりが点いている間は × / 消えている間だけ決まる
    gf_a4_visit  17 巡る        4 つの印を歩いて回り、印ごとに階段が 1 群ずつ増える

  第五幕(環の間) ★4 枚は【連鎖】。左上(または右下)の輪が 1→2→3→4 と増えていく。
    gf_a5_hide   22 かくれて合わせる  細い配管の陰へ偽物を入れる → 井戸に蓋
    gf_a5_shadow 23 床の影にはめる    床の影に浮遊物を落とす      → 棚への段
    gf_a5_marks  24 三つの印          印は 3 つ・地上からは ×     → 壁から段
    gf_a5_four   25 四つ同時          4 方向を同時 + 明かりが消えた一瞬 → 壁が開く
"""
import math
import os
import random

import bpy  # noqa: F401  (Blender の中でだけ動く)

# ---------------------------------------------------------------- 画布
W, H = 1400.0, 1000.0      # 設計座標(y は下向き。SVG と同じ向きで書けるように)
SC = 1000.0                # 1000 単位 = 1m。板は 1.4 x 1.0m 相当
ROT180 = True              # 箱の -Z 面へ貼るための 180 度焼き込み(上の 5 番)
OUT_H = 448                # 焼く高さ(px)

DASH = (26.0, 18.0)        # 破線(まだ無い物 / 視線)
DASH_S = (17.0, 12.0)      # 細い破線


# ---------------------------------------------------------------- 線を積む
class Ink:
    """平たい三角形を積むだけの画布。線 = 四角形 + 端の円盤。

    ★grow: 線も塗りも【この幅だけ太らせる】。同じ種(seed)で 2 回描けば、
      1 回目(grow>0)が輪郭、2 回目(grow=0)が芯になる ＝ 縁取りが作れる。
      揺らぎは種から決まるので、2 枚は 1 ピクセルもずれない。
    ★zbase: 芯を輪郭より手前へ置くため。
    """

    def __init__(self, seed=0, grow=0.0, zbase=0.0):
        self.v, self.f = [], []
        self.zz = zbase
        self.grow = float(grow)
        self.rnd = random.Random(seed)

    # -- 生の面 -------------------------------------------------------
    def _fan(self, pts):
        self.zz += 3e-5                       # 同一平面を避ける(罠 2)
        b = len(self.v)
        self.v.extend((float(p[0]), float(p[1]), self.zz) for p in pts)
        self.f.extend((b, b + i, b + i + 1) for i in range(1, len(pts) - 1))

    def _grown(self, pts):
        """凸多角形を重心から外へ押し広げる(塗り図形を太らせる近似)。"""
        g = self.grow * 0.5
        if g <= 0.0:
            return pts
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        out = []
        for x, y in pts:
            dx, dy = x - cx, y - cy
            L = math.hypot(dx, dy) or 1.0
            out.append((x + dx / L * g, y + dy / L * g))
        return out

    def poly(self, pts):
        self._fan(self._grown(pts))

    def disc(self, c, r, n=10):
        r = r + self.grow * 0.5
        self._fan([(c[0] + r * math.cos(2 * math.pi * i / n),
                    c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)])

    def tri(self, a, b, c):
        self.poly([a, b, c])

    def seg(self, p, q, w):
        w = w + self.grow
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        if L < 1e-9:
            return
        nx, ny = -dy / L * w * 0.5, dx / L * w * 0.5
        self._fan([(p[0] + nx, p[1] + ny), (q[0] + nx, q[1] + ny),
                   (q[0] - nx, q[1] - ny), (p[0] - nx, p[1] - ny)])

    # -- 手描きの揺らぎ ------------------------------------------------
    def _hand(self, pts, amp, close):
        pts = list(pts)
        if close and (pts[0] != pts[-1]):
            pts.append(pts[0])
        ph = [self.rnd.uniform(0, 6.2832) for _ in range(3)]
        fr = [2 * math.pi / 173.0, 2 * math.pi / 79.0, 2 * math.pi / 37.0]
        # 全体の「版ずれ」。1 本ごとにわずかに位置が狂う
        ox = self.rnd.uniform(-1.6, 1.6) * (amp / 3.0)
        oy = self.rnd.uniform(-1.6, 1.6) * (amp / 3.0)
        out, s = [], 0.0
        for i in range(len(pts) - 1):
            p, q = pts[i], pts[i + 1]
            dx, dy = q[0] - p[0], q[1] - p[1]
            L = math.hypot(dx, dy)
            if L < 1e-9:
                continue
            nx, ny = -dy / L, dx / L
            n = max(1, int(L / 24.0))
            for j in range(n):
                t = j / float(n)
                u = s + t * L
                off = amp * (0.55 * math.sin(u * fr[0] + ph[0])
                             + 0.30 * math.sin(u * fr[1] + ph[1])
                             + 0.15 * math.sin(u * fr[2] + ph[2]))
                out.append((p[0] + dx * t + nx * off + ox, p[1] + dy * t + ny * off + oy))
            s += L
        q = pts[-1]
        out.append((q[0] + ox, q[1] + oy))
        return out

    @staticmethod
    def _dashify(pts, dash):
        d, g = dash
        runs, cur = [], [pts[0]]
        pen, need, on = 0.0, d, True
        for i in range(len(pts) - 1):
            p, q = pts[i], pts[i + 1]
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            t0 = 0.0
            while L - t0 > 1e-9:
                step = min(need - pen, L - t0)
                t1 = t0 + step
                pt = (p[0] + (q[0] - p[0]) * t1 / L, p[1] + (q[1] - p[1]) * t1 / L)
                if on:
                    cur.append(pt)
                pen += step
                t0 = t1
                if pen >= need - 1e-9:
                    if on:
                        runs.append(cur)
                    on = not on
                    cur = [pt]
                    pen, need = 0.0, (d if on else g)
        if on and len(cur) > 1:
            runs.append(cur)
        return [r for r in runs if len(r) > 1]

    # -- 描く ---------------------------------------------------------
    def path(self, pts, w, jit=3.0, close=False, dash=None, caps=True):
        pp = self._hand(pts, jit, close)
        runs = self._dashify(pp, dash) if dash else [pp]
        for run in runs:
            for i in range(len(run) - 1):
                self.seg(run[i], run[i + 1], w)
            if caps:
                for p in run:
                    self.disc(p, w * 0.5, 8)

    def rect(self, x0, y0, x1, y1, w, jit=3.0, dash=None):
        self.path([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], w, jit, close=True, dash=dash)

    def arc(self, c, r, a0, a1, w, jit=2.0, dash=None, n=48, ry=None):
        ry = r if ry is None else ry
        pts = []
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / float(n))
            pts.append((c[0] + r * math.cos(a), c[1] + ry * math.sin(a)))
        self.path(pts, w, jit, dash=dash)

    def blob(self, c, rx, ry, ang=0.0, n=16):
        """塗りつぶした楕円(足跡・瞳など)。"""
        rx, ry = rx + self.grow * 0.5, ry + self.grow * 0.5
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        pts = []
        for i in range(n):
            t = 2 * math.pi * i / n
            x, y = rx * math.cos(t), ry * math.sin(t)
            pts.append((c[0] + x * ca - y * sa, c[1] + x * sa + y * ca))
        self._fan(pts)

    def hatch_quad(self, a, b, c, d, n, w, jit=2.0):
        """四辺形 a-b-c-d を n 本の横線で埋める(= 暗がり)。辺 a→d と b→c を渡す。"""
        for i in range(n + 1):
            t = i / float(n)
            p = (a[0] + (d[0] - a[0]) * t, a[1] + (d[1] - a[1]) * t)
            q = (b[0] + (c[0] - b[0]) * t, b[1] + (c[1] - b[1]) * t)
            self.path([p, q], w, jit)


# ---------------------------------------------------------------- 語彙(部品)
def qbez(p0, p1, p2, n=18):
    out = []
    for i in range(n + 1):
        t = i / float(n)
        u = 1.0 - t
        out.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return out


def person(ink, cx, feet, h, w=1.0, dash=None, jit=3.0, stride=1.0, arms=1.0):
    """棒人間。既存の案内板(sign_walk_look 等)と【まったく同じ 6 本の図形】。

    h = 頭のてっぺんから足元までの高さ。SVG 版の 384 単位を基準に相対で組む。
    戻り値 = 頭の中心(視線・扇の起点に使う)。
    """
    u = h / 384.0
    lw = (46 * u * w, 26 * u * w, 32 * u * w)
    ink.path([(cx, feet - 288 * u), (cx, feet - 144 * u)], lw[0], jit, dash=dash)
    ink.path([(cx, feet - 248 * u), (cx - 70 * u * arms, feet - 154 * u)], lw[1], jit, dash=dash)
    ink.path([(cx, feet - 248 * u), (cx + 70 * u * arms, feet - 154 * u)], lw[1], jit, dash=dash)
    ink.path([(cx, feet - 144 * u), (cx - 38 * u * stride, feet)], lw[2], jit, dash=dash)
    ink.path([(cx, feet - 144 * u), (cx + 38 * u * stride, feet)], lw[2], jit, dash=dash)
    hc = (cx, feet - 336 * u)
    if dash:
        ink.arc(hc, 48 * u, 0, 360, 18 * u, jit, dash=DASH_S, n=40)
    else:
        ink.disc(hc, 48 * u, 22)
    return hc


def eye(ink, cx, cy, rx, w, jit=2.0):
    """目。sign_walk_look と同じアーモンド + 瞳。"""
    ry = rx * 0.62
    ink.path(qbez((cx - rx, cy), (cx, cy - ry * 1.9), (cx + rx, cy)), w, jit)
    ink.path(qbez((cx - rx, cy), (cx, cy + ry * 1.9), (cx + rx, cy)), w, jit)
    ink.disc((cx, cy), rx * 0.27, 18)


def cross(ink, cx, cy, r, w, jit=3.0):
    ink.path([(cx - r, cy - r), (cx + r, cy + r)], w, jit)
    ink.path([(cx + r, cy - r), (cx - r, cy + r)], w, jit)


def arrow(ink, p, q, w=30.0, hw=46.0, hl=62.0, jit=2.5, dash=None):
    """太い矢印(「こうなる」)。既存の案内板と同じ、軸 + 塗った三角。
    w<=1 なら軸を描かず【矢尻だけ】(引き出し線の先などに使う)。"""
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return
    ux, uy = dx / L, dy / L
    b = (q[0] - ux * hl, q[1] - uy * hl)
    if w > 1.0:
        ink.path([p, b], w, jit, dash=dash, caps=(dash is None))
    ink.tri(q, (b[0] - uy * hw, b[1] + ux * hw), (b[0] + uy * hw, b[1] - ux * hw))


def foot(ink, c, ang, s=1.0):
    """足跡(そこに立つ / 歩く)。"""
    ink.blob(c, 15 * s, 26 * s, ang)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    for dx, dy in ((-9, -34), (2, -37), (12, -33)):
        ink.blob((c[0] + dx * s * ca - dy * s * sa, c[1] + dx * s * sa + dy * s * ca),
                 5.5 * s, 5.5 * s)


def floor_mark(ink, cx, cy, wtop, wbot, hh, w=11.0, jit=2.5, dash=None):
    """床の印。手前が広い台形(= 床に描いてある四角を斜めから見た形)。"""
    ink.path([(cx - wbot / 2, cy + hh / 2), (cx + wbot / 2, cy + hh / 2),
              (cx + wtop / 2, cy - hh / 2), (cx - wtop / 2, cy - hh / 2)],
             w, jit, close=True, dash=dash)


def lamp(ink, cx, cy, lit=True, s=1.0, jit=2.5):
    """吊り下がった灯り。sign_shadow_tip と同じ形。lit=False なら光の線を描かない。"""
    ink.path([(cx, cy - 82 * s), (cx, cy - 44 * s)], 10 * s, jit)
    ink.poly([(cx - 40 * s, cy), (cx + 40 * s, cy), (cx + 26 * s, cy - 42 * s),
              (cx - 26 * s, cy - 42 * s)])
    ink.disc((cx, cy + 12 * s), 13 * s, 14)
    if lit:
        for a in (200, 232, 262, 292, 340):
            ra = math.radians(a)
            ink.path([(cx + 52 * s * math.cos(ra), cy + 22 * s - 52 * s * math.sin(ra)),
                      (cx + 96 * s * math.cos(ra), cy + 22 * s - 96 * s * math.sin(ra))],
                     8 * s, jit)


def posts(ink, x, ytop, k, dash=None, jit=2.6):
    """窪みから生えた柱 2 本 + その上に渡った天端。継ぎ目 18 の出来上がり。"""
    hw, dn = 104 * k, 168 * k
    ink.path([(x - hw - 54 * k, ytop), (x + hw + 54 * k, ytop)], 20 * k + 6, jit, dash=dash)
    for dx in (-hw, hw):
        ink.path([(x + dx, ytop), (x + dx, ytop + dn)], 17 * k + 4, jit, dash=dash)
    ink.path([(x - hw - 74 * k, ytop + dn), (x + hw + 74 * k, ytop + dn)], 12, jit, dash=dash)


def slab(ink, x0, x1, y, th, w=10.0, jit=2.5, dash=None):
    """横に寝た板(段 / 蓋 / 棚)。実線 = 本物 / 破線 = まだ無い。"""
    ink.rect(x0, y - th / 2, x1, y + th / 2, w, jit, dash=dash)


def chain(ink, x, y, done, total=4, r=30.0, gap=44.0, w=10.0, jit=1.6):
    """連鎖の輪。左から done 個が実線、残りが破線。第五幕の 4 枚だけに付ける。

    ★数字ではない。前の継ぎ目が次の足場になる【積み上げ】であることを、
      同じ絵が幕内で 1→2→3→4 と育っていくことだけで伝える。
    """
    for i in range(total):
        ink.arc((x + i * gap, y), r, 0, 360, w, jit, n=34,
                dash=None if i < done else DASH_S, ry=r * 0.78)


# ================================================================ 9 枚
def gf_a4_peri(ink):
    """18 直視しない(西の柱)。視野の【真ん中】に据えると決まらない。端で決まる。

    人と扇 → 中心線の先に同じ柱が【破線のまま + ×】/ 扇の上の縁の先に同じ柱が【実線】。
    ★同じ物を二度描いて片方に × を打つのは sign_choose_one / sign_unframe_wall と同じ手。
    """
    ink.path([(80, 905), (1330, 905)], 13, 3.2)
    hc = person(ink, 232, 900, 340, stride=0.7)
    ap = (hc[0] + 22, hc[1] - 8)
    ink.path([ap, (1332, 236)], 8, 3.0, dash=DASH)          # 視野の上の縁
    ink.path([ap, (1332, 812)], 8, 3.0, dash=DASH)          # 視野の下の縁
    ink.path([ap, (1332, 548)], 12, 3.0, dash=DASH)         # 見ている真ん中
    eye(ink, 470, 556, 56, 10)
    posts(ink, 876, 552, 0.60, DASH)                        # 真ん中 = 決まらない
    cross(ink, 876, 600, 104, 19)
    posts(ink, 1092, 302, 0.92, None)                       # 端 = 決まる
    ink.path(qbez((944, 486), (1046, 466), (1062, 392)), 8, 2.4, dash=DASH_S)
    arrow(ink, (1062, 404), (1074, 352), 0.1, 30, 42)


def gf_a4_touch(ink):
    """19 触れる(東の橋)。焦点は無い。柱の頭と板の先端が【画面の上で】重なる。

    左 = 2 つの点が離れていて板は破線 → 矢印 →
    右 = 目から出た 1 本の破線が両方を貫き、点が 1 つに重なって板が実線になる。
    下 = 足跡と両向きの矢印 = 立ち止まる印は無い。重なるまで歩く。
    """
    for ox, joined in ((40, False), (790, True)):
        ink.path([(ox + 20, 878), (ox + 545, 878)], 12, 3.0)
        eye(ink, ox + 92, 784, 54, 10)
        if not joined:
            ink.path([(ox + 100, 762), (ox + 300, 262)], 7, 2.6, dash=DASH_S)
            ink.path([(ox + 104, 776), (ox + 398, 444)], 7, 2.6, dash=DASH_S)
            ink.path([(ox + 300, 262), (ox + 300, 878)], 18, 2.8)        # 柱
            ink.disc((ox + 300, 262), 28, 18)
            slab(ink, ox + 398, ox + 550, 444, 60, 10, 2.6, dash=DASH)   # 板(まだ無い)
            ink.disc((ox + 398, 444), 24, 18)
        else:
            jx, jy = ox + 322, 292
            ink.path([(ox + 100, 770), (ox + 470, 152)], 8, 2.6, dash=DASH)
            ink.path([(jx, jy), (jx, 878)], 18, 2.8)                     # 柱
            slab(ink, jx, ox + 548, jy, 60, 11, 2.6)                     # 板(本物)
            ink.disc((jx, jy), 30, 20)
            ink.arc((jx, jy), 60, 0, 360, 8, 1.8, n=34)
    arrow(ink, (620, 470), (764, 470), 30, 44, 58)
    # 下: 立ち止まる場所は無い。重なるまで左右に歩く
    foot(ink, (654, 928), 6, 0.86)
    foot(ink, (730, 928), -6, 0.86)
    arrow(ink, (620, 972), (536, 972), 0.1, 30, 42)
    arrow(ink, (764, 972), (848, 972), 0.1, 30, 42)
    ink.path([(536, 972), (848, 972)], 9, 2.4)


def gf_a4_both(ink):
    """20 二つ同時(南の踏み石)。1 つの立ち位置で、左右 2 方向を同時に満たす。

    中央の印に立つ人の頭から破線が 2 本、左右へ分かれて 2 つの的へ届く。
    両隣に同じ形の印があるが、そこには × ＝ 決まる所は 1 つだけ。
    """
    ink.path([(70, 906), (1330, 906)], 13, 3.2)
    floor_mark(ink, 700, 924, 152, 216, 62)
    hc = person(ink, 700, 894, 336, stride=0.55)
    ink.path([hc, (268, 300)], 9, 3.0, dash=DASH)
    ink.path([hc, (1156, 316)], 9, 3.0, dash=DASH)
    # 左の的: 同じ形の踏み石が 2 つ
    for px, py in ((252, 330), (340, 256)):
        ink.path([(px - 98, py), (px + 98, py), (px + 64, py - 56), (px - 64, py - 56)],
                 13, 2.6, close=True)
    # 右の的: 立った枠
    ink.rect(1064, 148, 1284, 396, 16, 2.8)
    # 隣の印では決まらない
    for mx in (388, 1012):
        floor_mark(ink, mx, 938, 120, 170, 50, 9, 2.4, dash=DASH_S)
        cross(ink, mx, 936, 56, 13)


def gf_a4_dark(ink):
    """21 暗の一瞬(北の庇)。明かりが点いている間は決まらない。消えた一瞬だけ。

    左 = 光を出している灯り + 庇は破線 + ×
    右 = 光の線の無い灯り + 上が横縞(暗がり) + 庇は実線 + 足跡(動かないで待つ)
    """
    arrow(ink, (618, 486), (770, 486), 30, 44, 58)
    for ox, lit in ((36, True), (796, False)):
        ink.path([(ox + 14, 898), (ox + 550, 898)], 12, 3.0)
        if not lit:
            ink.hatch_quad((ox + 8, 62), (ox + 556, 62), (ox + 556, 274), (ox + 8, 274),
                           6, 7, 2.6)
        lamp(ink, ox + 286, 138, lit, 1.25)
        # 庇(壁から張り出す)。★方杖(筋交い)は入れない ── 線が太いので三角が
        #   塗り潰れて「旗」に見えた。庇は【L 字】だけで十分に庇に見える。
        d = DASH if lit else None
        ink.path([(ox + 66, 330), (ox + 66, 898)], 14, 2.8)              # 壁
        slab(ink, ox + 66, ox + 340, 500, 36, 12, 2.6, dash=d)           # 庇の板
        ink.rect(ox + 306, 500, ox + 340, 592, 12, 2.6, dash=d)          # 先の垂れ
        if lit:
            cross(ink, ox + 208, 520, 108, 19)
        person(ink, ox + 442, 896, 296, stride=0.5 if lit else 0.42)
        floor_mark(ink, ox + 442, 916, 112, 160, 46, 9, 2.4)
        if not lit:
            foot(ink, (ox + 400, 958), 5, 0.9)
            foot(ink, (ox + 486, 958), -5, 0.9)


def gf_a4_visit(ink):
    """17 巡る(出口の階段)。4 つの印を歩いて回り、印ごとに階段が 1 群ずつ増える。

    下 = 4 つの印。破線の道と足跡でつながっている(= 歩いて回る)。
    右 = 出口へ上がる階段。2 段ずつ 4 群に分かれ、印から破線の引き出し線で対応する。
    ★どの印がどの群かは描くが、印の場所そのもの(座標)は描かない。
    """
    ink.path([(60, 876), (660, 876)], 12, 3.0)
    x0, y0, dx, dy = 664, 872, 72, 82
    for i in range(8):
        ink.path([(x0 + dx * i, y0 - dy * i), (x0 + dx * i, y0 - dy * (i + 1))], 12, 2.4)
        ink.path([(x0 + dx * i, y0 - dy * (i + 1)), (x0 + dx * (i + 1), y0 - dy * (i + 1))],
                 14, 2.4)
    # 群の切れ目(2 段ごと)に小さな刻み
    for g in range(4):
        gx, gy = x0 + dx * 2 * g, y0 - dy * 2 * g
        ink.path([(gx - 26, gy), (gx, gy)], 10, 2.2)
    ink.rect(1246, 96, 1330, 232, 15, 2.6)                  # 出口(開口)
    ink.path([(1240, 232), (1336, 232)], 12, 2.4)
    marks = ((136, 866), (296, 866), (456, 866), (612, 866))
    tips = ((x0 + dx * 1.5, y0 - dy * 2 - 26), (x0 + dx * 3.5, y0 - dy * 4 - 26),
            (x0 + dx * 5.5, y0 - dy * 6 - 26), (x0 + dx * 7.5, y0 - dy * 8 - 26))
    for (mx, my), tp in zip(marks, tips):
        floor_mark(ink, mx, my, 104, 148, 46, 10, 2.4)
        ink.path([(mx + 44, my - 30), tp], 6, 2.2, dash=DASH_S)
    # 回る道(破線 + 足跡)
    ink.path([(118, 936), (632, 936)], 8, 3.0, dash=DASH)
    for c in ((216, 930), (376, 930), (534, 930)):
        foot(ink, c, 92, 0.68)
    person(ink, 136, 862, 236, stride=0.6)


def gf_a5_hide(ink):
    """22 かくれて合わせる。細い配管の陰へ偽の板を入れる → 井戸に蓋が閉じる。

    ★2 枚とも【見えている画面そのもの】を描く(左下の目がそれを言う)。
      左 = 偽の板が配管の横に丸見え → ×
      右 = 偽の板が配管に断ち切られて、切れ端しか見えない → 井戸に蓋が架かる
    間の足跡と両向きの矢印 = 変わるのは【横へ一歩】だけ。
    """
    chain(ink, 76, 106, 1)
    for ox, hidden in ((36, False), (792, True)):
        eye(ink, ox + 78, 940, 46, 9)          # 「これが見えている画面」
        ink.path([(ox + 112, 916), (ox + 186, 838)], 7, 2.2, dash=DASH_S)
        if not hidden:
            ink.path([(ox + 30, 848), (ox + 552, 848)], 12, 3.0)
            ink.path([(ox + 216, 140), (ox + 216, 848)], 26, 2.6)          # 細い配管
            slab(ink, ox + 292, ox + 552, 420, 66, 10, 2.6, dash=DASH)     # 偽の板(丸見え)
            cross(ink, ox + 422, 420, 92, 18)
        else:
            ink.path([(ox + 24, 848), (ox + 236, 848)], 12, 3.0)
            ink.path([(ox + 236, 848), (ox + 236, 926)], 10, 2.4)          # 井戸の見切り
            ink.path([(ox + 494, 848), (ox + 494, 926)], 10, 2.4)
            ink.path([(ox + 494, 848), (ox + 556, 848)], 12, 3.0)
            ink.path([(ox + 216, 140), (ox + 216, 848)], 30, 2.6)          # 配管
            # 偽の板は配管に断ち切られ、切れ端だけ(= 中心が隠れている)
            ink.path([(ox + 116, 420), (ox + 194, 420)], 10, 2.4, dash=DASH_S)
            ink.path([(ox + 238, 420), (ox + 362, 420)], 10, 2.4, dash=DASH_S)
            # 井戸に蓋(結果)
            for i in range(3):
                slab(ink, ox + 242 + i * 86, ox + 320 + i * 86, 848, 30, 10, 2.4)
    arrow(ink, (632, 452), (764, 452), 30, 44, 58)
    foot(ink, (656, 594), 6, 0.8)
    foot(ink, (734, 594), -6, 0.8)
    ink.path([(608, 660), (786, 660)], 9, 2.4)
    arrow(ink, (700, 660), (600, 660), 0.1, 28, 40)
    arrow(ink, (700, 660), (794, 660), 0.1, 28, 40)


def gf_a5_shadow(ink):
    """23 床の影にはめる。床に落ちた影に、浮いている段を落とし込む。

    左 = 印に立つ人 + 破線の視線 / 中 = 破線の段が真下の【影】へ落ちる /
    右 = 影は棚の足元にある。落ちた段がそのまま棚への上がり口になる。
    """
    chain(ink, 76, 106, 2)
    ink.path([(60, 862), (1340, 862)], 12, 3.0)
    hc = person(ink, 212, 858, 322, stride=0.55)
    floor_mark(ink, 212, 882, 124, 176, 48, 10, 2.4)
    ink.path([hc, (676, 470)], 8, 2.8, dash=DASH)
    slab(ink, 626, 908, 452, 56, 10, 2.6, dash=DASH)         # 浮いている段(まだ無い)
    slab(ink, 626, 786, 386, 56, 10, 2.6, dash=DASH)
    arrow(ink, (706, 520), (706, 736), 16, 34, 46, dash=DASH_S)
    arrow(ink, (866, 520), (866, 736), 16, 34, 46, dash=DASH_S)
    sh = ((600, 790), (934, 790), (976, 856), (558, 856))     # 床に落ちた影
    ink.path(list(sh), 10, 2.4, close=True)
    ink.hatch_quad(sh[0], sh[1], sh[2], sh[3], 5, 6, 2.0)
    ink.path([(1006, 646), (1340, 646)], 16, 2.6)             # 棚(既に在る)
    ink.path([(1040, 646), (1040, 862)], 11, 2.6)
    ink.path([(1250, 646), (1250, 862)], 11, 2.6)
    ink.path([(934, 790), (1006, 790)], 9, 2.4, dash=DASH_S)
    arrow(ink, (946, 760), (1024, 684), 12, 30, 44)


def gf_a5_marks(ink):
    """24 三つの印。印は 3 つ・どれが本物かは描かない。地上からでは決まらない。

    下  = 地面に立つ人 + × (= ここからでは駄目)
    右  = 前の継ぎ目で出来た 2 段が棚へ掛かっている(= 連鎖)
    上  = 棚の上に印が 3 つ。目から 3 本の破線。印から印へ破線の道と足跡(= 試す)
    左  = 決まった結果。壁ぎわに段が生えて、上の踊り場へ続く。
    """
    chain(ink, 1148, 952, 3)
    ink.path([(60, 906), (1340, 906)], 12, 3.0)
    ink.path([(62, 150), (62, 906)], 14, 2.8)                       # 壁
    # 結果: 壁ぎわに生える段(棚 → 左上の踊り場)
    st = [(520, 622)]
    for i in range(5):
        st.append((520 - 78 * i, 622 - 80 * (i + 1)))
        st.append((520 - 78 * (i + 1), 622 - 80 * (i + 1)))
    ink.path(st, 14, 2.6)
    slab(ink, 66, 190, 222, 30, 11, 2.4)                            # 上の踊り場
    # 棚
    ink.path([(520, 626), (1112, 626)], 17, 2.8)
    ink.path([(566, 626), (566, 906)], 11, 2.6)
    ink.path([(1070, 626), (1070, 906)], 11, 2.6)
    # 前の継ぎ目(23)で出来た 2 段が棚へ掛かっている = 連鎖。★段は棚と繋げて描く
    #   (離して描いたら、宙に浮いた別の板に見えた)
    slab(ink, 1112, 1246, 706, 30, 11, 2.4)
    ink.path([(1112, 626), (1112, 706)], 10, 2.4)
    slab(ink, 1176, 1310, 800, 30, 11, 2.4)
    ink.path([(1176, 706), (1176, 800)], 10, 2.4)
    ink.path([(1240, 800), (1240, 906)], 10, 2.4)
    # 印 3 つ(3 つとも同じに描く) + 目 + 破線
    ey = (818, 344)
    eye(ink, ey[0], ey[1], 56, 10)
    for mx in (648, 818, 988):
        floor_mark(ink, mx, 598, 80, 116, 38, 9, 2.2)
        ink.path([(ey[0], ey[1] + 42), (mx, 582)], 6, 2.2, dash=DASH_S)
    ink.path([(648, 556), (818, 528), (988, 556)], 7, 2.6, dash=DASH_S)
    foot(ink, (734, 528), 74, 0.58)
    foot(ink, (904, 528), 106, 0.58)
    # 地上からでは決まらない
    person(ink, 300, 902, 238, dash=DASH_S, stride=0.6)
    cross(ink, 300, 712, 58, 14)


def gf_a5_four(ink):
    """25 四つ同時(仕上げ)。1 点で 4 方向を同時に満たし、明かりが落ちる一瞬を待つ。

    中 = 見下ろした踊り場。4 辺に 4 本の欄干。中心の印に立つ人から破線が 4 本、
         4 辺へ【同時に】伸びる。
    上 = 光を出した灯りに × / その隣に光の線の無い灯り + 横縞(暗がり)
    右 = 割れて左右へ開く壁。
    """
    chain(ink, 76, 952, 4)
    # ★暗がりの縞は【消えている灯りの側にだけ】敷く。全幅に敷いたら、点いている
    #   灯りと × が縞に埋もれて読めなくなった
    ink.hatch_quad((392, 66), (1338, 66), (1338, 200), (392, 200), 4, 7, 2.6)
    # ★× は灯りに【重ねない】。同じ太さの線どうしなので重ねると星印になって、
    #   何を否定しているのか読めなくなった。真下へ離して打つ。
    lamp(ink, 194, 112, True, 1.15)
    cross(ink, 194, 268, 58, 15)
    lamp(ink, 700, 116, False, 1.2)
    a, b, c, d = (282, 902), (1002, 902), (874, 512), (410, 512)
    ink.path([a, b, c, d], 9, 2.6, close=True, dash=DASH_S)       # 踊り場の輪郭
    rails = []
    for p, q, nx, ny in ((a, b, 0, 30), (b, c, 30, 0), (c, d, 0, -30), (d, a, -30, 0)):
        m = ((p[0] + q[0]) / 2 + nx, (p[1] + q[1]) / 2 + ny)
        ux, uy = (q[0] - p[0]) * 0.28, (q[1] - p[1]) * 0.28
        ink.path([(m[0] - ux, m[1] - uy), (m[0] + ux, m[1] + uy)], 22, 2.4)
        rails.append(m)
    floor_mark(ink, 642, 790, 92, 128, 40, 9, 2.2)
    hc = person(ink, 642, 764, 244, stride=0.45, arms=1.15)
    aim = (rails[0][0] - 210, rails[0][1]), rails[1], rails[2], rails[3]
    for t in aim:
        ink.path([hc, t], 7, 2.4, dash=DASH_S)
    # 割れて開く壁
    ink.path([(1128, 300), (1128, 902)], 14, 2.8)
    ink.path([(1330, 300), (1330, 902)], 14, 2.8)
    ink.path([(1128, 300), (1330, 300)], 12, 2.6)
    ink.path([(1226, 300), (1204, 424), (1246, 528), (1210, 656), (1242, 776), (1220, 902)],
             10, 3.4)
    arrow(ink, (1200, 592), (1140, 592), 0.1, 40, 54)
    arrow(ink, (1250, 592), (1314, 592), 0.1, 40, 54)


def gate_frame(ink, cx, ytop, ybot, hw, w=14, dash=None, jit=2.6):
    """自立した戸口(方立 2 本 + 楣)。継ぎ目 10 で建つ物そのもの。

    ★沓摺(下の横棒)は描かない。床の線と重なって【1 本の太い線】に潰れる。
      戸口は方立が床まで届いていれば戸口に見える。
    """
    ink.path([(cx - hw, ytop), (cx - hw, ybot)], w, jit, dash=dash)
    ink.path([(cx + hw, ytop), (cx + hw, ybot)], w, jit, dash=dash)
    ink.path([(cx - hw - 24, ytop), (cx + hw + 24, ytop)], w + 3, jit, dash=dash)


def gf_a2_gate(ink):
    """10 自立した戸口(第二幕・白い部屋)。★終盤より前なので【易しく・少なく】描く。

    左 = 印から外れて立つ人。破線の視線が 2 本に分かれ、吊り灯と、浮いている戸口の
         楣が【別々の所】にある。戸口は破線 = まだ無い。
    中 = 足跡と矢印 ＝ 印まで歩く。
    右 = 印に立つと視線が 1 本になり、吊り灯と楣が【1 つの点に重なる】。
         戸口が実線で建ち、そこを抜けられる。

    ★ここが規則B(触れる)の初出。第四幕の gf_a4_touch と同じ語彙・同じ組み立てに
      してあるので、あちらは「もう一度これをやる」として読める。
    ★連鎖の輪は付けない(連鎖なのは第五幕だけ)。
    ★天井の線・奥の壁は描かない。1 度描いたら線が多すぎて何の絵か読めなくなった。
      床の線 1 本と、必要な物だけにする。
    """
    # ★★線は終盤の 9 枚より【太い】。この 1 枚だけ 13.7m 先から読ませるので、
    #   細い線は縮小(ミップ)で halo と混ざって灰色に潰れる。実機で確認して 1.5 倍にした。
    for ox, joined in ((50, False), (762, True)):
        ink.path([(ox + 6, 866), (ox + 528, 866)], 20, 3.2)             # 床
        if not joined:
            ink.path([(ox + 452, 100), (ox + 452, 126)], 14, 2.4)       # 吊り紐
            lamp(ink, ox + 452, 200, True, 1.30)
            # ★輪はここでは描かない。輪は右の絵で【1 つに重なった】ことだけを言う印にする
            gate_frame(ink, ox + 262, 492, 866, 64, 20, dash=DASH)      # まだ無い戸口
            floor_mark(ink, ox + 172, 900, 104, 150, 46, 14, 2.6, dash=DASH_S)
            hc = person(ink, ox + 62, 864, 296, stride=0.62)
            ink.path([hc, (ox + 452, 218)], 11, 2.8, dash=DASH)         # 視線が 2 本
            ink.path([hc, (ox + 262, 486)], 11, 2.8, dash=DASH)
        else:
            # ★吊り灯の【球】が楣の上端にちょうど載る = 画面の上で重なっている。
            #   最初は球を楣の中へ置いたが、輪と笠と楣が団子になって何も読めなかった。
            jx, jy = ox + 352, 466
            gate_frame(ink, jx, jy, 866, 78, 23)                        # 建った戸口
            ink.path([(jx, 100), (jx, 380)], 14, 2.4)                   # 吊り紐
            lamp(ink, jx, 442, True, 1.0)
            ink.arc((jx, 456), 46, 0, 360, 10, 1.8, n=32)               # 重なった 1 点
            floor_mark(ink, ox + 172, 900, 104, 150, 46, 15, 2.6)
            hc = person(ink, ox + 172, 864, 296, stride=0.44)
            ink.path([hc, (ox + 506, 286)], 12, 2.8, dash=DASH)         # 視線は 1 本
            arrow(ink, (ox + 238, 742), (ox + 498, 742), 20, 40, 54)    # 抜けられる
    # 中: 印まで歩く
    arrow(ink, (610, 424), (748, 424), 34, 50, 64)
    foot(ink, (640, 616), 8, 1.02)
    foot(ink, (722, 616), -8, 1.02)
    ink.path([(602, 712), (740, 712)], 14, 2.6)
    arrow(ink, (610, 712), (752, 712), 0.1, 36, 48)


SHEETS = [
    ("gf_a2_gate", gf_a2_gate, 1.4, 7),
    ("gf_a4_peri", gf_a4_peri, 1.6, 11),
    ("gf_a4_touch", gf_a4_touch, -1.9, 22),
    ("gf_a4_both", gf_a4_both, 1.2, 33),
    ("gf_a4_dark", gf_a4_dark, -1.4, 44),
    ("gf_a4_visit", gf_a4_visit, 2.0, 55),
    ("gf_a5_hide", gf_a5_hide, -1.7, 66),
    ("gf_a5_shadow", gf_a5_shadow, 1.5, 77),
    ("gf_a5_marks", gf_a5_marks, -1.1, 88),
    ("gf_a5_four", gf_a5_four, 1.8, 99),
]


# ---------------------------------------------------------------- 焼く
HALO = 28.0        # 縁取りの太さ(設計座標)。線の両側へ 14 単位 ≒ 13mm ≒ 6px ずつ


def _ink_material(name, v):
    """Emission だけの不透明な材質。v=1 で芯(白) / v=0 で縁取り(黒)。"""
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (v, v, v, 1.0)
    em.inputs[1].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def build_graffiti(root=None, out_h=OUT_H, only=None):
    """9 枚を描いて assets/ui/graffiti/gf_*.png へ焼く。

    ★現在開いているシーンには一切触らない。専用のシーンを作って焼き、最後に消す
      (BlenderMCP から回すと、ユーザーが開いている .blend の中で動くため)。
    """
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "assets", "ui", "graffiti")
    os.makedirs(out_dir, exist_ok=True)

    win = getattr(bpy.context, "window", None)       # --background では None
    prev_scene = win.scene if win else None
    prev_display = bpy.context.preferences.view.render_display_type
    bpy.context.preferences.view.render_display_type = "NONE"

    sc = bpy.data.scenes.new("GF_BAKE")
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.render.resolution_y = int(out_h)
    sc.render.resolution_x = int(round(out_h * W / H))
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
    sc.render.image_settings.compression = 92
    # ★白は白のまま焼く(AgX/Filmic だと 1.0 が 0.9 くらいに落ちる)
    try:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
        sc.view_settings.exposure = 0.0
        sc.view_settings.gamma = 1.0
    except Exception as ex:                                    # noqa: BLE001
        print("  view_transform を設定できなかった:", ex)
    # ★world を作らないと EEVEE が落ちる。既定ノードは【名前で引かない】
    #   (Blender 5.2 では "Background" という名前では入っていない)。
    sc.world = bpy.data.worlds.new("GF_WORLD")
    sc.world.use_nodes = True
    for nd in sc.world.node_tree.nodes:
        if nd.type == "BACKGROUND":
            nd.inputs[0].default_value = (0, 0, 0, 1)
            nd.inputs[1].default_value = 0.0

    cam_d = bpy.data.cameras.new("GF_CAM")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = W / SC
    cam = bpy.data.objects.new("GF_CAM", cam_d)
    cam.location = (0.0, 0.0, 4.0)
    cam.rotation_euler = (0.0, 0.0, math.radians(180.0) if ROT180 else 0.0)
    sc.collection.objects.link(cam)
    sc.camera = cam

    mat_halo = _ink_material("GF_HALO", 0.0)
    mat_core = _ink_material("GF_CORE", 1.0)
    made = []
    for name, fn, tilt, seed in SHEETS:
        if only and name not in only:
            continue
        # ★★2 度描く: 太らせた【縁取り】(黒) の上に、素の太さの【芯】(白)。
        #   焼き上がりは  アルファ = 縁取りごとの覆い / 赤 = 芯かどうか。
        #   エンジン側(Graffiti.hlsl)が  色 = lerp(暗い縁, チョーク, 赤)  で組み直す。
        #   ★これが無いと【明るい壁で落書きが消える】。実機で確認した:
        #     暗い柱の上では白い線がよく読めるのに、明滅バンクの真下の白い壁では
        #     ほとんど見えなかった。逆に暗い線にすると今度は暗い所で消える。
        #     縁取りを付けると、明るい壁では暗い縁が、暗い壁では白い芯が形を出す。
        #   ★2 つの Ink は【同じ種】。揺らぎは種から決まるので 1 ピクセルもずれない。
        objs = []
        tris = 0
        for gi, (grow, zb, mt) in enumerate(((HALO, 0.0, mat_halo), (0.0, 0.5, mat_core))):
            ink = Ink(seed, grow=grow, zbase=zb)
            fn(ink)
            tris += len(ink.f)
            me = bpy.data.meshes.new("%s_%d" % (name, gi))
            # 設計座標(y 下向き・単位 1mm)→ Blender(y 上向き・m)。原点は画布の中心
            me.from_pydata([((x - W / 2) / SC, (H / 2 - y) / SC, z) for x, y, z in ink.v],
                           [], ink.f)
            me.update()
            me.materials.append(mt)
            ob = bpy.data.objects.new(me.name, me)
            ob.rotation_euler = (0.0, 0.0, math.radians(tilt))  # 傾きは絵へ焼き込む(罠 7)
            sc.collection.objects.link(ob)
            objs.append((ob, me))

        sc.render.filepath = os.path.join(out_dir, name + ".png")
        bpy.ops.render.render(write_still=True, scene=sc.name)
        made.append((name, tris))
        print("  %-14s  三角 %5d  -> %s.png" % (name, tris, name))

        for ob, me in objs:
            bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.meshes.remove(me, do_unlink=True)

    # 後片付け(ユーザーのシーンを元に戻す)
    rx, ry = sc.render.resolution_x, sc.render.resolution_y
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cam_d, do_unlink=True)
    w = sc.world
    bpy.data.scenes.remove(sc, do_unlink=True)
    bpy.data.worlds.remove(w, do_unlink=True)
    if win and prev_scene:
        win.scene = prev_scene
    bpy.context.preferences.view.render_display_type = prev_display

    print("%d 枚を %s へ焼いた(%dx%d / 180度回転=%s)"
          % (len(made), out_dir, rx, ry, ROT180))
    return made
