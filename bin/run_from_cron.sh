#!/bin/bash
#
# Set the environment for Oracle database access and the run specified script.
# Useful when running scripts from cron that need to access an Oracle database.
# Other variables and set-up can be added to this script.
#
# Initial version 03/31/23 TME
# Last updated 10/23/27 TME

# Show help message or get script command to run
showHelp=0

if [[ $# -gt 0 ]]
then
	if [[ $1 == '-h' ]]
	then
		showHelp=1
	else
		scriptCommand=$1
	fi
else
	showHelp=1
fi

if [[ $showHelp -eq 1 ]]
then
	echo "Set the environment for Oracle database access and the run specified script."
	echo "$0 script_name"
	exit
fi

# Get the name of the script's directory and then move to script base directory
scriptDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd $scriptDir
cd ..

# Set the Oracle environment
ORACLE_HOME=`/bin/grep -i oracleHome conf/main.yaml|/bin/cut -d "'" -f 2`

PATH=$PATH:$ORACLE_HOME/bin
LD_LIBRARY_PATH=$ORACLE_HOME/lib
NLS_LANG='.UTF8'
ORA_NLS=$ORACLE_HOME/ocommon/nls/admin/data

export ORACLE_HOME LD_LIBRARY_PATH NLS_LANG ORA_NLS

# And then run script
./$scriptCommand
