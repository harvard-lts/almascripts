#!/usr/bin/env python3
#
# Run the script with it's -h option to see it's description
# and usage or scroll down at bit
#
# TME  04/04/18  Initial version
# TME  08/15/18  Unsupported files found are now just logs a warn
# TME  04/01/19  Don't log a warning for an unsupported file 
#                unless specified in the config file.
#                Write out status flags if specified in the config file.
# TME  04/23/19  Use Alma webhook ID in status file.
#                Remove headings from result messages.
#                Use try/except for global config parameters.
# TME  04/27/21  Report proper error when unable to copy file
#                to the incoming archive directory
# TME  09/14/22  Using SafeLoader with yaml module
# TME  07/13/23  Move duplicate files to dupe directory
# TME  10/23/23  Changed shbang to use /usr/bin/env

#
# Load modules, set/initialize global variables, grab arguments & check usage
#
import os, re, yaml, shutil, sys

# To help find other directories that might hold modules or config files
binDir = os.path.dirname(os.path.realpath(__file__))

# Find and load any of our modules that we need
commonLib = binDir.replace('bin', 'lib')
sys.path.append(commonLib)
from ltstools import get_date_time_stamp

# run_script
# Checked usage, run main script and then display result
# Used when the script is called from the command prompt
def run_script():
    import argparse
    
    jobName  = 'Get dropbox files'

    usageMsg  = """
    Move dropbox file(s) in place. Files are archived after they are moved.
    A configuration file, with the needed parameters, must be specified. See
    get_dropbox_files.yaml_template in the adjacent conf directory for an example.
    """
    
    # Check for any command line parameters
    parser = argparse.ArgumentParser(description=usageMsg)
    parser.add_argument("conf_file", help="Configuration file to use")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-p", "--profile", help="Run only the specified profile in configuration file. Otherwise, all are run.")
    group.add_argument("-c", "--checkconf", action='store_true', help="Check configuration file, no files are copied")
    args = parser.parse_args()

    # Required, config file
    confFile = args.conf_file

    if args.checkconf:
	    mode     = 'checkConf'
	    profiles = 'ALL'
    elif args.profile:
	    mode     = 'getFiles'
	    profiles = args.profile
    else:
	    mode     = 'getFiles'
	    profiles = 'ALL'

    # Call function and then catch and display results
    [msgPass, msgWarn, msgFail] = get_dropbox_files(confFile, mode, profiles)

