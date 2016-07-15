# -*- coding: utf8 -*-
import ConfigParser, logging

import xlrd, xlwt

import time, datetime, sys, os

from jinja2 import Template
import codecs

import send_mail
"""
Load Attendance Register, create Absent Records

Powered by Liyan @ 2016-05-24
"""

#debug, show records details
debug_name = u''

class DtoRecord(object):
	"""数据传输对象: 一条具体的考勤记录
	"""
	def __init__(self, date, week_num, time_in, time_out, time_work, status, desc):
		self.date = date
		self.week_num = week_num #周几
		self.time_in = time_in #上班打卡时间
		self.time_out = time_out #下班打卡时间
		self.time_work = time_work #当天工时
		self.status = status #考勤状态
		self.desc = desc

	def __str__(self):
		return 'DtoRecord: ' + self.date + ' '+ self.status + ' '+ self.time_work

class PersonRecord(object):
	"""数据存储对象：一个人所有的打卡记录
	"""
	def __init__(self, datarange):
		# 加载考勤周期
		self.datarange = datarange
		self.util = DateUtil()

	def put_3_values(self, department, name, timestamp):
		"""第一次初始化dailyrecords，部门、姓名和时间戳
		"""
		self.count = 0
		self.department = department
		self.name = name
		self.dailyrecords = {} #日签到记录字典对象：{date as Key: List<timestamp in this day>}
		self.put_timestamp(timestamp)

	def put_timestamp(self, timestamp):
		"""同一个人，不需要再添加部门和姓名信息了
		"""
		self.count = self.count + 1
		d, t = DateUtil.parse_date_and_time(timestamp)
		#debug somebody
		if self.name == debug_name:
			print timestamp, (d, t)
		if d in self.dailyrecords:
			self.dailyrecords[d].append(t)
		else:
			self.dailyrecords[d] = [t]

