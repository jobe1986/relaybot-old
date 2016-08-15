# -*- coding: utf-8 -*-

# RelayBot - Simple Multi-protocol Relay Bot, core/relay.py
#
# Copyright (C) 2016 Matthew Beeching
#
# This file is part of RelayBot.
#
# RelayBot is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RelayBot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RelayBot.  If not, see <http://www.gnu.org/licenses/>.

import sys
from collections import namedtuple

from core.rblogging import *

relaybindings = []
RelayBinding = namedtuple('RelayBinding', ['type', 'name', 'callback'])
RelayTarget = namedtuple('RelayTarget', ['type', 'name', 'channel', 'extra', 'filters'])
RelaySource = namedtuple('RelaySource', ['type', 'name', 'channel', 'extra'])
RelayData = namedtuple('RelayData', ['text', 'source', 'target', 'extra'])

def bind(type, name, callback):
	global relaybindings
	targ = RelayBinding(type, name, callback)
	if not targ in relaybindings:
		relaybindings.append(targ)
		log.log(LOG_DEBUG, 'Bound relay (type:' + type + ', name:' + name + ')')
		return targ

def unbind(type, name, callback):
	global relaybindings
	for bind in relaybindings:
		if bind.type != type:
			continue
		if bind.name != name:
			continue
		if bind.callback != callback:
			continue
		relaybindings.remove(bind)
		log.log(LOG_DEBUG, 'Unbound relay (type:' + type + ', name:' + name + ')')
		break

def call(text, target, source, extra):
	global relaybindings
	data = RelayData(text, source, target, extra)
	log.log(LOG_DEBUG, 'Attempting to call relays (type:' + target.type + ', name:' + target.name + ', channel:' + target.channel + ')')
	if target.filters != None and len(target.filters) > 0:
		matched = False
		for filt in target.filters:
			try:
				if not hasattr(filt, 'filter'):
					log.log(LOG_ERROR, 'Filter without filter() method: ' + str(filt))
					continue
				ret = filt.filter(data)
				if ret != None:
					matched = True
					data = ret
			except Exception as e:
				log.log(LOG_ERROR, 'Error testing filter ' + str(filt) + ' for relay data: ' + str(e))
				return
		if not matched:
			return
	for bind in relaybindings:
		if bind.type == target.type and bind.name == target.name:
			if bind.callback != None:
				log.log(LOG_DEBUG, 'Calling relay (type:' + bind.type + ', name:' + bind.name + ')')
				bind.callback(data)
