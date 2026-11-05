# 运行指南

## 环境

Python3.9+；Pillow9.2+负责读取和派生图片，缺少时先用宿主已有可用解释器。可在用户任务目录创建虚拟环境安装requirements.txt，不修改全局环境；不能安装时交付未处理图片的文字草稿并说明限制，不能假称已脱敏。

可选python-docx1.1+生成Word。PDF通过LibreOffice将Word转换；系统已有libreoffice/soffice或macOS标准安装可自动发现，也可通过--soffice显式指定程序。不预设开发机缓存路径。Word缺失时Markdown和图片仍可导出；PDF缺失不妨碍Word交付。CLI不会自动安装依赖或联网。

```bash
python3 "<技能目录>/scripts/manual_tool.py" doctor
python3 "<技能目录>/scripts/manual_tool.py" ingest "<输入>/1.png" "<输入>/2.jpg" --notes "<任务>/说明.txt" --out "<任务>/来源.json"
python3 "<技能目录>/scripts/manual_tool.py" validate --model "<任务>/步骤.json" --sources "<任务>/来源.json"
python3 "<技能目录>/scripts/manual_tool.py" templates
python3 "<技能目录>/scripts/manual_tool.py" render --model "<任务>/步骤.json" --sources "<任务>/来源.json" --out "<任务>/交付" --template office --word auto --pdf auto
```

Windows可用py -3。路径带空格需加引号。ingest的--out不会覆盖已有JSON；修订使用新文件名。render总是创建独立版本目录。

## 输出模式

--word与--pdf均支持auto/off/required。auto失败时报告failed或missing_dependency并继续交付实际成功的格式；required失败退出，不发布部分目录。PDF依赖Word；--word off与--pdf required不能同时使用。--soffice仅接受本机实际存在且可执行的LibreOffice路径。

Word为A4图文手册，图片按比例缩放。`--template office|delivery|training`分别选择清爽办公、正式交付和培训图解，默认office；三套原生版式见[模板指南](templates.md)。模板只作用Word/PDF，不修改步骤与证据。长步骤可能自然跨页。中文字体按宿主系统选择，可通过STM_CJK_FONT显式指定已安装字体；不附带字体。PDF转换使用私有临时目录，只复制成功PDF，转换日志和临时文件不进入移交包。转换默认使用当前进程环境；若开发渲染器需要特定字体配置，调用者应设置环境，发布包不内置开发机路径。

macOS转换进程在未设置FONTCONFIG_FILE时，优先采用实际LibreOffice程序旁自带的字体配置；找不到时在本次私有临时目录登记标准macOS字体目录，不修改宿主设置。已有FONTCONFIG_FILE保持优先。其他系统使用宿主字体环境；生成PDF不代表字体与版式已经合格，仍要逐页检查中文，缺字时选择可用字体或修复宿主配置后重新生成。

## 容量与故障

每批1至20张PNG/JPEG，单文件10MiB，单图4000万像素，累计1.2亿像素；JSON上限5MiB，说明文字10万字符。脚本提示低分辨率和完全相同的图片，不能自动判别所有模糊图片或语义重复。

- 读取失败：来源保留error，Agent列出未覆盖资料，继续可用部分；不能把error截图当作已读。
- 来源改变：重新ingest并核对坐标与脱敏，不手改摘要。
- 引文不匹配：核对实际说明行，不改来源来迎合模型。
- 坐标错误：按归正尺寸重查，不能为通过校验扩大或缩小遮盖后不再目检。
- PDF转换失败：查看warnings，交付Word/Markdown并明确PDF未生成；不要给不存在的链接。
- 路径与资料：工作资料目录含原始说明与本地路径，内部使用；外发用移交ZIP，仍应人工复核截图及正文隐私。
