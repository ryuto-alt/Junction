// assets/components/Liminal.lua の >>>DATA ブロック(CONNS / CHECKS / GOAL)を読む。
//
// gen_liminal.py が書き出す Lua テーブルリテラルだけを相手にする小さな読み取り器。
// 扱う値は 数値 / 真偽 / 文字列 / 配列 / key=value テーブル のみ(式も関数も出てこない)。
// Python が無い環境から当たり判定や部屋一覧を調べるために使う。

const fs = require("fs");
const path = require("path");

function parseLuaValue(src, i) {
  const ws = () => { while (i < src.length && /[\s]/.test(src[i])) i++; };
  ws();
  const c = src[i];

  if (c === "{") {
    i++;
    const arr = [];
    const obj = {};
    let isObj = false;
    for (;;) {
      ws();
      if (src[i] === "}") { i++; break; }
      // key=value か、並びの値か
      const m = /^([A-Za-z_][A-Za-z0-9_]*)\s*=/.exec(src.slice(i));
      if (m) {
        i += m[0].length;
        const r = parseLuaValue(src, i);
        obj[m[1]] = r.value; i = r.i; isObj = true;
      } else {
        const r = parseLuaValue(src, i);
        arr.push(r.value); i = r.i;
      }
      ws();
      if (src[i] === "," || src[i] === ";") i++;
    }
    return { value: isObj ? obj : arr, i };
  }
  if (c === '"' || c === "'") {
    const q = c; i++;
    let out = "";
    while (i < src.length && src[i] !== q) {
      if (src[i] === "\\") { out += src[i + 1]; i += 2; } else out += src[i++];
    }
    i++;
    return { value: out, i };
  }
  if (src.startsWith("true", i)) return { value: true, i: i + 4 };
  if (src.startsWith("false", i)) return { value: false, i: i + 5 };
  if (src.startsWith("nil", i)) return { value: null, i: i + 3 };

  const m = /^-?\d+(\.\d+)?([eE][-+]?\d+)?/.exec(src.slice(i));
  if (!m) throw new Error("読めない値: " + JSON.stringify(src.slice(i, i + 40)));
  return { value: parseFloat(m[0]), i: i + m[0].length };
}

function readAssign(src, name) {
  const key = "\n" + name + " = ";
  const a = src.indexOf(key);
  if (a < 0) throw new Error(name + " が見つからない");
  return parseLuaValue(src, a + key.length).value;
}

function load(root) {
  root = root || path.resolve(__dirname, "..");
  const src = fs.readFileSync(path.join(root, "assets/components/Liminal.lua"), "utf8");
  const data = src.slice(src.indexOf("-- >>>DATA"), src.indexOf("-- <<<DATA"));
  return {
    CONNS: readAssign(data, "CONNS"),
    CHECKS: readAssign(data, "CHECKS"),
    GOAL: readAssign(data, "GOAL"),
  };
}

// 継ぎ目の仕掛けが掴んでいる実体の名前。★この集合には当たり判定を足してはいけない
// (破片は焦点から見た時だけ形になる幻で、動く。出現物・可動物・丁番も同様)。
function reservedNames(CONNS) {
  const s = new Set();
  const add = (n) => { if (typeof n === "string") s.add(n); };
  for (const c of CONNS) {
    for (const sh of c.shards || []) for (const e of sh.ents || []) add(e.n);
    for (const x of c.solids || []) add(x.n || x);
    for (const x of c.movers || []) add(x.n || x);
    for (const x of c.hinges || []) add(x.n || x.ent || x);
    for (const x of c.glows || []) add(x);
    for (const x of c.lights || []) add(x.n || x);
    for (const x of c.shines || []) add(x.n || x);
    for (const x of c.hides || []) add(x.n || x);
    for (const x of c.darkLights || []) { add(x); add(x + "_l"); add(x + "_p"); }
    if (c.slot && c.slot.ent) add(c.slot.ent);
    if (c.relay && c.relay.weight) add(c.relay.weight);
    if (c.trail) for (const t of c.trail) if (t && t.n) add(t.n);
  }
  return s;
}

module.exports = { load, reservedNames, parseLuaValue, readAssign };

if (require.main === module) {
  const d = load();
  console.log(`CONNS=${d.CONNS.length}  CHECKS=${d.CHECKS.length}  GOAL=${JSON.stringify(d.GOAL)}`);
  console.log(`仕掛けが掴んでいる実体 = ${reservedNames(d.CONNS).size} 個`);
}
