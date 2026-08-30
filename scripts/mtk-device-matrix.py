#!/usr/bin/env python3
"""将多选 MTK Filogic 设备解析为按 SoC 分组的构建矩阵, 并动态生成 defconfig。

设备清单来自 target/linux/mediatek/image/filogic.mk (TARGET_DEVICES)。
匹配规则: 先精确匹配设备 ID, 再子串模糊匹配; 'all' = 所选 SoC 的全部设备;
'help' = 打印全部支持设备。

命令:
  help [--soc S]
      打印设备清单(可按 SoC 过滤), 不生成矩阵。

  resolve --soc S --devices "D1 D2 ..."
      解析设备并输出 matrix=... 和 socs=... 两行(GITHUB_OUTPUT 可直接使用)。

  gen --soc S --devices "D1 D2 ..." --output FILE
      基于 defconfig/<soc>-all.config 生成只含所选设备的配置并写入 FILE。

--soc 取值: auto | mt7981 | mt7986 | mt7988。auto 表示按所选设备自动归类。
"""
import argparse
import hashlib
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILOGIC = os.path.join(BASE, "target/linux/mediatek/image/filogic.mk")
DEFCONF = os.path.join(BASE, "defconfig")
SOCS = ["mt7981", "mt7986", "mt7988"]
SOC_NAME = {
    "mt7981": "MT7981 (Filogic 820, mtwifi 闭源 + EasyMesh)",
    "mt7986": "MT7986 (Filogic 830, mtwifi 闭源 + EasyMesh)",
    "mt7988": "MT7988 (Filogic 880, 开源 mt76, 无 EasyMesh)",
}


def fail(msg):
    sys.stderr.write("::error::%s\n" % msg)
    sys.exit(1)


def parse_filogic():
    """返回 {device_id: dts_name} (仅 TARGET_DEVICES 列出的设备)."""
    lines = open(FILOGIC, encoding="utf-8").read().splitlines()
    dts, cur = {}, None
    for line in lines:
        m = re.match(r"^define Device/(.+)$", line)
        if m:
            cur = m.group(1).strip()
            continue
        if re.match(r"^endef", line):
            cur = None
            continue
        if cur:
            dm = re.match(r"^\s*DEVICE_DTS\s*:=\s*(.+)$", line)
            if dm:
                dts[cur] = dm.group(1).strip().split()[0]
    dev = {}
    for line in lines:
        m = re.match(r"^TARGET_DEVICES\s*\+?=\s*(.+)$", line)
        if m:
            for d in m.group(1).split():
                dev[d] = dts.get(d, "")
    return dev


def soc_of(dts):
    m = re.search(r"mt79(\d\d)", dts or "")
    return ("mt79" + m.group(1)) if m else None


def group_by_soc(dev):
    by = {}
    for d, dts in dev.items():
        s = soc_of(dts)
        if s:
            by.setdefault(s, []).append(d)
    for s in by:
        by[s].sort()
    return by


def match_devices(dev, tokens):
    """把输入 token 解析为设备 ID 列表 + 是否 all。"""
    chosen, all_flag = [], False
    for tok in tokens:
        if tok == "all":
            all_flag = True
            continue
        if tok == "help":
            continue
        if tok in dev:
            chosen.append(tok)
            continue
        key = re.sub(r"[-_.]", "", tok.lower())
        hits = sorted(d for d in dev if key in re.sub(r"[-_.]", "", d.lower()))
        if len(hits) == 1:
            chosen.append(hits[0])
        elif len(hits) > 1:
            fail("设备 '%s' 匹配到多个: %s\n请用完整设备 ID 或更精确的关键字。" % (tok, ", ".join(hits)))
        else:
            fail("未找到设备 '%s'。填 help 查看全部设备; 填 all 构建全部。" % tok)
    # 去重且保序
    seen, uniq = set(), []
    for d in chosen:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    return uniq, all_flag


