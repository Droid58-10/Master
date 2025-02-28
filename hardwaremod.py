# -*- coding: utf-8 -*-
"""
selected plan utility
"""
import shutil
import logging
import re
import os
import os.path
import sys
import string
import random
from datetime import datetime,date,timedelta
import time
import filestoragemod
import HWcontrol
import photomod
import cameradbmod
import struct
import imghdr
import copy
import statusdataDBmod



# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////


global DATABASEPATH
DATABASEPATH=filestoragemod.DATABASEPATH
global HWDATAFILENAME
HWDATAFILENAME="hwdata.txt"
global DEFHWDATAFILENAME
DEFHWDATAFILENAME="default/defhwdata.txt"

logger = logging.getLogger("hydrosys4."+__name__)
print "logger name ", __name__

# ///////////////// -- Hawrware data structure Setting --  ///////////////////////////////
#important this data is used almost everywhere

HWdataRECORDKEY=[]
HWdataKEYWORDS={}

# HW_INFO group includes info for the UI and identification of the item
HW_INFO_IOTYPE="IOtype" # info group, needed, specify if input or output 
HW_INFO_NAME="name" # info group , mandatory, identifier of the item  (shown in the UI)
HW_INFO_MEASUREUNIT="unit"  # info group , mandatory, measurement unit of info parameter
HW_INFO_MEASURE="measure"  # info group , mandatory, measurement type of info parameter

# HW_CTRL group includes info hardware to speak with HWcontrol module
HW_CTRL_CMD="controllercmd" # HW control group , mandatory, command sent to the HWControl section to specify the function to select -> HW
HW_CTRL_PIN="pin" # HW control  group ,optional, specify the PIN board for the HWControl if needed -> gpiopin
HW_CTRL_PIN2="pin2" # HW control  group ,optional, specify the PIN board for the HWControl if needed -> gpiopin (new item in rel 1.08)
HW_CTRL_ADCCH="ADCchannel" # HW control  group , optional, specify the arg1 board for the HWControl if needed -> "ADCchannel"
HW_CTRL_PWRPIN="powerpin"  # HW control  group , optional, specify PIN that is set ON before starting tasks relevant to ADC convert, Actuator pulse, then is set OFF when the task is finished -> "ADCpowerpin"
HW_CTRL_LOGIC="logic"  # HW control  group , optional, in case the relay works in negative logic
#"settingaction", # HW control  group , use the controllercmd instead -> to be removed
HW_CTRL_ADDR="address" # HW control  group , optional, specify this info for the HWControl if needed -> mailaddress, I2C address
HW_CTRL_TITLE="title" # HW control  group , optional, specify this info for the HWControl if needed (mail title) -> "mailtitle"

#servo/stepper/sensors
HW_CTRL_FREQ="frequency" # HW control  group , optional, working frequency of the servo
HW_CTRL_MIN="min"  # HW control  group , optional, minimum of the duty cycle, for sensor this is the min corresponding to zero
HW_CTRL_MAX="max"  # HW control  group , optional, maximum of the duty cycle, for sensor this is the max corresponding to scale

HW_CTRL_SCALE="scale"  # HW control  group , optional, for sensor this is the scale (new item in rel 1.08)
HW_CTRL_OFFSET="offset"  # HW control  group , optional, for sensor not clear how to use TBD (new item in rel 1.08)
HW_CTRL_DIR="direction"  # HW control  group , optional, invert the data min/max (new item in rel 1.08)


HW_FUNC_USEDFOR="usefor" # function group , optional, description of main usage of the item and the actions associated with the plan "selectedplanmod"
HW_FUNC_SCHEDTYPE="schedulingtype" # function group , optional, between "oneshot" and "periodic" 
HW_FUNC_TIME="time"  #function group , optional, description of time or interval to activate the item depending on the "schedulingtype" item, in case of interval information the minutes are used for the period, seconds are used for start offset

USAGELIST=["sensorquery", "watercontrol", "fertilizercontrol", "lightcontrol", "temperaturecontrol", "humiditycontrol", "photocontrol", "mailcontrol", "powercontrol", "N/A", "Other"]
MEASURELIST=["Temperature", "Humidity" , "Light" , "Pressure" , "Time", "Quantity", "Moisture","Percentage","Events"]
MEASUREUNITLIST=["C", "%" , "Lum" , "hPa" , "Sec", "Pcs", "Volt","F"]


HWdataKEYWORDS[HW_INFO_IOTYPE]=["input"  , "output" ]
HWdataKEYWORDS[HW_INFO_NAME]=[]
HWdataKEYWORDS[HW_INFO_MEASUREUNIT]=MEASUREUNITLIST
HWdataKEYWORDS[HW_INFO_MEASURE]=MEASURELIST
HWdataKEYWORDS[HW_CTRL_CMD]=HWcontrol.HWCONTROLLIST
HWdataKEYWORDS[HW_CTRL_PIN]=HWcontrol.RPIMODBGPIOPINLISTPLUS
HWdataKEYWORDS[HW_CTRL_PIN2]=HWcontrol.RPIMODBGPIOPINLISTPLUS

HWdataKEYWORDS[HW_CTRL_ADCCH]=HWcontrol.ADCCHANNELLIST
HWdataKEYWORDS[HW_CTRL_PWRPIN]=HWcontrol.RPIMODBGPIOPINLISTNA
HWdataKEYWORDS[HW_CTRL_LOGIC]=["pos","neg"]
HWdataKEYWORDS[HW_CTRL_ADDR]=[]
HWdataKEYWORDS[HW_CTRL_TITLE]=[]
HWdataKEYWORDS[HW_FUNC_USEDFOR]=USAGELIST #used for
HWdataKEYWORDS[HW_FUNC_SCHEDTYPE]=["oneshot", "periodic"] #scheduling type
HWdataKEYWORDS[HW_FUNC_TIME]=[] #time in format hh:mm:ss

HWdataKEYWORDS[HW_CTRL_FREQ]=[]
HWdataKEYWORDS[HW_CTRL_MIN]=[]
HWdataKEYWORDS[HW_CTRL_MAX]=[]

HWdataKEYWORDS[HW_CTRL_SCALE]=[]
HWdataKEYWORDS[HW_CTRL_OFFSET]=[]
HWdataKEYWORDS[HW_CTRL_DIR]=["dir","inv"]


# ///////////////// -- Hawrware data structure Setting --  ///////////////////////////////

IOdata=[]
# read IOdata -----
if not filestoragemod.readfiledata(HWDATAFILENAME,IOdata): #read calibration file
	print "warning hwdata file not found -------------------------------------------------------"
	#read from default file
	filestoragemod.readfiledata(DEFHWDATAFILENAME,IOdata)
	print "writing default calibration data"
	filestoragemod.savefiledata(HWDATAFILENAME,IOdata)
# end read IOdata -----
IOdatatemp=copy.deepcopy(IOdata)
IOdatarow={}

# ///////////////// --- END GLOBAL VARIABLES ------


