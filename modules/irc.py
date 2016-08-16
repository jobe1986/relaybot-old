# -*- coding: utf-8 -*-

# RelayBot - Simple Multi-protocol Relay Bot, modules/irc.py
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

import socket, sched, time, sys

from core.rblogging import *
import core.rbsocket as rbsocket
import core.relay as relay

configs = {}
clients = {}

def loadconfig(doc):
	global configs

	cliconfs = doc.findall('./irc')

	for irccli in cliconfs:
		if not 'name' in irccli.attrib:
			log.log(LOG_ERROR, 'IRC client config missing name attribute')
			raise Exception('IRC client config missing name attribute')
		if irccli.attrib['name'] in configs:
			log.log(LOG_ERROR, 'Duplicate IRC client config name')
			raise Exception('Duplicate IRC client config name')

		name = irccli.attrib['name']
		configs[name] = {'server': {}, 'user': {}, 'channels': []}

		servs = irccli.findall('./server')
		if len(servs) > 1:
			log.log(LOG_ERROR, 'Too many IRC client server elements')
			raise Exception('Too many IRC client server elements')
		if len(servs) < 1:
			log.log(LOG_ERROR, 'Missing IRC client server element')
			raise Exception('Missing IRC client server element')

		serv = servs[0]

		if not 'host' in serv.attrib:
			log.log(LOG_ERROR, 'IRC client server missing host attribute')
			raise Exception('IRC client server missing host attribute')
		if not 'port' in serv.attrib:
			log.log(LOG_ERROR, 'IRC client server missing port attribute')
			raise Exception('IRC client server missing port attribute')

		configs[name]['server'] = serv.attrib

		if not 'password' in serv.attrib:
			configs[name]['server']['password'] = None
		if configs[name]['server']['password'] == '':
			configs[name]['server']['password'] = None

		usrs = irccli.findall('./user')
		if len(usrs) > 1:
			log.log(LOG_ERROR, 'Too many IRC client user elements')
			raise Exception('Too many IRC client user elements')
		if len(usrs) < 1:
			log.log(LOG_ERROR, 'Missing IRC client user elements')
			raise Exception('Missing IRC client user elements')
		usr = usrs[0]

		configs[name]['user'] = usr.attrib

		if not 'nick' in usr.attrib:
			log.log(LOG_ERROR, 'IRC client user missing nick attribute')
			raise Exception('IRC client user missing nick attribute')
		if not 'user' in usr.attrib:
			log.log(LOG_ERROR, 'IRC client user missing user attribute')
			raise Exception('IRC client user missing user attribute')
		if not 'gecos' in usr.attrib:
			log.log(LOG_ERROR, 'IRC client user missing gecos attribute')
			raise Exception('IRC client user missing gecos attribute')

		chans = irccli.findall('./channel')
		configs[name]['relays'] = {}
		for chan in chans:
			if not 'name' in chan.attrib:
				continue
			cname = chan.attrib['name']
			if cname == '' or cname == None:
				continue
			configs[name]['channels'].append(cname)
			rels = chan.findall('./relay')
			for rel in rels:
				if not 'type' in rel.attrib:
					log.log(LOG_ERROR, 'IRC channel relay missing type attribute')
					raise Exception('IRC channel relay missing type attribute')
				if not 'name' in rel.attrib:
					log.log(LOG_ERROR, 'IRC channel relay missing name attribute')
					raise Exception('IRC channel relay missing name attribute')
				if not 'channel' in rel.attrib:
					raise Exception('IRC channel relay missing channel attribute')
					raise Exception('IRC channel relay missing channel attribute')
				if rel.attrib['type'] == 'irc' and rel.attrib['name'] == name and rel.attrib['channel'].lower() == cname.lower():
					log.log(LOG_INFO, 'Ignoring attempt to relay IRC channel to itself')
					continue
				if not cname.lower() in configs[name]['relays']:
					configs[name]['relays'][cname.lower()] = []
				relnew = rel.attrib
				if not 'prefix' in relnew:
					relnew['prefix'] = '[' + name + ']'
				configs[name]['relays'][cname.lower()].append(relnew)

