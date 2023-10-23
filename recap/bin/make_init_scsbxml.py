#!/usr/bin/env python3
#
# TME  02/01/21  Initial version
# TME  02/09/21  Now uses a file are barcodes to determine which items to keep.
#                Holdings without items are dropped. Bibs without holdings are 
#                dropped. Use 'HV' in datafield 900 subfield b.
# TME  03/02/21  Report if a barcode file is used
# TME  04/01/21  Catch and report output file write failures.
#                Skip files that are not named as expected.
# TME  04/19/21  Map value of 900 $b from 876 $9 (subfield 9)
# TME  04/20/21  Less matching in my regular expression and file glob, just 
#                want the numeric sequences. Copies barcode file properly now.
# TME  06/08/21  Support for a second file naming convention
# TME  10/23/23  Changed shbang to use /usr/bin/env

#                

#
# Load modules, set/initialize global variables, grab arguments & check usage
#
import argparse, gzip, os, re, shutil, sys, tarfile
from lxml import etree
from glob import glob

# To help find other directories that might hold modules or config files
binDir = os.path.dirname(os.path.realpath(__file__))

# Find and load any of our modules that we need
commonLib   = binDir.replace('recap/bin', 'lib')
commonBin   = binDir.replace('recap/bin', 'bin')
sys.path.append(commonLib)
from almatools import almaOutputRoot
from ltstools import get_date_time_stamp
from notify import notify

filesDir  = binDir.replace('bin', 'files')
logDir    = binDir.replace('bin', 'log')
jobCode   = 'recap_scsb'

almaScsbDir    = f'{almaOutputRoot}/recap-scsb-initial-accession'
almaScsbInDir  = f'{almaScsbDir}/input'
almaScsbOutDir = f'{almaScsbDir}/output'
almaScsbProcessedDir = f'{almaScsbDir}/processed'
inputFileGlob        = '*202*.xm*'
reInputFile1         = re.compile('.*_(\d+).*(202\d+_\d+)\.xm*.')
reInputFile2         = re.compile('.*_(202\d+_\d+)_.*_(\d+)\.xm*.')
barcodeFileGlob      = 'barcodes*.txt'

collectionNs = "http://www.loc.gov/MARC21/slim"

# Used when unpacking files
reGzippedFiles = re.compile('.+\.gz$')
reTarredFiles  = re.compile('.+\.tar$')

usageMsg  = f"""
Read Alma records and write them out formatted for the initial load for the 
SCSB project. Input, output and processed files are kept under {almaScsbDir}.
"""

# Check for any command line parameters
parser = argparse.ArgumentParser(description=usageMsg)
parser.add_argument("-v", "--verbose", action='store_true', help="Run with verbose output")
args = parser.parse_args()

verbose  = args.verbose
notifyJM = False

