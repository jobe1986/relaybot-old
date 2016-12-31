# -*- coding: utf-8 -*-

# RelayBot - Simple Multi-protocol Relay Bot, modules/ircfantasy.py
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

import re

from core.rblogging import *
import core.relay as relay

configs = {}
clients = {}

def loadconfig(doc):
	global configs, clients

	cliconfs = doc.findall('./ircfantasy')

	for cli in cliconfs:
		if not 'name' in cli.attrib:
			log.log(LOG_ERROR, 'IRC Fantasy client config missing name attribute')
			raise Exception('IRC Fantasy client config missing name attribute')
		if cli.attrib['name'] in configs:
			log.log(LOG_ERROR, 'Duplicate IRC Fantasy config name')
			raise Exception('Duplicate IRC Fantasy config name')

		name = cli.attrib['name']
		conf = {'relays': []}

		relconfs = cli.findall('./relay')
		for rel in relconfs:
			if not 'type' in rel.attrib:
				log.log(LOG_ERROR, 'IRC Fantasy relay missing type attribute')
				raise Exception('IRC Fantasy relay missing type attribute')
			if not 'name' in rel.attrib:
				log.log(LOG_ERROR, 'IRC Fantasy relay missing name attribute')
				raise Exception('IRC Fantasy relay missing name attribute')
			if not 'channel' in rel.attrib:
				log.log(LOG_ERROR, 'IRC Fantasy relay missing channel attribute')
				raise Exception('IRC Fantasy relay missing channel attribute')
			if rel.attrib['type'] == 'IRCfantasy' and rel.attrib['name'] == name:
				log.log(LOG_INFO, 'Ignoring attempt to relay IRC to itself')
				continue
			relnew = rel.attrib
			conf['relays'].append(relnew)

		configs[name] = conf

def runconfig(timers):
	global configs, clients

	for key in configs:
		conf = configs[key]
		cli = client(key)
		for rel in conf['relays']:
			cli.relay_add(rel['type'], rel['name'], rel['channel'])
		clients[key] = cli

def sockets():
    return []

class client():
	def __init__(self, name):
		self.name = name
		self._relays = []

		relay.bind('ircfantasy', self.name, self._relaycallback)

	def __del__(self):
		try:
			relay.unbind('ircfantasy', self.name, self._relaycallback)
		except:
			pass

	def _relaycallback(self, data):
		src = data.source

		if src.type == 'irc':
			if data.extra['msg']['params'][-1][0:8] == '?testing':
				self._callrelay("I R A TEST", None)

	def _callrelay(self, text, obj, type=None, name=None, channel=None, extra={}):
		for rel in self._relays:
			if type != None and rel.type != type:
				continue
			if name != None and rel.name != name:
				continue
			if channel != None and rel.channel != channel.lower():
				continue
			e = {'obj': obj}
			for k in extra:
				e[k] = extra[k]
			relay.call(text, rel, relay.RelaySource('ircfantasy', self.name, None, {}), e)

	def relay_add(self, type, name, channel):
		rel = relay.RelayTarget(type, name, channel, {}, None)
		self._relays.append(rel)
		log.log(LOG_DEBUG, 'Added relay rule (type:' + type + ', name:' + name + ', channel:' + channel + ')', self)
