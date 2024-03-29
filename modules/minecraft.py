# -*- coding: utf-8 -*-

# RelayBot - Simple Multi-protocol Relay Bot, modules/minecraft.py
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

import socket, sched, time, sys, json, re, binascii
from struct import pack, unpack
from collections import namedtuple

import core.rbsocket as rbsocket
from core.rblogging import *
import core.relay as relay

MCRConPacket = namedtuple('MCRConPacket', ['id', 'type', 'payload'])
MCUDPLogPacket = namedtuple('MCUDPLogPacket', ['timestamp', 'logger', 'message', 'thread', 'level'])
MCRConCallback = namedtuple('MCRConCallback', ['callback', 'time', 'args', 'command'])

configs = {}
clients = {}
filterobjs = {
		'playerdeath': None,
		'playerjoinpart': None,
		'playerchat': None,
		'overviewer': None,
		'crash': None
	}

def loadconfig(doc):
	global configs

	cliconfs = doc.findall('./minecraft')

	for cli in cliconfs:
		if not 'name' in cli.attrib:
			log.error('Minrcraft client config missing name attribute')
			raise Exception('Minecraft client config missing name attribute')
		if cli.attrib['name'] in configs:
			log.error('Duplicate Minecraft config name')
			raise Exception('Duplicate Minecraft config name')

		name = cli.attrib['name']
		configs[name] = {'rcon': {'host': '', 'port': '', 'password': ''}, 'udp': {'host': '', 'port': ''}, 'relays': {}}

		rcon = cli.find('./rcon')
		if not 'host' in rcon.attrib:
			log.error('Minrcraft client rcon config missing host attribute')
			raise Exception('Minrcraft client rcon config missing host attribute')
		if not 'port' in rcon.attrib:
			log.error('Minrcraft client rcon config missing port attribute')
			raise Exception('Minrcraft client rcon config missing port attribute')
		if not 'password' in rcon.attrib:
			log.error('Minrcraft client rcon config missing password attribute')
			raise Exception('Minrcraft client rcon config missing password attribute')
		configs[name]['rcon'] = rcon.attrib

		udp = cli.find('./udp')
		if not 'port' in udp.attrib:
			log.error('Minrcraft client udp config missing port attribute')
			raise Exception('Minrcraft client udp config missing port attribute')
		configs[name]['udp'] = udp.attrib

		rels = rcon.findall('./relay')
		for rel in rels:
			if not 'type' in rel.attrib:
				log.error('Minecraft rcon relay missing type attribute')
				raise Exception('Minecraft rcon relay missing type attribute')
			if not 'name' in rel.attrib:
				log.error('Minecraft rcon relay missing name attribute')
				raise Exception('Minecraft rcon relay missing name attribute')
			if not 'channel' in rel.attrib:
				log.error('Minecraft rcon relay missing channel attribute')
				raise Exception('Minecraft rcon relay missing channel attribute')
			if rel.attrib['type'] == 'minecraft' and rel.attrib['name'] == name:
				log.info('Ignoring attempt to relay Minecraft to itself')
				continue
			relnew = rel.attrib
			relnew['filters'] = []

			filters = rel.findall('./filter')
			for filt in filters:
				if 'type' in filt.attrib:
					relnew['filters'].append(filt.attrib['type'])

			if not 'prefix' in relnew:
				relnew['prefix'] = '[' + name + ']'
			if not 'rcon' in configs[name]['relays']:
				configs[name]['relays']['rcon'] = []
			configs[name]['relays']['rcon'].append(relnew)

		rels = udp.findall('./relay')
		for rel in rels:
			if not 'type' in rel.attrib:
				log.error('Minecraft udp relay missing type attribute')
				raise Exception('Minecraft udp relay missing type attribute')
			if not 'name' in rel.attrib:
				log.error('Minecraft udp relay missing name attribute')
				raise Exception('Minecraft udp relay missing name attribute')
			if not 'channel' in rel.attrib:
				log.error('Minecraft udp relay missing channel attribute')
				raise Exception('Minecraft udp relay missing channel attribute')
			if rel.attrib['type'] == 'minecraft' and rel.attrib['name'] == name:
				log.info('Ignoring attempt to relay Minecraft to itself')
				continue
			relnew = rel.attrib
			relnew['filters'] = []

			filters = rel.findall('./filter')
			for filt in filters:
				if 'type' in filt.attrib:
					relnew['filters'].append(filt.attrib['type'])

			if not 'prefix' in relnew:
				relnew['prefix'] = '[' + name + ']'
			if not 'udp' in configs[name]['relays']:
				configs[name]['relays']['udp'] = []
			configs[name]['relays']['udp'].append(relnew)

		rels = cli.findall('./relay')
		for rel in rels:
			if not 'type' in rel.attrib:
				log.error('Minecraft channel relay missing type attribute')
				raise Exception('Minecraft channel relay missing type attribute')
			if not 'name' in rel.attrib:
				log.error('Minecraft channel relay missing name attribute')
				raise Exception('Minecraft channel relay missing name attribute')
			if not 'channel' in rel.attrib:
				log.error('Minecraft channel relay missing channel attribute')
				raise Exception('Minecraft channel relay missing channel attribute')
			if rel.attrib['type'] == 'minecraft' and rel.attrib['name'] == name:
				log.info('Ignoring attempt to relay Minecraft to itself')
				continue
			relnew = rel.attrib
			relnew['filters'] = []

			filters = rel.findall('./filter')
			for filt in filters:
				if 'type' in filt.attrib:
					relnew['filters'].append(filt.attrib['type'])

			if not 'prefix' in relnew:
				relnew['prefix'] = '[' + name + ']'
			if not '' in configs[name]['relays']:
				configs[name]['relays'][''] = []
			configs[name]['relays'][''].append(relnew)

