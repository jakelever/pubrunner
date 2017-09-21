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
import glob
import requests
import datetime


def extractVariables(command):
	assert isinstance(command,six.string_types)
	#regex = re.compile("\?[A-Za-z_0-9]*")
	regex = re.compile("\{\S*\}")
	variables = []
	for m in regex.finditer(command):
		var = ( m.start(), m.end(), m.group()[1:-1] )
		variables.append(var)
	variables = sorted(variables,reverse=True)
	return variables


def getResourceLocation(resource):
	globalSettings = pubrunner.getGlobalSettings()
	resourceDir = os.path.expanduser(globalSettings["storage"]["resources"])
	thisResourceDir = os.path.join(resourceDir,resource)
	return thisResourceDir

def getResourceInfo(resource):
	packagePath = os.path.dirname(pubrunner.__file__)
	resourceYamlPath = os.path.join(packagePath,'resources','%s.yml' % resource)
	with open(resourceYamlPath) as f:
		resourceInfo = yaml.load(f)

	return resourceInfo

def makeLocation(toolname,name,mode,createDir=False):
	globalSettings = pubrunner.getGlobalSettings()
	workspaceDir = os.path.expanduser(globalSettings["storage"]["workspace"])
	thisDir = os.path.join(workspaceDir,toolname,name)
	thisDir = os.path.join(workspaceDir,toolname,mode,name)
	if createDir and not os.path.isdir(thisDir):
		os.makedirs(thisDir)
	return thisDir

def processResourceSettings(toolSettings,mode):
	toolName = toolSettings['name']
	locationMap = {}

	newResourceList = []
	preprocessingCommands = []
	for resourceGroupName in ["all",mode]:
		for resName in toolSettings["resources"][resourceGroupName]:
			if isinstance(resName,dict):
				print(resName)
				assert len(resName.items()) == 1

				# TODO: Rename resSettings and resInfo to be more meaningful
				resName,resSettings = list(resName.items())[0]
				resInfo = getResourceInfo(resName)

				allowed = ['rename','format']
				for k in resSettings.keys():
					assert k in allowed, "Unexpected attribute (%s) for resource %s" % (k,resName)

				nameToUse = resName
				if "rename" in resSettings:
					nameToUse = resSettings["rename"]

				if "format" in resSettings:
					inDir = nameToUse + "_UNCONVERTED"
					inFormat = resInfo["format"]
					inFilter = resInfo["filter"]
					outDir = nameToUse
					outFormat = resSettings["format"]

					command = "pubrunner_convert --i {IN:%s/*%s} --iFormat %s --o {OUT:%s/*%s} --oFormat %s" % (inDir,inFilter,inFormat,outDir,inFilter,outFormat)
					preprocessingCommands.append( command )

					locationMap[nameToUse+"_UNCONVERTED"] = getResourceLocation(resName)
					locationMap[nameToUse] = makeLocation(toolName,resName+"_CONVERTED",mode)
				else:
					locationMap[nameToUse] = getResourceLocation(resName)
					

				newResourceList.append(resName)
			else:
				locationMap[resName] = getResourceLocation(resName)
				newResourceList.append(resName)

	toolSettings["resources"] = newResourceList

	toolSettings["build"] = preprocessingCommands + toolSettings["build"]
	return locationMap

