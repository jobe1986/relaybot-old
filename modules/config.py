# -*- coding: utf-8 -*-

from xml.etree.ElementTree import ElementTree

from modules.logging import *
import modules.irc as irc
import modules.minecraft as minecraft

def loadconfig(timers, file = 'config.xml'):
	try:
		tree = ElementTree()
		doc = tree.parse(file)

		irc.loadconfig(doc)
		minecraft.loadconfig(doc)
	except Exception as e:
		log(LOG_NORMAL, "Error parsing config: " + str(e) + '\n')

	try:
		irc.runconfig(timers)
		minecraft.runconfig(timers)
	except Exception as e:
		log(LOG_NORMAL, "Error loading config: " + str(e) + '\n')
