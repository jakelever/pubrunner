import argparse
import os
import codecs
from collections import Counter

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Merges cooccurrences files down to a single file')
	parser.add_argument('--inDir',type=str,required=True,help='Directory containing cooccurrence files. Expected to be tab-delimited three columns (with IDs in first to columns and cooccurrence count in third)')
	parser.add_argument('--outFile',type=str,required=True,help='File to output combined cooccurrence data')

	args = parser.parse_args()

	assert os.path.isdir(args.inDir)

	counter = Counter()
	for filename in os.listdir(args.inDir):
		fullpath = os.path.join(args.inDir,filename)
		with codecs.open(fullpath,'r','utf-8') as f:
			for line in f:
				a,b,count = line.strip().split('\t')
				counter[(a,b)] += int(count)

	keys = sorted(counter.keys())
	with codecs.open(args.outFile,'w','utf-8') as outF:
		for a,b in keys:
			count = counter[(a,b)]
			outF.write("%s\t%s\t%d\n" % (a,b,count))

	print ("Complete.")

