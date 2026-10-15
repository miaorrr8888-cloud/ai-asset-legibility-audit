---
name: ai-asset-legibility-audit
description: 用人工确认的选区和形状比对辅助检查图片或视频帧中文字、数字与版式，明确启发式限制。
license: MIT
---

# 素材文字可读性检查

安装 requirements.txt 中的 NumPy 与 Pillow。

先用 `python references/roi_confirm.py --help` 的网格和选区预览确认目标区域。选区的坐标必须与当前图片空间一致；亮度高不代表字形正确。

用 `python references/legibility_audit.py --help` 查看真值、待测图、两个 ROI、阈值及输出参数。先对已知样例校准。旋转后再做二值化和归一化，搜索旋转以减少纯几何变化造成的低分；过滤空或几乎填满的退化掩膜。

报告形状 IoU、搜索角度、行带数和并排图。HIGH_SIMILARITY / AMBIGUOUS / LOW_SIMILARITY 是几何相似性信号，不能证明同源、生成方式、文字含义或修复可行性。选区错误、透视、背景及抗锯齿都可能影响分数。阈值不是通用科学标准。

最终逐字、逐数目视核对并记录未确认项。视频应覆盖字幕切换与片尾；抽样只能支持被查看帧的结论。本包不包含完整视频逐帧或 OCR 验证器。
