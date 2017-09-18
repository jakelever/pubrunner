import sys
import pickle
import argparse
import xml.etree.cElementTree as etree
import os
from os import listdir
from os.path import isfile, join
import codecs
import HTMLParser
import re
from collections import defaultdict
import tempfile
import bioc
import pymarc
import shutil
import six
import re

def getField(record,main,sub=None):
	try:
		if sub is None:
			value = record[main]
		else:
			value = record[main][sub]
	except:
		value = None
	return value

def summarizeMarcXMLFile(record,fTitles,fTitlesAndAbstracts,fPubYear,fJournals):
	metadata = record['008'].value()
	language = metadata[35:38]
	if language != 'eng':
		return

	recordid = record['001'].value()

	title = record.title()
	textSources = [title]

	abstract = getField(record,'520','a')
	journal = getField(record,'773','t')
	journalShort = getField(record,'773','p')
	pubdate = getField(record,'773','g')

	pubyear = "Unknown"
	if not pubdate is None:
		pubyearSearch = re.findall('[12][0-9]{3}', pubdate)
		if len(pubyearSearch) == 1:
			pubyear = pubyearSearch[0]

	if journal is None:
		journal = "Unknown"
	if journalShort is None:
		journalShort = "Unknown"

	title01 = 0 if title is None else 1
	abstract01 = 0 if abstract is None else 1

	fTitles.write(title + "\n")
	fTitlesAndAbstracts.write("%d\t%d\n" % (title01,abstract01))
	fPubYear.write(pubyear+"\n")
	fJournals.write("%s\t%s\n" % (journal,journalShort))

	#print journal, pubyear
	#print journal

	#print record.as_dict()
	#sys.exit(0)



def main():
	parser = argparse.ArgumentParser(description='Tool to summarize data from PubAg')
	parser.add_argument('--i',type=str,required=True,help="PubAg MarcXML file")
	parser.add_argument('--oTitles',type=str,required=True,help="File containing titles")
	parser.add_argument('--oHasTitlesAndAbstracts',type=str,required=True,help="File containing counts of titles and abstracts")
	parser.add_argument('--oPubYear',type=str,required=True,help="File containing counts of publication years")
	parser.add_argument('--oJournals',type=str,required=True,help="File containing counts of journals")

	args = parser.parse_args()

	fTitles = codecs.open(args.oTitles,'w','utf-8')
	fHasTitlesAndAbstracts = codecs.open(args.oHasTitlesAndAbstracts,'w','utf-8')
	fPubYear = codecs.open(args.oPubYear,'w','utf-8')
	fJournals = codecs.open(args.oJournals,'w','utf-8')
	
	def summarizeMarcXMLFile_helper(record):
		summarizeMarcXMLFile(record,fTitles,fHasTitlesAndAbstracts,fPubYear,fJournals)

	with open(args.i,'rb') as inF:
		pymarc.map_xml(summarizeMarcXMLFile_helper,inF)

if __name__ == '__main__':
	main()
