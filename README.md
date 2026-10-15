# ai-asset-legibility-audit

Python 3.10+, NumPy and Pillow (see requirements.txt).
Run `python references/legibility_audit.py --help`.
Invalid regions now raise an error; nonfinite scores are UNKNOWN.
Shape similarity is a heuristic; it does not certify text meaning or prove provenance.

Published by miaorrr8888-cloud with AI-assisted development and cleanup. See PROVENANCE.md and LICENSE.
Validation: run `python -m unittest discover -s tests -v` from this repository root.

## 独立仓库

本仓库只包含 ai-asset-legibility-audit 一个技能。
源码目录、SKILL.md、许可和相关测试均可独立取得，不依赖其他技能仓库。
工作记录与其他技能入口：[agent-skills-worklog](https://github.com/miaorrr8888-cloud/agent-skills-worklog)。

离线验证：`python -m unittest discover -s tests -v`。
