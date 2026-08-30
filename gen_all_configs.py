#!/usr/bin/env python3
"""Generate per-SoC all-device defconfigs for the padavanonly/immortalwrt-mt798x-6.6 tree.

Base: the working mt7986-n60pro.config (mtwifi 7.6.6.1 + EasyMesh + plugins).
Output:
  defconfig/mt7981-all.config   (all 91  MT7981 devices, mtwifi + EasyMesh)
  defconfig/mt7986-all.config   (all 47  MT7986 devices, mtwifi + EasyMesh)
  defconfig/mt7988-all.config   (all 7   MT7988 devices, mt76 开源无线, 无 mtwifi)
"""
import re, os

BASE = "/workspace/immortalwrt-mt798x-6.6"
FILOGIC = os.path.join(BASE, "target/linux/mediatek/image/filogic.mk")
N60 = os.path.join(BASE, "defconfig/mt7986-n60pro.config")

# ---------- 1. parse device -> SoC ----------
lines = open(FILOGIC, encoding="utf-8").read().splitlines()
blocks = {}
cur = None
for i, line in enumerate(lines):
    m = re.match(r"^define Device/(.+)$", line)
    if m:
        cur = m.group(1).strip(); blocks[cur] = {"dts": None}
    elif re.match(r"^endef", line):
        cur = None
cur_name = None
for line in lines:
    m = re.match(r"^define Device/(.+)$", line)
    if m: cur_name = m.group(1).strip(); continue
    if re.match(r"^endef", line): cur_name = None; continue
    if cur_name is None: continue
    dm = re.match(r"^\s*DEVICE_DTS\s*:=\s*(.*)$", line)
    if dm: blocks[cur_name]["dts"] = dm.group(1).strip()

devices = []
for line in lines:
    m = re.match(r"^TARGET_DEVICES\s*\+?=\s*(.+)$", line)
    if m:
        for d in m.group(1).split():
            devices.append((d, blocks.get(d, {}).get("dts")))

def soc_of(dts):
    dts = (dts or "").split()[0]
    m = re.search(r"mt79(\d\d)", dts)
    return ("mt79" + m.group(1)) if m else "unknown"

by_soc = {}
for name, dts in devices:
    by_soc.setdefault(soc_of(dts), []).append(name)
for k in by_soc:
    by_soc[k].sort()

# ---------- 2. read n60pro base ----------
base_lines = open(N60, encoding="utf-8").read().splitlines()

def line_no(prefix):
    for i, l in enumerate(base_lines):
        if l.startswith(prefix):
            return i
    return None

i_target = line_no("CONFIG_TARGET_mediatek=y")        # 8
i_dev_start = line_no("CONFIG_TARGET_MULTI_PROFILE=y") # 10
# device block = line 8 .. (line before CONFIG_TARGET_MULTI_PROFILE)
# We keep base settings starting from CONFIG_TARGET_MULTI_PROFILE .. but actually
# the bogus CONFIG_TARGET_mediatek_mt7986=y (line 9) is part of target block.
# Find first CONFIG_TARGET_DEVICE_ line
i_first_dev = next(i for i, l in enumerate(base_lines) if l.startswith("CONFIG_TARGET_DEVICE_mediatek"))
# find line after last device entry
i_after_dev = next(i for i, l in enumerate(base_lines) if l.startswith("CONFIG_CCACHE") or l.startswith("CONFIG_DEVEL"))
# base settings block: from i_after_dev .. 
# find the mtwifi block: from "# ---- EasyMesh" comment or first CONFIG_MTK_ line
i_mtk_start = next(i for i, l in enumerate(base_lines) if l.startswith("CONFIG_MTK_"))
# find end of mtk block: first line after mtk block that is not CONFIG_MTK_*
j = i_mtk_start
while j < len(base_lines) and (base_lines[j].startswith("CONFIG_MTK_") or base_lines[j].startswith("#")):
    j += 1
i_mtk_end = j

settings_block = base_lines[i_after_dev:i_mtk_start]   # CONFIG_CCACHE .. pre-MTK settings
common_tail    = base_lines[i_mtk_end:]                 # openssl .. end (includes per-SoC lines)

