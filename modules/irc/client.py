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

from modules.irc.protocol import IRCProtocol

class IRCClient():
	def __init__(self, loop, name, config, log):
		self.name = name
		self._loop = loop
		self._log = log.getChild(name)
		self._proto = IRCProtocol(self, loop, self._log)
		self._config = config
		self._log.info('Created client')

	def connect():
		pass

	def disconnect():
		pass

	def reconnect():
		pass
