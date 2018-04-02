import sys
import glob
import re
import six
import os
import shutil
import hashlib

def predictOutputFiles2(inPattern,outPattern):
	outfiles = []
	for potentialInputFiles in glob.glob(inPattern):
		wildcardValue = re.match(inPattern.replace('*','(.*)'), potentialInputFiles).groups()[0]
		potentialOutputFile = outPattern.replace('*',wildcardValue)
		outfiles.append(potentialOutputFile)
	return outfiles

def checkVariablesForWildcardLimit(variables):
	# no variable should contain both types of wildcards or more than one of each
	for varName,pattern in variables.items():
		asteriskWildcardCount = pattern.count('*')
		percentWildcardCount = pattern.count('%')
		assert asteriskWildcardCount + percentWildcardCount <= 1, 'A variable can only contain one type of wildcard (* or %). The following contains more than one: %s' % pattern

def checkOutputVariablesForAsteriskWildcards(variables):
	# no variable should contain both types of wildcards or more than one of each
	for varName,pattern in variables.items():
		asteriskWildcardCount = pattern.count('*')
		assert asteriskWildcardCount == 0, "An output variable can not contain asterisk wildcards. Perhaps you want a percent ('%%') wildcard to match with an input percent wildcard? Error found in: %s" % pattern

def checkVariables(inputVariables,outputVariables):
	# No variable should have more than one wildcard
	checkVariablesForWildcardLimit(inputVariables)
	checkVariablesForWildcardLimit(outputVariables)

	checkOutputVariablesForAsteriskWildcards(outputVariables)

def predictOutputFiles(inputVariables,outputVariables):
	allWildcardValues = None
	for i,(inputVarName,inPattern) in enumerate(inputVariables.items()):
		if not '{wildcard}' in inPattern:
			# No percent wildcard so skip
			continue
		assert not '*' in inPattern, "There should not be an asterisk wildcard in the same pattern as a percent wildcard"

		wildcardValues = set()
		for potentialInputFile in glob.glob(inPattern.replace('{wildcard}','*')):
			wildcardValue = re.match(inPattern.replace('{wildcard}','(.*)'), potentialInputFile).groups()[0]
			wildcardValues.add(wildcardValue)
		if allWildcardValues is None:
		 	allWildcardValues = wildcardValues
		else:
			allWildcardValues = allWildcardValues.intersection(wildcardValues)

	inputContainsPercentWildcards = isinstance(allWildcardValues,set)
	if inputContainsPercentWildcards:
		#assert len(allWildcardValues) > 0, "Percent wildcards on input unable to match to any input files"
		if len(allWildcardValues) == 0:
			return []

		allWildcardValues = sorted(list(allWildcardValues))

	expectedOutputFiles = []
	for outputVarName,outPattern in outputVariables.items():
		if '{wildcard}' in outPattern:
			# Replace percent wildcard with all wildcard values from inputs
			assert inputContainsPercentWildcards, "Output contains percent wildcards but no input contains percent wildcards"

			for w in allWildcardValues:
				expectedOutputFiles.append(outPattern.replace('{wildcard}',w))
		else:
			expectedOutputFiles.append(outPattern)

	return expectedOutputFiles

