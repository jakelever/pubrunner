import argparse
import os
import json
from collections import defaultdict
import pubrunner

def gatherPMIDs(inHashDir,outPMIDDir,whichHashes=None,pmidExclusions=None):
	# Check the age of inHashDir files and outPMIDDir files and check if anything is actually needed
	#if os.path.isdir(outPMIDDir):
	#	inHashDir_modifieds = [ os.path.getmtime(os.path.join(root,f)) for root, dir, files in os.walk(inHashDir) for f in files ]
	#	outPMIDDir_modifieds = [ os.path.getmtime(os.path.join(root,f)) for root, dir, files in os.walk(inHashDir) for f in files ]
	#	print("max(inHashDir_modifieds)",max(inHashDir_modifieds))
	#	print("min(outPMIDDir_modifieds)",min(outPMIDDir_modifieds))
	#	if max(inHashDir_modifieds) < min(outPMIDDir_modifieds):
	#		print("No PMID update necessary")
	#		return

	files = sorted([ os.path.join(inHashDir,f) for f in os.listdir(inHashDir) ])
	hashes = {}
	for filename in files:
		with open(filename) as f:
			tmpHashes = json.load(f)
			hashes.update(tmpHashes)

	pmidHashes = defaultdict(list)
	pmidToFilename = {}
	for filename in sorted(hashes.keys()):
		for pmid in hashes[filename].keys():
			if whichHashes is None:
				hashVal = hashes[filename][pmid]
			else:
				try:
					hashVal = [ hashes[filename][pmid][h] for h in whichHashes ]
				except KeyError as e:
					raise RuntimeError("The selected hash (%s) from the 'usePubmedHashes' option has not been found in the hash files." % (str(e)))

			pmidInt = int(pmid)
			if pmidHashes[pmidInt] != hashVal:
				pmidHashes[pmidInt] = hashVal
				pmidToFilename[pmidInt] = filename

	filenameToPMIDs = defaultdict(list)
	for pmid,filename in pmidToFilename.items():
		filenameToPMIDs[filename].append(pmid)

	if not os.path.isdir(outPMIDDir):
		os.makedirs(outPMIDDir)

	for filename in sorted(hashes.keys()):
		basename = os.path.basename(filename)
		outName = os.path.join(outPMIDDir,basename+'.pmids')
		pmids = sorted(filenameToPMIDs[filename])

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
