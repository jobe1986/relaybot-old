# -*- coding: utf-8 -*- 

import socket
import sched
import time
import sys
import json
import re
import binascii
import time
from struct import pack, unpack
from modules.mysocket import mysocket

from modules.logging import *
import modules.relay as relay

configs = {}
clients = {}

def loadconfig(doc):
	global configs

	cliconfs = doc.findall('./minecraft')

	for cli in cliconfs:
		if not 'name' in cli.attrib:
			log(LOG_ERROR, '[Minecraft] !!! Minrcraft client config missing name attribute' + '\n')
			raise Exception('[Minecraft] !!! Minecraft client config missing name attribute')
		if cli.attrib['name'] in configs:
			log(LOG_ERROR, '[Minecraft] !!! Duplicate Minecraft config name' + '\n')
			raise Exception('[Minecraft] !!! Duplicate Minecraft config name')

		name = cli.attrib['name']
		configs[name] = {'rcon': {'host': '', 'port': '', 'password': ''}, 'udp': {'host': '', 'port': ''}}

		rcon = cli.find('./rcon')
		if not 'host' in rcon.attrib:
			log(LOG_ERROR, '[Minecraft] !!! Minrcraft client rcon config missing host attribute' + '\n')
			raise Exception('[Minecraft] !!! Minrcraft client rcon config missing host attribute')
		if not 'port' in rcon.attrib:
			log(LOG_ERROR, '[Minecraft] !!! Minrcraft client rcon config missing port attribute' + '\n')
			raise Exception('[Minecraft] !!! Minrcraft client rcon config missing port attribute')
		if not 'password' in rcon.attrib:
			log(LOG_ERROR, '[Minecraft] !!! Minrcraft client rcon config missing password attribute' + '\n')
			raise Exception('[Minecraft] !!! Minrcraft client rcon config missing password attribute')
		configs[name]['rcon'] = rcon.attrib

		udp = cli.find('./udp')
		if not 'port' in udp.attrib:
			log(LOG_ERROR, '[Minecraft] !!! Minrcraft client udp config missing port attribute' + '\n')
			raise Exception('[Minecraft] !!! Minrcraft client udp config missing port attribute')
		configs[name]['udp'] = udp.attrib

		rels = cli.findall('./relay')
		configs[name]['relays'] = []
		for rel in rels:
			if not 'type' in rel.attrib:
				log(LOG_ERROR, '[Minecraft] !!! Minecraft channel relay missing type attribute' + '\n')
				raise Exception('[Minecraft] !!! Minecraft channel relay missing type attribute')
			if not 'name' in rel.attrib:
				log(LOG_ERROR, '[Minecraft] !!! Minecraft channel relay missing name attribute' + '\n')
				raise Exception('[Minecraft] !!! Minecraft channel relay missing name attribute')
			if not 'channel' in rel.attrib:
				log(LOG_ERROR, '[Minecraft] !!! Minecraft channel relay missing channel attribute' + '\n')
				raise Exception('[Minecraft] !!! Minecraft channel relay missing channel attribute')
			if rel.attrib['type'] == 'minecraft' and rel.attrib['name'] == name:
				log(LOG_NORMAL, '[Minecraft] --- Ignoring attempt to relay Minecraft to itself\n')
				continue
			relnew = rel.attrib
			if not 'prefix' in relnew:
				relnew['prefix'] = '[' + name + ']'
			configs[name]['relays'].append(relnew)

