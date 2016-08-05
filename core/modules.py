# -*- coding: utf-8 -*-

from collections import namedtuple

from core.rblogging import *

mods = {}

def load(name):
	global mods

	if 'name' in mods:
		log.log(LOG_WARN, 'Unable to load module ' + name + ': already loaded')
		return
	try:
		m = __import__('modules.' + name)
		if hasattr(m, name):
			m = getattr(m, name)
	except Exception as e:
		log.log(LOG_ERROR, 'Error loading module ' + name + ': ' + str(e))
		m = None

	if m != None:
		mods[name] = m

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
			load(mod.attrib['name'])
			if hasattr(mods[mod.attrib['name']], 'loadconfig'):
				mods[mod.attrib['name']].loadconfig(doc)

def runconfig(timers):
	global mods
	for name in mods:
		if hasattr(mods[name], 'runconfig'):
			mods[name].runconfig(timers)
