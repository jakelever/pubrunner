import argparse
import os
import json
from collections import defaultdict,Counter
import pubrunner
#import numpy as np
import sys
from sys import getsizeof

from sys import getsizeof, stderr
from itertools import chain
from collections import deque
try:
	from reprlib import repr
except ImportError:
	pass

def total_size(o, handlers={}, verbose=False):
	""" Returns the approximate memory footprint an object and all of its contents.

	Automatically finds the contents of the following builtin containers and
	their subclasses:  tuple, list, deque, dict, set and frozenset.
	To search other containers, add handlers to iterate over their contents:

		handlers = {SomeContainerClass: iter,
					OtherContainerClass: OtherContainerClass.get_elements}

	"""
	dict_handler = lambda d: chain.from_iterable(d.items())
	all_handlers = {tuple: iter,
					list: iter,
					deque: iter,
					dict: dict_handler,
					set: iter,
					frozenset: iter,
				   }
	all_handlers.update(handlers)	 # user handlers take precedence
	seen = set()					  # track which object id's have already been seen
	default_size = getsizeof(0)	   # estimate sizeof object without __sizeof__

	def sizeof(o):
		if id(o) in seen:	   # do not double count the same object
			return 0
		seen.add(id(o))
		s = getsizeof(o, default_size)

		if verbose:
			print(s, type(o), repr(o), file=stderr)

		for typ, handler in all_handlers.items():
			if isinstance(o, typ):
				s += sum(map(sizeof, handler(o)))
				break
		return s

	return sizeof(o)


def memReport(variables):
	print('-'*30)
	for var,obj in variables.items():
		if not var.startswith('_'):
			print("%s\t%.1fMB" % (var,total_size(obj) / (1024.0*1024.0)))
			#print("%s\t%.1fB" % (var,getsizeof(obj)))
	print('-'*30)