def runconfig(timers):
	global configs
	global clients

	for key in configs.keys():
		conf = configs[key]
		if not 'host' in conf['udp']:
			conf['udp']['host'] = None
		elif conf['udp']['host'] == '':
			conf['udp']['host'] = None

		cli = client(name=key, rconhost=conf['rcon']['host'], rconport=conf['rcon']['port'],
					rconpass=conf['rcon']['password'],
					udphost=conf['udp']['host'], udpport=conf['udp']['port'], schedobj=timers)

		for rel in conf['relays']:
			cli.relay_add(None, rel['type'], rel['name'], rel['channel'], rel['prefix'])

		cli.connect()
		clients[key] = cli

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
			'^.+? fell out of the world']
	_deathres = []
	_cmdoutputrep = {'players': '^(There are \d+/\d+ players online:)(.*?)$'}
	_cmdoutputres = {}

	def __init__(self, name, rconhost='127.0.0.1', rconport=25575, rconpass='',
			udphost=None, udpport=25585, schedobj=None, schedpri=100):
		self._name = name
		self._rcon = {'host': rconhost, 'port': rconport, 'password': rconpass}
		self._rconsock = None
		self._rconconnected = False
		self._rconid = 0
		self._rconbuf = ''
		self._udp = {'host': udphost, 'port': udpport}
		self._udpsock = None
		self._sched = schedobj
		self._schedpri = schedpri
		self._relays = []
		self._schedevs = {'conn': None, 'login': None, 'expirecalls': None}
		self._connfreq = 10
		self._rcontimeout = 10
		self._rconcalls = {}
		self._rconexpiretimeout = 30
		if self._sched == None:
			self._sched = sched.scheduler(time.time, time.sleep)
		relay.bind('minecraft', self._name, self._relaycallback)

	def __del__(self):
		self.disconnect("Shutting down")
		relay.unbind('minecraft', self._name, self._relaycallback)
		self._deltimer(self._schedevs['expirecalls'])

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
			self._rconsock.setdoread(self._doread)
			self._rconsock.setdoerr(self._doerr)
			self._rconsock.setdodisconnect(self._dodisconnect)
			if not self._rconsock in self.sockets:
				self.sockets.append(self._rconsock)
		if self._udpsock != None:
			self._udpsock.setdoread(self._doread)
			self._udpsock.setdoerr(self._doerr)
			self._udpsock.setdodisconnect(self._dodisconnect)
			if not self._udpsock in self.sockets:
				self.sockets.append(self._udpsock)

	def _delsock(self):
		if self._rconsock in sockets:
			sockets.remove(self._rconsock)

	def _doread(self, sock):
		if sock == self._udpsock:
			try:
				buf, src = self._udpsock.recvfrom(4096)
			except:
				buf = ''
				src = ('0.0.0.0', 0)
			if buf != '':
				log(LOG_NORMAL, '[Minecraft::' + self._name + '::UDP::[' + src[0] + ']:' + str(src[1]) + '] <-- ' + buf + '\n')
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
				self._handlejson(jsonobj)
		if sock == self._rconsock:
			try:
				buf = self._rconsock.recv(4110)
			except:
				buf = ''
			if buf != '':
				log(LOG_NORMAL, '[Minecraft::' + self._name + '::RCON] <-- ' + binascii.hexlify(buf) + '\n')

				self._rconbuf = self._rconbuf + buf

				if len(self._rconbuf) < 4:
					return

				size = unpack('<i', self._rconbuf[0:4])
				size = size[0]
				
				if len(self._rconbuf) < size + 4:
					return

				packet = self._rconbuf[4:size + 4]
				self._rconbuf = self._rconbuf[size + 5:]

				(idin, type, payload, padding) = unpack('<ii' + str(size-10) + 's2s', packet)

				log(LOG_NORMAL, '[Minecraft::' + self._name + '::RCON] <-- id:' + str(idin) + ', type:' + str(type) + ', payload:' + payload + '\n')

				self._rconhandle(idin, type, payload)

	def _doerr(self, sock):
		return

	def _dodisconnect(self, sock, msg):
		self.disconnect(msg, True, True)

	def _handlejson(self, jsonobj):
		if jsonobj['logger'] == 'crontab.overviewer':
			self._callrelay(jsonobj['message'], jsonobj)
		elif jsonobj['logger'] == 'crontab.overviewerpoi':
			self._callrelay(jsonobj['message'], jsonobj)
		elif jsonobj['logger'] == 'net.minecraft.server.MinecraftServer':
			matched = False
			for key in self._regp.keys():
				if not key in self._regs:
					self._regs[key] = re.compile(self._regp[key], re.S)
				m = self._regs[key].match(jsonobj['message'])

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
					self._callrelay(npre + name + nsuf + ' ' + text, jsonobj)
				else:
					self._callrelay(self._formatmctoirc(m.group(0)), jsonobj)
				break
			if not matched:
				if self._isdeath(jsonobj['message']):
					self._callrelay(self._formatmctoirc(jsonobj['message']), jsonobj)
		elif jsonobj['logger'] == 'mg':
			for key in self._mgregp.keys():
				if not key in self._mgregs:
					self._mgregs[key] = re.compile(self._mgregp[key], re.S)
				m = self._mgregs[key].match(jsonobj['message'])

				if m == None:
					continue
				if key == 'whitelist':
					name = m.group(2)
					ip = m.group(3)
					self._callrelay('*** Connection from ' + ip + ' rejected (not whitelisted: ' + name + ')', jsonobj)

	def _callrelay(self, text, obj, type=None, name=None, channel=None):
		for rel in self._relays:
			if type != None and rel.type.lower() != type.lower():
				continue
			if name != None and rel.name.lower() != name.lower():
				continue
			if channel != None and rel.channel.lower() != channel.lower():
				continue
			rtext = text
			if rel.prefix != '':
				rtext = rel.prefix + ' ' + text
			relay.call(rel.type, rel.name, rel.channel, (rtext, 'minecraft', self._name, obj))

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
		log(LOG_NORMAL, '[Minecraft::' + self._name + '] --- Attempting to reconnect in ' + str(freq) + ' seconds\n')

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

		log(LOG_NORMAL, '[Minecraft::' + self._name + '::RCON] --> ' + binascii.hexlify(packet) + '\n')
		log(LOG_NORMAL, '[Minecraft::' + self._name + '::RCON] --> id:' + str(id) + ', type:' + str(type) + ', payload:' + payload + '\n')

		self._rconsock.send(packet)

	def _rconhandle(self, id, type, payload):
		if id == -1 and type == 2:
			self.disconnect()
			log(LOG_ERROR, '[Minecraft::' + self._name + '::RCON] !!! Unable to login to RCON, will not attempt to reconnect\n')
		if type == 2:
			self._rconconnected = True
			self._deltimer(self._schedevs['login'])
			self._schedevs['login'] = None
			log(LOG_NORMAL, '[Minecraft::' + self._name + '::RCON] --- Sucessfully logged in to RCON\n')
		if type == 0:
			if id in self._rconcalls:
				if self._rconcalls[id]['callback'] != None:
					self._rconcalls[id]['callback'](id, type, payload, self._rconcalls[id])
				del self._rconcalls[id]

	def _rcontimeout(self):
		if self._rconconnected:
			log(LOG_ERROR, '[Minecraft::' + self._name + '::RCON] !!! Timed out logging in to RCON, attempting to reconnect\n')
		self.disconnect()
		self._schedconnect()

	def _cmd_players(self, id, type, payload, rconcall):
		if not 'players' in self._cmdoutputres:
			self._cmdoutputres['players'] = re.compile(self._cmdoutputrep['players'])
		m = self._cmdoutputres['players'].match(payload)
		if m != None:
			self._callrelay(m.group(1), None, rconcall['args'][0], rconcall['args'][1], rconcall['args'][2]['params'][0])
			self._callrelay(m.group(2), None, rconcall['args'][0], rconcall['args'][1], rconcall['args'][2]['params'][0])

	def _relaycallback(self, channel, args):
		if self._rconconnected:
			if args[1] == 'irc':
				if args[3]['params'][-1][0:8] == '!players':
					self._rconcommand('list', self._cmd_players, (args[1], args[2], args[3]))
					return
			self._rconcommand('tellraw @a ' + json.dumps([args[0]]))

	def _rconexpirecalls(self):
		for id in self._rconcalls.keys():
			if self._rconcalls[id]['time'] + self._rconexpiretimeout > time.time():
				log(LOG_NORMAL, '[Minecraft::' + self._name + '] --- Expiring RCON callback: ' + str(self._rconcalls[id]) + '\n')
				del self._rconcalls[id]
		self._schedevs['expirecalls'] = self._addtimer(delay=self._rconexpiretimeout, callback=self._rconexpirecalls)

	def _rconcommand(self, command, callback=None, args=None):
		id = self._rconid
		self._rconid = self._rconid + 1

		if callback != None:
			self._rconcalls[id] = {'callback': callback, 'time': time.time(), 'args': args}

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
				log(LOG_ERROR, '[Minecraft::' + self._name + '] !!! Error binding UDP socket: ' + str(e) + '\n')

			if len(addrs) < 1:
				return

			af, socktype, proto, canonname, sa = addrs[0]
			try:
				s = mysocket(af, socktype, proto)
			except Exception as e:
				log(LOG_ERROR, '[Minecraft::' + self._name + '] !!! Error creating UDP socket: ' + str(e) + '\n')
				return

			try:
				s.bind(sa)
			except Exception as e:
				log(LOG_ERROR, '[Minecraft::' + self._name + '] !!! Error binding UDP socket: ' + str(e) + '\n')
				return

			self._udpsock = s

		addrs = []
		try:
			addrs = socket.getaddrinfo(self._rcon['host'], self._rcon['port'], 0, 0, socket.IPPROTO_TCP)
		except Exception as e:
			log(LOG_ERROR, '[Minecraft::' + self._name + '] !!! Error connecting rcon socket: ' + str(e) + '\n')

		if len(addrs) < 1:
			return

		s = None
		for addr in addrs:
			af, socktype, proto, canonname, sa = addr
			try:
				s = mysocket(af, socktype, proto)
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
			log(LOG_ERROR, '[Minecraft::' + self._name + '] !!! Error connecting to rcon\n')
			self._schedconnect()
			return

		self._rconsock = s

		self._rconsend(self._rconid, 3, self._rcon['password'])
		self._rconid += 1

		self._schedevs['login'] = self._addtimer(delay=self._rcontimeout, callback=self._rcontimeout)
		self._schedevs['expirecalls'] = self._addtimer(delay=self._rconexpiretimeout, callback=self._rconexpirecalls)

		self._addsock()

	def disconnect(self, reason = '', sendexit = True, closeudp = False):
		if self._rconsock != None:
			self._rconsock.close()
		self._rconsock = None
		self._rconid = -1
		self._rconconnected = False

		if closeudp:
			if self._udpsock != None:
				self._udpsock.close()
			self._udpsock = None

	def relay_add(self, relchan, type, name, channel, prefix):
		rel = relay.RelayChannel(type, name, channel, prefix)
		if not rel in self._relays:
			self._relays.append(rel)
		print self._relays
		log(LOG_NORMAL, '[Minecraft::' + self._name + '] --- Added relay rule (type:' + type + ', name:' + name + ', channel:' + channel + ', prefix=' + prefix + ')\n')