# ///////////////// -- STATUS VARIABLES UTILITY --  ///////////////////////////////
Servo_Status={}
Servo_Status["default"]={'duty':"3"}

Stepper_Status={}
Stepper_Status["default"]={'position':"0"}

Hbridge_Status={}
Hbridge_Status["default"]={'position':"0"}

Blocking_Status={}
Blocking_Status["default"]={'priority':0} # priority level, the commands are executed only if the command priority is higher or equlal to the blocking status priority

# ///////////////// --- END STATUS VARIABLES ------




	
	

#-- start filestorage utility--------////////////////////////////////////////////////////////////////////////////////////	

# filestoragemod.readfiledata(filename,filedata)
# filestoragemod.savefiledata(filename,filedata)
# filestoragemod.appendfiledata(filename,filedata)
# filestoragemod.savechange(filename,searchfield,searchvalue,fieldtochange,newvalue)
# filestoragemod.deletefile(filename)

def readfromfile():
	global IOdata
	filestoragemod.readfiledata(HWDATAFILENAME,IOdata)


def IOdatatempalign():
	global IOdatatemp
	IOdatatemp=copy.deepcopy(IOdata)

def	IOdatafromtemp():
	global IOdata
	IOdata=copy.deepcopy(IOdatatemp)
	filestoragemod.savefiledata(HWDATAFILENAME,IOdata)
	
def checkdata(fieldtocheck,dictdata,temp=True): # check if basic info in the fields are correct
# name is the unique key indicating the row of the list, dictdata contains the datato be verified
	# check the "name" field
	fieldname=HW_INFO_NAME
	if (fieldtocheck==fieldname)or(fieldtocheck==""):
		if fieldname in dictdata:
			fieldvalue=dictdata[fieldname]	
			if fieldvalue=="":
				message="Name is empty"
				return False, message
			elif not re.match("^[A-Za-z0-9_-]*$", fieldvalue):
				message="Name should not contains alphanumeric caracters or spaces"
				return False, message		
			else:
				#check same name already present in IOdatatemp
				if searchmatch(fieldname,fieldvalue,temp):
					message="Same name is already present"
					return False, message
					
	
	fieldname=HW_FUNC_TIME
	correlatedfield=HW_INFO_IOTYPE	
	if (fieldtocheck==fieldname)or(fieldtocheck==""):
		if (correlatedfield in dictdata)and(fieldname in dictdata):
			fieldvalue=dictdata[fieldname]	
			if fieldvalue!="":
				#check format is correct
				if len(fieldvalue.split(":"))<3:
					message="Please enter correct time format hh:mm:ss"
					return False, message
			else:

				if dictdata[correlatedfield]=="input":
					message="Time cannot be empty for item belonging to input"
					return False, message	
	
	
	# check select field dependencies
	#dictdata[HW_INFO_IOTYPE]=["input"  , "output" ]
	#dictdata[HW_INFO_MEASUREUNIT]=MEASUREUNITLIST
	#dictdata[HW_INFO_MEASURE]=MEASURELIST
	#dictdata[HW_CTRL_CMD]=HWcontrol.HWCONTROLLIST

	fieldname=HW_CTRL_PIN	
	correlatedfield=HW_CTRL_CMD
	if (fieldtocheck==fieldname)or(fieldtocheck==""):
		if (correlatedfield in dictdata)and(fieldname in dictdata):
			if dictdata[correlatedfield]=="pulse":

				fieldvalue=dictdata[fieldname]	
				if fieldvalue!="N/A":
					if searchmatch(fieldname,fieldvalue,temp):
						message="Same PIN already used"
						return False, message
		
	#dictdata[HW_CTRL_ADCCH]=HWcontrol.ADCCHANNELLIST
	#dictdata[HW_CTRL_PWRPIN]=HWcontrol.RPIMODBGPIOPINLIST
	#dictdata[HW_CTRL_LOGIC]=["pos","neg"]
	#dictdata[HW_FUNC_USEDFOR]=USAGELIST #used for
	#dictdata[HW_FUNC_SCHEDTYPE]=["oneshot", "periodic"] #scheduling type
	return True, ""

def sendcommand(cmd,sendstring,recdata,target="", priority=0):
	if target!="":
		prioritystatus=statusdataDBmod.read_status_data(Blocking_Status,target,'priority')
		#print " Target output ", target , "priority status: ", prioritystatus , " Command Priority: ", priority
		#check if the actions are blocked
		if priority>=prioritystatus:
			return HWcontrol.sendcommand(cmd,sendstring,recdata)
		else:
			successflag=0
			recdata.append(cmd)
			recdata.append("blocked")
			recdata.append(successflag)
			return True
	else:
		return HWcontrol.sendcommand(cmd,sendstring,recdata)

def normalizesensordata(reading_str,sensorname):
	scaledefault=1
	offsetdefault=0
	Thereading=reading_str
	print " Sensor " , sensorname  , "reading ",Thereading
	print " Sensor value post elaboration"
	
	# get the normalization data
	Minimum=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_MIN)) # if not found searchdata return ""
	Maximum=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_MAX))
	Direction=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_DIR)) # can be two values "inv" , "dir"
	Scale=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_SCALE))
	Offset=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_OFFSET))					
	
	# transform all valuse in numbers
	Minvalue=tonumber(Minimum, 0)
	Maxvalue=tonumber(Maximum, 0)
	Scalevalue=tonumber(Scale, scaledefault)
	Offsetvalue=tonumber(Offset, offsetdefault)					
	readingvalue=tonumber(Thereading, 0)
	if abs(Minvalue-Maxvalue)>0.01: # in case values are zero or not consistent, stops here
		if Direction!="inv":
			den=Maxvalue-Minvalue
			readingvalue=(readingvalue-Minvalue)/den
		else:
			den=Maxvalue-Minvalue
			readingvalue=1-(readingvalue-Minvalue)/den
	if Scalevalue>0:
		readingvalue=readingvalue*Scalevalue		
	readingvalue=readingvalue+Offsetvalue
	
	# transform to string and adjust the format
	Thereading=str('%.2f' % readingvalue)
	return Thereading

