"""`guide`: the play guide for a new player ("怎么玩"), fixed text the model
relays as it is. Plain words only: no NPC, turn, command or field names."""

from .. import schema as S
from ..errors import INVALID_INPUT, AppError
from ..persistence import repo
from . import specs

TITLE = "怎么玩"
EXAMPLE = "· 直接打字，写你做什么、说什么。例如：我把伞递过去：“雨还大，一起走吧。”"

WHAT = [
    "【这是什么】",
    "一个由你当主角的互动故事。你打字说你做什么、说什么，AI 接着把故事写下去。",
    "故事里的其他人有自己的脾气和想法，会答应你，也会拒绝你。",
]
START = [
    "【第一步：开一局】",
    "· 说“开局”，再选一种：",
    "  日常：平平常常的一天，慢慢和人相处。",
    "  压力：一上来就有麻烦，要你想办法。",
    "  不想选就说“随便”。",
    "· 想自己挑故事：先说“世界列表”看看有哪些，也可以直接说“开局 民国”“开局 宫廷”。",
    "· 不想遇到天灾险情：说“开局 轻松点”。",
]
AGAIN = "· 说“继续上次”：接着玩上次没玩完的故事。"
FIRST_STEPS = [
    "【第二步：开始玩】",
    EXAMPLE,
    "· 只写你自己的事，别人怎么反应交给故事。",
    "· 想不出来就说“继续”，故事会自己往下走一点。",
]
HOW = [
    "【怎么玩】",
    EXAMPLE,
    "· 写得越具体，故事越照你的意思走。",
    "· 你只决定你自己。别人会答应，也会拒绝；想走近一点，就像现实里一样慢慢来。",
    "· 想不出来就说“继续”，故事会自己往下走一点。",
]
ANYTIME = [
    "【随时能说】",
    "· 存档 / 读档：保存进度，或回到存过的进度",
    "· 撤销：刚才那步不算，重来",
]
COMMON = [
    "【常用的话】",
    "· 状态：看看现在几点、在哪、和谁关系怎么样",
    "· 存档 / 读档：保存进度，或回到存过的进度",
    "· 撤销：刚才那步不算，重来",
    "· 快进到明早：跳过一段时间",
    "· 来点转折：让故事出点意外",
    "· 内心可见：看到别人心里没说出口的话",
    "· 节奏 慢热 / 直接，尺度 含蓄 / 直白：换个写法",
]
SAFETY = [
    "【不舒服的时候】",
    "· 暂停：马上停下",
    "· 换个场景：离开眼前这一幕",
    "· 边界：不要 ××：以后都不会写 ××",
]
MORE = "想看所有能说的话，说“帮助”。"


def lines_before_playing(has_played):
    start = START + ([AGAIN] if has_played else [])
    return WHAT + [""] + start + [""] + FIRST_STEPS + [""] + ANYTIME + [""] + SAFETY + ["", MORE]


def lines_while_playing(world_title):
    return ["你正在玩：《%s》。" % world_title, ""] + HOW + [""] + COMMON + [""] + SAFETY + ["", MORE]


def run(ctx, payload):
    payload, errors = S.validate(specs.GUIDE, payload or {})
    if errors:
        raise AppError(INVALID_INPUT, "输入有 %d 处问题" % len(errors) if len(errors) > 1 else errors[0]["reason"], errors)
    conn = ctx.db()
    if payload["session_id"]:
        session = repo.session_summary(conn, payload["session_id"])
        out = {"stage": "playing", "session_id": payload["session_id"], "world_title": session["world_title"]}
        lines = lines_while_playing(session["world_title"])
    else:
        out = {"stage": "start"}
        lines = lines_before_playing(repo.has_sessions(conn))
    out.update({"title": TITLE, "lines": lines, "text": "\n".join([TITLE, ""] + lines)})
    return out
