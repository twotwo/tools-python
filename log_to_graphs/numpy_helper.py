#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
numpy_helper.py
load and save day log data

https://docs.scipy.org/doc/numpy-dev/reference/routines.io.html

Copyright (c) 2016年 li3huo.com All rights reserved.
"""
import argparse, logging
import ConfigParser
from datetime import date, timedelta

from subprocess import Popen, PIPE
import numpy as np

def log(info):
	logging.info(info)
	print info

class Helper(object):
	def __init__(self, config_file, section):
		"""加载配置文件中的配置信息：
npz_file
request_cmd
resp_hour_cmd
auth_resp_groupby_ch_cmd
		"""
		# self.npz_file = npz_file
		config = ConfigParser.ConfigParser()
		config.read(config_file)

		timestamp = config.get(section, 'timestamp')
		self.yesterday = ( date.today()-timedelta(1) ).strftime(timestamp)

		self.npz_file = config.get(section, 'npz_file')
		log_file = config.get(section, 'log_file', 0, {'yesterday': self.yesterday})

		self.cost_type = config.get(section, 'cost_type')
		self.request_cmd = config.get(section, 'request_cmd', 0, {'log_file': log_file})
		self.resp_hour_cmd = config.get(section, 'resp_hour_cmd', 0, {'log_file': log_file})

		log( 'npz_file = %s, log_file = %s'% (self.npz_file, log_file) )
		log( 'request_cmd = %s'% self.request_cmd )
		log( 'resp_hour_cmd = %s'% self.resp_hour_cmd )
		if config.has_option(section, 'auth_resp_groupby_ch_cmd'):
			self.auth_resp_groupby_ch_cmd = config.get(section, 'auth_resp_groupby_ch_cmd', 0, {'log_file': log_file})
			log( 'auth_resp_groupby_ch_cmd = %s'% self.auth_resp_groupby_ch_cmd )

	def parse(self, save=False):
		"""根据加载的配置信息，按指定方式读取日志数据
		"""

		day_requests = Helper.parse_requests(self.request_cmd)
		(resp_time, resp_err) = Helper.parse_response_by_hour(self.resp_hour_cmd, self.cost_type)

		return {'day_requests':day_requests, 
				'day_resp_time_by_hour':resp_time,
				'day_resp_err_by_hour':resp_err}

		# if save:
		# 	np.savez(npz_file, day_requests=day_requests, 
		# 		day_resp_time_by_hour=resp_time,
		# 		day_resp_err_by_hour=resp_err)
		# 	log('parse & saved.')

	@staticmethod
	def parse_requests(cmd):
		"""
		命令获取 “计数 时:分:秒”结构的数据
		记录24小时中每秒的请求数量；生成一个长度为86400的一维数组
		"""
		day_requests = []
		
		buff = {}
		for line in Popen(cmd, shell=True, bufsize=102400, stdout=PIPE).stdout:
			try:
				buff[line.strip().split()[1]] = line.strip().split()[0]
			except IndexError as e:
				print 'IndexError', e.message,  len(line.strip().split()), 'line =',line.strip().split()
			except ValueError as e:
				print 'ValueError', e.message,  'line=[', line, ']'
				# break
		for h in range(24):
			for m in range(60):
				for s in range(60):
					if buff.has_key( '%02d:%02d:%02d' % (h, m, s) ):
						day_requests.append( int(buff['%02d:%02d:%02d' % (h, m, s)]) )
					else:
						day_requests.append(0)

		return day_requests

	@staticmethod
	def parse_response_by_hour(cmd, cost_type):
		"""按小时解析请求的响应速度(last 1000/100/10)和失败数量
		"""
		day_responses = {}
		day_responses_err = {}
		# init hours
		for i in range(24):
			# day_responses[hour] = [per cost,...]
			day_responses[i] = []
			# day_responses_err[hour] = [[code, cost],...]
			day_responses_err[i] = []

		for line in Popen(cmd, shell=True, bufsize=102400, stdout=PIPE).stdout:
			try:
				# hour cost code
				hour = int( line[0:2] )
				cost = line.split()[1]
				try:
					if 'string' == cost_type:
						cost = float( cost.split(':')[-1][0:-1] ) * 1000
					elif 'ms' == cost_type:
						cost = int( cost )
					else:
						cost = float( cost ) * 1000
				except ValueError as e:
					cost = float( cost.split()[-1] ) * 1000
				day_responses[hour].append(cost)
				code = int( line.split()[2].strip('\n') )
				if code != 0:
					day_responses_err[hour].append( [code, cost] )

			except IndexError as e:
				print 'IndexError:', e.message, 'line =',line.split()
			except ValueError as e:
				print 'ValueError:', e.message,  'line=[', line, ']'
				print 'cost=',line.split()[1].strip('\n')

		# resp_time_by_hour = [[00 resp time], [01 resp time], ...]
		resp_time_group_by_hour = []
		resp_err_group_by_hour = []
		for i in range(24):
			resp_time_group_by_hour.append(day_responses[i])
			resp_err_group_by_hour.append(day_responses_err[i])
		return resp_time_group_by_hour, resp_err_group_by_hour

	@staticmethod
	def parse_response_groupbytag(cmd, cost_type, ignore_err=False):
		"""命令返回结构: tag cost code
