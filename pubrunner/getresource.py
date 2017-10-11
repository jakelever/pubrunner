
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
import math

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
	
# https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in range(0, len(l), n):
		yield l[i:i + n]

def generatePubmedHashes(inDir,outDir):
	
	#inDir = 'PUBMED'
	#outDir = 'PUBMED.hashes'

	templateCommand = "'pubmed_hash --pubmedXMLFiles INFILE --outHashJSON OUTFILE'"
	templateOutFile = '%s/hashes.GROUPNO' % outDir

	ruleTxt = "rule RULE_GROUPNO:\n"
	ruleTxt += "\tinput:\n"
	ruleTxt += "\t\tINPUTS\n"
	ruleTxt += "\toutput:\n"
	#ruleTxt += "\t\t'%s'\n" % templateOutFile.replace("'","\\'")
	ruleTxt += "\t\tOUTPUTS\n"
	ruleTxt += "\tshell:\n"
	#ruleTxt += "\t\t'%s'\n" % templateCommand.replace("'","\\'")
	ruleTxt += "\t\tCOMMANDS\n"

	allRules = []

	expectedOutfiles = []

	files = sorted([ os.path.join(inDir,f) for f in os.listdir(inDir) ])
	chunkSize = int(math.ceil(len(files) / 100))
	for groupNo,group in enumerate(chunks(files,chunkSize)):
		inputFiles,outputFiles,commands = [],[],[]
		for fileNo,filename in enumerate(group):
			outFile = "%s.json" % os.path.join(outDir,os.path.basename(filename))
			inputFiles.append("IN%04d='%s'" % (fileNo,filename))
			outputFiles.append("OUT%04d='%s'" % (fileNo,outFile))
			expectedOutfiles.append(outFile)
			
			command = templateCommand
			command = command.replace("INFILE",'{input.IN%04d}' % fileNo)
			command = command.replace("OUTFILE",'{output.OUT%04d}' % fileNo)
			commands.append(command)
			
		inputFilesTxt = ',\n\t\t'.join(inputFiles)
		outputFilesTxt = ',\n\t\t'.join(outputFiles)
		commandsTxt = ',\n\t\t'.join(commands)
		
		thisRule = ruleTxt
		thisRule = thisRule.replace('GROUPNO',"%04d" % groupNo)
		thisRule = thisRule.replace('INPUTS',inputFilesTxt)
		thisRule = thisRule.replace('OUTPUTS',outputFilesTxt)
		thisRule = thisRule.replace('COMMANDS',commandsTxt)

		#allOutputFiles.append(templateOutFile.replace('GROUPNO',"%04d" % groupNo))
		allRules.append(thisRule)
		#break

	masterRule = "rule RULE_ALL:\n"
	masterRule += "\tinput:\n"
	masterRule += "\t\tALL_OUTPUT_FILES\n"
	ALL_OUTPUT_FILES = ',\n\t\t'.join( [ "'%s'" % f for f in expectedOutfiles ] )
	masterRule = masterRule.replace('ALL_OUTPUT_FILES', ALL_OUTPUT_FILES)

	allRules = [masterRule] + allRules

	snakeFilePath = 'tmpSnakeFile'
	with open(snakeFilePath,'w') as f:
		for r in allRules:
			f.write(r)
			f.write("\n\n")

	globalSettings = pubrunner.getGlobalSettings()
	
	clusterFlags = ""
	if False and "cluster" in globalSettings:
		assert "options" in globalSettings["cluster"], "Options must also be provided in the cluster settings, e.g. qsub"
		jobs = 1
		if "jobs" in globalSettings["cluster"]:
			jobs = int(globalSettings["cluster"]["jobs"])
		clusterFlags = "--cluster '%s' --jobs %d --latency-wait 60" % (globalSettings["cluster"]["options"],jobs)

	print("\nRunning pubmed_hash commands")
	makecommand = "snakemake %s -s %s" % (clusterFlags,snakeFilePath)

	retval = subprocess.call(shlex.split(makecommand))
	if retval != 0:
		raise RuntimeError("Snake make call FAILED for command: %s . (file:%s)" % (command,snakeFilePath))
	


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
		
		if 'generatePubmedHashes' in resourceInfo and resourceInfo['generatePubmedHashes'] == True:
			hashDir = os.path.join(resourceDir,'pubmedHashes',resource)
			if not os.path.isdir(hashDir):
				os.makedirs(hashDir)

			snakefile = thisResourceDir + ".hashes.SnakeFile"
			generatePubmedHashes(thisResourceDir,hashDir)
			print("Generated")

		return thisResourceDir
	else:
		raise RuntimeError("Unknown resource type (%s) for resource: %s" % (resourceInfo['type'],resource))
