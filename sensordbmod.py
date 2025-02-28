# -*- coding: utf-8 -*-
"""
utility for the planning database
"""

import logging
import string
from datetime import datetime,date,timedelta
import databasemod
import random
import hardwaremod



# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////

global DBFILENAME
DBFILENAME = 'Sensordb.db'
global TIMEFIELD
global DATAFIELD
TIMEFIELD='readtime'
DATAFIELD='data1'
global SENSORQUERYINTERVALMINUTES
SENSORQUERYINTERVALMINUTES=15


# ///////////////// --- END GLOBAL VARIABLES ------


# ///////////////// -- MODULE INIZIALIZATION --- //////////////////////////////////////////
print "SensordDBmod inizialization"
databasemod.init_db(DBFILENAME)
tablelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE,"input",hardwaremod.HW_INFO_NAME)
databasemod.aligndbtable(DBFILENAME, tablelist)

# ///////////////// --- END init


#-- start DB utility--------////////////////////////////////////////////////////////////////////////////////////	


def init_db():
	databasemod.init_db(DBFILENAME)	

def gettablelist():
	tablelist=hardwaremod.searchdatalist(hardwaremod.HW_INFO_IOTYPE,"input",hardwaremod.HW_INFO_NAME)
	return tablelist

def gettablenameapprox(stringtofind):
	valuelist=[]
	outlist=[]
	hardwaremod.getfieldinstringvalue(hardwaremod.HW_INFO_NAME,stringtofind,valuelist)
	tablelist=gettablelist()	
	for value in valuelist:
		if 	value in tablelist:
			outlist.append(value)
	return outlist




def columninfo():
	databasemod.columninfo(DBFILENAME,DBTABLE)
			
	
def insertdataintable(table,datavalue):
	rowfield=[]
	rowfield.append(TIMEFIELD)
	rowfield.append(DATAFIELD)	
	rowvalue=[]
	rowvalue.append(datetime.now().replace(microsecond=0))
	rowvalue.append(datavalue)
	databasemod.insertrowfields(DBFILENAME,table,rowfield,rowvalue)


def rowdescription(deletefirstN):
	return databasemod.rowdescription(DBFILENAME,DBTABLE,deletefirstN)

		
def getvaluelist(field,valuelist):
	databasemod.getvaluelist(DBFILENAME,DBTABLE,field,valuelist)

def getdatafromfields(fieldlist,valuelist):
	databasemod.getdatafromfields(DBFILENAME,DBTABLE,fieldlist,valuelist)
		
def deleterowwithfield(tablename,field,value):
	databasemod.deleterowwithfield(DBFILENAME,tablename,field,value)

def deleteallrow():
	tablelist=gettablelist()
	for tablename in tablelist :
		databasemod.deleteallrow(DBFILENAME,tablename)
	
def insertrowfields(rowfield,rowvalue):
	databasemod.insertrowfields(DBFILENAME,DBTABLE,rowfield,rowvalue)

def gettable(searchfield,searchvalue):
	return databasemod.gettable(DBFILENAME,DBTABLE,searchfield,searchvalue)


#--end --------////////////////////////////////////////////////////////////////////////////////////		

#-- start Plan table utility--------////////////////////////////////////////////////////////////////////////////////////	


		
def getsensordbdata(selsensor,sensordata):
	fieldlist=[]
	fieldlist.append(TIMEFIELD)
	fieldlist.append(DATAFIELD)
	databasemod.getdatafromfields(DBFILENAME,selsensor,fieldlist,sensordata)

def getsensordbdatadays(selsensor,sensordata,days):
	fieldlist=[]
	fieldlist.append(TIMEFIELD)
	fieldlist.append(DATAFIELD)
	sampletime=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,selsensor,hardwaremod.HW_FUNC_TIME)
	if sampletime!="":
		samplingintervalminutes=int(sampletime.split(":")[1])
		if samplingintervalminutes>=1:
			samplesnumber=(days*24*60)/samplingintervalminutes
			databasemod.getdatafromfieldslimit(DBFILENAME,selsensor,fieldlist,sensordata,samplesnumber)
		else:
			databasemod.getdatafromfields(DBFILENAME,selsensor,fieldlist,sensordata)		
	else:
		databasemod.getdatafromfields(DBFILENAME,selsensor,fieldlist,sensordata)

def getsensordbdatasamplesN(selsensor,sensordata,samplesnumber):
	fieldlist=[]
	fieldlist.append(TIMEFIELD)
	fieldlist.append(DATAFIELD)
	databasemod.getdatafromfieldslimit(DBFILENAME,selsensor,fieldlist,sensordata,samplesnumber)

