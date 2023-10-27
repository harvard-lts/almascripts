# Use this class to transfer files using ftp.
# Methods of the same name are used in this and the sftp_files class.
#
# Initial version 07/19/23 TME
# Last updated 07/19/23 TME

from ftplib import FTP

class FtpFiles(FTP):

	def __init__(self):
		super().__init__()
		self.error = False

	# Connect to remote site and login
	def logon(self, remoteSite, remoteUser, password, port = 21):
		self.remoteSite = remoteSite
		self.remoteUser = remoteUser
		self.password   = password
		self.port       = port

		try:
			self.connect(remoteSite, port)
		except Exception as error:
			self.error = 'Failed to connect to %s:%s. Error was: %s' % (self.remoteSite, self.port, error)
			return
		try:
			self.login(remoteUser, password)
		except Exception as error:
			self.error = 'Login failed: %s@%s. Error was: %s' % (self.remoteUser, self.remoteSite, error)
		
	# Change directory
	def cd(self, directory):
		try:
			self.cwd(directory)
			self.error = False
		except Exception as error:
			self.error = 'Failed to move to %s directory. Error was: %s' % (directory, error)
			
	# Return the present working directory	
	def getcwd(self):
		self.error = False
		return self.pwd()
		
	# Get directory list
	def listdir(self, directory = '.'):
		self.error = False
		return self.nlst(directory)
	
	# Ftp get file from remote system
	def get(self, remoteFile, localFile):
		try:
			with open(localFile, 'wb') as fp:
			    self.retrbinary('RETR %s' % remoteFile, fp.write)
			self.error = False

		except Exception as error:
			self.error = "FTP get failed. Error was: %s." % error

	# Ftp put file to remote system (not tested)
	def put(self, localFile, remoteFile):
		try:
			file   = open(localFile,'rb')
			ftpCmd = 'STOR %s' % remoteFile
			self.storbinary(ftpCmd, file)
			self.error = False

		except Exception as error:
			self.error = "FTP put failed. Error was: %s." % error
