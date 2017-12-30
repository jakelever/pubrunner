
import pubrunner
import os
import shlex
import subprocess

def launchSnakemake(snakeFilePath,useCluster=True,parameters={}):
	globalSettings = pubrunner.getGlobalSettings()
	
	clusterFlags = ""
	if useCluster and "cluster" in globalSettings:
		clusterSettings = globalSettings["cluster"]
		jobs = 1
		if "jobs" in globalSettings["cluster"]:
			jobs = int(globalSettings["cluster"]["jobs"])
		clusterFlags = "--jobs %d --latency-wait 60" % jobs

		if "drmaa" in clusterSettings and clusterSettings["drmaa"] == True:
			clusterFlags += ' --drmaa'
		elif "drmaa" in clusterSettings:
			clusterFlags += " --drmaa ' %s'" % clusterSettings["drmaa"]
		elif "options" in clusterSettings:
			clusterFlags += " --cluster '%s'" % clusterSettings["options"]
		else:
			raise RuntimeError("Cluster must either have drmaa = true or provide options (e.g. using qsub)")

	makecommand = "snakemake %s --nolock -s %s" % (clusterFlags,snakeFilePath)

	env = os.environ.copy()
	env.update(parameters)

	retval = subprocess.call(shlex.split(makecommand),env=env)
	if retval != 0:
		raise RuntimeError("Snake make call FAILED (file:%s)" % snakeFilePath)
