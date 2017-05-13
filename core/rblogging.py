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

import logging, logging.handlers, sys, time, re, os

#logging.CRITICAL = 50
#logging.ERROR = 40
#logging.WARNING = 30
#logging.INFO = 20
#LOG_PROTOCOL = 15
#logging.DEBUG = 10
#logging.NOTSET = 0

__all__ = ['log', 'LOG_CRITICAL', 'LOG_ERROR', 'LOG_WARNING', 'LOG_INFO', 'LOG_PROTOCOL', 'LOG_DEBUG']

LOG_CRITICAL = logging.CRITICAL
LOG_ERROR = logging.ERROR
LOG_WARNING = logging.WARNING
LOG_INFO = logging.INFO
LOG_PROTOCOL = 15
LOG_DEBUG = logging.DEBUG
LOG_NOTSET = logging.NOTSET

LOG_DEFAULT = LOG_DEBUG

levels = {'DEBUG': LOG_DEBUG, 'PROTOCOL': LOG_PROTOCOL, 'INFO': LOG_INFO, 'WARNING': LOG_WARNING, 'ERROR': LOG_ERROR, 'CRITICAL': LOG_CRITICAL}

cwd = os.getcwd()

def leveltoname(level):
	global levels
	for lvl in levels:
		if levels[lvl] == level:
			return lvl
	return 'NOTSET'

class AddModnameFilter(logging.Filter):
	def __init__(self):
		pass

	def setmod(self, record):
		global cwd
		if record.name == 'relaybot':
			modpath = os.path.relpath(record.pathname, cwd)
			parts = os.path.split(os.path.splitext(modpath)[0])
			if parts[0] != 'core' and parts[0] != '':
				mod = '.'.join(parts)
				if mod[0] == '.':
					mod = mod[1:]
				record.module = mod

	def filter(self, record):
		self.setmod(record)
		record.modname = record.name + '.' + record.module
		if hasattr(record, 'obj'):
			if hasattr(record.obj, 'name'):
				record.modname = record.modname + '::' + record.obj.name
		return True

class ModnameRegExFilter(logging.Filter):
	def __init__(self, regex):
		self._re = re.compile(regex)

	def filter(self, record):
		if hasattr(record, 'modname'):
			m = self._re.match(record.modname)
			if m != None:
				return True
		return False

class UTCFormatter(logging.Formatter):
	converter = time.gmtime

class MyLogger(logging.Logger):
	def _addextraobj(self, **kwargs):
		if self.name != 'relaybot':
			return kwargs
		object = None
		if 'object' in kwargs and kwargs['object'] != None:
			object = kwargs['object']
			del kwargs['object']
		elif 'obj' in kwargs and kwargs['obj'] != None:
			object = kwargs['obj']
			del kwargs['obj']
		if object != None:
			if not 'extra' in kwargs:
				kwargs['extra'] = {'obj': object}
			else:
				kwargs['extra']['obj'] = object
		return kwargs

	def critical(self, msg, *args, **kwargs):
		if self.isEnabledFor(LOG_CRITICAL):
			kwargs = self._addextraobj(**kwargs)
			self._log(LOG_CRITICAL, msg, args, **kwargs)

	def error(self, msg, *args, **kwargs):
		if self.isEnabledFor(LOG_ERROR):
			kwargs = self._addextraobj(**kwargs)
			self._log(LOG_ERROR, msg, args, **kwargs)

	def warning(self, msg, *args, **kwargs):
		if self.isEnabledFor(LOG_WARNING):
			kwargs = self._addextraobj(**kwargs)
			self._log(LOG_WARNING, msg, args, **kwargs)

	warn = warning

	def info(self, msg, *args, **kwargs):
		if self.isEnabledFor(LOG_INFO):
			kwargs = self._addextraobj(**kwargs)
			self._log(LOG_INFO, msg, args, **kwargs)

	def protocol(self, msg, *args, **kwargs):
		if self.isEnabledFor(LOG_PROTOCOL):
			kwargs = self._addextraobj(**kwargs)
			self._log(LOG_PROTOCOL, msg, args, **kwargs)

	def debug(self, msg, *args, **kwargs):
		if self.isEnabledFor(LOG_DEBUG):
			kwargs = self._addextraobj(**kwargs)
			self._log(LOG_DEBUG, msg, args, **kwargs)

	def log(self, level, msg, *args, **kwargs):
		if not isinstance(level, int):
			if raiseExceptions:
				raise TypeError("level must be an integer")
			else:
				return

		kwargs = self._addextraobj(**kwargs)

		if self.isEnabledFor(level):
			self._log(level, msg, args, **kwargs)

