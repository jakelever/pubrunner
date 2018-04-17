#!/usr/bin/env python 
import argparse
import os
import sys
import shutil

def copytree(src, dst, symlinks=False, ignore=None):
	for item in os.listdir(src):
		s = os.path.join(src, item)
		d = os.path.join(dst, item)
		if os.path.isdir(s):
			shutil.copytree(s, d, symlinks, ignore)
		else:
			shutil.copy2(s, d)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Main access point for OpenMinTeD Docker component')
	parser.add_argument('--input',required=True,type=str,help='Input directory')
	parser.add_argument('--output',required=True,type=str,help='Output directory')
	parser.add_argument('--param:language',required=False,type=str,help='Ignored language parameter')
	args = parser.parse_args()

	assert os.path.isdir(args.input)

	if not os.path.isdir(args.output):
		os.makedirs(args.output)

	copytree(args.input,args.output)

