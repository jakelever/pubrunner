import pubrunner
import os
import shutil
import yaml
import json
import six
import re
import requests
import datetime
import csv
import atexit

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
	
def processResourceSettings(toolSettings,mode,workingDirectory):
	newResourceList = []
	#preprocessingCommands = []
	conversions = []
	resourcesWithHashes = []
	for resourceGroupName in ["all",mode]:
		for resName in toolSettings["resources"][resourceGroupName]:
			if isinstance(resName,dict):
				assert len(resName.items()) == 1, "ERROR in pubrunner.yml: A resource (%s) is not being parsed correctly. It is likely that the resource settings (e.g. format) are not indented properly. Try indenting more" % (str(list(resName.keys())[0]))

				# TODO: Rename resSettings and resInfo to be more meaningful
				resName,resSettings = list(resName.items())[0]
				resInfo = pubrunner.getResourceInfo(resName)

				allowed = ['rename','format','removePMCOADuplicates','usePubmedHashes']
				for k in resSettings.keys():
					assert k in allowed, "Unexpected attribute (%s) for resource %s" % (k,resName)

				nameToUse = resName
				if "rename" in resSettings:
					nameToUse = resSettings["rename"]

				if "format" in resSettings:
					inDir = nameToUse + "_UNCONVERTED"
					inFormat = resInfo["format"]

					if 'chunkSize' in resInfo:
						chunkSize = resInfo["chunkSize"]
					else:
						chunkSize = 1

					outDir = nameToUse
					outFormat = resSettings["format"]

					removePMCOADuplicates = False
					if "removePMCOADuplicates" in resSettings and resSettings["removePMCOADuplicates"] == True:
						removePMCOADuplicates = True

					#command = "pubrunner_convert --i {IN:%s/*%s} --iFormat %s --o {OUT:%s/*%s} --oFormat %s" % (inDir,inFilter,inFormat,outDir,inFilter,outFormat)
					conversionInfo = (os.path.join(workingDirectory,inDir),inFormat,os.path.join(workingDirectory,outDir),outFormat,chunkSize)
					conversionInfo = {}
					conversionInfo['inDir'] = os.path.join(workingDirectory,inDir)
					conversionInfo['inFormat'] = inFormat
					conversionInfo['outDir'] = os.path.join(workingDirectory,outDir)
					conversionInfo['outFormat'] = outFormat
					conversionInfo['chunkSize'] = chunkSize
					conversions.append( conversionInfo )

					whichHashes = None
					if "usePubmedHashes" in resSettings:
						whichHashes = [ p.strip() for p in resSettings["usePubmedHashes"].split(',') ]

					resourceSymlink = os.path.join(workingDirectory,inDir)
					if not os.path.islink(resourceSymlink):
						os.symlink(getResourceLocation(resName), resourceSymlink)

					if "generatePubmedHashes" in resInfo and resInfo["generatePubmedHashes"] == True:
						hashesSymlink = os.path.join(workingDirectory,inDir+'.hashes')
						hashesInfo = {'resourceDir':os.path.join(workingDirectory,inDir),'hashDir':hashesSymlink,'removePMCOADuplicates':removePMCOADuplicates,'whichHashes':whichHashes}

						resourcesWithHashes.append(hashesInfo)
						if not os.path.islink(hashesSymlink):
							hashesDir = getResourceLocation(resName)+'.hashes'
							#assert os.path.isdir(hashesDir), "Couldn't find directory containing hashes for resource: %s. Looked in %s" % (resName,hashesDir)
							os.symlink(hashesDir, hashesSymlink)

					newDirectory = os.path.join(workingDirectory,outDir)
					if not os.path.isdir(newDirectory):
						os.makedirs(newDirectory)
				else:
					resourceSymlink = os.path.join(workingDirectory,nameToUse)
					if not os.path.islink(resourceSymlink):
						os.symlink(getResourceLocation(resName), resourceSymlink)

				newResourceList.append(resName)
			else:
				resourceSymlink = os.path.join(workingDirectory,resName)
				if not os.path.islink(resourceSymlink):
					os.symlink(getResourceLocation(resName), resourceSymlink)
				newResourceList.append(resName)

	toolSettings["resources"] = newResourceList
	toolSettings["pubmed_hashes"] = resourcesWithHashes

	toolSettings["conversions"] = conversions

def cleanWorkingDirectory(directory,doTest,execute=False):
	mode = "test" if doTest else "full"

	globalSettings = pubrunner.getGlobalSettings()
	os.chdir(directory)

	toolYamlFile = 'pubrunner.yml'
	if not os.path.isfile(toolYamlFile):
		raise RuntimeError("Expected a %s file in root of codebase" % toolYamlFile)

	toolSettings = pubrunner.loadYAML(toolYamlFile)
	toolName = toolSettings["name"]

	workspaceDir = os.path.expanduser(globalSettings["storage"]["workspace"])
	workingDirectory = os.path.join(workspaceDir,toolName,mode)

	if os.path.isdir(workingDirectory):
		print("Removing working directory for tool %s" % toolName)
		print("Directory: %s" % workingDirectory)
		shutil.rmtree(workingDirectory)
	else:
		print("No working directory to remove for tool %s" % toolName)
		print("Expected directory: %s" % workingDirectory)
		
