
import pubrunner
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
		with ftputil.FTPHost(hostname, 'anonymous', 'secret') as host:
			downloadFTP(path,out,host,fileSuffixFilter)
	elif url.startswith('http'):
		downloadHTTP(url,out,fileSuffixFilter)
	else:
		raise RuntimeError("Unsure how to download file. Expecting URL to start with ftp or http. Got: %s" % url)

def downloadFTP(path,out,host,fileSuffixFilter=None,tries=5):
	for tryNo in range(tries):
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

def downloadHTTP(url,out,fileSuffixFilter=None):
	if not checkFileSuffixFilter(url,fileSuffixFilter):
		return

	fileAlreadyExists = os.path.isfile(out)

	if fileAlreadyExists:
		timestamp = os.path.getmtime(out)
		beforeHash = pubrunner.calcSHA256(out)
		os.unlink(out)

	wget.download(url,out,bar=None)
	if fileAlreadyExists:
		afterHash = pubrunner.calcSHA256(out)
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
	
# https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in range(0, len(l), n):
		yield l[i:i + n]


def generatePubmedHashes(inDir,outDir):
	snakeFile = os.path.join(pubrunner.__path__[0],'Snakefiles','PubmedHashes.py')
	parameters = {'INDIR':inDir,'OUTDIR':outDir}
	pubrunner.launchSnakemake(snakeFile,parameters=parameters)
	
def getResourceInfo(resource):
	packagePath = os.path.dirname(pubrunner.__file__)
	pubrunnerResourcePath = os.path.join(packagePath,'resources','%s.yml' % resource)
	projectResourcePath = os.path.join('resources','%s.yml' % resource)

	options = [pubrunnerResourcePath,projectResourcePath]
	for option in options:
		if os.path.isfile(option):
			with open(option) as f:
				resourceInfo = yaml.load(f)
			return resourceInfo

	raise RuntimeError("Unable to find resource YAML file for resource: %s" % resource)

def generateFileListing(thisResourceDir):
	listing = glob.glob(thisResourceDir + '/**',recursive=True)
	with open(thisResourceDir + '.listing.json','w') as f:
		json.dump(listing,f)

def getResource(resource):
	print("Fetching resource: %s" % resource)

	globalSettings = pubrunner.getGlobalSettings()
	resourceDir = os.path.expanduser(globalSettings["storage"]["resources"])
	thisResourceDir = os.path.join(resourceDir,resource)

	resourceInfo = getResourceInfo(resource)
	#print(json.dumps(resourceInfo,indent=2))

	if resourceInfo['type'] == 'git':
		assert isinstance(resourceInfo['url'], six.string_types), 'The URL for a git resource must be a single address'

		if os.path.isdir(thisResourceDir):
			# Assume it is an existing git repo
			repo = git.Repo(thisResourceDir)
			repo.remote().pull()
		else:
			os.makedirs(thisResourceDir)
			git.Repo.clone_from(resourceInfo["url"], thisResourceDir)
		
		#generateFileListing(thisResourceDir)

		return thisResourceDir
	elif resourceInfo['type'] == 'zenodo':
		assert isinstance(resourceInfo['record'], int), 'The Zenodo record must be an integer'

		print("  Starting Zenodo download...")
		downloadZenodo(resourceInfo['record'],thisResourceDir)

		return thisResourceDir
	elif resourceInfo['type'] == 'remote':
		assert isinstance(resourceInfo['url'], six.string_types) or isinstance(resourceInfo['url'],list), 'The URL for a remote resource must be a single or multiple addresses'
		if isinstance(resourceInfo['url'], six.string_types):
			urls = [resourceInfo['url']]
		else:
			urls = resourceInfo['url']
		
		if 'filter' in resourceInfo:
			fileSuffixFilter = resourceInfo['filter']
		else:
			fileSuffixFilter = None

		if not os.path.isdir(thisResourceDir):
			print("  Creating directory...")
			os.makedirs(thisResourceDir)

		print("  Starting download...")
		for url in urls:
			basename = url.split('/')[-1]
			assert isinstance(url,six.string_types), 'Each URL for the dir resource must be a string'
			download(url,os.path.join(thisResourceDir,basename),fileSuffixFilter)

		if 'unzip' in resourceInfo and resourceInfo['unzip'] == True:
			print("  Unzipping archives...")
			for filename in os.listdir(thisResourceDir):
				if filename.endswith('.tar.gz') or filename.endswith('.tgz'):
					tar = tarfile.open(os.path.join(thisResourceDir,filename), "r:gz")
					tar.extractall(thisResourceDir)
					tar.close()
				elif filename.endswith('.gz'):
					unzippedName = filename[:-3]
					gunzip(os.path.join(thisResourceDir,filename), os.path.join(thisResourceDir,unzippedName), deleteSource=True)

		if not fileSuffixFilter is None:
			print("  Removing files not matching filter (%s)..." % fileSuffixFilter)
			for root, subdirs, files in os.walk(thisResourceDir):
				for f in files:
					if not f.endswith(fileSuffixFilter):
						fullpath = os.path.join(root,f)
						os.unlink(fullpath)

		if 'generatePubmedHashes' in resourceInfo and resourceInfo['generatePubmedHashes'] == True:
			print("  Generating Pubmed hashes...")
			hashDir = os.path.join(resourceDir,resource+'.hashes')
			if not os.path.isdir(hashDir):
				os.makedirs(hashDir)

			generatePubmedHashes(thisResourceDir,hashDir)

		#generateFileListing(thisResourceDir)

		return thisResourceDir
	elif resourceInfo['type'] == 'local':
		assert isinstance(resourceInfo['directory'], six.string_types) and os.path.isdir(resourceInfo['directory']), 'The directory for a remote resource must be a string and exist'

		if not os.path.islink(thisResourceDir) and os.path.isdir(thisResourceDir):
			shutil.rmtree(thisResourceDir)

		if not os.path.islink(thisResourceDir):
			os.symlink(resourceInfo['directory'],thisResourceDir)
	else:
		raise RuntimeError("Unknown resource type (%s) for resource: %s" % (resourceInfo['type'],resource))