def runconfig(timers):
	global configs
	global clients
	global filterobjs

	for key in configs:
		conf = configs[key]
		if not 'host' in conf['udp']:
			conf['udp']['host'] = None
		elif conf['udp']['host'] == '':
			conf['udp']['host'] = None

		cli = client(name=key, rconhost=conf['rcon']['host'], rconport=conf['rcon']['port'],
					rconpass=conf['rcon']['password'],
					udphost=conf['udp']['host'], udpport=conf['udp']['port'], schedobj=timers)

		for rkey in conf['relays']:
			for rel in conf['relays'][rkey]:
				filters = []
				for fname in rel['filters']:
					filt = _getfilter(fname)
					if filt != None:
						filters.append(filt)
				if len(filters) < 1:
					filters = None
				cli.relay_add(rel['type'], rel['name'], rel['channel'], rel['prefix'], rkey, filters)

		cli.connect()
		clients[key] = cli

def sockets():
	return client.sockets

def _getfilter(name):
	global filterobjs, filterclasses

	if not name.lower() in filterobjs:
		return None

	return filterobjs[name.lower()]

def _cleanformatting(text):
	s = text.replace(u'§0', '')
	s = s.replace(u'§1', '')
	s = s.replace(u'§2', '')
	s = s.replace(u'§3', '')
	s = s.replace(u'§4', '')
	s = s.replace(u'§5', '')
	s = s.replace(u'§6', '')
	s = s.replace(u'§7', '')
	s = s.replace(u'§8', '')
	s = s.replace(u'§9', '')
	s = s.replace(u'§a', '')
	s = s.replace(u'§b', '')
	s = s.replace(u'§c', '')
	s = s.replace(u'§d', '')
	s = s.replace(u'§e', '')
	s = s.replace(u'§f', '')
	s = s.replace(u'§k', '')
	s = s.replace(u'§l', '')
	s = s.replace(u'§m', '')
	s = s.replace(u'§n', '')
	s = s.replace(u'§o', '')
	return s.replace(u'§r', '')

def _formatmctoirc(text):
	s = text.replace(u'§0', '\x0301')
	s = s.replace(u'§1', '\x0302')
	s = s.replace(u'§2', '\x0303')
	s = s.replace(u'§3', '\x0310')
	s = s.replace(u'§4', '\x0305')
	s = s.replace(u'§5', '\x0306')
	s = s.replace(u'§6', '\x0307')
	s = s.replace(u'§7', '\x0315')
	s = s.replace(u'§8', '\x0314')
	s = s.replace(u'§9', '\x0312')
	s = s.replace(u'§a', '\x0309')
	s = s.replace(u'§b', '\x0311')
	s = s.replace(u'§c', '\x0304')
	s = s.replace(u'§d', '\x0313')
	s = s.replace(u'§e', '\x0308')
	s = s.replace(u'§f', '\x0300')
	s = s.replace(u'§k', '')
	s = s.replace(u'§l', '\x02')
	s = s.replace(u'§m', '')
	s = s.replace(u'§n', '\x1F')
	s = s.replace(u'§o', '\x1D')
	return s.replace(u'§r', '\x0F')

