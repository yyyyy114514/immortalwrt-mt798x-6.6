#!/usr/bin/env python3
import re, collections

path = "/workspace/immortalwrt-mt798x-6.6/target/linux/mediatek/image/filogic.mk"
lines = open(path, encoding="utf-8").read().splitlines()

blocks = {}
cur = None
for i, line in enumerate(lines):
    m = re.match(r"^define Device/(.+)$", line)
    if m:
        cur = m.group(1).strip()
        blocks[cur] = {"dts": None}
    elif re.match(r"^endef", line):
        cur = None

cur_name = None
for i, line in enumerate(lines):
    m = re.match(r"^define Device/(.+)$", line)
    if m:
        cur_name = m.group(1).strip()
        continue
    if re.match(r"^endef", line):
        cur_name = None
        continue
    if cur_name is None:
        continue
    dm = re.match(r"^\s*DEVICE_DTS\s*:=\s*(.*)$", line)
    if dm:
        blocks[cur_name]["dts"] = dm.group(1).strip()

devices = []
for i, line in enumerate(lines):
    m = re.match(r"^TARGET_DEVICES\s*\+?=\s*(.+)$", line)
    if m:
        for d in m.group(1).split():
            devices.append((d, blocks.get(d, {}).get("dts")))

def soc_of(dts):
    if not dts:
        return "unknown"
    dts = dts.split()[0]
    m = re.search(r"mt79(\d\d)", dts)
    if m:
        return "mt79" + m.group(1)
    return dts.split("-")[0]

by_soc = collections.defaultdict(list)
for name, dts in devices:
    by_soc[soc_of(dts)].append((name, dts))

for soc in sorted(by_soc):
    print(f"===== {soc} ({len(by_soc[soc])}) =====")
    for name, dts in by_soc[soc]:
        print(f"{name}\t{dts}")
