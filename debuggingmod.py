import logging
import subprocess
import filestoragemod


logger = logging.getLogger("hydrosys4."+__name__)

SENTERRORTEXT=""


def createfiletailsyslog(dstfile):
	rownumber="100"
	data=tailsyslogcmd(rownumber)
	if data:
		filestoragemod.savefiledata_plaintext(dstfile,data)
		return True
	else:
		print "data empty"
		return False


def searchsyslogkeyword(keyword):
	rownumber="300"
	data=tailsyslogcmd(rownumber)
	numrowafter=10
	countdown=0
	extract=[]
	for row in data:
		if keyword.lower() in row.lower():
			countdown=numrowafter
		if countdown:
			extract.append(row)
			countdown=countdown-1
	return extract

def searchLOGkeyword(filename,keyword):
	print "debugging check errors in: ", filename
	rownumber="300"
	data=tailLOGcmd(filename,rownumber)
	numrowafter=10
	countdown=0
	extract=[]
	for row in data:
		if keyword.lower() in row.lower():
			countdown=numrowafter
		if countdown:
			extract.append(row)
			countdown=countdown-1
	return extract


def tailsyslogcmd(rownumber):
	syslogfile="/var/log/syslog"
	cmd = ['tail', syslogfile , '-n '+ str(rownumber)]
	return execcommand(cmd)

def tailLOGcmd(filename,rownumber):
	cmd = ['tail', filename , '-n '+ str(rownumber)]
	return execcommand(cmd)	


def execcommand(cmd):
	try:
		scanoutput = subprocess.check_output(cmd).decode('utf-8')
	except:
		print "error to execute the command" , cmd
		logger.error("error to execute the command %s",cmd)
		return []
	return scanoutput.split('\n')



	
if __name__ == '__main__':
	# comment
	#a=[]
	print "Hello"