def downloadPMIDSFromPMC(workingDirectory):
	url = 'ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_file_list.csv'
	localFile = os.path.join(workingDirectory,'oa_file_list.csv')
	pubrunner.download(url,localFile)

	pmids = set()
	with open(localFile) as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			pmid = row['PMID']
			if pmid != '':
				pmids.add(int(pmid))

	os.unlink(localFile)

	return pmids

def cleanup():
	if os.path.isdir('.pubrunner_lock'):
		shutil.rmtree('.pubrunner_lock')
	if os.path.isdir('.snakemake'):
		shutil.rmtree('.snakemake')

def pubrun(directory,doTest):
	mode = "test" if doTest else "full"

	globalSettings = pubrunner.getGlobalSettings()

	os.chdir(directory)
	
	if os.path.isdir('.pubrunner_lock'):
		raise RuntimeError("A .pubrunner_lock directory exists in this project directory. These are created by PubRunner during an incomplete run. Are you sure another instance of PubRunner is not currently running? If you're sure, you will need to delete this directory before continuing. The directory is: %s" % os.path.join(directory,'.pubrunner_lock'))

	os.mkdir('.pubrunner_lock')
	atexit.register(cleanup)

	toolYamlFile = 'pubrunner.yml'
	if not os.path.isfile(toolYamlFile):
		raise RuntimeError("Expected a %s file in root of codebase" % toolYamlFile)

	toolSettings = pubrunner.loadYAML(toolYamlFile)
	toolName = toolSettings["name"]

	workspacesDir = os.path.expanduser(globalSettings["storage"]["workspace"])
	workingDirectory = os.path.join(workspacesDir,toolName,mode)
	if not os.path.isdir(workingDirectory):
		os.makedirs(workingDirectory)

	print("Working directory: %s" % workingDirectory)
	
	if not "build" in toolSettings:
		toolSettings["build"] = []
	if not "all" in toolSettings["resources"]:
		toolSettings["resources"]["all"] = []
	if not mode in toolSettings["resources"]:
		toolSettings["resources"][mode] = []

	processResourceSettings(toolSettings,mode,workingDirectory)

	print("\nFetching resources")
	for res in toolSettings["resources"]:
		pubrunner.getResource(res)

	pmidsFromPMCFile = None
	needPMIDsFromPMC = any( hashesInfo['removePMCOADuplicates'] for hashesInfo in toolSettings["pubmed_hashes"] )
	if needPMIDsFromPMC:
		print("\nGetting list of PMIDs in Pubmed Central")
		pmidsFromPMCFile = downloadPMIDSFromPMC(workingDirectory)

	directoriesWithHashes = set()
	if toolSettings["pubmed_hashes"] != []:
		print("\nUsing Pubmed Hashes to identify updates")
		for hashesInfo in toolSettings["pubmed_hashes"]:
			hashDirectory = hashesInfo['hashDir']
			whichHashes = hashesInfo['whichHashes']
			removePMCOADuplicates = hashesInfo['removePMCOADuplicates']

			directoriesWithHashes.add(hashesInfo['resourceDir'])

			pmidDirectory = hashesInfo["resourceDir"].rstrip('/') + '.pmids'
			print("Using hashes in %s to identify PMID updates" % hashDirectory)
			if removePMCOADuplicates:
				assert not pmidsFromPMCFile is None
				pubrunner.gatherPMIDs(hashDirectory,pmidDirectory,whichHashes=whichHashes,pmidExclusions=pmidsFromPMCFile)
			else:
				pubrunner.gatherPMIDs(hashDirectory,pmidDirectory,whichHashes=whichHashes)

	print("\nRunning conversions")
	for conversionInfo in toolSettings["conversions"]:
		inDir,inFormat = conversionInfo['inDir'],conversionInfo['inFormat']
		outDir,outFormat = conversionInfo['outDir'],conversionInfo['outFormat']
		chunkSize = conversionInfo['chunkSize']
		parameters = {'INDIR':inDir,'INFORMAT':inFormat,'OUTDIR':outDir,'OUTFORMAT':outFormat,'CHUNKSIZE':str(chunkSize)}

		if inDir in directoriesWithHashes:
			pmidDirectory = inDir.rstrip('/') + '.pmids'
			assert os.path.isdir(pmidDirectory), "Cannot find PMIDs directory for resource. Tried: %s" % pmidDirectory
			parameters['PMIDDIR'] = pmidDirectory

		convertSnakeFile = os.path.join(pubrunner.__path__[0],'Snakefiles','Convert.py')
		pubrunner.launchSnakemake(convertSnakeFile,parameters=parameters)


	runSnakeFile = os.path.join(pubrunner.__path__[0],'Snakefiles','Run.py')
	for commandGroup in ["build","run"]:
		for i,command in enumerate(toolSettings[commandGroup]):
			print("\nStarting '%s' command #%d: %s" % (commandGroup,i+1,command))
			useClusterIfPossible = True
			parameters = {'COMMAND':command,'DATADIR':workingDirectory}
			pubrunner.launchSnakemake(runSnakeFile,useCluster=useClusterIfPossible,parameters=parameters)
			print("")

	if "output" in toolSettings:
		outputList = toolSettings["output"]
		if not isinstance(outputList,list):
			outputList = [outputList]

		outputLocList = [ os.path.join(workingDirectory,o) for o in outputList ]

		print("\nExecution of tool is complete. Full paths of output files are below:")
		for f in outputLocList:
			print('  %s' % f)
		print()

		if mode != 'test':

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
				print("Could not update website. Did not find %s under website-update in .pubrunner.settings.yml file" % toolName)



