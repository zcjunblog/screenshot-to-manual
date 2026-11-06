# 参与贡献

感谢你帮助完善截图转操作手册。欢迎反馈使用问题、改进文档与模板，以及提交可复现的修复。

## 提交问题

请先搜索已有Issue，提供技能版本、操作系统、Agent客户端、Python与文档依赖版本、复现步骤、预期与实际结果。图片或文件只使用虚构演示、已获授权且充分脱敏的资料；不要提交真实客户原文、个人信息、账号、密钥或完整内部工作目录。

## 本地验证

```bash
git clone https://github.com/zcjunblog/screenshot-to-manual.git
cd screenshot-to-manual
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/screenshot-to-manual/requirements.txt -r skills/screenshot-to-manual/requirements-optional.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/smoke_archive.py
```

Windows将解释器路径换成`.venv\Scripts\python.exe`。归档验证使用仓库中已登记的版本和虚构资料；PDF版式验证还需可用的LibreOffice与中文字体。涉及导出版式的修改，请提供样张并逐页检查实际效果。

## 提交修改

从独立分支提交PR，说明具体问题、修改后的行为和实际验证范围。保留已有来源与原图，维持草稿/待确认语义、原始输入只读、独立版本输出和依赖缺失时的明确反馈；不要为通过校验修改来源。

技能正文位于`skills/screenshot-to-manual/`，WorkBuddy展示字段位于`distribution/workbuddy.json`。构建命令为`python3 tools/build_release.py`；开发时可用`--out outputs/release-preview`检查候选包。不要直接覆盖已登记、已提审或已发布归档；版本及正式包由维护者统一处理。

面向用户的发布概述写清适用场景、功能、操作流程、交付结果与必要使用条件。自动测试、CI和内部验收信息放在验证报告中；兼容性限制如实说明。

贡献按仓库[MIT许可证](LICENSE)分发。请确保新增资料与图片有权按该许可证公开，第三方依赖仍遵循各自许可证。