def settings_for(soc):
    s = list(settings_block)
    if soc == "mt7988":
        s = [l for l in s
             if not l.startswith("CONFIG_CONNINFRA_")
             and not (l.startswith("#") and re.search(r"mtwifi|EasyMesh|MAP|闭源", l))]
    return s

# ---------- 3. per-SoC mtwifi blocks ----------
MTK_COMMON = [
    "CONFIG_MTK_ACK_CTS_TIMEOUT_SUPPORT=y", "CONFIG_MTK_AIR_MONITOR=y",
    "CONFIG_MTK_AMPDU_CONF_SUPPORT=y", "CONFIG_MTK_ANTENNA_CONTROL_SUPPORT=y",
    "CONFIG_MTK_APCLI_SUPPORT=y", "CONFIG_MTK_ATE_SUPPORT=y",
    "CONFIG_MTK_BACKGROUND_SCAN_SUPPORT=y", "CONFIG_MTK_CAL_BIN_FILE_SUPPORT=y",
    "CONFIG_MTK_CFG_SUPPORT_FALCON_MURU=y", "CONFIG_MTK_CFG_SUPPORT_FALCON_PP=y",
    "CONFIG_MTK_CFG_SUPPORT_FALCON_SR=y", "CONFIG_MTK_CFG_SUPPORT_FALCON_TXCMD_DBG=y",
    "CONFIG_MTK_CONNINFRA_APSOC=y", "CONFIG_MTK_CON_WPS_SUPPORT=y",
    "CONFIG_MTK_DBDC_MODE=y", "CONFIG_MTK_DOT11K_RRM_SUPPORT=y",
    "CONFIG_MTK_DOT11R_FT_SUPPORT=y", "CONFIG_MTK_DOT11W_PMF_SUPPORT=y",
    "CONFIG_MTK_DOT11_HE_AX=y", "CONFIG_MTK_DOT11_N_SUPPORT=y",
    "CONFIG_MTK_DOT11_VHT_AC=y", "CONFIG_MTK_FAST_NAT_SUPPORT=y",
    "CONFIG_MTK_FIRST_IF_EEPROM_FLASH=y", "CONFIG_MTK_FIRST_IF_IPAILNA=y",
    "CONFIG_MTK_GREENAP_SUPPORT=y", "CONFIG_MTK_G_BAND_256QAM_SUPPORT=y",
    "CONFIG_MTK_HDR_TRANS_RX_SUPPORT=y", "CONFIG_MTK_HDR_TRANS_TX_SUPPORT=y",
    "CONFIG_MTK_ICAP_SUPPORT=y", "CONFIG_MTK_IGMP_SNOOP_SUPPORT=y",
    "CONFIG_MTK_INTERWORKING=y", "CONFIG_MTK_BAND_STEERING=y",
    # ---- EasyMesh / Multi-AP 开关 ----
    "CONFIG_MTK_MAP_SUPPORT=y", "CONFIG_MTK_MAP_R2_VER_SUPPORT=y",
    "CONFIG_MTK_MAP_R3_VER_SUPPORT=y", "CONFIG_MTK_MAP_R2_6E_SUPPORT=y",
    "CONFIG_MTK_MAP_R3_6E_SUPPORT=y",
    "CONFIG_MTK_MBO_SUPPORT=y", "CONFIG_MTK_MBSS_DTIM_SUPPORT=y",
    "CONFIG_MTK_MBSS_SUPPORT=y", "CONFIG_MTK_MCAST_RATE_SPECIFIC=y",
    "CONFIG_MTK_MGMT_TXPWR_CTRL=y", "CONFIG_MTK_MLME_MULTI_QUEUE_SUPPORT=y",
    "CONFIG_MTK_MT_AP_SUPPORT=m", "CONFIG_MTK_MT_DFS_SUPPORT=y",
    "CONFIG_MTK_MT_MAC=y", "CONFIG_MTK_MT_WIFI=m", 'CONFIG_MTK_MT_WIFI_PATH="mt_wifi"',
    "CONFIG_MTK_MUMIMO_SUPPORT=y", "CONFIG_MTK_MU_RA_SUPPORT=y",
    "CONFIG_MTK_OFFCHANNEL_SCAN_FEATURE=y", "CONFIG_MTK_OWE_SUPPORT=y",
    "CONFIG_MTK_QOS_R1_SUPPORT=y", "CONFIG_MTK_RA_PHY_RATE_SUPPORT=y",
    "CONFIG_MTK_RED_SUPPORT=y", "CONFIG_MTK_RTMP_FLASH_SUPPORT=y",
    'CONFIG_MTK_RT_FIRST_CARD_EEPROM="flash"', "CONFIG_MTK_RT_FIRST_IF_RF_OFFSET=0xc0000",
    "CONFIG_MTK_SCS_FW_OFFLOAD=y", "CONFIG_MTK_SECOND_IF_NONE=y",
    "CONFIG_MTK_SMART_CARRIER_SENSE_SUPPORT=y", "CONFIG_MTK_SPECTRUM_SUPPORT=y",
    "CONFIG_MTK_SUPPORT_OPENWRT=y", "CONFIG_MTK_THIRD_IF_NONE=y",
    "CONFIG_MTK_TPC_SUPPORT=y", "CONFIG_MTK_TXBF_SUPPORT=y",
    "CONFIG_MTK_UAPSD=y", "CONFIG_MTK_VLAN_SUPPORT=y",
    "CONFIG_MTK_VOW_SUPPORT=y", "CONFIG_MTK_WARP_V2=y",
    "CONFIG_MTK_WDS_SUPPORT=y", "CONFIG_MTK_WHNAT_SUPPORT=m",
    "CONFIG_MTK_WIFI_BASIC_FUNC=y", "CONFIG_MTK_WIFI_DRIVER=y",
    "CONFIG_MTK_WIFI_EAP_FEATURE=y", "CONFIG_MTK_WIFI_FW_BIN_LOAD=y",
    "CONFIG_MTK_WIFI_MODE_AP=m", "CONFIG_MTK_WIFI_MT_MAC=y",
    "CONFIG_MTK_WIFI_TWT_SUPPORT=y", "CONFIG_MTK_WLAN_HOOK=y",
    "CONFIG_MTK_WLAN_SERVICE=y", "CONFIG_MTK_WNM_SUPPORT=y",
    "CONFIG_MTK_WPA3_SUPPORT=y", "CONFIG_MTK_WSC_INCLUDED=y",
    "CONFIG_MTK_WSC_V2_SUPPORT=y",
]