class DateUtil(object):
	D_week = {0:u'周一',1:u'周二', 2:u'周三',3:u'周四', 4:u'周五',5:u'周六', 6:u'周日'}
	# D_week = {0:u'Mon.',1:u'Tue.', 2:u'Wed.',3:u'Thu.', 4:u'Fri.',5:u'Sat.', 6:u'Sun.'}

	# 员工考勤状态：休息日工作(加班)、正常、迟到、早退(18:00前下班或工时不足9小时)、漏打卡、缺勤
	Attendance_Status = {'over_time':u'休息日工作','normal':u'正常','be_late':u'迟到', 'leave_early':u'早退', 'missing':u'漏打卡', 'absence':u'缺勤', }

	"""计算工作日、工作状态和工时的工具类
	"""
	@staticmethod
	def create_daterange(start, end, working_days=[], holidays=[]):
		"""生成工作日历
		比如，start='2016-05-24', end='2016-06-27'，则生成含起始日期的工作区间表
		还可以制定调休情况：working_days，需要工作的周末；holidays，放假的工作日
		注：这个表在代码中作为字典表使用，不要往表内做任何更新！

Sample return
('2016-04-30', datetime.date(2016, 4, 30), u'Sat.', True)
('2016-05-01', datetime.date(2016, 5, 1), u'Sun.', False)
('2016-05-02', datetime.date(2016, 5, 2), u'Mon.', False)
('2016-05-03', datetime.date(2016, 5, 3), u'Tue.', False)
		"""
		# working_days = self.config.get('check info','working_days').split(',')
		# holidays = self.config.get('check info','holidays').split(',')
		oneday = datetime.timedelta(days=1)
		day_start = datetime.datetime.strptime(start,"%Y-%m-%d").date()
		day_end = datetime.datetime.strptime(end,"%Y-%m-%d").date()
		datarange = [] # (str, datatime, week number, is_working_day)
		if day_end < day_start:
			print 'wrong date range!'
			return
		
		# format working_days & holidays
		tmp_days = []
		for day in working_days:
			day = datetime.datetime.strptime(day.strip(), '%Y-%m-%d').strftime('%Y-%m-%d')
			tmp_days.append(day)
		working_days = tmp_days
		tmp_days = []
		for day in holidays:
			day = datetime.datetime.strptime(day.strip(), '%Y-%m-%d').strftime('%Y-%m-%d')
			tmp_days.append(day)
		holidays = tmp_days
		print "working_days = ", working_days, " holidays = ", holidays

		day_next = day_start
		while day_end >= day_next:
			is_working_day = True
			if day_next.strftime('%Y-%m-%d') in working_days:
				is_working_day = True
			elif day_next.strftime('%Y-%m-%d') in holidays:
				is_working_day = False
			else:
				is_working_day = (day_next.weekday() < 5)
			datarange.append( (day_next.strftime('%Y-%m-%d'), day_next, DateUtil.D_week[day_next.weekday()], is_working_day) ) 
			day_next = day_next + oneday

		return datarange

	@staticmethod
	def parse_date_and_time(timestamp): # 2008/1/25 12:22:00
		"""把打卡记录字串转换成日期和时间
		注：从excel中读取原始打卡记录时使用
		"""
		obj = datetime.datetime.strptime(timestamp, '%Y/%m/%d %H:%M:%S')
		return obj.strftime('%Y-%m-%d'), obj.strftime('%H:%M:%S')
	
	@staticmethod
	def calc_workinghours(start, end):
		"""计算当日工时和工作状态
		比如，19:00:00 - 9:45:00，得出一天的工作时长
		"""
		status = 'normal'
		is_late=False
		is_early=False
		time_in = datetime.datetime.strptime(start, '%H:%M:%S')
		time_out = datetime.datetime.strptime(end, '%H:%M:%S')
		if time_in > datetime.datetime.strptime('10:00:00', '%H:%M:%S'): is_late = True
		if time_out < datetime.datetime.strptime('18:00:00', '%H:%M:%S'): is_early = True
		if (time_out - time_in)< datetime.timedelta(hours=9): is_early = True
		
		#双重状态也记录成早退
		if is_late: status = 'be_late'
		if is_early: status = 'leave_early'

		return str(time_out - time_in), status

	@staticmethod
	def gen_person_records(datarange, dailyrecords, debug=False):
		"""根据考勤周期和个人打卡记录，生成员工考勤表
		考勤日类型：工作日、休息日
		"""
		records = [] # date, check in & out, check in, check out, working hours, status, desc
		for d in datarange: # (str, datatime, week number, is_working_day)
			date = d[0]
			c_in = ''
			c_out = ''
			workinghours = ''
			status = 'normal'
			today_record = dailyrecords.get(date)

			if today_record==None or len(today_record) == 0:# 无记录
				if d[3]: # is_working_day
					status = 'absence' # 缺勤
			elif len(today_record) > 1: # 考勤周期内有2条以上打卡记录
				c_in = dailyrecords.get(date)[0]
				c_out = dailyrecords.get(date)[-1]
				workinghours, status = DateUtil.calc_workinghours(c_in, c_out)
				if not d[3]: status = 'over_time' #休息日工作
			else: # 漏打卡 len(today_record) == 1
				c_in = dailyrecords.get(date)[0]
				status = 'missing' # 漏打卡

			record = DtoRecord(date, d[2], c_in, c_out, workinghours, status, DateUtil.Attendance_Status.get(status))
			records.append(record)

		if debug:
			print 'DateUtil.gen_person_records: ', len(records)
			for r in records: print r

		return records