def runconfig(timers):
	global configs
	global clients

	for key in configs:
		user = configs[key]['user']
		server = configs[key]['server']
		cmds = []

		cli = client(name=key, nick=user['nick'], user=user['user'], gecos=user['gecos'],
			server=server['host'], port=server['port'], serverpassword=server['password'],
			schedobj=timers, performs=cmds)

		for chan in configs[key]['channels']:
			cli.channel_add(chan)

		for chan in configs[key]['relays']:
			rels = configs[key]['relays'][chan]
			for rel in rels:
				cli.relay_add(chan, rel['type'], rel['name'], rel['channel'], rel['prefix'], None)

		cli.connect()
		clients[key] = cli

def sockets():
	return client.sockets

class client:
	sockets = []

	def __init__(self, name, connfreq=30, pingfreq=120, capdelay=3, schedobj=None, schedpri=100,
				nick='IRCBot', user='IRCBot', gecos='IRCBot',
				server='localhost', port=6667, serverpassword=None, performs=[]):
		self.name = name
		self._sock = None
		self._connected = False
		self._disconnecting = False
		self._connfreq = connfreq
		self._errconnfreq = 10
		self._nexterrconnfreq = 10
		self._pingfreq = pingfreq
		self._pingrcvd = True
		self._capdelay = capdelay
		self._iscap = False
		self._caps = {} # key == cap, true == ack
		self._sched = schedobj
		self._schedpri = schedpri
		self._schedevs = {'cap': None, 'conn': None, 'ping': None, 'perform': None, 'nick': None}
		self._myid = {'nick': nick, 'user': user, 'gecos': gecos, 'curnick': nick, 'curnicknum': -1}
		self._server = {'server': server, 'curserver': server, 'port': port, 'password': serverpassword}
		self._msgbinds = {}
		self._ircbuf = ''
		self._performdone = False
		self._nickdelay = 60
		self._performs = performs
		self._channels = {}
		self._relays = {}
		if self._sched == None:
			self._sched = sched.scheduler(time.time, time.sleep)
		self.bindmsg('ping', self._m_ping)
		self.bindmsg('004', self._m_004)
		self.bindmsg('005', self._m_005)
		self.bindmsg('433', self._m_433)
		self.bindmsg('privmsg', self._m_privmsg)
		self.bindmsg('nick', self._m_nick)
		self.bindmsg('join', self._m_join)
		self.bindmsg('kick', self._m_kick)
		self.bindmsg('part', self._m_part)
		self.bindmsg('cap', self._m_cap)
		self.bindmsg('error', self._m_error)
		relay.bind('irc', self.name, self._relaycallback)

	def __del__(self):
		try:
			self.disconnect("Shutting down")
			relay.unbind('irc', self.name, self._relaycallback)
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

	def _execmsg(self, msgobj):
		if msgobj['msg'].lower() in self._msgbinds:
			for callback in self._msgbinds[msgobj['msg'].lower()]:
				callback(msgobj)

	def _addsock(self):
		if self._sock == None:
			return
		if not self._sock in self.sockets:
			rbsocket.bindsockcallbacks(self._sock, self.dodisconnect, self.doerr, self.doread)
			self.sockets.append(self._sock)

	def _delsock(self):
		if self._sock in self.sockets:
			rbsocket.unbindsockcallbacks(self._sock)
			self.sockets.remove(self._sock)

	def _startping(self):
		self._pingrcvd = True
		self._schedevs['ping'] = self._addtimer(delay=self._pingfreq, callback=self._doping)

	def _cancelping(self):
		self._deltimer(self._schedevs['ping'])
		self._schedevs['ping'] = None

	def _doping(self):
		if not self._pingrcvd:
			log.log(LOG_INFO, 'Ping Timeout', self)
			self.disconnect('', False)
			self._schedconnect()
			return
		self.send('PING ' + self._server['curserver'])
		self._pingrcvd = False
		self._schedevs['ping'] = self._addtimer(delay=self._pingfreq, callback=self._doping)

	def _checkping(self):
		self._deltimer(self._schedevs['ping'])
		self._schedevs['ping'] = self._addtimer(delay=self._pingfreq, callback=self._doping)
		self._pingrcvd = True

	def _docapend(self):
		self.send('CAP END')

	def _schedconnect(self, freq=None):
		if freq == None:
			freq = self._connfreq
		if self._schedevs['conn'] != None:
			return
		self._schedevs['conn'] = self._addtimer(delay=freq, callback=self.connect)
		log.log(LOG_INFO, 'Attempting to reconnect in ' + str(freq) + ' seconds', self)

	def _doline(self, line):
		if ((line == None) or (line == '')):
			return
		log.log(LOG_DEBUG, '<-- ' + line, self)
		msg = self._parse_raw(line)
		self._execmsg(msg)

	def _parse_raw(self, line):
		ret = {'source': {'full': "", 'name': "", 'ident': "", 'host': ""}, 'msg': "", 'params': []}

		stat = 0

		words = line.split(' ')
		for word in words:
			if ((stat < 3) and (len(word) == 0)):
				continue

			if (stat == 0):
				stat += 1
				if (word[0] == ":"):
					 ret['source']['full'] = word[1:]
				else:
					ret['msg'] = word.upper()
					stat += 1
			elif (stat == 1):
				ret['msg'] = word.upper()
				stat += 1
			elif (stat == 2):
				if (word[0] == ":"):
					ret['params'].append(word[1:])
					stat += 1
				else:
					ret['params'].append(word)
			else:
				ret['params'][-1] = ret['params'][-1] + " " + word

		if (len(ret['source']['full']) > 0):
			src = ret['source']['full']
			if (src.find("@") >= 0):
				ret['source']['host'] = src[src.find("@")+1:]
				src = src[:src.find("@")]
			if (src.find("!") >= 0):
				ret['source']['ident'] = src[src.find("!")+1:]
				src = src[:src.find("!")]
			ret['source']['name'] = src

		return ret

	def _perform(self):
		if self._performdone:
			return
		self._performdone = True
		for cmd in self._performs:
			self.send(cmd)
		for chan in self._channels:
			if not self._channels[chan]:
				self.send('JOIN ' + chan)
		self._nexterrconnfreq = self._errconnfreq
		self._schedevs['perform'] = None

	def _m_ping(self, msg):
		self.send('PONG :' + msg['params'][0])

	def _m_004(self, msg):
		self._server['curserver'] = msg['params'][1]

	def _m_005(self, msg):
		if self._schedevs['perform'] == None and not self._performdone:
			self._schedevs['perform'] = self._addtimer(delay=3, callback=self._perform)

	def _m_433(self, msg):
		if msg['params'][0].lower() != self._myid['curnick'].lower():
			self._myid['curnicknum'] = self._myid['curnicknum'] + 1
			self._myid['curnick'] = self._myid['nick'] + str(self._myid['curnicknum'])
			self.send('NICK ' + self._myid['curnick'])
			if self._schedevs['nick'] == None:
				self._schedevs['nick'] = self._addtimer(delay=self._nickdelay, callback=self._renick)

	def _m_privmsg(self, msg):
		if msg['params'][0].lower() in self._channels:
			if msg['params'][0].lower() in self._relays:
				for rel in self._relays[msg['params'][0].lower()]:
					text = msg['params'][-1]
					prefix = ''
					if rel.extra['prefix'] != '':
						prefix = rel.extra['prefix']
					if text[0:7].lower() == '\x01action':
						if text[-1] == '\x01':
							text = text[:-1]
						text = prefix + ' * ' + msg['source']['name'] + ' ' + text[8:]
					else:
						if prefix != '':
							prefix = rel.extra['prefix'] + ' '
						text = prefix + '<' + msg['source']['name'] + '> ' + text
					relay.call(text, rel, relay.RelaySource('irc', self.name, msg['params'][0].lower(), {}), {'msg': msg})

	def _m_join(self, msg):
		chan = msg['params'][0]
		if msg['source']['name'].lower() == self._myid['curnick'].lower():
			if chan.lower() in self._channels:
				self._channels[chan.lower()] = True

	def _m_kick(self, msg):
		if msg['params'][1].lower() == self._myid['curnick'].lower():
			if msg['params'][0].lower() in self._channels:
				self._channels[msg['params'][0].lower()] = False
				self.send('JOIN ' + msg['params'][0])

	def _m_part(self, msg):
		if msg['source']['name'].lower() == self._myid['curnick'].lower():
			if msg['params'][0].lower() in self._channels:
				self._channels[msg['params'][0].lower()] = False
				self.send('JOIN ' + msg['params'][0])

	def _m_nick(self, msg):
		if msg['source']['name'].lower() == self._myid['curnick'].lower():
			self._myid['curnick'] = msg['params'][0]
			if self._myid['curnick'].lower() == self._myid['nick'].lower():
				self._myid['curnicknum'] = -1
			log.log(LOG_INFO, 'Current nick changed to: ' + self._myid['curnick'], self)
			if self._schedevs['nick'] != None:
				self._deltimer(self._schedevs['nick'])
				self._schedevs['nick'] = None

	def _m_cap(self, msg):
		if not self._iscap:
			self._caps = {}
			self._schedevs['cap'] = self._addtimer(delay=self._capdelay, callback=self._docapend)
		self._iscap = True
		if (msg['params'][1] == 'LS'):
			reqcaps = []
			capsls = msg['params'][-1].split(' ')
			knowncaps = ['account-notify', 'away-notify', 'extended-join', 'multi-prefix', 'userhost-in-names']
			for cap in capsls:
				if cap in knowncaps:
					reqcaps.append(cap)
					self._caps[cap] = False
			if len(reqcaps) > 0:
				self.send('CAP REQ :' + ' '.join(reqcaps))
		elif (msg['params'][1] == 'ACK'):
			capsack = msg['params'][-1].split(' ')
			for cap in capsack:
				if cap in self._caps:
					self._caps[cap] = True

	def _m_error(self, msg):
		log.log(LOG_INFO, 'Disconnected from ' + self._server['server'] + ', attemoting to reconnect', self)
		self.disconnect('', False)
		self._schedconnect(self._nexterrconnfreq)
		self._nexterrconnfreq = self._nexterrconnfreq + self._errconnfreq

	def _renick(self):
		self.send('NICK ' + self._myid['nick'])
		self._schedevs['nick'] = self._addtimer(delay=self._nickdelay, callback=self._renick)

	def _relaycallback(self, data):
		if data.text == None:
			return
		if self._connected and self._performdone:
			if data.target.channel.lower() in self._channels:
				self.send('PRIVMSG ' + data.target.channel + ' :' + data.text)

	def bindmsg(self, msg, callback):
		if not msg.lower() in self._msgbinds:
			self._msgbinds[msg.lower()] = []
		if not callback in self._msgbinds[msg.lower()]:
			self._msgbinds[msg.lower()].append(callback)

	def unbindmsg(self, msg, callback):
		if msg.lower() in self._msgbinds:
			if callback in self._msgbinds[msg.lower()]:
				self._msgbinds[msg.lower()].remove(callback)
			if len(self._msgbinds[msg.lower()]) < 1:
				del self._msgbinds[msg.lower()]

	def connect(self):
		self._ircbuf = ''
		self._performdone = False
		if self._schedevs['conn'] != None:
			self._deltimer(self._schedevs['conn'])
		self._schedevs['conn'] = None
		if self._schedevs['cap'] != None:
			self._deltimer(self._schedevs['cap'])
		self._schedevs['cap'] = None
		self._schedevs['perform'] = None
		log.log(LOG_INFO, 'Attempting to connect to ' + self._server['server'] + ' on port ' + str(self._server['port']), self)

		addrs = []

		try:
			addrs = socket.getaddrinfo(self._server['server'], self._server['port'], 0, 0, socket.IPPROTO_TCP)
		except socket.gaierror as e:
			log.log(LOG_ERROR, 'Error connecting to ' + self._server['server'] + ': ' + e.strerror, self)
		except:
			log.log(LOG_ERROR, 'Unknown error looking up host name ' + self._server['server'], self)

		if (len(addrs) < 1):
			return

		s = None
		for addr in addrs:
			af, socktype, proto, canonname, sa = addr
			try:
				s = rbsocket.rbsocket(af, socktype, proto)
			except socket.error as e:
				s = None
				continue
			try:
				s.connect(sa)
			except socket.error as e:
				s.close()
				s = None
				continue
			break

		if s == None:
			log.log(LOG_ERROR, 'Error connecting to ' + self._server['server'], self)
			self._schedconnect()
			return

		self._connected = True
		self._sock = s
		self._addsock()
		self._myid['curnick'] = self._myid['nick']

		log.log(LOG_INFO, 'Connected to ' + self._server['server'] + ' on port ' + str(self._server['port']), self)

		self._startping()

		self.send('CAP LS')
		if (self._server['password'] != None):
			self.send('PASS :' + self._server['password'])
		self.send('NICK ' + self._myid['nick'])
		self.send('USER ' + self._myid['user'] + ' 0 * :' + self._myid['gecos'])

		return

	def disconnect(self, reason = '', sendexit = True):
		if self._disconnecting:
			return
		self._disconnecting = True
		if reason != '' and reason != None and reason[0] != ' ':
			reason = ' ' + reason
		if (sendexit):
			self.send('QUIT :Disconnecting' + reason)
		self._cancelping()
		self._delsock()
		try:
			self._sock.close()
		except:
			self._sock = None
		self._sock = None
		self._connected = False
		self._performdone = False
		self._iscap = False
		self._disconnecting = False
		self._server['curserver'] = self._server['server']
		for ev in self._schedevs:
			self._deltimer(self._schedevs[ev])
		for chan in self._channels:
			self._channels[chan] = False
		return

	def send(self, line):
		sent = 0
		try:
			if isinstance(line, unicode):
				text = line.encode('UTF-8')
			elif isinstance(line, str):
				 text = line
			else:
				text = ''
			sent = self._sock.send(text + '\r\n')
		except Exception as e:
			sent = 0
		if (sent == 0):
			log.log(LOG_INFO, 'Disconnected from ' + self._server['server'] + ', attemoting to reconnect', self)
			self.disconnect('', False)
			self._schedconnect()
			return
		log.log(LOG_DEBUG, '--> ' + line, self)

	def channel_add(self, channel):
		if channel == None or channel == '':
			return
		if not channel.lower() in self._channels:
			self._channels[channel.lower()] = False
		if self._connected and self._performdone:
			self.send('JOIN ' + channel)

	def relay_add(self, relchan, type, name, channel, prefix, what=None, filters=None):
		rel = relay.RelayTarget(type, name, channel, {'prefix': prefix}, filters)
		if relchan.lower() in self._relays:
			if not rel in self._relays[relchan.lower()]:
				self._relays[relchan.lower()].append(rel)
		else:
			self._relays[relchan.lower()] = [rel]
		log.log(LOG_INFO, 'Added relay rule for channel ' + relchan + ' (type:' + type + ', name:' + name + ', channel:' + channel + ', prefix:' + prefix + ')', self)

	def doread(self, sock):
		if self._sock != sock:
			return

		try:
			buf = self._ircbuf + self._sock.recv(1024)
		except:
			buf = ''

		if (buf == ''):
			log.log(LOG_INFO, 'Received no data from ' + self._server['server'] + ', attemoting to reconnect', self)
			self.disconnect('', False)
			self._schedconnect()
			return

		lines = buf.replace('\r', '\n').split('\n')
		if ((len(lines) > 0) and (lines[-1] != '')):
			self._ircbuf = lines[-1]
			del lines[-1]
		else:
			self._ircbuf = ''

		self._checkping()

		for line in lines:
			self._doline(line)

		return

	def doerr(self, sock):
		log.log(LOG_INFO, 'Exceptional condition from ' + self._server['server'] + ', attemoting to reconnect', self)
		self.disconnect('', False)
		self._schedconnect()
		return

	def dodisconnect(self, sock, msg):
		self.disconnect(msg, True)
		self._deltimer(self._schedevs['ping'])
		self._deltimer(self._schedevs['cap'])
		self._deltimer(self._schedevs['perform'])
		return
