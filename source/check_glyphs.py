# -*- coding: utf-8 -*-
"""HUD の文字が ImGui のフォントに載っているかを確かめる。

★エンジンの ImGui は日本語フォントを GetGlyphRangesJapanese() で読み込む。
  この範囲は「ASCII + Latin-1 + CJK記号/かな + 半角全角形 + 常用漢字 + 人名用漢字」だけで、
  【矢印や記号(→ ★ ▸ ▶ — Ⅰ)は入っていない】。入っていない文字は無言で豆腐(?)になる。
  実際に objective の "▸" が "？" に化けた。

使い方:  python source/check_glyphs.py
  imgui_draw.cpp から本物の範囲表を読んで、Lua の文字列リテラルを全部照合する。
"""
import os, re, sys, glob

IMGUI = (r"C:\Users\ryuto\Documents\dx12\build\release\vcpkg_installed\vcpkg"
         r"\blds\imgui\src\.6-docking-0556b168f4.clean\imgui_draw.cpp")

BASE = [(0x0020, 0x00FF), (0x3000, 0x30FF), (0x31F0, 0x31FF),
        (0xFF00, 0xFFEF), (0xFFFD, 0xFFFD)]


def kanji_set(path):
    """accumulative_offsets_from_0x4E00 を読んで常用+人名用漢字の集合にする。"""
    src = open(path, encoding="utf-8", errors="replace").read()
    # ★同名のテーブルが GetGlyphRangesChineseSimplifiedCommon() にもあり、そちらが
    #   ファイル上で先に出てくる。素の find だと【簡体字の表】を掴んで、常用漢字まで
    #   「載っていない」と誤報する(実際に一度やった)。必ず日本語版の関数以降から探す。
    fn = src.find("GetGlyphRangesJapanese()")
    fn = src.find("GetGlyphRangesJapanese()", fn + 1)   # 宣言コメント行を飛ばして定義へ
    i = src.find("accumulative_offsets_from_0x4E00[]", fn if fn > 0 else 0)
    if i < 0:
        print("!! imgui_draw.cpp の漢字テーブルが見つからない:", path)
        return None
    body = src[src.index("{", i) + 1: src.index("};", i)]
    nums = [int(x) for x in re.findall(r"-?\d+", body)]
    cps, cur = set(), 0x4E00
    for n in nums:
        cur += n
        cps.add(cur)
    return cps


def main():
    if not os.path.exists(IMGUI):
        print("!! imgui_draw.cpp が無いので照合をスキップ:", IMGUI)
        return 0
    kanji = kanji_set(IMGUI)
    if kanji is None:
        return 1

    def ok(ch):
        c = ord(ch)
        if any(lo <= c <= hi for lo, hi in BASE):
            return True
        return c in kanji

    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    bad = {}
    for f in glob.glob(os.path.join(root, "assets", "components", "*.lua")):
        for ln, line in enumerate(open(f, encoding="utf-8"), 1):
            if line.lstrip().startswith("--"):
                continue                      # コメントは描画されない
            for lit in re.findall(r'"([^"\\]*)"', line):
                for ch in lit:
                    if not ok(ch):
                        bad.setdefault((ch, hex(ord(ch))), []).append(
                            "%s:%d" % (os.path.basename(f), ln))
    if not bad:
        print("OK: HUD の文字はすべてフォントに載っている")
        return 0
    print("豆腐になる文字が %d 種類:" % len(bad))
    for (ch, cp), where in sorted(bad.items()):
        print("  %r (%s)  <- %s" % (ch, cp, ", ".join(sorted(set(where))[:6])))
    return 1


if __name__ == "__main__":
    sys.exit(main())
