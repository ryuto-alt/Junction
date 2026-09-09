# -*- coding: utf-8 -*-
"""第1幕の案内板の額縁を書き出す。

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background ^
        --factory-startup --python source/run_signs.py

★BlenderMCP から回す時は read_factory_settings を絶対に撃たないこと
  (アドオンごと登録解除されて接続が切れる)。MCP 経由なら execute_blender_code で
  このファイルを exec するだけでよい。
★run_shaft.py と同じ作り。blender_kit.py は【道具だけ】読み込む(JX_SKIP_BUILD)ので、
  触っていないモデルが焼き直されて差分が出ることはない。
"""
import os

ROOT = os.environ.get("JUNCTION_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ns = {"JX_MANIFEST_ONLY": True, "JX_ROOT": ROOT, "JX_SKIP_BUILD": True, "__name__": "jx_kit"}
src = os.path.join(ROOT, "source", "blender_kit.py")
exec(compile(open(src, encoding="utf-8").read(), src, "exec"), ns)

sg = os.path.join(ROOT, "source", "blender_signs.py")
exec(compile(open(sg, encoding="utf-8").read(), sg, "exec"), ns)
ns["build_signs"]()
print("RUN_SIGNS_OK", ROOT)
