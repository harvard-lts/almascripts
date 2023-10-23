# Common LTS script routines and variables 
#
# TME  06/22/18  Initial version
# TME  12/07/18  Added send_mail_attachment()
# TME  07/09/19  Using SafeLoader with yaml module
# TME  09/12/19  Added get_date_time_stamp()
# TME  10/31/19  Added privateKey and try/excepts
# TME  01/24/20  Added support for the gpg parameters
# TME  03/27/20  Added monthly precision get_date_time_stamp
# TME  04/07/21  Added oracleHome
# TME  08/12/21  Added support for Footprints API
# TME  08/23/21  Remove make_fp_ticket() since it used hulmail.
#                Added get_mail_list()
# TME  06/30/22  Now using mailhub.harvard.edu as mail host
# TME  10/05/22  Removed variables used with Footprints
# TME  10/13/22  Added year precision to get_date_time_stamp()
# TME  12/13/22  Added is_holiday()
# TME  12/14/22  Added is_winter_break()
# TME  01/25/23  Added unpack_file()
# TME  03/02/23  Added zip_files() and usage message for unpack_file
# TME  03/13/23  send_mail_attachment() now accepts a replyTo optional parameter  
# TME  05/12/23  Added is_maintenance_window()
# TME  09/15/23  Added is_week_day()
# TME  10/23/23  Get variables for mail.yaml config file. 
#                Removed ltsScripts and notify. Removed shbang.

#
# Load modules, set/initialize global variables
#
import calendar, os, subprocess, sys, yaml
from datetime import datetime
from glob import glob

# To help find other directories that might hold modules or config files 
libDir      = os.path.dirname(os.path.realpath(__file__))
confDir     = libDir.replace('lib', 'conf')
mailListDir = libDir.replace('lib', 'mail_lists')
sys.path.append(confDir)

# Load top level script configuration file
scriptConf = os.path.join(confDir, 'main.yaml')

with open(scriptConf, 'r') as ymlfile:
    config = yaml.load(ymlfile, Loader=yaml.SafeLoader)

try:
	mode = config['mode']
except:
	print('Error: failed to load config parameter mode from %s' % scriptConf)
try:
	privateKey = config['privateKey']
except:
	print('Error: failed to load config parameter privateKey from %s' % scriptConf)
try:
	jobMonitor = config['jobMonitor']
except:
	print('Error: failed to load config parameter jobMonitor from %s' % scriptConf)
try:
	adminMailTo = config['adminMailTo']
except:
	print('Error: failed to load config parameter adminMailTo from %s' % scriptConf)
try:
	adminMailFrom = config['adminMailTo']
except:
	print('Error: failed to load config parameter adminMailFrom from %s' % scriptConf)
try:
	oracleHome = config['oracleHome']
except:
	print('Error: failed to load config parameter oracleHome from %s' % scriptConf)
try:
	gpgDir = config['gpgDir']
	gpgCmd = config['gpgCmd']
except:
	print('Gpg parameters are not set')
		
#
# Functions
#

# get_date_time_stamp
#
# Parameters
#   precision   Choices are year, month, day, hour, minute or second.
#               Defaults to minute.
#
# Returns
#   A date time stamp string
#
def get_date_time_stamp(precision = 'minute'):
	from time import time

	if precision == 'minute':
		dateTimeStamp = datetime.fromtimestamp(int(time())).strftime("%Y%m%d%H%M")
	elif precision == 'second':
		dateTimeStamp = datetime.fromtimestamp(int(time())).strftime("%Y%m%d%H%M%S")
	elif precision == 'hour':
		dateTimeStamp = datetime.fromtimestamp(int(time())).strftime("%Y%m%d%H")
	elif precision == 'day':
		dateTimeStamp = datetime.fromtimestamp(int(time())).strftime("%Y%m%d")
	elif precision == 'month':
		dateTimeStamp = datetime.fromtimestamp(int(time())).strftime("%Y%m")
	elif precision == 'year':
		dateTimeStamp = datetime.fromtimestamp(int(time())).strftime("%Y")
	else:
		dateTimeStamp = None

	return dateTimeStamp