class client:
	sockets = []
	_jsonfixreg = None
	_cmdoutputrep = {'players': '^(There are \d+ of a max of \d+ players online:) ?(.*?)$'}
	_cmdoutputres = {}

	def __init__(self, name, rconhost='127.0.0.1', rconport=25575, rconpass='',
			udphost=None, udpport=25585, schedobj=None, schedpri=100):
		self.name = name
		self._rcon = {'host': rconhost, 'port': rconport, 'password': rconpass}
		self._rconsock = None
		self._rconconnected = False
		self._rconid = 0
		self._rconbuf = ''
		self._rconidbuf = {'id': -1, 'buf': ''}
		self._udp = {'host': udphost, 'port': udpport}
		self._udpsock = None
		self._sched = schedobj
		self._schedpri = schedpri
		self._relays = {}
		self._schedevs = {'conn': None, 'login': None, 'expirecalls': None}
		self._connfreq = 10
		self._rcontimeout = 10
		self._rconcalls = {}
		self._rconexpiretimeout = 30
		if self._sched == None:
			self._sched = sched.scheduler(time.time, time.sleep)
		relay.bind('minecraft', self.name, self._relaycallback)

	def __del__(self):
		try:
			self.disconnect("Shutting down")
			relay.unbind('minecraft', self.name, self._relaycallback)
			self._deltimer(self._schedevs['expirecalls'])
		except:
			pass

	def _nullcallback(self, *args, **kwargs):
		return

	def _addtimer(self, delay=10, callback=None, params=(), ts=None, pri=None):
		if pri == None:
			pri = self._schedpri
		if callback == None:
			callback = self._nullcallback

		if self._sched:
			if ts != None:
				return self._sched.enterabs(ts, pri, callback, params)
			else:
				return self._sched.enter(delay, pri, callback, params)

	def _deltimer(self, event):
		if self._sched:
			if event in self._sched.queue:
				self._sched.cancel(event)

	def _addsock(self):
		if self._rconsock != None:
			if not self._rconsock in self.sockets:
				rbsocket.bindsockcallbacks(self._rconsock, self._dodisconnect, self._doerr, self._doread)
				self.sockets.append(self._rconsock)
		if self._udpsock != None:
			if not self._udpsock in self.sockets:
				rbsocket.bindsockcallbacks(self._udpsock, self._dodisconnect, self._doerr, self._doread)
				self.sockets.append(self._udpsock)

	def _delsock(self, doudp=False):
		if self._rconsock in self.sockets:
			rbsocket.unbindsockcallbacks(self._rconsock)
			self.sockets.remove(self._rconsock)
		if doudp and self._udpsock in self.sockets:
			rbsocket.unbindsockcallbacks(self._udpsock)
			self.sockets.remove(self._udpsock)

	def _doread(self, sock):
		if sock == self._udpsock:
			try:
				buf, src = self._udpsock.recvfrom(4096)
			except:
				buf = ''
				src = ('0.0.0.0', 0)
			if buf != '':
				log.protocol('UDP:[' + src[0] + ']:' + str(src[1]) + ' <-- ' + buf, self)
				if buf[0] == ',':
					buf = buf[1:]
				try:
					if self._jsonfixreg == None:
						self._jsonfixreg = re.compile('^(.*?"message":")(.*)("})$')
					m = self._jsonfixreg.match(buf)
					jsonbuf = buf
					if m != None:
						s = m.group(2).replace('\\"', '"')
						s = s.replace('\\', '\\\\')
						jsonbuf = m.group(1) + s.replace('"', '\\"') + m.group(3)
					jsonobj = json.loads(jsonbuf)
				except Exception as e:
					return
				try:
					udpobj = MCUDPLogPacket(jsonobj['timeMillis'], jsonobj['loggerName'], jsonobj['message'], jsonobj['thread'], jsonobj['level'])
					self._handleudp(udpobj)
				except Exception as e:
					log.error('UDP Error handling UDP log packet: ' + str(e), self)
		if sock == self._rconsock:
			try:
				buf = self._rconsock.recv(4096)
			except:
				buf = ''

			if (buf == ''):
				log.info('RCON Received no data from ' + self._rcon['host'] + ', attemoting to reconnect', self)
				self.disconnect('', False)
				self._schedconnect()
				return

			if buf != '':
				log.debug('RCON <-- ' + binascii.hexlify(buf), self)

				self._rconbuf = self._rconbuf + buf

				while True:
					if len(self._rconbuf) < 4:
						break

					size = unpack('<i', self._rconbuf[0:4])
					size = size[0]

					if len(self._rconbuf) < size + 4:
						break

					log.debug('RCON Parsing packet: ' + binascii.hexlify(self._rconbuf[:size + 4]), self)
					packet = self._rconbuf[4:size + 4]
					self._rconbuf = self._rconbuf[size + 4:]
					if self._rconbuf != '':
						log.debug('RCON Remaining packet: ' + binascii.hexlify(self._rconbuf), self)

					if size == 10:
						payload = ''
						(idin, type, padding) = unpack('<ii2s', packet)
					elif size > 10:
						(idin, type, payload, padding) = unpack('<ii' + str(size-10) + 's2s', packet)
					else:
						log.debug('RCON Packet with erroneous length (' + str(size) + '): ' + binascii.hexlify(packet), self)
						continue

					log.protocol('RCON <-- id:' + str(idin) + ', type:' + str(type) + ', payload:' + payload, self)

					if self._rconidbuf['id'] != idin:
						if self._rconidbuf['id'] != -1:
							log.debug('RCON Unparsed packet being dropped with id ' + self._rconidbuf['id'], self)
						self._rconidbuf = {'id': idin, 'buf': ''}
					self._rconidbuf['buf'] = self._rconidbuf['buf'] + payload

					if size != 4106:
						rcon = MCRConPacket(idin, type, self._rconidbuf['buf'])
						log.debug('RCON Handling packet: ' + str(rcon), self)
						self._rconidbuf = {'id': -1, 'buf': ''}

						try:
							self._rconhandle(rcon)
						except Exception as e:
							log.error('RCON Error handling RCON packet: ' + str(e), self)

	def _doerr(self, sock):
		return

	def _dodisconnect(self, sock, msg):
		self.disconnect(msg, True, True)

	def _handleudp(self, udpobj):
		self._callrelay(None, udpobj, what='udp', schannel='udp')

	def _callrelay(self, text, obj, type=None, name=None, channel=None, what='', schannel=''):
		found = False
		for key in self._relays:
			if key != what and what != 'all':
				continue
			for rel in self._relays[key]:
				if type != None and rel.type != type:
					continue
				if name != None and rel.name != name:
					continue
				if channel != None and rel.channel != channel.lower():
					continue
				found = True
				rtext = text
				if rel.extra['prefix'] != '' and text != None and text != '':
					rtext = rel.extra['prefix'] + ' ' + text
				relay.call(rtext, rel, relay.RelaySource('minecraft', self.name, schannel, {}), {'obj': obj})
		if not found:
			rel = relay.RelayTarget(type, name, channel, {}, None)
			rtext = text
			if text != None and text != '':
				rtext = '[' + self.name + ']' + ' ' + text
			relay.call(rtext, rel, relay.RelaySource('minecraft', self.name, schannel, {}), {'obj': obj})

	def _schedconnect(self, freq=None):
		if freq == None:
			freq = self._connfreq
		if self._schedevs['conn'] != None:
			return
		self._schedevs['conn'] = self._addtimer(delay=freq, callback=self.connect)
		log.info('RCON Attempting to reconnect in ' + str(freq) + ' seconds', self)

	def _rconsend(self, id=0, type=0, payload=None):
		if self._rconsock == None:
			return

		packet = pack('<ii', id, type)
		if payload != None:
			packet += payload
		else:
			payload = ''
		packet = packet + '\x00\x00'

		packet = pack('<i', len(packet)) + packet

		log.debug('RCON --> ' + binascii.hexlify(packet), self)
		log.protocol('RCON --> id:' + str(id) + ', type:' + str(type) + ', payload:' + payload, self)

		try:
			self._rconsock.send(packet)
		except Exception as e:
			log.error('RCON Error sending to RCON: ' + str(e), self)
			self.disconnect('', False)
			self._schedconnect()

	def _rconhandle(self, rcon):
		if rcon.id == -1 and rcon.type == 2:
			self.disconnect()
			log.error('RCON Unable to login to RCON, will not attempt to reconnect', self)
		elif rcon.type == 2:
			self._rconconnected = True
			self._deltimer(self._schedevs['login'])
			self._schedevs['login'] = None
			log.info('RCON Sucessfully logged in to RCON', self)
			self._callrelay(None, rcon, what='rcon', schannel='rcon')
		elif rcon.type == 0:
			if rcon.id in self._rconcalls:
				log.debug('RCON Handling callback for RCON response', self)
				if self._rconcalls[rcon.id].callback != None:
					self._rconcalls[rcon.id].callback(rcon, self._rconcalls[rcon.id])
				del self._rconcalls[rcon.id]

	def _rcontimeout(self):
		if self._rconconnected:
			log.error('RCON Timed out logging in to RCON, attempting to reconnect', self)
		self.disconnect()
		self._schedconnect()

	def _cmd_players(self, rcon, rconcall):
		try:
			if not 'players' in self._cmdoutputres:
				self._cmdoutputres['players'] = re.compile(self._cmdoutputrep['players'])
			m = self._cmdoutputres['players'].match(rcon.payload)
			if m != None:
				first = m.group(1)
				if m.group(2) == '':
					first = first[0:-1]
				self._callrelay(first, rcon, rconcall.args[0].type, rconcall.args[0].name, rconcall.args[0].channel, what='rcon', schannel='rcon')
				if m.group(2) != '':
					self._callrelay(m.group(2), rcon, rconcall.args[0].type, rconcall.args[0].name, rconcall.args[0].channel, what='rcon', schannel='rcon')
		except Exception as e:
			log.error('RCON Error handling RCON players list response: ' + str(e), self)

	def _relaycallback(self, data):
		if self._rconconnected:
			if data.source.type == 'irc':
				if data.extra['msg']['params'][-1][0:8] == '?players':
					self._rconcommand('list', self._cmd_players, [data.source, data.extra['msg']])
					return
			if data.target.channel == 'rcon':
				callback = None
				args = None
				if 'callback' in data.extra:
					callback = data.extra['callback']
				if 'args' in data.extra:
					args = data.extra['args']
				self._rconcommand(data.text, callback, args)
			else:
				parts = []
				for part in filter(None, re.split('(https?://[^\s]+)', data.text)):
					if part[0:7] == 'http://' or part[0:8] == 'https://':
						parts.append({'text':part, 'underlined':True, 'clickEvent':{'action':'open_url', 'value':part}})
					else:
						parts.append(part)
				#parts = [data.text]
				self._rconcommand('tellraw @a ' + json.dumps(parts))

	def _rconexpirecalls(self):
		delids = []
		for id in self._rconcalls:
			if self._rconcalls[id].time + self._rconexpiretimeout > time.time():
				log.debug('RCON Expiring RCON callback: ' + str(self._rconcalls[id]), self)
				delids.append(id)
		for id in delids:
			del self._rconcalls[id]
		self._schedevs['expirecalls'] = self._addtimer(delay=self._rconexpiretimeout, callback=self._rconexpirecalls)

	def _rconcommand(self, command, callback=None, args=None):
		id = self._rconid
		self._rconid = self._rconid + 1
		if self._rconid > 0xffffffff:
			self._rconid = 0

		if callback != None:
			self._rconcalls[id] = MCRConCallback(callback=callback, time=time.time(), args=args, command=command)

		self._rconsend(id, 2, command)

	def connect(self, reconudp=False):
		self._rconsock = None
		self._rconconnected = False
		if self._schedevs['conn'] != None:
			self._deltimer(self._schedevs['conn'])
		self._schedevs['conn'] = None

		if reconudp or self._udpsock == None:
			log.info('UDP Attempting to bind to port ' + str(self._udp['port']) + ' on host ' + self._udp['host'], self)

			if self._udpsock != None:
				self._udpsock.close()
				self._udpsock = None
			addrs = []
			try:
				addrs = socket.getaddrinfo(self._udp['host'], self._udp['port'], 0, 0, socket.IPPROTO_UDP)
			except Exception as e:
				log.error('UDP Error binding UDP socket: ' + str(e), self)

			if len(addrs) < 1:
				return

			af, socktype, proto, canonname, sa = addrs[0]
			try:
				s = rbsocket.rbsocket(af, socktype, proto)
			except Exception as e:
				log.error('UDP Error creating UDP socket: ' + str(e), self)
				return

			try:
				s.bind(sa)
			except Exception as e:
				log.error('UDP Error binding UDP socket: ' + str(e), self)
				return

			self._udpsock = s

			log.info('UDP Bound to port ' + str(self._udp['port']) + ' on host ' + self._udp['host'], self)

		log.info('RCON Attempting to connect to ' + self._rcon['host'] + ' on port ' + str(self._rcon['port']), self)

		addrs = []
		try:
			addrs = socket.getaddrinfo(self._rcon['host'], self._rcon['port'], 0, 0, socket.IPPROTO_TCP)
		except Exception as e:
			log.error('RCON Error connecting rcon socket: ' + str(e), self)

		if len(addrs) < 1:
			return

		s = None
		ex = []
		for addr in addrs:
			af, socktype, proto, canonname, sa = addr
			try:
				s = rbsocket.rbsocket(af, socktype, proto)
			except Exception as e:
				s = None
				continue

			try:
				s.connect(sa)
			except Exception as e:
				s.close()
				s = None
				ex.append(e)
				continue
			break

		if s == None:
			log.error('RCON Error connecting to rcon: ' + str(ex[-1]), self)
			self._schedconnect()
			return

		self._rconsock = s

		self._rconsend(self._rconid, 3, self._rcon['password'])
		self._rconid += 1

		self._schedevs['login'] = self._addtimer(delay=self._rcontimeout, callback=self._rcontimeout)
		self._schedevs['expirecalls'] = self._addtimer(delay=self._rconexpiretimeout, callback=self._rconexpirecalls)

		self._addsock()

		log.info('RCON Connected to rcon socket, waiting for logon confirmation', self)

	def disconnect(self, reason = '', sendexit = True, closeudp = False):
		self._delsock(closeudp)

		if self._rconsock != None:
			self._rconsock.close()
		self._rconsock = None
		self._rconid = 0
		self._rconconnected = False

		if closeudp:
			if self._udpsock != None:
				self._udpsock.close()
			self._udpsock = None

	def relay_add(self, type, name, channel, prefix, what=None, filters=None):
		rel = relay.RelayTarget(type, name, channel, {'prefix': prefix}, filters)
		if not what in self._relays:
			self._relays[what] = [rel]
		else:
			self._relays[what].append(rel)
		log.debug('Added relay rule (type:' + type + ', name:' + name + ', channel:' + channel + ', prefix=' + prefix + ')', self)

