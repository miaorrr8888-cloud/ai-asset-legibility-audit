# -*- coding: utf-8 -*-
"""
legibility_audit.py — 可读性审计核心：归一化掩膜 IoU + 版式行带数

用法：
    python legibility_audit.py --truth <真值图> --test <待测图或帧> \
        --truth-box x0,y0,x1,y1 --test-box x0,y0,x1,y1 [--th 150] [--out outdir]

输出：终端报告 + <outdir>/legibility_verdict.json + <outdir>/mask_sidebyside.png

自检（校准阈值，强烈建议先跑）：
    python legibility_audit.py --selftest --truth <真值图> --truth-box x0,y0,x1,y1
    会把真值区自己缩放旋转一版当"待测"，验证同源样本确实 > 0.60。
"""
import os
import sys
import json
import argparse

import numpy as np
from PIL import Image


def load_gray(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float64)


def crop(arr, box):
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= arr.shape[1] and 0 <= y0 < y1 <= arr.shape[0]):
        raise ValueError("ROI is empty or outside image bounds")
    return arr[y0:y1, x0:x1]


def binarize(arr, th):
    return arr > th


def norm_mask(mask, n=192):
    """按自身 bbox 裁剪后 resize 到 n×n，消除位置与尺度差异。

    ⚠️ 实测重要限制：本变换是 **尺度不变、但旋转不不变** 的。
    bbox 归一化无法消除旋转 —— 一个纯旋转过的同源图形，此处会得到很低的 IoU。
    因此**必须**配合 rotate_search 使用，否则会把"仅旋转"误判成"重绘"（假阳性）。
    自检已证实：scale 0.7–1.4 无旋转 → IoU 0.87~1.00；
                 任意角度旋转 → IoU 0.05~0.11（与真实重绘无法区分）。
    """
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return np.zeros((n, n), bool)
    c = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    im = Image.fromarray((c * 255).astype(np.uint8)).resize((n, n), Image.NEAREST)
    return np.asarray(im) > 127


def _rot_mask(mask, ang, n=192):
    """把二值掩膜按其 bbox 裁出后旋转 ang 度，再归一化到 n×n。"""
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return np.zeros((n, n), bool)
    c = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    im = Image.fromarray((c * 255).astype(np.uint8)).rotate(
        ang, expand=True, resample=Image.BILINEAR, fillcolor=0)
    im = im.resize((n, n), Image.NEAREST)
    return np.asarray(im) > 127


def _rot_gray(gray_crop, ang, th, n=192):
    """★ 首选路径：在**灰度**上旋转，再二值化。

    为什么不用 _rot_mask：先二值化再旋转会在 expand 出的画布上引入多余黑边、
    并把细笔画的抗锯齿信息丢掉，导致同源样本虚低（实测 -15° 时只有 0.52）。
    先旋转灰度、后二值化可保住笔画，同源样本回升到 >0.6。
    """
    if gray_crop.size == 0:
        return np.zeros((n, n), bool)
    im = Image.fromarray(np.clip(gray_crop, 0, 255).astype(np.uint8)).rotate(
        ang, expand=True, resample=Image.BICUBIC, fillcolor=0)
    a = np.asarray(im).astype(np.float64)
    m = a > th
    ys, xs = np.where(m)
    if len(xs) == 0:
        return m.reshape(-1, n) if m.size == n * n else np.zeros((n, n), bool)
    sub = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    img2 = Image.fromarray((sub * 255).astype(np.uint8)).resize((n, n), Image.NEAREST)
    return np.asarray(img2) > 127


def _coverage_ok(m, ref, lo=0.10, hi=4.00):
    """退化匹配守卫：拒绝「几乎全空 / 几乎填满 / 覆盖面积与真值差太多」的掩膜。

    ★ 这是全网搜索类判据的必备守卫，缺了会出**假阳性**。
    实测：某工具在旋转搜索下对每一帧都返回 best_IoU = 1.0000 —— 这是退化解，
    旋转到某角度后掩膜塌缩成小团，归一化后与参考几乎同形，IoU 触顶。
    判据：候选掩膜的填充率必须与参考掩膜在同一量级。
    """
    r = float(ref.mean())
    c = float(m.mean())
    if c < 0.02 or c > 0.98:
        return False
    if r <= 1e-9:
        return False
    ratio = c / r
    return lo <= ratio <= hi


def _mask_shape_sig(mask):
    """粗略形状签名（填充率 + 长宽比），用于排除形状明显不符的候选。"""
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    h = ys.max() - ys.min() + 1
    w = xs.max() - xs.min() + 1
    return float(mask.mean()), (h / float(w) if w else 0.0)


