import pubrunner
import argparse
import os
from git import Repo
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

def execCommands(commands):
	assert isinstance(commands,list)
	for command in commands:
		print(command)
		subprocess.call(shlex.split(command))

def fetchDataset(dataset):
	homeDir = os.path.expanduser("~")
	baseDir = os.path.join(homeDir,'.pubrunner')

	if dataset == "PUBMED_SINGLEFILE":
		datasetDir = os.path.join(baseDir,dataset)
		if not os.path.isdir(datasetDir):
			os.makedirs(datasetDir)

		singleFile = 'ftp://ftp.ncbi.nlm.nih.gov/pubmed/baseline/medline17n0892.xml.gz'
		wget.download(singleFile,datasetDir)
		fileGZ = os.path.join(datasetDir,'medline17n0892.xml.gz')
		fileXML = os.path.join(datasetDir,'medline17n0892.xml')

		with gzip.open(fileGZ, 'rb') as f_in, open(fileXML, 'wb') as f_out:
			shutil.copyfileobj(f_in, f_out)

		return datasetDir
	else:
		raise RuntimeError("Unknown dataset: %s" % dataset)

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
	
def pubrun(directory,doTest):
	settingsYamlFile = findSettingsFile()
	globalSettings = loadYAML(settingsYamlFile)

	os.chdir(directory)

	toolYamlFile = '.pubrunner.yml'
	if not os.path.isfile(toolYamlFile):
		raise RuntimeError("Expected a .pubrunner.yml file in root of codebase")

	toolSettings = loadYAML(toolYamlFile)

	if "build" in toolSettings:
		print("Running build")
		execCommands(toolSettings["build"])
	
	print("Fetching datasets")
	datasets = toolSettings["testdata"] if doTest else toolSettings["rundata"]
	datasetMap = {}
	for dataset in datasets:
		datasetMap[dataset] = fetchDataset(dataset)

	print("Running tool")
	outputDir = tempfile.mkdtemp()
	runCommands = toolSettings["test"] if doTest else toolSettings["run"]
	print(runCommands)
	adaptedCommands = []
	for command in runCommands:
		split = command.split(' ')
		for i in range(len(split)):
			if split[i] in datasetMap:
				split[i] = datasetMap[split[i]]
			elif split[i] == 'OUTPUTDIR':
				split[i] = outputDir
			elif split[i] == 'OUTPUTFILE':
				split[i] = os.path.join(outputDir,'output')
		adaptedCommand = " ".join(split)
		adaptedCommands.append(adaptedCommand)
	print(adaptedCommands)
	execCommands(adaptedCommands)

def cloneGithubRepoToTempDir(githubRepo):
	tempDir = tempfile.mkdtemp()
	Repo.clone_from(githubRepo, tempDir)
	return tempDir

def main():
	parser = argparse.ArgumentParser(description='PubRunner will manage the download of needed resources for a text mining tool, build and execute it and then share the results publicly')
	parser.add_argument('codebase',type=str,help='Code base containing the text mining tool to execute. Code base should contain a .pubrunner.yml file. The code base can be a directory, Github repo or archive')
	parser.add_argument('--test',action='store_true',help='Run the test functionality instead of the full run')

	args = parser.parse_args()

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


