# SPDX-Identifier-License: GPL-3.0-only
#
# LuCI application for MediaTek EasyMesh (MAP) based on mtwifi-cfg / wapp.

include $(TOPDIR)/rules.mk

PKG_LICENSE:=GPL-3.0-only

LUCI_TITLE:=LuCI support for MTK EasyMesh (MAP / wapp)
LUCI_DEPENDS:=+mtwifi-cfg +mtwifi-wapp +lua-cjson
LUCI_PKGARCH:=all

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature
