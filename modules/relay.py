# -*- coding: utf-8 -*-

import sys
from collections import namedtuple

from modules.mylogging import *

relaybindings = []
RelayBinding = namedtuple('RelayBinding', ['type', 'name', 'callback'])
RelayTarget = namedtuple('RelayTarget', ['type', 'name', 'channel', 'prefix', 'what', 'extra'])

def bind(type, name, callback):
	global relaybindings
	targ = RelayBinding(type, name, callback)
	if not targ in relaybindings:
		relaybindings.append(targ)
		log.log(LOG_DEBUG, 'Bound relay (type:' + type + ', name:' + name + ')')

def unbind(type, name, callback):
	global relaybindings
	targ = RelayBinding(type, name, callback)
	if targ in relaybindings:
		relaybindings.remove(targ)
		log.log(LOG_DEBUG, 'Unbound relay (type:' + type + ', name:' + name + ')')

def call(type, name, channel, args):
	global relaybindings
	log.log(LOG_DEBUG, 'Attempting to call relays (type:' + type + ', name:' + name + ', channel:' + channel + ', args:' + str(args) + ')')
	for targ in relaybindings:
		if targ.type == type and targ.name == name:
			if targ.callback != None:
				log.log(LOG_DEBUG, 'Calling relay (type:' + type + ', name:' + name + ')')
				targ.callback(channel, args)
