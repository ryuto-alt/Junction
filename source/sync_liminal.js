// source/liminal_runtime.lua の変更を assets/components/Liminal.lua へ反映する。
//
// ★なぜこれがあるか:
//   本来この差し込みは gen_liminal.py がやる。だが gen_liminal.py はシーン(stagedemo3.json)
//   まで丸ごと作り直すので Blender 由来の重い依存が要り、Python の無い環境では走らない。
//   ここでは gen_liminal.py と【同じ切り貼り】だけを行う:
//     出力 = liminal_runtime.lua の >>>DATA より前
//          + 既存 Liminal.lua の >>>DATA 〜 <<<DATA (自動生成データはそのまま持ち越す)
//          + liminal_runtime.lua の <<<DATA より後
//   つまり CONNS/CHECKS/GOAL は一切触らず、ランタイム側のコードだけを差し替える。
//   データも作り直したい時は Python を入れて gen_liminal.py を回すこと。
//
// 使い方: node source/sync_liminal.js

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const RUNTIME = path.join(ROOT, "source/liminal_runtime.lua");
const OUT = path.join(ROOT, "assets/components/Liminal.lua");

const BEGIN = "-- >>>DATA";
const END = "-- <<<DATA\n";

function slice(text, what) {
  const a = text.indexOf(BEGIN);
  const b = text.indexOf("-- <<<DATA");
  if (a < 0 || b < 0) throw new Error(`${what}: DATA の目印が見つからない`);
  return { head: text.slice(0, a), data: text.slice(a, b + END.length), tail: text.slice(b + END.length) };
}

const runtime = slice(fs.readFileSync(RUNTIME, "utf8"), "liminal_runtime.lua");
const current = slice(fs.readFileSync(OUT, "utf8"), "Liminal.lua");

const out = runtime.head + current.data + runtime.tail;
fs.writeFileSync(OUT, out, "utf8");

const lines = (s) => s.split("\n").length;
console.log(`Liminal.lua を更新した: ${lines(out)} 行 ` +
            `(ランタイム ${lines(runtime.head) + lines(runtime.tail) - 1} 行 + 自動生成データ ${lines(current.data) - 1} 行)`);
