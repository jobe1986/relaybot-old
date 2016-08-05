# -*- coding: utf-8 -*-

import sys
from collections import namedtuple

from core.rblogging import *

relaybindings = []
RelayBinding = namedtuple('RelayBinding', ['type', 'name', 'callback'])
RelayTarget = namedtuple('RelayTarget', ['type', 'name', 'channel', 'extra'])
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
	log.log(LOG_DEBUG, 'Attempting to call relays (' + str(data) + ')')
	for bind in relaybindings:
		if bind.type == target.type and bind.name == target.name:
			if bind.callback != None:
				log.log(LOG_DEBUG, 'Calling relay (type:' + bind.type + ', name:' + bind.name + ')')
				bind.callback(data)
