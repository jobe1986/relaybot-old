#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, socket, select, time, sched

import core.modules as modules
from core.config import *
from core.mylogging import *

timers = None

def doselect(timeout):
	sockets = modules.getsockets()
	try:
		selread, selwrite, selerr = select.select(sockets, [], sockets, timeout)
	except KeyboardInterrupt as e:
		log.log(LOG_INFO, 'Received keyboard interrupt, shutting down.')
		for sock in sockets:
			sock.dodisconnect('Shutting down (Ctrl+C)')
		exit()
	except Exception as e:
		log.log(LOG_CRITICAL, str(e))
		exit()
	for sock in selerr:
		sock.doerr()
	for sock in selread:
		sock.doread()

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
	log.log(LOG_INFO, 'Received keyboard interrupt, shutting down.')
	sockets = modules.getsockets()
	for sock in sockets:
		sock.dodisconnect('Shutting down (Ctrl+C)')
except Exception as e:
	log.log(LOG_CRITICAL, str(e))
	sockets = modules.getsockets()
	for sock in sockets:
		sock.dodisconnect('Exception: ' + str(e))
