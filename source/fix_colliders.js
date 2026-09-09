// stagedemo3.json の「歩いて当たるはずなのに擦り抜ける物」に静的な当たり判定を足す。
//
// ★なぜ機械で決めるか:
//   什器は 900 個ある。手で選ぶと必ず取りこぼすし、逆に天井の照明や床の擦れ跡へ
//   当たり判定を付けてしまう(見えない壁になる)。そこで【体の高さ帯に掛かるか】
//   という一つの規則だけで決める。
//
// 規則:
//   その箱の真下にある一番高い『立てる面』を床とみなし、床からの高さで見る。
//     ・天井 (箱の下端 >= 身長)                  … いらない。頭上を通るだけ
//     ・床の模様/幅木 (箱の上端 <= またげる高さ) … いらない。踏んで歩ける
//     ・その間に掛かる物                          … 要る。体が通れないので止める
//
// 付けないもの(除外):
//   ・継ぎ目の仕掛けが掴んでいる実体(破片・出現物・可動物・丁番・標識)。
//     破片は焦点から見た時だけ形になる幻で、動く。当たり判定を付けると
//     「見えないのにぶつかる」「動く壁に押し出される」になる。
//   ・glow() で作った発光板。物ではなく【明かり】なので、ぶつかる物ではない。
//   ・囮と偽の印(lure / dud / mark)。★これは特に大事:
//     囮の板は「浮いている破片と同じ見かけ」に【わざと】してある(gen_liminal.py の
//     W5_lure のコメント)。当たり判定を付けると、ぶつかるかどうかで本物の破片と
//     見分けがついてしまい、謎解きが崩れる。偽の印も同じ理由。
//   ・非常口の標識と開口のケーシング(枠飾り)。壁に貼ってあるだけの薄い飾りで、
//     壁側に当たり判定がある。付けると出入口が左右から狭まるだけ。
//   ・プレイヤーの通り道(CHECKS)を塞ぐ物。これを足すと進行不能になる。
//     ★塞ぐと判定した物は applied ではなく blocked として必ず表示する。
//
// 使い方:
//   node source/fix_colliders.js          … 何が変わるか見るだけ(書かない)
//   node source/fix_colliders.js --write  … 実際に書き込む
//
// ★同じ規則が gen_liminal.py の add_walk_colliders() にもある。片方だけ直さないこと。

const fs = require("fs");
const path = require("path");
const { load, reservedNames } = require("./lm_data.js");

const ROOT = path.resolve(__dirname, "..");
const SCENE = path.join(ROOT, "assets/scenes/stagedemo3.json");

// LM_Player の CharacterController と合わせる(radius .34 / halfHeight .56 / stepHeight .32)
const P_RADIUS = 0.34;
const P_HEIGHT = 1.80;   // 足元から頭まで
const P_STEP = 0.32;   // またげる高さ
const CLEAR = 0.28;   // 通り道の左右にこれだけ空いていないと「塞いだ」とみなす

// 飾りであって「物」ではないもの。名前は gen_liminal.py の作り手関数と対応する:
//   _mark/dud … mark() の印と嘘の印   lure … 囮の板   _exit/_exit_b … exit_sign()
//   _cl/_cr/_ct … door_casing() の枠飾り
const DECOR = /(_mark$|dud\d*$|lure|_exit(_b)?$|_c[lrt]$)/;
// glow() が作った発光板。テクスチャを持たず ReconnectInk シェーダーだけを持つ
const isGlow = (e) => !!e.shader && !e.materialTextureOverrides;

const aabb = (e) => {
  const [x, y, z] = e.transform.position;
  const [w, h, d] = e.transform.scale;
  return { x0: x - w / 2, x1: x + w / 2, y0: y - h / 2, y1: y + h / 2, z0: z - d / 2, z1: z + d / 2 };
};
const overlapXZ = (a, b, pad = 0) =>
  a.x0 < b.x1 + pad && a.x1 > b.x0 - pad && a.z0 < b.z1 + pad && a.z1 > b.z0 - pad;

