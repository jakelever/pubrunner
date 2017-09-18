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
	regex = re.compile("\?[A-Za-z_0-9]*")
	variables = []
	for m in regex.finditer(command):
		var = ( m.start(), m.end(), m.group()[1:] )
		variables.append(var)
	variables = sorted(variables,reverse=True)
	return variables

def dealWithResourceSettings(toolSettings,mode):
	newResourceList = []
	preprocessingCommands = []
	renameMap = {}
	for resourceGroupName in ["all",mode]:
		for resName in toolSettings["resources"][resourceGroupName]:
			if isinstance(resName,dict):
				assert len(resName.items()) == 1

				resName,resSettings = resName.items()[0]
	
				resInfo = getResourceInfo(resName)
				fromFormat = resInfo["format"]

				if "name" in resSettings:
					rename = resSettings["name"]
					renameMap[rename] = resName + "_CONVERTED"
				if "format" in resSettings:
					toFormat = resSettings["format"]
					parallelInfo = {'indir':'?'+resName, 'outdir':"?"+resName+"_CONVERTED", 'filter':resInfo["filter"]}
					command = "pubrunner_convert --i ?INFILE --iFormat "+fromFormat+" --o ?OUTFILE --oFormat "+toFormat
					preprocessingCommands.append( (parallelInfo, command) )
				newResourceList.append(resName)
			else:
				newResourceList.append(resName)

		#newResources[resourceGroupName] = newResourceList
	toolSettings["resources"] = newResourceList

	toolSettings["build"] = preprocessingCommands + toolSettings["build"]
	
	for execList in ["build","run"]:
		assert isinstance(toolSettings[execList],list)
		for i in range(len(toolSettings[execList])):
			parallelinfo,command = toolSettings[execList][i]
			variables = extractVariables(command)
			for startPos,endPos,v in variables:
				if v in renameMap:
					command = command[:startPos] + "$("+renameMap[v]+"_LOC)" + command[endPos:]

			if isinstance(parallelinfo,dict) and "indir" in parallelinfo:
				dirname = parallelinfo['indir'].lstrip('?')
				if dirname in renameMap:
					parallelinfo['indir'] = '?'+renameMap[dirname]

			toolSettings[execList][i] = (parallelinfo,command)

