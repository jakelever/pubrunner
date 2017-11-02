import sys
import glob
import re
import six
import os
import shutil

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
		if i == 0:
		 	allWildcardValues = wildcardValues
		else:
		 	allWildcardValues = allWildcardValues.intersection(wildcardValue)

	inputContainsPercentWildcards = isinstance(allWildcardValues,set)
	if inputContainsPercentWildcards:
		assert len(allWildcardValues) > 0, "Percent wildcards on input unable to match to any input files"
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
	regex = re.compile("\{(?P<type>(IN|OUT)):(?P<value>\S*)\}")
	variablesWithLocations = []
	for m in regex.finditer(command):
		variableWithLocation = (m.start(), m.end(), m.groupdict()['type'], m.groupdict()['value'])
		variablesWithLocations.append(variableWithLocation)
	variablesWithLocations = sorted(variablesWithLocations,reverse=True)

	inputVariables,outputVariables = {},{}
	newCommand = command
	for i,(start,end,vartype,value) in enumerate(variablesWithLocations):
		assert vartype == 'IN' or vartype == 'OUT'

		snakevartype = 'input' if vartype == 'IN' else 'output'
		name = "%s%04d" % (vartype,i)
		newCommand = newCommand[:start] + '{%s.%s}' % (snakevartype,name) + newCommand[end:]

		location = os.path.join(dataDir,value).replace('%','{wildcard}')

		if vartype == 'IN':
			inputVariables[name] = location
		elif vartype == 'OUT':
			outputVariables[name] = location

	return newCommand,inputVariables,outputVariables

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

command,inputVariables,outputVariables = processCommand(dataDir,unprocessedCommand)

checkVariables(inputVariables,outputVariables)
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
else:
	rule Main_Command_But_Unknown_Output_Files:
		input: **inputVariables
		output:	**outputVariables
		shell: command
	