class AttendanceProcessor(object):
	"""考勤记录处理逻辑
		1、从配置文件读取考勤开始日和截止日，生成并加载考勤周期
		2、初始化考勤汇总表：生成写excel对象，写表头
		3、生成读excel对象，读取每条考勤记录
		3.1 合成日签到记录
		3.2 对比考勤周期，生成完整周期的考勤
		3.3 写入汇总表

	存储结构
		- self.datarange: 考勤周期(从开始日到截止日) - [(str, datatime, isweekend, isholiday), ...]
		- 以姓名为key的日签到记录： 详见PersonRecord -- 如果有重名会出bug
			日签到记录字典对象：{date as Key: List<timestamp in this day>}
	
	"""
	def __init__(self, ini_file):
		self.config = ConfigParser.RawConfigParser(allow_no_value=True)
		self.config.read(ini_file)
		# 服务基础路径：
		self.base_dir = self.config.get('basic','base_dir')
		if sys.platform == 'win32': #decode to unicode
			self.base_dir = self.base_dir.decode('utf-8')
		if not os.access(self.base_dir,os.F_OK): 
			os.mkdir(self.base_dir)
			logging.info('create base_dir: %s'%self.base_dir)
		print 'base_dir = ', self.base_dir, type(self.base_dir)
		# 初始化日志服务
		log_file = os.path.join(self.base_dir, 'excel.log')
		logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s %(message)s')
		logging.info('init gen excel tool...')
		# 加载考勤周期
		self.datarange = self.__daterange()
		# 加载邮件地址: {姓名_部门:address, }
		self.mails = self.__load_email_address()
		# 加载通知邮件的内容模板
		self.template = Template(codecs.open('template.html', encoding='utf-8').read())
		# print self.datarange
		self.row_write = 0 #当前写入excel的行数
		self.__summary_sheet_init()
		self.style_red = xlwt.easyxf(
			"font: name Arial;"
			"pattern: pattern solid, fore_colour red;"
			)

	def __daterange(self):
		start = self.config.get('check info','start')
		end = self.config.get('check info','end')
		logging.info('daterange: from %s to %s' % (start, end))
		print('daterange: from %s to %s' % (start, end))
		working_days = self.config.get('check info','working_days').split(',')
		holidays = self.config.get('check info','holidays').split(',')
		return DateUtil.create_daterange(start, end, working_days, holidays)

	def __load_email_address(self):
		"""读取mail.xlsx中姓名、部门、邮箱信息
		select department, name, email from fl_users;
		"""
		# 用来匹配未知地址
		self.mail = self.config.get('check info','mail')
		workbook = xlrd.open_workbook('mail.xlsx', encoding_override='gb2312')
		print '__load_email_address - loading sheets: ' + ', '.join(workbook.sheet_names())
		sheet = workbook.sheet_by_index(0)
		num_rows = sheet.nrows
		num_cells = sheet.ncols
		print 'rows =%d, cells =%d' % (num_rows, num_cells)
		mails = {}

		for num_row in range(1,num_rows):
			(department, name, mail) = (sheet.cell_value(num_row, 0), sheet.cell_value(num_row, 1), sheet.cell_value(num_row, 2))
			mails[name+'_'+department] = mail
			# print (department, name, mail)
		return mails

	def __summary_sheet_init(self):
			style = xlwt.easyxf(
				"font: bold on; align: wrap on, vert centre, horiz center;"
				)
			self.book = xlwt.Workbook(encoding="utf-8")
			self.sheet = self.book.add_sheet('Sheet 1')

			self.sheet.write(self.row_write, 0, u'姓名', style) # row, column, value
			self.sheet.write(self.row_write, 1, u'部门', style)
			self.sheet.write(self.row_write, 2, u'日期', style)
			self.sheet.write(self.row_write, 3, u'上下班', style)
			self.sheet.write(self.row_write, 4, u'上班', style)
			self.sheet.write(self.row_write, 5, u'下班', style)
			self.sheet.write(self.row_write, 6, u'工时', style)
			self.sheet.write(self.row_write, 7, u'描述', style)

			# for num_row in range(1,10):
			# 	self.sheet.write(num_row, 0, u'姓名'+str(num_row),style) # row, column, value

	def __summary_sheet_writebyperson(self, name, department, records, debug=False):
			m_records = [] #考勤异常记录

			try:

				for record in records: # date, check in & out, check in, check out, working hours, desc
					self.row_write = self.row_write + 1
					# print '============write at ',self.row_write, record
					self.sheet.write(self.row_write, 0, name) 
					self.sheet.write(self.row_write, 1, department)
					self.sheet.write(self.row_write, 2, record.date+record.week_num)
					self.sheet.write(self.row_write, 3, (record.time_in + ' ' + record.time_out).strip())
					self.sheet.write(self.row_write, 4, record.time_in)
					self.sheet.write(self.row_write, 5, record.time_out)
					self.sheet.write(self.row_write, 6, record.time_work)
					self.sheet.write(self.row_write, 7, record.desc)
					# self.sheet.write(self.row_write, 8, record.status)

					if record.status !='normal': m_records.append(record)
					if debug: print name, self.row_write, record

			except:
				print "Unexpected error:", sys.exc_info()[0]
				raise
			self.sheet.flush_row_data()

			if debug:
				print '__summary_sheet_writebyperson(all & abnormal): ', len(records), len(m_records)
				for r in records: print r

			if len(m_records) > 0:
				mail = None
				try:
					mail = self.mails.get(name+'_'+department) # 根据姓名和部门获得邮箱地址
				except UnicodeEncodeError as e:
					logging.error('UnicodeEncodeError({0}): on writebyperson name={1}, department={2}'.format(e.message, name, self.department))
				if mail == None or len(mail) == 0: mail = 'unknow'
				self.__write_person_mail(name, department, mail, m_records)
				m_records = []


	def __write_person_mail(self, name, department, mail, records):
		file_path = os.path.join(self.base_dir, self.config.get('check info','outbox'))

		try:
			if not os.access(file_path,os.F_OK): 
				os.mkdir(file_path)
				logging.info('create outbox dir[%s]' % file_path)
			file_path = file_path.decode('utf-8')
		except: pass

		# 写个人html文件
		file_path = os.path.join(file_path, name +'_'+ department +'_'+ mail +'_.html')
		body = self.template.render(name=name, department=department, records=records)
		try:
			codecs.open(file_path, 'w', encoding='utf-8').write(body)
		except: 
			logging.error('failed to write mail for %s_%s: %s' % (name, department, mail))

		# 写个人Excel文件
		# if not os.path.isdir(file_path):
		# 	print 'missing outbox.'
		# 	raise Exception('outbox path not exist!')
		# try:
		# 	file_path = os.path.join(file_path, name +'_'+ department +'_'+ mail +'_.xls')
		# 	print 'Write to: '+file_path
		# except Exception as e:
		# 	print 'Exception({0}): fail to generate abslute path {1}'.format(e.message, name +'_'+ department + mail +'_.xlsx')
		# 	raise e

		# book = xlwt.Workbook(encoding="utf-8")
		# sheet = book.add_sheet('Sheet 1')
		# num = 0
		# sheet.write(num, 0, u'姓名') # row, column, value
		# sheet.write(num, 1, u'部门')
		# sheet.write(num, 2, u'日期')
		# sheet.write(num, 3, u'周几')
		# sheet.write(num, 4, u'上班时间')
		# sheet.write(num, 5, u'下班时间')
		# sheet.write(num, 6, u'说明')

		# for record in records:
		# 	num = num + 1
		# 	sheet.write(num, 0, name, self.style_red)
		# 	sheet.write(num, 1, department, self.style_red)
		# 	sheet.write(num, 2, record.date, self.style_red)
		# 	sheet.write(num, 3, record.week_num, self.style_red)
		# 	sheet.write(num, 4, record.time_in, self.style_red)
		# 	sheet.write(num, 5, record.time_out, self.style_red)
		# 	sheet.write(num, 6, record.desc, self.style_red)

		# book.save(file_path)
		# print 'Save Excel: '+file_path
		# book = None


	def generate_excels(self):
			file_path = self.config.get('check info','raw_excel')
			# file_path = '/opt/e_disk/doc/NetQin/2015-Feiliu/当前工作/AttendanceRegister/old/kaoqin/app/uploads/11.xls'
			workbook = xlrd.open_workbook(file_path, encoding_override='gb2312')
			print 'loading sheets: ' + ', '.join(workbook.sheet_names())
			sheet = workbook.sheet_by_index(0)
			num_rows = sheet.nrows
			num_cells = sheet.ncols
			print 'rows =%d, cells =%d' % (num_rows, num_cells)
			
			##################################################
			# load (department, name, timestamp) line by line
			##################################################
			# 1 line: title
			# 2 line: real first line, only put
			record = PersonRecord(self.datarange)
			num_row = 1
			record.put_3_values(sheet.cell_value(num_row, 0), sheet.cell_value(num_row, 1), sheet.cell_value(num_row, 2))

			# 3 line to last-1 line: check different, write or put
			for num_row in range(1+1,num_rows-1):

				try:
					(department, name, timestamp) = (sheet.cell_value(num_row, 0), sheet.cell_value(num_row, 1), sheet.cell_value(num_row, 2))
					# print name, timestamp
					if record.name == name:
						if record.department != department:
							print "same name but different department!", name, department
						record.put_timestamp(timestamp)
					else:
						# 新名字出现了，把当面员工的考勤写入汇总表
						# records = record.get_person_records()
						# debug 查看产出内容
						debug = False
						if record.name == debug_name:
							print '\n'.join(["%s=%s" % (k, v) for k, v in record.dailyrecords.items()])
							print record.name, 'all record size = ', record.count
							debug = True
						if debug_name != None:
							print record.name, ' write from row: ', self.row_write
						records = DateUtil.gen_person_records(self.datarange, record.dailyrecords, debug)
						record.dailyrecords = {}

						# 写文件
						self.__summary_sheet_writebyperson(record.name, department, records, debug)

						# 开始下一个人
						record.put_3_values(department, name, timestamp)
				except IndexError as e:
					print 'IndexError({0}): on read row {1}/write row {2}'.format(e.message, num_row, self.row_write)
					# print "I/O error({0}): {1}".format(e.errno, e.strerror)
				except NameError as e:
					print 'NameError({0}): on read row {1}/write row {2}'.format(e.message, num_row, self.row_write)
				except Exception as e:
					# print "Unexpected error:", sys.exc_info()[0]
					print 'Exception({0}): on read row {1}/write row {2}'.format(e.message, num_row, self.row_write)
					# raise e

			try:
				# last line: write last person
				(department, name, timestamp) = (sheet.cell_value(num_rows-1, 0), sheet.cell_value(num_rows-1, 1), sheet.cell_value(num_rows-1, 2))
				if record.name == name: record.put_timestamp(timestamp)
				records = DateUtil.gen_person_records(self.datarange, record.dailyrecords)
				record.dailyrecords = {}
				if debug_name != None:
					print record.name, ' write from row: ', self.row_write
				self.__summary_sheet_writebyperson(record.name, department, records, True)
			except Exception as e:
				# print "Unexpected error:", sys.exc_info()[0]
				print 'Exception({0}): on write row {1}'.format(e.message, self.row_write)

			# 生成考勤汇总表	
			file_path = os.path.join(self.base_dir, self.config.get('check info','summary_sheet'))
			self.book.save(file_path)
			print 'Write to ', file_path
			logging.info('Write to %s' % file_path)


