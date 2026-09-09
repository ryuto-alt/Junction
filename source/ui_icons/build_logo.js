// source/ui_icons/svg_logo/*.svg を assets/ui/logo/*.png へ焼く。
//
// ★build.js(HUD のキー記号を 3:2 の画布へ押し込む)とも
//   build_signs.js(壁の案内板。不透明な板・180 度回転)とも【別物】。
//   タイトルの字は「UI に重ねる透明な絵」なので:
//     ・縦横比は SVG のまま(押し込むと字が痩せる)
//     ・背景は透明・字は白(色は実行時に scene:setUiColor で掛ける)
//     ・回転しない(3D の板ではなく画面に貼る絵なので)
//
// ★junction_top.png と junction_bottom.png は【同じ viewBox】から焼くので
//   必ず同じ画素数になる。同じ矩形に重ねれば継ぎ目が合う。ここで検査もしている。
//
// 焼いた PNG はリポジトリに入れる = 遊ぶ側に node は要らない。
// 字を直したい時だけ:  cd source/ui_icons && node gen_logo_svg.js && node build_logo.js

const fs = require("fs");
const path = require("path");
const { Resvg } = require("@resvg/resvg-js");

const HERE = __dirname;
const SVG_DIR = path.join(HERE, "svg_logo");
const OUT_DIR = path.resolve(HERE, "../../assets/ui/logo");

// 焼く幅(px)。題名は画面(1600 基準)で 1030 前後で出すので 2 倍強。
// 選択肢は小さく出すので幅を抑える(それでも画面上の 5 倍以上ある)。
const WIDTH = { junction_top: 2100, junction_bottom: 2100, label_start: 900, label_exit: 640 };

function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const names = fs.readdirSync(SVG_DIR).filter((f) => f.endsWith(".svg")).sort();
  if (!names.length) throw new Error("svg_logo/ に SVG が無い。先に node gen_logo_svg.js");

  const sizes = {};
  for (const file of names) {
    const name = file.replace(/\.svg$/, "");
    const src = fs.readFileSync(path.join(SVG_DIR, file), "utf8");
    const r = new Resvg(src, {
      background: "rgba(0,0,0,0)",
      fitTo: { mode: "width", value: WIDTH[name] || 1024 },
      font: { loadSystemFonts: false },   // ★字は図形。フォントは一切使わない
    });
    const img = r.render();
    fs.writeFileSync(path.join(OUT_DIR, name + ".png"), img.asPng());
    sizes[name] = [img.width, img.height];
    console.log(`  ${name}  ${img.width}x${img.height}`);
  }

  // 上半分と下半分がずれていたら継ぎ目が合わない。焼いた時点で気づけるようにする。
  const a = sizes["junction_top"], b = sizes["junction_bottom"];
  if (a && b && (a[0] !== b[0] || a[1] !== b[1]))
    throw new Error(`題名の上下で画素数が違う: ${a} vs ${b}`);

  console.log(`${names.length} 枚を assets/ui/logo/ へ焼いた`);
}

main();
