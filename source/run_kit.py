# -*- coding: utf-8 -*-
"""gen/manifest.json のモデルを Blender で書き出す。★BlenderMCP が落ちていても回る道。

    "C:\\Blender\\blender-5.1.2-windows-x64\\blender.exe" --background --factory-startup ^
        --python source/run_kit.py

★blender_kit.py の ROOT は「実在する方を選ぶ」書き方なので、開発者ごとに違う。
  ここから JX_ROOT を渡さないと StopIteration で落ちる。環境変数 JUNCTION_ROOT で上書きできる。
★JX_MANIFEST_ONLY=True にすると build_all/build_rooms 等の作り置きを飛ばし、
  扉板と gen/manifest.json のモデル(壁・床・天井・廊下)だけを出す。
"""
import os

ROOT = os.environ.get("JUNCTION_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(ROOT, "source", "blender_kit.py")
exec(compile(open(src, encoding="utf-8").read(), src, "exec"),
     {"JX_MANIFEST_ONLY": True, "JX_ROOT": ROOT, "__name__": "jx_kit"})
print("RUN_KIT_OK", ROOT)
