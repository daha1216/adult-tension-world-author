"""Self-test for the bundled checker: a good pack passes, broken ones fail.

    python tools/selftest.py
"""

import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(HERE, "adult-tension-world-author")
CHECK = os.path.join(SKILL, "scripts", "world_check.py")
EXAMPLE = os.path.join(SKILL, "references", "example_world.json")


def run(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, CHECK] + list(args), capture_output=True, text=True, encoding="utf-8", env=env)


def check_json(pack, tmp, name):
    path = os.path.join(tmp, name + ".json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(pack, handle, ensure_ascii=False, indent=2)
    result = run("check", path, "--json")
    return result.returncode, json.loads(result.stdout)


def main():
    failures = []
    with open(EXAMPLE, encoding="utf-8") as handle:
        good = json.load(handle)
    with tempfile.TemporaryDirectory() as tmp:
        code, out = check_json(good, tmp, "good")
        if code != 0:
            failures.append("example world should pass: %s" % out["problems"][:3])

        result = run("new", "selftest_world", "--title", "测试", "--era", "当代", "--region", "上海", "--out", tmp)
        if result.returncode != 0:
            failures.append("new failed: %s" % result.stdout)
        code = run("check", os.path.join(tmp, "selftest_world.json")).returncode
        if code != 1:
            failures.append("empty skeleton should fail, got %d" % code)

        any_template = next(t for t in good["character_templates"] if t["gender"] == "any")
        bad = copy.deepcopy(good)
        target = next(t for t in bad["character_templates"] if t["id"] == any_template["id"])
        target["public_role"] = "他是" + target["public_role"][:20]
        code, out = check_json(bad, tmp, "pronoun")
        if code != 1 or not any("他" in p["reason"] for p in out["problems"]):
            failures.append("hard-coded pronoun on an any-gender NPC should fail")

        bad = copy.deepcopy(good)
        bad["character_templates"][0]["age_range"] = [16, 30]
        code, out = check_json(bad, tmp, "minor")
        if code != 1:
            failures.append("an age below 18 should fail")

        bad = copy.deepcopy(good)
        keep = {c["power_structure"] for c in bad["cast_combos"]}.pop()
        bad["cast_combos"] = [c for c in bad["cast_combos"] if c["power_structure"] == keep]
        code, out = check_json(bad, tmp, "one_structure")
        if code != 1:
            failures.append("a world with one power structure should fail")
        bad = copy.deepcopy(good)
        for i, t in enumerate(bad["character_templates"]):
            if t["gender"] == "any":
                t["gender"] = "female"
                t["gender_reason"] = "测试第 %d 位：全部固定为女性，女性玩家应开不出局。" % i
        code, out = check_json(bad, tmp, "all_female")
        if code != 1 or not any(p["path"].endswith(":female") for p in out["problems"]):
            failures.append("all-female NPCs should leave female players without an opening")
    if failures:
        print("FAILED")
        for f in failures:
            print(" -", f)
        return 1
    print("selftest ok: example passes; skeleton, pronoun, under-18, single-structure and all-female packs fail")
    return 0


if __name__ == "__main__":
    sys.exit(main())
