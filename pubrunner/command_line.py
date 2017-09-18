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



#	if dataset == "PUBMED_SINGLEFILE":
#		datasetDir = os.path.join(baseDir,dataset)
#		if not os.path.isdir(datasetDir):
#			os.makedirs(datasetDir)
#
#		singleFile = 'ftp://ftp.ncbi.nlm.nih.gov/pubmed/baseline/medline17n0892.xml.gz'
#		wget.download(singleFile,datasetDir)
#		fileGZ = os.path.join(datasetDir,'medline17n0892.xml.gz')
#		fileXML = os.path.join(datasetDir,'medline17n0892.xml')
#
#		with gzip.open(fileGZ, 'rb') as f_in, open(fileXML, 'wb') as f_out:
#			shutil.copyfileobj(f_in, f_out)
#
#		return datasetDir
#	else:
#		raise RuntimeError("Unknown dataset: %s" % dataset)

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

def adaptCommands(commands,resourceMap,outputDir):
	adaptedCommands = []
	for command in runCommands:
		split = command.split(' ')
		for i in range(len(split)):
			if split[i] in resourceMap:
				split[i] = resourceMap[split[i]][0]
			elif split[i] == '$OUTPUTDIR':
				split[i] = outputDir
			#elif split[i] == 'OUTPUTFILE':
			#	split[i] = os.path.join(outputDir,'output')
		adaptedCommand = " ".join(split)
		adaptedCommands.append(adaptedCommand)
	return adaptedCommands

def transformParallelCommands(commands):
	runCommands = []
	for command in commands:
		if isinstance(command,dict):
			assert len(command.items()) == 1
			key,tmpparallelinfo = command.items()[0]
			assert key == 'parallel'
			parallelcommands = []
			parallelinfo = {}
			for pi in tmpparallelinfo:
				if isinstance(pi,dict):
					assert len(pi.items()) == 1
					parallelinfo.update(pi)
				else:
					parallelcommands.append(pi)
			#print parallelinfo, parallelcommands
			for pc in parallelcommands:
				runCommands.append((parallelinfo,pc))
		else:
			runCommands.append((None,command))
	return runCommands

def orderedUniq(lst):
	d = OrderedDict()
	for k in lst:
		d[k] = 1
	return list(d.keys())

def createMakeFile(filename, makeDefinitions, makeCommands):
	with open(filename, 'w') as f:
		for name,value in makeDefinitions:
			f.write("%s = %s\n\n" % (name,value))

		for target,(dependencies,commands) in makeCommands.items():
			dependencies = orderedUniq(dependencies)
			f.write("%s: %s\n" % (target, " ".join(dependencies)))
			if not isinstance(commands,list):
				commands = [commands]

			for command in commands:
				f.write("\t%s\n" % command)
			f.write("\n")


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

def generateParallelMakeCode(parallelinfo,command,target,dependencies):
	variables = extractVariables(command)
	for startPos,endPos,v in variables:
		if v == 'INFILE':
			command = command[:startPos] + "$<" + command[endPos:]
		elif v == 'OUTFILE':
			command = command[:startPos] + "$@" + command[endPos:]
		else:
			command = command[:startPos] + "$("+v+"_LOC)" + command[endPos:]

	t = ""
	if isinstance(parallelinfo,dict):
		inDir = parallelinfo['indir'].lstrip('?')
		outDir = parallelinfo['outdir'].lstrip('?')
		inFilter = parallelinfo['filter'].lstrip('?') if 'filter' in parallelinfo else ''

		makeLocation(outDir,createDir=True)
		#makeLocation(outDir+'_PARALLEL',createDir=True)

		t += "@OUTDIR_FILES = $(@INDIR_FILES:$(@INDIR_LOC)/%@INFILTER=$(@OUTDIR_LOC)/%)\n"
		#t += "@OUTDIR_FILES_PARALLEL = $(@INDIR_FILES:$(@INDIR_LOC)/%@INFILTER=$(@OUTDIR_LOC)/%.parallel)\n"
		t += "$(@OUTDIR_LOC)/%: $(@INDIR_LOC)/%@INFILTER $(@INDIR_LOC) @DEPENDENCIES\n"
		t += "\techo '@COMMAND' >> $(@OUTDIR_LOC)_JOBLIST\n"
		t += "\ttouch $<\n"

		t += "$(@OUTDIR_LOC)_JOBLIST: $(@OUTDIR_FILES)\n"


		#t += "$(@OUTDIR_LOC)/FENCE: $(@OUTDIR_FILES_PARALLEL)\n"
		t += "$(@OUTDIR_LOC): $(@OUTDIR_LOC)_JOBLIST\n"
		t += "\tsh $(@OUTDIR_LOC)_JOBLIST\n"
		#t += "\trm $(@OUTDIR_LOC)/JOBLIST\n"
		#t += "\ttouch $(@OUTDIR_LOC)/FENCE\n"
		t += "\ttouch $(@OUTDIR_LOC)\n\n"
		
		#t += "$(@OUTDIR_LOC)/%: $(@OUTDIR_LOC)/FENCE\n"



		t = t.replace('@INDIR',inDir)
		t = t.replace('@OUTDIR',outDir)
		t = t.replace('@INFILTER',inFilter)
	else:
		t += "$(@TARGET_LOC): @DEPENDENCIES\n"
		t += "\t@COMMAND\n\n"

	if not target is None:
		t = t.replace('@TARGET',target)
	t = t.replace('@COMMAND',command)

	depsWithFiles = []
	for dependency in dependencies:
		d = "$(@DEP_LOC)".replace('@DEP',dependency)
		depsWithFiles.append(d)
	dependencyText = " ".join(depsWithFiles)
	t = t.replace('@DEPENDENCIES', dependencyText)

	return t