def commandToSnakeMake(toolName,ruleName,command,locationMap,mode):
	variables = extractVariables(command)

	inputs = []
	outputs = []
	dirsToTouch = []
	newCommand = command

	firstInputPattern,firstOutputPattern = None,None
	hasWildcard = False
	hasIn = False

	for startPos,endPos,var in variables:
		#isIn = var.startswith('IN:')
		#isOut = var.startswith('OUT:')
		#assert isIn or isOut
		#split = var.split(':')
		#asset len(split) == 2
		#var = split[1]

		#m = re.match("IN:[A-Za-z0-9.]*", var)
		m = re.match("(?P<vartype>IN|OUT):(?P<varname>[A-Za-z0-9_\.]*)(/(?P<pattern>[A-Za-z0-9_\.\*]*))?", var)
		if not m:
			raise RuntimeError("Unable to parse variable: %s" % var)
		mDict = m.groupdict()
		vartype = mDict['vartype']
		varname = mDict['varname']
		pattern = mDict['pattern'] if 'pattern' in mDict else None

		assert var.count('*') <= 1, "Cannot have more than one wildcard in variable: %s" % var

		if not varname in locationMap:
			locationMap[varname] = makeLocation(toolName,varname,mode)
		loc = locationMap[varname]
		loc = os.path.relpath(loc)

		if pattern:
			hasWildcard = True

		repname = varname + str(startPos)
		repname = repname.replace('.','_')
		if vartype == 'IN' and not pattern:
			inputs.append((repname,loc))
			hasIn = True
		elif vartype == 'OUT' and not pattern:
			if not firstOutputPattern:
				firstOutputPattern = loc

			outputs.append((repname,loc))
			dirsToTouch.append(loc)
		elif vartype == 'IN' and pattern:
			if not firstInputPattern:
				firstInputPattern = loc + '/' + pattern

			snakepattern = loc + '/' + pattern.replace('*','{f}')
			inputs.append((repname,snakepattern))
			hasIn = True
		elif vartype == 'OUT' and pattern:
			if not firstOutputPattern:
				firstOutputPattern = loc + '/' + pattern

			# Make sure the directory is created
			makeLocation(toolName,varname,mode,createDir=True)

			snakepattern = loc + '/' + pattern.replace('*','{f}')
			outputs.append((repname,snakepattern))
			dirsToTouch.append(loc)

		if vartype == 'IN':
			newCommand = newCommand[:startPos] + '{input.%s}' % repname + newCommand[endPos:]
		elif vartype == 'OUT':
			newCommand = newCommand[:startPos] + '{output.%s}' % repname + newCommand[endPos:]

	
	ruleTxt = ""
	
	ruleTxt += "\n"
	if hasWildcard:
		ruleTxt += "%s_EXPECTED_FILES = predictOutputFiles('%s','%s')\n" % (ruleName,firstInputPattern,firstOutputPattern)
	else:
		ruleTxt += "%s_EXPECTED_FILES = ['%s']\n" % (ruleName,firstOutputPattern)
	ruleTxt += "rule %s:\n" % ruleName

	if hasIn:
		ruleTxt += "\tinput: %s_EXPECTED_FILES\n" % ruleName

		ruleTxt += "rule %s_ACTIONS:\n" % ruleName
		ruleTxt += "\tinput:\n"
		#ruleTxt += "\t\tINPUTS\n"
		for i,(name,pattern) in enumerate(inputs):
			comma = "" if i+1 == len(inputs) else ","
			ruleTxt += "\t\t%s='%s'%s\n" % (name,pattern,comma)
		ruleTxt += "\toutput:\n"
		#ruleTxt += "\t\tOUTPUTS\n"
		for i,(name,pattern) in enumerate(outputs):
			comma = "" if i+1 == len(outputs) else ","
			ruleTxt += "\t\t%s='%s'%s\n" % (name,pattern,comma)

	ruleTxt += "\tshell:\n"
	ruleTxt += '\t\t"""\n'
	ruleTxt += "\t\t%s\n" % newCommand
	for dirToTouch in dirsToTouch:
		ruleTxt += "\t\ttouch %s\n" % dirToTouch
	ruleTxt += '\t\t"""\n'


	return ruleTxt

def generateGetResourceSnakeRule(resources):
	ruleTxt = 'rule getResources:\n'
	ruleTxt += '\tshell:\n'
	ruleTxt += '\t\t"""\n'
	for resource in resources:
		ruleTxt += '\t\t pubrunner --getResource %s\n' % resource 
	ruleTxt += '\t\t"""\n\n'
	return ruleTxt


