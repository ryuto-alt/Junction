// source/ui_icons/svg/*.svg を assets/ui/icons/*.png へ焼く。
//
// ★なぜ PNG にするのか:
//   エンジンのテクスチャ読み込みは DirectXTex で、SVG は読めない(vcpkg.json に
//   ラスタライザが無い)。そこで【編集元は SVG のまま】にして、ゲームが読むのは
//   ここで焼いた PNG にする。線の太さも文字も SVG 側で直せば、焼き直すだけで反映される。
//
// ★白 + 透明で焼く。色は実行時に scene:setUiColor で掛ける(色は掛け算なので、
//   白く焼いておけば 1 枚の PNG が「薄い案内」にも「押された瞬間の明るい強調」にもなる)。
//
// 焼いた PNG はリポジトリに入れる = 遊ぶ側に npm は要らない。
// 絵を直したい時だけ:  cd source/ui_icons && npm install && node build.js
//
// ★全部を同じ縦横比(3:2)の画布へ入れて焼く。理由は差し替えのため:
//   同じ枠に「キーボードの記号」と「コントローラーの記号」を出し分けるのに、
//   エンジンには UIRect の大きさを実行時に変える口が無い(setUiTexture はある)。
//   縦横比が違うまま差し替えると絵が潰れるので、焼く側で揃えておく。
//   はみ出す分は透明の余白になるだけなので、並べる時は見えている部分で詰めてよい。

const fs = require("fs");
const path = require("path");
const { Resvg } = require("@resvg/resvg-js");

const HERE = __dirname;
const SVG_DIR = path.join(HERE, "svg");
const OUT_DIR = path.resolve(HERE, "../../assets/ui/icons");

const HEIGHT = 192;          // 焼く高さ(px)。画面上は 34〜56px なので 3〜5 倍。拡大に耐える
const ASPECT = 1.5;          // 全部この縦横比の画布へ収める(差し替えても潰れない)
const PAD = 0.94;            // 画布いっぱいだと縁が切れるので少し余らせる

// 元の SVG を 3:2 の画布の中央へ、はみ出さない倍率で入れ子にする。
// 入れ子の <svg viewBox> は SVG の標準機能なので、元のファイルは一切書き換えない。
function fitToCanvas(src, cw, ch) {
  const m = /<svg[^>]*\bwidth="([\d.]+)"[^>]*\bheight="([\d.]+)"/.exec(src);
  if (!m) throw new Error("width/height の無い SVG");
  const w = parseFloat(m[1]), h = parseFloat(m[2]);
  const k = Math.min((cw * PAD) / w, (ch * PAD) / h);
  const iw = w * k, ih = h * k;
  const inner = src.replace(/^[\s\S]*?<svg[^>]*>/, "").replace(/<\/svg>\s*$/, "");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${cw}" height="${ch}" viewBox="0 0 ${cw} ${ch}">\n` +
    `<svg x="${((cw - iw) / 2).toFixed(2)}" y="${((ch - ih) / 2).toFixed(2)}" ` +
    `width="${iw.toFixed(2)}" height="${ih.toFixed(2)}" viewBox="0 0 ${w} ${h}">\n${inner}</svg>\n</svg>\n`;
}

function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const names = fs.readdirSync(SVG_DIR).filter((f) => f.endsWith(".svg")).sort();
  const cw = Math.round(HEIGHT * ASPECT), ch = HEIGHT;

  for (const file of names) {
    const src = fs.readFileSync(path.join(SVG_DIR, file), "utf8");
    const r = new Resvg(fitToCanvas(src, cw, ch), {
      background: "rgba(0,0,0,0)",
      font: { loadSystemFonts: true, defaultFontFamily: "Arial" },
    });
    const img = r.render();
    const name = file.replace(/\.svg$/, "");
    if (img.width !== cw || img.height !== ch)
      throw new Error(`${name}: ${img.width}x${img.height} になった(${cw}x${ch} のはず)`);
    fs.writeFileSync(path.join(OUT_DIR, name + ".png"), img.asPng());
    console.log(`  ${name}`);
  }
  console.log(`${names.length} 枚を ${cw}x${ch}(縦横比 ${ASPECT})で assets/ui/icons/ へ焼いた`);
}

main();