def pubrun(directory,doTest):
	mode = "test" if doTest else "main"
	settingsYamlFile = findSettingsFile()
	globalSettings = loadYAML(settingsYamlFile)

	os.chdir(directory)

	toolYamlFile = '.pubrunner.yml'
	if not os.path.isfile(toolYamlFile):
		raise RuntimeError("Expected a .pubrunner.yml file in root of codebase")

	toolSettings = loadYAML(toolYamlFile)
	print(json.dumps(toolSettings,indent=2))
	
	if not "build" in toolSettings:
		toolSettings["build"] = []
	if not "all" in toolSettings["resources"]:
		toolSettings["resources"]["all"] = []
	if not mode in toolSettings["resources"]:
		toolSettings["resources"][mode] = []

	toolSettings["build"] = transformParallelCommands(toolSettings["build"])
	toolSettings["run"] = transformParallelCommands(toolSettings["run"])

	dealWithResourceSettings(toolSettings,mode)
	#print(json.dumps(toolSettings,indent=2))
	#sys.exit(0)

	execCommands = toolSettings["build"] + toolSettings["run"]
	execCommandsWithTargets = []

	alltargets = set(toolSettings["resources"])
	for parallelinfo,command in execCommands:
		variables = extractVariables(command)
		thisDependencies = set()
		thisTarget = None


		for startPos,endPos,v in variables:
			if v == 'INFILE' or v == "OUTFILE":
				continue
			#if isinstance(parallelinfo,dict):
				#assert False, v
			#	continue

			if v in alltargets:
				thisDependencies.add(v)
			else:
				assert thisTarget is None, 'Only one target per command. Already got %s and now got %s for command: %s' % (thisTarget,v,command) 
				thisTarget = v
				alltargets.add(v)
		
		if not isinstance(parallelinfo,dict):
		#	alltargets.add(parallelinfo["outdir"].lstrip('?'))

			print alltargets
			assert not thisTarget is None, "Couldn't find target in command: %s" % command
		else:
			alltargets.add(parallelinfo["outdir"].lstrip('?'))
			

		commandWithTarget = (parallelinfo,command,thisTarget,list(thisDependencies))
		execCommandsWithTargets.append(commandWithTarget)

	allMakeCode = ""
	allMakeCode += ".PHONY: default\n"
	allMakeCode += "default: all\n\n"

	for res in toolSettings["resources"]:
		resLocation = getResourceLocation(res)
		resInfo = getResourceInfo(res)
		resFilter = resInfo["filter"] if "filter" in resInfo else ""
		makeCode = "@RESOURCE_LOC = @RESLOCATION\n"
		makeCode += "@RESOURCE_FILES := $(wildcard $(@RESOURCE_LOC)/*@RESFILTER)\n"
		makeCode += "@RESOURCE:\n"
		makeCode += "\tpubrunner --getResource @RESOURCE\n"
		makeCode = makeCode.replace("@RESOURCE",res)
		makeCode = makeCode.replace("@RESLOCATION",resLocation)
		makeCode = makeCode.replace("@RESFILTER",resFilter)

		allMakeCode += makeCode + "\n"
		print makeCode

	for target in alltargets:
		if target in toolSettings["resources"]:
			continue

		targetLocation = makeLocation(target)
		makeCode = "@TARGET_LOC = @TARGETLOCATION\n"
		makeCode = makeCode.replace("@TARGETLOCATION",targetLocation)
		makeCode = makeCode.replace("@TARGET",target)
		allMakeCode += makeCode + "\n"
		print makeCode


	#print(json.dumps(execCommandsWithTargets,indent=2))
	for parallelinfo,command,target,dependencies in execCommandsWithTargets:
		#makeCode = generateMakeCode(parallelinfo,command,target,dependencies)
		makeCode = generateParallelMakeCode(parallelinfo,command,target,dependencies)
		allMakeCode += makeCode + "\n"
		print makeCode
		#print (command,target,dependencies)

	output = toolSettings["output"]
	makeCode = "\n.PHONY: all\n"
	makeCode += "all: $(@OUTPUT_LOC)\n\n"
	makeCode = makeCode.replace("@OUTPUT",output)
	allMakeCode += makeCode

	with open('Makefile','w') as f:
		f.write(allMakeCode)
	sys.exit(0)

	for parallelinfo, command, target, dependencies in execCommands:
		if isinstance(parallelinfo,dict):
			inDir = parallelinfo['indir']
			inFilter = parallelinfo['filter']
			outDir = parallelinfo['outdir']
			

	print(json.dumps(toolSettings,indent=2))

	sys.exit(0)

	print("Getting resources")
	resourceMap = {}
	resources = toolSettings["resources"]["all"] + toolSettings["resources"][mode]

	makeCommands = OrderedDict()
	makeDefinitions = []
	locations = {}

	#variableRenameTracker = {}

	for r in resources:
		if isinstance(r,dict):
			actualName,otherStuff = r.items()[0]
			rename = actualName
			if "name" in otherStuff:
				rename = otherStuff["name"]
			#locations[rename] = getResource(actualName)[0]
			resLocation = getResourceLocation(actualName)
			resInfo = getResourceInfo(actualName)
			fromFilter = resInfo["filter"] if "filter" in resInfo else ""

			if "format" in otherStuff:
				assert "format" in resInfo, "Format is not defined for resource (%s). Cannot convert it to something else" % actualName


				fromFormat = resInfo["format"]
				toFormat = otherStuff["format"]

				locations[rename+"_UNCONVERTED"] = resLocation
				makeCommands[rename+"_UNCONVERTED"] = ([],"pubrunner --getResource %s #--out %s" % (actualName,resLocation))
				makeDefinitions.append( (rename+"_UNCONVERTED_LOC", resLocation) )
				makeDefinitions.append( (rename+"_UNCONVERTED_FILES", "$(wildcard $("+rename+"_UNCONVERTED_LOC)/*."+fromFilter+")" ) )

				convertedLocation = makeLocation(rename+"_CONVERTED_"+toFormat,createDir=True)
				locations[rename] = convertedLocation
				wildcard = "$(" + rename + '_LOC)/%'
				makeCommands[wildcard] = (["$(%s_UNCONVERTED_FILES)" % rename],"pubrunner_convert --i $< --iFormat "+fromFormat+" --o $@ --oFormat "+toFormat)
				makeDefinitions.append( (rename+"_LOC", convertedLocation) )
				makeDefinitions.append( (rename+"_FILES", "$("+rename+"_UNCONVERTED_FILES)/%"+fromFilter+"="+wildcard+")" ))
			else:
				makeCommands[rename] = ([],"pubrunner --getResource %s #--out %s" % (actualName,resLocation))
				locations[rename] = resLocation
				makeDefinitions.append( (rename+"_LOC", resLocation) )
				makeDefinitions.append( (rename+"_FILES", "$(wildcard $("+rename+"_LOC)/*"+fromFilter+")" ) )
			
		else:
			#locations[r] = getResource(r)[0]
			resLocation = getResourceLocation(r)
			resInfo = getResourceInfo(r)
			fromFilter = resInfo["filter"] if "filter" in resInfo else ""

			makeCommands[r] = ([],"pubrunner --getResource %s #--out %s" % (r,resLocation))
			locations[r] = resLocation
			makeDefinitions.append( (r+"_LOC", resLocation) )
			makeDefinitions.append( (r+"_FILES", "$(wildcard $("+r+"_LOC)/*"+fromFilter+")" ) )


	if not "build" in toolSettings:
		toolSettings["build"] = []

	print("Running build")
	#commandSet.append(('build',toolSettings["build"]))
	for command in toolSettings["build"]:
		#print command
		variables = extractVariables(command)
		dependencies = []
		targets = []
		#print variables
		for startPos,endPos,v in variables:
			if v in locations:
				#dependencies.append(locations[v])
				#dependencies.append(v)
				dependencies.append("$("+v+"_FILES)")
			else:
			 	locations[v] = makeLocation(v)
				makeDefinitions.append( (v+"_LOC", locations[v]) )
				targets.append("$("+v+"_LOC)")
			#command = command[:startPos] + locations[v] + command[endPos:]
			command = command[:startPos] + "$("+v+"_LOC)" + command[endPos:]

		touchCommand = "touch $("+v+"_LOC)"

		#print 'X', targets, dependencies, command
		assert len(targets) == 1, "Each command is expected to generate ONE new output file/dir"
		makeCommands[targets[0]] = (dependencies,[command,touchCommand])
		#print variables

	createMakeFile('Makefile',makeDefinitions,makeCommands)
	sys.exit(0)

	print json.dumps(makeCommands,indent=2)

	print("Running tool")
	#outputDir = tempfile.mkdtemp()
	outputDir = '/projects/bioracle/jake/pubrunnerTmp/out/'
	#runCommands = adaptCommands(toolSettings["run"],resourceMap,outputDir)
	#print(runCommands)
	runCommands = transformParallelCommands(toolSettings["run"])
					
	print(runCommands)
	#execCommands(adaptedCommands)

	sys.exit(0)


	if "upload" in globalSettings:
		print(json.dumps(globalSettings,indent=2))
		if "ftp" in globalSettings["upload"]:
			print("Uploading results to FTP")
			pubrunner.pushToFTP(outputDir,toolSettings,globalSettings)
		if "local-directory" in globalSettings["upload"]:
			print("Uploading results to local directory")
			pubrunner.pushToLocalDirectory(outputDir,toolSettings,globalSettings)
		if "zenodo" in globalSettings["upload"]:
			print("Uploading results to Zenodo")
			pubrunner.pushToZenodo(outputDir,toolSettings,globalSettings)

	print("Sending update to website")
