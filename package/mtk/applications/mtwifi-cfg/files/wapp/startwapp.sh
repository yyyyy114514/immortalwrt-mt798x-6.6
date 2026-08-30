#!/bin/sh
# startwapp.sh - EasyMesh (MAP/wapp/bs20) 启动脚本
# 方案: wifi-profile + luci-app-mtk (l1profile.dat / dbdc dat), 无 UCI wireless
# 数据源:
#   /etc/wireless/l1profile.dat           -> 射频接口列表 (INDEX*_main_ifname)
#   /etc/wireless/mediatek/*.dbdc.bN.dat  -> MapEnable 等 EasyMesh 开关

LOG_TAG="wapp"

log_i() {
    logger -t "$LOG_TAG" "INFO: $*"
}

log_e() {
    logger -t "$LOG_TAG" "ERROR: $*"
}

run_cmd() {
    log_i "exec: $*"
    "$@"
    local rc=$?
    if [ "$rc" -eq 0 ]; then
        log_i "ok($rc): $*"
    else
        log_e "fail($rc): $*"
    fi
    return "$rc"
}

run_bg() {
    log_i "exec(bg): $*"
    "$@" >/dev/null 2>&1 &
    log_i "started pid=$!: $*"
}

L1PROFILE=/etc/wireless/l1profile.dat
DAT_DIR=/etc/wireless/mediatek

log_i "startwapp.sh (wifi-profile) start"

run_cmd sh -c "killall bs20 2>/dev/null || true"
run_cmd sh -c "killall wapp 2>/dev/null || true"

br0_mac=$(cat /sys/class/net/br-lan/address 2>/dev/null)
ctrlr_al_mac=$br0_mac
agent_al_mac=$br0_mac

log_i "bridge mac: ${br0_mac}"

# 读取 dat 中某频段字段 (band 为 0 起始的频段序号)
dat_get() {
    local band=$1 field=$2 dat
    dat=$(ls "$DAT_DIR"/*.dbdc.b${band}.dat 2>/dev/null | head -1)
    [ -n "$dat" ] && sed -n "s/^${field}=//p" "$dat" | head -1
}

# 射频接口列表 (main_ifname=ra0;rax0), 按 ';' 拆分
IFNAMES=$(sed -n 's/^INDEX[0-9]*_main_ifname=//p' "$L1PROFILE" 2>/dev/null | tr ';' ' ')
[ -n "$IFNAMES" ] || IFNAMES="ra0"

# 第一遍: 依据各频段 MapEnable 决定是否启动 wapp
wapp_enabled=0
band=0
for ifname in $IFNAMES; do
    map_enable=$(dat_get "$band" MapEnable)
    log_i "band=${band} if=${ifname} MapEnable=${map_enable}"
    if [ -n "$map_enable" ] && [ "$map_enable" != "0" ]; then
        wapp_enabled=1
        eval "map_${band}=1"
    fi
    band=$((band+1))
done

if [ "$wapp_enabled" -ne "1" ]; then
    log_i "EasyMesh 未启用 (各频段 MapEnable=0), exit"
    exit 0
fi

log_i "EasyMesh enabled, continue"

sleep 2

run_cmd sed -i "s/map_controller_alid=.*/map_controller_alid=${ctrlr_al_mac}/g" /etc/map/1905d.cfg
run_cmd sed -i "s/map_agent_alid=.*/map_agent_alid=${agent_al_mac}/g" /etc/map/1905d.cfg

# 第二遍: 组装 wapp 参数, 并对启用频段下发驱动 iwpriv
wapp_args=""
band=0
for ifname in $IFNAMES; do
    enabled=0
    eval "enabled=\${map_${band}:-0}"
    if [ "$enabled" -eq "1" ]; then
        wapp_args="${wapp_args} -c${ifname}"
        run_cmd iwpriv "$ifname" set mapEnable=2
        run_cmd iwpriv "$ifname" set mapR2Enable=0
        run_cmd iwpriv "$ifname" set mapTSEnable=0
        run_cmd iwpriv "$ifname" set mapR3Enable=0
        run_cmd iwpriv "$ifname" set DppEnable=0
    fi
    band=$((band+1))
done

log_i "wapp_args: ${wapp_args}"

if [ -n "$wapp_args" ]; then
    # shellcheck disable=SC2086
    run_bg wapp -d1 -v2 $wapp_args
    sleep 1
    run_bg bs20
    band=0
    for ifname in $IFNAMES; do
        enabled=0
        eval "enabled=\${map_${band}:-0}"
        if [ "$enabled" -eq "1" ]; then
            run_cmd wappctrl "$ifname" mbo reset_default
        fi
        band=$((band+1))
    done
fi

log_i "startwapp.sh done"
