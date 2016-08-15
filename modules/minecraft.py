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

configs = {}
clients = {}

def loadconfig(doc):
	global configs

	cliconfs = doc.findall('./minecraft')

	for cli in cliconfs:
		if not 'name' in cli.attrib:
			log.log(LOG_ERROR, 'Minrcraft client config missing name attribute')
			raise Exception('Minecraft client config missing name attribute')
		if cli.attrib['name'] in configs:
			log.log(LOG_ERROR, 'Duplicate Minecraft config name')
			raise Exception('Duplicate Minecraft config name')

		name = cli.attrib['name']
		configs[name] = {'rcon': {'host': '', 'port': '', 'password': ''}, 'udp': {'host': '', 'port': ''}, 'relays': {}}

		rcon = cli.find('./rcon')
		if not 'host' in rcon.attrib:
			log.log(LOG_ERROR, 'Minrcraft client rcon config missing host attribute')
			raise Exception('Minrcraft client rcon config missing host attribute')
		if not 'port' in rcon.attrib:
			log.log(LOG_ERROR, 'Minrcraft client rcon config missing port attribute')
			raise Exception('Minrcraft client rcon config missing port attribute')
		if not 'password' in rcon.attrib:
			log.log(LOG_ERROR, 'Minrcraft client rcon config missing password attribute')
			raise Exception('Minrcraft client rcon config missing password attribute')
		configs[name]['rcon'] = rcon.attrib

		udp = cli.find('./udp')
		if not 'port' in udp.attrib:
			log.log(LOG_ERROR, 'Minrcraft client udp config missing port attribute')
			raise Exception('Minrcraft client udp config missing port attribute')
		configs[name]['udp'] = udp.attrib

		rels = rcon.findall('./relay')
		for rel in rels:
			if not 'type' in rel.attrib:
				log.log(LOG_ERROR, 'Minecraft rcon relay missing type attribute')
				raise Exception('Minecraft rcon relay missing type attribute')
			if not 'name' in rel.attrib:
				log.log(LOG_ERROR, 'Minecraft rcon relay missing name attribute')
				raise Exception('Minecraft rcon relay missing name attribute')
			if not 'channel' in rel.attrib:
				log.log(LOG_ERROR, 'Minecraft rcon relay missing channel attribute')
				raise Exception('Minecraft rcon relay missing channel attribute')
			if rel.attrib['type'] == 'minecraft' and rel.attrib['name'] == name:
				log.log(LOG_INFO, 'Ignoring attempt to relay Minecraft to itself')
				continue
			relnew = rel.attrib
			if not 'prefix' in relnew:
				relnew['prefix'] = '[' + name + ']'
			if not 'rcon' in configs[name]['relays']:
				configs[name]['relays']['rcon'] = []
			configs[name]['relays']['rcon'].append(relnew)

		rels = udp.findall('./relay')
		for rel in rels:
			if not 'type' in rel.attrib:
				log.log(LOG_ERROR, 'Minecraft udp relay missing type attribute')
				raise Exception('Minecraft udp relay missing type attribute')
			if not 'name' in rel.attrib:
				log.log(LOG_ERROR, 'Minecraft udp relay missing name attribute')
				raise Exception('Minecraft udp relay missing name attribute')
			if not 'channel' in rel.attrib:
				log.log(LOG_ERROR, 'Minecraft udp relay missing channel attribute')
				raise Exception('Minecraft udp relay missing channel attribute')
			if rel.attrib['type'] == 'minecraft' and rel.attrib['name'] == name:
				log.log(LOG_INFO, 'Ignoring attempt to relay Minecraft to itself')
				continue
			relnew = rel.attrib
			if not 'prefix' in relnew:
				relnew['prefix'] = '[' + name + ']'
			if not 'udp' in configs[name]['relays']:
				configs[name]['relays']['udp'] = []
			configs[name]['relays']['udp'].append(relnew)

		rels = cli.findall('./relay')
		for rel in rels:
			if not 'type' in rel.attrib:
				log.log(LOG_ERROR, 'Minecraft channel relay missing type attribute')
				raise Exception('Minecraft channel relay missing type attribute')
			if not 'name' in rel.attrib:
				log.log(LOG_ERROR, 'Minecraft channel relay missing name attribute')
				raise Exception('Minecraft channel relay missing name attribute')
			if not 'channel' in rel.attrib:
				log.log(LOG_ERROR, 'Minecraft channel relay missing channel attribute')
				raise Exception('Minecraft channel relay missing channel attribute')
			if rel.attrib['type'] == 'minecraft' and rel.attrib['name'] == name:
				log.log(LOG_INFO, 'Ignoring attempt to relay Minecraft to itself')
				continue
			relnew = rel.attrib
			if not 'prefix' in relnew:
				relnew['prefix'] = '[' + name + ']'
			if not '' in configs[name]['relays']:
				configs[name]['relays'][''] = []
			configs[name]['relays'][''].append(relnew)

