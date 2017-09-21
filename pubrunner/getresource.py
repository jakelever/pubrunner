
import pubrunner
import sys
import argparse
import os
import git
import tempfile
import shutil
import logging
import traceback
import yaml
import json
import subprocess
import shlex
import wget
import gzip
import hashlib
import six
import six.moves.urllib as urllib
import time
from six.moves import reload_module
import ftplib
import ftputil
from collections import OrderedDict
import re

def calcSHA256(filename):
	return hashlib.sha256(open(filename, 'rb').read()).hexdigest()

def calcSHA256forDir(directory):
	sha256s = {}
	for filename in os.listdir(directory):
		sha256 = calcSHA256(os.path.join(directory,filename))
		sha256s[filename] = sha256
	return sha256s

def download(url,out):
	if url.startswith('ftp'):
		url = url.replace("ftp://","")
		hostname = url.split('/')[0]
		path = "/".join(url.split('/')[1:])
		with ftputil.FTPHost(hostname, 'anonymous', 'secret') as host:
			downloadFTP(path,out,host)
	elif url.startswith('http'):
		downloadHTTP(url,out)
	else:
		raise RuntimeError("Unsure how to download file. Expecting URL to start with ftp or http. Got: %s" % url)

def downloadFTP(path,out,host):
	if host.path.isfile(path):
		remoteTimestamp = host.path.getmtime(path)
		
		doDownload = True
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
			print("\tDownloading %s" % path)
			didDownload = host.download(path,out)
			os.utime(out,(remoteTimestamp,remoteTimestamp))
		else:
			print("\tSkipping %s" % path)

	elif host.path.isdir(path):
		basename = host.path.basename(path)
		newOut = os.path.join(out,basename)
		if not os.path.isdir(newOut):
			os.makedirs(newOut)
		for child in host.listdir(path):
			srcFilename = host.path.join(path,child)
			dstFilename = os.path.join(newOut,child)
			downloadFTP(srcFilename,dstFilename,host)
	else:
		raise RuntimeError("Path (%s) is not a file or directory" % path) 

def downloadHTTP(url,out):
	fileAlreadyExists = os.path.isfile(out)

	if fileAlreadyExists:
		timestamp = os.path.getmtime(source)
		beforeHash = calcSHA256(out)
		os.unlink(out)

	wget.download(url,out,bar=None)
	if fileAlreadyExists:
		afterHash = calcSHA256(out)
		if beforeHash == afterHash: # File's haven't changed to move the modified date back
			os.utime(out,(timestamp,timestamp))

def gunzip(source,dest,deleteSource=False):
	timestamp = os.path.getmtime(source)
	with gzip.open(source, 'rb') as f_in, open(dest, 'wb') as f_out:
		shutil.copyfileobj(f_in, f_out)
	os.utime(dest,(timestamp,timestamp))

	if deleteSource:
		os.unlink(source)
	

def getResource(resource):
	print("Fetching resource: %s" % resource)

	globalSettings = pubrunner.getGlobalSettings()
	resourceDir = os.path.expanduser(globalSettings["storage"]["resources"])
	thisResourceDir = os.path.join(resourceDir,resource)

	packagePath = os.path.dirname(pubrunner.__file__)
	resourceYamlPath = os.path.join(packagePath,'resources','%s.yml' % resource)
	assert os.path.isfile(resourceYamlPath), "Can not find appropriate file for resource: %s" % resource

	with open(resourceYamlPath) as f:
		resourceInfo = yaml.load(f)

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
		return thisResourceDir
	elif resourceInfo['type'] == 'dir':
		assert isinstance(resourceInfo['url'], six.string_types) or isinstance(resourceInfo['url'],list), 'The URL for a dir resource must be a single or multiple addresses'
		if isinstance(resourceInfo['url'], six.string_types):
			urls = [resourceInfo['url']]
		else:
			urls = resourceInfo['url']

		if os.path.isdir(thisResourceDir):
			for url in urls:
				basename = url.split('/')[-1]
				assert isinstance(url,six.string_types), 'Each URL for the dir resource must be a string'
				download(url,os.path.join(thisResourceDir,basename))
		else:
			os.makedirs(thisResourceDir)
			for url in urls:
				basename = url.split('/')[-1]
				assert isinstance(url,six.string_types), 'Each URL for the dir resource must be a string'
				download(url,os.path.join(thisResourceDir,basename))
		
		if 'unzip' in resourceInfo and resourceInfo['unzip'] == True:
			for filename in os.listdir(thisResourceDir):
				if filename.endswith('.gz'):
					unzippedName = filename[:-3]
					gunzip(os.path.join(thisResourceDir,filename), os.path.join(thisResourceDir,unzippedName), deleteSource=True)

		return thisResourceDir
	else:
		raise RuntimeError("Unknown resource type (%s) for resource: %s" % (resourceInfo['type'],resource))
