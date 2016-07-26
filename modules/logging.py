# -*- coding: utf-8 -*-

import sys
from time import gmtime, strftime

LOG_NORMAL = 0
LOG_ERROR = 1

def log(level, message):
	out = sys.stdout
	if level == LOG_ERROR:
		out = sys.stderr

	text = message
	time = '[' + strftime('%Y-%m-%d %H:%M:%S', gmtime()) + '] '

	if text[-1] != '\n':
		text = text + '\n'

	text = time + text

	out.write(text)
