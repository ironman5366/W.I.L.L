from termcolor import colored
import datetime
class logs():
	def openlogs(self):
		global logfile
		if self.keepcheck():
			try:
				logfile=open("WILL.log",'a')
			except IOError:
				logfile=open("WILL.log",'w')
		else:
			logfile=open("WILL.log",'w')
	def keepcheck(self):
		f=open("settings.conf")
		s=f.read()
		slines=s.split("\n")
		f.close()
		for line in slines:
			if 'keep=' in line:
				mode=line.split('=')[1]
				if mode=='true':
					return True
				else:
					return False
			else:
				pass
	def debug(self):
		f=open("settings.conf")
		s=f.read()
		slines=s.split("\n")
		f.close()
		for line in slines:
			if 'debug=' in line:
				mode=line.split('=')[1]
				if mode=='true':
					return True
				else:
					return False
			else:
				pass
	def write(self, item, logtype):
		logtype=logtype.lower()
		if logtype=="error":
			color='red'
		elif logtype=="success":
			color='green'
		elif logtype=='trying':
			color='yellow'
		elif logtype=='working':
			color='blue'
		else:
			color='white'
		logtime=('[{0}]'.format(str(datetime.datetime.now()).split(" ")[1].split('.')[0]))
		logitem=colored(item,color)
		finallog=("{0}: {1}".format(logtime,item))
		debuglog=("{0}: {1}".format(logtime,logitem))
		debug=self.debug()
		logfile=open("WILL.log", 'a')
		logfile.write('{0}\n'.format(finallog))
		if debug:
			print debuglog