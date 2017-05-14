#!/usr/bin/python3
# -*- coding: utf-8 -*-

# RelayBot - Simple Multi-protocol Relay Bot, run.py
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

from core.rblogging import *
import core.rblogging as _logging
import core.rbconfig as _config

import asyncio, sys, argparse

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--config', help='Specify the path to config.xml', action='store', default=_config.configpath, dest='config')
	parser.add_argument('-d', '--debug', help='Enable debug output to STDOUT', action='store_true', dest='debug')
	return parser.parse_args()

args = parse_args()

_config.checkdebug(args)

_logging.init_logging(args)

loop = asyncio.get_event_loop()

if not _config.load(loop, args):
	log.critical('Unable to load configuration')
	sys.exit()

try:
	loop.run_forever()
except KeyboardInterrupt:
	log.info('Stopping: Keyboard interrupt')

loop.close()
