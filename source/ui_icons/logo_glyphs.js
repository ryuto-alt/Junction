// JUNCTION タイトル用の【字の版下】。
//
// ★なぜ自前で字を作るのか:
//   assets/ にフォントファイル(.ttf/.otf)が無く、ui:text の素の字は
//   「施設の標識」には見えない。build_signs.js が font.loadSystemFonts=false で
//   焼いているのと同じ理由で、字は【図形として】描く。
//
// ★字の考え方(この作品に合わせたもの):
//   ・リミナル空間 = 誰も居ない施設。だから避難経路図・案内板の字に寄せる。
//     幾何学的サンセリフ(円と直線だけ)、セリフ無し、装飾無し。
//   ・全部の字が【キャップハイト 200 の枡目】に入る。ベースラインは y=200。
//     y は下向き(SVG の流儀)。左上が原点。
//   ・太さ W は引数。ロゴは太く(46)、START/EXIT は細く(24)焼く =
//     「見出しは太い板、案内は細い刻印」という標識の階層をそのまま持ち込む。
//
// ★曲線の字(J U C O S)は【線(stroke)】で描く。太さが一定になるうえ、
//   輪郭を手で解く必要が無いので歪まない。角の尖る字(N T I E X R A)は
//   【塗り(fill)】で描く。混ぜてよい: どちらも同じ色で塗るので継ぎ目は出ない。
//
// 返り値: { advance, elems }  elems は SVG 要素の文字列の配列。
//   線の字は fill="none" + stroke-width 付き、塗りの字は素の <path>。

const H = 200; // キャップハイト。全字共通

// 小数を短く。SVG のパスは桁が多いと読めなくなるだけ
const f = (v) => {
  const s = (Math.round(v * 100) / 100).toString();
  return s;
};

// 塗りで描く字。★stroke="none" を必ず付ける(親の stroke を継ぐと字が太る)
const rect = (x, y, w, h) => `<path stroke="none" d="M${f(x)} ${f(y)}h${f(w)}v${f(h)}h${f(-w)}z"/>`;
const poly = (pts) => `<path stroke="none" d="M${pts.map((p) => `${f(p[0])} ${f(p[1])}`).join("L")}z"/>`;
// 線で描く字。★fill="none" を必ず付ける(親の fill を継ぐと、線で描いた
//   "U" の内側まで塗り潰されて別の字になる。実際そうなった)
const line = (d, W, join) =>
  `<path fill="none" stroke-width="${f(W)}" stroke-linejoin="${join || "round"}" d="${d}"/>`;

const rad = (deg) => (deg * Math.PI) / 180;

// ---------------------------------------------------------------- 字の定義
// どれも (W, advance) を受けて { advance, elems } を返す。
// advance を省くと、その字の「素直な幅」を使う。

function glyphJ(W, A) {
  // 右に縦棒、下で左へ回り込む鉤。鉤は半円 1 つ。
  const hw = W / 2;
  const r = (A - W) / 2;          // 中心線の半径
  const cy = H - hw - r;          // 半円の中心 y。外周が y=200 にちょうど接する
  return { advance: A, elems: [line(`M${f(A - hw)} 0V${f(cy)}A${f(r)} ${f(r)} 0 0 1 ${f(hw)} ${f(cy)}`, W)] };
}

function glyphU(W, A) {
  const hw = W / 2;
  const r = (A - W) / 2;
  const cy = H - hw - r;
  return {
    advance: A,
    elems: [line(`M${f(hw)} 0V${f(cy)}A${f(r)} ${f(r)} 0 0 0 ${f(A - hw)} ${f(cy)}V0`, W)],
  };
}

function glyphN(W, A) {
  return {
    advance: A,
    elems: [
      rect(0, 0, W, H),
      rect(A - W, 0, W, H),
      poly([[0, 0], [W, 0], [A, H], [A - W, H]]),
    ],
  };
}

function glyphC(W, A) {
  // 右に 38 度ぶんの口を開けた楕円環。終端は放射状の切り口(標識の字の切り方)
  const rx = (A - W) / 2;
  const ry = (H - W) / 2;
  const cx = A / 2;
  const cy = H / 2;
  const a = rad(38);
  const px = cx + rx * Math.cos(a);
  const py1 = cy + ry * Math.sin(a);
  const py2 = cy - ry * Math.sin(a);
  return {
    advance: A,
    elems: [line(`M${f(px)} ${f(py1)}A${f(rx)} ${f(ry)} 0 1 1 ${f(px)} ${f(py2)}`, W)],
  };
}

function glyphT(W, A) {
  return { advance: A, elems: [rect(0, 0, A, W), rect((A - W) / 2, W, W, H - W)] };
}

function glyphI(W) {
  return { advance: W, elems: [rect(0, 0, W, H)] };
}

function glyphO(W, A) {
  const hw = W / 2;
  const rx = (A - W) / 2;
  const ry = (H - W) / 2;
  return {
    advance: A,
    elems: [
      line(
        `M${f(hw)} ${f(H / 2)}A${f(rx)} ${f(ry)} 0 0 1 ${f(A - hw)} ${f(H / 2)}` +
          `A${f(rx)} ${f(ry)} 0 0 1 ${f(hw)} ${f(H / 2)}Z`,
        W
      ),
    ],
  };
}

