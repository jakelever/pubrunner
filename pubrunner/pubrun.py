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

def loadYAML(yamlFilename):
	yamlData = None
	with open(yamlFilename,'r') as f:
		try:
			yamlData = yaml.load(f)
		except yaml.YAMLError as exc:
			print(exc)
			raise
	return yamlData

def findSettingsFile():
	possibilities = [ os.getcwd(), os.path.expanduser("~") ]
	for directory in possibilities:
		settingsPath = os.path.join(directory,'.pubrunner.settings.yml')
		if os.path.isfile(settingsPath):
			return settingsPath
	raise RuntimeError("Unable to find .pubrunner.settings.yml file. Tried current directory first, then home directory")

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
	#homeDir = os.path.expanduser("~")
	homeDir = '/projects/bioracle/jake/pubrunnerTmp'
	baseDir = os.path.join(homeDir,'.pubrunner')
	thisResourceDir = os.path.join(baseDir,'resources',resource)
	return thisResourceDir

def getResourceInfo(resource):
	packagePath = os.path.dirname(pubrunner.__file__)
	resourceYamlPath = os.path.join(packagePath,'resources','%s.yml' % resource)
	with open(resourceYamlPath) as f:
		resourceInfo = yaml.load(f)

	return resourceInfo

def makeLocation(name,createDir=False):
	homeDir = '/projects/bioracle/jake/pubrunnerTmp'
	baseDir = os.path.join(homeDir,'.pubrunner')
	thisDir = os.path.join(baseDir,'workingDir',name)
	if createDir and not os.path.isdir(thisDir):
		os.makedirs(thisDir)
	return thisDir

def processResourceSettings(toolSettings,mode):
	locationMap = {}

	newResourceList = []
	preprocessingCommands = []
	for resourceGroupName in ["all",mode]:
		for resName in toolSettings["resources"][resourceGroupName]:
			if isinstance(resName,dict):
				assert len(resName.items()) == 1

				# TODO: Rename resSettings and resInfo to be more meaningful
				resName,resSettings = resName.items()[0]
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

					command = "pubrunner_convert --i {IN:%s/*%s} --iFormat %s --o {OUT:%s/*.converted} --oFormat %s" % (inDir,inFilter,inFormat,outDir,outFormat)
					preprocessingCommands.append( command )

					locationMap[nameToUse+"_UNCONVERTED"] = getResourceLocation(resName)
					locationMap[nameToUse] = makeLocation(resName+"_CONVERTED")
				else:
					locationMap[nameToUse] = getResourceLocation(resName)
					

				newResourceList.append(resName)
			else:
				locationMap[resName] = getResourceLocation(resName)
				newResourceList.append(resName)

	toolSettings["resources"] = newResourceList

	toolSettings["build"] = preprocessingCommands + toolSettings["build"]
	return locationMap

def commandToSnakeMake(ruleName,command,locationMap):
	variables = extractVariables(command)

	inputs = []
	outputs = []
	dirsToTouch = []
	newCommand = command

	firstInputPattern,firstOutputPattern = None,None
	hasWildcard = False

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
			locationMap[varname] = makeLocation(varname)
		loc = locationMap[varname]
		loc = os.path.relpath(loc)

		if pattern:
			hasWildcard = True

		repname = varname + str(startPos)
		if vartype == 'IN' and not pattern:
			inputs.append((repname,loc))
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
		elif vartype == 'OUT' and pattern:
			if not firstOutputPattern:
				firstOutputPattern = loc + '/' + pattern

			snakepattern = loc + '/' + pattern.replace('*','{f}')
			outputs.append((repname,snakepattern))
			dirsToTouch.append(loc)

		if vartype == 'IN':
			newCommand = newCommand[:startPos] + '{input.%s}' % repname + newCommand[endPos:]
		elif vartype == 'OUT':
			newCommand = newCommand[:startPos] + '{output.%s}' % repname + newCommand[endPos:]

	ruleTxt = ""
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
	
	ruleTxt += "\n"
	if hasWildcard:
		ruleTxt += "%s_EXPECTED_FILES = predictOutputFiles('%s','%s')\n" % (ruleName,firstInputPattern,firstOutputPattern)
	else:
		ruleTxt += "%s_EXPECTED_FILES = ['%s']\n" % (ruleName,firstOutputPattern)
	ruleTxt += "rule %s:\n" % ruleName
	ruleTxt += "\tinput: %s_EXPECTED_FILES\n" % ruleName

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
	settingsYamlFile = findSettingsFile()
	globalSettings = loadYAML(settingsYamlFile)

	os.chdir(directory)

	toolYamlFile = '.pubrunner.yml'
	if not os.path.isfile(toolYamlFile):
		raise RuntimeError("Expected a .pubrunner.yml file in root of codebase")

	toolSettings = loadYAML(toolYamlFile)
	#print(json.dumps(toolSettings,indent=2))
	
	if not "build" in toolSettings:
		toolSettings["build"] = []
	if not "all" in toolSettings["resources"]:
		toolSettings["resources"]["all"] = []
	if not mode in toolSettings["resources"]:
		toolSettings["resources"][mode] = []

	locationMap = processResourceSettings(toolSettings,mode)

	with open(os.path.join(os.path.dirname(__file__),'Snakefile.header')) as f:
		snakefileHeader = f.read()

	print("Building Snakefile")
	with open('Snakefile','w') as f:
		f.write(snakefileHeader)

		resourcesSnakeRule = generateGetResourceSnakeRule(toolSettings["resources"])
		f.write(resourcesSnakeRule)

		commands = toolSettings["build"] + toolSettings["run"]
		for i,command in enumerate(commands):
			ruleName = "RULE_%d" % (i+1)
			snakecode = commandToSnakeMake(ruleName, command,locationMap)
			f.write(snakecode + "\n")
	print("Completed Snakefile")

	if execute:
		for i,command in enumerate(commands):
			ruleName = "RULE_%d" % (i+1)
			print("\nRunning command %d: %s" % (i+1,command))
			retval = subprocess.call(["snakemake",ruleName])
			if retval != 0:
				raise RuntimeError("Snake make call FAILED for rule: %s" % ruleName)
		print("")

		if "output" in toolSettings:
			outputList = toolSettings["output"]
			if not isinstance(outputList,list):
				outputList = [outputList]

			outputLocList = [ locationMap[o] for o in outputList ]

			if "upload" in globalSettings:
				if "ftp" in globalSettings["upload"]:
					print("Uploading results to FTP")
					pubrunner.pushToFTP(outputLocList,toolSettings,globalSettings)
				if "local-directory" in globalSettings["upload"]:
					print("Uploading results to local directory")
					pubrunner.pushToLocalDirectory(outputLocList,toolSettings,globalSettings)
				if "zenodo" in globalSettings["upload"]:
					print("Uploading results to Zenodo")
					pubrunner.pushToZenodo(outputLocList,toolSettings,globalSettings)

			print("Sending update to website")


