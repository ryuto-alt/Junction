# -*- coding: utf-8 -*-
"""終盤の壁の落書き 9 枚を焼く。

    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" --background ^
        --factory-startup --python source/run_graffiti.py

★BlenderMCP から回す時は read_factory_settings を絶対に撃たないこと
  (アドオンごと登録解除されて接続が切れる)。MCP 経由なら execute_blender_code で

      exec(compile(open(r"...\\source\\run_graffiti.py", encoding="utf-8").read(),
                   "run_graffiti", "exec"))

  とするだけでよい。blender_kit.py は読み込まない(モデルを 1 つも作らないので不要)。
★現在開いている .blend には触らない。専用シーンを作って焼き、最後に消す。
"""
import os
import sys

# ★MCP から exec した時は __file__ が無い。JUNCTION_ROOT か既定の場所で拾う
_here = globals().get("__file__")
ROOT = (os.environ.get("JUNCTION_ROOT")
        or (os.path.dirname(os.path.dirname(os.path.abspath(_here))) if _here else None)
        or r"C:\Users\ryuto\Documents\dev\game\Junction")
ns = {"__name__": "jx_graffiti", "__file__": os.path.join(ROOT, "source", "blender_graffiti.py")}
src = ns["__file__"]
exec(compile(open(src, encoding="utf-8").read(), src, "exec"), ns)

only = None
if "--only" in sys.argv:
    only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
ns["build_graffiti"](ROOT, only=only)
print("RUN_GRAFFITI_OK", ROOT)
