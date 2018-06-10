import argparse
import math
import re
from collections import defaultdict,Counter

def loadMD5s(filename):
	with open(filename) as f:
		data = [ tuple(line.strip().split()) for line in f ]

	data = { filename:md5 for md5,filename in data }
	return data

def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in range(0, len(l), n):
		yield l[i:i + n]

def extractPMCID(filename):
	re_search = re.search('PMC\d+',filename)
	if re_search:
		return re_search.group(0)
	else:
		return None

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Tool to test out different strategies for grouping PubMed Central Open Access files')
	parser.add_argument('--oldPMCFilelist',required=True,type=str,help='CSV file containing PMCOA metadata')
	parser.add_argument('--oldDir',required=True,type=str,help='Directory with older version of PMCOA')
	parser.add_argument('--oldMD5s',required=True,type=str,help='File containing MD5s of older version of PMCOA')
	parser.add_argument('--newDir',required=True,type=str,help='Directory with newer version of PMCOA')
	parser.add_argument('--newMD5s',required=True,type=str,help='File containing MD5s of newer version of PMCOA')
	parser.add_argument('--groupCount',required=False,type=int,default=300,help='Number of groups to try')
	args = parser.parse_args()

	pmcID2Date = {}
	pmcID2Date = defaultdict(lambda : '0')
	with open(args.oldPMCFilelist) as f:
		header = f.readline()
		for line in f:
			split = line.strip().split(',')
			pmcid = split[2]
			date = split[3]
			#print(list(enumerate(split)))
			pmcID2Date[pmcid] = date
			#assert False

	oldMD5s = loadMD5s(args.oldMD5s)
	newMD5s = loadMD5s(args.newMD5s)

	oldFilenames = set(oldMD5s.keys())
	newFilenames = set(newMD5s.keys())

	missing = oldFilenames.difference(newFilenames)
	brandNew = newFilenames.difference(oldFilenames)
	stillThere = newFilenames.intersection(oldFilenames)


	print("len(missing)=",len(missing))
	print("len(brandNew)=",len(brandNew))
	print("len(stillThere)=",len(stillThere))

	dirty = [ filename for filename in list(stillThere) if oldMD5s[filename] != newMD5s[filename] ]
	dirty += list(missing)
	dirty = set(dirty)
	print("len(dirty)=",len(dirty))

	pmcids = [ extractPMCID(filename) for filename in list(oldFilenames) ]
	pmcidsInMetadata = [ pmcid in pmcID2Date for pmcid in pmcids ]
	print("pmcidsInMetadata",sum(pmcidsInMetadata),len(pmcidsInMetadata))

	ordering = list(oldFilenames)
	ordering = [ (pmcID2Date[extractPMCID(filename)],filename) for filename in ordering ]
	#ordering = [ (filename.split('/')[-1],filename) for filename in list(oldFilenames) ]
	ordering = sorted(ordering)
	ordering = [ filename for sortby,filename in ordering ]
	#ordering = sorted(list(oldFilenames))
	#print(ordering[:100])
	#assert False
	print("len(ordering)=",len(ordering))
	groupSize = int(math.ceil(len(ordering)/args.groupCount))
	print("groupSize=",groupSize)

	groups = list(chunks(ordering, groupSize))
	groups = [ set(g) for g in groups ]
	print("len(groups)=",len(groups))

	dirtyGroups = [ not dirty.isdisjoint(g) for g in groups ]
	#print(dirtyGroups[:10])
	dirtyGroupCount = sum(dirtyGroups)
	print("dirtyGroupCount=",dirtyGroupCount)
