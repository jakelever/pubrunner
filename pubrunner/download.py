
import os
import git
import shutil
import yaml
import wget
import gzip
import hashlib
import six
import ftputil
import tarfile
import glob
import json
import requests
import datetime
import time
import re

def calcSHA256(filename):
	return hashlib.sha256(open(filename, 'rb').read()).hexdigest()

def checkFileSuffixFilter(filename,fileSuffixFilter):
	if fileSuffixFilter is None:
		return True
	elif filename.endswith('.tar.gz') or filename.endswith('.gz'):
		return True
	elif filename.endswith(fileSuffixFilter):
		return True
	else:
	 	return False

def download(url,out,fileSuffixFilter=None):
	if url.startswith('ftp'):
		url = url.replace("ftp://","")
		hostname = url.split('/')[0]
		path = "/".join(url.split('/')[1:])
		host = ftputil.FTPHost(hostname, 'anonymous', 'secret')
		downloadFTP(path,out,host,fileSuffixFilter)
		host.close()
	elif url.startswith('http'):
		downloadHTTP(url,out,fileSuffixFilter)
	else:
		raise RuntimeError("Unsure how to download file. Expecting URL to start with ftp or http. Got: %s" % url)

def downloadFTP(path,out,host,fileSuffixFilter=None,tries=5):
	for _ in range(tries):
		try:
			if host.path.isfile(path):
				remoteTimestamp = host.path.getmtime(path)
				
				doDownload = True
				if not checkFileSuffixFilter(path,fileSuffixFilter):
					doDownload = False

				if os.path.isdir(out):
					localTimestamp = os.path.getmtime(out)
					if not remoteTimestamp > localTimestamp:
						doDownload = False
				if path.endswith('.gz'):
					outUnzipped = out[:-3]
					if os.path.isfile(outUnzipped):
						localTimestamp = os.path.getmtime(outUnzipped)
						if not remoteTimestamp > localTimestamp:
							doDownload = False
				if doDownload:
					print("  Downloading %s" % path)
					host.download(path,out)
					os.utime(out,(remoteTimestamp,remoteTimestamp))
				else:
					print("  Skipping %s" % path)

			elif host.path.isdir(path):
				basename = host.path.basename(path)
				newOut = os.path.join(out,basename)
				if not os.path.isdir(newOut):
					os.makedirs(newOut)
				for child in host.listdir(path):
					srcFilename = host.path.join(path,child)
					dstFilename = os.path.join(newOut,child)
					downloadFTP(srcFilename,dstFilename,host,fileSuffixFilter)
			else:
				raise RuntimeError("Path (%s) is not a file or directory" % path) 

			break
		except ftputil.error.FTPOSError as e:
			errinfo = str(e.errno) + ' ' + str(e.strerror)
			print("Try %d for %s : Received FTPOSError(%s)" % (tryNo+1,path,errinfo))
			time.sleep(1)
			host = ftputil.FTPHost(hostname, 'anonymous', 'secret')

def downloadHTTP(url,out,fileSuffixFilter=None):
	if not checkFileSuffixFilter(url,fileSuffixFilter):
		return

	fileAlreadyExists = os.path.isfile(out)

	if fileAlreadyExists:
		timestamp = os.path.getmtime(out)
		beforeHash = calcSHA256(out)
		os.unlink(out)

	wget.download(url,out,bar=None)
	if fileAlreadyExists:
		afterHash = calcSHA256(out)
		if beforeHash == afterHash: # File hasn't changed so move the modified date back
			os.utime(out,(timestamp,timestamp))

def downloadZenodo(recordNumber,outputDirectory):
	assert isinstance(recordNumber,int)

	if not os.path.isdir(outputDirectory):
		os.makedirs(outputDirectory)

	ZENODO_URL = 'https://zenodo.org'
	
	headers = {"Content-Type": "application/json"}
	r = requests.get(ZENODO_URL + '/api/records/%d' % recordNumber, json={}, headers=headers)

	assert r.status_code == 200, 'Unable to download Zenodo record %d' % recordNumber

	jsonResponse = r.json()

	updated = jsonResponse['updated']
	updated = re.sub(':00$','00',updated)

	updated_datetime = datetime.datetime.strptime(updated, "%Y-%m-%dT%H:%M:%S.%f%z")
	timestamp = time.mktime(updated_datetime.timetuple())

	for f in jsonResponse['files']:
		url = f['links']['self']
		name = f['key']
		out = os.path.join(outputDirectory,name)

		doDownload = (not os.path.isfile(out)) or os.path.getmtime(out) < timestamp

		if doDownload:
			download(url,out)
			os.utime(out,(timestamp,timestamp))

def gunzip(source,dest,deleteSource=False):
	timestamp = os.path.getmtime(source)
	with gzip.open(source, 'rb') as f_in, open(dest, 'wb') as f_out:
		shutil.copyfileobj(f_in, f_out)
	os.utime(dest,(timestamp,timestamp))

	if deleteSource:
		os.unlink(source)
