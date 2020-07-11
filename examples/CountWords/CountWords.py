import argparse
import xml.etree.cElementTree as etree
import os
from os import listdir
from os.path import isfile, join

def processPubmedFile(pubmedFile,outFile):
	"""Calculates word counts on a PubMed XML file and outputs the results

	Args:
		pubmedFile (file): PubMed XML file
		outFile (file): Output file
	Returns:
		Nothing

	"""
	abstractCount = 0

	with open(outFile, "a") as result:
		# Iterate over all files
		for event, elem in etree.iterparse(pubmedFile, events=('start', 'end', 'start-ns', 'end-ns')):
			if (event=='end' and elem.tag=='MedlineCitation'):

				# Let's get the PMID and Abstract elements from the XML
				pmidElements = elem.findall('./PMID')
				abstractElements = elem.findall('./Article/Abstract/AbstractText')

				if len(pmidElements) != 1 or len(abstractElements) != 1:
					continue

				# Pull the values of the PMID and abstract elements
				pmid = pmidElements[0].text
				abstract = abstractElements[0].text

				if not abstract is None:
					# Do a very basic word count
					wordCount = len(abstract.split())

					# Prepare and save output to file
					line = "%s\t%d\n" % (pmid,wordCount)

					result.write(line)

					abstractCount += 1

	print("%d abstracts processed" % abstractCount)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Little toy example to "process" a Medline abstract file and gives naive word counts for each abstract')
	parser.add_argument('-i',required=True,help='Medline file to process')
	parser.add_argument('-o',required=True,help='Output file for word-counts')

	args = parser.parse_args()

	processPubmedFile(args.i,args.o)
