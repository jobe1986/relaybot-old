# -*- coding: utf-8 -*-

import sys
from collections import namedtuple

from modules.logging import *

relaytargets = []
RelayTarget = namedtuple('RelayTarget', ['type', 'name', 'callback'])
RelayChannel = namedtuple('RelayChannel', ['type', 'name', 'channel', 'prefix'])

def bind(type, name, callback):
	global relaytargets
	targ = RelayTarget(type, name, callback)
	if not targ in relaytargets:
		relaytargets.append(targ)
		log(LOG_NORMAL, '[Relay] --- Bound relay (type:' + type + ', name:' + name + ')\n')

def unbind(type, name, callback):
	global relaytargets
	targ = RelayTarget(type, name, callback)
	if targ in relaytargets:
		relaytargets.remove(targ)
		log(LOG_NORMAL, '[Relay] --- Unbound relay (type:' + type + ', name:' + name + ')\n')

def call(type, name, channel, args):
	global relaytargets
	for targ in relaytargets:
		if targ.type == type and targ.name == name:
			if targ.callback != None:
				log(LOG_NORMAL, '[Relay] --- Calling relay (type:' + type + ', name:' + name + ')\n')
				targ.callback(channel, args)
