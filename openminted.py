#!/usr/bin/env python 
import argparse
import pubrunner
import os

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Main access point for OpenMinTeD Docker component')
	parser.add_argument('--input',required=True,type=str,help='Input directory')
	parser.add_argument('--output',required=True,type=str,help='Output directory')
	parser.add_argument('--param:inputFormat',required=True,type=str,help='Input format')
	parser.add_argument('--param:outputFormat',required=True,type=str,help='Output format')
	args = parser.parse_args()

	assert os.path.isdir(args.input)
	assert os.path.isdir(args.output)

	inputFormat = args.__dict__['param:inputFormat']
	outputFormat = args.__dict__['param:outputFormat']

	for f in os.listdir(args.input):
		inFiles = [os.path.join(args.input,f)]
		outFile = os.path.join(args.output,f)
		pubrunner.convertFiles(inFiles,inputFormat,outFile,outputFormat)

