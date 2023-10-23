#!/usr/bin/env python3
#
# Run the script with it's -h option to see it's description
# and usage or scroll down at bit
#
# TME  08/04/23  New updated version of send_files.py
# TME  10/23/23  Changed shbang to use /usr/bin/env

#
# Load modules, set/initialize global variables, grab arguments & check usage
#
import os, re, yaml, gzip, tarfile, shutil, stat, sys
from subprocess import run, PIPE

# To help find other directories that might hold modules or config files
binDir = os.path.dirname(os.path.realpath(__file__))

# Find and load any of our modules that we need
commonLib = binDir.replace('bin', 'lib')
sys.path.append(commonLib)
from ltstools import get_date_time_stamp
from sftp_files import SftpFiles
from ftp_files import FtpFiles
from notify import notify

jobName     = 'Send Files'
scp         = '/bin/scp'
xferSession = False

# Used when unpacking files
reGzippedFiles = re.compile('.+\.gz$')
reTarredFiles  = re.compile('.+\.tar$')

# Might use in file or directory names
year     = get_date_time_stamp('year')
month    = get_date_time_stamp('month')
day      = get_date_time_stamp('day')
yyyymmdd = f'{year}{month}{day}'

# run_script
# Checked usage, run main script and then display result
# Used when the script is called from the command prompt
def run_script():
	import argparse

	usageMsg  = """
	Send files to remote systems. A configuration file, with the needed 
	parameters, must be specified. See send_files.yaml_template in the 
	adjacent conf directory for an example.
	"""

	# Check for any command line parameters
	parser = argparse.ArgumentParser(description=usageMsg)
	parser.add_argument("conf_file", help="Configuration file to use")
	parser.add_argument("-v", "--verbose", action = 'store_true', help = "Run script with verbose output")
	group = parser.add_mutually_exclusive_group()
	group.add_argument("-p", "--profile", help="Run only the specified profile in configuration file. Otherwise, all are run.")
	group.add_argument("-c", "--checkconf", action='store_true', help="Check configuration file, no files are sent")
	args = parser.parse_args()

	if args.checkconf:
		mode     = 'checkConf'
		profiles = 'ALL'
	elif args.profile:
		mode     = 'sendFile'
		profiles = args.profile
	else:
		mode     = 'sendFile'
		profiles = 'ALL'

	# Call function and then catch and display results
	send_files(args.conf_file, mode, profiles, False, args.verbose)