def test_xls_read():
	file_path = '/opt/e_disk/doc/NetQin/2015-Feiliu/当前工作/AttendanceRegister/raw.xlsx'
	# file_path = '/opt/e_disk/doc/NetQin/2015-Feiliu/当前工作/AttendanceRegister/old/kaoqin/app/uploads/11.xls'
	workbook = xlrd.open_workbook(file_path, encoding_override='gb2312')
	print 'loading sheets: ' + ', '.join(workbook.sheet_names())
	sheet = workbook.sheet_by_index(0)
	num_rows = sheet.nrows
	num_cells = sheet.ncols
	print 'rows =%d, cells =%d' % (num_rows, num_cells)
	for num_row in range(0,num_rows):
		values = sheet.row_values(num_row) #sheet.cell_value(num_row, 1)
		print ', '.join(values)

def test_xls_write(file_path):
	book = xlwt.Workbook(encoding="utf-8")
	sheet = book.add_sheet('Sheet 1')
	num = 0
	# 编辑单元格
	sheet.write(num, 0, u'姓名') # row, column, value
	sheet.write(num, 1, u'部门')
	sheet.write(num, 2, u'日期')
	sheet.write(num, 3, u'上下班')
	sheet.write(num, 4, u'上班')
	sheet.write(num, 5, u'下班')
	sheet.write(num, 6, u'工时')
	sheet.write(num, 7, u'描述')

	style = xlwt.easyxf(
	"font: name Arial;"
	"pattern: pattern solid, fore_colour red;"
	)


	for num in range(1,10):
		sheet.write(num, 0, u'姓名'+str(num),style) # row, column, value

	book.save(file_path)

