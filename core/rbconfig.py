# -*- coding: utf-8 -*-

# RelayBot - Simple Multi-protocol Relay Bot, core/rbconfig.py
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

import core.rblogging as _logging
import core.rbmodules as _modules

import os

log = _logging.log.getChild(__name__)

config = None
configpath = 'config/config.xml'

def load(loop, args):
	global config, configpath
	try:
		log.info('Loading configuration from ' + configpath)

		log.debug('Loading logging configuration')
		logcfg = config.find('logging')
		if _logging.loadconfig(logcfg):
			_logging.applyconfig(loop)
		else:
			log.error('Unable to load logging configuration')
			loop.stop()
			return

		log.debug('Loading modules')
		if _modules.loadconfig(config):
			_modules.applyconfig(loop)
		else:
			log.error('Unable to load modules')
			loop.stop()
			return

		log.info('Configuration successfully loaded')
		return
	except Exception as e:
		log.error('Error parsing configuration: ' + str(e))
		loop.stop()
		return

def checkdebug(args):
	global config, configpath
	try:
		configpath = os.path.abspath(args.config)
		tree = ElementTree()
		config = tree.parse(configpath)

		dbgconf = config.findall('debug')
		if len(dbgconf) > 0:
			args.debug = True
	except Exception as e:
		log.error('Error checking configuration for debug mode: ' + str(e))
		
def getattrs(node, log, required=[], defaults={}, types={}):
	ret = {}

	for key in node.attrib:
		val = node.attrib[key]

		if key in types:
			t = types[key]
			err = None
			if t == 'int':
				try:
					val = int(val)
				except Exception as e:
					err = str(e)
			elif t == 'float':
				try:
					val = float(val)
				except Exception as e:
					err = str(e)
			elif t == 'bool':
				if val.lower() in ['false', 'no', '0']:
					val = False
				else:
					val = True

			if not err is None:
				if key in defaults:
					log.warning('Error converting attribute ' + key + ' to type ' + t + ', using default value instead')
					val = defaults[key]
				else:
					log.error('Error converting attribute ' + key + ' to type ' + t + ': ' + err)
					continue

		ret[key] = val
		if key in required:
			required.remove(key)

	if len(required) > 0:
		log.error('Missing attribute(s) for ' + node.tag + ' configuration: ' + ', '.join(required))
		return None

	for key in defaults:
		if not key in ret:
			ret[key] = defaults[key]

	return ret