function glyphS(W) {
  // 上下に接する同じ半径の円 2 つ。幅は自動的に決まる(細くすると自然に細くなる)
  const hw = W / 2;
  const r = (H - W) / 4;
  const A = 2 * r + W;
  const cx = A / 2;
  const cy1 = hw + r;
  const cy2 = H - hw - r;
  const a = rad(20);
  const sx = cx + r * Math.cos(-a), sy = cy1 + r * Math.sin(-a);
  const ex = cx - r * Math.cos(a), ey = cy2 + r * Math.sin(a);
  return {
    advance: A,
    elems: [
      line(
        `M${f(sx)} ${f(sy)}A${f(r)} ${f(r)} 0 1 0 ${f(cx)} ${f(H / 2)}` +
          `A${f(r)} ${f(r)} 0 1 1 ${f(ex)} ${f(ey)}`,
        W
      ),
    ],
  };
}

function glyphE(W, A) {
  const m0 = H / 2 - W / 2;
  const m1 = H / 2 + W / 2;
  const Am = A * 0.84;            // 中の腕だけ少し短い(標識の字の作法)
  const d =
    `M0 0H${f(A)}V${f(W)}H${f(W)}V${f(m0)}H${f(Am)}V${f(m1)}H${f(W)}` +
    `V${f(H - W)}H${f(A)}V${f(H)}H0z`;
  return { advance: A, elems: [`<path stroke="none" d="${d}"/>`] };
}

function glyphX(W, A) {
  return {
    advance: A,
    elems: [
      poly([[0, 0], [W, 0], [A, H], [A - W, H]]),
      poly([[A - W, 0], [A, 0], [W, H], [0, H]]),
    ],
  };
}

function glyphR(W, A) {
  const hw = W / 2;
  const BH = H * 0.52;            // 腹(ボウル)の高さ
  const bowlRight = A - W * 0.55; // 腹の右の外側
  const bx = bowlRight - hw - (BH - W) / 2;
  const rx = bowlRight - hw - bx;
  const ry = (BH - W) / 2;
  const legW = W * 1.25;          // 斜めの脚は「横幅」で測るので少し広い
  return {
    advance: A,
    elems: [
      rect(0, 0, W, H),
      line(`M${f(hw)} ${f(hw)}H${f(bx)}A${f(rx)} ${f(ry)} 0 0 1 ${f(bx)} ${f(BH - hw)}H${f(hw)}`, W),
      poly([[W, BH], [W + legW, BH], [A, H], [A - legW, H]]),
    ],
  };
}

function glyphA(W, A) {
  // 山は【面取り(bevel)】。尖らせると miter が枡目の外へ飛び出す
  const hw = W / 2;
  const cx = A / 2;
  const len = Math.hypot(cx, H);
  const halfX = hw * (len / H);           // 斜めの脚の「横方向の」半幅
  const cbY = H * 0.66;                   // 横棒の上端
  const xcAtBottom = (cx * (H - (cbY + W))) / H;
  const L = xcAtBottom + halfX - 1;       // 横棒は脚の内側へ 1 だけ食い込ませる(隙間を作らない)
  return {
    advance: A,
    elems: [
      line(`M0 ${f(H)}L${f(cx)} 0L${f(A)} ${f(H)}`, W, "bevel"),
      rect(L, cbY, A - L * 2, W),
    ],
  };
}

// ---------------------------------------------------------------- 表
// キー = 文字。値 = (W) => {advance, elems}
// advance は「太さ 46(ロゴ)」を基準に決めた値を W で素直に伸縮させる。
const TABLE = {
  J: (W) => glyphJ(W, 46 + W * 1.87),
  U: (W) => glyphU(W, 46 + W * 2.26),
  N: (W) => glyphN(W, 46 + W * 2.39),
  C: (W) => glyphC(W, 46 + W * 2.43),
  T: (W) => glyphT(W, 46 + W * 2.26),
  I: (W) => glyphI(W),
  O: (W) => glyphO(W, 46 + W * 2.43),
  S: (W) => glyphS(W),
  E: (W) => glyphE(W, 46 + W * 1.65),
  X: (W) => glyphX(W, 46 + W * 2.0),
  R: (W) => glyphR(W, 46 + W * 2.1),
  A: (W) => glyphA(W, 46 + W * 2.3),
};

// 語を組む。{ width, body } を返す。body は原点 (0,0) 起点の SVG 要素列。
function layout(word, W, tracking) {
  const parts = [];
  let x = 0;
  for (let i = 0; i < word.length; i++) {
    const ch = word[i];
    const make = TABLE[ch];
    if (!make) throw new Error(`版下に無い字: ${ch}`);
    const g = make(W);
    parts.push(`<g transform="translate(${f(x)} 0)">${g.elems.join("")}</g>`);
    x += g.advance;
    if (i < word.length - 1) x += tracking;
  }
  return { width: x, body: parts.join("\n  ") };
}

module.exports = { H, layout, f };