SOC_MTK = {
    "mt7981": [
        "CONFIG_MTK_CHIP_MT7981=y", "CONFIG_MTK_CONNINFRA_APSOC_MT7981=y",
        "CONFIG_MTK_FIRST_IF_MT7981=y", "CONFIG_MTK_MT7981_NEW_FW=y",
        "CONFIG_MTK_MEMORY_SHRINK=y", "CONFIG_MTK_MEMORY_SHRINK_AGGRESS=y",
    ],
    "mt7986": [
        "CONFIG_MTK_CHIP_MT7986=y", "CONFIG_MTK_CONNINFRA_APSOC_MT7986=y",
        "CONFIG_MTK_FIRST_IF_MT7986=y", "CONFIG_MTK_MT7986_NEW_FW=y",
        "CONFIG_MTK_THERMAL_PROTECT_SUPPORT=y", "CONFIG_MTK_PHY_ICS_SUPPORT=y",
        'CONFIG_MTK_WIFI_ADIE_TYPE="mt7976"', 'CONFIG_MTK_WIFI_SKU_TYPE="AX6000"',
    ],
    "mt7988": [],
}

# ---------- 4. tail replacements ----------
def tail_for(soc):
    tail = list(common_tail)
    if soc == "mt7981":
        tail = [l.replace('CONFIG_WARP_CHIPSET="mt7986"', 'CONFIG_WARP_CHIPSET="mt7981"')
                 .replace('CONFIG_first_card_name="MT7986"', 'CONFIG_first_card_name="MT7981"')
                for l in tail]
    if soc == "mt7988":
        drop_prefixes = (
            "CONFIG_PACKAGE_kmod-mt_wifi=", "CONFIG_PACKAGE_kmod-warp=",
            "CONFIG_PACKAGE_kmod-mediatek_hnat=", "CONFIG_PACKAGE_kmod-conninfra=",
            "CONFIG_PACKAGE_luci-app-eqos-mtk=", "CONFIG_PACKAGE_luci-app-mtwifi-cfg=",
            "CONFIG_PACKAGE_mtwifi-wapp=", "CONFIG_PACKAGE_mtwifi-cfg=",
            "CONFIG_PACKAGE_luci-i18n-eqos-mtk-zh-cn=", "CONFIG_PACKAGE_luci-i18n-mtwifi-cfg-zh-cn=",
            "CONFIG_CONNINFRA_", "CONFIG_WARP_CHIPSET=", "CONFIG_WARP_DBG_SUPPORT=",
            "CONFIG_WARP_MEMORY_LEAK_DBG=", "CONFIG_WARP_NEW_FW=",
            "CONFIG_WARP_VERSION=", "CONFIG_WED_HW_RRO_SUPPORT=",
            "CONFIG_first_card=", "CONFIG_first_card_name=",
        )
        tail = [l for l in tail
                if not l.startswith(drop_prefixes)
                and not (l.startswith("#") and re.search(r"mtwifi|EasyMesh|wapp|luci-app-mtk", l))]
    return tail

