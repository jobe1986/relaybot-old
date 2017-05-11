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

import logging, logging.handlers, sys, time

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
	def _addextraobj(self, **kwargs):
		if self.name != 'relaybot':
			return kwargs
		if 'object' in kwargs and kwargs['object'] != None:
			object = kwargs['object']
			del kwargs['object']
			if not 'extra' in kwargs:
				kwargs['extra'] = {'obj': object}
			else:
				kwargs['extra']['obj'] = object
		return kwargs

	def critical(self, msg, *args, **kwargs):
		if self.isEnabledFor(logging.CRITICAL):
			kwargs = self._addextraobj(**kwargs)
			self._log(logging.CRITICAL, msg, args, **kwargs)

	def error(self, msg, *args, **kwargs):
		if self.isEnabledFor(logging.ERROR):
			kwargs = self._addextraobj(**kwargs)
			self._log(logging.ERROR, msg, args, **kwargs)

	def warning(self, msg, *args, **kwargs):
		if self.isEnabledFor(logging.WARNING):
			kwargs = self._addextraobj(**kwargs)
			self._log(logging.WARNING, msg, args, **kwargs)

	def info(self, msg, *args, **kwargs):
		if self.isEnabledFor(logging.INFO):
			kwargs = self._addextraobj(**kwargs)
			self._log(logging.INFO, msg, args, **kwargs)

	def protocol(self, msg, *args, **kwargs):
		if self.isEnabledFor(LOG_PROTOCOL):
			kwargs = self._addextraobj(**kwargs)
			self._log(LOG_PROTOCOL, msg, args, **kwargs)

	def debug(self, msg, *args, **kwargs):
		if self.isEnabledFor(logging.DEBUG):
			kwargs = self._addextraobj(**kwargs)
			self._log(logging.DEBUG, msg, args, **kwargs)

	def log(self, level, msg, *args, **kwargs):
		if not isinstance(level, int):
			if raiseExceptions:
				raise TypeError("level must be an integer")
			else:
				return

		kwargs = self._addextraobj(**kwargs)

		if self.isEnabledFor(level):
			self._log(level, msg, args, **kwargs)

for name in levels:
	logging.addLevelName(levels[name], name)

logging.setLoggerClass(MyLogger)

root = logging.getLogger(None)
root.setLevel(logging.DEBUG)

defloghandler = logging.StreamHandler(sys.stderr)
deflogformatter = UTCFormatter('[%(asctime)s] [%(modname)s/%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
defloghandler.setFormatter(deflogformatter)
defloghandler.setLevel('INFO')
root.addHandler(defloghandler)

log = logging.getLogger('relaybot')
log.setLevel(logging.DEBUG)
