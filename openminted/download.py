#!/usr/bin/env python 
import argparse
import pubrunner
import pubrunner.command_line
import os
import sys

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Main access point for OpenMinTeD Docker component')
	#parser.add_argument('--input',required=True,type=str,help='Input directory')
	parser.add_argument('--output',required=True,type=str,help='Output directory')
	parser.add_argument('--param:resource',required=True,type=str,help='Resource name to download (e.g. PUBMED)')
	args = parser.parse_args()

	#assert os.path.isdir(args.input)
	assert os.path.isdir(args.output)

	resourceName = args.__dict__['param:resource']
	sys.argv = ['pubrunner']
	sys.argv += ['--defaultsettings']
	sys.argv += ['--getresource', resourceName]
	pubrunner.command_line.main()

	resourceInfo = pubrunner.getResourceInfo(resourceName)
	print(resourceInfo)

	#allResourcesDir = os.path.expanduser('~/pubrunner/resources')
	#resourceDir = os.path.join(resourceDir,resourceName)
	globalSettings = pubrunner.getGlobalSettings()
	resourceDir = os.path.expanduser(globalSettings["storage"]["resources"])
	thisResourceDir = os.path.join(resourceDir,resourceName)

	inputFormat = resourceInfo['format']
	outputFormat = 'bioc'

	for root, dirnames, filenames in os.walk(thisResourceDir):
		for filename in filenames:
			inFiles = [os.path.join(root,filename)]
			outFile = os.path.join(args.output,filename)
			pubrunner.convertFiles(inFiles,inputFormat,outFile,outputFormat)