def getsensordata(sensorname,attemptnumber): #needed
	# this procedure was initially built to communicate using the serial interface with a module in charge of HW control (e.g. Arduino)
	# To lower the costs, I used the PI hardware itself but I still like the way to communicate with the HWcontrol module that is now a SW module not hardware
	cmd=searchdata(HW_INFO_NAME,sensorname,HW_CTRL_CMD)
	Thereading=""	
	if not cmd=="":
		pin=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_PIN))
		arg1=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_ADCCH))
		arg2=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_PWRPIN))
		arg3=str(searchdata(HW_INFO_NAME,sensorname,HW_INFO_MEASUREUNIT))
		arg4=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_LOGIC))
		arg5=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_ADDR))
		arg6=str(searchdata(HW_INFO_NAME,sensorname,HW_CTRL_PIN2))
		
		sendstring=sensorname+":"+pin+":"+arg1+":"+arg2+":"+arg3+":"+arg4+":"+arg5+":"+arg6
		recdata=[]
		ack=False
		i=0
		while (not ack)and(i<attemptnumber): # old check when the serial interface was used, in this case ack only indicates that the trasmission was correct, not the sensor value
			ack=sendcommand(cmd,sendstring,recdata,sensorname,0)
			i=i+1
		if ack:
			if recdata[0]==cmd: # this was used to check the response and command consistency when serial comm was used
				if recdata[2]>0: # this is the flag that indicates if the measurement is correct
					#print " Sensor " , sensorname  , "reading ",recdata[1]	
									
					Thereading=normalizesensordata(recdata[1],sensorname)  # output is a string

					print " Sensor " , sensorname  , "Normalized reading ",Thereading												
					
				else:
					print "Problem with sensor reading ", sensorname
					logger.error("Problem with sensor reading: %s", sensorname)
			else:
				print "Problem with response consistency ", sensorname , " cmd " , cmd
				logger.error("Problem with response consistency : %s", sensorname)
		else:
			print "no answer from Hardware control module", sensorname
			logger.error("no answer from Hardware control module: %s", sensorname)
	else:
		print "sensor name not found in list of sensors ", sensorname
		logger.error("sensor name not found in list of sensors : %s", sensorname)
	return Thereading

def makepulse(target,duration,addtime=True, priority=0): # pulse in seconds , addtime=True extend the pulse time with new time , addtime=False let the current pulse finish , 
	#search the data in IOdata
	
	print "Check target is already ON ", target
	activated=getpinstate(target, priority)
	if activated=="error":
		return "error"
	if activated=="on":
		if not addtime:
			print "Already ON, no action"
			return "Already ON"
		else:
			print "Already ON, add time"

	
	print "Fire Pulse - ", target
	
	PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)	
	

	try:
		testpulsetimeint=int(duration)
		testpulsetime=str(testpulsetimeint) # durantion in seconds 
	except ValueError:
		print " No valid data or zero  ", target
		return "error"

	logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)
	POWERPIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PWRPIN)

	# dual pulse option, a short pulse activate at beginning of th time and another short pulse at the end of the activation period, 
	# MIN and MAX are the duration of the subpulses in seconds.
	MIN=toint(searchdata(HW_INFO_NAME,target,HW_CTRL_MIN),0)
	MAX=toint(searchdata(HW_INFO_NAME,target,HW_CTRL_MAX),0)
	if MIN and MAX:
		# dual pulse setting
		if (MIN>=testpulsetimeint)or(MAX>=testpulsetimeint):
			return "error MIN or MAX >Pulsetime"
		sendstring="pulse:"+PIN+":"+testpulsetime+":"+logic+":"+POWERPIN+":"+str(MIN) +":"+str(MAX)
	else:
		# normal pulse
		sendstring="pulse:"+PIN+":"+testpulsetime+":"+logic+":"+POWERPIN

	print "logic " , logic , " sendstring " , sendstring
	isok=False	
	if float(testpulsetime)>0:
		print "Sendstring  ", sendstring	
		isok=False
		i=0
		while (not(isok))and(i<2):
			i=i+1
			recdata=[]
			ack= sendcommand("pulse",sendstring,recdata,target,priority)
			print "returned data " , recdata
			# recdata[0]=command (string), recdata[1]=data (string) , recdata[2]=successflag (0,1)
			if ack and recdata[2]:
				print target, "correctly activated"
				isok=True
				return "Pulse Started"
			else:
				if not recdata[2]:
					return recdata[1]
			
			
	return "error"
	
	
def stoppulse(target):
	#search the data in IOdata
	
	print "Check target is already OFF ", target
	activated=getpinstate(target)
	if activated=="error":
		return "error"
	if activated=="off":
		print "Already OFF"
		return "Already OFF"

	print "Stop Pulse - ", target
	
	PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)	
	
	logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)
	POWERPIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PWRPIN)

	# dual pulse option, a short pulse activate at beginning of th time and another short pulse at the end of the activation period, 
	# MIN and MAX are the duration of the subpulses in seconds.
	MIN=toint(searchdata(HW_INFO_NAME,target,HW_CTRL_MIN),0)
	MAX=toint(searchdata(HW_INFO_NAME,target,HW_CTRL_MAX),0)
	if MIN and MAX:
		# dual pulse setting
		sendstring="stoppulse:"+PIN+":"+"0"+":"+logic+":"+POWERPIN+":"+str(MIN) +":"+str(MAX)
	else:
		# normal pulse
		sendstring="stoppulse:"+PIN+":"+"0"+":"+logic+":"+POWERPIN

	print "logic " , logic , " sendstring " , sendstring

	isok=False
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand("stoppulse",sendstring,recdata,target,5)
		print "returned data " , recdata
		if ack and recdata[1]!="e":
			print target, "correctly activated"
			isok=True
			return "Stopped"
			
	return "error"

def servoangle(target,percentage,delay,priority=0): #percentage go from zeo to 100 and is the percentage between min and max duty cycle
	
	global Servo_Status
	#search the data in IOdata
	isok=False
	
	print "Move Servo - ", target #normally is servo1
	
	# check if servo is belonging to servolist
	servolist=searchdatalist(HW_CTRL_CMD,"servo",HW_INFO_NAME)
	
	if target in servolist:
	
		PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)	

		try:

			FREQ=searchdata(HW_INFO_NAME,target,HW_CTRL_FREQ)	
			MIN=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)	
			MAX=searchdata(HW_INFO_NAME,target,HW_CTRL_MAX)	

			previousduty=getservoduty(target) 
			dutycycle= str(int(MIN)+(int(MAX)-int(MIN))*int(percentage)/float(100))
			stepsnumber="40" # this should be a string
			
			difference=float(previousduty)-float(dutycycle)
			percentagediff=abs(float(100)*difference/(int(MAX)-int(MIN)))
			
			if percentagediff<1: # one percent difference
				print " No difference with prevoius position ", target , " percentage difference ", percentagediff
				return "same" , isok				
			
			if 0<=int(percentage)<=100:
				print "range OK"
			else:
				print " No valid data for Servo ", target , " out of Range"
				return "Out of Range" , isok

		except ValueError:
			print " No valid data for Servo", target
			return "error" , isok


		sendstring="servo:"+PIN+":"+FREQ+":"+dutycycle+":"+str(delay)+":"+previousduty+":"+stepsnumber
		print " sendstring " , sendstring

		i=0
		while (not(isok))and(i<2):
			i=i+1
			recdata=[]
			ack= sendcommand("servo",sendstring,recdata,target,priority)
			print "returned data " , recdata
			if ack and recdata[1]!="e":
				print target, "correctly activated"
				# save duty as new status
				statusdataDBmod.write_status_data(Servo_Status,target,'duty',dutycycle)
				isok=True
				return percentage , isok
			
	return "error" , isok

