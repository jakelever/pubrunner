import argparse
from collections import defaultdict
import json
import codecs

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Create word-list from PubChem data')
	parser.add_argument('--pubChemMeshPharmFile',type=str,required=True,help='PMID file from PubChem')
	parser.add_argument('--stopwords',type=str,required=True,help='Stopwords file')
	parser.add_argument('--outFile',type=str,required=True,help='Output file for term names')
	args = parser.parse_args()

	print("Loading PubChem PMID data")
	d = defaultdict(list)
	with codecs.open(args.pubChemMeshPharmFile,'r','utf-8') as f:
		for i,line in enumerate(f):
			#chemid,pmid,count = line.strip().split()
			drugnames = line.strip().split('\t')[0]
			for drugname in drugnames.split(','):
				drugname = drugname.strip()
				if len(drugname) > 3:
					d[i].append(drugname)

	stopwords = set()
	print ("Loading stopwords")
	with codecs.open(args.stopwords,'r','utf-8') as f:
		stopwords = set( [ line.strip().lower() for line in f ] )

	print("Outputting term list to file")
	with open(args.outFile,'w') as f:
		json.dump(d,f,indent=2,sort_keys=True)
	print("Done")