class playerdeathfilter:
	_deathreg = ['^.*? was doomed to fall$',
				'^.*? withered away$',
				'^.*? was killed by .*? trying to hurt .*?$',
				'^.*? was poked to death by a sweet berry bush whilst trying to escape .*?$',
				'^.*? fell off some weeping vines$',
				'^.*? was slain by .*?$',
				'^.*? fell too far and was finished by .*? using .*?$',
				'^.*? was killed by .*?$',
				'^.*? was roasted in dragon breath by .*?$',
				'^.*? was killed trying to hurt .*?$',
				'^.*? was slain by .*? using .*?$',
				'^.*? was squished too much$',
				'^.*? was roasted in dragon breath$',
				'^.*? tried to swim in lava to escape .*?$',
				'^.*? was blown up by .*? using .*?$',
				'^.*? discovered the floor was lava$',
				'^.*? fell off some vines$',
				'^.*? was impaled by .*? with .*?$',
				'^.*? was pummeled by .*? using .*?$',
				'^.*? fell too far and was finished by .*?$',
				'^.*? suffocated in a wall$',
				'^.*? went off with a bang due to a firework fired from .*? by .*?$',
				'^.*? withered away whilst fighting .*?$',
				'^.*? was impaled by .*?$',
				'^.*? was poked to death by a sweet berry bush$',
				'^.*? burned to death$',
				'^.*? was shot by .*?$',
				'^.*? was stung to death$',
				'^Actually, message was too long to deliver fully. Sorry! Here\'s stripped version: .*?$',
				'^.*? starved to death whilst fighting .*?$',
				'^.*? was squashed by .*?$',
				'^.*? didn\'t want to live in the same world as .*?$',
				'^.*? fell out of the world$',
				'^.*? was killed by .*? using magic$',
				'^.*? was doomed to fall by .*? using .*?$',
				'^.*? was shot by .*? using .*?$',
				'^.*? went up in flames$',
				'^.*? was squashed by a falling block whilst fighting .*?$',
				'^.*? was blown up by .*?$',
				'^.*? was killed by .*? using .*?$',
				'^.*? was struck by lightning whilst fighting .*?$',
				'^.*? went off with a bang whilst fighting .*?$',
				'^.*? was killed by magic$',
				'^.*? was squashed by a falling anvil$',
				'^.*? walked into fire whilst fighting .*?$',
				'^.*? was shot by a .*?\'s skull$',
				'^.*? was burnt to a crisp whilst fighting .*?$',
				'^.*? died because of .*?$',
				'^.*? was squashed by a falling block$',
				'^.*? was stung to death by .*?$',
				'^.*? drowned$',
				'^.*? tried to swim in lava$',
				'^.*? experienced kinetic energy$',
				'^.*? walked into a cactus whilst trying to escape .*?$',
				'^.*? fell off some twisting vines$',
				'^.*? hit the ground too hard$',
				'^.*? was fireballed by .*?$',
				'^.*? suffocated in a wall whilst fighting .*?$',
				'^.*? was fireballed by .*? using .*?$',
				'^.*? went off with a bang$',
				'^.*? fell off a ladder$',
				'^.*? was killed by even more magic$']

	_deathregc = []

	def filter(self, data):
		if data.source.type != 'minecraft' or \
			data.source.channel != 'udp':
			return relay.FILTER_NOMATCH, None
		if not 'obj' in data.extra:
			return relay.FILTER_NOMATCH, None
		if type(data.extra['obj']) != MCUDPLogPacket:
			return relay.FILTER_NOMATCH, None
		if data.extra['obj'].logger != 'net.minecraft.server.MinecraftServer':
			return relay.FILTER_NOMATCH, None

		if len(self._deathregc) < 1:
			for reg in self._deathreg:
				self._deathregc.append(re.compile(reg, re.S))

		for reg in self._deathregc:
			m = reg.match(data.extra['obj'].message)
			if m != None:
				text = _formatmctoirc(data.extra['obj'].message)
				if 'prefix' in data.target.extra and data.target.extra['prefix'] != None and data.target.extra['prefix'] != '':
					text = data.target.extra['prefix'] + ' ' + text
				ret = data._replace(text=text)
				return relay.FILTER_MATCH, ret

		return relay.FILTER_NOMATCH, None

