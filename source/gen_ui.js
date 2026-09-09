// source/hud_layout.json の表を stagedemo3.json の HUD へ差し込む。
//
// ★何度走らせても同じ結果になる(冪等)。先に前回置いた要素を name で消してから入れ直すので、
//   配置を直して走らせ直す、を繰り返してよい。
//
// ★gen_liminal.py の build_hud() が同じ JSON を読んで同じ物を組む。
//   Python の無い環境ではこちらを使う。表を直すのは hud_layout.json だけでよい。
//
// 使い方:
//   node source/gen_ui.js          … 何が変わるか見るだけ
//   node source/gen_ui.js --write  … 実際に書き込む

const fs = require("fs");
const path = require("path");
const scene_text = require("./scene_text.js");

const ROOT = path.resolve(__dirname, "..");
const SCENE = path.join(ROOT, "assets/scenes/stagedemo3.json");
const LAYOUT = path.join(__dirname, "hud_layout.json");

// guid は名前から決める(毎回同じ値になる = 走らせ直しても差分が出ない)
function guidOf(name) {
  let h1 = 0x9e3779b9, h2 = 0x85ebca6b;
  for (let i = 0; i < name.length; i++) {
    h1 = Math.imul(h1 ^ name.charCodeAt(i), 0x01000193) >>> 0;
    h2 = Math.imul(h2 + name.charCodeAt(i), 0x85ebca6b) >>> 0;
  }
  return (h1.toString(16).padStart(8, "0") + h2.toString(16).padStart(8, "0")).slice(0, 16);
}

// 配置の 1 行 -> シーンの実体
function toEntity(el, pal, canvasGuid) {
  const ink = pal.ink, sub = pal.sub;
  const x0 = el.x0 !== undefined ? el.x0 : el.x - el.w / 2;
  const x1 = el.x1 !== undefined ? el.x1 : el.x + el.w / 2;
  const y0 = el.y - el.h / 2, y1 = el.y + el.h / 2;

  const e = {
    name: el.name,
    guid: guidOf(el.name),
    transform: { position: [0, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] },
    parentGuid: canvasGuid,
    uiRect: {
      anchorMin: [0, 0], anchorMax: [0, 0], pivot: [0.5, 0.5],
      offsetMin: [x0, y0], offsetMax: [x1, y1],
      visible: !el.hidden, order: el.order || 0,
    },
  };

  const rgb = el.color || (el.sub ? sub : ink);
  const a = el.a !== undefined ? el.a : 1;

  if (el.type === "image") {
    const img = { texturePath: el.tex || "", color: [rgb[0], rgb[1], rgb[2], a] };
    if (el.radius) img.cornerRadius = el.radius;
    if (el.outline) {
      img.outlineWidth = el.outline;
      const oc = el.outlineColor || ink;
      img.outlineColor = [oc[0], oc[1], oc[2], 0.22];
    }
    e.uiImage = img;
  } else {
    e.uiText = {
      text: el.text || "", fontSize: el.size || 22,
      color: [rgb[0], rgb[1], rgb[2], a],
      alignH: el.align === undefined ? 1 : el.align, alignV: 1, wrap: false,
      // ★暗い場所にも明るい場所にも同じ HUD が出るので、細くても縁は必ず付ける
      outlineWidth: 0.8, outlineColor: [0.03, 0.03, 0.03, 0.55],
    };
  }
  return e;
}

function build(layout, canvasGuid) {
  return layout.elements.filter((el) => el.name).map((el) => toEntity(el, layout.palette, canvasGuid));
}

function main() {
  const write = process.argv.includes("--write");
  const layout = JSON.parse(fs.readFileSync(LAYOUT, "utf8"));
  const scene = JSON.parse(fs.readFileSync(SCENE, "utf8"));

  const canvas = scene.entities.find((e) => e.name === layout.canvas);
  if (!canvas) throw new Error(`${layout.canvas} がシーンに無い`);

  const added = build(layout, canvas.guid);
  const names = new Set(added.map((e) => e.name));
  const before = scene.entities.length;
  scene.entities = scene.entities.filter((e) => !names.has(e.name));
  const replaced = before - scene.entities.length;
  scene.entities.push(...added);

  console.log(`HUD 要素 ${added.length} 個` + (replaced ? `(うち ${replaced} 個は置き換え)` : "(新規)"));
  for (const e of added)
    console.log(`  ${e.name.padEnd(16)} ${e.uiImage ? "画像 " + (e.uiImage.texturePath || "(単色)") : "文字 " + JSON.stringify(e.uiText.text)}`);

  if (!write) { console.log("\n(--write を付けると実際に書き込む)"); return; }

  // ★JSON.stringify で書き直さない(scene_text.js の頭のコメントの理由)。
  //   前回置いた要素をテキストごと取り除いてから、末尾へ足す。
  let text = fs.readFileSync(SCENE, "utf8");
  for (const n of names) text = scene_text.removeEntity(text, n);
  text = scene_text.appendEntities(text, added);

  const check = JSON.parse(text);          // 壊していないことを書く前に確かめる
  const got = new Set(check.entities.map((e) => e.name));
  for (const n of names) if (!got.has(n)) throw new Error(`${n} が入っていない`);

  fs.writeFileSync(SCENE, text, "utf8");
  console.log(`\nstagedemo3.json を更新した(実体 ${check.entities.length} 個)`);
}

module.exports = { build, guidOf };
if (require.main === module) main();