def generateMakeCode(parallelinfo,command,target,dependencies):
	variables = extractVariables(command)
	for startPos,endPos,v in variables:
		if v == 'INFILE':
			command = command[:startPos] + "$<" + command[endPos:]
		elif v == 'OUTFILE':
			command = command[:startPos] + "$@" + command[endPos:]
		else:
			command = command[:startPos] + "$("+v+"_LOC)" + command[endPos:]

	t = ""
	if isinstance(parallelinfo,dict):
		inDir = parallelinfo['indir'].lstrip('?')
		outDir = parallelinfo['outdir'].lstrip('?')
		inFilter = parallelinfo['filter'].lstrip('?') if 'filter' in parallelinfo else ''

		makeLocation(outDir,createDir=True)

		t += "@OUTDIR_FILES = $(@INDIR_FILES:$(@INDIR_LOC)/%@INFILTER=$(@OUTDIR_LOC)/%)\n"
		t += "$(@OUTDIR_LOC)/%: $(@INDIR_LOC)/%@INFILTER @DEPENDENCIES\n"
		t += "\t@COMMAND\n"

		t += "$(@OUTDIR_LOC): $(@OUTDIR_FILES)\n"
		t += "\ttouch $(@OUTDIR_LOC)\n\n"

		t = t.replace('@INDIR',inDir)
		t = t.replace('@OUTDIR',outDir)
		t = t.replace('@INFILTER',inFilter)
	else:
		t += "$(@TARGET_LOC): @DEPENDENCIES\n"
		t += "\t@COMMAND\n\n"

	if not target is None:
		t = t.replace('@TARGET',target)
	t = t.replace('@COMMAND',command)

	depsWithFiles = []
	for dependency in dependencies:
		d = "$(@DEP_LOC)".replace('@DEP',dependency)
		depsWithFiles.append(d)
	dependencyText = " ".join(depsWithFiles)
	t = t.replace('@DEPENDENCIES', dependencyText)

	return t



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

def cloneGithubRepoToTempDir(githubRepo):
	tempDir = tempfile.mkdtemp()
	Repo.clone_from(githubRepo, tempDir)
	return tempDir

def main():
	parser = argparse.ArgumentParser(description='PubRunner will manage the download of needed resources for a text mining tool, build and execute it and then share the results publicly')
	parser.add_argument('codebase',nargs='?',type=str,help='Code base containing the text mining tool to execute. Code base should contain a .pubrunner.yml file. The code base can be a directory, Github repo or archive')
	parser.add_argument('--test',action='store_true',help='Run the test functionality instead of the full run')
	parser.add_argument('--getResource',required=False,type=str,help='Fetch a specific resource (instead of doing a normal PubRunner run). This is really only needed for debugging and understanding resources.')

	args = parser.parse_args()

	if args.getResource:
		location = pubrunner.getResource(args.getResource)
		print("Downloaded latest version of resource '%s' to location:" % args.getResource)
		print(location)
		print("")
		print("Exiting without doing PubRun")
		sys.exit(0)
	
	if not args.codebase:
		print("codebase must be provided (if not downloading individual resources)")
		parser.print_help()
		sys.exit(1)

	if os.path.isdir(args.codebase):
		pubrun(args.codebase,args.test)
	elif args.codebase.startswith('https://github.com/'):
		tempDir = ''
		try:
			tempDir = cloneGithubRepoToTempDir(args.codebase)
			pubrun(tempDir,args.test)
			shutil.rmtree(tempDir)
		except:
			if os.path.isdir(tempDir):
				shutil.rmtree(tempDir)
			logging.error(traceback.format_exc())
			raise

	elif os.path.isfile(args.codebase):
		raise RuntimeError("Not implemented")
	else:
		raise RuntimeError("Not sure what to do with codebase: %s. Doesn't appear to be a directory, Github repo or archive")