class playerjoinpartfilter:
	_reg = {
			'net.minecraft.server.MinecraftServer': {
				'joinpart': '^(.+?) (\\(formerly known as .+?\\) )?(?:joined|left) the game$'
				},
			'aba': {
				'whitelist': '^com.mojang.authlib.GameProfile.*?id=([-a-f0-9]+?),.*?name=([^,]+?),.+?\\(\\/([0-9\\.]+?):([0-9]+?)\\) lost connection: You are not white-listed on this server!.*$'
				}
			}
	_regc = {
			'net.minecraft.server.MinecraftServer': {},
			'aba': {}
			}

	def filter(self, data):
		if data.source.type != 'minecraft' or \
			data.source.channel != 'udp':
			return relay.FILTER_NOMATCH, None
		if not 'obj' in data.extra:
			return relay.FILTER_NOMATCH, None
		if type(data.extra['obj']) != MCUDPLogPacket:
			return relay.FILTER_NOMATCH, None
		if not data.extra['obj'].logger in self._reg:
			return relay.FILTER_NOMATCH, None

		for key in self._reg[data.extra['obj'].logger]:
			if not key in self._regc[data.extra['obj'].logger]:
				self._regc[data.extra['obj'].logger][key] = re.compile(self._reg[data.extra['obj'].logger][key])

			m = self._regc[data.extra['obj'].logger][key].match(data.extra['obj'].message)

			if m != None:
				ret = data
				if key == 'joinpart':
					text = _formatmctoirc(data.extra['obj'].message)
					if 'prefix' in data.target.extra and data.target.extra['prefix'] != None and data.target.extra['prefix'] != '':
						text = data.target.extra['prefix'] + ' ' + text
					ret = data._replace(text=text)
				elif key == 'whitelist':
					name = m.group(2)
					ip = m.group(3)
					text = '*** Connection from ' + ip + ' rejected (not whitelisted: ' + name + ')'
					if 'prefix' in data.target.extra and data.target.extra['prefix'] != None and data.target.extra['prefix'] != '':
						text = data.target.extra['prefix'] + ' ' + text
					ret = data._replace(text=text)
				return relay.FILTER_MATCH, ret
		return relay.FILTER_NOMATCH, None

