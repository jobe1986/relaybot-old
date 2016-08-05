# RelayBot - Simple Multi-protocol Relay Bot, core/config.py
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