def getservopercentage(target):
	percentage="50"
	MIN=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)	
	MAX=searchdata(HW_INFO_NAME,target,HW_CTRL_MAX)	
	
	if (not MIN=="")and(not MAX==""):
		#print " MIN ", MIN , " MAX ", MAX
		try:
			den=(int(MAX)-int(MIN))
			percentage_num=int((100*(float(getservoduty(target))-int(MIN)))/den)
			if percentage_num<0:
				percentage_num=0
			if percentage_num>100:
				percentage_num=100
			percentage=str(percentage_num)
		except:
			print " No valid data for Servo", target

	print "servo percntage " , percentage
	return percentage

def getservoduty(element):
	return statusdataDBmod.read_status_data(Servo_Status,element,'duty')


# stepper section

def GO_stepper_position(target,position,priority=0):
	prev_position_string=getstepperposition(target)
	prev_position=int(prev_position_string)
	steps=position-prev_position
	isdone=False
	if steps>0:
		out , isdone=GO_stepper(target,steps,"FORWARD",priority)
	else:
		steps=abs(steps)	
		out , isdone=GO_stepper(target,steps,"BACKWARD",priority)
		
	return out , isdone


def get_stepper_busystatus(target): 
	tempdict , isok=get_stepper_HWstatus(target)
	if isok:
		if "busyflag" in tempdict:
			return tempdict["busyflag"]
	return ""
	
	
	
def get_stepper_HWstatus(target): 
	#search the data in IOdata
	isok=False
	
	try:
		Interface_Number=searchdata(HW_INFO_NAME,target,HW_CTRL_ADCCH)
	except ValueError:
		return "error" , isok
		
	sendstring="stepperstatus:"+Interface_Number
	print " sendstring " , sendstring
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand("stepperstatus",sendstring,recdata,target,0) 
		print "returned data " , recdata
		if ack:
			print target, "correctly activated"	
			print "get stepper status : " , recdata[1]
			isok=True
			return recdata[1], isok
			
	return "Error" , isok



def GO_stepper(target,steps,direction,priority=0): 
	global Stepper_Status
	#search the data in IOdata
	isok=False
	print "Move Stepper - ", target #only supported the I2C default address, the module supports 2 stepper interfaces: 1,2
	
	position_string=getstepperposition(target)
	
	print " position " , position_string
 
	try:
		Interface_Number=searchdata(HW_INFO_NAME,target,HW_CTRL_ADCCH)	
		FREQ=searchdata(HW_INFO_NAME,target,HW_CTRL_FREQ)	
		MIN=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)	
		MAX=searchdata(HW_INFO_NAME,target,HW_CTRL_MAX)	

		steps=int(steps)
		
		if steps<=0:
			print " No valid range for Stepper ", target
			return "Out of Range" , isok
		
		# simulate endpoints
		position=int(position_string)
		
		if direction=="FORWARD":
			position=position+steps
		elif direction=="BACKWARD":
			position=position-steps

		if int(MIN)<=(position)<=int(MAX):
			print "range OK"
		else:
			print " No valid range for Stepper ", target
			return "Out of Range" , isok

	except ValueError:
		print " No valid data for Servo", target
		return "error" , isok


	sendstring="stepper:"+Interface_Number+":"+direction+":"+FREQ+":"+str(steps)
	print " sendstring " , sendstring

	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand("stepper",sendstring,recdata,target,priority) 
		print "returned data " , recdata
		if ack and recdata[1]!="e":
			print target, "correctly activated"
			# save position as new status
			statusdataDBmod.write_status_data(Stepper_Status,target,'position',str(position),True,"Stepper_Status")
			
			isok=True
			return str(position) , isok
			
	return "Error" , isok

def getstepperposition(element):
	return statusdataDBmod.read_status_data(Stepper_Status,element,'position',True,"Stepper_Status")

def setstepperposition(element, position):
	global Stepper_Status
	return statusdataDBmod.write_status_data(Stepper_Status,element,'position',position,True,"Stepper_Status")


# END stepper section

# START hbridge section

def GO_hbridge_position(target,position,priority=0):
	prev_position_string=gethbridgeposition(target)
	prev_position=int(prev_position_string)
	MINstr=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)
	MIN=toint(MINstr,0)
	zerooffset=0
	steps=position-prev_position
	absolutesteps=abs(steps)
	if position<=MIN: # the final position is intended to be the minimum
		zerooffsetstr=searchdata(HW_INFO_NAME,target,HW_CTRL_OFFSET)
		zerooffset=toint(zerooffsetstr,0)		

	isdone=False
	if steps>0:
		out , isdone=GO_hbridge(target,absolutesteps,zerooffset,"FORWARD",priority)
	else:	
		out , isdone=GO_hbridge(target,absolutesteps,zerooffset,"BACKWARD",priority)
		
	return out , isdone


def get_hbridge_busystatus(target): 
	
	PIN1=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)
	PIN2=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN2)		
	logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)
	
	print "Check target is already ON ", target
	priority=0
	activated1=getpinstate_pin(PIN1,logic, priority)
	activated2=getpinstate_pin(PIN2,logic, priority)

	if (activated1=="off")and(activated2=="off"):
		return False
	else:
		return True
		
	return ""
	
	
	
def get_hbridge_HWstatus(target): 
	#search the data in IOdata
	isok=False
	
	try:
		PIN1=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)
		PIN2=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN2)			
	except ValueError:
		return "error" , isok
		
	sendstring="hbridgestatus:"+PIN1+PIN2
	print " sendstring " , sendstring
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand("hbridgestatus",sendstring,recdata,target,0) 
		print "returned data " , recdata
		if ack:
			print target, "correctly activated"	
			print "get hbridge status : " , recdata[1]
			isok=True
			return recdata[1], isok
			
	return "Error" , isok



def GO_hbridge(target,steps,zerooffset,direction,priority=0): 
	global Hbridge_Status
	#search the data in IOdata
	isok=False
	print "Move Hbridge - ", target 
	
	position_string=gethbridgeposition(target)
	
	print " position " , position_string
 
	try:
		PIN1=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)
		PIN2=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN2)	
		logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)	
		MIN=searchdata(HW_INFO_NAME,target,HW_CTRL_MIN)	
		MAX=searchdata(HW_INFO_NAME,target,HW_CTRL_MAX)	

		steps=int(steps)
		
		if steps<=0:
			print " No valid range for pulse ", target
			return "Out of Range" , isok
		
		# simulate endpoints
		position=int(position_string)
		
		if direction=="FORWARD":
			position=position+steps
		elif direction=="BACKWARD":
			position=position-steps

		if int(MIN)<=(position)<=int(MAX):
			print "range OK"
		else:
			print " No valid range for hbridge ", target
			return "Out of Range" , isok

	except ValueError:
		print " No valid data for hbridge", target
		return "error" , isok

	# here apply the offset
	steps=steps+zerooffset
	
	
	sendstring="hbridge:"+PIN1+":"+PIN2+":"+direction+":"+str(steps)+":"+logic
	print " sendstring " , sendstring

	errorcode="error"
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand("hbridge",sendstring,recdata,target,priority) 
		print "returned data " , recdata
		if ack and recdata[1]!="e":
			print target, "correctly activated"
			# save position as new status
			statusdataDBmod.write_status_data(Hbridge_Status,target,'position',str(position),True,"Hbridge_Status") # save in persistent mode
			isok=True
			return str(position) , isok
		else:
			errorcode="error"
			if len(recdata)>2:
				errorcode=recdata[2]
				
	return errorcode , isok