class playerchatfilter:
	_reg = {
			'net.minecraft.server.MinecraftServer': {
				'chatmsg': '^(<)(.+?)(>) (.*)$',
				'chatmsgsrv': '^(\\[)([^ ]+?)(\\]) (.*)$',
				'chatact': '^\\* ([^ ]+) (.*)$',
				'achievment': '^(.+?) has (lost|just earned) the achievement \[.*?\]$',
				'advancement': '^(.+?) has made the advancement \[.*?\]$',
				'challenge': '^(.+?) has completed the challenge \[.*?\]$',
				'goal': '^(.+?) has reached the goal \[.*?\]$'
				},
			}
	_regc = {
			'net.minecraft.server.MinecraftServer': {}
			}

	def filter(self, data):
		if data.source.type != 'minecraft' or \
			data.source.channel != 'udp':
			return relay.FILTER_NOMATCH, None
		if not 'obj' in data.extra:
			return relay.FILTER_NOMATCH, None
		if type(data.extra['obj']) != MCUDPLogPacket:
			return relay.FILTER_NOMATCH, None
		if not data.extra['obj'].logger in self._reg:
			return relay.FILTER_NOMATCH, None

		for key in self._reg[data.extra['obj'].logger]:
			if not key in self._regc[data.extra['obj'].logger]:
				self._regc[data.extra['obj'].logger][key] = re.compile(self._reg[data.extra['obj'].logger][key])

			m = self._regc[data.extra['obj'].logger][key].match(data.extra['obj'].message)

			if m != None:
				ret = data
				text = _formatmctoirc(data.extra['obj'].message)
				if key == 'chatmsg' or key == 'chatact' or key == 'chatmsgsrv':
					name = ''
					npre = ''
					nsuf = ''
					text = ''
					if key == 'chatmsg' or key == 'chatmsgsrv':
						npre = m.group(1)
						name = m.group(2)
						nsuf = m.group(3)
						text = m.group(4)
					else:
						npre = '* '
						name = m.group(1)
						text = m.group(2)
					name = _formatmctoirc(name)
					text = npre + name + nsuf + ' ' + _formatmctoirc(text)
				if 'prefix' in data.target.extra and data.target.extra['prefix'] != None and data.target.extra['prefix'] != '':
					text = data.target.extra['prefix'] + ' ' + text
				ret = data._replace(text=text)
				return relay.FILTER_MATCH, ret
		return relay.FILTER_NOMATCH, None

