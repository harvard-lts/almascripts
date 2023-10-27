#!/usr/bin/env python3
#
# Run the script with it's -h option to see it's description
# and usage or scroll down at bit
#
# Initial version 07/12/18 TME
# Last updated 10/23/27 TME

#
# Load modules, set/initialize global variables, grab arguments & check usage
#
import os, re, yaml, shutil

jobName  = 'Archive Alma files'

# run_script
# Checked usage, run main script and then display result
# Used when the script is called from the command prompt
def run_script():
    import argparse
    
    usageMsg  = """
    Move file(s) to their archive directories after Alma processing.
    A configuration file, with the needed parameters, must be specified.
    See
    archive_alma_files.yaml_template in the adjacent conf directory for an example.
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
    [msgPass, msgWarn, msgFail] = archive_alma_files(confFile, mode, profiles)

# archive_alma_files
# Move dropbox file(s) in place.
#
# Parameters: confFile    Configuration file to use
#             mode        getFiles or checkConf
#             profiles    The keyword 'ALL' or a single profile name
#
# Returns:    An array containing msgPass, msgWarn and msgFail 
#             containing successful, warning and failure messages
#
def archive_alma_files(confFile, mode, profiles):
    statusFileDir      = False
    archiveOnlyHandled = False

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

    profileFound = False
    archivedFile = False
    
    # Loop through config sets, check/set parameters
    for configSet in configSets:
        badConfigSet = False

        # Get any global parameters and then move on
        if configSet['profile_name'] == 'GLOBAL':
            try:
                statusFileDir = configSet['status_file_directory']
            except:
                pass
            try:
                archiveOnlyHandled = configSet['archive_only_handled']
                if archiveOnlyHandled.lower() == 'yes': 
                    archiveOnlyHandled = True
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
            almaDirectory = configSet['local_directory']
        except:
            almaDirectory = False
        try:
            almaArchive = configSet['local_archive']
        except:
            almaArchive = False

        # Skip disabled config sets
        if jobStatus == 'DISABLED': continue
                            
        if profileName:        
            # Just process a single config profile
            if not profiles == 'ALL':
                if not profileName == profiles:
                    continue
        else:
            msgFail += 'Configuration error: profile_name is not set in %s\n' % (confFile)
            badConfigSet = True
            
        if not almaDirectory:
            msgFail += 'Configuration error: local_directory is not set in %s for %s\n' % (confFile, profileName)
            badConfigSet = True
        if not almaArchive:
            msgFail += 'Configuration error: local_archive is not set in %s for %s\n' % (confFile, profileName)
            badConfigSet = True

        if badConfigSet: continue

        # Just check config file if specified, no files are moved
        if mode == 'checkConf':
            continue

        profileFound = True

        # Check that all the needed directories exist
        if not os.path.exists(almaDirectory):
            msgFail += 'Error: directory %s not found\n' % (almaDirectory)
            continue
        if not os.path.exists(almaArchive):
            msgFail += 'Error: directory %s not found\n' % (almaArchive)
            continue

        # Check for files processed by Alma
        for almaFile in os.listdir(almaDirectory):
        
            # Put incoming files in place and archive, renaming if specified
            sourceFileFullPath = os.path.join(almaDirectory, almaFile)
            targetFileFullPath = os.path.join(almaArchive, almaFile)
            
            # Archive only *.handled files if specified
            if archiveOnlyHandled:
                if not re.search('.+\.handled$', almaFile):
                    continue
 
            try:
                shutil.copy(sourceFileFullPath, targetFileFullPath)
            except:
                msgFail += "Copy %s to %s\n" % (sourceFileFullPath, targetFileFullPath)
                continue
            try:
                os.remove(sourceFileFullPath)
            except:
                msgFail += "Remove %s\n" % (sourceFileFullPath)
                continue

            archivedFile = True
            msgPass += 'Moved %s to %s\n' % (sourceFileFullPath, targetFileFullPath)

    if mode == 'checkConf':
        if len(msgFail)  == 0:
            msgPass += "%s is formatted properly" % confFile
    elif not profileFound:
        msgWarn += 'No matching config profiles were found in %s\n' % confFile
    elif not archivedFile:
        msgWarn += 'No files found to archive using config file %s\n' % confFile

    # Print and return the results 
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
