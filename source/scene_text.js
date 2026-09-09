// シーン JSON を【テキストのまま】編集するための道具。
//
// ★なぜ JSON.parse -> stringify で書き戻さないか:
//   シーンは gen_liminal.py(Python) が json.dumps(indent=1) で書いている。Python は
//   0 を "0.0" と書き、Node の JSON.stringify は "0" と書く。丸ごと書き直すと
//   【全 65000 行が別物になり】、実際の変更が差分の中に埋もれて誰にも読めなくなる。
//   そこで元のテキストには一切触れず、必要な所だけ切り貼りする。

const ENTITY_INDENT = "  ";     // entities 配列の要素({)の字下げ
const KEY_INDENT = "   ";       // その中のキーの字下げ

// 文字列リテラルを飛ばしながら、open の { に対応する } の位置を返す
function matchBrace(text, open) {
  let depth = 0;
  for (let i = open; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') { while (++i < text.length && (text[i] !== '"' || text[i - 1] === "\\")); continue; }
    if (ch === "{") depth++;
    else if (ch === "}" && --depth === 0) return i;
  }
  return -1;
}

// 名前で実体の {...} の範囲を返す。無ければ null
function entitySpan(text, name) {
  const at = text.indexOf(`"name": "${name}",`);
  if (at < 0) return null;
  const open = text.lastIndexOf("{", at);
  const close = matchBrace(text, open);
  if (close < 0) throw new Error(`${name} の閉じ括弧が見つからない`);
  return { open, close };
}

// 実体の最後のキーの直後(閉じ括弧の直前の非空白)へ text を差し込む
function appendKeys(text, name, block) {
  const span = entitySpan(text, name);
  if (!span) throw new Error(`${name} が見つからない`);
  let end = span.close - 1;
  while (end > span.open && /\s/.test(text[end])) end--;
  return text.slice(0, end + 1) + block + text.slice(end + 1);
}

// 名前の合う実体を、前後のカンマごと取り除く
function removeEntity(text, name) {
  const span = entitySpan(text, name);
  if (!span) return text;
  let a = span.open, b = span.close + 1;
  // 「,\n  {…}」の形なら手前のカンマから、先頭の要素なら後ろのカンマまで消す
  let p = a - 1;
  while (p >= 0 && /\s/.test(text[p])) p--;
  if (text[p] === ",") a = p;
  else { let q = b; while (q < text.length && /\s/.test(text[q])) q++; if (text[q] === ",") b = q + 1; }
  return text.slice(0, a) + text.slice(b);
}

// entities 配列の末尾へ実体を足す
function appendEntities(text, entities) {
  const key = '"entities": [';
  const at = text.indexOf(key);
  if (at < 0) throw new Error("entities 配列が見つからない");
  // 配列の閉じ ] を探す(入れ子の [ ] と文字列を飛ばす)
  let depth = 0, close = -1;
  for (let i = at + key.length - 1; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') { while (++i < text.length && (text[i] !== '"' || text[i - 1] === "\\")); continue; }
    if (ch === "[") depth++;
    else if (ch === "]" && --depth === 0) { close = i; break; }
  }
  if (close < 0) throw new Error("entities 配列の閉じ括弧が見つからない");

  let end = close - 1;
  while (end > at && /\s/.test(text[end])) end--;
  const body = entities.map((e) => indent(JSON.stringify(e, null, 1))).join(",\n");
  return text.slice(0, end + 1) + ",\n" + body + "\n" + ENTITY_INDENT + text.slice(close);
}

// JSON.stringify(indent 1) の結果を、シーンの字下げ(要素が 2 スペース)へ寄せる
function indent(s) {
  return s.split("\n").map((line, i) => (i === 0 ? ENTITY_INDENT + line : ENTITY_INDENT + line)).join("\n");
}

module.exports = { entitySpan, appendKeys, removeEntity, appendEntities, matchBrace, KEY_INDENT };
