# Alma related variables and Python functions
# Loads almaconfig.yaml and makes its variables available to our Python scripts 
#
# TME  10/12/18  Initial version
# TME  03/20/19  Adding NCIP variable and start http session functions
# TME  04/25/19  Try/excepts used when set config parameters
#                Added is_maintenance_window()
# TME  05/10/19  Added almaDropboxRoot
# TME  10/31/19  Added almaDropboxRoot and hdServer
# TME  03/12/20  Added apiKeyUserRequest
# TME  03/23/20  Addded userPdsApi and pwPdsApi
# TME  04/06/20  Added is_reqular_work_hours()
# TME  11/23/20  Added webhookDir
# TME  02/17/21  Updated to support the new PDS API
# TME  04/29/21  Added urlBarcodeApi
# TME  05/05/21  Added almaHdExportDir
# TME  09/15/21  Added lrwConnectStr
# TME  02/14/22  Added read_queue_file(), add_to_queue_file() and write_queue_file()
# TME  07/19/22  Added is_week_day() and a is_regular_work_hours()
#                that's spelled properly and uses is_week_day()
# TME  09/13/22  Using SafeLoader with yaml module
# TME  09/16/22  Added urlJobsApi
# TME  09/23/22  Added urlHoldingsApi
# TME  10/23/23  Get variables for mail.yaml config file. Removed shbang.
#                Removed is_reqular_work_hours (but kept is_regular_work_hours)
             
#
# Load modules, set/initialize global variables
#
import os, yaml
import calendar
from time import sleep
from pathlib import Path
from datetime import datetime

# To help find other directories that might hold modules or config files 
scriptLib  = os.path.dirname(os.path.realpath(__file__))
scriptHome = scriptLib.replace('lib', 'conf')

# Load top level script configuration file
scriptConf = os.path.join(scriptHome, 'main.yaml')

try:
	with open(scriptConf, 'r') as ymlfile:
		config = yaml.load(ymlfile, Loader=yaml.SafeLoader)
except:
	print('Error: failed to open %s' % scriptConf)
	quit()

try:
	urlAlmaApi      = config['urlAlmaApi']
	urlPatronApi    = urlAlmaApi + 'users'
	urlAnalyticsApi = urlAlmaApi + 'analytics/reports/'
	urlBibsApi      = urlAlmaApi + 'bibs/'
	urlBarcodeApi   = urlAlmaApi + 'items?item_barcode='
	urlJobsApi      = urlAlmaApi + 'conf/jobs/{job_id}?op=run'
	urlHoldingsApi  = urlAlmaApi + 'bibs/{mmsId}/holdings/{holdingsId}'
except:
	print('Error: failed to load config parameter urlAlmaApi from %s' % scriptConf)
try:
	urlNcip = config['urlNcip']
except:
	print('Error: failed to load config parameter urlNcip from %s' % scriptConf)
try:
	apiKeyPatron = config['apiKeyPatron']
except:
	print('Error: failed to load config parameter apiKeyPatron from %s' % scriptConf)
try:
	apiKeyBibsRw = config['apiKeyBibsRw']
except:
	print('Error: failed to load config parameter apiKeyBibsRw from %s' % scriptConf)
try:
	apiKeyAcquisitions = config['apiKeyAcquisitions']
except:
	print('Error: failed to load config parameter apiKeyAcquisitions from %s' % scriptConf)
try:
	apiKeyAnalytics = config['apiKeyAnalytics']
except:
	print('Error: failed to load config parameter apiKeyAnalytics from %s' % scriptConf)
try:
	urlPdsApi = config['urlPdsApi']
except:
	print('Error: failed to load config parameter urlPdsApi from %s' % scriptConf)
try:
	apiKeyPds = config['apiKeyPds']
except:
	print('Error: failed to load config parameter apiKeyPds from %s' % scriptConf)
try:
	gpgLtsPassPhrase = config['gpgLtsPassPhrase']	
except:
	print('Error: failed to load config parameter gpgLtsPassPhrase from %s' % scriptConf)
try:
	almaDropboxRoot = config['almaDropboxRoot']	
except:
	print('Error: failed to load config parameter almaDropboxRoot from %s' % scriptConf)
try:
	almaOutputRoot  = config['almaOutputRoot']
	almaHdExportDir = f'{almaOutputRoot}/HDEP'
except:
	print('Error: failed to load config parameter almaOutputRoot from %s' % scriptConf)
try:
	hdServer = config['hdServer']	
except:
	print('Error: failed to load config parameter hdServer from %s' % scriptConf)
try:
	apiKeyUserRequest = config['apiKeyUserRequest']	
except:
	print('Error: failed to load config parameter apiKeyUserRequest from %s' % scriptConf)
try:
	webhookDir = config['webhookDir']	
except:
	print('Error: failed to load config parameter webhookDir from %s' % scriptConf)