# get_mail_list
#
# Parameters
#   mailList	Mailing list to fetch
#	returnType	Choices are; "string" to return email addresses as a string
#				separated by commas or "list" to get them as a Python list.
#
# Returns
#   A mailing list upon success, otherwise, False.
#
def get_mail_list(mailList, returnType):
	import re
	
	if re.match('.*\.txt', mailList):
		mailListFile = f'{mailListDir}/{mailList}'
	else:
		mailListFile = f'{mailListDir}/{mailList}.txt'
	
	# Read file into a list without newlines
	with open(mailListFile) as input:
		addresses = input.read().splitlines()
			
	if returnType == 'string':
		addresses = ','.join(addresses)
	elif returnType == 'list':
		pass
	else:
		print(f'returnType of {returnType} is not supported')
		return False
			
	return addresses

# is_holiday
# Returns True if datestamp falls on a Harvard holiday,
# otherwise, returns False
#
# Optional parameters
#   notifyJM     A notify object used to log messages for the Job Monitor
#   datestamp    Datestamp to check in the form of YYYYMMDD
#
def is_holiday(notifyJM = False, datestamp = False):
	from holidays import holidays, updatedTil

	if not datestamp:
		datestamp = get_date_time_stamp('day')

	# Notify is the holidays lookup table is out of date
	if datestamp > updatedTil:
		message = 'The holidays configuration tables needs to be updated'
		if notifyJM:
			notifyJM.log('fail', message, True)
		else:
			print(message)
						
	if datestamp in holidays:
		return True
	else:
		return False

# Routine maintenance is scheduled on Tues/Thurs 5-7am and Sunday 1-9am
# Return True if current day and time falls in a maintenance window
# Otherwise, return False
def is_maintenance_window():
	
	returnStatus   = False
	currentDayTime = datetime.now()
	dayOfTheWeek   = calendar.day_name[currentDayTime.weekday()]
	
	if dayOfTheWeek in ('Tuesday', 'Thursday'):
		if currentDayTime.hour >= 5 and currentDayTime.hour < 7:
			returnStatus = True
		
	elif dayOfTheWeek == 'Sunday':
		if currentDayTime.hour >= 1 and currentDayTime.hour < 9:
			returnStatus = True

	return returnStatus

# Return True if current day is a weekday, otherwise, return False
def is_week_day():
	
	returnStatus   = False
	currentDayTime = datetime.now()
	dayOfTheWeek   = calendar.day_name[currentDayTime.weekday()]
	
	if dayOfTheWeek in ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'):
		returnStatus = True
		
	return returnStatus

# is_winter_break
# Returns True if datestamp falls with in our winter break,
#  otherwise, returns False
#
# Optional parameters
#   notifyJM     A notify object used to log messages for the Job Monitor
#   datestamp    Datestamp to check in the form of YYYYMMDD
#
def is_winter_break(notifyJM = False, datestamp = False):
	from holidays import winterBreak, updatedTil

	if not datestamp:
		datestamp = get_date_time_stamp('day')

	# Notify is the holidays lookup table is out of date
	if datestamp > updatedTil:
		message = 'The holidays configuration tables needs to be updated'
		if notifyJM:
			notifyJM.log('fail', message, True)
		else:
			print(message)
						
	if datestamp in winterBreak:
		return True
	else:
		return False

# send_mail
#
# Parameters
#   mailTo       Email address to send message to
#   mailFrom     Email address to use as the 'From'
#   subject      Message to appear in subject line
#   message      Optional, the subject we be used in the
#                body of the email if message is not set
#
def send_mail(mailTo, mailFrom, subject, message = False):
    import smtplib, re
    from email.mime.text import MIMEText

    # Create a text/plain message
    if message:
	    msgEmail = MIMEText(message)
    else:
	    msgEmail = MIMEText(subject)
    
    msgEmail['Subject'] = subject
    msgEmail['From']    = mailFrom
    msgEmail['To']      = mailTo
        
    # Convert scalar to array if more than 1 address is used
    matched = re.match('.+,.+', mailTo)
    if matched != None:
        mailTo = mailTo.split(',')
        
    smtp = smtplib.SMTP('mailhub.harvard.edu')
    smtp.sendmail(mailFrom, mailTo, msgEmail.as_string())
    smtp.quit()            

    return True

