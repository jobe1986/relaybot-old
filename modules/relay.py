# -*- coding: utf-8 -*-

import sys
from collections import namedtuple

from modules.mylogging import *

relaytargets = []
RelayTarget = namedtuple('RelayTarget', ['type', 'name', 'callback'])
RelayChannel = namedtuple('RelayChannel', ['type', 'name', 'channel', 'prefix'])

def bind(type, name, callback):
	global relaytargets
	targ = RelayTarget(type, name, callback)
	if not targ in relaytargets:
		relaytargets.append(targ)
		log.log(LOG_INFO, 'Bound relay (type:' + type + ', name:' + name + ')')

def unbind(type, name, callback):
	global relaytargets
	targ = RelayTarget(type, name, callback)
	if targ in relaytargets:
		relaytargets.remove(targ)
		log.log(LOG_INFO, 'Unbound relay (type:' + type + ', name:' + name + ')')

def call(type, name, channel, args):
	global relaytargets
	for targ in relaytargets:
		if targ.type == type and targ.name == name:
			if targ.callback != None:
				log.log(LOG_INFO, 'Calling relay (type:' + type + ', name:' + name + ')')
				targ.callback(channel, args)
