
from pubrunner.command_line import *
from pubrunner.upload import *
from pubrunner.FTPClient import *
from pubrunner.getresource import *
from pubrunner.pubrun import pubrun,cleanWorkingDirectory
from pubrunner.convert import *
from pubrunner.pubmed_hash import pubmed_hash

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

def launchSnakemake(snakeFilePath,useCluster=True,parameters={}):
	globalSettings = pubrunner.getGlobalSettings()
	
	clusterFlags = ""
	if useCluster and "cluster" in globalSettings:
		assert "options" in globalSettings["cluster"], "Options must also be provided in the cluster settings, e.g. qsub"
		jobs = 1
		if "jobs" in globalSettings["cluster"]:
			jobs = int(globalSettings["cluster"]["jobs"])
		clusterFlags = "--cluster '%s' --jobs %d --latency-wait 60" % (globalSettings["cluster"]["options"],jobs)

	print("\nRunning pubmed_hash commands")
	makecommand = "snakemake %s -s %s" % (clusterFlags,snakeFilePath)

	env = os.environ.copy()
	env.update(parameters)

	retval = subprocess.call(shlex.split(makecommand),env=env)
	if retval != 0:
		raise RuntimeError("Snake make call FAILED (file:%s)" % snakeFilePath)