def readallsensorsdatabase():
	#sensorlist=searchdatalist(HW_INFO_IOTYPE,"input",HW_INFO_NAME)
	sensorlist=gettablelist()
	sensorvalues={}
	sensortimestamp={}
	for sensorname in sensorlist:
		#sensorvalues[sensorname]=getsensordata(sensorname,3)
		databasevalues=[]
		samplesnumber=1
		getsensordbdatasamplesN(sensorname,databasevalues,samplesnumber)
		for value in databasevalues:
			sensorvalues[sensorname]=value[1]
			sensortimestamp[sensorname]=value[0]
	return sensorvalues
	
def getSensorDataPeriod(selsensor,sensordata,enddate,pastdays):
	num = int(pastdays)
	tdelta=timedelta(days=num)
	startdate=enddate-tdelta
	#print " stratdate " ,startdate
	#print " enddate ", enddate
	allsensordata=[]
	#getsensordbdata(selsensor,allsensordata)
	getsensordbdatadays(selsensor,allsensordata,num)
	del sensordata[:]
	for rowdata in allsensordata:
		try:
			dateref=datetime.strptime(rowdata[0].split(".")[0],'%Y-%m-%d %H:%M:%S')
			if (dateref>=startdate)and(dateref<=enddate):
				value=float(rowdata[1])
				templist=[rowdata[0], value]
				sensordata.append(templist)
		except ValueError:
			print "Error in database reading ",rowdata
	# sensor data --------------------------------------------

def getSensorDataPeriodXminutes(selsensor,datax,datay,startdate,enddate): # return sensordata in form of a matrix Nx2
	# x value is in minutes, y value is float. Shifted to have average Zero
	allsensordata=[]
	getsensordbdata(selsensor,allsensordata)
	del datax[:]	
	del datay[:]
	lenght=0
	for rowdata in allsensordata:
		try:
			dateref=datetime.strptime(rowdata[0].split(".")[0],'%Y-%m-%d %H:%M:%S')
			if (dateref>=startdate)and(dateref<=enddate):
				valuex=timediffinminutes(startdate, dateref)
				valuey=float(rowdata[1])
				datax.append(valuex)
				datay.append(valuey)
				lenght=lenght+1				
		except ValueError:
			print "Error in database reading ",rowdata

	return lenght

def timediffinminutes(data2, data1):
	diff =  data1 - data2
	return abs(diff.days*1440 + diff.seconds/60)


def timediffdays(data2, data1):
	diff =  data1 - data2
	return abs(diff.days)


def getAllSensorsDataPeriodv2(enddate,pastdays):
	usedsensorlist=[]
	num = int(pastdays)
	tdelta=timedelta(days=num)
	startdate=enddate-tdelta
	print "sensordbmod "
	print " stratdate " ,startdate
	print " enddate ", enddate
	outputallsensordata=[]
	sensorlist=gettablelist()
	mintime=(enddate - datetime(1970,1,1)).total_seconds()
	maxtime=0
	for selsensor in sensorlist:
		allsensordata=[]
		#getsensordbdata(selsensor,allsensordata)
		#print " reading sensor database " , selsensor
		getsensordbdatadays(selsensor,allsensordata,num+(datetime.now()-enddate).days+1)
		#print " reading sensor database DONE!"		
		sensordata=[]
		# fetch raw data from database
		for rowdata in allsensordata:
			try:
				dateref=datetime.strptime(rowdata[0].split(".")[0],'%Y-%m-%d %H:%M:%S')
				if (dateref>=startdate)and(dateref<=enddate):
					value=float(rowdata[1])
					dateinsecepoch=(dateref - datetime(1970,1,1)).total_seconds()
					templist=[rowdata[0], value]
					sensordata.append(templist)
					if mintime>dateinsecepoch:
						mintime=dateinsecepoch
					if maxtime<dateinsecepoch:
						maxtime=dateinsecepoch					
			except:
				print "Error in database reading ",rowdata
		if len(sensordata)>0:
			outputallsensordata.append(sensordata)
			usedsensorlist.append(selsensor)

	print 
	return outputallsensordata,usedsensorlist,mintime,maxtime
	# sensor data --------------------------------------------




