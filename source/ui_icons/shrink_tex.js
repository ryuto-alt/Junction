// assets/models/tex/lm_*_col.png と assets/ui/shots/*.png を縮小する。
//
// ★なぜ要るのか(2026-09-09「まじで重たい」「タイトルから遷移するとフリーズ」):
//   配布ビルドのログを測ると、タイトルから stagedemo3 の preloadScene に届くまで
//   34.9 秒。その内訳はほぼ全部【BC7 圧縮】だった:
//
//     BC 圧縮 2.5s: 1024x1024 BC7_UNORM_SRGB ... lm_carpet_col.png
//     BC 圧縮 1.1s: 1164x768  BC7_UNORM_SRGB ... sign_stand_mark.png
//     …これが 18 枚で合計 29.4 秒。残りの全処理を足しても 0.35 秒しかない。
//
//   しかも配布ビルドでは圧縮結果を保存できていない:
//     [warning] BC 圧縮キャッシュの保存に失敗しました: <ゲームフォルダ>/.texcache/*.dds
//   ＝【毎回】起動するたびに 29 秒かけて焼き直している。キャッシュは engine 側の
//   話なので直せないが、BC7 の時間は【画素数にほぼ比例】する。だから縮める。
//
// ★どこまで縮めるか = 実際に PNG を開いて 1:1 で見比べて決めた。
//   この作品はポストプロセスの pixelSize=2.0 (Liminal.lua) で 960x540 相当まで
//   落としてから出しているので、1024 の解像度はそもそも画面に出ていない。
//   ただし「潰れる物」と「潰れない物」があったので一律にはしない:
//
//     512 に留める … 細かい模様が 256 で目に見えて消えた物
//        lm_tilefloor / lm_tilewall … 目地(グラウト)の線。256 だと線が薄れて
//                                     格子がまだらになる
//        lm_carpet                  … 織り目の粒。256 だとのっぺりする
//        lm_ceil                    … 細かい斑点。同上
//        lm_exit                    … 非常口ピクトグラム。枠の白帯が 256 で痩せる
//
//     256 まで落とす … 1:1 で見て【ほぼ無地】だった物。256 と 1024 の差が無い
//        lm_wall / lm_wall2 / lm_paint / lm_conc / lm_metal / lm_lamp / lm_door
//        (縮小版のサムネイルだと lm_wall に縦縞が見えるが、あれは【サムネイル側の
//         モアレ】で、原寸を見ると縞は無い。見ないで決めないこと)
//
//   ui/shots は【ぼかしてからピントを合わせる】タイトルの演出用なので半分で足りる。
//   ただし shots は BC7 に掛からない(format=91 のまま)ので【読み込みは速くならない】。
//   game.pak が 2MB 縮むだけ。
//
// ★触らない物:
//   ・assets/ui/logo/*.png … 2100x356 だが実測 0.14 秒。題名なので画質優先で据え置き。
//   ・assets/models/tex/ の lm_ が付かない 20 枚 … gltf からは参照されているが
//     相対パスが解決できず(「テクスチャが見つかりません: ../../tex/carpet_col.png」)、
//     実際には【一度も読み込まれない】。縮めても起動は 1 秒も速くならない。
//     消せば game.pak が 15MB ほど減るが、それは別の判断なので触らない。
//
// ★元に戻したい時: out/tex_orig_1024/ に原寸を退避してある(out/ は .gitignore 済み)。
//
// 使い方:  cd source/ui_icons && node shrink_tex.js
// ★二度流しても壊れない。目標より小さい画像は触らずに飛ばす。

const fs = require("fs");
const path = require("path");
const sharp = require("sharp");

const ROOT = path.resolve(__dirname, "../..");
const TEX = path.join(ROOT, "assets/models/tex");
const SHOTS = path.join(ROOT, "assets/ui/shots");
const BACKUP = path.join(ROOT, "out/tex_orig_1024");

// 目標の一辺(px)。上のコメントの理由で 512 組と 256 組に分けている。
const KEEP_512 = ["lm_tilefloor_col", "lm_tilewall_col", "lm_carpet_col",
                  "lm_ceil_col", "lm_exit_col"];
const TO_256 = ["lm_wall_col", "lm_wall2_col", "lm_paint_col", "lm_conc_col",
                "lm_metal_col", "lm_lamp_col", "lm_door_col"];

async function shrink(file, w, h) {
  const buf = fs.readFileSync(file);
  const meta = await sharp(buf).metadata();
  if (meta.width <= w) {                       // ★もう小さい = 二度流し。飛ばす
    console.log(`  skip  ${path.basename(file)}  (既に ${meta.width}x${meta.height})`);
    return;
  }
  // 原寸を退避。既にあれば【上書きしない】(縮小版で原寸を潰さないため)
  fs.mkdirSync(BACKUP, { recursive: true });
  const bak = path.join(BACKUP, path.basename(file));
  if (!fs.existsSync(bak)) fs.writeFileSync(bak, buf);

  // lanczos3。目地のような細い線を残したいので、ぼける kernel は使わない
  const out = await sharp(buf).resize(w, h, { kernel: "lanczos3" })
    .png({ compressionLevel: 9 }).toBuffer();
  fs.writeFileSync(file, out);
  console.log(`  ${path.basename(file)}  ${meta.width}x${meta.height} -> ${w}x${h}` +
    `  ${(buf.length / 1024).toFixed(0)}KB -> ${(out.length / 1024).toFixed(0)}KB`);
}

async function main() {
  console.log("assets/models/tex/  (BC7 圧縮の 8 割を占めている所)");
  for (const n of KEEP_512) await shrink(path.join(TEX, n + ".png"), 512, 512);
  for (const n of TO_256) await shrink(path.join(TEX, n + ".png"), 256, 256);

  console.log("assets/ui/shots/  (タイトルの縮小モンタージュ。pak を減らすだけ)");
  for (const f of fs.readdirSync(SHOTS).filter((f) => f.endsWith(".png")).sort())
    await shrink(path.join(SHOTS, f), 526, 296);

  console.log(`原寸は ${path.relative(ROOT, BACKUP)} に退避済み`);
}

main();