def gethbridgeposition(element):
	return statusdataDBmod.read_status_data(Hbridge_Status,element,'position',True,"Hbridge_Status")

def sethbridgeposition(element, position):
	global Hbridge_Status
	return statusdataDBmod.write_status_data(Hbridge_Status,element,'position',position,True,"Hbridge_Status")


# END hbridge section


def getpinstate(target, priority=0):
	#search the data in IOdata
	print "Check PIN state ", target
	PIN=searchdata(HW_INFO_NAME,target,HW_CTRL_PIN)
	logic=searchdata(HW_INFO_NAME,target,HW_CTRL_LOGIC)
	return getpinstate_pin(PIN, logic, priority)


def getpinstate_pin(PIN, logic, priority=0):

	sendstring="status:"+PIN

	isok=False
	value=0
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand("pinstate",sendstring,recdata)
		print "returned data " , recdata
		if ack and recdata[1]!="e":
			value=recdata[1]
			isok=True
		else:
			activated="error"
			
	if isok:
		if logic=="neg":
			if value=="0":
				activated="on"
			else:
				activated="off"
		elif logic=="pos":
			if value=="1":
				activated="on"
			else:
				activated="off"		

				
	return activated





def readinputpin(PIN):
	#search the data in IOdata
	
	print "Read input PIN ", PIN
	sendstring="inputpin:"+str(PIN)

	isok=False
	value=0
	i=0
	while (not(isok))and(i<2):
		i=i+1
		recdata=[]
		ack= sendcommand("readinputpin",sendstring,recdata,target="")
		print "returned data " , recdata
		if ack and recdata[2]:
			value=recdata[1]
			isok=True
		else:
			value="error"
			
	return value # either "0" or "1"
	
	
	

def getsensornamebymeasure(measure):
	# MEASURELIST is the list with valid values for the "measure" parameter
	sensorlist=searchdatalist(HW_INFO_MEASURE,measure,HW_INFO_NAME)
	return sensorlist

			
def readallsensors():
	# read from serial the values for arduino
	sensorlist=searchdatalist(HW_INFO_IOTYPE,"input",HW_INFO_NAME)
	sensorvalues={}
	for sensorname in sensorlist:
		sensorvalues[sensorname]=getsensordata(sensorname,3)
	return sensorvalues



			
def checkallsensors():
	# check if the sensor respond properly according to sensor list in HWdata file
	print " check sensor list "
	sensorlist=searchdatalist(HW_INFO_IOTYPE,"input",HW_INFO_NAME)
	sensorvalues={}
	for sensorname in sensorlist:
		sensorvalues[sensorname]=getsensordata(sensorname,3)
	return sensorvalues

		
def initallGPIOpins():	
	removeallinterruptevents()
	checkGPIOconsistency()
	initallGPIOoutput()
	return True

def setallGPIOinputs():	# this function sets all GPIO to input, actually it disable I2C and SPI as this functions are set using the PIN special mode Alt0
	for pinstr in HWcontrol.RPIMODBGPIOPINLIST:
		HWcontrol.GPIO_setup(pinstr, "in")
	return True
	
def checkGPIOconsistency():	
	# chek PIN in input and output cannot be the same
	inputpinlist=[]
	outputpinlist=[]	
	for ln in IOdata:
		if (HW_INFO_IOTYPE in ln) and (HW_CTRL_PIN in ln):
			iotype=ln[HW_INFO_IOTYPE]
			PIN=ln[HW_CTRL_PIN]
			if (iotype=="input"):
				if PIN in inputpinlist:
					print "Warning input PIN duplicated", PIN
					logger.warning('Warning, input PIN duplicated PIN=%s', PIN)					
				inputpinlist.append(PIN)
			if (iotype=="output"):
				if (PIN in outputpinlist)and(PIN in HWcontrol.RPIMODBGPIOPINLIST):
					print "Warning output PIN duplicated", PIN
					logger.warning('Warning, output PIN duplicated PIN=%s', PIN)
				else:
					outputpinlist.append(PIN)
				if (HW_CTRL_PWRPIN in ln):
					PWRPIN=ln[HW_CTRL_PWRPIN]
					if (PWRPIN in outputpinlist)and(PWRPIN in HWcontrol.RPIMODBGPIOPINLIST):
						print "Warning output PWRPIN overlapping", PWRPIN
						logger.warning('Warning, output PWRPIN overlapping PIN=%s', PWRPIN)
					else:
						outputpinlist.append(PWRPIN)
				if (HW_CTRL_PIN2 in ln):
					PIN2=ln[HW_CTRL_PIN2]
					if (PIN2 in outputpinlist)and(PIN2 in HWcontrol.RPIMODBGPIOPINLIST):
						print "Warning output PIN2 overlapping", PIN2
						logger.warning('Warning, output PIN2 overlapping PIN=%s', PIN2)
					else:
						outputpinlist.append(PIN2)
				

		if (HW_CTRL_PWRPIN in ln):
			PWRPIN=ln[HW_CTRL_PWRPIN]
			outputpinlist.append(PWRPIN)
				
	#print inputpinlist
	#print outputpinlist
				
	for inputpin in inputpinlist:
		if inputpin in outputpinlist:
			if inputpin in HWcontrol.RPIMODBGPIOPINLIST:
				print "error output PIN and Input PIN are the same", inputpin
				logger.error('Error, output PIN and Input PIN are the same PIN=%s', inputpin)

	return True

		
