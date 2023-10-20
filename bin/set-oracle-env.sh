#!/bin/bash
#
# To set-up the current environment for Oracle database access. 
# Useful when running scripts, that access an Oracle database from cron.
#
# TME  04/20/21  Get Oracle home from the ltsconfig.yaml
# TME  05/25/23  Oracle home bin added to path

if [ $# -gt 0 ]; then
	echo "Set environment for Oracle database access"
	echo ". $0"
	exit
fi

# Get the name of the script's directory and then move into place
scriptDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd $scriptDir

ORACLE_HOME=`/bin/grep -i oracleHome ../conf/ltsconfig.yaml|/bin/cut -d "'" -f 2`

PATH=$PATH:$ORACLE_HOME/bin
LD_LIBRARY_PATH=$ORACLE_HOME/lib
NLS_LANG='.UTF8'
ORA_NLS=$ORACLE_HOME/ocommon/nls/admin/data

export ORACLE_HOME LD_LIBRARY_PATH NLS_LANG ORA_NLS

cd -
