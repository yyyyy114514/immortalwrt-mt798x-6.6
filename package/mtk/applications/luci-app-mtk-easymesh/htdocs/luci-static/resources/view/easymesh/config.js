'use strict';
'require form';
'require rpc';
'require uci';
'require ui';
'require view';

var callGetConfig = rpc.declare({
	object: 'luci.easymesh',
	method: 'getConfig',
	expect: { '': {} }
});

var callGetStatus = rpc.declare({
	object: 'luci.easymesh',
	method: 'getStatus',
	expect: { '': {} }
});

var callApplyConfig = rpc.declare({
	object: 'luci.easymesh',
	method: 'applyConfig',
	expect: { '': {} }
});

var callResetDefault = rpc.declare({
	object: 'luci.easymesh',
	method: 'resetDefault',
	expect: { '': {} }
});

var callPbcTrigger = rpc.declare({
	object: 'luci.easymesh',
	method: 'pbcTrigger',
	params: [ 'iface' ],
	expect: { '': {} }
});

var callDppUriAdd = rpc.declare({
	object: 'luci.easymesh',
	method: 'dppUriAdd',
	params: [ 'uri' ],
	expect: { '': {} }
});

var callDppUriShow = rpc.declare({
	object: 'luci.easymesh',
	method: 'dppUriShow',
	expect: { '': {} }
});

