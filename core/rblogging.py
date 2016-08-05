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
#logging.DEBUG = 10
#logging.NOTSET = 0

__all__ = ['log', 'LOG_CRITICAL', 'LOG_ERROR', 'LOG_WARNING', 'LOG_INFO', 'LOG_DEBUG']

LOG_CRITICAL = logging.CRITICAL
LOG_ERROR = logging.ERROR
LOG_WARNING = logging.WARNING
LOG_INFO = logging.INFO
LOG_DEBUG = logging.DEBUG

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

logging.setLoggerClass(MyLogger)

log = logging.getLogger('relaybot')

loghandler = logging.StreamHandler(sys.stdout)
logfilehandler = logging.handlers.TimedRotatingFileHandler('logs/relaybot.log', when='midnight', interval=1, backupCount=10, utc=True)
logformatter = UTCFormatter('[%(asctime)s] [%(modname)s/%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')

loghandler.setFormatter(logformatter)
logfilehandler.setFormatter(logformatter)

log.addHandler(loghandler)
log.addHandler(logfilehandler)

log.setLevel(logging.DEBUG)
