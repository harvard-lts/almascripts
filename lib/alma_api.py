# Use this class for working with the Alma's API
#
# Initial version 03/26/19 TME
# Last updated 09/16/22 TME

import os, sys, re
from time import sleep
from requests import Session
from almatools import urlAlmaApi, urlBarcodeApi, urlBibsApi, urlJobsApi, apiKeyBibsRw

class api_session(Session):

	def __init__(self, sessionType, apiKey = False):

		if sessionType == 'json' or sessionType == 'xml':
			super().__init__()
			self.sessionType    = sessionType
			self.apiKey         = apiKey
			self.startSession()
			self.connectTimeOut = 5
			self.readTimeOut    = 60
			self.maxTries       = 3
			self.urlRequest     = False 
		else:
			self.msgFail = 'Session type %s is not supported' % sessionType
			return None
	
	# Start Http session
	def startSession(self):
	
		if self.sessionType == 'json':
			headers = {
			           'Content-type': 'application/json',
			           'accept': 'application/json'
			           }
		elif self.sessionType == 'xml':
			headers = {
			           'Content-type': 'application/xml',
			           'accept': 'application/xml'
			           }
	
		self.headers.update(headers)
		self.sessionAlive = True

		if self.apiKey:
			self.headers.update({'authorization': 'apikey {}'.format(self.apiKey)})
			
		return self

	# Start Http session
	def stopSession(self):	
		self.headers.update({'Connection':'close'})
		return self

	# Make Alma's API request. Multiple attempts will be made if needed.
	def api_request(self, method, url, data = False):
		self.attempts = 1
		self.text     = False

		for loopCount in range(1, (self.maxTries + 1)):
			try:
				if method == 'post':
					if data:
						response = self.post(url, data = data, timeout = (self.connectTimeOut, self.readTimeOut))
					else:
						response = self.post(url, timeout = (self.connectTimeOut, self.readTimeOut))
						
				elif method == 'put':
					if data:
						response = self.put(url, data = data, timeout = (self.connectTimeOut, self.readTimeOut))
					else:
						response = self.put(url, timeout = (self.connectTimeOut, self.readTimeOut))
						
				elif method == 'get':
					response = self.get(url, timeout = (self.connectTimeOut, self.readTimeOut))

				elif method == 'delete':
					response = self.delete(url, timeout = (self.connectTimeOut, self.readTimeOut))

				else:
					self.error = 'Http method %s is not supported' % method
					return None
						
				self.statusCode = response.status_code
				self.text       = response.text
	
				if self.statusCode == 200:
					self.error = False
					break
				# Try to capture errors
				else:
					returnedMsg = response.text.replace('\n', ' ')
					match = re.match('.*<errorMessage>(.+)</errorMessage>.*', returnedMsg)
					if match == None:
						match = re.match('.*"errorMessage":"(.+)",.*', returnedMsg)
						if match == None:
							self.error = response.text
						else:
							self.error = match.group(1)
					else:
						self.error = match.group(1)
			
			except Exception as e:
				self.error = e

			# If API calls fails, restart session, increment attempts, and then wait
			self.stopSession()
			sleep((loopCount * 10))
			self.startSession()
			self.attempts += 1
				
	# Get Bib record
	def get_bib(self, mmsId):
		self.apiKey = apiKeyBibsRw
		self.urlRequest = f'{urlBibsApi}{mmsId}'
		self.api_request('get', self.urlRequest)
		
	# Update Bib record
	def update_bib(self, mmsId, data):
		self.apiKey = apiKeyBibsRw
		self.urlRequest = f'{urlBibsApi}{mmsId}'
		self.api_request('put', self.urlRequest, data)
	
	# Get holdings record
	def get_holdings(self, mmsId, holdingsId):
		self.apiKey = apiKeyBibsRw
		self.urlRequest = f'{urlAlmaApi}bibs/{mmsId}/holdings/{holdingsId}'
		self.api_request('get', self.urlRequest)
		
	# Update holdings record
	def update_holdings(self, mmsId, holdingsId, data):
		self.apiKey = apiKeyBibsRw
		self.urlRequest = f'{urlAlmaApi}bibs/{mmsId}/holdings/{holdingsId}'
		self.api_request('put', self.urlRequest, data)
	
	# Get holdings, bib and item by Barcode Item
	def lookup_by_barcode(self, barcode):
		self.apiKey = apiKeyBibsRw
		self.urlRequest = f'{urlBarcodeApi}{barcode}'
		self.api_request('get', self.urlRequest)
				
	# Get Item record. Get as xml.
	def get_item(self, mmsId, holdingId, itemPid):
		self.apiKey = apiKeyBibsRw
		self.urlRequest = f'{urlBibsApi}{mmsId}/holdings/{holdingId}/items/{itemPid}'
		self.urlRequest = f'{urlBibsApi}{mmsId}'
		self.api_request('get', self.urlRequest)

	# Start Alma job
	def start_job(self, jobId):
		jobPayload = "<?xml version='1.0' encoding='utf-8'?>\n<job/>"
		urlRequest = urlJobsApi.format(job_id = jobId)
		self.api_request('post', urlRequest, data = jobPayload)
