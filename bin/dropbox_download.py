#!/usr/bin/env python3
#
# Run the script with it's -h option to see it's description
# and usage or scroll down at bit
#
# Initial version 08/03/23 TME
# Last updated 10/23/27 TME

#
# Load modules, set/initialize global variables, grab arguments & check usage
#
import os, re, sys, yaml

# To help find other directories that might hold modules or config files
binDir = os.path.dirname(os.path.realpath(__file__))

# Find and load any of our modules that we need
commonLib = binDir.replace('bin', 'lib')
sys.path.append(commonLib)
from sftp_files import SftpFiles
from ftp_files import FtpFiles
from notify import notify

jobName = 'Dropbox Download'

# run_script
# Checked usage, run main script and then display result
# Used when the script is called from the command prompt
def run_script():
	import argparse

	usageMsg  = """
This is our dropbox download script that is intended to be run on dropbox.
It uses a configuration file to set the parameters that will define it's
downloads. The file dropbox_download.yaml_tempate, in the adjacent conf 
directory, has been provided to use as a template when creating
a new config file.

Any user account using this script must meet the requirements listed below.
 * The user account must be a member of the guestftp group.
 * The account must have incoming and archives directories that belong to the
   guestftp group and have group write permission. These directories can be 
   named differently but they must be defined in the config file.
 * A files-downloaded.ref file must exist in the defined archives directory 
   (it can be empty). The script will use this file to hold the list of 
   files it has download.
	"""

	# Check for any command line parameters
	parser = argparse.ArgumentParser(description=usageMsg, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("conf_file", help="Configuration file to use")
	group = parser.add_mutually_exclusive_group()
	group.add_argument("-p", "--profile", help="Run only the specified profile in configuration file. Otherwise, all are run.")
	group.add_argument("-c", "--checkconf", action='store_true', help="Check configuration file, no files are sent")
	parser.add_argument("-v", "--verbose", action = 'store_true', help = "Run script with verbose output")
	args = parser.parse_args()

	if args.checkconf:
		mode    = 'checkConf'
		profile = 'ALL'
	elif args.profile:
		mode    = 'getFiles'
		profile = args.profile
	else:
		mode    = 'getFiles'
		profile = 'ALL'

	dl = DownloadFiles(args.conf_file, False, args.verbose)
	dl.get_files(profile, mode)


class DownloadFiles():

	def __init__(self, confFile, notifyJM = False, verbose = False):
		self.confFile     = confFile
		self.verbose      = verbose
		self.loginSession = None
		self.configSets   = False
		self.error        = ''
		
		# Make sure we have a notify object. Just echo to screen by default.
		if notifyJM:
			self.notifyJM = notifyJM
		else:
			self.notifyJM = notify('echo')
			self.notifyJM.log('pass', jobName, self.verbose)

		# Make sure config file exists
		if not os.path.isfile(self.confFile):
			self.error = f'Configuration file {self.confFile} not found'
			self.notifyJM.log('fail', self.error, True)
	
	# Returns the profile names as a list from the config
	def get_profile_names(self):
		profileNames = []
		self.error   = ''

		self.get_config_sets()
		if not self.configSets: return None

		for configSet in self.configSets:
			try:
				profileNames.append(configSet['profile_name'])
			except:
				self.error = f'Configuration error: profile_name is not set for one or more profiles in {self.confFile}'
				self.notifyJM.log('fail', self.error, True)

		return profileNames

	# Open config file and get config sets (profiles)
	def get_config_sets(self):
		try:
			with open(self.confFile, 'r') as ymlfile:
				self.configSets = yaml.load(ymlfile, Loader=yaml.SafeLoader)
		except:
			self.error = f'Unable to read configuration file {self.confFile}'
			self.notifyJM.log('fail', self.error, True)
			return None
		
		return self.configSets

	# Login to s/ftp site
	def login_remote_site(self, downloadProtocol, downloadSite, downloadUser, password, privateKey, downloadPort, jobStatus):
		self.error = ''

		if downloadProtocol == 'SFTP':
			if not downloadPort: downloadPort = 22
			self.loginSession = SftpFiles()
			self.loginSession.logon(downloadSite, downloadUser, password, privateKey, downloadPort)

		elif downloadProtocol == 'FTP':
			if not downloadPort: downloadPort = 21
			self.loginSession = FtpFiles()
			self.loginSession.logon(downloadSite, downloadUser, password, downloadPort)
	
		if self.loginSession.error:
			if jobStatus == 'SITEDOWN':
				self.notifyJM.log('warn', self.loginSession.error, self.verbose)
			else:
				self.notifyJM.log('fail', self.loginSession.error, True)
				self.error = self.loginSession.error

			self.loginSession = None
		else:
			self.notifyJM.log('info', f'Logon to {downloadUser}@{downloadSite}', self.verbose)

	# Download files or just check if mode is checkConf
	def get_files(self, profile = 'ALL', mode = 'getFiles'):
		formerDownloadSite = ''
		formerDownloadUser = ''
		downloadSite       = ''
		returnStatus       = False
		self.error         = ''
		profileFound       = False
		newFilesFound      = False

		# To hold the latest files downloaded
		self.filesDownloaded = []

		# Get and set config sets (profiles) from config file if needed
		if not self.configSets: self.get_config_sets()

		# Loop through config sets, check/set parameters
		for configSet in self.configSets:
			badConfigSet = False

			if downloadSite:
				formerDownloadSite = downloadSite
				formerDownloadUser = downloadUser

			try:
				profileName = configSet['profile_name']
			except:
				self.notifyJM.log('fail', f'Configuration error: profile_name is not set in {self.confFile}', True)
				continue
			try:
				jobStatus = configSet['job_status']
			except:
				self.notifyJM.log('info', f'job_status is not set in {self.confFile} for {profileName}. A job status of ENABLED will be used.', self.verbose)
				jobStatus = 'ENABLED' 
			try:
				downloadProtocol = configSet['download_protocol']
			except:
				self.notifyJM.log('fail', f'Configuration error: download_protocol is not set in {self.confFile} for {profileName}', True)
				badConfigSet = True
			try:
				downloadPort = configSet['download_port']
			except:
				downloadPort = False
			try:
				downloadSite = configSet['download_site']
			except:
				self.notifyJM.log('fail', f'Configuration error: download_site is not set in {self.confFile} for {profileName}', True)
				badConfigSet = True
			try:
				downloadUser = configSet['download_user']
			except:
				self.notifyJM.log('fail', f'Configuration error: download_user is not set in {self.confFile} for {profileName}', True)
				badConfigSet = True
			try:
				password = configSet['download_password']
			except:
				password = False
			try:
				privateKey = configSet['private_key']
			except:
				privateKey = False
			try:
				filesToDownload = configSet['files_to_download']
			except:
				self.notifyJM.log('fail', f'Configuration error: files_to_download is not set in {self.confFile} for {profileName}', True)
				badConfigSet = True
			try:
				downloadFilename = configSet['download_filename']
			except:
				self.notifyJM.log('fail', f'Configuration error: download_filename is not set in {self.confFile} for {profileName}', True)
				badConfigSet = True
			try:
				downloadDirs = configSet['download_directories'].split(',')
			except:
				downloadDirs = ['.',]
			try:
				incomingDir = configSet['dropbox_incoming']
			except:
				self.notifyJM.log('fail', f'Configuration error: dropbox_incoming is not set in {self.confFile} for {profileName}', True)
				badConfigSet = True
			try:
				renameDownloadFile = configSet['rename_download_file']
			except:
				renameDownloadFile = False
			try:
				dropboxArchive = configSet['dropbox_archive']
			except:
				self.notifyJM.log('fail', f'Configuration error: dropbox_archive is not set in {self.confFile} for {profileName}', True)
				badConfigSet = True
			try:
				downloadFiles = configSet['download_files']
			except:
				downloadFiles = True

			# We need a password for ftp logins
			if downloadProtocol == 'FTP':
				if not password:
					self.notifyJM.log('fail', f'Configuration error: download_password is not set in {self.confFile} for {profileName}', True)
					badConfigSet = True

			# Sftp logins can use an ssh key as well as a password
			elif downloadProtocol == 'SFTP':
				if not password and not privateKey:
					self.notifyJM.log('fail', f'Configuration error: neither download_password or private_key is not set in {self.confFile} for {profileName}', True)
					badConfigSet = True
			else:
				self.notifyJM.log('fail', f'Configuration error: download_protocol is not set properly in {self.confFile} for {profileName}. Supported values are "SFTP" of "FTP."', True)
				badConfigSet = True
		
			# Just download files for a single config profile
			if profile != 'ALL':
				if profileName != profile:
					continue

			if badConfigSet:
				self.error += f'Configuration error: profile {profileName} in {self.confFile} has one or more error.\n'
			else:
				profileFound = True

			# Check that needed directories and files exist
			msgError = ''
			if not os.path.exists(incomingDir):
				msgError = f'Error: local directory {incomingDir} not found'
				self.notifyJM.log('fail', msgError, True)
				self.error += f'{msgError}\n'
				
			if not os.path.exists(dropboxArchive):
				msgError = f'Error: archive directory {dropboxArchive} not found'
				self.notifyJM.log('fail', msgError, True)
				self.error += f'{msgError}\n'

			filesDownloadedFile = f'{dropboxArchive}/files-downloaded.ref'
			if not os.path.exists(filesDownloadedFile):
				msgError = f'Error: {filesDownloadedFile} not found'
				self.notifyJM.log('fail', msgError, True)
				self.error += f'{msgError}\n'

			if badConfigSet or msgError: continue
			
			# Just check config file if specified, no files are copied
			if mode == 'checkConf':
				self.notifyJM.log('pass', f"Profile {profileName} looks good", True)
				continue

			# Move onto next config set if this one is disabled
			# or not actually intended to download_files
			if jobStatus == 'DISABLED' or not downloadFiles: continue			
			
			os.chdir(incomingDir)
			
			# If we're looking for new files, open the file holding
			# the list of files already downloaded and load into a list
			if filesToDownload == 'NEW':
				filesDownloadedList = []
				with open(filesDownloadedFile) as input:
					for line in input:
						filesDownloadedList.append(line.rstrip())

			# And then open it again to add any newly download files
			try:
				filesDownloadedOut = open(filesDownloadedFile, 'a')
			except:
				self.notifyJM.log('fail', f'Failed to open {filesDownloadedFile} for writing', True)
				continue

			# Connect and login to s/ftp server but only if we need to.
			# Some config files have multiple profiles using the same account.
			if self.loginSession is None:
				self.login_remote_site(downloadProtocol, downloadSite, downloadUser, password, privateKey, downloadPort, jobStatus)

			elif formerDownloadSite != downloadSite and formerDownloadUser != downloadUser:
				if self.loginSession: self.loginSession.close()
				self.login_remote_site(downloadProtocol, downloadSite, downloadUser, password, privateKey, downloadPort, jobStatus)

			if self.loginSession is None: continue
				
			# Check each specified directory on remote server for new files
			reDownloadFilename = re.compile(downloadFilename)
			homeDir            = self.loginSession.getcwd()

			for downloadDir in downloadDirs:

				self.loginSession.cd(downloadDir)

				if self.loginSession.error:
					message = f'Failed to moved into {downloadDir}: Error was: {self.loginSession.error}'
					if jobStatus == 'SITEDOWN':
						self.notifyJM.log('warn', message, verbose)
					else:
						self.notifyJM.log('fail', message, True)
						self.error += f'{message}\n'
					continue
				
				self.notifyJM.log('info', f'Moved into {downloadDir}', self.verbose)
				
				# Loop on directory list
				for remoteFile in self.loginSession.listdir():
					
					# Move on unless its a file we want
					match = reDownloadFilename.match(remoteFile)
					if not match: continue
					
					# Set new name for file if renaming was specified
					if renameDownloadFile:

						# Up to 10 match and swaps are supported
						if 'MATCH' in renameDownloadFile:
							localFile = renameDownloadFile
							for index in range(1, 11):
								try:
									localFile = localFile.replace('MATCH', match.group(index), 1)
								except:
									break
								
						# Or swap in year
						elif 'YEAR' in renameDownloadFile:
							localFile = renameDownloadFile.replace('YEAR', match.group(1))

						# Or make all lower case
						elif renameDownloadFile == 'LOWERCASE':
							localFile = remoteFile.lower()

					else:						
						localFile = remoteFile

					# To only download files that we haven't yet
					if filesToDownload == 'NEW':
						if localFile in filesDownloadedList:
							continue
					
					# If we got this far its time to download the file
					self.loginSession.get(remoteFile, f'{incomingDir}/{localFile}')
					
					if self.loginSession.error:
						if jobStatus == 'SITEDOWN':
							self.notifyJM.log('warn', self.loginSession.error, True)
						else:
							self.notifyJM.log('fail', self.loginSession.error, True)
							self.error += f'{self.loginSession.error}\n'

						# Reset connection to remote site if file download fails
						self.loginSession.close()
						self.login_remote_site(downloadProtocol, downloadSite, downloadUser, password, privateKey, downloadPort, jobStatus)
						if self.loginSession is None:
							break
						else:
							continue

					if len(self.filesDownloaded) == 0:
						self.notifyJM.log('pass', f'The following file(s) were downloaded for {profileName}', self.verbose)
					
					self.filesDownloaded.append(localFile)
					
					# Report and update the file downloaded file
					self.notifyJM.log('pass', f'{downloadDir}/{remoteFile} -> {incomingDir}/{localFile}', self.verbose)
					filesDownloadedOut.write(f'{localFile}\n')
					
				self.loginSession.cd(homeDir)
				
			# Clean-up and report for profile
			filesDownloadedOut.close()
 
			fileDownloadCount = len(self.filesDownloaded)
			if fileDownloadCount == 0:
				self.notifyJM.log('pass', f'No new files found for {profileName}', self.verbose)
			else:
				self.notifyJM.log('pass', f'{fileDownloadCount} files downloaded for {profileName}', self.verbose)
				returnStatus = True

		# If downloading for a single profile, was it found?
		if profile != 'ALL':
			if not profileFound:
				msgError = f'Error: profile {profile} not found in {self.confFile}'
				self.notifyJM.log('fail', msgError, True)
				self.error += f'{msgError}\n'

		# Return results 
		return returnStatus
    
#    
# Run script, with usage check, if called from the command prompt 
#
if __name__ == '__main__':
    run_script()