class crashfilter:
	_reg = {'uj': '^This crash report has been saved to'}
	_regc = {'uj': None}

	def filter(self, data):
		if data.source.type != 'minecraft' or \
			data.source.channel != 'udp':
			return relay.FILTER_NOMATCH, None
		if not 'obj' in data.extra:
			return relay.FILTER_NOMATCH, None
		if type(data.extra['obj']) != MCUDPLogPacket:
			return relay.FILTER_NOMATCH, None
		if not data.extra['obj'].logger in self._reg:
			return relay.FILTER_NOMATCH, None
		if data.extra['obj'].level != 'ERROR':
			return relay.FILTER_NOMATCH, None
		if data.extra['obj'].thread != 'Server Watchdog':
			return relay.FILTER_NOMATCH, None

		if self._regc[data.extra['obj'].logger] is None:
			self._regc[data.extra['obj'].logger] = re.compile(self._reg[data.extra['obj'].logger])

		m = self._regc[data.extra['obj'].logger].match(data.extra['obj'].message)
		if m != None:
			ret = data._replace(text='ERROR: The server has crashed')
			return relay.FILTER_MATCH, ret

		return relay.FILTER_NOMATCH, None


class overviewerfilter:
	def filter(self, data):
		if data.source.type != 'minecraft' or \
			data.source.channel != 'udp':
			return relay.FILTER_NOMATCH, None
		if not 'obj' in data.extra:
			return relay.FILTER_NOMATCH, None
		if type(data.extra['obj']) != MCUDPLogPacket:
			return relay.FILTER_NOMATCH, None
		if not data.extra['obj'].logger in ['crontab.overviewer', 'crontab.overviewerpoi']:
			return relay.FILTER_NOMATCH, None

		text = data.extra['obj'].message
		if 'prefix' in data.target.extra and data.target.extra['prefix'] != None and data.target.extra['prefix'] != '':
			text = data.target.extra['prefix'] + ' ' + text
		return relay.FILTER_MATCH, data._replace(text=text)

filterobjs['playerdeath'] = playerdeathfilter()
filterobjs['playerjoinpart'] = playerjoinpartfilter()
filterobjs['playerchat'] = playerchatfilter()
filterobjs['overviewer'] = overviewerfilter()
filterobjs['crash'] = crashfilter()
