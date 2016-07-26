# -*- coding: utf-8 -*-

import socket

from modules.logging import *

class mysocket(socket.socket):
	def __init__(self, *p, **d):
		self._doread = None
		self._doerr = None
		self._dodisconnect = None
		super( mysocket, self ).__init__(*p, **d)

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
