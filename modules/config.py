# -*- coding: utf-8 -*-

from xml.etree.ElementTree import ElementTree

from modules.mylogging import *
import modules.irc as irc
import modules.minecraft as minecraft

def loadconfig(timers, file = 'config.xml'):
	try:
		tree = ElementTree()
		doc = tree.parse(file)

		irc.loadconfig(doc)
		minecraft.loadconfig(doc)
	except Exception as e:
		log.log(LOG_INFO, "Error parsing config: " + str(e))

	try:
		irc.runconfig(timers)
		minecraft.runconfig(timers)
	except Exception as e:
		log.log(LOG_INFO, "Error loading config: " + str(e))
