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

from core.rblogging import *

mods = {}

def load(name):
	global mods

	if 'name' in mods:
		log.log(LOG_WARN, 'Unable to load module ' + name + ': already loaded')
		return False
	try:
		m = __import__('modules.' + name)
		if hasattr(m, name):
			m = getattr(m, name)
	except Exception as e:
		log.log(LOG_ERROR, 'Error loading module ' + name + ': ' + str(e))
		m = None

	if m != None:
		mods[name] = m
		return True
	return False

def getsockets():
	global mods

	socks = []

	for name in mods:
		if hasattr(mods[name], 'sockets'):
			socks = socks + mods[name].sockets()

	return socks


def loadconfig(doc):
	global mods

	modconfs = doc.findall('./module')

	for mod in modconfs:
		if not 'name' in mod.attrib:
			log.log(LOG_ERROR, 'Module config missing module name')
			raise Exception('Module config missing module name')
		if not mod.attrib['name'] in mods:
			if not load(mod.attrib['name']):
				continue
			if hasattr(mods[mod.attrib['name']], 'loadconfig'):
				mods[mod.attrib['name']].loadconfig(doc)

def runconfig(timers):
	global mods
	for name in mods:
		if hasattr(mods[name], 'runconfig'):
			mods[name].runconfig(timers)
