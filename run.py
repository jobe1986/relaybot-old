#!/usr/bin/python
# -*- coding: utf-8 -*-

# RelayBot - Simple Multi-protocol Relay Bot, run.py
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

import sys, socket, select, time, sched

import core.modules as modules
import core.rbsocket as rbsocket
from core.config import *
from core.rblogging import *

timers = None

def doselect(timeout):
	sockets = modules.getsockets()
	try:
		selread, selwrite, selerr = select.select(sockets, [], sockets, timeout)
	except KeyboardInterrupt as e:
		for sock in sockets:
			rbsocket.dodisconnect(sock, 'Shutting down (Ctrl+C)')
		log.log(LOG_INFO, 'Received keyboard interrupt, shutting down.')
		exit()
	except Exception as e:
		log.log(LOG_CRITICAL, str(e))
		exit()
	for sock in selerr:
		rbsocket.doerr(sock)
	for sock in selread:
		rbsocket.doread(sock)

def main():
	global timers
	timers = sched.scheduler(time.time, doselect)

	loadconfig(timers)

	while (True):
		if (timers.empty()):
			doselect(None)
		else:
			timers.run()

try:
	main()
except KeyboardInterrupt as e:
	sockets = modules.getsockets()
	for sock in sockets:
		rbsocket.dodisconnect(sock, 'Shutting down (Ctrl+C)')
	log.log(LOG_INFO, 'Received keyboard interrupt, shutting down.')
except Exception as e:
	sockets = modules.getsockets()
	for sock in sockets:
		rbsocket.dodisconnect(sock, 'Exception: ' + str(e))
	log.log(LOG_CRITICAL, str(e))