# send_files
# Send files to remote systems.
#
# Parameters: confFile    Configuration file to use
#             mode        sendFile or checkConf
#             profiles    The keyword 'ALL' or a single profile name
#             verbose     True for verbose output
#
# Returns:    True upon successful, otherwise, False
#
def send_files(confFile, mode, profiles = 'ALL', notifyJM = False, verbose = False):
	global xferSession
	profileFound = False

	# Make sure we have a notify object. Just echo to screen by default.
	if not notifyJM:
		notifyJM = notify('echo')
		notifyJM.log('pass', jobName, verbose)

	# Open and loaded config file into an array of hashes
	if os.path.isfile(confFile):
		with open(confFile, 'r') as ymlfile:
			configSets = yaml.load(ymlfile, Loader=yaml.SafeLoader)
	else:
		notifyJM.log('fail', f'Configuration file {confFile} not found', True)
		notifyJM.report('stopped')
		return False

	# Loop through config sets, check/set parameters
	for configSet in configSets:
		badConfigSet = False
		fileUploaded = False

		try:
			profileName = configSet['profile_name']
		except:
			profileName = False
		try:
			xferProtocol = configSet['upload_protocol']
		except:
			xferProtocol = False
		try:
			xferPort = configSet['upload_port']
		except:
			xferPort = False
		try:
			sendDone = configSet['send_done']
		except:
			sendDone = False
		try:
			remoteSite = configSet['upload_site']
		except:
			remoteSite = False
		try:
			remoteUser = configSet['upload_user']
		except:
			remoteUser = False
		try:
			password = configSet['upload_password']
		except:
			password = False
		try:
			privateKey = configSet['private_key']
		except:
			privateKey = False
		try:
			remoteDir = configSet['upload_directory']
		except:
			remoteDir = False
		try:
			localDir = configSet['local_directory']
		except:
			localDir = False
		try:
			localFiles = configSet['local_files']
		except:
			localFiles = False
		try:
			renameUploadFile = configSet['rename_upload_file']
		except:
			renameUploadFile = False
		try:
			localArchive = configSet['local_archive']
		except:
			localArchive = False                        
		try:
			handleUnmatchedFiles = configSet['handle_unmatched_files']
		except:
			handleUnmatchedFiles = False                        
		try:
			unpackFiles = configSet['unpack_first']
		except:
			unpackFiles = False                        
		try:
			handleNoFiles = configSet['handle_no_files']
		except:
			handleNoFiles = 'PASS'                        
	   
		# Just send files for a single config profile
		if profileName:        
			if not profiles == 'ALL':
				if not profileName == profiles:
					continue
		else:
			notifyJM.log('fail', 'Configuration error: profile_name is not set in %s' % (confFile), True)
			badConfigSet = True
		
		profileFound = True

		if not xferProtocol:
			notifyJM.log('fail', 'Configuration error: upload_protocol is not set in %s for %s' % (confFile, profileName), True)
			badConfigSet = True
		if not remoteSite:
			notifyJM.log('fail', 'Configuration error: upload_site is not set in %s for %s' % (confFile, profileName), True)
			badConfigSet = True
		if not remoteUser:
			notifyJM.log('fail', 'Configuration error: upload_user is not set in %s for %s' % (confFile, profileName), True)
			badConfigSet = True
		if not remoteDir:
			notifyJM.log('fail', 'Configuration error: upload_directory is not set in %s for %s' % (confFile, profileName), True)
			badConfigSet = True
		if not localDir:
			notifyJM.log('fail', 'Configuration error: local_directory is not set in %s for %s' % (confFile, profileName), True)
			badConfigSet = True
		if not localFiles:
			notifyJM.log('fail', 'Configuration error: local_files is not set in %s for %s' % (confFile, profileName), True)
			badConfigSet = True
		if xferProtocol == 'FTP':
			if not password:
				notifyJM.log('fail', 'Configuration error: password is not set in %s for %s' % (confFile, profileName), True)
				badConfigSet = True
	
		if badConfigSet: continue

		# Just check config file if specified, no files are copied
		if mode == 'checkConf':
			notifyJM.log('pass', f'Profile {profileName} looks good', verbose)
			continue

		# Swap any key words
		localDir   = localDir.replace('_YEAR_', year).replace('_MONTH_', month).replace('_DAY_', day)
		localFiles = localFiles.replace('_YEAR_', year).replace('_MONTH_', month).replace('_DAY_', day)

		# Check that all the needed directories exist
		if not os.path.exists(localDir):
			notifyJM.log('fail', 'Error: local directory %s not found' % (localDir), True)
			continue
		if localArchive:
			if not os.path.exists(localArchive):
				notifyJM.log('fail', 'Error: archive directory %s not found' % (localArchive), True)

		# Make sure that we don't already have a s/ftp connection
		if xferSession: 
			xferSession.close()
			xferSession = False

		# Check for local files that we want to upload
		filesUploaded = 0
		reLocalFiles  = re.compile(localFiles)
		os.chdir(localDir)
		for localFile in os.listdir('.'):
	
			match = reLocalFiles.match(localFile)
		
			# Track unmatched files if specified by config set
			if match == None:
				if handleUnmatchedFiles:
					notifyJM.log(handleNoFiles.lower(), f'{localFile} found in {localDir} but does not match the file name regular expression of {localFiles}', verbose)
				continue

			# Set new name for file if renaming was specified.
			# Up to 10 match and swaps are supported.
			if renameUploadFile:
				newFileName = renameUploadFile
				for index in range(1, 11):
					try:
						newFileName = newFileName.replace('_MATCH_', match.group(index), 1)
					except:
						break
						
			# Unpack files if specified and needed
			if unpackFiles:
				unzippedFile = False
				untarredFile = False

				# Ungzip if needed
				match = reGzippedFiles.match(localFile)
				if match != None:
					unzippedFile = localFile.replace('.gz', '')
					if not os.path.isfile(unzippedFile):					
						try:
							with gzip.open(localFile, 'rb') as fileIn:
								with open(unzippedFile, 'wb') as fileOut:
									shutil.copyfileobj(fileIn, fileOut)
						except:
							notifyJM.log('fail', "Failed to gunzip %s/%s" % (localDir, localFile), True)
							continue
						
					localFile = unzippedFile

				# Extract tar archive if needed
				match = reTarredFiles.match(localFile)
				if match != None:
					untarredFile = localFile.replace('.tar', '')
					if not os.path.isfile(untarredFile):
						try:
							tar = tarfile.open(localFile)
							tar.extractall()
							tar.close()
						except:
							notifyJM.log('fail', "Failed to untar %s/%s" % (localDir, localFile), True)
							continue

					localFile = untarredFile
				
					# Make sure file permissions are correct (Alma has issues)
					os.chmod(localFile, stat.S_IRUSR)

			# Use new name when uploading if renaming was specified
			if renameUploadFile:
				remoteFile = f'{remoteDir}/{newFileName}'
				
			# Otherwise, just use local file name
			else:
				remoteFile = remoteDir + '/' + localFile

			localFileFullPath = os.path.join(localDir, localFile)

			if xferProtocol == 'SCP':
				fileUploaded = scp_file(remoteSite, remoteUser, privateKey, xferPort, remoteFile, localFileFullPath, notifyJM)
			else:
				fileUploaded = sftp_ftp_file(xferProtocol, remoteSite, remoteUser, password, privateKey, xferPort, remoteFile, localFileFullPath, notifyJM)
			
			if fileUploaded:				
				if filesUploaded == 0:
					notifyJM.log('pass', f'The following file(s) were uploaded for {profileName}', verbose)
				
				notifyJM.log('pass', f'{localFileFullPath} {xferProtocol} to {remoteSite}:{remoteFile}', verbose)
				filesUploaded += 1
				fileUploaded   = False
				
			else:
				continue
	
			# Archive upload file if specified
			if localArchive:

				# Archive using new name if renaming was specified
				if renameUploadFile:
					archiveFileFullPath = f'{localArchive}/{newFileName}'
				
				# Otherwise, just use local file name
				else:
					archiveFileFullPath = f'{localArchive}/{localFile}'

				try:
					shutil.copy(localFileFullPath, archiveFileFullPath)
				except:
					notifyJM.log('fail', "Failed to copy %s to %s" % (localFileFullPath, archiveFileFullPath), True)
					continue
				try:
					os.remove(localFileFullPath)
				except:
					notifyJM.log('fail', "Failed to remove %s" % (localFileFullPath), True)
					continue

			# If files were unpacked, clean up
			if unpackFiles:
				if unzippedFile: os.remove(unzippedFile)
				if untarredFile: os.remove(untarredFile)
		
		if filesUploaded == 0:
			notifyJM.log(handleNoFiles.lower(), f'No files uploaded for {profileName}', verbose)
		else:
			notifyJM.log('pass', f'{filesUploaded} files uploaded for {profileName}', verbose)

	# Clean-up and report
	if xferSession:
		xferSession.close()
		xferSession = False

	if not profileFound:
		notifyJM.log('warn', 'No matching config profiles were found', verbose)

	notifyJM.report('running')
	return True

