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

import core.logging as _logging
import core.config as _config

import asyncio, sys, argparse, signal

log = _logging.log.getChild('main')

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--config', help='Specify the path to config.xml', action='store', default=_config.configpath, dest='config')
	parser.add_argument('-d', '--debug', help='Enable debug output to STDOUT', action='store_true', dest='debug')
	return parser.parse_args()

def handle_sigint():
	log.info('Stopping loop: Received signal SIGINT')
	loop.stop()

args = parse_args()

_config.checkdebug(args)
_logging.init_logging(args)

# Create event loop and set signal handlers
loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGINT, handle_sigint)

# Begin by loading config when we start the loop
loop.call_soon(_config.load, loop, args)

log.info('Starting loop')

try:
	loop.run_forever()
except KeyboardInterrupt:
	log.info('Stopping loop: Keyboard interrupt')

loop.close()
