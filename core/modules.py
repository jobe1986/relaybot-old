# -*- coding: utf-8 -*-

# RelayBot - Simple Multi-protocol Relay Bot, core/modules.py
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

from collections import namedtuple

import core.logging as _logging
import importlib

log = _logging.log.getChild(__name__)

mods = {}

def loadmod(name):
	global mods

	if name in mods:
		log.warning('Unable to load module ' + name + ': already loaded')
		return False

	try:
		m = importlib.import_module('modules.' + name)
		importlib.invalidate_caches()
	except Exception as e:
		log.error('Error loading module ' + name + ': ' + str(e))
		return False

	mods[name] = m
	log.debug('Loaded module ' + name)
	return m

def loadconfig(config):
	global mods

	modcfgs = config.findall('module')

	for mod in modcfgs:
		if not 'name' in mod.attrib:
			log.warning('Missing name attribute for module')
			continue
		name = mod.attrib['name']

		m = loadmod(name)

	for name in mods:
		m = mods[name]
		if m != None:
			if hasattr(m, 'loadconfig'):
				cfg = config.findall(name)
				m.loadconfig(cfg)

	return True

def applyconfig(loop):
	global mods
	for name in mods:
		if hasattr(mods[name], 'applyconfig'):
			mods[name].applyconfig(loop)