try:
	lrwHost       = config['lrwHost']
	lrwPort       = config['lrwPort']
	lrwSchema     = config['lrwSchema']
	lrwConnectStr = f"{config['lrwRoUser']}/{config['lrwRoPasswd']}@{lrwHost}:{lrwPort}/{lrwSchema}"
	lrwRoConnectStr = f"{config['lrwRoUser']}/{config['lrwRoPasswd']}@{lrwHost}:{lrwPort}/{lrwSchema}"
	lrwRwConnectStr = f"{config['lrwRwUser']}/{config['lrwRwPasswd']}@{lrwHost}:{lrwPort}/{lrwSchema}"
except:
	print('Error: failed to set lrwConnectStr from %s' % scriptConf)

#
# Functions
#

# Return True if current day is a weekday, otherwise, return False
def is_week_day():
	
	returnStatus   = False
	currentDayTime = datetime.now()
	dayOfTheWeek   = calendar.day_name[currentDayTime.weekday()]
	
	if dayOfTheWeek in ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'):
		returnStatus = True
		
	return returnStatus

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

# Return True if current day and time falls within regular
# working hours (Monday-Friday 9-5), otherwise, return False
def is_regular_work_hours():
	returnStatus   = False
	
	if is_week_day():
		currentDayTime = datetime.now()
		
		if currentDayTime.hour >= 9 and currentDayTime.hour < 17:
			returnStatus = True
		
	return returnStatus

# Read the queue file and return the list of file names it contains
# Parameters:
#	queueFile	Full path name for the queue file.
#
#	notifyJM	Optionally pass a notifyJM object to the routine 
#               which can be used log messages
#
# Returns:	A list if file names on success, otherwise False
#
def read_queue_file(queueFile, notifyJM = False):
	inputFiles = []
	message    = False
	
	# Don't access file if it's in use
	lockFile   = queueFile.replace('.txt', '.LOCK')
	fileLocked = is_file_locked(lockFile)
			
	if not fileLocked:
		if os.path.isfile(queueFile):
			lockFlag = Path(lockFile)
			lockFlag.touch()

			with open(queueFile) as input:
				for line in input:
					inputFiles.append(line.rstrip())
			
			os.remove(lockFlag)
		
		else:
			message = f'{queueFile} not found'
	else:
		inputFiles = False
		message    = f'{queueFile} is locked'
		
		if notifyJM:
			notifyJM.log('fail', message, True)
		else:
			print(message)

	if message:
		if notifyJM:
			notifyJM.log('info', message, True)
		else:
			print(message)
	
	return inputFiles

# Write out queue file
# Parameters:
#	inputFiles	A list containing the names of the files to be process.
#               Paths to file should not be included, just the file's name.
#
#	queueFile	Full path name for the queue file.
#
# Returns:	True on success, otherwise False
#
def write_queue_file(inputFiles, queueFile, notifyJM = False):
	status = True
	
	# Don't access file if it's in use
	lockFile   = queueFile.replace('.txt', '.LOCK')
	fileLocked = is_file_locked(lockFile)
			
	if not fileLocked:
		lockFlag = Path(lockFile)
		lockFlag.touch()

		with open(queueFile, 'w') as output:
			for inputFile in inputFiles:
				output.write(f'{inputFile}\n')

		os.remove(lockFlag)

	else:
		status  = False
		message = f'{queueFile} is locked'

		if notifyJM:
			notifyJM.log('fail', message, True)
		else:
			print(message)

	return status

# Add to queue file
# Parameters:
#	inputFiles	A list of file names to added to the queue file.
#               Paths to file should not be included, just the file's name.
#               File will be created if necessary.
#
#	queueFile	Full path name for the queue file.
#
# Returns:	True on success, otherwise False
#
def add_to_queue_file(inputFiles, queueFile, notifyJM = False):
	status = True
	
	# Don't access file if it's in use
	lockFile   = queueFile.replace('.txt', '.LOCK')
	fileLocked = is_file_locked(lockFile)
			
	if not fileLocked:
		lockFlag = Path(lockFile)
		lockFlag.touch()

		with open(queueFile, 'a+') as output:
			for inputFile in inputFiles:
				output.write(f'{inputFile}\n')

		os.remove(lockFlag)

	else:
		status  = False
		message = f'{queueFile} is locked'

		if notifyJM:
			notifyJM.log('fail', message, True)
		else:
			print(message)

	return status

# Check for file lock. Will wait for 10 seconds for lock file removal.
#
# Parameters:
#	lockFile	Full path name for the lock file
#
# Returns:	True if lock file is found, otherwise False
#
def is_file_locked(lockFile):
	for seconds in range(1, 5):
		if os.path.isfile(lockFile):
			status = True
			sleep(seconds)
		else:
			status = False
			break

	return status