def initallGPIOoutput():	
	for ln in IOdata:
		iotype=ln[HW_INFO_IOTYPE]
		
		# output: set gpio status
		if (iotype=="output") :
			if (ln[HW_CTRL_CMD]=="pulse"):
				# safe code in case of non int input
				PIN=ln[HW_CTRL_PIN]
				HWcontrol.GPIO_setup(PIN, "out")
				if ln[HW_CTRL_LOGIC]=="pos":
					HWcontrol.GPIO_output(PIN, 0)
				else:
					HWcontrol.GPIO_output(PIN, 1)
			elif (ln[HW_CTRL_CMD]=="hbridge"):
				PIN1=ln[HW_CTRL_PIN]
				PIN2=ln[HW_CTRL_PIN2]
				HWcontrol.GPIO_setup(PIN1, "out")
				HWcontrol.GPIO_setup(PIN2, "out")
				if ln[HW_CTRL_LOGIC]=="pos":
					HWcontrol.GPIO_output(PIN1, 0)
					HWcontrol.GPIO_output(PIN2, 0)
				else:
					HWcontrol.GPIO_output(PIN1, 1)
					HWcontrol.GPIO_output(PIN2, 1)				
			
		# powerpin		
		if (HW_CTRL_PWRPIN in ln):
			PWRPIN=ln[HW_CTRL_PWRPIN] 
			HWcontrol.GPIO_setup(PWRPIN, "out")
			if (HW_CTRL_LOGIC in ln):
				if (ln[HW_CTRL_LOGIC]=="pos") or (ln[HW_CTRL_LOGIC]==""):
					HWcontrol.GPIO_output(PWRPIN, 0)
					#print "power PIN ", ln[HW_CTRL_PWRPIN] , " set to 0 " 
				else:
					HWcontrol.GPIO_output(PWRPIN, 1)
					#print "power PIN ", ln[HW_CTRL_PWRPIN] , " set to 1 " 					
			else:			
				HWcontrol.GPIO_output(PWRPIN, 0) # assume logic is positive
				print "power PIN ", ln[HW_CTRL_PWRPIN] , " set to 0, No logic information available " 	

		# Input: enable one wire
		if (iotype=="input") :
			if (ln[HW_CTRL_CMD]=="DS18B20"):
				# safe code in case of non int input
				PIN=ln[HW_CTRL_PIN]
				logic=ln[HW_CTRL_LOGIC]
				Set_1wire_Pin(PIN,logic)


	#print HWcontrol.GPIO_data
	return True

def Set_1wire_Pin(PIN,logic):
	#Newer kernels (4.9.28 and later) allow you to use dynamic overlay loading, 
	#including creating multiple 1-Wire busses to be used at the same time:

	#sudo dtoverlay w1-gpio gpiopin=4 pullup=0 pull-up does not seem to work
	
	try:
		# These tow lines mount the device, anyway seems not to be needed
		cmdstring="dtoverlay w1-gpio gpiopin="+PIN
		os.system(cmdstring)
		os.system('modprobe w1-gpio')
		os.system('modprobe w1-therm')
		if logic=="pos":
			HWcontrol.GPIO_setup(PIN, "in", "pull_up")
		else:
			HWcontrol.GPIO_setup(PIN, "in")
		
		# dtoverlay w1-gpio gpiopin=4 pullup=0		
		#cmd = ['dtoverlay', 'w1-gpio' , 'gpiopin='+ PIN, 'pullup=0']		
		#ifup_output = subprocess.check_output(cmd).decode('utf-8')
		return True
	except:
		print "Fail to set the One Wire driver"
		logger.error('Fail to set the One Wire driver')
		return False

def get_devices_list():
	outlist=[]
	devtype="One Wire"
	devicelist=HWcontrol.get_1wire_devices_list()
	
	print devicelist
	for item in devicelist:
		outlist.append({"address":item , "type":devtype})
		
	devtype="I2C"
	devicelist=HWcontrol.get_I2C_devices_list()
	for item in devicelist:
		outlist.append({"address":item , "type":devtype})
		
	return outlist
		
def get_device_list_address_property():
	addresslist=get_devices_list()
	#print "before=",  addresslist
	for item in addresslist:
		if item["type"]=="I2C":
			recordkey=HW_CTRL_PIN
			recordvalue="I2C"
			recordkey1=HW_CTRL_ADDR
			recordvalue1=item["address"]
			keytosearch=HW_INFO_NAME
			namelist=searchdatalist2keys(recordkey,recordvalue,recordkey1,recordvalue1,keytosearch)
			item["message"]=""
			item["name"]=""
			item["cmd"]=""			
			if len(namelist)==1:
				# found only one item corresponding to the search
				item["name"]=namelist[0]
				# find the associated command
				recordkey=HW_INFO_NAME
				recordvalue=item["name"]				
				keytosearch=HW_CTRL_CMD
				item["cmd"]=searchdata(recordkey,recordvalue,keytosearch)								
			elif len(namelist)==0:
				item["message"]="Unknown"
			elif len(namelist)>1:
				item["message"]="Duplicated!!"


			# flag to enable the change address button
			# currently only one hardware support this option
			item["changeaddressflag"]=""
			if item["cmd"]=="Hygro24_I2C":
				item["changeaddressflag"]="1"
		else:
			item["message"]=""
			item["name"]=""
			item["cmd"]=""
			item["changeaddressflag"]=0
			
	print "after=",  addresslist
	return addresslist



def GPIO_setup(PIN, state, pull_up_down):
	HWcontrol.GPIO_setup(PIN, state, pull_up_down)

def GPIO_add_event_detect(PIN, evenslopetype, eventcallback , bouncetimeINT=200):
	HWcontrol.GPIO_add_event_detect(PIN, evenslopetype, eventcallback , bouncetimeINT)

def GPIO_remove_event_detect(PIN):
	HWcontrol.GPIO_remove_event_detect(PIN)

def removeallinterruptevents():
	for channel in HWcontrol.RPIMODBGPIOPINLIST: 
		try:
			#print "try to remove event detect ", channel
			GPIO_remove_event_detect(channel)
		except:
			#print "Warning, not able to remove the event detect"
			a=1
		
	return ""


def removeinterruptevents():
	print "load interrupt list "
	interruptlist=searchdatalist2keys(HW_INFO_IOTYPE,"input", HW_CTRL_CMD, "readinputpin" ,HW_INFO_NAME)
	print "len interrupt list "	, len(interruptlist)	
	for item in interruptlist:
		print "got into the loop "
		# get PIN number

		recordkey=HW_INFO_NAME
		recordvalue=item	
		keytosearch=HW_CTRL_PIN
		PINstr=searchdata(recordkey,recordvalue,keytosearch)
		print "set event for the PIN ", PINstr

		try:
			HWcontrol.GPIO_remove_event_detect(PIN)
		except:
			print "Warning, not able to remove the event detect"
			logger.info('Warning, not able to remove the event detect')
		
	return ""





def restoredefault():
	filestoragemod.deletefile(HWDATAFILENAME)
	filestoragemod.readfiledata(DEFHWDATAFILENAME,IOdata)
	savecalibartion()
	
def savecalibartion():
	filestoragemod.savefiledata(HWDATAFILENAME,IOdata)

def changesavecalibartion(IOname,IOparameter,IOvalue):  #needed
# questo il possibile dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	for line in IOdata:
		if line[HW_INFO_NAME]==IOname:
			line[IOparameter]=IOvalue
			savecalibartion()
			return True
	return False

def changeIOdatatemp(IOname,IOparameter,IOvalue):  #needed
# questo il possibile dizionario: { 'name':'', 'm':0.0, 'q':0.0, 'lastupdate':'' } #variabile tipo dizionario
	global IOdatatemp
	for line in IOdatatemp:
		if line[HW_INFO_NAME]==IOname:
			line[IOparameter]=IOvalue
			return True
	return False




def searchdata(recordkey,recordvalue,keytosearch):
	for ln in IOdata:
		if recordkey in ln:			
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					return ln[keytosearch]	
	return ""


