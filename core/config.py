# -*- coding: utf-8 -*-

from xml.etree.ElementTree import ElementTree

from core.rblogging import *
import core.modules as modules

def loadconfig(timers, file = 'config.xml'):
	try:
		tree = ElementTree()
		doc = tree.parse(file)

		modules.loadconfig(doc)
	except Exception as e:
		log.log(LOG_INFO, "Error parsing config: " + str(e))

	try:
		modules.runconfig(timers)
	except Exception as e:
		log.log(LOG_INFO, "Error loading config: " + str(e))