def gatherPMIDs(inHashDir,outPMIDDir,whichHashes=None,pmidExclusions=None):
	# Check the age of inHashDir files and outPMIDDir files and check if anything is actually needed
	if os.path.isdir(outPMIDDir):
		inHashDir_modifieds = [ os.path.getmtime(os.path.join(root,f)) for root, dir, files in os.walk(inHashDir) for f in files ]
		outPMIDDir_modifieds = [ os.path.getmtime(os.path.join(root,f)) for root, dir, files in os.walk(inHashDir) for f in files ]
	#	print("max(inHashDir_modifieds)",max(inHashDir_modifieds))
	#	print("max(outPMIDDir_modifieds)",max(outPMIDDir_modifieds))
		if max(inHashDir_modifieds) < max(outPMIDDir_modifieds):
			print("No PMID update necessary")
			return

	files = sorted([ os.path.join(inHashDir,f) for f in os.listdir(inHashDir) ])
	pmidToFilename = {}

	pubmedXMLFiles = ['/projects/jlever/pubrunner_data/resources/PUBMED/pubmed19n1000.xml']

	#memReport(locals())

	#for pmid in range(29661075):
	#	pmidToFilename[pmid] = '/projects/jlever/pubrunner_data/resources/PUBMED/pubmed19n1000.xml'

	if True:
		maxPmidInt = -1
		for filename in files:
			
			#continue
			with open(filename) as f:
				hashes = json.load(f)
				keys = list(hashes.keys())
				assert len(keys) == 1
				pubmedXMLFile = keys[0]
				pubmedXMLFiles.append(pubmedXMLFile)

			tempMaxPmid = max( map(int,hashes[pubmedXMLFile].keys()) )
			maxPmidInt = max(maxPmidInt,tempMaxPmid)

		#print('maxPmidInt:',maxPmidInt)

		pubmedXMLFiles = []
		#firstFile = {}
		firstFile = [ None for _ in range(maxPmidInt+1) ]
		versionCounts = [ 0 for _ in range(maxPmidInt+1) ]
		#versionCounts = np.zeros((maxPmidInt+1),dtype=int)

		for filename in files:
			
			#continue
			with open(filename) as f:
				hashes = json.load(f)
				keys = list(hashes.keys())
				assert len(keys) == 1
				pubmedXMLFile = keys[0]
				pubmedXMLFiles.append(pubmedXMLFile)


			for pmid in hashes[pubmedXMLFile].keys():
				pmidInt = int(pmid)
				#if not pmidInt in firstFile:
				if firstFile[pmidInt] is None:
					firstFile[pmidInt] = pubmedXMLFile
				versionCounts[pmidInt] += 1


		#pmidToFilename = { pmid:firstFile[pmid] for pmid,count in versionCounts.items() if count == 1 }
		#pmidToFilename = { pmid:'/projects/jlever/pubrunner_data/resources/PUBMED/pubmed19n1000.xml' for pmid,count in versionCounts.items() if count == 1 }
		#pmidToFilename = { pmid:'/projects/jlever/pubrunner_data/resources/PUBMED/pubmed19n1000.xml' for pmid,count in enumerate(versionCounts) if count == 1 }

		pmidToFilename = list(firstFile)

		#pmidsToSkip = set(pmid for pmid,count in enumerate(versionCounts) if count == 1)
		#versionCounts = None

		
		#print('hashes',getsizeof(hashes))
		#print('pubmedXMLFiles',getsizeof(pubmedXMLFiles))
		#print('firstFile',getsizeof(firstFile))
		#print('versionCounts',getsizeof(versionCounts))
		#print('pmidsToSkip',getsizeof(pmidsToSkip))


		if True:

			runningHashes = {} #defaultdict(lambda : None)
			for filename in reversed(files):
				with open(filename) as f:
					hashes = json.load(f)
					keys = list(hashes.keys())
					assert len(keys) == 1
					pubmedXMLFile = keys[0]

				for pmid in hashes[pubmedXMLFile].keys():
					pmidInt = int(pmid)
					#if pmidInt in pmidsToSkip:

					# Only one version of this PMID so don't need to track changes
					if versionCounts[pmidInt] == 1:
						continue
					#if not pmid.startswith(pmidPrefix):
					#	continue

					if whichHashes is None:
						hashVal = hashes[pubmedXMLFile][pmid]
					else:
						try:
							hashVal = [ hashes[pubmedXMLFile][pmid][h] for h in whichHashes ]
						except KeyError as e:
							raise RuntimeError("The selected hash (%s) from the 'usePubmedHashes' option has not been found in the hash files." % (str(e)))

					#if pmidInt == 1:
					#	print(pmidInt, filename, firstFile[pmidInt], pubmedXMLFile, pmidInt in runningHashes)

					# Check this version against a newer version
					# If this older version is different, leave the pmidToFilename as the newer version and stop looking for this pmid
					if pmidInt in runningHashes and runningHashes[pmidInt] != hashVal:
						#pmidsToSkip.add(pmidInt)
						versionCounts[pmidInt] = 1
						del runningHashes[pmidInt]
					else: # No newer version to compare against, so set the hash and pmidToFilename to this version
						runningHashes[pmidInt] = hashVal
						pmidToFilename[pmidInt] = pubmedXMLFile

					if firstFile[pmidInt] == pubmedXMLFile and pmidInt in runningHashes:
						del runningHashes[pmidInt]
			

	#for pmidPrefix in map(str,range(1,10)):
	if False:
		pmidHashes = defaultdict(list)
		for filename in sorted(files):
			
			#continue
			with open(filename) as f:
				hashes = json.load(f)
				keys = list(hashes.keys())
				assert len(keys) == 1
				pubmedXMLFile = keys[0]
				#pubmedXMLFiles.append(pubmedXMLFile)

			for pmid in hashes[pubmedXMLFile].keys():
				#if not pmid.startswith(pmidPrefix):
				#	continue

				if whichHashes is None:
					hashVal = hashes[pubmedXMLFile][pmid]
				else:
					try:
						hashVal = [ hashes[pubmedXMLFile][pmid][h] for h in whichHashes ]
					except KeyError as e:
						raise RuntimeError("The selected hash (%s) from the 'usePubmedHashes' option has not been found in the hash files." % (str(e)))

				pmidInt = int(pmid)
				if pmidHashes[pmidInt] != hashVal:
					pmidHashes[pmidInt] = hashVal
					pmidToFilename[pmidInt] = pubmedXMLFile
		pmidHashes = None

	#pmidToFilename = {}
	#for pmid in range(29661075):
	#	pmidToFilename[pmid] = '/projects/jlever/pubrunner_data/resources/PUBMED/pubmed19n1000.xml'

	#sys.exit(0)

	filenameToPMIDs = defaultdict(list)
	#filenameToPMIDs = [ [] for _ in pubmedXMLFiles ]
	#for pmid,filename in pmidToFilename.items():
	#	filenameToPMIDs[filename].append(pmid)
	for pmid,filename in enumerate(pmidToFilename):
		if filename is not None:
			filenameToPMIDs[filename].append(pmid)

	if not os.path.isdir(outPMIDDir):
		os.makedirs(outPMIDDir)

	for filename in pubmedXMLFiles:
		basename = os.path.basename(filename)
		outName = os.path.join(outPMIDDir,basename+'.pmids')

		#pmids = [ pmid for pmid,f in enumerate(pmidToFilename) if f == filename ]
		pmids = filenameToPMIDs[filename]

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

	#memReport(locals())

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
