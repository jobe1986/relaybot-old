# RelayBot - Simple Multi-protocol Relay Bot, core/rbsocket.py
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

# -*- coding: utf-8 -*-

import socket

from core.rblogging import *

class rbsocket(socket.socket):
	def __init__(self, *p, **d):
		self._doread = None
		self._doerr = None
		self._dodisconnect = None
		super( rbsocket, self ).__init__(*p, **d)

	def doread(self):
		if self._doread != None:
			self._doread(self)

	def doerr(self):
		if self._doerr != None:
			self._doerr(self)

	def dodisconnect(self, msg = None):
		if self._dodisconnect != None:
			self._dodisconnect(self, msg)

	def setdoread(self, func):
		self._doread = func

	def setdoerr(self, func):
		self._doerr = func

	def setdodisconnect(self, func):
		self._dodisconnect = func