按照tag把返回结果分组
		"""
		resp_group = {}
		resp_group_err = {}
		for line in Popen(cmd, shell=True, bufsize=102400, stdout=PIPE).stdout:
			try:
				# tag cost code
				(tag, cost, code) = line.split()
				if tag not in resp_group: 
					resp_group[tag]=[]
					resp_group_err[tag]=[]
				try:
					if 'string' == cost_type:
						cost = float( cost.split(':')[-1][0:-1] ) * 1000
					elif 'ms' == cost_type:
						cost = int( cost )
					else:
						cost = float( cost ) * 1000
				except ValueError as e:
					cost = float( cost.split()[-1] ) * 1000
				
				code = int( code.strip('\n') )
				if code == 0:
					resp_group[tag].append(cost)
				else:
					if not ignore_err: resp_group[tag].append(cost)
					resp_group_err[tag].append( [code, cost] )

			except IndexError as e:
				print 'IndexError:', e.message, 'line =',line.split()
			except ValueError as e:
				print 'ValueError:', e.message,  'line=[', line, ']'
				print 'cost=',line.split()[1].strip('\n')

		return resp_group, resp_group_err


	@staticmethod
	def save(npz_file, **kwds):
		np.savez(npz_file, **kwds)

	@staticmethod
	def load(npz_file):
		"""
		load data from npz_file(.npz format file)
		"""
		# with np.load(npz_file) as data:
		data = np.load(npz_file)
		log('file[%s] has %s' % (npz_file, str(data.files)) )
		return data

def main():
	parser = argparse.ArgumentParser(prog='Numpy Helper', usage='%(prog)s [options]')

	parser.add_argument('-c', dest='cmd', type=str, default='parse', choices=['parse', 'load'], 
											help='command for helper')
	parser.add_argument('-i', dest='ini', type=str, default='helper.ini',
											help='NumPy binary file')
	parser.add_argument('-s', dest='section', type=str, default='agent',
											help='section in .ini file')
	parser.add_argument('-n', dest='npz', type=str, default='data.npz',
											help='NumPy binary file')
	parser.add_argument('-v', dest='verbose', action='store_true',
											help='List Data in NumPy binary file')
	# parser.add_argument('-h', dest='help', type=bool, default=False,
	# 										help='print help')
	parser.add_argument('--dry-run', dest='dry_run', action='store_true',
											help='Dry Run Mode: do not excute time-consuming operation')
	parser.set_defaults(verbose=False)
	parser.set_defaults(dry_run=False)
	# config a log
	logging.basicConfig(filename='./l2g.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

	args = parser.parse_args()

	save=True
	if args.dry_run: 
		print 'in dry-run mode'
		save=False

	if args.cmd == 'parse':
		log( 'parse for %s [%s]'% (args.ini, args.section) )
		helper = Helper(args.ini, args.section)
		data = helper.parse()
		print ", ".join(["%s=%d" % (k, len(v) ) for k, v in data.items()])

		Helper.save(helper.npz_file, **data)
	elif args.cmd == 'load':
		print 'load from ', args.npz
		data = Helper.load(args.npz)

		if args.verbose:
			for f in data.files:
				if f == 'day_requests':
					day_requests_by_hour = data['day_requests'].reshape(24, 3600)
					print '================    day_requests by hour    ================'
					print [np.sum(req) for req in day_requests_by_hour]

				elif f == 'day_resp_time_by_hour':
					resps_sorted = [np.sort(resp) for resp in data['day_resp_time_by_hour']]
					print '================ day_resp_time_by_hour(last 100) ================'
					print [np.mean(resp[-100:]) for resp in resps_sorted]

				elif f == 'day_resp_err_by_hour':
					day_resp_err_by_hour = data['day_resp_err_by_hour']
					print '================ day_resp_err_by_hour[0:23] ================'
					print [len(resp) for resp in day_resp_err_by_hour]

				else:
					print f, 'has', len(data[f]), 'items'
			# try:
			# 	day_requests = data['day_requests']
			# except:
			# 	log('npz_to_data: failed to load day_requests!')
			# 	day_requests = None

if __name__ == '__main__':
	"""python numpy_helper.py -h
python numpy_helper.py -c parse -i helper.ini -s agent # parse log & save data
python numpy_helper.py -c load -n agent.npz -v #load from data.npz
"""
	main()

