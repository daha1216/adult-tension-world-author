# -*- coding: utf-8 -*-
"""Adult Tension world-pack checker (bundled with the world-author skill).

    python scripts/world_check.py new <id> --title 标题 --era 时代 --region 地域 [--out DIR]
    python scripts/world_check.py check <world.json> [--json] [--stats]

`new` writes a skeleton with every field present and every list empty.
`check` runs the same checks as the game engine on one world pack:
structure, limits, naming and gender rules, adult-only rules, references,
fixed-seed openings, openings for male and female players in both modes,
and the anti-collapse diversity gate (20 random openings per mode, 3 runs).
Exit code 0 means the pack is ready to hand over; 1 means problems were
found (all of them are listed at once); 2 means bad usage.

Only the Python standard library is needed (Python 3.10+).
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "engine")
sys.dont_write_bytecode = True
sys.path.insert(0, ENGINE)

from adult_tension.domain import opening, opening_checks, worldpack  # noqa: E402
from adult_tension.errors import AppError  # noqa: E402
from adult_tension.jsonio import decode_bytes, loads_strict  # noqa: E402

LIST_FIELDS = (
    "rules", "customs", "player_identities", "locations", "character_templates", "background_cast",
    "channels", "tension_engines", "cast_combos", "daily_activities", "pressures", "hooks", "twists",
    "forbidden_terms", "content_tags",
)
GATE_BASES = (1, 2, 3)
CHECK_NAMES = {
    "signatures": "不同开局数",
    "min_power_structure_share": "最少的权力结构占比",
    "identities": "出现过的玩家身份数",
    "approach_hook_share": "approach 钩子占比",
}


def tag_ids():
    with open(os.path.join(ENGINE, "tags.json"), encoding="utf-8") as handle:
        return {t["id"] for t in json.load(handle)["tags"]}


def skeleton(world_id, title, era, region):
    pack = {
        "schema_version": 1,
        "id": world_id,
        "title": title,
        "extends": None,
        "era": era,
        "region": region,
        "premise": "%s，%s。" % (era, region),
        "tone": ["日常"],
        "style_hint": "写%s的器物、声音与称呼，句子短，少写心理独白。" % era,
        "clock_start": {"label": None, "minute": 1200},
        "clock_style": "hm",
        "default_person": "second",
        "default_npc_gender_mix": {"female": 0.5, "male": 0.5, "nonbinary": 0.0},
        "stage_labels": None,
        "name_pools": {"family": [], "given_female": [], "given_male": [], "given_neutral": [], "nickname_patterns": []},
        "status": "draft",
        "notes": "",
    }
    for field in LIST_FIELDS:
        pack[field] = []
    return pack


def problem(where, reason, hint=None):
    return {"path": where, "reason": reason, "hint": hint}


def player_genders(pack):
    genders = set()
    for identity in pack["player_identities"]:
        g = identity.get("gender", "any")
        genders.update(("male", "female") if g == "any" else (g,))
    return sorted(genders & {"male", "female"})


def gender_openings(pack):
    """Every player gender the identities allow must open in every mode the world has."""
    problems = []
    for mode in ("daily", "pressure"):
        if not pack["daily_activities" if mode == "daily" else "pressures"]:
            continue
        for gender in player_genders(pack):
            conditions = opening.normalize_conditions(
                {"mode": mode, "locks": {"world_id": pack["id"]}, "player": {"gender": gender}}
            )
            tuples, reasons = opening.plan_candidates(pack, mode, conditions)
            if not tuples:
                problems.append(problem(
                    "opening:%s:%s" % (mode, gender),
                    "%s玩家在%s模式开不出局：%s" % ("男" if gender == "male" else "女",
                                              "日常" if mode == "daily" else "压力", "；".join(reasons)),
                    "给这种性别的玩家补能配上的人物组合、NPC（any 或相反性别）和钩子",
                ))
    return problems


def check(path, stats=False):
    if not os.path.isfile(path):
        return None, [problem("$", "文件不存在：%s" % path)]
    try:
        with open(path, "rb") as handle:
            raw = loads_strict(decode_bytes(handle.read(), path), path)
    except AppError as err:
        return None, [problem(d.get("path", "$"), d.get("reason", err.message), d.get("hint")) for d in (err.details or [])] or [
            problem("$", err.message)]
    if isinstance(raw, dict) and raw.get("extends"):
        return None, [problem("$.extends", "这个检查器不展开时代底包", "extends 写 null，把底包里需要的内容直接写进世界包")]
    pack, errs = worldpack.validate_world(raw, tag_ids=tag_ids())
    problems = [problem(e.get("path"), e.get("reason"), e.get("hint")) for e in errs]
    report = {"file": path, "world": raw.get("id") if isinstance(raw, dict) else None}
    if pack is None:
        return report, problems
    count, failures = opening_checks.fixed_seed_openings(pack)
    report["fixed_seed_openings"] = count
    for failure in failures:
        problems.append(problem("opening:%s:seed%d" % (failure["mode"], failure["seed"]),
                                "；".join(failure["problems"][:3]), "修内容（钩子地点、组合、身份）"))
    problems.extend(gender_openings(pack))
    runs = []
    for mode in ("daily", "pressure"):
        if not pack["daily_activities" if mode == "daily" else "pressures"]:
            continue
        for base in GATE_BASES:
            try:
                item = opening_checks.diversity(pack, mode, base)
            except AppError as err:
                problems.append(problem("diversity:%s:base%d" % (mode, base), err.message))
                continue
            runs.append(item)
            if not item["pass"]:
                failed = [k for k, c in item["checks"].items() if not c["pass"]]
                problems.append(problem(
                    "diversity:%s:base%d" % (mode, base),
                    "开局多样性不达标：%s" % "、".join(
                        "%s=%s（要 %s）" % (CHECK_NAMES.get(k, k), item["checks"][k]["value"], item["checks"][k]["need"]) for k in failed),
                    "增加对应的内容（组合、活动/压力、钩子、身份），不要删检查",
                ))
    report["diversity"] = [{"mode": r["mode"], "base": r["base"], "pass": r["pass"],
                            "power_structures": r["power_structures"], "identities": len(r["identities"]),
                            "hook_kinds": r["hook_kinds"]} for r in runs]
    if stats:
        report["stats"] = worldpack.world_stats(pack)
    return report, problems


def cmd_new(args):
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,39}", args.id):
        print("世界 id 只能用小写字母、数字和下划线，以字母开头，不超过 40 个字符：%s" % args.id)
        return 2
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, args.id + ".json")
    if os.path.exists(path) and not args.force:
        print("文件已存在：%s（要覆盖请加 --force）" % path)
        return 2
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(skeleton(args.id, args.title, args.era, args.region), ensure_ascii=False, indent=2) + "\n")
    print("已生成骨架：%s" % path)
    print("下一步：python %s check %s" % (os.path.relpath(os.path.abspath(__file__)), path))
    return 0


def cmd_check(args):
    report, problems = check(args.file, args.stats)
    if args.json:
        print(json.dumps({"ok": not problems, "problems": problems, "report": report}, ensure_ascii=False, indent=2))
        return 0 if not problems else 1
    if not problems:
        print("通过：%s 没有发现问题。" % args.file)
        if report and report.get("diversity"):
            for r in report["diversity"]:
                print("  %s 第 %d 组：权力结构 %s，玩家身份 %d 种，钩子 %s" % (
                    "日常" if r["mode"] == "daily" else "压力", r["base"], r["power_structures"], r["identities"], r["hook_kinds"]))
        if args.stats and report.get("stats"):
            print(json.dumps(report["stats"], ensure_ascii=False, indent=2))
        return 0
    print("发现 %d 处问题（一次列全，逐条改完再跑）：" % len(problems))
    for i, p in enumerate(problems, 1):
        line = "%d. [%s] %s" % (i, p["path"], p["reason"])
        if p.get("hint"):
            line += " —— %s" % p["hint"]
        print(line)
    return 1


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Adult Tension 世界包检查器")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_new = sub.add_parser("new", help="生成空骨架")
    p_new.add_argument("id")
    p_new.add_argument("--title", required=True)
    p_new.add_argument("--era", required=True)
    p_new.add_argument("--region", required=True)
    p_new.add_argument("--out", default=".")
    p_new.add_argument("--force", action="store_true")
    p_check = sub.add_parser("check", help="检查一个世界包")
    p_check.add_argument("file")
    p_check.add_argument("--json", action="store_true")
    p_check.add_argument("--stats", action="store_true")
    args = parser.parse_args(argv)
    return cmd_new(args) if args.cmd == "new" else cmd_check(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