function main() {
  const write = process.argv.includes("--write");
  const scene = JSON.parse(fs.readFileSync(SCENE, "utf8"));
  const reserved = reservedNames(load(ROOT).CONNS);
  const CHECKS = load(ROOT).CHECKS;

  // すでに当たり判定を持つ箱 = 立てる面の候補(床・階段・台)
  const floors = scene.entities.filter((e) => e.boxCollider && e.transform).map(aabb);

  const applied = [], blocked = [], skipped = { ceiling: 0, flat: 0, reserved: 0, nofloor: 0, decor: 0 };

  for (const e of scene.entities) {
    if (!e.primitive || e.boxCollider || !e.transform) continue;
    if (reserved.has(e.name)) { skipped.reserved++; continue; }
    if (isGlow(e) || DECOR.test(e.name)) { skipped.decor++; continue; }

    const b = aabb(e);

    // 真下で一番高い『立てる面』を探す。天井裏の物は床が見つかっても遠いので下で落ちる
    let floorY = null;
    for (const f of floors) {
      if (!overlapXZ(b, f)) continue;
      if (f.y1 > b.y1 - 0.02) continue;              // 自分より上の面は床ではない
      if (floorY === null || f.y1 > floorY) floorY = f.y1;
    }
    if (floorY === null) { skipped.nofloor++; continue; }

    const lo = b.y0 - floorY, hi = b.y1 - floorY;
    if (lo >= P_HEIGHT) { skipped.ceiling++; continue; }   // 頭より上 = 通れる
    if (hi <= P_STEP) { skipped.flat++; continue; }      // またげる = 踏んで歩ける

    // 通り道を塞がないか。到達点そのものと、到達点どうしを結ぶ線の上を見る
    let hits = null;
    for (let i = 0; i < CHECKS.length && !hits; i++) {
      const c = CHECKS[i];
      const seg = [[c.x, c.z]];
      if (i + 1 < CHECKS.length) {
        const n = CHECKS[i + 1];
        const steps = Math.ceil(Math.hypot(n.x - c.x, n.z - c.z) / 0.5);
        for (let t = 1; t <= steps; t++)
          seg.push([c.x + (n.x - c.x) * t / steps, c.z + (n.z - c.z) * t / steps]);
      }
      for (const [px, pz] of seg) {
        // その点に立つ体(半径 + 余裕)が箱と重なるか。高さも体の帯に掛かる時だけ
        const pad = P_RADIUS + CLEAR;
        if (px > b.x0 - pad && px < b.x1 + pad && pz > b.z0 - pad && pz < b.z1 + pad) {
          const fy = Math.abs(c.y - 0.9 - floorY) < 2.5;   // その到達点がこの床の上にあるか
          if (fy) { hits = { at: i + 1, x: +px.toFixed(2), z: +pz.toFixed(2) }; break; }
        }
      }
    }
    if (hits) { blocked.push({ name: e.name, hits, size: e.transform.scale }); continue; }

    // gen_liminal.py の box(solid=True) と同じ値
    e.boxCollider = { halfExtents: [0.5, 0.5, 0.5], offset: [0, 0, 0] };
    e.rigidBody = {
      motionType: 0, mass: 1, friction: 0.75, restitution: 0,
      useGravity: false, linearDamping: 0.02, angularDamping: 0.01,
    };
    applied.push({ name: e.name, lo: +lo.toFixed(2), hi: +hi.toFixed(2), size: e.transform.scale });
  }

  const roleOf = (n) => n.replace(/^[A-Za-z][A-Za-z0-9+-]*?_/, "").replace(/-?\d+(\.\d+)?/g, "#");
  const group = (list) => {
    const m = new Map();
    for (const a of list) { const r = roleOf(a.name); (m.get(r) || m.set(r, []).get(r)).push(a); }
    return [...m.entries()].sort((x, y) => y[1].length - x[1].length);
  };

  console.log(`== 当たり判定を足す ${applied.length} 個 ==`);
  for (const [r, xs] of group(applied))
    console.log(`  ${String(xs.length).padStart(3)}  ${r.padEnd(12)} 例 ${xs[0].name} (床上 ${xs[0].lo}〜${xs[0].hi}m, ${xs[0].size.map(v => +v.toFixed(2)).join("x")})`);

  console.log(`\n== 通り道を塞ぐので足さない ${blocked.length} 個 ==`);
  for (const [r, xs] of group(blocked))
    console.log(`  ${String(xs.length).padStart(3)}  ${r.padEnd(12)} 例 ${xs[0].name} (到達点 ${xs[0].hits.at} の上)`);

  console.log(`\n== 元から不要 == 天井 ${skipped.ceiling} / 床の模様・幅木 ${skipped.flat} / ` +
    `飾り・囮 ${skipped.decor} / 仕掛けの実体 ${skipped.reserved} / 床が無い ${skipped.nofloor}`);

  if (!write) { console.log("\n(--write を付けると実際に書き込む)"); return; }

  // ★JSON.stringify で書き直さない。gen_liminal.py(Python) は 0 を "0.0" と書くので、
  //   丸ごと書き直すとファイル全体が別物になり、53 個の追加が 3000 行の差分に埋もれる。
  //   元のテキストはそのままにして、対象の実体の閉じ括弧の直前へ 2 つのキーを差し込む。
  let text = fs.readFileSync(SCENE, "utf8");
  const names = new Set(applied.map((a) => a.name));
  let done = 0;

  for (const name of names) {
    const at = text.indexOf(`"name": "${name}",`);
    if (at < 0) throw new Error(`${name} が見つからない`);
    const open = text.lastIndexOf("{", at);          // この実体を開く括弧
    let depth = 0, close = -1;
    for (let i = open; i < text.length; i++) {
      const ch = text[i];
      if (ch === '"') { while (++i < text.length && (text[i] !== '"' || text[i - 1] === "\\")); continue; }
      if (ch === "{") depth++;
      else if (ch === "}" && --depth === 0) { close = i; break; }
    }
    if (close < 0) throw new Error(`${name} の閉じ括弧が見つからない`);

    // 直前のキーと同じ字下げに揃える(gen_liminal.py の indent=1 に合わせる)
    const lineStart = text.lastIndexOf("\n", close) + 1;
    const pad = text.slice(lineStart, close) + " ";
    const add =
      `,\n${pad}"boxCollider": {\n${pad} "halfExtents": [\n${pad}  0.5,\n${pad}  0.5,\n${pad}  0.5\n${pad} ],\n` +
      `${pad} "offset": [\n${pad}  0.0,\n${pad}  0.0,\n${pad}  0.0\n${pad} ]\n${pad}},\n` +
      `${pad}"rigidBody": {\n${pad} "motionType": 0,\n${pad} "mass": 1.0,\n${pad} "friction": 0.75,\n` +
      `${pad} "restitution": 0.0,\n${pad} "useGravity": false,\n${pad} "linearDamping": 0.02,\n` +
      `${pad} "angularDamping": 0.01\n${pad}}`;

    // 最後のキーの終わり(閉じ括弧の直前の非空白)へ差し込む
    let end = close - 1;
    while (end > open && /\s/.test(text[end])) end--;
    text = text.slice(0, end + 1) + add + text.slice(end + 1);
    done++;
  }

  JSON.parse(text);   // 壊していないことを書く前に確かめる
  fs.writeFileSync(SCENE, text, "utf8");
  console.log(`\nstagedemo3.json へ当たり判定を ${done} 個 差し込んだ(他の行は 1 文字も変えていない)`);
}

main();
