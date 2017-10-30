import argparse
import os

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Tool for adding up term frequency counts')
	parser.add_argument('--inDir',type=str,required=True,help='Directory containing term counts')
	parser.add_argument('--outFile',type=str,required=True,help='File to output total')
	args = parser.parse_args()

	totalcount = 0
	for filename in os.listdir(args.inDir):
		fullpath = os.path.join(args.inDir,filename)
		with open(fullpath) as f:
			count = int(f.read().strip())
			totalcount += count

	with open(args.outFile,'w') as f:
		f.write('%d\n' % totalcount)

