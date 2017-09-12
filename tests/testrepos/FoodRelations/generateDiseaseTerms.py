"""
This script is used to build a word-list of relevant cancer specific terms from the Disease Ontology and UMLS Metathesaurus.
"""
import argparse
import sys
import codecs
import pronto
from collections import defaultdict
import json

def augmentTermList(terms):
	"""
	Do some filtering of terms
	
	Args:
		terms (list of strings): List of strings of terms
		
	Returns:
		list of augmente strings
	"""
	
	# Lower case everything (if not already done anyway)
	terms = [ t.lower() for t in terms ]
	
	# Filter out smaller terms except the allowed ones
	terms = [ t for t in terms if len(t) > 3 ]

	# Filter out terms with a comma
	terms = [ t for t in terms if not ',' in t ]

	# Sorted and unique the terms back together
	merged = sorted(list(set(terms)))
	return merged

def findTerm(ont,name):
	"""
	Searches an ontology for a specific term name and returns the first hit

	Args:
		ont (pronto Ontology): Ontology to search
		name (str): Search query

	Returns:
		pronto Ontology: Term that matched name or None if not found
	"""
	for term in ont:
		if term.name == name:
			return term
	return None



def getCUIDs(term):
	"""
	Gets all CUIDs for a given pronto Ontology object (from the xrefs)

	Args:
		term (pronto Ontology): Term from ontology to extract CUIDs for

	Returns:
		list of CUIDs
	"""
	cuids = []
	if 'xref' in term.other:
		for xref in term.other['xref']:
			if xref.startswith('UMLS_CUI'):
				cuid = xref[9:]
				cuids.append(cuid)
	return cuids

def getSynonyms(term):
	"""
	Gets all synonyms for a given pronto Ontology object (with IDs removed)

	Args:
		term (pronto Ontology): Term from ontology to extract CUIDs for

	Returns:
		list of synonyms
	"""
	synonyms = []
	if 'synonym' in term.other:
		for s in term.other['synonym']:
			if 'EXACT' in s:
				pos = s.index('EXACT')
				before = s[:pos].strip()
				if before[0] == '"' and before[-1] == '"':
					synonyms.append(before.strip('"'))
	return synonyms



def loadMetathesaurus(filename):
	"""
	Loads the UMLS metathesaurus into a dictionary where CUID relates to a set of terms. Only English terms are included

	Args:
		filename (str): Filename of UMLS Concept file (MRCONSO.RRF)

	Returns:
		Dictionary where each key (CUID) points to a list of strings (terms)
	"""
	meta = defaultdict(list)
	with codecs.open(filename,'r','utf8') as f:
		for line in f:
			split = line.split('|')
			cuid = split[0]
			lang = split[1]
			term = split[14]
			if lang != 'ENG':
				continue
			meta[cuid].append(term)
	return meta
	
if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Generate term list from Disease Ontology and UMLS Metathesarus for terms')
	parser.add_argument('--diseaseOntologyFile', required=True, type=str, help='Path to the Disease Ontology OBO file')
	parser.add_argument('--stopwords',required=False,type=str,help='File containing terms to ignore')
	parser.add_argument('--umlsConceptFile', required=False, type=str, help='Path on the MRCONSO.RRF file in UMLS metathesaurus')
	parser.add_argument('--outFile', required=True, type=str, help='Path to output wordlist file')
	args = parser.parse_args()

	if args.umlsConceptFile:
		print "Loading metathesaurus..."
		metathesaurus = loadMetathesaurus(args.umlsConceptFile)

	print "Loading disease ontology..."
	ont = pronto.Ontology(args.diseaseOntologyFile)
	cancerTerm = findTerm(ont,'cancer')

	stopwords = set()
	if args.stopwords:
		print "Loading stopwords..."
		with codecs.open(args.stopwords,'r','utf8') as f:
			stopwords = [ line.strip().lower() for line in f ]
			stopwords = set(stopwords)

	print "Processing..."
	allterms = {}
	# Skip down to the children of the cancer term and then find all their descendents (recursive children)
	for term in ont: #.rchildren(): #cancerTerm.children.rchildren():

		if args.umlsConceptFile:
			# Get the CUIDs for this term
			cuids = getCUIDs(term)

			# Get the English terms for the metathesaurus
			mmterms = [ metathesaurus[cuid] for cuid in cuids ]

			# Merge the lists together
			mmterms = sum(mmterms, [])
		else:
			mmterms = []

		# Add in the Disease Ontology term (in case it's not already in there)
		mmterms.append(term.name)

		# Add synonyms in the Disease Ontology term
		mmterms += getSynonyms(term)

		# Lowercase everything
		mmterms = [ mmterm.lower() for mmterm in mmterms ]
		
		# Filter out general terms
		mmterms = [ mmterm for mmterm in mmterms if not mmterm in stopwords ]

		# Add extra spellings and plurals
		mmterms = augmentTermList(mmterms)

		# Remove any duplicates and sort it
		mmterms = sorted(list(set(mmterms)))

		if len(mmterms) > 0:
			allterms[term.id] = mmterms

	print "Generated %d terms" % len(allterms)
	
	print "Outputting to file..."
	with open(args.outFile,'w') as outF:
		json.dump(allterms,outF,indent=2,sort_keys=True)

	print "Successfully output to %s" % args.outFile

		