def deepcopydict(dictin):
	return copy.deepcopy(dictin)

def searchrowtemp(recordkey,recordvalue):
	for ln in IOdatatemp:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				return copy.deepcopy(ln)
	return {}

def searchrowtempbyname(recordvalue):
	recordkey=HW_INFO_NAME
	return searchrowtemp(recordkey,recordvalue)


def searchmatch(recordkey,recordvalue,temp):
	if temp:
		for ln in IOdatatemp:
			if recordkey in ln:
				if ln[recordkey]==recordvalue:
					return True	
		return False
	else:
		for ln in IOdata:
			if recordkey in ln:
				if ln[recordkey]==recordvalue:
					return True	
		return False

def gettimedata(name):
	# return list with three integer values: hour , minute, second
	timestr=searchdata(HW_INFO_NAME,name,HW_FUNC_TIME)
	return separatetimestringint(timestr)


def separatetimestringint(timestr): # given the string input "hh:mm:ss" output a list with  Hour, min, sec in integer format 
	outlist=[]
	timelist=timestr.split(":")
	for i in range(3):
		if i<len(timelist):
			if timelist[i]!="":
				outlist.append(toint(timelist[i],1))
			else:
				outlist.append(0)	
		else:
			outlist.append(0)		
	return outlist
		
def tonumber(thestring, outwhenfail):
	try:
		n=float(thestring)
		return n
	except:
		return outwhenfail

def toint(thestring, outwhenfail):
	try:
		f=float(thestring)
		n=int(f)
		return n
	except:
		return outwhenfail


def searchdatalist(recordkey,recordvalue,keytosearch):
	datalist=[]
	for ln in IOdata:
		if recordkey in ln:
			if ln[recordkey]==recordvalue:
				if keytosearch in ln:
					datalist.append(str(ln[keytosearch]))	
	return datalist

def searchdatalist2keys(recordkey,recordvalue,recordkey1,recordvalue1,keytosearch):
	datalist=[]
	for ln in IOdata:
		if (recordkey in ln)and(recordkey1 in ln):
			if (ln[recordkey]==recordvalue)and(ln[recordkey1]==recordvalue1):
				if keytosearch in ln:
					datalist.append(str(ln[keytosearch]))	
	return datalist



def getfieldvaluelist(fielditem,valuelist):
	del valuelist[:]
	for line in IOdata:
		valuelist.append(line[fielditem])

def getfieldvaluelisttemp(fielditem,valuelist):
	del valuelist[:]
	for line in IOdatatemp:
		valuelist.append(line[fielditem])



def getfieldinstringvalue(fielditem,stringtofind,valuelist):
	del valuelist[:]
	for line in IOdata:
		name=line[fielditem]
		if name.find(stringtofind)>-1:
			valuelist.append(name)

def photolist(apprunningpath, withindays=0):

	folderpath=os.path.join(apprunningpath, "static")
	folderpath=os.path.join(folderpath, "hydropicture")
	# control if the folder hydropicture exist otherwise create it
	if not os.path.exists(folderpath):
		os.makedirs(folderpath)
		print "Hydropicture folder has been created"
	
	filenamelist=[]
	sortedlist=sorted([f for f in os.listdir(folderpath) if os.path.isfile(os.path.join(folderpath, f))])
	sortedlist.reverse()
	for files in sortedlist:
		if (files.endswith(".jpg") or files.endswith(".png")):
			isok=False
			if "@" in files:
				datestr=files.split("@")[0]
			else:
				datestr=files.split(".")[0]
			try:
				dateref=datetime.strptime(datestr,'%y-%m-%d,%H:%M')
				# here check how long time ago the picture was taken
				# if withindays==0 then is not applicable
				if withindays>0:
					todaydate=datetime.now()
					tdelta=timedelta(days=withindays)
					startdate=todaydate-tdelta
					print " startdate " ,startdate
					if dateref>=startdate:
						isok=True
				else:
					isok=True
			except:
				print "file name format not compatible with date"
				
			if isok:
				templist=[]
				templist.append("hydropicture/"+files)
				templist.append("Image taken on "+datestr)
				templist.append(dateref)
				templist.append("hydropicture/thumb/"+files)		
				filenamelist.append(templist)						
			
	return filenamelist # item1 (path+filename) item2 (name for title) item3 (datetime) item4 (thumbpath + filename)

def loglist(apprunningpath,logfolder,searchstring):
	templist=[]	
	folderpath=os.path.join(apprunningpath,logfolder)
	# control if the folder  exist otherwise exit
	if not os.path.exists(folderpath):
		print "log folder does not exist"
		return templist
	filenamelist=[]
	sortedlist=sorted(os.listdir(folderpath))
	sortedlist.reverse()
	for files in sortedlist:
		if (searchstring in files):
			templist.append(files)
	return templist 

def deleteallpictures(apprunningpath):
	#delete pictures
	folderpath=os.path.join(apprunningpath, "static")
	folderpath=os.path.join(folderpath, "hydropicture")	
	sortedlist=os.listdir(folderpath)
	i=0
	for files in sortedlist:
		if os.path.isfile(os.path.join(folderpath, files)):
			os.remove(os.path.join(folderpath, files))
			i=i+1
	#delete thumb 
	paththumb=os.path.join(folderpath,"thumb")
	sortedlist=os.listdir(paththumb)
	i=0
	for files in sortedlist:
		if os.path.isfile(os.path.join(paththumb, files)):
			os.remove(os.path.join(paththumb, files))
			i=i+1
	return i

def HWpresetlist(apprunningpath):
	folderpath=os.path.join(apprunningpath, "database")
	folderpath=os.path.join(folderpath, "default")
	folderpath=os.path.join(folderpath, "presetHWsetting")
	filenamelist=[]
	sortedlist=sorted(os.listdir(folderpath))
	sortedlist.reverse()
	for files in sortedlist:
		if files.startswith("defhwdata"):
			templist=[]
			templist.append("database/default/presetHWsetting/"+files)			
			templist.append(files)
			filenamelist.append(templist)
	return filenamelist # item1 (path) item2 (name)


def removephotodataperiod(removebeforedays, maxphototoremove=20):

	todaydate=datetime.now()
	num = removebeforedays
	tdelta=timedelta(days=num)
	enddate=todaydate-tdelta
	pastdays=364 # number of days between beforeremovedays and start to search
	num = pastdays
	tdelta=timedelta(days=num)
	startdate=enddate-tdelta
	print " stratdate " ,startdate
	print " enddate ", enddate
	
	photodata=photolist(get_path())
	i=0
	for photo in photodata:
		dateref=photo[2]
		if isinstance(dateref, datetime):
			print dateref
			if (dateref>=startdate)and(dateref<=enddate)and(i<maxphototoremove):
				try:
					filepath=os.path.join(get_path(), "static")
					filepath=os.path.join(filepath, photo[0])
					# remove photo
					filestoragemod.deletefile(filepath)
					print "removed Photo " , filepath
					i=i+1
				except ValueError:
					print "Error in photo delete "
		else:
			print "datetime format incorrect"
	thumbconsistency(get_path())

			
	

	