def processCommand(dataDir,command):
	assert isinstance(command,six.string_types)
	#regex = re.compile("\{(?P<type>(IN|OUT)):(?P<value>\S*)\}")
	regex = re.compile("\{(?P<content>[^}]*)\}")
	variablesWithLocations = []
	for m in regex.finditer(command):
		content = m.groupdict()['content'].split(':')
		assert len(content)==2, "ERROR for: Inputs/outputs in PubRunner commands must follow the format of {IN:pattern} or {OUT:pattern}. No other curly brackets are allowed as they clash with PubRunner & SnakeMake." % m.groupdict()['content']
		vartype,value = content
		assert vartype == 'IN' or vartype == 'OUT', "ERROR for: %s. Inputs/outputs in PubRunner commands must follow the format of {IN:pattern} or {OUT:pattern}. No other curly brackets are allowed as they clash with PubRunner & SnakeMake." % m.groupdict()['content']

		variableWithLocation = (m.start(), m.end(), vartype, value)
		variablesWithLocations.append(variableWithLocation)
	variablesWithLocations = sorted(variablesWithLocations,reverse=True)

	inputVariables,outputVariables = {},{}
	newCommand = command
	inputPercentWildcard,outputPercentWildcard = False,False
	for i,(start,end,vartype,value) in enumerate(variablesWithLocations):
		assert vartype == 'IN' or vartype == 'OUT'

		snakevartype = 'input' if vartype == 'IN' else 'output'
		name = "%s%04d" % (vartype,i)
		newCommand = newCommand[:start] + '{%s.%s}' % (snakevartype,name) + newCommand[end:]

		if '%' in value:
			if vartype == 'IN':
				inputPercentWildcard = True
			elif vartype == 'OUT':
				outputPercentWildcard = True

		location = os.path.join(dataDir,value).replace('%','{wildcard}')

		if vartype == 'IN':
			inputVariables[name] = location
		elif vartype == 'OUT':
			outputVariables[name] = location

	# For the case where a percent wildcard is used in an input but not an output.
	# We need to add an artificial (and hidden) output file with a wildcard
	if inputPercentWildcard and not outputPercentWildcard:
		md5 = hashlib.md5()
		md5.update(bytes(command.encode('utf-8')))
		commandHash = str(md5.hexdigest())
		hiddenDir = os.path.join(dataDir,'.hidden',commandHash)
		if not os.path.isdir(hiddenDir):
			os.makedirs(hiddenDir)

		artificialName = 'artificial'
		artificialOutput = os.path.join(hiddenDir,'{wildcard}.txt')
		outputVariables[artificialName] = artificialOutput
		#newCommand = 'touch {output.%s}; %s' % (artificialName, newCommand)

		outputPercentWildcard = True

	# If there are wildcards used in the outputs, we actually need to remove any non-wildcard arguments and just put them directly into the command
	if outputPercentWildcard:
		toRemove = []
		for name in outputVariables.keys():
			if not '{wildcard}' in outputVariables[name]:
				toRemove.append(name)
				newCommand = newCommand.replace('{output.%s}'%name, outputVariables[name])
		for tr in toRemove:
			del outputVariables[tr]

	return inputPercentWildcard,outputPercentWildcard,newCommand,inputVariables,outputVariables

def expandAsteriskWildcards(variables):
	newVariables = {}
	for name,location in variables.items():
		# Deal with asterisk wildcard by expanding out to all files
		if '*' in location:
			location = glob.glob(location)
			assert len(location) > 0, "No matching files found for wildcard: %s" % value
		newVariables[name] = location
	return newVariables


def addTouchToCommands(command,outputVariables):
	for varName,outputPath in outputVariables.items():
		command += '; touch {output.%s}' % varName
	return command

snakemakeExec = shutil.which('snakemake')

requiredEnvironmentalVariables = ["COMMAND","DATADIR"]
missingVariables = []
for v in requiredEnvironmentalVariables:
	if os.environ.get(v) is None:
		missingVariables.append(v)

if not missingVariables == []:
	print("ERROR: Missing required environmental variables: %s" % (str(missingVariables)))
	print("This Snakefile uses environmental variables as input parameters")
	print()
	print("Example usage:")
	print("  COMMAND='make' DATADIR='~/data' snakemake -s %s" % __file__)
	print()
	print("  COMMAND is a command from the 'run' section of the pubrunner.yml file. It may contain wildcards (percent or asterisk) which will be resolved.")
	print("  DATADIR is the location to store the intermediate files produced")
	sys.exit(1)

unprocessedCommand = os.environ.get("COMMAND")
dataDir = os.environ.get("DATADIR")

if not os.path.isdir(dataDir):
	os.makedirs(dataDir)

inputPercentWildcard,outputPercentWildcard,command,inputVariables,outputVariables = processCommand(dataDir,unprocessedCommand)

checkVariables(inputVariables,outputVariables)

inputVariables = expandAsteriskWildcards(inputVariables)

expectedOutputFiles = predictOutputFiles(inputVariables,outputVariables)

command = addTouchToCommands(command,outputVariables)

#print("command:",command)
#print("inputVariables",inputVariables)
#print("outputVariables",outputVariables)
#print("expectedOutputFiles",expectedOutputFiles)

# If we can determine the output files, we will create a dependency on them to force the main rule to run
if len(expectedOutputFiles) > 0:
	localrules: Wait_For_All_Expected_Output_Files
	rule Wait_For_All_Expected_Output_Files:
		input: expectedOutputFiles

	rule Main_Command:
		input: **inputVariables
		output:	**outputVariables
		shell: command
	
# If we can't determine the output files, we will not have a main dependency rule and exclude the output file list from this rule which will then force snakemake to run this
elif inputPercentWildcard == False and outputPercentWildcard == False:
	rule Main_Command_But_Unknown_Output_Files:
		input: **inputVariables
		output:	**outputVariables
		shell: command
	