confs = {'outputs': []}

def loadconfig(conf):
	global confs, levels, log

	outs = conf.findall('output')

	for out in outs:
		if not 'type' in out.attrib:
			log.error('Missing type attribute in logging output')
			continue
		if not out.attrib['type'].lower() in ['file', 'stdout', 'stderr']:
			log.error('Invalid type "' + out.attrib['type'] + '" in logging output')
			continue

		outconf = {'type': out.attrib['type'].lower(), 'path': None, 'rollover': None, 'level': LOG_INFO}

		if 'level' in out.attrib:
			if not out.attrib['level'].upper() in levels:
				log.warning('Invalid level attribute value "' + out.attrib['level'] + '" in logging output, assuming INFO')
				outconf['level'] = LOG_INFO
			else:
				outconf['level'] = levels[out.attrib['level'].upper()]

		if outconf['type'] == 'file':
			if not 'path' in out.attrib:
				log.error('Missing path attribute in file logging output')
				continue
			outconf['path'] = out.attrib['path']

			if 'rollover' in out.attrib:
				if out.attrib['rollover'].lower() in ['midnight']:
					outconf['rollover'] = out.attrib['rollover'].lower()
				else:
					try:
						outconf['rollover'] = int(out.attrib['rollover'])
					except:
						log.warning('Invalid value for rollover in logging output, assuming no rollover')

		oc2 = outconf.copy()
		oc2['level'] = leveltoname(oc2['level'])
		log.debug('Found logging output: ' + str(oc2))
		confs['outputs'].append(outconf)

	return True

def applyconfig(loop):
	global confs, log, root, defloghandler, deflogformatter

	i = 0

	for out in confs['outputs']:
		if out['type'] == 'stdout':
			loghandler = logging.StreamHandler(sys.stdout)
		elif out['type'] == 'stderr':
			loghandler = logging.StreamHandler(sys.stderr)
		elif out['type'] == 'file':
			if out['rollover'] == None:
				loghandler = logging.FileHandler(out['path'])
			elif out['rollover'] == 'midnight':
				loghandler = logging.handlers.TimedRotatingFileHandler(out['path'], when='midnight', interval=1, backupCount=10, utc=True)
			else:
				loghandler = logging.handlers.RotatingFileHandler(out['path'], maxBytes=out['rollover'], backupCount=10)
		else:
			continue

		logformatter = UTCFormatter('[%(asctime)s] [%(modname)s/%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
		loghandler.setFormatter(logformatter)
		loghandler.setLevel(out['level'])
		loghandler.addFilter(AddModnameFilter())
		root.addHandler(loghandler)
		i += 1

	if i > 0:
		root.removeHandler(defloghandler)
		log.debug('Found at least one valid logging output, no longer using default output')

for name in levels:
	logging.addLevelName(levels[name], name)

logging.setLoggerClass(MyLogger)

root = logging.getLogger(None)
root.setLevel(LOG_DEFAULT)

defloghandler = logging.StreamHandler(sys.stderr)
deflogformatter = UTCFormatter('[%(asctime)s] [%(modname)s/%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
defloghandler.setFormatter(deflogformatter)
defloghandler.setLevel(LOG_DEFAULT)
defloghandler.addFilter(AddModnameFilter())
root.addHandler(defloghandler)

log = logging.getLogger('relaybot')
log.setLevel(LOG_DEFAULT)
