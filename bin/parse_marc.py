#!/usr/bin/env python3
#
# Run the script with it's -h option to see it's description
# and usage or scroll down at bit
#
# Initial version 03/25/22 TME
# Last updated 10/23/27 TME

import argparse
from pymarc import MARCReader

usageMsg  = """
Parse specified file and print out
"""

# Check for any command line parameters
parser = argparse.ArgumentParser(description=usageMsg)
parser.add_argument("inputfile", help = "File to parse")
parser.add_argument("-f", "--field", help = "Find and print just this field")
args = parser.parse_args()

inputFile = args.inputfile
if args.field:
	searchField = args.field
else:
	searchField = False

# Open marc file print out each record
with open(inputFile, 'rb') as fh:
	reader = MARCReader(fh, to_unicode=True)
	for record in reader:        	
		if searchField:
			for field in record.get_fields(searchField):
				print(field)
		else:
			print(record)
