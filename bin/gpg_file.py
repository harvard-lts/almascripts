#!/bin/env python3
#
# Run the script with it's -h option to see it's description
# and usage or scroll down at bit
#
# TME  12/17/18  Initial version
# TME  06/06/19  Use string formatting to set encryptedFile
# TME  01/24/20  gpgCmd and gpgDir are now set in ltstools.py

#
# Load modules, set/initialize global variables, grab arguments & check usage
#
import os, sys, argparse, re
from subprocess import run

# To help find other directories that might hold modules or config files
binDir = os.path.dirname(os.path.realpath(__file__))

# Find and load any of our modules that we need
commonLib = binDir.replace('bin', 'lib')
sys.path.append(commonLib)
from ltstools import ltsScripts, mode, gpgCmd, gpgDir

usageMsg  = "This script can be used to encrypt or decrypt a file"

# Used when script is run from the command line
def run_script():

	# Check for any command line parameters
	parser = argparse.ArgumentParser(description=usageMsg)
	parser.add_argument("operation", choices=['encrypt', 'decrypt'], help="encrypt or decrypt")
	parser.add_argument("file", help="File to encrypt or decrypt")
	parser.add_argument("-r", "--recipient", help="Recipient to use when encrypting a file")
	parser.add_argument("-p", "--passphrase", help="Passphrse to use when decrypting a file")
	parser.add_argument("-d", "--deletefile", action='store_true', help="Delete the source file")
	args = parser.parse_args()

	# Call function and then catch and display results
	if args.operation == 'encrypt':
		[msgPass, msgWarn, msgFail] = encrypt_file(args.file, args.recipient, args.deletefile)
	elif args.operation == 'decrypt':
		[msgPass, msgWarn, msgFail] = decrypt_file(args.file, args.passphrase, args.deletefile)
	
	if msgFail:
		print('\nFailed')
		print(msgFail)	
	if msgWarn:
		print('\nWarnings')
		print(msgWarn)	
	if msgPass:
		print('\nSuccessful')
		print(msgPass)

#
# Main program
#

# Encrypt given file with given recipient
def encrypt_file(unencryptedFile, recipient = False, rmSourceFile = False):
	if not recipient:
		print('Recipient must be specified to encrypt a file')
		return False
	
	# Group messages by status type
	msgPass = '';
	msgWarn = '';
	msgFail = '';

	# Encrypt file
	command = [gpgCmd, '--homedir', gpgDir, '--quiet', '--yes', '--batch', '--encrypt', '--recipient', recipient, unencryptedFile]
	try:
		run(command)
	except:
		msgFail += 'Failed: %s' % command
		return [msgPass, msgWarn, msgFail]
		
	# and then rename it with a gpg extension
	encryptedFile = '%s.gpg' % unencryptedFile
	try:
		if os.path.getsize(encryptedFile) == 0:
			msgFail += '%s is empty' % encryptedFile
			return [msgPass, msgWarn, msgFail]
		else:
			msgPass += 'Encrypted %s' % unencryptedFile
	except:
		msgFail += '%s was not created' % encryptedFile
		return [msgPass, msgWarn, msgFail]
	
	# Remove source file if specified
	if rmSourceFile:
		try:
			os.remove(unencryptedFile)
		except:
			msgFail += 'Failed to remove %s' % unencryptedFile

	return [msgPass, msgWarn, msgFail]

# Decrypt given file with given passphrase. Remove source file if specified.
def decrypt_file(encryptedFile, passphrase = False, rmSourceFile = False):
	
	# Group messages by status type
	msgPass = '';
	msgWarn = '';
	msgFail = '';

	if not passphrase:
		msgFail += 'Passphrase must be specified to decrypt a file'
		return [msgPass, msgWarn, msgFail]
		
	# Only files an extension of gpg or pgp are supported
	match = re.match('(.+)\.(gpg|pgp)$', encryptedFile)
	if match == None:
		msgFail += 'Only files with an extension of gpg or pgp are supported'
		return [msgPass, msgWarn, msgFail]
	# Use base name of encrypted file to get the decrypted file name
	else:
		decryptedFile = match.group(1)

	# Decrypt file
	command = [gpgCmd, '--homedir', gpgDir, '--quiet', '--yes', '--batch', '--passphrase', passphrase, '--output', decryptedFile, '--decrypt', encryptedFile]
	try:
		run(command)
	except:
		msgFail += 'Failed to decrypt %s' % encryptedFile
		return [msgPass, msgWarn, msgFail]
		
	# Make sure that we got our decrypted file
	try:
		if os.path.getsize(decryptedFile) == 0:
			msgFail += '%s is empty' % decryptedFile
			return [msgPass, msgWarn, msgFail]
		else:
			msgPass += 'Decrypted %s' % encryptedFile
	except:
		msgFail += '%s was not created' % decryptedFile
		return [msgPass, msgWarn, msgFail]
	
	# Remove source file if specified
	if rmSourceFile:
		try:
			os.remove(encryptedFile)
		except:
			msgFail += 'Failed to remove %s' % encryptedFile

	return [msgPass, msgWarn, msgFail]

#
# Sub-routines
#

#    
# Run script, with usage check, if called from the command prompt 
#
if __name__ == '__main__':
	run_script()

