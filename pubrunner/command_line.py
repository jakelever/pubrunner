import pubrunner
import sys
import argparse
import os
import tempfile
import shutil
import logging
import traceback
import pyfiglet
import git

def cloneGithubRepoToTempDir(githubRepo):
	tempDir = tempfile.mkdtemp()
	git.Repo.clone_from(githubRepo, tempDir)
	return tempDir

def main():
	parser = argparse.ArgumentParser(description='PubRunner will manage the download of needed resources for a text mining tool, build and execute it and then share the results publicly')
	parser.add_argument('codebase',nargs='?',type=str,help='Code base containing the text mining tool to execute. Code base should contain a pubrunner.yml file. The code base can be a directory, Github repo or archive')
	parser.add_argument('--defaultsettings',action='store_true',help='Use default .pubrunner.settings.xml. Ignore ~/.pubrunner.settings.yml if it exists.')
	parser.add_argument('--ignorecluster',action='store_true',help='Ignore any cluster settings and run everything locally')
	parser.add_argument('--clean',action='store_true',help='Remove the existing working directory')
	parser.add_argument('--test',action='store_true',help='Run the test functionality instead of the full run')
	parser.add_argument('--getResource',required=False,type=str,help='Fetch a specific resource (instead of doing a normal PubRunner run). This is really only needed for debugging and understanding resources.')

	args = parser.parse_args()

	print(pyfiglet.figlet_format('PubRunner', font='cyberlarge', justify='center'))
	print()

	if args.getResource:
		location = pubrunner.getResource(args.getResource)
		print("Downloaded latest version of resource '%s' to location:" % args.getResource)
		print(location)
		print("")
		print("Exiting without doing PubRun")
		sys.exit(0)
	
	if not args.codebase:
		print("ERROR: codebase must be provided (if not downloading individual resources)")
		print()
		parser.print_help()
		sys.exit(1)

	if args.defaultsettings:
		globalSettings = pubrunner.getGlobalSettings(useDefault=True)

	if args.ignorecluster:
		globalSettings = pubrunner.getGlobalSettings()
		if "cluster" in globalSettings:
			del globalSettings["cluster"]

	if os.path.isdir(args.codebase):
		if args.clean:
			pubrunner.cleanWorkingDirectory(args.codebase,args.test)
		else:
			pubrunner.pubrun(args.codebase,args.test)
	elif args.codebase.startswith('https://github.com/'):
		tempDir = ''
		try:
			print("Cloning Github repo")
			tempDir = cloneGithubRepoToTempDir(args.codebase)
			if args.clean:
				pubrunner.cleanWorkingDirectory(tempDir,args.test)
			else:
				pubrunner.pubrun(tempDir,args.test)
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