def videodevlist():
	return photomod.videodevlist()
	
def  thumbconsistency(apprunningpath):
	return photomod.thumbconsistency(apprunningpath)
			

def shotit(video,istest,resolution,positionvalue,vdirection):
	shottaken=False
    # send command to the actuator for test
	if istest:
		filepath=os.path.join(get_path(), "static")
		filepath=os.path.join(filepath, "cameratest")
		filedelete=os.path.join(filepath, "testimage.png")
		filestoragemod.deletefile(filedelete)		
		shottaken=photomod.saveshot(filepath,video,False,resolution,positionvalue,vdirection)       
	else:
		filepath=os.path.join(get_path(), "static")
		filepath=os.path.join(filepath, "hydropicture")
		shottaken=photomod.saveshot(filepath,video,True,resolution,positionvalue,vdirection)			
	if shottaken:
		ret_data = {"answer": "photo taken"}
	else:
		ret_data = {"answer": "Camera not detected"}	
	print "The photo ", ret_data
	return shottaken , ret_data


			
def takephoto(Activateanyway=False):
	isok=False
	count=0
	print "take photo", " " , datetime.now()
	videolist=videodevlist()
	for video in videolist:
		isok=False
		if cameradbmod.isCameraActive(video)or(Activateanyway):
			videolist=[video]
			camdata=cameradbmod.getcameradata(videolist)# if not found return default parameters
			resolution=camdata[0]["resolution"] 
			position=camdata[0]["position"]
			servo=camdata[0]["servo"]
			vdirection=camdata[0]["vflip"]
			print "Camera: ", video , " Resolution ", resolution , " Position " , position , " Vertical direction " , vdirection 
			logger.info("Camera: %s Resolution %s Position %s Vertical direction %s " , video , resolution , position , vdirection)
			positionlist=position.split(",")
			if (positionlist)and(servo!="none"):
				for positionvalue in positionlist:
				# move servo
					servoangle(servo,positionvalue,2)
					isok , ret_data=shotit(video,False,resolution,positionvalue,vdirection)

			else:
				isok , ret_data=shotit(video,False,resolution,"0",vdirection)			

			logger.info(ret_data["answer"])
		else:
			logger.info("Camera: %s not activated " , video)
			
		if isok:
			count = count +1
	if count > 0:
		isok=True
	return isok	

		

def resetandbackuplog_bak():
	#setup log file ---------------------------------------
	mainpath=get_path()
	filename=LOGFILENAME
	try:
		#os.rename(os.path.join(mainpath,filename), os.path.join(mainpath,filename+".txt"))
		shutil.copyfile(os.path.join(mainpath,filename), os.path.join(mainpath,filename+".txt"))

	except:
		print "No log file"

	logger.FileHandler(filename=os.path.join(mainpath,filename), mode='w')	
	#logger.basicConfig(filename=os.path.join(mainpath,filename),level=logger.INFO)
	#logger.basicConfig(format='%(asctime)s %(message)s')
	#logger.basicConfig(format='%(levelname)s %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
	
	# set up logging to file - see previous section for more details
	logger.basicConfig(level=logging.INFO,
						format='%(asctime)-2s %(levelname)-8s %(message)s',
						datefmt='%H:%M:%S',
						filename=os.path.join(mainpath,filename))


def get_path():
    '''Get the path to this script no matter how it's run.'''
    #Determine if the application is a py/pyw or a frozen exe.
    if hasattr(sys, 'frozen'):
        # If run from exe
        dir_path = os.path.dirname(sys.executable)
    elif '__file__' in locals():
        # If run from py
        dir_path = os.path.dirname(__file__)
    else:
        # If run from command line
        dir_path = sys.path[0]
    return dir_path
	


def get_image_size(picturepath):
	filepath=os.path.join(get_path(), "static")
	fname=os.path.join(filepath, picturepath)
	'''Determine the image type of fhandle and return its size.
	from draco'''
	with open(fname, 'rb') as fhandle:
		head = fhandle.read(24)
		if len(head) != 24:
			return 0,0
		if imghdr.what(fname) == 'png':
			check = struct.unpack('>i', head[4:8])[0]
			if check != 0x0d0a1a0a:
				return 0,0
			width, height = struct.unpack('>ii', head[16:24])
		elif imghdr.what(fname) == 'gif':
			width, height = struct.unpack('<HH', head[6:10])
		elif imghdr.what(fname) == 'jpeg':
			try:
				fhandle.seek(0) # Read 0xff next
				size = 2
				ftype = 0
				while not 0xc0 <= ftype <= 0xcf:
					fhandle.seek(size, 1)
					byte = fhandle.read(1)
					while ord(byte) == 0xff:
						byte = fhandle.read(1)
					ftype = ord(byte)
					size = struct.unpack('>H', fhandle.read(2))[0] - 2
				# We are at a SOFn block
				fhandle.seek(1, 1)  # Skip `precision' byte.
				height, width = struct.unpack('>HH', fhandle.read(4))
			except Exception: #IGNORE:W0703
				return 0,0
		else:
			return 0,0
		return width, height
		
def additionalRowInit():
	#initialize IOdatarow	
	global IOdatarow	
	fields=HWdataKEYWORDS
	tablehead=[]
	for key, value in fields.iteritems():
		tablehead.append(key)
	IOdatarow={}
	for th in tablehead:
		if len(fields[th])>1:
			IOdatarow[th]=fields[th][0]
		else:
			IOdatarow[th]=""
	return True

def addrow(dictrow, temp=True):
	dicttemp=copy.deepcopy(dictrow)
	global IOdata
	global IOdatatemp
	if temp:
		IOdatatemp.append(dicttemp)
		return True
	else:
		IOdata.append(dicttemp)
		filestoragemod.savefiledata(HWDATAFILENAME,IOdata)
		return True
	
def deleterow(element, temp=True):
	global IOdata
	global IOdatatemp
	searchfield=HW_INFO_NAME
	searchvalue=element
	if temp:
		for line in IOdatatemp:
			if searchfield in line:
				if line[searchfield]==searchvalue:
					IOdatatemp.remove(line)
					return True
		return False
	else:	
		for line in IOdata:
			if searchfield in line:
				if line[searchfield]==searchvalue:
					IOdata.remove(line)
					filestoragemod.savefiledata(HWDATAFILENAME,IOdata)
					return True
		return False



def blink(PINstr, wait, numtimes):
	HWcontrol.GPIO_setup(PINstr, "out")
	for i in range(0,numtimes):
		level=1
		HWcontrol.GPIO_output(PINstr, level)
		time.sleep(wait)
		level=0
		HWcontrol.GPIO_output(PINstr, level)	
		time.sleep(wait)
	




	
if __name__ == '__main__':
	# comment
	a=10
	
