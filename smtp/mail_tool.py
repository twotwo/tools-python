# -*- coding:utf-8 -*-                                                          
"""
mail_tool.py
使用SMTP协议发送邮件的工具

参考
https://hg.python.org/cpython/file/2.7/Lib/smtplib.py
https://docs.python.org/2/library/email-examples.html
https://my.oschina.net/guol/blog/129913

Copyright (c) 2016年 li3huo.com All rights reserved.
"""
from smtplib import SMTP, SMTPConnectError, SMTPAuthenticationError

import mimetypes
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from email.header import Header

from email.utils import COMMASPACE, formatdate, formataddr
from email import encoders

import base64, time, os, json
from datetime import datetime, date

try:
	import simplejson
except ImportError:
	import json as simplejson

import ConfigParser, logging, argparse
import codecs, sys

from string import Template
from datetime import datetime, timedelta
"""
一个简单的邮件发送工具

Powered by Liyan @ 2016-07-17
"""

class MailTool(object):
	"""一个发邮件的工具类
	"""

	def __init__(self, host, port, timeout, user, password, ssl=False):
		"""初始化客户端连接
		"""

		# for python< 2.6
		# timeout=socket._GLOBAL_DEFAULT_TIMEOUT

		if ssl:
			self.client.starttls()

		try:
			self.client = SMTP(host=host, port=port, timeout=timeout)
			logging.info('SMTP init: host=%s, port=%s, timeout=%s' % (host, port, timeout))
			# print self.client.ehlo()
			response = self.client.login(user, password)
			print(response)
			logging.info('SMTP login: '+str(response) )
			# 设置邮件服务的发送者为发送账号
			self.sender = user
		except SMTPConnectError as e:
			logging.error('SMTPConnectError({0}): on {1}:{2}'.format(e.message, host, port))
		except SMTPAuthenticationError as e:
			logging.error('SMTPAuthenticationError({0}): on {1}:{2}'.format(e.message, user, password))
			print(e)
			exit(-1)

		self.client.set_debuglevel(0) # 1: debug=True

	def close(self):
		"""释放连接
		"""
		self.client.close()
		logging.info('SMTP close')
		# self.client.quit()

	@staticmethod
	def msg(ffrom, rcpt_tos, reply_to, subject, content, files):
		"""生成待发送内容
		"""

		# Create the enclosing (outer) message
		outer = MIMEMultipart()
		outer['subject'] = subject
		outer['from'] = ffrom
		outer['reply-to'] = reply_to
		outer['to'] = ','.join(rcpt_tos).strip()

		logging.info('Create Msg...')
		if len(content.strip()) > 0:
			cnt = MIMEText(content, 'html', 'utf8')
			print('content:', content)
			outer.attach(cnt)

		if files != None:
			for f in files:
				# Guess the content type based on the file's extension.  Encoding
				# will be ignored, although we should check for simple things like
				# gzip'd or compressed files.
				ctype, encoding = mimetypes.guess_type(f)

				if ctype is None or encoding is not None:
				# No guess could be made, or the file is encoded (compressed), so
				# use a generic bag-of-bits type.
					ctype = 'application/octet-stream'
				maintype, subtype = ctype.split('/', 1)
				logging.info('mail add attached: [{0}/{1}]{2}'.format(maintype, subtype,os.path.basename(f).encode('gb2312') ))

				try:
					if maintype == 'text':
						# Note: we should handle calculating the charset
						msg = MIMEText(open(f.strip(), 'rb').read(), _subtype=subtype)
					elif maintype == 'image':
						msg = MIMEImage(open(f.strip(), 'rb').read(), _subtype=subtype)
					elif maintype == 'audio':
						msg = MIMEAudio(open(f.strip(), 'rb').read(), _subtype=subtype)
					else:
						msg = MIMEBase(maintype, subtype)
						msg.set_payload(open(f.strip(), 'rb').read(), _subtype=subtype)
						# Encode the payload using Base64
						encoders.encode_base64(msg)
					# Set the filename parameter
					msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(f).encode('gb2312'))
					outer.attach(msg)
				except Exception as e:
					# Add attach file errors
					outer.attach(MIMEText('<p><b>failed to add {0}</b></p><pre>msg: <span style="color:red; font-size:18px;">{1}</span></pre>'.format(f.strip(), e), 'html', 'utf8'))

		# Add end mark in mail
		outer.attach(MIMEText('<p><b>--end--</b></p>', 'html', 'utf8'))

		logging.info('mail({0}) from[{1}] to[{2}] created.'.format(outer['subject'], outer['from'] , outer['to']))
		return outer

	@staticmethod
	def show_msg(msg):
		"""show MIMEMultipart
		"""
		print('mail({0}) from[{1}] to[{2}]:'.format(msg['subject'], msg['from'] , msg['to']))

		counter = 1
		for part in msg.walk():
			# multipart/* are just containers
			if part.get_content_maintype() == 'multipart':
				continue
			# Applications should really sanitize the given filename so that an
			# email message can't be used to overwrite important files
			filename = part.get_filename()
			if not filename:
				ext = mimetypes.guess_extension(part.get_content_type())
				if not ext:
					# Use a generic bag-of-bits extension
					ext = '.bin'
				filename = 'part-%03d%s' % (counter, ext)
			counter += 1
			# fp = open(os.path.join(opts.directory, filename), 'wb')
			# fp.write(part.get_payload(decode=True))
			# fp.close()
			print('mail part: {0}'.format(filename))


	def _message_id(self, reply):
		message_id = None

		if str(reply[0]) == '250': 
			message_id = str(reply[1]).split('#')[1]

		return message_id


	def send(self, msg):

		logging.info('Sending Msg...')
		try:
			self.client.sendmail(msg['from'], msg['to'].split(','), msg.as_string())
			logging.info('mail({0}) from[{1}] to[{2}] sent'.format(msg['subject'], msg['from'] , msg['to']))
			return True
		except Exception as e:
			logging.error('mail({0}) to {1} sent failed: msg = {2}'.format(msg['subject'], msg['to'], e))
		
		return False

		# self.client.mail(self.sender)
		# self.client.rcpt(msg['to'].split(','))
		
		# try:
		# 	(code, resp) = self.client.data(msg.as_string())
		# 	self.client.rset()

		# 	# logging.info('send %s' % resp)

		# 	if code == 250:
		# 		logging.info('mail({0}) from[{1}] to[{2}] sent.\n\t{3}.'.format(msg['subject'], msg['from'] , msg['to'], resp))
		# 		return True
		# 	logging.error('mail({0}) to {1} sent failed: code = {2}, msg = {3}'.format(msg['subject'], msg['to'], code, resp))

		# 	return False

		# except:
		# 	return False


