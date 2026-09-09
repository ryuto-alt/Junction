// source/ui_icons/svg_signs/*.svg を assets/ui/signs/*.png へ焼く。
//
// ★build.js とは【別物】。build.js は HUD のキー記号を全部 3:2 の画布へ押し込むが、
//   案内板は壁に貼る一枚板なので、縦横比を SVG のまま保ったまま高い解像度で焼く。
//   (押し込むと絵が縮んで余白だらけになり、廊下の向こうから読めない)
//
// ★焼いた PNG はリポジトリに入れる = 遊ぶ側に node は要らない。
//   絵を直したい時だけ:  cd source/ui_icons && node build_signs.js
//
// ★★【上下左右を反転して焼く】。理由:
//   案内板は box プリミティブの -Z 面へ貼る。このエンジンの箱の -Z 面は
//     ・u が -x 向き   … 左右が反転する(source/gen_liminal_tex.py の exitsign() が
//                        既に col[:, ::-1, :] で先に反転させているのと同じ理由)
//     ・v が 画像の上=実物の下 … 上下も反転する(同じ exitsign() は頭を w=0.72 =
//                        PNG の下半分に描いている。それで実物では頭が上に来る)
//   合わせて 180 度回転。だから SVG は【人が見て正しい向き】のまま描いてよく、
//   ここで回してから書き出す。SVG を直接いじらないので、絵の編集は普通にできる。
//   ★もし実機で案内板が逆さまに見えたら、ここの ROT180 を false にすれば直る。
//     (SVG 側は一切触らないこと)

const fs = require("fs");
const path = require("path");
const { Resvg } = require("@resvg/resvg-js");

const HERE = __dirname;
const SVG_DIR = path.join(HERE, "svg_signs");
const OUT_DIR = path.resolve(HERE, "../../assets/ui/signs");

const HEIGHT = 768;      // 焼く高さ(px)。板は実寸 0.66m なので 1160 texel/m。近寄っても崩れない
const ROT180 = true;     // 箱の -Z 面へ貼るための 180 度回転(上の説明)

// 元の SVG を、同じ viewBox のまま 180 度回した入れ子にする。
// 入れ子の <g transform> は SVG の標準機能なので、元のファイルは一切書き換えない。
function rotate180(src) {
  const m = /<svg[^>]*\bwidth="([\d.]+)"[^>]*\bheight="([\d.]+)"/.exec(src);
  if (!m) throw new Error("width/height の無い SVG");
  const w = parseFloat(m[1]), h = parseFloat(m[2]);
  const inner = src.replace(/^[\s\S]*?<svg[^>]*>/, "").replace(/<\/svg>\s*$/, "");
  const body = ROT180
    ? `<g transform="rotate(180 ${w / 2} ${h / 2})">\n${inner}</g>\n`
    : inner;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" ` +
    `viewBox="0 0 ${w} ${h}">\n${body}</svg>\n`;
}

function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const names = fs.readdirSync(SVG_DIR).filter((f) => f.endsWith(".svg")).sort();
  if (!names.length) throw new Error("svg_signs/ に SVG が無い");

  for (const file of names) {
    const src = fs.readFileSync(path.join(SVG_DIR, file), "utf8");
    // 案内板は不透明な板。透明で焼くと縁が黒く抜ける
    const r = new Resvg(rotate180(src), {
      background: "#E4DFCD",
      fitTo: { mode: "height", value: HEIGHT },
      font: { loadSystemFonts: false },   // ★文字は使わない。読み込む必要も無い
    });
    const img = r.render();
    const name = file.replace(/\.svg$/, "");
    fs.writeFileSync(path.join(OUT_DIR, name + ".png"), img.asPng());
    console.log(`  ${name}  ${img.width}x${img.height}`);
  }
  console.log(`${names.length} 枚を assets/ui/signs/ へ焼いた(180度回転 = ${ROT180})`);
}

main();