def pubrun(directory,doTest,execute=False):
	mode = "test" if doTest else "main"

	globalSettings = pubrunner.getGlobalSettings()

	os.chdir(directory)

	toolYamlFile = 'pubrunner.yml'
	if not os.path.isfile(toolYamlFile):
		raise RuntimeError("Expected a %s file in root of codebase" % toolYamlFile)

	toolSettings = pubrunner.loadYAML(toolYamlFile)
	toolName = toolSettings["name"]
	
	if not "build" in toolSettings:
		toolSettings["build"] = []
	if not "all" in toolSettings["resources"]:
		toolSettings["resources"]["all"] = []
	if not mode in toolSettings["resources"]:
		toolSettings["resources"][mode] = []

	locationMap = processResourceSettings(toolSettings,mode)

	with open(os.path.join(os.path.dirname(__file__),'Snakefile.header')) as f:
		snakefileHeader = f.read()

	ruleDir = '.pubrunner'
	if not os.path.isdir(ruleDir):
		os.makedirs(ruleDir)

	print("Building Snakefile")

	with open(os.path.join(ruleDir,'Snakefile.resources'),'w') as f:
		resourcesSnakeRule = generateGetResourceSnakeRule(toolSettings["resources"])
		f.write(resourcesSnakeRule)


	commandExecutionList = []
	for commandGroup in ["build","run"]:
		for i,command in enumerate(toolSettings[commandGroup]):
			snakeFilePath = os.path.join(ruleDir,'Snakefile.%s_%d' % (commandGroup,i+1))
			commandExecutionList.append((commandGroup=="run",snakeFilePath,command))
			with open(snakeFilePath,'w') as f:
				ruleName = "RULE_%d" % (i+1)
				snakecode = commandToSnakeMake(toolName, ruleName, command, locationMap, mode)
				f.write(snakefileHeader)
				f.write(snakecode + "\n")
	print("Completed Snakefile")

	if execute:
		snakeFilePath = os.path.join(ruleDir,'Snakefile.resources')
		print("\nRunning command to fetch resourcess")
		makecommand = "snakemake -s %s" % (snakeFilePath)
		retval = subprocess.call(shlex.split(makecommand))
		if retval != 0:
			raise RuntimeError("Snake make call FAILED for get resources")


		clusterFlags = ""
		if "cluster" in globalSettings:
			assert "options" in globalSettings["cluster"], "Options must also be provided in the cluster settings, e.g. qsub"
			jobs = 1
			if "jobs" in globalSettings["cluster"]:
				jobs = int(globalSettings["cluster"]["jobs"])
			clusterFlags = "--cluster '%s' --jobs %d --latency-wait 60" % (globalSettings["cluster"]["options"],jobs)

		for i,(isRunCommand,snakeFilePath,command) in enumerate(commandExecutionList):
			print("\nRunning command %d: %s" % (i+1,command))
			if isRunCommand:
				makecommand = "snakemake %s -s %s" % (clusterFlags,snakeFilePath)
			else:
				makecommand = "snakemake -s %s" % (snakeFilePath)

			retval = subprocess.call(shlex.split(makecommand))
			if retval != 0:
				raise RuntimeError("Snake make call FAILED for command: %s . (file:%s)" % (command,snakeFilePath))
		print("")

		if "output" in toolSettings and mode != 'test':
			outputList = toolSettings["output"]
			if not isinstance(outputList,list):
				outputList = [outputList]

			outputLocList = [ locationMap[o] for o in outputList ]

			dataurl = None
			if "upload" in globalSettings:
				if "ftp" in globalSettings["upload"]:
					print("Uploading results to FTP")
					pubrunner.pushToFTP(outputLocList,toolSettings,globalSettings)
				if "local-directory" in globalSettings["upload"]:
					print("Uploading results to local directory")
					pubrunner.pushToLocalDirectory(outputLocList,toolSettings,globalSettings)
				if "zenodo" in globalSettings["upload"]:
					print("Uploading results to Zenodo")
					dataurl = pubrunner.pushToZenodo(outputLocList,toolSettings,globalSettings)

			if "website-update" in globalSettings and toolName in globalSettings["website-update"]:
				assert not dataurl is None, "Don't have URL to update website with"
				websiteToken = globalSettings["website-update"][toolName]
				print("Sending update to website")
				
				headers = {'User-Agent': 'Pubrunner Agent', 'From': 'no-reply@pubrunner.org'  }
				today = datetime.datetime.now().strftime("%m-%d-%Y")	
				updateData = [{'authentication':websiteToken,'success':True,'lastRun':today,'codeurl':toolSettings['url'],'dataurl':dataurl}]
				
				jsonData = json.dumps(updateData)
				r = requests.post('http://www.pubrunner.org/update.php',headers=headers,files={'jsonFile': jsonData})
				assert r.status_code == 200, "Error updating website with job status"
			else:
				print("Could not update website. Did not find %s under website-update in .pubrunner.settings.yml file")