def RemoveSensorDataPeriod(removebeforedays, maxremovepersensor=300):
	sensordata=[]
	field=TIMEFIELD
	startdate=datetime.now()
	num = removebeforedays
	tdelta=timedelta(days=num)
	enddate=startdate-tdelta
	pastdays=364
	
	sensorlist=gettablelist()
	for selsensor in sensorlist:
		getSensorDataPeriod(selsensor,sensordata,enddate,pastdays)
		#print "page ", selsensor
		#print sensordata
		itemnum=min(maxremovepersensor, len(sensordata))
		for i in range(itemnum):
			deleterowwithfield(selsensor,field,sensordata[i][0])
	# sensor data --------------------------------------------
	
	
def EvaluateDataPeriod(sensordata,startdate,enddate):
	# sensor data --------------------------------------------
	isok=False
	outputdata={}
	summa=0
	inde=0
	for data in sensordata:
		dateref=datetime.strptime(data[0],'%Y-%m-%d %H:%M:%S')
		if (dateref>=startdate)and(dateref<=enddate):
			try:
				number=float(data[1])
				if inde==0:
					mini=number
					maxi=number
				else:
					if mini>number:
						mini=number
					if maxi<number:
						maxi=number
				summa=summa+number
				inde=inde+1
			except ValueError:
				print "Evaluation : Error in database reading ",dateref , "  " ,data[1]
	
	
	if inde>0:
		average=summa/inde
		isok=True
	else:
		average=0
		mini=0
		maxi=0
		
	outputdata["sum"]=summa		
	outputdata["average"]=average
	outputdata["min"]=mini
	outputdata["max"]=maxi	
	return isok , outputdata
	
def SumProductDataPeriod(sensordata,startdate,enddate,timeinterval):
	# sensor data --------------------------------------------
	sum=0
	for data in sensordata:
		dateref=datetime.strptime(data[0],'%Y-%m-%d %H:%M:%S')
		if (dateref>=startdate)and(dateref<=enddate):
			try:
				sum=sum+float(data[1])*timeinterval
			except ValueError:
				print data[1]
	return sum

	
	
def insertrandomrecords(recordnumber):
	rowfield=databasemod.rowdescription(DBFILENAME,DBTABLE,1)
	for i in range(recordnumber):
		randomvalues=[]
		randomvalues.append(datetime.now().replace(microsecond=0))
		for j in range(len(rowfield)-1):
			randomvalues.append(random.randrange(1,101,1))
		# waste time
		for j in range(20000):
			a=1
		insertrowfields(rowfield,randomvalues)

#--end --------////////////////////////////////////////////////////////////////////////////////////	


def sensorsysinfomatrix():
	# first row includes headers
	matrix=[]
	row=[]
	row.append("Sensor Name")
	row.append("Measure")
	row.append("Unit")
	row.append("Average 24H")	
	row.append("Min 24H")	
	row.append("Max 24H")	
	matrix.append(row)
	
	namelist=gettablelist()
	for name in namelist:
		row=[]
		row.append(name)
		row.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASURE))
		row.append(hardwaremod.searchdata(hardwaremod.HW_INFO_NAME,name,hardwaremod.HW_INFO_MEASUREUNIT))

		sensordata=[]
		getsensordbdatadays(name,sensordata,1)
		#set date interval for average
		endtime=datetime.now()
		starttime= endtime - timedelta(days=1)
		isok, evaluateddata=EvaluateDataPeriod(sensordata,starttime,endtime)
		row.append(str('%.1f' % evaluateddata["average"]))
		row.append(str('%.1f' % evaluateddata["min"]))
		row.append(str('%.1f' % evaluateddata["max"]))
		matrix.append(row)
	
	return matrix



def consistencycheck():
	# this routine align the database table elements with the Hardware available elements "IOtype" labelled with usedfor "input"
	tablelist=gettablelist()
	databasemod.aligndbtable(DBFILENAME, tablelist)

			

if __name__ == '__main__':

	DBFILENAME='Sensordb.db'
	init_db()
	insertrandomrecords(5)
	sensordata=[]
	getsensordbdata("temp1",sensordata)
	getSensorDataPeriod("temp1",sensordata,datetime.now(),1)
	print "data: "
	print sensordata
	rowvalue=[]
	teperatura=10
	PHreading=10
	ECreading=10
	light=10
	rowvalue.append(datetime.now().replace(microsecond=0))
	rowvalue.append(teperatura)
	rowvalue.append(PHreading)
	rowvalue.append(ECreading)
	rowvalue.append(light)
	rowfield=[]
	rowfield.append("readtime")
	rowfield.append("temp1")
	rowfield.append("ph1")
	rowfield.append("ec1")
	rowfield.append("light1")
	insertrowfields(rowfield,rowvalue)


	