#
# Main program
#
def main():
	global notifyJM
	fileCountPass = 0
	fileCountFail = 0
	recordCount   = 0
	dateTimeStamp = get_date_time_stamp('day')

	# Logging will be done through notify()
	logFile = f'{logDir}/{jobCode}.{dateTimeStamp}'

	# Get a notify instance and let the Job Monitor know that the job started
	notifyJM = notify('log', jobCode, logFile)
	message = f'ReCAP SCSB xml started'
	notifyJM.report('start')
	
	# Find input files and parse xml
	try:
		os.chdir(almaScsbInDir)
	except:
		notifyJM.log('fail', f"Failed to change to the {almaScsbInDir} directory", verbose)
		notifyJM.report('stopped')
		quit()

	try:
		barcodes = []
		barcodeFile = glob(barcodeFileGlob)[0]
		with open(barcodeFile) as input:
			for line in input:
				if 'Barcode' in line:
					continue
				else:
					match = re.match('(\w+)', line)
					if match:
						barcodes.append(match[1])
	except:
		barcodes = False

	if barcodes:
		notifyJM.log('info', f'Using barcode file {barcodeFile}', verbose)
	
	for inputFile in (glob(inputFileGlob)):
		notifyJM.log('info', f'Start processing {inputFile}', verbose)
		inputFile = unpack_file(inputFile)
	
		# Start output file
		match = reInputFile1.match(inputFile)	
		if match:
			outputFile = f'{almaScsbOutDir}/initialAccessionHL_{match[2]}_{match[1]}.scsbxml'
		else:
			match = reInputFile2.match(inputFile)	
			if match:
				outputFile = f'{almaScsbOutDir}/initialAccessionHL_{match[1]}_{match[2]}.scsbxml'
			else:
				notifyJM.log('fail', f'{inputFile} is not named properly and will not be processed', verbose)
				continue
					
		try:
			output = open(outputFile, 'w')
			output.write('<bibRecords>\n')
		except:
			notifyJM.log('fail', f'Could not write {outputFile}', verbose)
			notifyJM.report('stopped')
			quit()
		
		for event, element in etree.iterparse(inputFile, events=('start', 'end'), tag=('record', 'leader', 'controlfield', 'datafield', 'subfield'), encoding='utf-8'):
		
			# Start events
			if event == 'start':

				# Clear variables at the start of a new record
				# and start a new bib record in the output xml
				if element.tag == 'record':
					mmsId        = ''
					datafield    = ''
					datafieldTag = ''
					df876sf9     = ''
					holdingsIds  = set()
					
					bibRecord     = etree.Element('bibRecord')
					bib           = etree.SubElement(bibRecord, 'bib')
					owningId      = etree.SubElement(bib, 'owningInstitutionId')
					owningId.text = 'HL'
					owningBibId   = etree.SubElement(bib, 'owningInstitutionBibId')
					bibContent    = etree.SubElement(bib, 'content')
					bibCollection = etree.SubElement(bibContent, 'collection')
					bibrecord     = etree.SubElement(bibCollection, 'record')
					holdings      = etree.SubElement(bibRecord, 'holdings')

				# Track which datafield that we're currently parsing
				elif element.tag == 'datafield':
					datafieldTag = element.attrib['tag']
					
					# Start a new holding tree for each 852 datafield
					if datafieldTag == '852':
						holding           = etree.SubElement(holdings, 'holding')
						owningHoldingId   = etree.SubElement(holding, 'owningInstitutionHoldingsId')
						holdingContent    = etree.SubElement(holding, 'content')
						holdingCollection = etree.SubElement(holdingContent, 'collection')
						holdingRecord     = etree.SubElement(holdingCollection, 'record')

						holdingItems    = etree.SubElement(holding, 'items')
						itemsContent    = etree.SubElement(holdingItems, 'content')
						etree.SubElement(itemsContent, 'collection')
					
			# End events
			else:
				# Handle leader and control fields
				if element.tag == 'controlfield' or element.tag == 'leader':
				
					# Get MMSID
					if element.tag == 'controlfield' and element.attrib['tag'] == '001':
						owningBibId.text = element.text
						mmsId = element.text

					# Copy element from source doc to target
					xmlfield = etree.SubElement(bibrecord, element.tag)
					
					for key in element.keys():
						xmlfield.attrib[key] = element.attrib[key]
						
					text = element.text
					if re.match('\w*', text):
						xmlfield.text = text
					
				# Handling datafields
				elif element.tag == 'datafield':

					# Holdings info
					if datafieldTag == '852':
						datafield = etree.SubElement(holdingRecord, 'datafield')
						
					# Items record, need to add it to the proper 
					# holding record using the ID in subfield 8
					elif datafieldTag == '876':
						subfieldXtext = ''
					
						for subfield in element.findall('subfield'):
							if subfield.attrib['code'] == '8':
								holdingIdItem = subfield.text
							elif subfield.attrib['code'] == 'p':
								barcodeItem = subfield.text
							elif subfield.attrib['code'] == '9':
								df876sf9 = subfield.text

						# Drop bib unless its barcode is on our list
						if barcodes:
							dropBib = True
							for barcode in barcodes:
								if barcode == barcodeItem:
									dropBib = False
									break
						else:
							dropBib = False
																
						if dropBib:
							continue
							
						for holding in holdings.findall('holding'):
							holdingId = holding.findtext('owningInstitutionHoldingsId')
							if holdingIdItem == holdingId:
								holdingsIds.add(holdingId)
								itemsCollection = holding.find('items').find('content').find('collection')
								break
						
						itemsRecord = etree.SubElement(itemsCollection, 'record')
						datafield   = etree.SubElement(itemsRecord, 'datafield')
					else:
						datafield = etree.SubElement(bibrecord, 'datafield')
					
					for key in element.keys():
						datafield.attrib[key] = element.attrib[key]
						
					text = element.text
					try:
						if re.match('\w*', text):
							datafield.text = text
					except:
						pass
											
					for subfieldIn in element:
						if subfieldIn.attrib['code'] == '8' and datafieldTag == '852':
							holdingId = subfieldIn.text
							owningHoldingId.text = holdingId

						# Needed Item's datafield/subfield a
						elif datafieldTag == '876':
							if subfieldIn.attrib['code'] == 'x':
								subfieldXtext = subfieldIn.text
					
						subfieldOut = etree.SubElement(datafield, 'subfield')
											
						for key in subfieldIn.keys():
							subfieldOut.attrib[key] = subfieldIn.attrib[key]
						
						text = subfieldIn.text
						if text:
							if re.match('\w*', text):
								subfieldOut.text = text
												
					# Add 900 datafield with subfields to items record
					if datafieldTag == '876':
						datafield = etree.SubElement(itemsRecord, 'datafield')
						datafield.attrib['tag'] = '900'
						datafield.attrib['ind1'] = '0'
						datafield.attrib['ind2'] = '0'
						subfield = etree.SubElement(datafield, 'subfield')
						subfield.attrib['code'] = 'a'
						
						if subfieldXtext == 'committed to retain - ReCAP':
							subfield.text = 'Shared'
						else:
							subfield.text = 'Private'
						
						subfield = etree.SubElement(datafield, 'subfield')
						subfield.attrib['code'] = 'b'
						subfield.text = df876sf9
						
					datafield  = None
					datafieldTag  = None

				# End of record
				elif element.tag == 'record':

					# Check for required elements
					if not mmsId:
						notifyJM.log('fail', "MMS ID not found for record number %s" % recordCount, verbose)
					if notifyJM.countFail > 0:
						notifyJM.report('stopped')
						fileCountFail += 1
						quit()
					
					# Drop any holding record if it doesn't have any items
					if holdingsIds:
						for holding in holdings.findall('holding'):
							holdingIdDoc = holding.find('owningInstitutionHoldingsId').text
							dropHolding = False

							for holdingIdRef in holdingsIds:
								if holdingIdRef == holdingIdDoc:
									dropHolding = False
									break
									
							if dropHolding:
								holdings.remove(holding)
							
					# Drop entire bib record if none of it holdings has items
					else:
						notifyJM.log('info', f'Bib {mmsId} will be dropped because none of its holdings had items', verbose)
						continue
						
					recordCount += 1

					# Finish bib record in output file
					bibRecord = etree.tostring(bibRecord,pretty_print=True, encoding='unicode')
					bibRecord = bibRecord.replace('<collection>', f'<collection xmlns="%s">' % collectionNs)
					output.write('%s' % bibRecord)
					
					# Clear record from memory
					element.clear()

		# Finish and close our xml output file
		output.write('</bibRecords>\n')
		output.close()

		# Move files after processing
		shutil.move(inputFile, f'{almaScsbProcessedDir}/{inputFile}')

		fileCountPass += 1
		notifyJM.log('pass', '%s records written to %s' % (recordCount, outputFile), verbose)
	
	# Move barcode file after processing
	if barcodes:
		shutil.move(barcodeFile, f'{almaScsbProcessedDir}/{barcodeFile}')

	# Clean-up and report results				
	if fileCountPass:
		notifyJM.log('pass', '%s files processed successfully' % fileCountPass, verbose)
	if fileCountFail:
		notifyJM.log('pass', '%s files processed with errors' % fileCountFail, verbose)
	if fileCountPass == 0 and fileCountFail == 0:
		notifyJM.log('warn', 'No files found in %s' % almaScsbInDir, verbose)
	notifyJM.report('complete')