# send_mail_attachment
# Send email with attachments
#
# Parameters
#   mailTo       Email address(es) to send message to.
#   mailFrom     Email address to use as the 'From'
#   subject      Message to appear in subject line
#   message      Optional, the subject we be used in the
#                body of the email if message is not set
#
def send_mail_attachment(mailTo, mailFrom, subject, message, files = None, replyTo = False):
	import smtplib, re
	from os.path import basename
	from email.mime.application import MIMEApplication
	from email.mime.multipart import MIMEMultipart
	from email.mime.text import MIMEText
	from email.utils import COMMASPACE, formatdate

	msgEmail = MIMEMultipart()
	msgEmail['From']    = mailFrom
	msgEmail['To']      = mailTo
	msgEmail['Date']    = formatdate(localtime=True)
	msgEmail['Subject'] = subject
	if replyTo:
	    msgEmail['Reply-to'] = replyTo

	# Convert scalar to array if more than 1 address is used
	matched = re.match('.+,.+', mailTo)
	if matched != None:
		mailTo = mailTo.split(',')
        
	# files needs to be converted to a list regardless
	matched = re.match('.+,.+', files)
	if matched == None:
		files = [files]
	else:
		files = files.split(',')
        
	msgEmail.attach(MIMEText(message))
	
	# Attach any files (or not)
	for file in files or []:
		with open(file, "rb") as attachment:
			part = MIMEApplication(
				attachment.read(),
				Name=basename(file)
			)
	
		# After the file is closed
		part['Content-Disposition'] = 'attachment; filename="%s"' % basename(file)
		msgEmail.attach(part)

	smtp = smtplib.SMTP('mailhub.harvard.edu')
	smtp.sendmail(mailFrom, mailTo, msgEmail.as_string())
	smtp.close()

# unpack_file
# Untar and gunzip specified file
#
# Parameters
#   file        Name of file to unpack.
#   notifyJM    A notify object pass in to use for reporting.
#   verbose     Optional. Set to True for verbose output.
#
def unpack_file(file, notifyJM, verbose = False):
	import gzip, re, shutil, tarfile
	zippedFile = False
	tarredFile = False
	
	# Ungzip if needed
	match = re.match('.+\.gz$', file)
	if match:
		unzippedFile = file.replace('.gz', '')
		if not os.path.isfile(unzippedFile):
			notifyJM.log('info', f'Gunzipping {file}', verbose)				
			try:
				with gzip.open(file, 'rb') as fileIn:
					with open(unzippedFile, 'wb') as fileOut:
						shutil.copyfileobj(fileIn, fileOut)
			except:
				notifyJM.log('fail', "Gunzip %s failed" % file, verbose)
				notifyJM.report('stopped')
				quit()
			
		zippedFile = file
		file       = unzippedFile

	# Extract tar archive if needed
	match = re.match('.+\.tar$', file)
	if match:
		untarredFile = file.replace('.tar', '')
		if not os.path.isfile(untarredFile):
			notifyJM.log('info', f'Untarring {file}', verbose)				
			try:
				tar = tarfile.open(file)
				tar.extractall()
				tar.close()
			except:
				notifyJM.log('fail', "Tar extract of %s failed" % file, verbose)
				notifyJM.report('stopped')
				quit()

		tarredFile = file
		file       = untarredFile				
	
	# Remove packed file if needed
	if zippedFile: os.remove(zippedFile)
	if tarredFile: os.remove(tarredFile)
	
	return file

# zip_files
# Zip up all files and send via email
#
# Parameters
#   archiveFile    Name of the zip archive file to create.
#   fileGlob       Glob or wildcat pattern used to find files to archive.
#   notifyJM       A notify object pass in to use for reporting.
#   verbose        Optional. Set to True for verbose output.
#
def zip_files(archiveFile, fileGlob, notifyJM, verbose = False):

	cmdNargs = ['zip', archiveFile]
	for file in glob(fileGlob):
		cmdNargs.append(file)

	try:
		subprocess.run(cmdNargs)
		
	except Exception as e:
		notifyJM.log('fail', 'Zipping up reports failed. Error was: %s' % e, True)
		return False
		
	if os.path.exists(archiveFile) and os.path.getsize(archiveFile) > 0:
		notifyJM.log('info', f'{archiveFile} was created', verbose)
	else:
		notifyJM.log('fail', 'Zipping up reports failed', True)
		return False
		
	return True
