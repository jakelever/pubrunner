import pubrunner
import argparse
import hashlib
import json

def md5(text):
	if isinstance(text,list):
		text = "\n".join(text)

	m = hashlib.md5()
	m.update(text.encode('utf8'))
	return m.hexdigest()

def main():
	parser = argparse.ArgumentParser(description='Calculate MD5 hashes for the different sections of a Pubmed file. Used to evaluate the Pubmed updates')
	parser.add_argument('--pubmedXML',required=True,type=str,help='Pubmed XML file to calculate hashes for')
	parser.add_argument('--outHashJSON',required=True,type=str,help='Output file (in JSON format) containing hashes associated with each PMID')
	args = parser.parse_args()

	allHashes = {}
	for doc in pubrunner.processMedlineFile(args.pubmedXML):
		pmid = doc['pmid']

		hashes = {}
		hashes['pubYear'] = md5(doc['pubYear'])
		hashes['titleText'] = md5(doc['titleText'])
		hashes['abstractText'] = md5(doc['abstractText'])

		allHashes[pmid] = hashes

	with open(args.outHashJSON,'w') as f:
		json.dump(allHashes,f,indent=2,sort_keys=True)

	print("Hashes for %d documents written to %s" % (len(allHashes),args.outHashJSON))



if __name__ == '__main__':
	main()

