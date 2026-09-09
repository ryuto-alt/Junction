// タイトルの字の SVG を書き出す。  node gen_logo_svg.js
//
// 出力先: source/ui_icons/svg_logo/*.svg  (ここが【編集元】。PNG は build_logo.js で焼く)
//
// ★なぜ生成するのか: 字は logo_glyphs.js の枡目(キャップハイト 200)から組んでいる。
//   太さ・字間・継ぎ目の位置を変えたくなったとき、パスを手で書き直すのは無理なので
//   「版下 → SVG」を機械にやらせる。SVG 自体は普通に開いて手直ししてよいが、
//   このスクリプトを再実行すると上書きされる。
//
// ★【継ぎ目】について:
//   JUNCTION は「継ぎ目」の意味。だから題名の字そのものを 1 本の水平線で
//   上下に断ち割り、上半分 junction_top.svg / 下半分 junction_bottom.svg の
//   【2 枚】に分けて焼く。線そのものは焼かない ―― 線は TitleMenu.lua が
//   ui:rect で引く(ロード画面の 1 本の線・カーテンの合わせ目と同じ「線」に揃えるため。
//   画面幅いっぱいまで伸ばしたり、蛍光灯のように瞬かせたりできる)。
//   2 枚は同じ viewBox なので、同じ矩形に重ねれば必ず継ぎ目が合う。

const fs = require("fs");
const path = require("path");
const { layout, f } = require("./logo_glyphs");

const OUT = path.join(__dirname, "svg_logo");

// ---- 題名 ----
const LOGO_W     = 46;   // 太さ。案内板の見出しくらい太く
const LOGO_TRACK = 36;   // 字間。余白を多く = 静かな絵作り
const LOGO_M     = 24;   // 余白(焼くときに端が欠けないように)
const SEAM_Y     = 94;   // 継ぎ目の位置(キャップ上端からの距離)。中心よりわずかに上
const SEAM_GAP   = 13;   // 継ぎ目の空き

// ---- 選択肢 ----
const MENU_W     = 24;   // 題名より細い = 「見出しの板」と「刻印」の差
const MENU_TRACK = 40;   // 字間はさらに広く。読ませるのではなく「置いてある」見え方
const MENU_M     = 12;

function svg(w, h, body, defs) {
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${f(w)}" height="${f(h)}" ` +
    `viewBox="0 0 ${f(w)} ${f(h)}">\n` +
    (defs || "") +
    // 塗りも線も白。色は実行時に scene:setUiColor で掛ける(色は乗算なので、
    // 白く焼いておけば「薄い金」にも「点いた瞬間の白」にも同じ 1 枚が使える)
    `<g fill="#ffffff" stroke="none">\n  ${body}\n</g>\n</svg>\n`
  );
}

// 字の入れ物。塗りの字も線の字も同じ白。太さ・fill/stroke の有無は
// logo_glyphs.js が path ごとに書き出しているので、ここでは色だけ与える。
function wordGroup(body, M) {
  return (
    `<g transform="translate(${f(M)} ${f(M)})" ` +
    `fill="#ffffff" stroke="#ffffff" stroke-linecap="butt">\n  ${body}\n  </g>`
  );
}

function writeWord(name, word, W, track, M) {
  const { width, body } = layout(word, W, track);
  const vw = width + M * 2;
  const vh = 200 + M * 2;
  fs.writeFileSync(path.join(OUT, name + ".svg"), svg(vw, vh, wordGroup(body, M)));
  return { vw, vh, width };
}

function main() {
  fs.mkdirSync(OUT, { recursive: true });

  // ---- 題名を上下 2 枚に割る ----
  {
    const { width, body } = layout("JUNCTION", LOGO_W, LOGO_TRACK);
    const vw = width + LOGO_M * 2;
    const vh = 200 + LOGO_M * 2;
    const seam = LOGO_M + SEAM_Y;
    const cutT = seam - SEAM_GAP / 2;
    const cutB = seam + SEAM_GAP / 2;

    const word = wordGroup(body, LOGO_M);

    const mk = (clipId, y0, y1) =>
      svg(
        vw,
        vh,
        `<g clip-path="url(#${clipId})">${word}</g>`,
        `<defs><clipPath id="${clipId}">` +
          `<rect x="0" y="${f(y0)}" width="${f(vw)}" height="${f(y1 - y0)}"/>` +
          `</clipPath></defs>\n`
      );

    fs.writeFileSync(path.join(OUT, "junction_top.svg"), mk("cT", 0, cutT));
    fs.writeFileSync(path.join(OUT, "junction_bottom.svg"), mk("cB", cutB, vh));

    console.log(`題名  viewBox ${f(vw)}x${f(vh)}  字幅 ${f(width)}  継ぎ目 y=${f(seam)}`);
    console.log(`      → 画面(1600x900 基準)で高さ H を決めると 幅 = H * ${(vw / vh).toFixed(4)}`);
    console.log(`      → 継ぎ目は矩形の上端から 高さ * ${(seam / vh).toFixed(4)}`);
  }

  // ---- 選択肢 ----
  for (const w of ["START", "EXIT"]) {
    const r = writeWord("label_" + w.toLowerCase(), w, MENU_W, MENU_TRACK, MENU_M);
    console.log(
      `${w}  viewBox ${f(r.vw)}x${f(r.vh)}  → 高さ H のとき 幅 = H * ${(r.vw / r.vh).toFixed(4)}`
    );
  }
}

main();
