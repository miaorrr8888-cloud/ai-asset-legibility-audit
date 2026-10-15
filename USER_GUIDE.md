# 图片文字与型号核对：用户使用指南

## 它能帮你做什么

用本地OCR读取图片文字，与自己提供的正确文字比较；还提供选区和形状比较工具作辅助。

## 适合谁

核对产品图、报价图、宣传图中文字和数字的电商运营、设计师、资料整理人员。

## 具体解决什么问题

图片里的型号、价格和数字容易看漏；只看图片整体像不像，发现不了具体文字是否正确。

**不适合这些目标：**自动证明所有文字正确、替代校对人员、仅靠一个分数判断复杂实拍照片或完整视频。

## 下载与准备

- [打开独立仓库](https://github.com/miaorrr8888-cloud/ai-asset-legibility-audit)
- [直接下载源码ZIP](https://github.com/miaorrr8888-cloud/ai-asset-legibility-audit/archive/refs/heads/main.zip)

也可在仓库页面点 Code → Download ZIP。解压后打开包含 SKILL.md、README.md、USER_GUIDE.md 的那层文件夹。不要停在外层目录或只复制一个脚本。

建议使用Windows电脑和Python 3.12；这是本次验证环境。先在该文件夹打开PowerShell，再执行：

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe --version
```

这里直接使用虚拟环境里的Python，不需要运行激活脚本或修改系统执行策略。安装步骤及其他系统说明见[通用安装说明](https://github.com/miaorrr8888-cloud/agent-skills-worklog/blob/main/INSTALLATION.md)。

安装本示例需要的依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
```

## 第一次使用：先跑自带示例

读取示例中的“产品型号 DEMO 123、价格199元”。正确期望值匹配；把123误写成128时，应得到不匹配。

```powershell
.\.venv\Scripts\python.exe scripts/rapid_ocr_check.py examples/ocr-real.png --expected "产品型号 DEMO 123 价格 199 元"
```

## 结果怎么看

终端输出识别文字、文字框、置信度和 TEXT_MATCH。把命令中的123改成128后应返回 TEXT_MISMATCH 和退出码1；这是发现差异，不是程序崩溃。

## 换成自己的资料

一张本地图片，加上 --expected 后面用引号包住的正确文字。正确文字由使用者提供，工具不能替你确定事实。

先核对图片真实应有的文字，再把图片路径和 --expected 替换成自己的输入。保留原图，查看识别框；低置信度或空结果需人工检查。

## 不想手动敲命令：给AI助手的任务

以下任务适用于能读取所选目录、执行本地命令的助手。WorkBuddy需要先确认当前版本的权限与技能启用状态；本项目未完成WorkBuddy实际导入验收。

```text
请先读取我选定文件夹中的 SKILL.md 和 USER_GUIDE.md，只在该项目范围内处理。
先按USER_GUIDE运行示例图片OCR，分别验证正确型号123和故意错误型号128的结果。把识别文本、差异和需要人工检查的地方用中文说明。不要把测试图片当成真实客户资料或所有场景的准确率证明。
缺少依赖时先说明用途，优先放进本项目虚拟环境；不要读取其他目录中的密码、密钥或浏览器登录数据。
```

## 常见问题

**缺少 rapidocr_onnxruntime**

确认下面安装依赖和运行命令用的是同一个 .venv Python；首次安装需要下载依赖。

**返回 REVIEW_REQUIRED**

可能没识别到文字或置信度低。先看图片是否清晰、文字是否太小，不要直接改成通过。

**找不到文件或脚本**

确认终端当前目录就是包含SKILL.md的技能根目录；路径含空格时加双引号。输出目录已存在时换新名字，不覆盖已有结果。

## 当前能力边界

演示使用清晰合成图片。OCR会漏字、错字，透视、背景、艺术字体可能降低效果；置信度不是正确概率。识别在本地引擎中运行，仍需核对原图。

## 验证范围

本指南示例已在Windows独立副本中运行复核，见[命令复核结果](https://github.com/miaorrr8888-cloud/agent-skills-worklog/blob/main/USER_GUIDES_VERIFICATION.md)。已有回归测试只覆盖被测试行为，不证明真实业务结果。WorkBuddy实际运行、手机端使用和所有系统版本均不在本次已验证范围内。

许可证和素材来源分别见 [LICENSE](LICENSE)、[PROVENANCE.md](PROVENANCE.md)。
