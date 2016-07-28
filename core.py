#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import socket, select
import time
import sched


from modules.config import *
from modules.mylogging import *

import modules.irc as irc
import modules.minecraft as minecraft

timers = None

def doselect(timeout):
	sockets = irc.client.sockets + minecraft.client.sockets
	try:
		selread, selwrite, selerr = select.select(sockets, [], sockets, timeout)
	except KeyboardInterrupt as e:
		for sock in sockets:
			sock.dodisconnect('Shutting down (Ctrl+C)')
		exit()
	except:
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
	sockets = irc.client.sockets + minecraft.client.sockets
	for sock in sockets:
		sock.dodisconnect('Shutting down (Ctrl+C)')
except Exception as e:
	log.log(LOG_CRITICAL, str(e))
	sockets = irc.client.sockets + minecraft.client.sockets
	for sock in sockets:
		sock.dodisconnect('Exception: ' + str(e))
