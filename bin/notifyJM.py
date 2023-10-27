#!/usr/bin/env python3
#
# Run the script with it's -h option to see it's description
# and usage or scroll down at bit
#
# Initial version 02/16/18 TME
# Last updated 10/23/27 TME

#
# Load modules, set/initialize global variables
#
import os, sys

# To help find other directories that might hold modules or config files
binDir = os.path.dirname(os.path.realpath(__file__))

# Find and load any of our modules that we need
scriptLib = binDir.replace('bin', 'lib')
sys.path.append(scriptLib)
from notify import notify

# run_script
# Checked usage, run main script and then display result
# Used when the script is called from the command prompt
def run_script():
    import argparse

    usageMsg = """
	Notify the Job Monitor. Supported status codes are;

			STARTED_SUCCESS
			STARTED_WARNING
			STARTED_FAIL
			RUNNING
			RUNNING_WARNING
			RUNNING_ERROR
			FAILED
			COMPLETED_SUCCESS
			COMPLETED_WARNING
			COMPLETED_FAILED
	"""

    # Check for any command line parameters
    parser = argparse.ArgumentParser(description=usageMsg)
    parser.add_argument("job_code", help = "Job code as defined in the Job Monitor")
    parser.add_argument("status_code", help = "Status code as defined in the Job Monitor (see above)")
    parser.add_argument("-m", "--message", help = "Job result message to pass to the Job Monitor")
    parser.add_argument("-r", "--run_id", help = "Job run ID used to identify the job run in the Job Monitor")
    parser.add_argument("-n", "--no_retries", action = 'store_true', help = "Do not retry if Job Monitor fails to respond")
    args = parser.parse_args()

     # Required, job code and status code
    jobCode    = args.job_code
    statusCode = args.status_code

    # Optional, message and run ID
    message   = args.message
    runId     = args.run_id        
    noRetries = args.no_retries

    # Call function and then catch and display results
    returnMsg = notifyJM(jobCode, statusCode, message, runId, noRetries)
    print(returnMsg)

# notifyJM
# Notify Job Monitor
#
# Parameters
#   jobCode       Job Monitor job code such as "edi_orders" or "patload"
#
#   statusCode    Supported Job Monitor status codes are;
#                     STARTED_SUCCESS
#                     STARTED_WARNING
#                     STARTED_FAIL
#                     RUNNING
#                     RUNNING_WARNING
#                     RUNNING_ERROR
#                     FAILED
#                     COMPLETED_SUCCESS
#                     COMPLETED_WARNING
#                     COMPLETED_FAILED
#
#   message       Optional, use to pass a result message to the Job Monitor
#
#   runId         Optional, use to update a specific Job Monitor job run.
#                 This parameter is not usually needed.
#
#   noRetries     Do not retry if Job Monitor fails to respond
#
def notifyJM(jobCode, statusCode, message = 'none', runId = False, noRetries = False):

	# Get instance of notify and then report to the Job Monitor
	notifyJM = notify('monitor', jobCode)
	runId    = notifyJM.notifyJM(jobCode, statusCode, message, runId, noRetries)

	return runId

#    
# Run script, with usage check, if called from the command prompt 
#
if __name__ == '__main__':
    run_script()
    