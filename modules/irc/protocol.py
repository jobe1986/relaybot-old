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

from core.rblogging import *
import asyncio

class IRCProtocol(asyncio.Protocol):
	def __init__(self, client, loop, log):
		self._client = client
		self._loop = loop
		self._log = log.getChild('protocol')

		self._handlers = {}

		self._reset()
		self._log.debug('Created client protocol')

	def _reset(self):
		self._sock = None
		self._buf = ''

	def connection_made(self, transport):
		self._sock = transport

	def data_received(self, data):
		self._buf = self._buf + data.decode()
		self._buf = self._buf.replace('\r', '\n')
		self._log.debug('RECV: ' + data.decode())

		while True:
			nl = self._buf.find('\n')
			if nl < 0:
				break

			line = self._buf[0:nl]
			self._buf = self._buf[nl+1:]

			if len(line) > 0:
				msg = self._parseline(line)

		if len(self._buf) > 0:
			self._log.debug('Remaining buffer: ' + self._buf)

	def connection_lost(self, exc):
		pass

	def _parseline(self, line):
		msg = {'source': {'name': None, 'ident': None, 'host': None, 'full': None}, 'msg': None, 'params': []}
		self._log.debug('Parsing line: ' + line)

		trailing = False
		for word in line.split(' '):
			if word[0] == ':':
				if msg['source']['full'] is None:
					msg['source']['full'] = word[1:]
					sourcedone = True
				else:
					msg['params'].append(word[1:])
					trailing = True
			else:
				if msg['msg'] is None:
					msg['msg'] = word
				else:
					if trailing:
						msg['params'][-1] = msg['params'][-1] + ' ' + word
					else:
						msg['params'].append(word)

		if not msg['source']['full'] is None:
			src = msg['source']['full']
			pos = src.find('@')
			if pos >= 0:
				msg['source']['host'] = src[pos+1:]
				src = src[:pos]
			pos = src.find('!')
			if pos >= 0:
				msg['source']['ident'] = src[pos+1:]
				src = src[:pos]
			msg['source']['name'] = src

		self._log.debug('Parsed line: ' + str(msg))
		return msg

