import pubrunner
import argparse
import hashlib
import json
from collections import defaultdict

def md5(text):
	if text is None:
		return ''
	if isinstance(text,list):
		text = "\n".join(text)
	if not isinstance(text,str):
		text = str(text)

	m = hashlib.md5()
	m.update(text.encode('utf8'))
	return m.hexdigest()

def pubmed_hash(pubmedXMLFiles,outHashJSON):
	if not isinstance(pubmedXMLFiles,list):
		pubmedXMLFiles = [pubmedXMLFiles]

	allHashes = defaultdict(dict)
	docCount = 0
	for f in pubmedXMLFiles:
		for doc in pubrunner.processMedlineFile(f):
			pmid = doc['pmid']

			hashes = {}
			hashes['year'] = md5(doc['pubYear'])
			hashes['title'] = md5(doc['title'])
			hashes['abstract'] = md5(doc['abstract'])
			hashes['journal'] = md5(doc['journal'])
			hashes['journalISO'] = md5(doc['journalISO'])

			allHashes[f][pmid] = hashes
			docCount += 1

	with open(outHashJSON,'w') as f:
		json.dump(allHashes,f,indent=2,sort_keys=True)

	print("Hashes for %d documents across %d Pubmed XML files written to %s" % (docCount,len(pubmedXMLFiles),outHashJSON))

def main():
	parser = argparse.ArgumentParser(description='Calculate MD5 hashes for the different sections of a Pubmed file. Used to evaluate the Pubmed updates')
	parser.add_argument('--pubmedXMLFiles',required=True,type=str,help='Comma-delimited Pubmed XML files to calculate hashes for')
	parser.add_argument('--outHashJSON',required=True,type=str,help='Output file (in JSON format) containing hashes associated with each PMID')
	args = parser.parse_args()

	pubmedXMLFiles = args.pubmedXMLFiles.split(',')
	pubmed_hash(pubmedXMLFiles,args.outHashJSON)




if __name__ == '__main__':
	main()