#
# Subroutines
#

# Upload file using SFTP
def sftp_ftp_file(xferProtocol, remoteSite, remoteUser, password, privateKey, xferPort, remoteFile, localFile, notifyJM):
	global xferSession

	# Login to remote site using sftp or ftp if not already
	if not xferSession:
		try:
			if xferProtocol == 'SFTP':
				if not xferPort: xferPort = 22
				xferSession = SftpFiles()
				xferSession.logon(remoteSite, remoteUser, password, privateKey, xferPort)

			elif xferProtocol == 'FTP':
				if not xferPort: xferPort = 21
				xferSession = FtpFiles()
				xferSession.logon(remoteSite, remoteUser, password, xferPort)

			if xferSession.error:
				notifyJM.log('fail', xferSession.error, True)
				return False
		except:
			notifyJM.log('fail', "Login to %s using %s account" % (remoteSite, remoteUser), True)
			return False

	# And then upload file
	try:
		xferSession.put(localFile, remoteFile)
	except:
		notifyJM.log('fail', "S/ftp %s to %s@%s:%s" % (localFile, remoteUser, remoteSite, remoteFile), True)
		return False

	if xferSession.error:
		notifyJM.log('fail', xferSession.error, True)
		return False

	return True
    
# Upload file using SCP
def scp_file(remoteSite, remoteUser, privateKey, xferPort, remoteFile, localFile, notifyJM):

	destination = f'{remoteUser}@{remoteSite}:{remoteFile}'
	
	command = scp
	if xferPort: command += f' -P {xferPort}'
	if privateKey: command += f' -i {privateKey}'
	command += f' {localFile} {destination}'

	try:
		cp = run(command.split(), stdout=PIPE, universal_newlines=True)
	except:
		notifyJM.log('fail', f"Failed {command}", True)
		return False

	if cp.returncode > 0:
		if cp.stderr:
			notifyJM.log('fail', "Failed: %s. Error was: %s" % (command, cp.stderr), True)
		else:
			notifyJM.log('fail', f"Failed: {command}", True)
		return False
	else:
		return True

#    
# Run script, with usage check, if called from the command prompt 
#
if __name__ == '__main__':
    run_script()
