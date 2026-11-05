# 客户端与运行能力

技能正文使用标准Agent Skills name/description元数据，WorkBuddy字段只在构建专用ZIP时注入。版本统一来自包内VERSION。规范参考： https://agentskills.io/specification 与 https://open.workbuddy.cn/docs/skill ，2026-11-05核对。

| 客户端 | 安装参数 | 项目技能根目录 | 当前实测 |
| --- | --- | --- | --- |
| Codex | codex | .agents/skills | 安装器与独立脚本验证；本Skill尚未实测客户端任务 |
| Claude Code | claude | .claude/skills | 安装器验证；未实测客户端 |
| Cursor | cursor | .cursor/skills | 安装器验证；未实测客户端 |
| Copilot | copilot | .github/skills | 安装器验证；未实测客户端 |
| Gemini CLI | gemini | .gemini/skills | 安装器验证；未实测客户端 |
| OpenCode | opencode | .opencode/skills | 安装器验证；未实测客户端 |
| 共享/其他 | generic/--dest | .agents/skills或显式指定 | 需宿主读取SKILL.md和资源 |
| WorkBuddy | 专用ZIP上传 | 客户端管理 | 本版客户端验证见evidence/0.1.0/verification.md |

用户范围路径由安装器按客户端生成，使用--dry-run检查；自定义--dest填写技能根目录。--replace先备份，--work-dir可指定技能目录外的可写临时/备份位置。不修改客户端全局规则和账号设置。

完整流程需要图片理解、Python执行、文件读写和Pillow。Word及PDF能力分别检测；宿主不具备相应能力时，必须按SKILL.md说明降级范围。格式适配和目录安装通过不等于所有客户端均实测。
