import argparse
import os
import json
from collections import defaultdict,Counter
import pubrunner

def gatherPMIDs(inHashDir,outPMIDDir,whichHashes=None,pmidExclusions=None):
	# Check the age of inHashDir files and outPMIDDir files and check if anything is actually needed
	if os.path.isdir(outPMIDDir):
		inHashDir_modifieds = [ os.path.getmtime(os.path.join(root,f)) for root, dir, files in os.walk(inHashDir) for f in files ]
		outPMIDDir_modifieds = [ os.path.getmtime(os.path.join(root,f)) for root, dir, files in os.walk(inHashDir) for f in files ]
		if max(inHashDir_modifieds) < max(outPMIDDir_modifieds):
			print("No PMID update necessary")
			return

	files = sorted([ os.path.join(inHashDir,f) for f in os.listdir(inHashDir) ])
	pmidToFilename = {}

	pubmedXMLFiles = []
	firstFile = {}
	versionCounts = Counter()
	for filename in files:
		with open(filename) as f:
			hashes = json.load(f)
			keys = list(hashes.keys())
			assert len(keys) == 1
			pubmedXMLFile = keys[0]
			pubmedXMLFiles.append(pubmedXMLFile)

		for pmid in hashes[pubmedXMLFile].keys():
			pmidInt = int(pmid)
			if not pmidInt in firstFile:
				firstFile[pmidInt] = pubmedXMLFile
			versionCounts[pmidInt] += 1

	# Set up the filenames for PMIDs with only one version (which is the vast majority)
	pmidToFilename = { pmid:firstFile[pmid] for pmid,count in versionCounts.items() if count == 1 }
	pmidsToSkip = set(pmidToFilename.keys())

	# Now we iterate through (looking at only those with multiple versions) and check if the hashes change
	pmidHashes = defaultdict(list)
	for filename in sorted(files):
		with open(filename) as f:
			hashes = json.load(f)
			keys = list(hashes.keys())
			assert len(keys) == 1
			pubmedXMLFile = keys[0]

		for pmid in hashes[pubmedXMLFile].keys():
			pmidInt = int(pmid)
			if pmidInt in pmidsToSkip:
				continue

			if whichHashes is None:
				hashVal = hashes[pubmedXMLFile][pmid]
			else:
				try:
					hashVal = [ hashes[pubmedXMLFile][pmid][h] for h in whichHashes ]
				except KeyError as e:
					raise RuntimeError("The selected hash (%s) from the 'usePubmedHashes' option has not been found in the hash files." % (str(e)))

			if pmidHashes[pmidInt] != hashVal:
				pmidHashes[pmidInt] = hashVal
				pmidToFilename[pmidInt] = pubmedXMLFile


	filenameToPMIDs = defaultdict(list)
	for pmid,filename in pmidToFilename.items():
		filenameToPMIDs[filename].append(pmid)

	if not os.path.isdir(outPMIDDir):
		os.makedirs(outPMIDDir)

	for filename in pubmedXMLFiles:
		basename = os.path.basename(filename)
		outName = os.path.join(outPMIDDir,basename+'.pmids')

		if filename in filenameToPMIDs:
			pmids = sorted(filenameToPMIDs[filename])
		else:
			pmids = []

		if not pmidExclusions is None:
			pmids = [ pmid for pmid in pmids if not pmid in pmidExclusions ]
		
		fileAlreadyExists = os.path.isfile(outName)
		if fileAlreadyExists:
			timestamp = os.path.getmtime(outName)
			beforeHash = pubrunner.calcSHA256(outName)

		with open(outName,'w') as f:
			for pmid in pmids:
				f.write("%d\n" % pmid)

		if fileAlreadyExists:
			afterHash = pubrunner.calcSHA256(outName)
			if beforeHash == afterHash: # File hasn't changed so move the modified date back
				os.utime(outName,(timestamp,timestamp))

def main():
	parser = argparse.ArgumentParser('Use a set of Pubmed hashes to generate the list of PMIDs that should be processed for each file')
	parser.add_argument('--hashDir',required=True,type=str,help='Directory containing hash JSON files')
	parser.add_argument('--whichHashes',type=str,help='Comma-delimited list of which hashes to use')
	parser.add_argument('--outDir',required=True,type=str,help='Directory to output PMID lists')
	args = parser.parse_args()

	if args.whichHashes:
		whichHashes = args.whichHashes.split(',')
	else:
		whichHashes = None

	gatherPMIDs(args.hashDir,args.outDir,whichHashes)



if __name__ == '__main__':
	main()