def pick_socs(dev, chosen, all_flag, soc_opt):
    """确定要构建的 SoC 列表和每个 SoC 的设备集合。返回 {soc: [device...] | 'all'}"""
    if not chosen and not all_flag:
        fail("未选择任何设备。填 help 查看设备; 填 all 构建全部; 或用逗号/空格分隔多个设备 ID。")
    result = {}
    if all_flag:
        if soc_opt != "auto":
            result[soc_opt] = "all"
        else:
            for s in SOCS:
                result[s] = "all"
        return result
    cs = {}
    for d in chosen:
        s = soc_of(dev.get(d, ""))
        if not s:
            fail("设备 %s 缺少 DTS, 无法确定芯片型号。" % d)
        cs.setdefault(s, []).append(d)
    if soc_opt != "auto":
        if any(s != soc_opt for s in cs):
            fail("所选设备不属于 %s: %s\n(这些设备属于: %s)" % (
                soc_opt, ", ".join(chosen), ", ".join(sorted(cs))))
        result[soc_opt] = cs.get(soc_opt, [])
    else:
        result = cs
    return result


def gen_config(soc, devices):
    base = os.path.join(DEFCONF, "%s-all.config" % soc)
    if not os.path.exists(base):
        fail("缺少配置基线 defconfig/%s-all.config, 请先运行 gen_all_configs.py。" % soc)
    if devices == "all":
        return open(base, encoding="utf-8").read()
    dev_list = devices.split(",")
    lines = open(base, encoding="utf-8").read().splitlines()
    out = [l for l in lines if not l.startswith("CONFIG_TARGET_DEVICE_")]
    ins = []
    for d in dev_list:
        ins.append("CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_%s=y" % d)
        ins.append('CONFIG_TARGET_DEVICE_PACKAGES_mediatek_filogic_DEVICE_%s=""' % d)
    idx = next((i for i, l in enumerate(out) if l.startswith("CONFIG_HAS_SUBTARGETS=")), 1)
    out[idx + 1:idx + 1] = ins
    return "\n".join(out) + "\n"


def cfg_name(soc, devices):
    if devices == "all":
        return "%s-all.config" % soc
    h = hashlib.sha1(devices.encode()).hexdigest()[:8]
    return "custom-%s-%s.config" % (soc, h)


def cmd_help(dev, soc_opt):
    by = group_by_soc(dev)
    print("# 支持的 MTK Filogic 设备 (共 %d 台):" % len(dev))
    for s in SOCS:
        if soc_opt != "auto" and s != soc_opt:
            continue
        print("\n## %s  (%d 台)  %s" % (s, len(by.get(s, [])), SOC_NAME[s]))
        for d in by.get(s, []):
            print("  %s" % d)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["help", "resolve", "gen"])
    ap.add_argument("--soc", default="auto")
    ap.add_argument("--devices", default="")
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    dev = parse_filogic()
    tokens = [t.strip() for t in re.split(r"[,;\s]+", args.devices) if t.strip()]

    if args.cmd == "help":
        cmd_help(dev, args.soc)
        return

    if not tokens:
        fail("--devices 不能为空。填 help 查看设备; 填 all 构建全部。")
    if "help" in tokens:
        cmd_help(dev, args.soc)
        print("matrix=[]")
        return

    chosen, all_flag = match_devices(dev, tokens)
    groups = pick_socs(dev, chosen, all_flag, args.soc)

    if args.cmd == "gen":
        if not args.output:
            fail("gen 需要 --output 指定输出文件。")
        for soc, devs in groups.items():
            cfg = devs if devs == "all" else ",".join(devs)
            open(args.output, "w", encoding="utf-8").write(gen_config(soc, cfg))
        return

    # resolve -> 输出矩阵
    by = group_by_soc(dev)
    matrix = []
    for soc in sorted(groups):
        devs = groups[soc]
        cfg = devs if devs == "all" else ",".join(devs)
        matrix.append({"soc": soc, "file": cfg_name(soc, cfg), "devices": cfg})
    print("# 选中设备: %s" % (", ".join(chosen) if chosen else "(全部)"))
    for entry in matrix:
        cnt = len(by.get(entry["soc"], [])) if entry["devices"] == "all" else len(entry["devices"].split(","))
        print("#   %s -> %s (%d 台)" % (entry["soc"], entry["file"], cnt))
    print("matrix=" + json.dumps(matrix, ensure_ascii=False))
    print("socs=" + ",".join(e["soc"] for e in matrix))


if __name__ == "__main__":
    main()
