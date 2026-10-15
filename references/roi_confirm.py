# -*- coding: utf-8 -*-
"""
roi_confirm.py — 在测任何指标之前，先确认 ROI 真的框在目标上。

背景（实测踩坑）：
  坏 ROI 会产出语义完全反向的结论。实测把机身平面当屏幕测，得到"峰值 49–86，屏幕损坏"；
  换对 ROI 后同一帧是"255，很亮"。两次都是幻觉，因为 ROI 就错了。

本工具做三件事：
  A. 输出带 100px 网格 + 坐标标注的对照图，供肉眼确认目标位置
  B. 对给定 ROI 给出「这个 ROI 是不是框住的」的自检信号
     （若亮像素 bbox 恰好贴住 ROI 四边 → 说明 ROI 太紧或抓到了别的东西）
  C. 扫描模式：在整帧里按行带找出"亮内容"的分布，辅助定位目标真实位置

用法：
    python roi_confirm.py --img frame.png --grid --out g.png
    python roi_confirm.py --img frame.png --check 330,690,630,1150 --th 150
    python roi_confirm.py --img frame.png --scan --th 150
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageDraw


def load_gray(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float64)


def make_grid(img_path, out_path, step=100):
    im = Image.open(img_path).convert("RGB")
    d = ImageDraw.Draw(im)
    W, H = im.size
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=(255, 0, 0), width=1)
        d.text((x + 3, 3), str(x), fill=(255, 0, 0))
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=(0, 128, 255), width=1)
        d.text((3, y + 3), str(y), fill=(0, 128, 255))
    im.save(out_path)
    print(f"saved grid -> {out_path}  size={im.size}  (红=竖线x, 蓝=横线y, 步长{step})")


def check(img_path, box, th):
    g = load_gray(img_path)
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= g.shape[1] and 0 <= y0 < y1 <= g.shape[0]):
        print(f"!! ROI {box} 越界，图像为 {g.shape[1]}x{g.shape[0]}")
        return
    roi = g[y0:y1, x0:x1]
    m = roi > th
    n = int(m.sum())
    print(f"ROI={box}  size={x1-x0}x{y1-y0}  th={th}")
    print(f"  max={roi.max():.0f}  mean={roi.mean():.1f}  "
          f"p95={np.percentile(roi,95):.1f}  p99={np.percentile(roi,99):.1f}")
    print(f"  亮像素(>{th:.0f}) = {n}  ({100.0*n/m.size:.2f}% of ROI)")
    if n == 0:
        print("  !! ROI 内零亮像素 —— 几乎可以肯定 ROI 定错了（或阈值过高）")
        return
    ys, xs = np.where(m)
    bx = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    print(f"  亮像素 bbox(ROI 局部) = {bx}")
    edge = []
    if bx[0] == 0:
        edge.append("左")
    if bx[1] == 0:
        edge.append("上")
    if bx[2] == roi.shape[1] - 1:
        edge.append("右")
    if bx[3] == roi.shape[0] - 1:
        edge.append("下")
    if edge:
        print(f"  !! 亮像素触边（{'/'.join(edge)}）→ ROI 太紧，或抓到的不是目标。"
              f" 请放宽 ROI 后重测，勿据此下结论。")
    else:
        print("  亮像素未触边，ROI 初步合格（仍建议看图确认语义正确）")


def scan(img_path, th, min_run=3):
    g = load_gray(img_path)
    rc = (g > th).sum(axis=1)
    print(f"逐行亮像素(>{th:.0f}) 成段区间（min_run={min_run}）:")
    st, bands = None, []
    for y, c in enumerate(rc):
        if c >= min_run and st is None:
            st = y
        elif c < min_run and st is not None:
            if y - st >= 4:
                bands.append((st, y - 1))
            st = None
    if st is not None:
        bands.append((st, len(rc) - 1))
    for b in bands:
        strip = g[b[0]:b[1] + 1, :] > th
        ys2, xs2 = np.where(strip)
        if len(xs2):
            print(f"  y={b[0]:5d}..{b[1]:5d} h={b[1]-b[0]+1:4d}   "
                  f"x={int(xs2.min()):4d}..{int(xs2.max()):4d} w={int(xs2.max()-xs2.min())+1:4d} "
                  f"px={int(strip.sum()):7d}")
    if not bands:
        print("  （无成段亮区，检查阈值或图像）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--img", required=True)
    ap.add_argument("--grid", action="store_true")
    ap.add_argument("--check")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--th", type=float, default=150.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.grid:
        out = a.out or os.path.splitext(a.img)[0] + "_grid.png"
        make_grid(a.img, out)
    if a.check:
        check(a.img, tuple(int(v) for v in a.check.split(",")), a.th)
    if a.scan:
        scan(a.img, a.th)
    if not (a.grid or a.check or a.scan):
        ap.error("至少指定 --grid / --check / --scan 之一")


if __name__ == "__main__":
    main()
