# Adult Tension 世界包写作 Skill

一个通用的 Agent Skill：让 AI 按写作指南为 Adult Tension 写新的世界包 JSON，并用自带的检查器跑和游戏引擎相同的校验，直到通过。

只用 Python 3.10+ 标准库，不依赖 Adult Tension 项目本身，任何支持 Agent Skills（`SKILL.md` 格式）的宿主都能用。

## 目录

```
adult-tension-world-author/      ← Skill 本体，整个目录装进宿主
  SKILL.md                       ← 给 AI 的工作流程
  references/guide.md            ← 写作指南（由世界包填写模板生成）
  references/fields.md           ← 字段表（由引擎 schema 生成）
  references/example_world.json  ← 完整示例世界
  scripts/world_check.py         ← 检查器：new 生成骨架，check 检查
  scripts/engine/                ← 引擎校验代码的副本（SOURCE.txt 记着来源版本）
tools/                           ← 维护用，不用装
  sync_from_engine.py            ← 从 Adult Tension 仓库更新引擎副本、字段表和示例
  make_guide.py                  ← 从填写模板重新生成 guide.md
  selftest.py                    ← 自测：示例通过、各种坏包被拦下
```

## 安装

把 `adult-tension-world-author/` 整个目录复制到宿主的 Skill 目录，目录名保持不变：

- Claude Code：项目级 `<项目>/.claude/skills/adult-tension-world-author/`，或用户级 `~/.claude/skills/adult-tension-world-author/`
- Claude.ai / Claude 桌面版：把该目录打成 zip，在设置的 Skills（技能）里上传
- 其他宿主：放进它的 Skill 目录（见宿主文档）；不支持 Skill 的宿主，可以把 `SKILL.md` 的正文当提示词，再让它读 `references/` 里的文件

然后对 AI 说“写一个新的 Adult Tension 世界：……”即可。

## 手动用检查器

```bash
python adult-tension-world-author/scripts/world_check.py new my_world --title 标题 --era 时代 --region 地方 --out .
python adult-tension-world-author/scripts/world_check.py check my_world.json
```

## 维护

引擎的世界包规则变了之后：

```bash
python tools/sync_from_engine.py <adult-tension-v2 仓库路径>
python tools/selftest.py
```

填写模板改了之后：

```bash
python tools/make_guide.py <世界包填写模板.md>
```

检查器查得出结构、字数、称呼、性别、成年、引用、开局与多样性问题；查不出内容红线（交换、胁迫、神志不清时的亲密等），也查不出与其他世界的跨世界重复——后者在世界包放进 Adult Tension 项目编译时才查。
