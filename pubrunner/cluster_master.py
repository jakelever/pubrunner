#import drmaa
import argparse
import subprocess
import shlex
import codecs

def runLocally(commandsFilename):
	with codecs.open(commandsFilename) as f:
		for command in f:
			#split = shlex.split(command.strip())
			command = command.strip()
			print("Executing: %s" % command)
			return_code = subprocess.call(command, shell=True)
			assert return_code == 0, "Command (%s) gave non-zero error (%d)" % (command,return_code)
			

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Cluster tool for DRMAA-compliant clusters (e.g. SGE/Slurm) for running large groups of jobs')
	parser.add_argument('--jobList',type=str,required=True,help='File containing one row per command')
	parser.add_argument('--local',action='store_true',help='Whether to actually just run the command on this node and ignore using a cluster')

	args = parser.parse_args()

	assert args.local == True, "Cluster is on the todo list"

	if args.local:
		runLocally(args.jobList)

