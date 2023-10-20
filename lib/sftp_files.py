# Use this class to transfer files using sftp.
# Methods of the same name are used in this and the ftp_files class.
#
# TME  08/04/23  Initial version

from paramiko import SSHClient, AutoAddPolicy

class SftpFiles():

	def __init__(self):
		self.client = SSHClient()
		self.error  = False
		self.client.set_missing_host_key_policy(AutoAddPolicy())

	def logon(self, remoteSite, remoteUser, password = False, privateKey = False, sshPort = 22):
		self.remoteSite = remoteSite
		self.remoteUser = remoteUser
		self.privateKey = privateKey
		self.password   = password
		self.sshPort    = sshPort

		# Connect and login to remote site using a password or a ssh key
		if self.password:
			try:
				self.client.connect(hostname = remoteSite, port = sshPort, username = remoteUser, password = password, allow_agent = False)
				self.error = False
			except Exception as error:
				self.error = 'Login failed: %s@%s. Error was: %s' % (self.remoteUser, self.remoteSite, error)
				return

		elif self.privateKey:
			try:
				self.client.connect(hostname = remoteSite, port = sshPort, username = remoteUser, key_filename = privateKey, allow_agent = False)
				self.error = False
			except Exception as error:
				self.error = 'Login failed: %s@%s. Error was: %s' % (self.remoteUser, self.remoteSite, error)
				return
		else:
			self.error = 'A password or private key  must be specified'
			return
		
		self.sftpSession = self.client.open_sftp()

	# Change directory
	def cd(self, directory):
		try:
			self.sftpSession.chdir(directory)
			self.error = False
		except Exception as error:
			self.error = 'Failed to move to %s directory. Error was: %s' % (directory, error)
	
	# Return the present working directory	
	def getcwd(self):
		self.error = False
		pwd = self.sftpSession.getcwd()
		if not pwd: pwd = '/'
		return pwd

	# Get directory list
	def listdir(self, directory = '.'):
		self.error = False
		return self.sftpSession.listdir(directory)
	
	# Sftp get file from remote system
	def get(self, remoteFile, localFile):
		try:
			self.sftpSession.get(remoteFile, localFile)
			self.error = False
		except Exception as error:
			self.error = 'Failed to download %s@%s:%s to %s. Error was: %s' % (self.remoteUser, self.remoteSite, remoteFile, localFile, error)

	# Sftp put file to remote system
	def put(self, localFile, remoteFile):
		try:
			self.sftpSession.put(localFile, remoteFile)
			self.error = False
		except Exception as error:
			self.error = 'Failed to send %s to %s@%s:%s. Error was: %s' % (localFile, self.remoteUser, self.remoteSite, remoteFile, error)

	# Close connect
	def close(self):
		try:
			self.sftpSession.close()
			self.client.close()
		except:
			pass