def target_block(soc, dev_list):
    out = []
    out.append("CONFIG_TARGET_mediatek=y")
    out.append("CONFIG_TARGET_mediatek_%s=y" % soc)   # 占位(实际由设备符号确定 filogic)
    out.append("CONFIG_TARGET_MULTI_PROFILE=y")
    out.append("CONFIG_TARGET_PER_DEVICE_ROOTFS=y")
    out.append("CONFIG_HAS_SUBTARGETS=y")
    for d in dev_list:
        out.append("CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_%s=y" % d)
        out.append('CONFIG_TARGET_DEVICE_PACKAGES_mediatek_filogic_DEVICE_%s=""' % d)
    return out

SOC_HEAD = {
    "mt7981": "MT7981 (MTK Filogic 820) 全设备 %d 台 — mtwifi 闭源 7.6.6.1 + EasyMesh",
    "mt7986": "MT7986 (MTK Filogic 830) 全设备 %d 台 — mtwifi 闭源 7.6.6.1 + EasyMesh",
    "mt7988": "MT7988 (MTK Filogic 880) 全设备 %d 台 — 使用开源 mt76 无线驱动(mtwifi 闭源驱动不支持 MT7988)",
}

def build(soc):
    dev_list = by_soc[soc]
    body = []
    body.append("# ============================================================")
    body.append("# ImmortalWrt 24.10 (kernel 6.6) — %s" % (SOC_HEAD[soc] % len(dev_list)))
    body.append("# 插件: turboacc-mtk / AdGuardHome / SmartDNS / OpenClash / Argon 主题")
    if soc != "mt7988":
        body.append("# EasyMesh: mtwifi-wapp (MAP R2/R3, 802.11k/v/r, Band Steering)")
    body.append("# 用法: cp -f defconfig/%s-all.config .config && make" % soc)
    body.append("# ============================================================")
    body += target_block(soc, dev_list)
    body.append("")
    body += settings_for(soc)
    body.append("")
    body.append("# ------------------------------------------------------------")
    body.append("# mtwifi 闭源驱动 —— EasyMesh / MAP (核心)   [%s]" % soc)
    body.append("# ------------------------------------------------------------")
    if soc == "mt7988":
        body.append("# MT7988 无内置 WiFi, mtwifi 闭源驱动不支持; 无线使用设备自带的开源 mt76 驱动 + 固件包(由设备 DEVICE_PACKAGES 自动选择)")
        body.append("# 如需 EasyMesh, 请选用 mt7981-all.config / mt7986-all.config")
    else:
        body += MTK_COMMON + SOC_MTK[soc]
    body.append("")
    tail = tail_for(soc)
    body += tail
    out = "\n".join(body) + "\n"
    # 合并重复的分隔注释行
    sep = "# ------------------------------------------------------------"
    while "\n%s\n%s\n" % (sep, sep) in out:
        out = out.replace("\n%s\n%s\n" % (sep, sep), "\n%s\n" % sep)
    return out

for soc in ("mt7981", "mt7986", "mt7988"):
    path = os.path.join(BASE, "defconfig/%s-all.config" % soc)
    with open(path, "w", encoding="utf-8") as f:
        f.write(build(soc))
    print("wrote %s  (%d devices)" % (path, len(by_soc[soc])))
