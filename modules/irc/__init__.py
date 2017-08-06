# -*- coding: utf-8 -*-

# RelayBot - Simple Multi-protocol Relay Bot, modules/irc.py
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

from core.logging import *
import core.config  as _config
import asyncio

from modules.irc.protocol import IRCProtocol
from modules.irc.client import IRCClient

log = log.getChild(__name__)

cliconfs = {}
clients = {}

def loadconfig(config):
	global cliconfs

	attrconf = {'irc': {
				'name': {'reqd': True}
				},
			'server': {
				'host': {'reqd': True},
				'port': {'def': 6667, 'type': _config.TYPE_INT},
				'ssl': {'def': False, 'type': _config.TYPE_BOOL},
				},
			'user': {
				'nick': {'def': 'RelayBot'},
				'user': {'def': 'relaybot'},
				'gecos': {'def': 'Relay Bot'}
				},
			'channel': {
				}
			}

	for clinode in config:
		attrs = _config.getattrs(clinode, log, attrconf['irc'])
		if attrs is None:
			continue
		if attrs['name'] in cliconfs:
			log.error('Duplicate IRC client name, skipping client configuration')
			continue
		cliname = attrs['name']

		log.debug('Found client configuration for IRC client: ' + cliname)

		conf = {'channels': []}

		srvnode = clinode.find('server')
		if srvnode is None:
			log.error('Missing node server in IRC client configuration ' + cliname)
			continue
		conf['server'] = _config.getattrs(srvnode, log, attrconf['server'])

		usrnode = clinode.find('user')
		if usrnode is None:
			log.error('Missing node user in IRC client configuration ' + cliname)
			continue
		conf['user'] = _config.getattrs(usrnode, log, attrconf['user'])

		cliconfs[cliname] = conf

def applyconfig(loop):
	global cliconfs, clients

	for name in cliconfs:
		clients[name] = IRCClient(loop, name, cliconfs[name], log)
