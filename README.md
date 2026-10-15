# 图片文字与数字可读性辅助检查

`ai-asset-legibility-audit` · 独立技能仓库 · MIT

适合：检查 AI 图片、产品屏幕和字幕帧的设计师或 QA

## 解决什么问题

先确认检查区域，再比较真值与待测区域的几何结构，辅助发现疑似变形或缺失。

## 快速开始

Python 3.10+，numpy 与 Pillow：python -m pip install -r requirements.txt。

在本仓库根目录运行：

```sh
python references/roi_confirm.py --img examples/truth.png --grid --out output-grid.png
python references/legibility_audit.py --truth examples/truth.png --test examples/test.png --truth-box 0,0,200,100 --test-box 0,0,200,100 --out output-audit
```

## 输入与输出

**输入**：两张图片、人工确认的四坐标 ROI 和阈值。示例为相同的人工构造图案，用于演示，不是模型效果证明。

**输出**：相似性 JSON、掩膜并排图、行带统计；UNKNOWN 表示不能据此判断。

## 本次完善

原有缺口：空白或全填满的掩膜仍可能产出误导性的低相似性；异常阈值和失败校准没有清楚反馈。

已补：空白/退化信号标 UNKNOWN；拒绝非有限阈值，输出标准 JSON；失败校准返回失败码；提供可运行的合成图片示例。

## 仍然缺什么

不是 OCR，也不判读具体文字；旋转与阈值搜索不能完全处理透视、背景与噪声；高低分都不能证明同源或重绘，需要人工逐字看图。

## 验证与使用注意

```sh
python -m unittest discover -s tests -v
```

测试覆盖被断言的离线行为，不等于真实平台、生产模型或业务效果验证。

示例数据和图片均为合成演示，不是真实客户、交易、销量或模型成绩。不要提交真实凭据和私有输入。

## 来源与工作记录

由 miaorrr8888-cloud 在 AI 辅助下积累和维护，来源与边界见 [PROVENANCE.md](PROVENANCE.md)，许可见 [LICENSE](LICENSE)。

[全部独立技能与阶段性工作记录](https://github.com/miaorrr8888-cloud/agent-skills-worklog)