def _best_scale_rot(ref, gray_crop, th, angles=range(-40, 41, 1), n=192):
    """在旋转 + 相对尺度上搜索，返回 (best_iou, best_scale, best_angle)。

    旋转不不变是已知陷阱，这里用暴力搜索补掉。
    ★ 在灰度上旋转（见 _rot_gray），保住细笔画。
    ★ 角度步长 1°：2° 步长会错过真实角度。
    ★ 缩放后必须重新归一化回 n×n，否则形状不匹配。
    ★★ 必须用 _coverage_ok 过滤退化解，否则会出现 best_IoU=1.0000 的假阳性。
    """
    ref_sig = _mask_shape_sig(ref)
    best = (0.0, 1.0, 0)
    for ang in angles:
        base = _rot_gray(gray_crop, ang, th, n)
        if base.sum() == 0:
            continue
        for sc in (0.80, 0.90, 1.00, 1.11, 1.25):
            if abs(sc - 1.0) < 1e-9:
                m = base
            else:
                h, w = base.shape
                img = Image.fromarray((base * 255).astype(np.uint8)).resize(
                    (max(4, int(w * sc)), max(4, int(h * sc))), Image.NEAREST)
                a2 = np.asarray(img) > 127
                ys2, xs2 = np.where(a2)
                if len(xs2) == 0:
                    continue
                sub = a2[ys2.min():ys2.max() + 1, xs2.min():xs2.max() + 1]
                img2 = Image.fromarray((sub * 255).astype(np.uint8)).resize(
                    (n, n), Image.NEAREST)
                m = np.asarray(img2) > 127
            if m.shape != ref.shape:
                continue
            if not _coverage_ok(m, ref):        # ★ 退化解守卫
                continue
            s = iou(ref, m)
            if s > best[0]:
                best = (s, sc, ang)
    return best


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum()) / float(u) if u else 0.0


def row_bands(mask, min_c=3, min_h=5):
    """亮像素成段的行带 —— 用于比对版式。"""
    rc = mask.sum(axis=1)
    bands, st = [], None
    for i, c in enumerate(rc):
        if c >= min_c and st is None:
            st = i
        elif c < min_c and st is not None:
            if i - st >= min_h:
                bands.append((st, i - 1))
            st = None
    if st is not None and len(rc) - st >= min_h:
        bands.append((st, len(rc) - 1))
    return bands


def verdict_from_iou(v):
    if not np.isfinite(v):
        return "UNKNOWN", "nonfinite similarity score"
    if v > 0.60:
        return "HIGH_SIMILARITY", "high geometric similarity; inspect text manually"
    if v >= 0.30:
        return "AMBIGUOUS", "intermediate geometric similarity"
    return "LOW_SIMILARITY", "low geometric similarity; provenance remains unknown"


def verdict_from_best(v):
    return verdict_from_iou(v)


def save_sidebyside(a, b, path):
    n = a.shape[0]
    im = Image.new("RGB", (n * 2 + 20, n), (20, 20, 20))
    im.paste(Image.fromarray((a * 255).astype(np.uint8)).convert("RGB"), (0, 0))
    im.paste(Image.fromarray((b * 255).astype(np.uint8)).convert("RGB"), (n + 20, 0))
    im.resize((im.width * 5, im.height * 5), Image.NEAREST).save(path)


