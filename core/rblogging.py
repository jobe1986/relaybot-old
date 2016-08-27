# -*- coding: utf-8 -*-

# RelayBot - Simple Multi-protocol Relay Bot, core/rblogging.py
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

import logging, logging.handlers, sys, time, json

#logging.CRITICAL = 50
#logging.ERROR = 40
#logging.WARNING = 30
#logging.INFO = 20
#LOG_PROTOCOL = 15
#logging.DEBUG = 10
#logging.NOTSET = 0

__all__ = ['log', 'LOG_CRITICAL', 'LOG_ERROR', 'LOG_WARNING', 'LOG_INFO', 'LOG_PROTOCOL', 'LOG_DEBUG']

LOG_CRITICAL = 50
LOG_ERROR = 40
LOG_WARNING = 30
LOG_INFO = 20
LOG_PROTOCOL = 15
LOG_DEBUG = 10

levels = {'DEBUG': LOG_DEBUG, 'PROTOCOL': LOG_PROTOCOL, 'INFO': LOG_INFO, 'WARNING': LOG_WARNING, 'ERROR': LOG_ERROR, 'CRITICAL': LOG_CRITICAL}

class UTCFormatter(logging.Formatter):
	converter = time.gmtime

	def format(self, record):
		record.modname = record.name + '.' + record.module
		if hasattr(record, 'obj'):
			if hasattr(record.obj, 'name'):
				record.modname = record.modname + '::' + record.obj.name
		return super( UTCFormatter, self ).format(record)

class MyLogger(logging.Logger):
	def _addextraobj(self, object=None, **kwargs):
		if object != None:
			if not 'extra' in kwargs:
				kwargs['extra'] = {'obj': object}
			else:
				kwargs['extra']['obj'] = object
		return kwargs

	def critical(self, msg, object=None, *args, **kwargs):
		if self.isEnabledFor(logging.CRITICAL):
			kwargs = self._addextraobj(object, **kwargs)
			self._log(logging.CRITICAL, msg, args, **kwargs)

	def error(self, msg, object=None, *args, **kwargs):
		if self.isEnabledFor(logging.ERROR):
			kwargs = self._addextraobj(object, **kwargs)
			self._log(logging.ERROR, msg, args, **kwargs)

	def warning(self, msg, object=None, *args, **kwargs):
		if self.isEnabledFor(logging.WARNING):
			kwargs = self._addextraobj(object, **kwargs)
			self._log(logging.WARNING, msg, args, **kwargs)

	def info(self, msg, object=None, *args, **kwargs):
		if self.isEnabledFor(logging.INFO):
			kwargs = self._addextraobj(object, **kwargs)
			self._log(logging.INFO, msg, args, **kwargs)

	def debug(self, msg, object=None, *args, **kwargs):
		if self.isEnabledFor(logging.DEBUG):
			kwargs = self._addextraobj(object, **kwargs)
			self._log(logging.DEBUG, msg, args, **kwargs)

	def log(self, level, msg, object=None, *args, **kwargs):
		if not isinstance(level, int):
			if raiseExceptions:
				raise TypeError("level must be an integer")
			else:
				return

		kwargs = self._addextraobj(object, **kwargs)

		if self.isEnabledFor(level):
			self._log(level, msg, args, **kwargs)

def loadconfig(doc):
	global configs
	global levels

	configs = {'outputs': []}

	logconfs = doc.findall('./logging')

	if len(logconfs) < 1:
		return

	logconf = logconfs[0]

	outs = logconf.findall('./output')

	for out in outs:
		if not 'type' in out.attrib:
			print 'Error: Logging output missing type attribute'
			raise Exception('Error: Logging output missing type attribute')
		if not out.attrib['type'].lower() in ['file', 'stdout', 'stderr']:
			print 'Skipping Logging output with invalid type attribute'
			continue

		outconf = {'type': out.attrib['type'].lower(), 'path': None, 'rollover': None, 'level': None}

		if outconf['type'] == 'file':
			if not 'path' in out.attrib:
				print 'Error: Logging output missing path attribute'
				raise Exception('Error: Logging output missing path attribute')
			outconf['path'] = out.attrib['path']

			if 'rollover' in out.attrib:
				if not out.attrib['rollover'].lower() in ['midnight']:
					try:
						outconf['rollover'] = int(out.attrib['rollover'])
					except:
						outconf['rollover'] = None
				else:
					outconf['rollover'] = out.attrib['rollover'].lower()

		if 'level' in out.attrib and out.attrib['level'].upper() in levels:
			outconf['level'] = out.attrib['level']
		else:
			outconf['level'] = 'INFO'

		configs['outputs'].append(outconf)

def runconfig():
	global configs
	global log
	global levels

	for outconf in configs['outputs']:
		if outconf['type'] == 'stdout':
			loghandler = logging.StreamHandler(sys.stdout)
		elif outconf['type'] == 'stderr':
			loghandler = logging.StreamHandler(sys.stderr)
		elif outconf['type'] == 'file':
			if outconf['rollover'] == None:
				loghandler = logging.FileHandler(outconf['path'])
			elif outconf['rollover'] == 'midnight':
				loghandler = logging.handlers.TimedRotatingFileHandler(outconf['path'], when='midnight', interval=1, backupCount=10, utc=True)
			else:
				loghandler = logging.handlers.RotatingFileHandler(outconf['path'], maxBytes=outconf['rollover'], backupCount=10)
		logformatter = UTCFormatter('[%(asctime)s] [%(modname)s/%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
		loghandler.setFormatter(logformatter)

		loghandler.setLevel(levels[outconf['level']])
		log.addHandler(loghandler)

for name in levels:
	logging.addLevelName(levels[name], name)

logging.setLoggerClass(MyLogger)
log = logging.getLogger('relaybot')
log.setLevel(logging.DEBUG)
