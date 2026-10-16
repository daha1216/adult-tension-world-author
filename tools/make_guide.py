"""Build references/guide.md from the user's fill-in template.

    python tools/make_guide.py <世界包填写模板.md>

The template is written for a person who fills it in and hands it over; the
guide keeps every rule but speaks to the AI that writes the JSON itself, and
names the JSON field behind each section. Re-run after the template changes.
"""

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "adult-tension-world-author", "references", "guide.md")

HEAD = """# 世界包写作指南

写 Adult Tension 世界包时逐节对照本文。第 0 节是红线和最常返工的地方，第 1–16 节按世界包 JSON 的顺序写，每节标题后面是对应的 JSON 字段；字段的类型和上限见 `fields.md`，完整的样子见 `example_world.json`。
写完用 `scripts/world_check.py check` 检查，问题一次列全，逐条改到通过。

"""

SECTION_FIELDS = {
    "## 1. 基本信息": "（`id` `title` `era` `region` `premise` `tone` `style_hint` `clock_start` `clock_style` `name_pools.order` `default_person` `default_npc_gender_mix` `content_tags` `forbidden_terms`）",
    "## 2. 关系阶段名": "（`stage_labels`）",
    "## 3. 名字池": "（`name_pools`）",
    "## 4. 世界规则": "（`rules` `customs`）",
    "## 5. 玩家身份": "（`player_identities`）",
    "## 6. 地点": "（`locations`）",
    "## 7. NPC 模板": "（`character_templates`）",
    "## 8. 背景人物": "（`background_cast`）",
    "## 9. 传话渠道": "（`channels`）",
    "## 10. 张力引擎": "（`tension_engines`）",
    "## 11. 人物组合": "（`cast_combos`）",
    "## 12. 日常活动": "（`daily_activities`）",
    "## 13. 压力事件": "（`pressures`）",
    "## 14. 开场钩子": "（`hooks`）",
    "## 15. 转折": "（`twists`）",
    "## 16. 备注": "（`notes`）",
}

REPLACE = [
    ("按顺序填完下面的内容，交给 Claude 转成 JSON 就行。\n", ""),
    ("写之前先看第 0 节的硬性红线，再看第 0.3 节的“两人开局”：新世界每一局开场都只有两个人，一男一女。\n",
     "写之前先看第 0 节的硬性红线，再看第 0.3 节的“两人开局”：新世界每一局开场都只有两个人，一男一女。\n"),
    ("**三、开局检查（转 JSON 后跑，不过就要补内容）**", "**三、开局检查（`world_check.py check` 会跑，不过就要补内容）**"),
    ("明确放行20~22岁成年青年女性特有的健康婴儿肥与紧致胶原蛋白面部反差（用户最新明确指令最高优先级），", ""),
    ("（注：20~22岁成年女性特有的健康婴儿肥反差描写已明确放行）", ""),
    ("由我审稿时把关", "检查器查不出来，写的时候自己把关，交稿前逐条自查"),
]


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    text = open(argv[0], encoding="utf-8").read().replace("\r\n", "\n")
    lines = text.split("\n")
    # drop the template's own title and dated update note
    body = "\n".join(l for l in lines[1:] if not l.startswith("（20") or "更新" not in l)
    for old, new in REPLACE:
        body = body.replace(old, new)
    out = []
    for line in body.split("\n"):
        for prefix, fields in SECTION_FIELDS.items():
            if line.startswith(prefix):
                line = line + " " + fields
                break
        out.append(line)
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(HEAD + "\n".join(out).lstrip("\n"))
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
