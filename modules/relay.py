# -*- coding: utf-8 -*-

import sys
from collections import namedtuple

from modules.mylogging import *

RelayBindings = []
RelayBinding = namedtuple('RelayBinding', ['type', 'name', 'callback'])
RelayTarget = namedtuple('RelayTarget', ['type', 'name', 'channel', 'prefix'])

def bind(type, name, callback):
	global RelayBindings
	targ = RelayBinding(type, name, callback)
	if not targ in RelayBindings:
		RelayBindings.append(targ)
		log.log(LOG_DEBUG, 'Bound relay (type:' + type + ', name:' + name + ')')

def unbind(type, name, callback):
	global RelayBindings
	targ = RelayBinding(type, name, callback)
	if targ in RelayBindings:
		RelayBindings.remove(targ)
		log.log(LOG_DEBUG, 'Unbound relay (type:' + type + ', name:' + name + ')')

def call(type, name, channel, args):
	global RelayBindings
	for targ in RelayBindings:
		if targ.type == type and targ.name == name:
			if targ.callback != None:
				log.log(LOG_DEBUG, 'Calling relay (type:' + type + ', name:' + name + ')')
				targ.callback(channel, args)
