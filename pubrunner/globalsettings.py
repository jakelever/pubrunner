
import pubrunner
import yaml
import os
import sys
import codecs
import shutil

def loadYAML(yamlFilename):
	yamlData = None
	with open(yamlFilename,'r') as f:
		try:
			yamlData = yaml.load(f)
		except yaml.YAMLError as exc:
			print(exc)
			raise
	return yamlData

def promptuser(prompt='> ', accepted=None):
	while True:
		print(prompt,end='')
		sys.stdout.flush()
		userinput = sys.stdin.readline().strip()
		if accepted is None or userinput in accepted:
			break
		else:
		 	print("Input not allowed. Must be one of %s" % str(accepted))
	return userinput

def getDefaultGlobalSettingsPath():
	defaultPath = os.path.join(pubrunner.__path__[0],'pubrunner.settings.default.yml')
	assert os.path.isfile(defaultPath), "Unable to find default settings file"
	return defaultPath

def setupDefaultGlobalSettingsFile(globalSettingsPath):
	defaultPath = getDefaultGlobalSettingsPath()
	with codecs.open(defaultPath,'r','utf-8') as f:
		defaultSettings = f.read()

	print("No global settings file (%s) was found. Do you want to install the default one (below)?\n" % globalSettingsPath)
	print(defaultSettings)

	userinput = promptuser(prompt='(Y/N): ',accepted=['Y','N','y','n'])
	if userinput.lower() == 'y':

		shutil.copy(defaultPath,globalSettingsPath)

		print("Default settings installed. Do you want to continue with this run?")
		userinput = promptuser(prompt='(Y/N): ',accepted=['Y','N','y','n'])
		if userinput.lower() == 'n':
			print("Exiting...")
			sys.exit(0)
		
globalSettings = None
def getGlobalSettings(useDefault=False):
	global globalSettings
	if globalSettings is None:
		if useDefault:
			globalSettingsPath = getDefaultGlobalSettingsPath()
		else:
			homeDirectory = os.path.expanduser("~")
			globalSettingsPath = os.path.join(homeDirectory,'.pubrunner.settings.yml')
			if not os.path.isfile(globalSettingsPath):
				setupDefaultGlobalSettingsFile(globalSettingsPath)
			assert os.path.isfile(globalSettingsPath), "Unable to find ~/.pubrunner.settings.yml file."

		globalSettings = loadYAML(globalSettingsPath)

	return globalSettings
	