def runconfig(timers):
	global configs
	global clients

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
				cli.relay_add(rel['type'], rel['name'], rel['channel'], rel['prefix'], rkey)

		cli.connect()
		clients[key] = cli

def sockets():
	return client.sockets

class client:
	sockets = []
	_regp = {'chatmsg': '^([\\[<])([^ ]+?)([\\]>]) (.*)$',
			'chatact': '^\\* ([^ ]+) (.*)$',
			'userjoin': '^([^\s]+) (\\(formerly known as .+?\\) )?(?:joined|left) the game$',
			'achievment': '^([^\s]+?) has (lost|just earned) the achievement \[.*?\]$'}
	_regs = {}
	_mgregp = {'whitelist': '^com.mojang.authlib.GameProfile.*?id=([-a-f0-9]+?),.*?name=([^,]+?),.+?\\(\\/([0-9\\.]+?):([0-9]+?)\\) lost connection: You are not white-listed on this server!.*$'}
	_mgregs = {}
	_jsonfixreg = None
	_deathreg = ['^.+? fell off a ladder$',
			'^.+? fell off some vines$',
			'^.+? fell out of the water$',
			'^.+? fell from a high place$',
			'^.+? was doomed to fall$',
			'^.+? was doomed to fall by .+?$',
			'^.+? was doomed to fall by .+? using .+?$',
			'^.+? fell too far and was finished by .+?$',
			'^.+? fell too far and was finished by .+? using .+?$',
			'^.+? was struck by lightning$',
			'^.+? went up in flames$',
			'^.+? walked into fire whilst fighting .+?$',
			'^.+? burned to death$',
			'^.+? was burnt to a crisp whilst fighting .+?$',
			'^.+? tried to swim in lava$',
			'^.+? tried to swim in lava to escape .+?$',
			'^.+? discovered floor was lava$',
			'^.+? walked into danger zone due to .+?$',
			'^.+? suffocated in a wall$',
			'^.+? drowned$',
			'^.+? drowned whilst trying to escape .+?$',
			'^.+? starved to death$',
			'^.+? was pricked to death$',
			'^.+? walked into a cactus whilst trying to escape .+?$',
			'^.+? died$',
			'^.+? blew up$',
			'^.+? was blown up by .+?$',
			'^.+? was killed by magic$',
			'^.+? withered away$',
			'^.+? was squashed by a falling anvil$',
			'^.+? was squashed by a falling block$',
			'^.+? was slain by .+?$',
			'^.+? was slain by .+? using .+?$',
			'^.+? was shot by .+?$',
			'^.+? was shot by .+? using .+?$',
			'^.+? was fireballed by .+?$',
			'^.+? was fireballed by .+? using .+?$',
			'^.+? was pummeled by .+?$',
			'^.+? was pummeled by .+? using .+?$',
			'^.+? was killed by .+? using magic$',
			'^.+? was killed by .+? using .+?$',
			'^.+? was killed trying to hurt .+?$',
			'^.+? hit the ground too hard$',
			'^.+? fell out of the world$',
			'^.+? was roasted in dragon breath$',
			'^.+? experienced kinetic energy$']
	_deathres = []
	_cmdoutputrep = {'players': '^(There are \d+/\d+ players online:)(.*?)$'}
	_cmdoutputres = {}

	def __init__(self, name, rconhost='127.0.0.1', rconport=25575, rconpass='',
			udphost=None, udpport=25585, schedobj=None, schedpri=100):
		self.name = name
		self._rcon = {'host': rconhost, 'port': rconport, 'password': rconpass}
		self._rconsock = None
		self._rconconnected = False
		self._rconid = 0
		self._rconbuf = ''
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
				log.log(LOG_DEBUG, 'UDP:[' + src[0] + ']:' + str(src[1]) + ' <-- ' + buf, self)
				if buf[0] == ',':
					buf = buf[1:]
				try:
					if self._jsonfixreg == None:
						self._jsonfixreg = re.compile('^(.*?"message":")(.*)("})$')
					m = self._jsonfixreg.match(buf)
					jsonbuf = buf
					if m != None:
						s = m.group(2).replace('\\"', '"')
						jsonbuf = m.group(1) + s.replace('"', '\\"') + m.group(3)
					jsonobj = json.loads(jsonbuf)
				except Exception as e:
					return
				try:
					udpobj = MCUDPLogPacket(jsonobj['timestamp'], jsonobj['logger'], jsonobj['message'], jsonobj['thread'], jsonobj['level'])
					self._handleudp(udpobj)
				except Exception as e:
					log.log(LOG_ERROR, 'Error handling UDP log packet: ' + str(e))
		if sock == self._rconsock:
			try:
				buf = self._rconsock.recv(4110)
			except:
				buf = ''
			if buf != '':
				log.log(LOG_DEBUG, 'RCON <-- ' + binascii.hexlify(buf), self)

				self._rconbuf = self._rconbuf + buf

				while True:
					if len(self._rconbuf) < 4:
						break

					size = unpack('<i', self._rconbuf[0:4])
					size = size[0]
				
					if len(self._rconbuf) < size + 4:
						break

					log.log(LOG_DEBUG, 'RCON Parsing packet: ' + binascii.hexlify(self._rconbuf[:size + 4]), self)
					packet = self._rconbuf[4:size + 4]
					self._rconbuf = self._rconbuf[size + 5:]

					if size == 10:
						payload = ''
						(idin, type, padding) = unpack('<ii2s', packet)
					elif size > 10:
						(idin, type, payload, padding) = unpack('<ii' + str(size-10) + 's2s', packet)
					else:
						log.log(LOG_DEBUG, 'RCON Packet with erroneous length (' + str(size) + '): ' + binascii.hexlify(packet), self)
						continue

					log.log(LOG_DEBUG, 'RCON <-- id:' + str(idin) + ', type:' + str(type) + ', payload:' + payload, self)

					rcon = MCRConPacket(idin, type, payload)

					try:
						self._rconhandle(rcon)
					except Exception as e:
						log.log(LOG_ERROR, 'Error handling RCON packet: ' + str(e), self)

	def _doerr(self, sock):
		return

	def _dodisconnect(self, sock, msg):
		self.disconnect(msg, True, True)

	def _handleudp(self, udpobj):
		if udpobj.logger == 'crontab.overviewer':
			self._callrelay(udpobj.message, udpobj, schannel='udp')
		elif udpobj.logger == 'crontab.overviewerpoi':
			self._callrelay(udpobj.message, udpobj, schannel='udp')
		elif udpobj.logger == 'net.minecraft.server.MinecraftServer':
			matched = False
			for key in self._regp:
				if not key in self._regs:
					self._regs[key] = re.compile(self._regp[key], re.S)
				m = self._regs[key].match(udpobj.message)

				if m == None:
					continue

				matched = True

				if key == 'chatmsg' or key == 'chatact':
					name = ''
					npre = ''
					nsuf = ''
					text = ''
					if key == 'chatmsg':
						npre = m.group(1)
						name = m.group(2)
						nsuf = m.group(3)
						text = m.group(4)
					else:
						npre = '* '
						name = m.group(1)
						text = m.group(2)
					name = self._formatmctoirc(name)
					text = self._formatmctoirc(text)
					if name == 'Rcon':
						continue
					self._callrelay(npre + name + nsuf + ' ' + text, udpobj, schannel='udp')
				else:
					self._callrelay(self._formatmctoirc(m.group(0)), udpobj, schannel='udp')
				break
			if not matched:
				if self._isdeath(udpobj.message):
					self._callrelay(self._formatmctoirc(udpobj.message), udpobj, schannel='udp')
		elif udpobj.logger == 'mg':
			for key in self._mgregp:
				if not key in self._mgregs:
					self._mgregs[key] = re.compile(self._mgregp[key], re.S)
				m = self._mgregs[key].match(udpobj.message)

				if m == None:
					continue
				if key == 'whitelist':
					name = m.group(2)
					ip = m.group(3)
					self._callrelay('*** Connection from ' + ip + ' rejected (not whitelisted: ' + name + ')', udpobj, schannel='udp')
		self._callrelay(None, udpobj, what='udp', schannel='udp')

	def _callrelay(self, text, obj, type=None, name=None, channel=None, what='', schannel=''):
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
				rtext = text
				if rel.extra['prefix'] != '' and text != None and text != '':
					rtext = rel.extra['prefix'] + ' ' + text
				relay.call(rtext, rel, relay.RelaySource('minecraft', self.name, schannel, {}), {'obj': obj})

	def _cleanformatting(self, text):
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

	def _formatmctoirc(self, text):
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

	def _isdeath(self, message):
		if len(self._deathres) < 1:
			for reg in self._deathreg:
				self._deathres.append(re.compile(reg, re.S))

		for reg in self._deathres:
			m = reg.match(message)
			if m != None:
				return True

		return False

	def _schedconnect(self, freq=None):
		if freq == None:
			freq = self._connfreq
		if self._schedevs['conn'] != None:
			return
		self._schedevs['conn'] = self._addtimer(delay=freq, callback=self.connect)
		log.log(LOG_INFO, 'Attempting to reconnect in ' + str(freq) + ' seconds', self)

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

		log.log(LOG_DEBUG, 'RCON --> ' + binascii.hexlify(packet), self)
		log.log(LOG_DEBUG, 'RCON --> id:' + str(id) + ', type:' + str(type) + ', payload:' + payload, self)

		try:
			self._rconsock.send(packet)
		except Exception as e:
			log.log(LOG_ERROR, 'RCON Error sending to RCON: ' + str(e), self)
			self.disconnect('', False)
			self._schedconnect()

	def _rconhandle(self, rcon):
		if rcon.id == -1 and rcon.type == 2:
			self.disconnect()
			log.log(LOG_ERROR, 'RCON Unable to login to RCON, will not attempt to reconnect', self)
		if rcon.type == 2:
			self._rconconnected = True
			self._deltimer(self._schedevs['login'])
			self._schedevs['login'] = None
			log.log(LOG_INFO, 'RCON Sucessfully logged in to RCON', self)
		if rcon.type == 0:
			if rcon.id in self._rconcalls:
				if self._rconcalls[rcon.id]['callback'] != None:
					self._rconcalls[rcon.id]['callback'](rcon, self._rconcalls[rcon.id])
				del self._rconcalls[rcon.id]

	def _rcontimeout(self):
		if self._rconconnected:
			log.log(LOG_ERROR, 'RCON Timed out logging in to RCON, attempting to reconnect', self)
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
				self._callrelay(first, rcon, rconcall['args'][0].type, rconcall['args'][0].name, rconcall['args'][0].channel, schannel='rcon')
				if m.group(2) != '':
					self._callrelay(m.group(2), rcon, rconcall['args'][0].type, rconcall['args'][0].name, rconcall['args'][0].channel, schannel='rcon')
		except Exception as e:
			log.log(LOG_ERROR, 'Error handling RCON players list response: ' + str(e), self)

	def _relaycallback(self, data):
		if self._rconconnected:
			if data.source.type == 'irc':
				if data.extra['msg']['params'][-1][0:8] == '?players':
					self._rconcommand('list', self._cmd_players, (data.source, data.extra['msg']))
					return
			self._rconcommand('tellraw @a ' + json.dumps([data.text]))

	def _rconexpirecalls(self):
		delids = []
		for id in self._rconcalls:
			if self._rconcalls[id]['time'] + self._rconexpiretimeout > time.time():
				log.log(LOG_INFO, 'Expiring RCON callback: ' + str(self._rconcalls[id]), self)
				delids.append(id)
		for id in delids:
			del self._rconcalls[id]
		self._schedevs['expirecalls'] = self._addtimer(delay=self._rconexpiretimeout, callback=self._rconexpirecalls)

	def _rconcommand(self, command, callback=None, args=None):
		id = self._rconid
		self._rconid = self._rconid + 1

		if callback != None:
			self._rconcalls[id] = {'callback': callback, 'time': time.time(), 'args': args, 'command': command}

		self._rconsend(id, 2, command)

	def connect(self, reconudp=False):
		self._rconsock = None
		self._rconconnected = False

		if reconudp or self._udpsock == None:
			if self._udpsock != None:
				self._udpsock.close()
				self._udpsock = None
			addrs = []
			try:
				addrs = socket.getaddrinfo(self._udp['host'], self._udp['port'], 0, 0, socket.IPPROTO_UDP)
			except Exception as e:
				log.log(LOG_ERROR, 'Error binding UDP socket: ' + str(e), self)

			if len(addrs) < 1:
				return

			af, socktype, proto, canonname, sa = addrs[0]
			try:
				s = rbsocket.rbsocket(af, socktype, proto)
			except Exception as e:
				log.log(LOG_ERROR, 'Error creating UDP socket: ' + str(e), self)
				return

			try:
				s.bind(sa)
			except Exception as e:
				log.log(LOG_ERROR, 'Error binding UDP socket: ' + str(e), self)
				return

			self._udpsock = s

		addrs = []
		try:
			addrs = socket.getaddrinfo(self._rcon['host'], self._rcon['port'], 0, 0, socket.IPPROTO_TCP)
		except Exception as e:
			log.log(LOG_ERROR, 'Error connecting rcon socket: ' + str(e), self)

		if len(addrs) < 1:
			return

		s = None
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
				continue
			break

		if s == None:
			log.log(LOG_ERROR, 'Error connecting to rcon', self)
			self._schedconnect()
			return

		self._rconsock = s

		self._rconsend(self._rconid, 3, self._rcon['password'])
		self._rconid += 1

		self._schedevs['login'] = self._addtimer(delay=self._rcontimeout, callback=self._rcontimeout)
		self._schedevs['expirecalls'] = self._addtimer(delay=self._rconexpiretimeout, callback=self._rconexpirecalls)

		self._addsock()

		log.log(LOG_INFO, 'Connected to rcon socket, waiting for logon confirmation', self)

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

	def relay_add(self, type, name, channel, prefix, what=None):
		rel = relay.RelayTarget(type, name, channel, {'prefix': prefix})
		if not what in self._relays:
			self._relays[what] = [rel]
		else:
			self._relays[what].append(rel)
		log.log(LOG_INFO, 'Added relay rule (type:' + type + ', name:' + name + ', channel:' + channel + ', prefix=' + prefix + ')', self)