return view.extend({
	load: function() {
		return Promise.all([
			uci.load('easymesh'),
			L.resolveDefault(callGetConfig(), {}),
			L.resolveDefault(callGetStatus(), {})
		]);
	},

	handleSave: function(ev) {
		return this.super('handleSave', ev).then(function() {
			return L.resolveDefault(callApplyConfig(), {}).then(function(res) {
				ui.addNotification(null, E('p', {}, res.enabled == '1'
					? _('EasyMesh configuration applied, wapp has been restarted.')
					: _('EasyMesh has been disabled, wapp has been stopped.')));
			});
		});
	},

	render: function(data) {
		var cfg = data[1] || {};
		var status = data[2] || {};
		var m, s, o;

		m = new form.Map('easymesh', _('EasyMesh Configurations'),
			_('Configure MTK EasyMesh (MAP / wapp) on this device.'));

		s = m.section(form.NamedSection, 'config', 'easymesh');
		s.tab('basic', _('Basic'));
		s.tab('advanced', _('Advanced'));
		s.tab('status', _('Status'));
		s.tab('mapqos', _('MAP QoS'));

		o = s.taboption('basic', form.Flag, 'enabled', _('Enable EasyMesh'),
			_('Master switch. When enabled, the wapp/bs20 daemons are started and the radios join the MAP network.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('basic', form.ListValue, 'mode', _('EasyMesh Mode'),
			_('MAP turnkey operating mode written to mapd_cfg.'));
		o.value('0', _('Disabled'));
		o.value('1', _('Controller'));
		o.value('2', _('Agent'));
		o.value('3', _('Controller + Agent'));
		o.default = '0';
		o.rmempty = false;

		o = s.taboption('basic', form.ListValue, 'device_mode', _('Set Device Mode as'),
			_('Device mode of this unit.'));
		o.value('router', _('Router'));
		o.value('extender', _('Extender'));
		o.default = 'router';
		o.rmempty = false;

		o = s.taboption('basic', form.DummyValue, '_cur_mode', _('Current Device Mode'));
		o.cfgvalue = function() {
			return cfg.cur_mode;
		};

		o = s.taboption('basic', form.ListValue, 'device_role', _('Set Device Role as'),
			_('Controller (MAP root) or Agent (MAP repeater).'));
		o.value('controller', _('Controller'));
		o.value('agent', _('Agent'));
		o.default = 'controller';
		o.rmempty = false;

		o = s.taboption('basic', form.DummyValue, '_cur_role', _('Current Device Role'));
		o.cfgvalue = function() {
			return cfg.cur_role;
		};

		o = s.taboption('basic', form.Button, '_reset_default', _('Reset EasyMesh Settings to default'));
		o.inputtitle = _('Load Default Settings');
		o.inputstyle = 'reset';
		o.onclick = function() {
			return L.resolveDefault(callResetDefault(), {}).then(function() {
				location.reload();
			});
		};

		o = s.taboption('basic', form.Button, '_pbc', _('PBC On-boarding'),
			_('Trigger WPS push-button on-boarding for MAP agents.'));
		o.inputtitle = _('Trigger Wi-Fi On-boarding');
		o.inputstyle = 'apply';
		o.onclick = function() {
			return L.resolveDefault(callPbcTrigger('ra0'), {}).then(function() {
				ui.addNotification(null, E('p', {}, _('Wi-Fi on-boarding (PBC) has been triggered.')));
			});
		};

		o = s.taboption('basic', form.Value, 'dpp_uri', _('Add DPP URI'),
			_('Paste a DPP bootstrap URI to be written to mapd_cfg.'));
		o.optional = true;

		o = s.taboption('basic', form.Button, '_dpp_submit', _('Submit DPP URI'));
		o.inputtitle = _('Submit DPP URI');
		o.inputstyle = 'apply';
		o.onclick = function(ev, section_id) {
			var uri = s.formvalue(section_id, 'dpp_uri');
			if (!uri) {
				ui.addNotification(null, E('p', {}, _('Please enter a DPP URI first.')));
				return;
			}
			return L.resolveDefault(callDppUriAdd(uri), {}).then(function() {
				ui.addNotification(null, E('p', {}, _('DPP URI has been submitted.')));
			});
		};

		o = s.taboption('basic', form.Button, '_dpp_show', _('Display Bootstrapping URIs'));
		o.inputtitle = _('Display Bootstrapping URIs');
		o.inputstyle = 'button';
		o.onclick = function() {
			return L.resolveDefault(callDppUriShow(), {}).then(function(res) {
				ui.showModal(_('Bootstrapping URIs'), [
					E('p', {}, E('code', { 'style': 'white-space:pre-wrap;word-break:break-all' },
						res.uri || res.output || _('No URI available.'))),
					E('div', { 'class': 'right' },
						E('button', { 'class': 'cbi-button', 'click': ui.hideModal }, [ _('Dismiss') ]))
				]);
			});
		};

		o = s.taboption('basic', form.Button, '_topology', _('Runtime Topology'));
		o.inputtitle = _('Display Runtime Topology');
		o.inputstyle = 'button';
		o.onclick = function() {
			location.href = L.url('admin/network/easymesh/topology');
		};

		o = s.taboption('advanced', form.Flag, 'mesh_sr', _('Mesh SR'),
			_('Enable mesh seamless roaming (ieee80211r / fast transition) on the radios.'));
		o.default = o.enabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'bandsteering', _('Band Steering'),
			_('Enable band steering on mtwifi radios (synced to wireless UCI).'));
		o.default = o.enabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'steeringthresold', _('Steering RSSI Threshold'),
			_('steeringthresold applied to every AP interface (dBm).'));
		o.datatype = 'integer';
		o.default = '-65';
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'steer_rssi_th', _('AP Steering RSSI Threshold'),
			_('APSteerRssiTh in mapd_cfg (dBm).'));
		o.datatype = 'integer';
		o.default = '-54';
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'roam_rssi_th', _('Force Roam RSSI Threshold'),
			_('force_roam_rssi_th in mapd_cfg (dBm).'));
		o.datatype = 'integer';
		o.default = '-70';
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'lr_steer_edge', _('Low RSSI Steering Edge'),
			_('LowRSSIAPSteerEdge_RE in mapd_cfg.'));
		o.datatype = 'uinteger';
		o.default = '25';
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'scan_th_2g', _('Scan Threshold 2.4G'),
			_('ScanThreshold2g in mapd_cfg (dBm).'));
		o.datatype = 'integer';
		o.default = '-88';
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'scan_th_5g', _('Scan Threshold 5G'),
			_('ScanThreshold5g in mapd_cfg (dBm).'));
		o.datatype = 'integer';
		o.default = '-88';
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'scan_th_6g', _('Scan Threshold 6G'),
			_('ScanThreshold6g in mapd_cfg (dBm).'));
		o.datatype = 'integer';
		o.default = '-88';
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'bh_steer_timeout', _('Backhaul Steering Timeout'),
			_('BHSteerTimeout in mapd_cfg (seconds).'));
		o.datatype = 'uinteger';
		o.default = '120';
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'centralized_steering', _('Centralized Steering'),
			_('CentralizedSteering in mapd_cfg.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'auto_bh_switch', _('Auto Backhaul Switch'),
			_('AutoBHSwitching in mapd_cfg: allow automatic backhaul link switching.'));
		o.default = o.enabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'bh_prio_2g', _('Backhaul Priority 2.4G'),
			_('BhPriority2G in mapd_cfg: allow 2.4G as backhaul.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'bh_prio_5gl', _('Backhaul Priority 5G Low'),
			_('BhPriority5GL in mapd_cfg: allow 5G low band as backhaul.'));
		o.default = o.enabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'bh_prio_5gh', _('Backhaul Priority 5G High'),
			_('BhPriority5GH in mapd_cfg: allow 5G high band as backhaul.'));
		o.default = o.enabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'bh_prio_6g', _('Backhaul Priority 6G'),
			_('BhPriority6G in mapd_cfg: allow 6G as backhaul.'));
		o.default = o.enabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'dual_bh', _('Dual Backhaul'),
			_('DualBH in mapd_cfg. Leave empty to disable dual backhaul.'));
		o.optional = true;

		o = s.taboption('advanced', form.Value, 'bss_prio', _('BSS Config Priority'),
			_('bss_config_priority: semicolon separated BSS bring-up order (mapd_cfg and 1905d.cfg).'));
		o.default = 'ra0;rax0;apclix0';
		o.rmempty = false;

		o = s.taboption('advanced', form.ListValue, 'bh_type', _('Backhaul Type'),
			_('bh_type in 1905d.cfg.'));
		o.value('eth', _('Ethernet backhaul'));
		o.value('wifi', _('Wireless backhaul'));
		o.default = 'eth';
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'non_map_ap', _('Non-MAP AP Support'),
			_('NonMAPAPEnable in mapd_cfg: allow non-MAP APs in the network.'));
		o.default = o.enabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'third_party', _('Third Party Connection'),
			_('ThirdPartyConnection in mapd_cfg.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'role_detect_ext', _('External Role Detection'),
			_('role_detection_external in mapd_cfg.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'dhcp_ctl', _('DHCP Control'),
			_('DhcpCtl in mapd_cfg: controller-side DHCP handling for agents.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'quick_ch_change', _('Quick Channel Change'),
			_('MAP_QuickChChange in mapd_cfg.'));
		o.default = o.enabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'metric_interval', _('Metric Report Interval'),
			_('MetricRepIntv in mapd_cfg (seconds).'));
		o.datatype = 'uinteger';
		o.default = '60';
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'psc_6g', _('PSC Channel on 6G'),
			_('SetPSCChannel_6G in mapd_cfg: restrict 6G to PSC channels.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'decrypt_fail_th', _('Decrypt Fail Threshold'),
			_('decrypt_fail_threshold in 1905d.cfg.'));
		o.datatype = 'uinteger';
		o.default = '10';
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'gtk_rekey', _('GTK Rekey Interval'),
			_('gtk_rekey_interval in 1905d.cfg (seconds).'));
		o.datatype = 'uinteger';
		o.default = '3600';
		o.rmempty = false;

		o = s.taboption('advanced', form.Flag, 'ob_wan_only', _('Onboarding over WAN'),
			_('ob_wan_only in 1905d.cfg: restrict onboarding traffic to the WAN interface.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'br_inf', _('Bridge Interface'),
			_('br_inf in 1905d.cfg: bridge used by the MAP AL entity.'));
		o.default = 'br-lan';
		o.rmempty = false;

		o = s.taboption('advanced', form.Value, 'radio_band', _('Radio Band Layout'),
			_('radio_band in 1905d.cfg: semicolon separated band per radio (e.g. 24G;5G;5G;).'));
		o.default = '24G;5G;5G;';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Flag, 'steering', _('Steering'),
			_('Enable MAP steering (SteerEnable in mapd_cfg).'));
		o.default = o.enabled;
		o.rmempty = false;

		o = s.taboption('mapqos', form.Flag, 'ch_plan_enable', _('Channel Planning'),
			_('ChPlanningEnable in mapd_cfg: controller-driven channel planning.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'ch_plan_init_timeout', _('Channel Planning Init Timeout'),
			_('ChPlanningInitTimeout in mapd_cfg (seconds).'));
		o.datatype = 'uinteger';
		o.default = '120';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'ch_plan_scan_valid', _('Channel Planning Scan Valid'),
			_('ChPlanningScanValidTime in mapd_cfg (seconds).'));
		o.datatype = 'uinteger';
		o.default = '14400';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'ch_plan_ch_2g', _('Preferred Channels 2.4G'),
			_('ChPlanningUserPreferredChannel2G: comma separated channel list, empty for automatic.'));
		o.optional = true;

		o = s.taboption('mapqos', form.Value, 'ch_plan_ch_5gl', _('Preferred Channels 5G Low'),
			_('ChPlanningUserPreferredChannel5G: comma separated channel list, empty for automatic.'));
		o.optional = true;

		o = s.taboption('mapqos', form.Value, 'ch_plan_ch_5gh', _('Preferred Channels 5G High'),
			_('ChPlanningUserPreferredChannel5GH: comma separated channel list, empty for automatic.'));
		o.optional = true;

		o = s.taboption('mapqos', form.Value, 'ch_plan_ch_6g', _('Preferred Channels 6G'),
			_('ChPlanningUserPreferredChannel6G: comma separated channel list, empty for automatic.'));
		o.optional = true;

		o = s.taboption('mapqos', form.Flag, 'divergent_ch_plan', _('Divergent Channel Planning'),
			_('DivergentChPlanning in mapd_cfg.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('mapqos', form.Flag, 'nop_enable', _('Network Optimization'),
			_('NetworkOptimizationEnabled in mapd_cfg.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'nop_bootup_wait', _('NOP Bootup Wait'),
			_('NtwrkOptBootupWaitTime in mapd_cfg (seconds).'));
		o.datatype = 'uinteger';
		o.default = '45';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'nop_connect_wait', _('NOP Connect Wait'),
			_('NtwrkOptConnectWaitTime in mapd_cfg (seconds).'));
		o.datatype = 'uinteger';
		o.default = '45';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'nop_disconnect_wait', _('NOP Disconnect Wait'),
			_('NtwrkOptDisconnectWaitTime in mapd_cfg (seconds).'));
		o.datatype = 'uinteger';
		o.default = '45';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'nop_periodicity', _('NOP Periodicity'),
			_('NtwrkOptPeriodicity in mapd_cfg (seconds).'));
		o.datatype = 'uinteger';
		o.default = '3600';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'nop_score_margin', _('NOP Score Margin'),
			_('NetworkOptimizationScoreMargin in mapd_cfg.'));
		o.datatype = 'uinteger';
		o.default = '100';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Flag, 'nop_prefer_5g', _('NOP Prefer 5G over 2G'),
			_('NetworkOptPrefer5Gover2G in mapd_cfg.'));
		o.default = o.disabled;
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'nop_prefer_5g_retry', _('NOP Prefer 5G Retry Count'),
			_('NetworkOptPrefer5Gover2GRetryCnt in mapd_cfg.'));
		o.datatype = 'uinteger';
		o.default = '0';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'nop_post_cac', _('NOP Post-CAC Trigger'),
			_('NtwrkOptPostCACTriggerTime in mapd_cfg (seconds).'));
		o.datatype = 'uinteger';
		o.default = '30';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'nop_data_collect', _('NOP Data Collection Time'),
			_('NtwrkOptDataCollectionTime in mapd_cfg (seconds).'));
		o.datatype = 'uinteger';
		o.default = '60';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'nop_user_prio', _('NOP User Priority'),
			_('NetOptUserSetPriority in mapd_cfg.'));
		o.datatype = 'uinteger';
		o.default = '0';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'cu_th_2g', _('CU Overload Threshold 2.4G'),
			_('CUOverloadTh_2G in mapd_cfg (percent).'));
		o.datatype = 'range(0, 100)';
		o.default = '70';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'cu_th_5gl', _('CU Overload Threshold 5G Low'),
			_('CUOverloadTh_5G_L in mapd_cfg (percent).'));
		o.datatype = 'range(0, 100)';
		o.default = '80';
		o.rmempty = false;

		o = s.taboption('mapqos', form.Value, 'cu_th_5gh', _('CU Overload Threshold 5G High'),
			_('CUOverloadTh_5G_H in mapd_cfg (percent).'));
		o.datatype = 'range(0, 100)';
		o.default = '80';
		o.rmempty = false;

		o = s.taboption('status', form.DummyValue, '_wapp', _('wapp daemon'));
		o.cfgvalue = function() {
			return status.wapp_running ? _('Running') : _('Stopped');
		};

		o = s.taboption('status', form.DummyValue, '_bs20', _('bs20 daemon'));
		o.cfgvalue = function() {
			return status.bs20_running ? _('Running') : _('Stopped');
		};

		o = s.taboption('status', form.DummyValue, '_almac', _('AL MAC'));
		o.cfgvalue = function() {
			return status.al_mac || '-';
		};

		o = s.taboption('status', form.DummyValue, '_mapver', _('MAP version'));
		o.cfgvalue = function() {
			return status.map_ver || '-';
		};

		o = s.taboption('status', form.DummyValue, '_role', _('Device Role'));
		o.cfgvalue = function() {
			return status.device_role || '-';
		};

		o = s.taboption('status', form.DummyValue, '_calid', _('Controller ALID'));
		o.cfgvalue = function() {
			return status.controller_alid || '-';
		};

		o = s.taboption('status', form.DummyValue, '_aalid', _('Agent ALID'));
		o.cfgvalue = function() {
			return status.agent_alid || '-';
		};

		o = s.taboption('status', form.DummyValue, '_radios', _('Radios'));
		o.cfgvalue = function() {
			var radios = status.radios || [];
			if (!radios.length)
				return '-';
			return radios.map(function(r) {
				return '%s (%s, ch %s)'.format(r.name, r.band || '?', r.channel || '?');
			}).join(', ');
		};

		return m.render();
	}
});
