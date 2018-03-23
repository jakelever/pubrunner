#!/usr/bin/env python 
import argparse
import pubrunner
import pubrunner.command_line
import os
import sys

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Main access point for OpenMinTeD Docker component')
	parser.add_argument('--input',required=True,type=str,help='Input directory')
	parser.add_argument('--output',required=True,type=str,help='Output directory')
	parser.add_argument('--param:githubrepo',required=True,type=str,help='Github repo to execute')
	args = parser.parse_args()

	assert os.path.isdir(args.input)
	assert os.path.isdir(args.output)

	inputFormat = 'uimaxmi'
	githubRepo = args.__dict__['param:githubrepo']

	sys.argv = ['pubrunner']
	sys.argv += ['--defaultsettings']
	sys.argv += ['--forceresource_dir', args.input]
	sys.argv += ['--forceresource_format', inputFormat]
	sys.argv += ['--outputdir', args.output]
	sys.argv += [githubRepo]
	pubrunner.command_line.main()