def test_gen_html(file_path):
	# file_path = os.path.join('.', 'template.html')
	template = Template(codecs.open('template.html', encoding='utf-8').read())

	# DtoRecord(date, week_num, time_in, time_out, time_work, status, desc)
	records = []
	records.append(DtoRecord(u'2016-6-17',u'周五','9:50','18.40','8:50','',u'迟到'))
	body = template.render(name=u'张三', department=u'游戏平台业务部', records=records)
	# print body
	codecs.open(file_path, 'w', encoding='utf-8').write(body)



def gen_excel():
	"""生成考勤汇总表(summary.xls)和考勤异常同事的异常记录表(outbox/*.xls)
	"""
	p = AttendanceProcessor("mail.ini")
	p.generate_excels()

def main():
	# test_xls_write('/tmp/example.xls')
	# test_gen_html('/tmp/somebody.html')

	# # 测试工时计算
	# print DateUtil.calc_workinghours('9:45:00', '19:00:00')
	# print DateUtil.calc_workinghours('9:45:00', '18:00:00')
	# print DateUtil.calc_workinghours('7:45:00', '17:00:00')

	# start = '2016-4-21'
	# end = '2016-5-20'
	# # 节假日调休安排：需要上班的周末和放假的工作日，用逗号(,)分割
	# working_days = '2016-4-30'.split(',')
	# holidays = '2016-5-2, 2016-5-3'.split(',')
	# for line in DateUtil.create_daterange(start, end, working_days, holidays):
	# 	print line

	gen_excel()

if __name__ == '__main__':
	main()
	raw_input("Press Enter to Exit:)")