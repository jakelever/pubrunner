import argparse
import os
import json
from collections import defaultdict

def main():
	parser = argparse.ArgumentParser('Use a set of Pubmed hashes to generate the list of PMIDs that should be processed for each file')
	parser.add_argument('--hashDir',required=True,type=str,help='Directory containing hash JSON files')
	parser.add_argument('--whichHashes',required=True,type=str,help='Comma-delimited list of which hashes to use')
	parser.add_argument('--outDir',required=True,type=str,help='Directory to output PMID lists')
	args = parser.parse_args()

	files = sorted([ os.path.join(args.hashDir,f) for f in os.listdir(args.hashDir) ])
	hashes = {}
	for filename in files:
		print(filename)
		with open(filename) as f:
			tmpHashes = json.load(f)
			hashes.update(tmpHashes)

	whichHashes = args.whichHashes.split(',')

	pmidHashes = defaultdict(list)
	pmidToFilename = {}
	for filename in sorted(hashes.keys()):
		for pmid in hashes[filename].keys():
			hashVal = [ hashes[filename][pmid][h] for h in whichHashes ]
			pmidInt = int(pmid)
			if pmidHashes[pmidInt] != hashVal:
				pmidHashes[pmidInt] = hashVal
				pmidToFilename[pmidInt] = filename

	filenameToPMIDs = defaultdict(list)
	for pmid,filename in pmidToFilename.items():
		filenameToPMIDs[filename].append(pmid)

	if not os.path.isdir(args.outDir):
		os.makedirs(args.outDir)

	for filename in sorted(hashes.keys()):
		basename = os.path.basename(filename)
		outName = os.path.join(args.outDir,basename+'.pmids')
		pmids = sorted(filenameToPMIDs[filename])
		with open(outName,'w') as f:
			for pmid in pmids:
				f.write("%d\n" % pmid)


if __name__ == '__main__':
	main()
