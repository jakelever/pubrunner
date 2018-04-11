#!/usr/bin/env python 
import argparse
import pubrunner
import pubrunner.command_line
import os
import sys

def deleteNonXMIFiles(directory):
	for root, dirs, files in os.walk(directory):
		toDelete = [ os.path.join(root,f) for f in files if not f.lower().endswith('.xmi') ]
		for f in toDelete:
			os.remove(f)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Main access point for OpenMinTeD Docker component')
	parser.add_argument('--input',required=True,type=str,help='Input directory')
	parser.add_argument('--output',required=True,type=str,help='Output directory')
	parser.add_argument('--param:language',required=False,type=str,help='Ignored language parameter')
	args = parser.parse_args()

	assert os.path.isdir(args.input)
	assert os.path.isdir(args.output)

	# Remove non XMI files (e.g. PDFs, spec files, etc)
	deleteNonXMIFiles(args.input)

	inputFormat = 'uimaxmi'
	githubRepo = 'https://github.com/jakelever/Ab3P'

	sys.argv = ['pubrunner']
	sys.argv += ['--defaultsettings']
	sys.argv += ['--forceresource_dir', args.input]
	sys.argv += ['--forceresource_format', inputFormat]
	sys.argv += ['--outputdir', args.output]
	sys.argv += [githubRepo]
	pubrunner.command_line.main()
