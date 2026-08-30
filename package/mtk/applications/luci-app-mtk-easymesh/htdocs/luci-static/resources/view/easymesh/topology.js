'use strict';
'require poll';
'require rpc';
'require ui';
'require view';

var callGetTopology = rpc.declare({
	object: 'luci.easymesh',
	method: 'getTopology',
	expect: { '': {} }
});

var showAll = false;

function roleText(role) {
	return role == 'controller' ? _('Controller')
		: role == 'agent' ? _('Agent')
		: role == 'auto' ? _('Auto')
		: role == 'router' ? _('Router')
		: role == 'bridge' ? _('Bridge')
		: role == 'unknown' ? _('Unknown')
		: (role || '-');
}

function roleColor(role) {
	return (role == 'agent') ? '#e8912d'
		: (role == 'controller') ? '#2f6fd0'
		: '#808894';
}

function nodeBox(title, lines, color) {
	var kids = [
		E('div', { 'style': 'font-weight:bold;color:%s;margin-bottom:6px'.format(color) }, title)
	];
	for (var i = 0; i < lines.length; i++)
		kids.push(E('div', { 'style': 'font-size:12px;line-height:1.6' }, lines[i]));

	return E('div', {
		'style': 'display:inline-block;vertical-align:top;margin:6px;padding:10px 14px;' +
			'border:2px solid %s;border-radius:8px;background:#fff;min-width:190px'.format(color)
	}, kids);
}

function renderTopology(topo) {
	topo = topo || {};
	var role = topo.device_role || 'auto';
	var color = roleColor(role);
	var children = [];

	if (!topo.wapp_running)
		children.push(E('div', { 'class': 'alert-message warning', 'style': 'margin-bottom:12px' },
			_('wapp is not running. Enable EasyMesh and apply the configuration first.')));

	var devLines = [
		'%s: %s'.format(_('Role'), roleText(role)),
		'%s: %s'.format(_('Mode'), roleText(topo.device_mode)),
		'%s: %s'.format(_('AL MAC'), topo.al_mac || '-'),
		'%s: %s'.format(_('MAP version'), topo.map_ver || '-')
	];
	if (showAll) {
		devLines.push('%s: %s'.format(_('Controller ALID'), topo.controller_alid || '-'));
		devLines.push('%s: %s'.format(_('Agent ALID'), topo.agent_alid || '-'));
	}
	children.push(nodeBox(_('This Device'), devLines, color));

	var radios = topo.radios || [];
	if (radios.length) {
		children.push(E('div', { 'style': 'margin:12px 0 4px' }, radios.map(function(r) {
			var lines = [
				'%s: %s'.format(_('Band'), r.band || '-'),
				'%s: %s'.format(_('Channel'), r.channel || '-')
			];
			if (showAll)
				lines.push('%s: %s'.format(_('DBDC main'), r.dbdc_main || '0'));
			return nodeBox('%s: %s'.format(_('Radio'), r.name), lines, '#808894');
		})));
	}

	var stas = topo.stations || [];
	children.push(E('h3', { 'style': 'margin-top:16px' },
		'%s (%d)'.format(_('Connected Stations'), stas.length)));

	if (!stas.length) {
		children.push(E('div', {}, E('em', {}, _('No stations associated.'))));
	} else {
		children.push(E('div', {}, stas.map(function(st) {
			var lines = [ '%s: %s dBm'.format(_('RSSI'), st.rssi || '?') ];
			if (showAll) {
				lines.push('%s: %s'.format(_('Radio'), st.radio || '-'));
				lines.push('%s: %s'.format(_('Interface'), st.ifname || '-'));
				lines.push('%s: %s'.format(_('Band'), st.band || '-'));
			}
			return nodeBox(st.mac || _('Unknown'), lines, '#3a9a3a');
		})));
	}

	return E('div', {}, children);
}

function update(container) {
	return L.resolveDefault(callGetTopology(), {}).then(function(topo) {
		container.innerHTML = '';
		container.appendChild(renderTopology(topo));
	});
}

return view.extend({
	handleSave: null,
	handleSaveApply: null,
	handleReset: null,

	load: function() {
		return L.resolveDefault(callGetTopology(), {});
	},

	render: function(topo) {
		var container = E('div', { 'id': 'easymesh-topology' }, renderTopology(topo));

		var toolbar = E('div', { 'style': 'margin-bottom:14px' }, [
			E('button', {
				'class': 'cbi-button cbi-button-apply',
				'click': function(ev) {
					showAll = !showAll;
					ev.currentTarget.textContent = showAll
						? _('Hide detailed info') : _('Show all device info');
					return update(container);
				}
			}, [ _('Show all device info') ]),
			' ',
			E('button', {
				'class': 'cbi-button',
				'click': function() {
					return update(container);
				}
			}, [ _('Refresh') ])
		]);

		poll.add(function() {
			return update(container);
		});

		return E('div', {}, [
			E('h2', {}, _('EasyMesh Run-time Topology Display')),
			toolbar,
			container
		]);
	}
});
