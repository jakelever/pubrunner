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
	parser.add_argument('--forceresource_dir',type=str,required=False,help='Ignore the resources for the project and use this directory instead for the first one only (all others are empty)')
	parser.add_argument('--forceresource_format',type=str,required=False,help='The format of the resource to use instead for this run')
	parser.add_argument('--outputdir',type=str,required=False,help='Where to store the results of the run (instead of the default location defined by ~/.pubrunner.settings.yml)')
	parser.add_argument('--nogetresource',action='store_true',help='Do not fetch resources before executing a project. Will fail if old versions of resources do not already exists.')
	parser.add_argument('--test',action='store_true',help='Run the test functionality instead of the full run')
	parser.add_argument('--getresource',required=False,type=str,help='Fetch a specific resource (instead of doing a normal PubRunner run). This is really only needed for debugging and understanding resources.')

	args = parser.parse_args()

	print(pyfiglet.figlet_format('PubRunner', font='cyberlarge', justify='center'))
	print()

	if args.defaultsettings:
		globalSettings = pubrunner.getGlobalSettings(useDefault=True)

	if args.forceresource_dir:
		args.forceresource_dir = os.path.abspath(args.forceresource_dir)
	if args.outputdir:
		args.outputdir = os.path.abspath(args.outputdir)

	if args.getresource:
		location = pubrunner.getResource(args.getresource)
		print("Downloaded latest version of resource '%s' to location:" % args.getresource)
		print(location)
		print("")
		print("Exiting without doing PubRun")
		return
	
	if not args.codebase:
		print("ERROR: codebase must be provided (if not downloading individual resources)")
		print()
		parser.print_help()
		sys.exit(1)

	if args.ignorecluster:
		globalSettings = pubrunner.getGlobalSettings()
		if "cluster" in globalSettings:
			del globalSettings["cluster"]

	if os.path.isdir(args.codebase):
		if args.clean:
			pubrunner.cleanWorkingDirectory(args.codebase,args.test)
		else:
			pubrunner.pubrun(args.codebase,args.test,(not args.nogetresource),forceresource_dir=args.forceresource_dir,forceresource_format=args.forceresource_format,outputdir=args.outputdir)
	elif args.codebase.startswith('https://github.com/'):
		tempDir = ''
		try:
			print("Cloning Github repo")
			tempDir = cloneGithubRepoToTempDir(args.codebase)
			if args.clean:
				pubrunner.cleanWorkingDirectory(tempDir,args.test,(not args.nogetresource))
			else:
				pubrunner.pubrun(tempDir,args.test,(not args.nogetresource),forceresource_dir=args.forceresource_dir,forceresource_format=args.forceresource_format,outputdir=args.outputdir)
			shutil.rmtree(tempDir)
		except:
			if os.path.isdir(tempDir):
				shutil.rmtree(tempDir)
			logging.error(traceback.format_exc())
			raise

	elif os.path.isfile(args.codebase):
		raise RuntimeError("Not implemented")
	else:
		raise RuntimeError("Not sure what to do with codebase: %s. Doesn't appear to be a directory, Github repo or archive" % args.codebase)