#
# Sub-routines
#

# Unpack file
def unpack_file(file):
	global notifyJM
	zippedFile = False
	tarredFile = False
	
	# Ungzip if needed
	match = reGzippedFiles.match(file)
	if match:
		unzippedFile = file.replace('.gz', '')
		if not os.path.isfile(unzippedFile):
			notifyJM.log('info', f'Gunzipping {file}', verbose)				
			try:
				with gzip.open(file, 'rb') as fileIn:
					with open(unzippedFile, 'wb') as fileOut:
						shutil.copyfileobj(fileIn, fileOut)
			except:
				notifyJM.log('fail', "Gunzip of %s failed" % file, verbose)
				notifyJM.report('stopped')
				quit()
			
		zippedFile = file
		file       = unzippedFile

	# Extract tar archive if needed
	match = reTarredFiles.match(file)
	if match:
		untarredFile = file.replace('.tar', '')
		if not os.path.isfile(untarredFile):
			notifyJM.log('info', f'Untarring {file}', verbose)				
			try:
				tar = tarfile.open(file)
				tar.extractall()
				tar.close()
			except:
				notifyJM.log('fail', "Gunzip of %s failed" % file, verbose)
				notifyJM.report('stopped')
				quit()

		tarredFile = file
		file       = untarredFile				
	
	# Remove packed file if needed
	if zippedFile: os.remove(zippedFile)
	if tarredFile: os.remove(tarredFile)
	
	return file

if __name__ == "__main__":
    main()