def selftest(truth_path, tbox, th, outdir):
    """同源校准：把真值区自己缩放+旋转，验证【旋转搜索后】确实得高分。

    ★ 这是本技能最有价值的一步。若不做，会误把"仅旋转"判成"重绘"。
    """
    g = load_gray(truth_path)
    t = binarize(crop(g, tbox), th)
    ref = norm_mask(t)
    print("\n=== SELFTEST A: 纯 bbox 归一化（无旋转搜索）===")
    print("    预期：无旋转高分；有旋转低分 —— 这正是必须补旋转搜索的原因")
    rows = []
    for sc, ang in [(0.7, 0), (1.0, 0), (1.4, 0), (1.0, 8), (1.0, -15), (0.8, 12)]:
        img = Image.open(truth_path).convert("L").crop(tbox)
        w, h = img.size
        img2 = img.resize((max(4, int(w * sc)), max(4, int(h * sc))), Image.BICUBIC)
        img2 = img2.rotate(ang, expand=True, fillcolor=0)
        m = norm_mask(np.asarray(img2).astype(np.float64) > th)
        rows.append((sc, ang, iou(ref, m)))
    for sc, ang, s in rows:
        print(f"  scale={sc:<5} rot={ang:>4}°  IoU={s:.4f}")

    print("\n=== SELFTEST B: 旋转+尺度搜索后（正式判据）===")
    ok = True
    for sc, ang in [(0.7, 0), (1.0, 0), (1.4, 0), (1.0, 8), (1.0, -15), (0.8, 12)]:
        img = Image.open(truth_path).convert("L").crop(tbox)
        w, h = img.size
        img2 = img.resize((max(4, int(w * sc)), max(4, int(h * sc))), Image.BICUBIC)
        img2 = img2.rotate(ang, expand=True, fillcolor=0)
        cg = np.asarray(img2).astype(np.float64)
        bi, bs, ba = _best_scale_rot(ref, cg, th)
        flag = "OK" if bi > 0.60 else "LOW!!"
        if bi <= 0.60:
            ok = False
        print(f"  scale={sc:<5} rot={ang:>4}°  best_IoU={bi:.4f} "
              f"@(s={bs}, a={ba}°)  {flag}")
    print(f"\n结论：{'✅ 阈值标定通过 —— 同源样本在搜索后均 > 0.60，可用 0.60/0.30' if ok else '⚠️ 有同源样本未达 0.60：该角度/尺度组合下判据偏保守，遇到 AMBIGUOUS 结果时务必人工看图'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth")
    ap.add_argument("--test")
    ap.add_argument("--truth-box")
    ap.add_argument("--test-box")
    ap.add_argument("--th", type=float, default=150.0,
                    help="二值化阈值。真实暗底亮字场景常用 150；"
                         "若真值图是白底会误判，请先确认 ROI 内是暗底")
    ap.add_argument("--out", default="legibility_out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if not a.truth or not a.truth_box:
        ap.error("--truth 与 --truth-box 必填")
    tbox = tuple(int(v) for v in a.truth_box.split(","))
    os.makedirs(a.out, exist_ok=True)

    if a.selftest:
        selftest(a.truth, tbox, a.th, a.out)
        return

    if not a.test or not a.test_box:
        ap.error("非 selftest 模式需 --test 与 --test-box")
    vbox = tuple(int(v) for v in a.test_box.split(","))

    tg = load_gray(a.truth)
    vg = load_gray(a.test)
    tm = binarize(crop(tg, tbox), a.th)
    vm = binarize(crop(vg, vbox), a.th)
    tb, vb = row_bands(tm), row_bands(vm)

    print(f"truth  box={tbox}  seg_px={int(tm.sum()):7d}  row_bands={len(tb)}")
    print(f"test   box={vbox}  seg_px={int(vm.sum()):7d}  row_bands={len(vb)}")
    for i, b in enumerate(tb):
        print(f"    truth band{i}: y={b[0]}..{b[1]}")
    for i, b in enumerate(vb):
        print(f"    test  band{i}: y={b[0]}..{b[1]}")

    na, nb = norm_mask(tm), norm_mask(vm)   # n=192
    v_plain = iou(na, nb)
    # ★ 必须传【待测(test)】的灰度裁剪去搜索，不是真值裁剪。
    #   曾经误传真值裁剪 → 变成拿真值跟自己比 → 恒为 IoU=1.0000 假阳性。
    v_crop_gray = crop(vg, vbox)
    best_iou, best_s, best_ang = _best_scale_rot(na, v_crop_gray, a.th)

    tag, msg = verdict_from_best(best_iou)
    save_sidebyside(na, nb, os.path.join(a.out, "mask_sidebyside.png"))

    print(f"\n旋转搜索：best_IoU = {best_iou:.4f}  (s={best_s}, rot={best_ang}°)")
    print(f"未搜索参考值 = {v_plain:.4f}（仅留痕；★ 不可单独用于判决，见下方提示）")
    print(f"版式行带：truth={len(tb)}  test={len(vb)}  "
          f"{'一致' if len(tb) == len(vb) else '★不一致（版式不同源，独立佐证）'}")
    print(f"\n判决：{tag} — {msg}")

    agree = (tag == "LOW_SIMILARITY" and len(tb) != len(vb)) or (tag == "HIGH_SIMILARITY" and len(tb) == len(vb))
    print(f"\n证据一致性：IoU 判决={'REDRAWN' if tag=='REDRAWN' else tag} vs "
          f"行带{'一致' if len(tb)==len(vb) else '不一致'} → "
          f"{'两者互证，信心高' if agree else '★两者冲突，必须人工看图裁定，勿下结论'}")
    print("提示：分数仅描述几何相似性；高分或低分均不能证明来源或重绘方式。")

    json.dump({"best_iou": round(best_iou, 4), "best_scale": best_s,
               "best_angle_deg": best_ang, "verdict": tag,
               "iou_no_rotation_search": round(v_plain, 4),
               "truth_row_bands": len(tb), "test_row_bands": len(vb),
               "truth_seg_px": int(tm.sum()), "test_seg_px": int(vm.sum()),
               "truth_box": list(tbox), "test_box": list(vbox), "th": a.th,
               "evidence_agreement": bool(agree)},
              open(os.path.join(a.out, "legibility_verdict.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"saved {a.out}/legibility_verdict.json, {a.out}/mask_sidebyside.png")


if __name__ == "__main__":
    main()
