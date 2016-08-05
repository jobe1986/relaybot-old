# -*- coding: utf-8 -*-

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

import socket

from core.rblogging import *
from collections import namedtuple

SockCallbacks = namedtuple('SockCallbacks', ['dodisconnect', 'doerr', 'doread'])

socks = {}

def dodisconnect(sock, msg = None):
	global socks

	if hasattr(sock, 'dodisconnect'):
		sock.dodisconnect(msg)
	elif sock in socks:
		if socks[sock].dodisconnect != None:
			socks[sock].dodisconnect(sock, msg)

def doerr(sock):
	global socks

	if hasattr(sock, 'doerr'):
		sock.doerr()
	elif sock in socks:
		if socks[sock].doerr != None:
			socks[sock].doerr(sock)

def doread(sock):
	global socks

	if hasattr(sock, 'doread'):
		sock.doread()
	elif sock in socks:
		if socks[sock].doread != None:
			socks[sock].doread(sock)

def bindsockcallbacks(sock, dodisconnect=None, doerr=None, doread=None):
	global socks

	if isinstance(sock, rbsocket):
		sock.setdoread(doread)
		sock.setdoerr(doerr)
		sock.setdodisconnect(dodisconnect)
	else:
		sockcalls = SockCallbacks(dodisconnect, doerr, doread)
		socks[sock] = sockcalls

def unbindsockcallbacks(sock):
	global socks

	if sock in socks:
		socks.pop(sock)

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
