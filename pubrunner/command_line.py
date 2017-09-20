import pubrunner
import sys
import argparse
import os
import git
import tempfile
import shutil
import logging
import traceback
import yaml
import json
import subprocess
import shlex
import wget
import gzip
import hashlib
import six
import six.moves.urllib as urllib
import time
from six.moves import reload_module
import ftplib
import ftputil
from collections import OrderedDict
import re

def cloneGithubRepoToTempDir(githubRepo):
	tempDir = tempfile.mkdtemp()
	Repo.clone_from(githubRepo, tempDir)
	return tempDir

def main():
	parser = argparse.ArgumentParser(description='PubRunner will manage the download of needed resources for a text mining tool, build and execute it and then share the results publicly')
	parser.add_argument('codebase',nargs='?',type=str,help='Code base containing the text mining tool to execute. Code base should contain a pubrunner.yml file. The code base can be a directory, Github repo or archive')
	parser.add_argument('--snakefileonly',action='store_true',help='Create the Snakefile, do not execute each step')
	parser.add_argument('--test',action='store_true',help='Run the test functionality instead of the full run')
	parser.add_argument('--getResource',required=False,type=str,help='Fetch a specific resource (instead of doing a normal PubRunner run). This is really only needed for debugging and understanding resources.')

	args = parser.parse_args()

	if args.getResource:
		location = pubrunner.getResource(args.getResource)
		print("Downloaded latest version of resource '%s' to location:" % args.getResource)
		print(location)
		print("")
		print("Exiting without doing PubRun")
		sys.exit(0)
	
	if not args.codebase:
		print("codebase must be provided (if not downloading individual resources)")
		parser.print_help()
		sys.exit(1)

	execute = not args.snakefileonly

	if os.path.isdir(args.codebase):
		pubrunner.pubrun(args.codebase,args.test,execute)
	elif args.codebase.startswith('https://github.com/'):
		tempDir = ''
		try:
			tempDir = cloneGithubRepoToTempDir(args.codebase)
			pubrunner.pubrun(tempDir,args.test,execute)
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