def init_smtp(ini_file):
	"""Load basic and smtp config from mail.ini
	"""
	config = ConfigParser.RawConfigParser(allow_no_value=True)
	print ('read ini file', ini_file)
	if not os.path.exists(ini_file):
		# use ini in python dir
		ini_file=os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])),ini_file)
		print('try to use another place', ini_file)
	config.read(ini_file)
	base_dir = config.get('basic', 'base_dir')
	if sys.platform == 'win32': #decode to unicode
		base_dir = base_dir.decode('utf-8')
	if not os.access(base_dir,os.F_OK):
		os.makedirs(base_dir)
		print('now base dir created: '+base_dir)
	log_file = os.path.join(base_dir, 'mail.log')
	logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s %(message)s')

	host = config.get('smtp', 'host')
	port = config.get('smtp', 'port')
	timeout = config.getfloat('smtp', 'timeout')
	user = config.get('smtp', 'user')
	password = config.get('smtp', 'password')

	return MailTool(host, port, timeout, user, password), base_dir, config


def load_msg(section, config):
	"""加载指定配置对应的信息，并生成待发送邮件
	"""
	ffrom = formataddr((str(Header(u'业务支撑中心技术组', 'utf-8')), config.get(section, 'from')))
	# ffrom = config.get(section, 'from')
	rcpt_tos = config.get(section, 'to').split(',')
	reply_to = config.get(section, 'cc')
	template = Template(config.get(section, 'subject'))
	subject = template.substitute(date=(datetime.today()-timedelta(days=1)).strftime('%Y-%m-%d'))
	# ToDo: load content from text file
	content = config.get(section, 'content')
	files = config.get(section, 'files').split(',')

	return MailTool.msg(ffrom, rcpt_tos, reply_to, subject, content, files)


def main():
	parser = argparse.ArgumentParser(prog='Mail Tool', usage='%(prog)s [options]')

	parser.add_argument('-i', dest='ini', type=str, default='mail.ini',
											help='Mail Config file')
	parser.add_argument('-s', dest='section', type=str, default='test',
											help='section in .ini file')
	args = parser.parse_args()


	# init smtp tool
	tool, base_dir, config = init_smtp(args.ini)

	# send one mail
	print('section = '+args.section)
	msg = load_msg(args.section, config)
	MailTool.show_msg(msg)

	status = False
	count = 0
	while not status:
		count = count +1
		try:

			status = tool.send(msg)

		except Exception as e:
			logging.error('Exception({0}): on sending {1}'.format(e.message, msg['subject']))
			print('Exception({0}): on sending {1}'.format(e.message, msg['subject']))

		if count >= 3: break

	
	# release smtp connection
	tool.close()

if __name__ == '__main__':
	"""
	python mail_tool.py -i /tmp/mail.ini -s test
	"""
	main()