# get_dropbox_files
# Move dropbox file(s) in place.
#
# Parameters: confFile    Configuration file to use
#             mode        getFiles or checkConf
#             profiles    The keyword 'ALL' or a single profile name
#
# Returns:    An array containing msgPass, msgWarn and msgFail 
#             containing successful, warning and failure messages
#
def get_dropbox_files(confFile, mode, profiles):

	# Open and load config file into an array of hashes
	if os.path.isfile(confFile):
		with open(confFile, 'r') as ymlfile:
			configSets = yaml.load(ymlfile, Loader=yaml.SafeLoader)
	else:
		return [False, False, 'Configuration file %s not found' % (confFile)]

	# Group messages by status type
	msgPass = "";
	msgWarn = "";
	msgFail = "";

	profileFound   = False
	gotDropboxFile = False
	statusFileDir  = False

	# Use if duplicate files are found
	dateStamp = get_date_time_stamp('day')

	# Loop through config sets, check/set parameters
	for configSet in configSets:
		badConfigSet = False

		# Get any global parameters and then move on
		if configSet['profile_name'] == 'GLOBAL':
			try:
				statusFileDir = configSet['status_file_directory']
			except:
				pass
			
			continue

		try:
			profileName = configSet['profile_name']
		except:
			profileName = False
		try:
			jobStatus = configSet['job_status']
		except:
			jobStatus = 'ENABLED'
		try:
			dropboxIncoming = configSet['dropbox_incoming']
		except:
			dropboxIncoming = False
		try:
			dropboxArchive = configSet['dropbox_archive']
		except:
			dropboxArchive = False
		try:
			sourceFilename = configSet['dropbox_filename']
		except:
			sourceFilename = False
		try:
			targetDirectory = configSet['local_directory']
		except:
			targetDirectory = False
		try:
			renameLocalFile = configSet['rename_local_file']
		except:
			renameLocalFile = False
		try:
			warnUnsupportedFile = configSet['warn_unsupported_file']
		except:
			warnUnsupportedFile = False
		try:
			createInvoice = configSet['edi_invoices']
		except:
			createInvoice = False
		try:
			almaWebhookId = configSet['alma_webhook_id']
		except:
			almaWebhookId = False

		# Skip disabled config sets
		if jobStatus == 'DISABLED': continue
	
		# Just get files for a single config profile
		if profileName:        
			if not profiles == 'ALL':
				if not profileName == profiles:
					continue
		else:
			msgFail += 'Configuration error: profile_name is not set in %s\n' % (confFile)
			badConfigSet = True
		
		if not dropboxIncoming:
			msgFail += 'Configuration error: dropbox_incoming is not set in %s for %s\n' % (confFile, profileName)
			badConfigSet = True
		if not dropboxArchive:
			msgFail += 'Configuration error: dropbox_archive is not set in %s for %s\n' % (confFile, profileName)
			badConfigSet = True
		if not sourceFilename:
			msgFail += 'Configuration error: dropbox_filename is not set in %s for %s\n' % (confFile, profileName)
			badConfigSet = True
		if not targetDirectory:
			msgFail += 'Configuration error: local_directory is not set in %s for %s\n' % (confFile, profileName)
			badConfigSet = True

		if badConfigSet: continue

		# Just check config file if specified, no files are copied
		if mode == 'checkConf':
			continue

		profileFound = True
	
		# Check that all the needed directories exist
		if not os.path.exists(dropboxIncoming):
			msgFail += 'Error: incoming directory %s not found\n' % (dropboxIncoming)
			continue
		if not os.path.exists(dropboxArchive):
			msgFail += 'Error: archive directory %s not found\n' % (dropboxArchive)
			continue
		if not os.path.exists(targetDirectory):
			msgFail += 'Error: destination directory %s not found\n' % (targetDirectory)
			continue

		# In case we need a directory for duplicate files
		# It's expect to be adjacent to the incoming directory.
		dupeDir = re.sub('/\w+/*$', '/dupe', dropboxIncoming, 1)

		# Check for incoming files
		reSourceFilename = re.compile(sourceFilename)
		for incomingFile in os.listdir(dropboxIncoming):
	
			# Only process unsupported files
			match = reSourceFilename.match(incomingFile)
			if match == None:

				# If specified, warn for unsupported files found
				if warnUnsupportedFile:
					msgWarn += '%s found in %s but does not match the file name regular expression of %s\n' % (incomingFile, dropboxIncoming, sourceFilename)

				continue

			incomingFileFullPath = os.path.join(dropboxIncoming, incomingFile)
		
			# Check for duplicate files
			if os.path.isfile(os.path.join(dropboxArchive, incomingFile)):

				# Duplicate file will be renamed
				dupeFile = f'{incomingFile}.{dateStamp}'
	
				# Move any found to duplicate directory if one exits
				if os.path.exists(dupeDir):
					try:
						shutil.copy(incomingFileFullPath, f'{dupeDir}/{dupeFile}')
					except:
						msgFail += f"Failed to copy {incomingFileFullPath} to {dupeDir}/{dupeFile}\n"
						continue
					try:
						os.remove(incomingFileFullPath)
					except:
						msgFail += f"Failed to remove {incomingFileFullPath}\n"
						continue

					msgFail += f'Found duplicate file {incomingFileFullPath} and moved and renamed it to {dupeDir}/{dupeFile}.\n'
					
				else:
					msgFail += f'Found duplicate file {incomingFile} in {dropboxIncoming} but no duplicate directory was found to move file to.\n'

				continue
		
			# Put incoming files in place and archive, renaming if specified
			if renameLocalFile:
				if renameLocalFile == 'LOWERCASE':
					targetFileFullPath = os.path.join(targetDirectory, incomingFile.lower())
				elif 'MATCH' in renameLocalFile:
					targetFileRenamed  = renameLocalFile.replace('MATCH', match.group(1))
					targetFileFullPath = os.path.join(targetDirectory, targetFileRenamed)
			else:
				targetFileFullPath = os.path.join(targetDirectory, incomingFile)

			try:
				shutil.copy(incomingFileFullPath, targetFileFullPath)
			except:
				msgFail += "Failed to copy %s to %s\n" % (incomingFileFullPath, targetFileFullPath)
				continue
			try:
				shutil.copy(incomingFileFullPath, dropboxArchive)
			except:
				msgFail += "Failed to copy %s to %s\n" % (incomingFileFullPath, dropboxArchive)
				continue
			try:
				os.remove(incomingFileFullPath)
			except:
				msgFail += "Failed to remove %s\n" % (incomingFileFullPath)
				continue

			gotDropboxFile = profileName
			msgPass += 'Moved %s to %s\n' % (incomingFileFullPath, targetFileFullPath)

		# Make status file for vendor if files were moved
		# and vendor needs invoices created
		if gotDropboxFile and gotDropboxFile == profileName:
			if createInvoice and statusFileDir and almaWebhookId:
				statusFlag = profileName.replace(' ', '_') + '_' + almaWebhookId + '.SUBMITTED'
				statusFlagFullPath = os.path.join(statusFileDir, statusFlag)
				try:
					flag = open(statusFlagFullPath, 'w')
					flag.close()
				except:
					msgFail += "Failed to create %s\n" % (statusFlagFullPath)
					
	if mode == 'checkConf':
		if len(msgFail) == 0:
			msgPass += "%s is formatted properly" % confFile
	elif not profileFound:
		msgWarn += 'No matching config profiles were found in %s\n' % confFile
	elif not gotDropboxFile:
		msgWarn += 'No files for Alma processing were found using config file %s\n' % confFile
	
	if msgFail:
		print()
		print('Failures')
		print(msgFail)
	if msgWarn:
		print()
		print('Warnings')
		print(msgWarn)
	if msgPass:
		print()
		print('Successful')
		print(msgPass)

	return [msgPass, msgWarn, msgFail]

#    
# Run script, with usage check, if called from the command prompt 
#
if __name__ == '__main__':
    run_script()
