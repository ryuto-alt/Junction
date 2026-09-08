# -*- coding: utf-8 -*-
"""第三幕「立坑」のモデルを書き出す。

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background ^
        --factory-startup --python source/run_shaft.py

★BlenderMCP から回す時は read_factory_settings を絶対に撃たないこと
  (アドオンごと登録解除されて接続が切れる。実際に切った)。
  MCP 経由なら execute_blender_code で下の 3 行だけを実行する。
"""
import os

ROOT = os.environ.get("JUNCTION_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ns = {"JX_MANIFEST_ONLY": True, "JX_ROOT": ROOT, "JX_SKIP_BUILD": True, "__name__": "jx_kit"}
src = os.path.join(ROOT, "source", "blender_kit.py")
exec(compile(open(src, encoding="utf-8").read(), src, "exec"), ns)

sh = os.path.join(ROOT, "source", "blender_shaft.py")
exec(compile(open(sh, encoding="utf-8").read(), sh, "exec"), ns)
ns["build_shaft"]()
print("RUN_SHAFT_OK", ROOT)
