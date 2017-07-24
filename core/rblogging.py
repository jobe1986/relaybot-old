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

import logging, logging.handlers, sys, time, re, os

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
LOG_NOTSET = logging.NOTSET

levels = {'DEBUG': LOG_DEBUG, 'INFO': LOG_INFO, 'WARNING': LOG_WARNING, 'ERROR': LOG_ERROR, 'CRITICAL': LOG_CRITICAL}

cwd = os.getcwd()

root = logging.getLogger(None)
log = logging.getLogger('relaybot')
mylog = log.getChild(__name__)
args = None

def leveltoname(level):
	global levels
	for lvl in levels:
		if levels[lvl] == level:
			return lvl
	return 'NOTSET'

class UTCFormatter(logging.Formatter):
	converter = time.gmtime

confs = {'outputs': []}

def loadconfig(conf):
	global confs, levels

	outs = conf.findall('output')

	for out in outs:
		if not 'type' in out.attrib:
			mylog.error('Missing type attribute in logging output')
			continue
		if not out.attrib['type'].lower() in ['file', 'stdout', 'stderr']:
			mylog.error('Invalid type "' + out.attrib['type'] + '" in logging output')
			continue

		outconf = {'type': out.attrib['type'].lower(), 'path': None, 'rollover': None, 'level': LOG_INFO}

		if 'level' in out.attrib:
			if not out.attrib['level'].upper() in levels:
				mylog.warning('Invalid level attribute value "' + out.attrib['level'] + '" in logging output, assuming INFO')
				outconf['level'] = LOG_INFO
			else:
				outconf['level'] = levels[out.attrib['level'].upper()]

		if outconf['type'] == 'file':
			if not 'path' in out.attrib:
				mylog.error('Missing path attribute in file logging output')
				continue
			outconf['path'] = out.attrib['path']

			if 'rollover' in out.attrib:
				if out.attrib['rollover'].lower() in ['midnight']:
					outconf['rollover'] = out.attrib['rollover'].lower()
				else:
					try:
						outconf['rollover'] = int(out.attrib['rollover'])
					except:
						mylog.warning('Invalid value for rollover in logging output, assuming no rollover')

		oc2 = outconf.copy()
		oc2['level'] = leveltoname(oc2['level'])
		mylog.debug('Found logging output: ' + str(oc2))
		confs['outputs'].append(outconf)

	return True

def applyconfig(loop):
	global confs, root, defloghandler, deflogformatter, cliargs

	removedef = False

	for out in confs['outputs']:
		if out['type'] == 'stdout':
			if cliargs.debug:
				continue
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

		logformatter = UTCFormatter('[%(asctime)s] [%(name)s/%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
		loghandler.setFormatter(logformatter)
		loghandler.setLevel(out['level'])
		root.addHandler(loghandler)
		if not cliargs.debug:
			removedef = True

	if removedef:
		root.removeHandler(defloghandler)
		mylog.debug('Found at least one valid logging output, no longer using default output')

def init_logging(args):
	global rblog, levels, root, defloghandler, deflogformatter, cliargs
	cliargs = args

	for name in levels:
		logging.addLevelName(levels[name], name)

	defloghandler = logging.StreamHandler(sys.stderr)
	deflogformatter = UTCFormatter('[%(asctime)s] [%(name)s/%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
	defloghandler.setFormatter(deflogformatter)

	if args.debug:
		defloghandler.setLevel(LOG_DEBUG)
	else:
		defloghandler.setLevel(LOG_INFO)

	root.setLevel(LOG_DEBUG)
	log.setLevel(LOG_DEBUG)
	root.addHandler(defloghandler)

	if args.debug:
		log.debug('Debug logging enabled')
