"""Refresh the bundled engine copy inside the skill from an Adult Tension checkout.

    python tools/sync_from_engine.py <path-to-adult-tension-v2>

Copies the runtime package (validation and opening code) and the content tag
table into adult-tension-world-author/scripts/engine/, regenerates
references/fields.md from the engine's schema, copies the example world, and
records the source commit and content version in scripts/engine/SOURCE.txt.
Run it whenever the engine's world-pack rules change, then run
tools/selftest.py.
"""

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(HERE, "adult-tension-world-author")
ENGINE = os.path.join(SKILL, "scripts", "engine")
EXAMPLE_WORLD = "harbor_night_shift"


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    src = os.path.abspath(argv[0])
    runtime = os.path.join(src, "skill", "adult-tension", "runtime", "adult_tension")
    if not os.path.isdir(runtime):
        print("找不到引擎运行时：%s" % runtime)
        return 2
    sys.dont_write_bytecode = True
    target = os.path.join(ENGINE, "adult_tension")
    if os.path.isdir(target):
        shutil.rmtree(target)
    shutil.copytree(runtime, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(os.path.join(src, "skill", "adult-tension", "content", "tags.json"), os.path.join(ENGINE, "tags.json"))
    shutil.copy2(
        os.path.join(src, "content-src", "worlds", EXAMPLE_WORLD + ".json"),
        os.path.join(SKILL, "references", "example_world.json"),
    )

    sys.path.insert(0, os.path.join(src, "tools"))
    import _runtime  # noqa: E402

    _runtime.use_runtime()
    import gen_references  # noqa: E402  (the engine's own reference generator)

    text = gen_references.render_custom_world()
    fields = text[text.index("## 字段"): text.index("## 示例")].rstrip() + "\n"
    head = (
        "<!-- 本文件由 tools/sync_from_engine.py 从引擎的世界包 schema 生成，不要手改。 -->\n\n"
        "# 世界包字段表\n\n"
        "引擎世界包的全部字段、类型、上限与说明。正式世界包：`custom` 不写（或写 false），`extends` 写 null，"
        "`status` 先写 `draft`。数量下限以 guide.md 第 2 节为准（下表的“自定义世界”下限更低，不适用）。\n\n"
    )
    with open(os.path.join(SKILL, "references", "fields.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(head + fields.replace("## 字段", "## 字段", 1))

    commit = subprocess.run(["git", "-C", src, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    import json

    with open(os.path.join(src, "content-src", "content.json"), encoding="utf-8") as handle:
        version = json.load(handle)["content_version"]
    with open(os.path.join(ENGINE, "SOURCE.txt"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("engine commit: %s\ncontent version: %s\n" % (commit or "unknown", version))
    print("synced from %s (commit %s, content %s)" % (src, commit, version))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
