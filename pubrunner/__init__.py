
from pubrunner.command_line import *
from pubrunner.upload import *
from pubrunner.FTPClient import *
from pubrunner.getresource import *
from pubrunner.pubrun import pubrun

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

globalSettings = None
def getGlobalSettings():
	global globalSettings
	if globalSettings is None:
		settingsYamlFile = findSettingsFile()
		globalSettings = loadYAML(settingsYamlFile)

	return globalSettings
