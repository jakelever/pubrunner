import argparse
from collections import defaultdict
import json
import codecs

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Create word-list from PubChem data')
	parser.add_argument('--pubChemPMIDsFile',type=str,required=True,help='PMID file from PubChem')
	parser.add_argument('--pubChemSynonymsFile',type=str,required=True,help='Synonyms file from PubChem')
	parser.add_argument('--stopwords',type=str,required=True,help='Stopwords file')
	parser.add_argument('--outFile',type=str,required=True,help='Output file for term names')
	args = parser.parse_args()

	print("Loading PubChem PMID data")
	chemidsInPubMed = set()
	with codecs.open(args.pubChemPMIDsFile,'r','utf-8') as f:
		for line in f:
			chemid,pmid,count = line.strip().split()
			chemidsInPubMed.add(chemid)

	stopwords = set()
	print ("Loading stopwords")
	with codecs.open(args.stopwords,'r','utf-8') as f:
		stopwords = set( [ line.strip().lower() for line in f ] )

	print("Loading PubChem synonym data (and filtering using PMID data)")
	d = defaultdict(list)
	with codecs.open(args.pubChemSynonymsFile,'r','utf-8') as f:
		for i,line in enumerate(f):
			chemid,term = line.strip().split('\t')
			if chemid in chemidsInPubMed:
				if len(term) >= 3 and not term.lower() in stopwords:
					d[chemid].append(term)
			if (i%100000) == 0:
				print(i, term)

	print("Outputting term list to file")
	with open(args.outFile,'w') as f:
		json.dump(d,f,indent=2,sort_keys=True)
	print("Done")


