# -*- coding: utf-8 -*-

# RelayBot - Simple Multi-protocol Relay Bot, core/rbLOG_py
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

from xml.etree.ElementTree import ElementTree

import core.rblogging as rblogging
import core.rbmodules as rbmodules
from core.rblogging import *

import os

def load(loop, file='config/config.xml'):
	try:
		absfile = os.path.abspath(file)
		tree = ElementTree()
		doc = tree.parse(absfile)

		log.info('Loading configuration from ' + absfile)

		log.debug('Loading logging config')
		logcfg = doc.find('logging')
		if rblogging.loadconfig(logcfg):
			rblogging.applyconfig(loop)
		else:
			log.error('Unable to load logging config')
			return False

		log.debug('Loading modules')
		if rbmodules.loadconfig(doc):
			rbmodules.applyconfig(loop)
		else:
			log.error('Unable to load modules')
			return False

		log.info('Configuration successfully loaded')
		return True
	except Exception as e:
		log.error('Error parsing config: ' + str(e))
