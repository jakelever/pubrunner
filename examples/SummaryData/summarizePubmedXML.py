import sys
import pickle
import argparse
import xml.etree.cElementTree as etree
import os
from os import listdir
from os.path import isfile, join
import codecs
from six.moves.html_parser import HTMLParser
import re
from collections import defaultdict
import tempfile
import bioc
import pymarc
import shutil
import six
import re

# Remove empty brackets (that could happen if the contents have been removed already
# e.g. for citation ( [3] [4] ) -> ( ) -> nothing
def removeBracketsWithoutWords(text):
	fixed = re.sub(r'\([\W\s]*\)', ' ', text)
	fixed = re.sub(r'\[[\W\s]*\]', ' ', fixed)
	fixed = re.sub(r'\{[\W\s]*\}', ' ', fixed)
	return fixed

# Some older articles have titles like "[A study of ...]."
# This removes the brackets while retaining the full stop
def removeWeirdBracketsFromOldTitles(titleText):
	titleText = titleText.strip()
	if titleText[0] == '[' and titleText[-2:] == '].':
		titleText = titleText[1:-2] + '.'
	return titleText

# Unescape HTML special characters e.g. &gt; is changed to >
htmlParser = HTMLParser.HTMLParser()
def htmlUnescape(text):
	return htmlParser.unescape(text)

# XML elements to ignore the contents of
ignoreList = ['table', 'table-wrap', 'xref', 'disp-formula', 'inline-formula', 'ref-list', 'bio', 'ack', 'graphic', 'media', 'tex-math', 'mml:math', 'object-id', 'ext-link']

# XML elements to separate text between
separationList = ['title', 'p', 'sec', 'break', 'def-item', 'list-item', 'caption']
def extractTextFromElem(elem):
	textList = []
	
	# Extract any raw text directly in XML element or just after
	head = ""
	if elem.text:
		head = elem.text
	tail = ""
	if elem.tail:
		tail = elem.tail
	
	# Then get the text from all child XML nodes recursively
	childText = []
	for child in elem:
		childText = childText + extractTextFromElem(child)
		
	# Check if the tag should be ignore (so don't use main contents)
	if elem.tag in ignoreList:
		return [tail.strip()]
	# Add a zero delimiter if it should be separated
	elif elem.tag in separationList:
		return [0] + [head] + childText + [tail]
	# Or just use the whole text
	else:
		return [head] + childText + [tail]
	

# Merge a list of extracted text blocks and deal with the zero delimiter
def extractTextFromElemList_merge(list):
	textList = []
	current = ""
	# Basically merge a list of text, except separate into a new list
	# whenever a zero appears
	for t in list:
		if t == 0: # Zero delimiter so split
			if len(current) > 0:
				textList.append(current)
				current = ""
		else: # Just keep adding
			current = current + " " + t
			current = current.strip()
	if len(current) > 0:
		textList.append(current)
	return textList
	
# Main function that extracts text from XML element or list of XML elements
def extractTextFromElemList(elemList):
	textList = []
	# Extracts text and adds delimiters (so text is accidentally merged later)
	if isinstance(elemList, list):
		for e in elemList:
			textList = textList + extractTextFromElem(e) + [0]
	else:
		textList = extractTextFromElem(elemList) + [0]

	# Merge text blocks with awareness of zero delimiters
	mergedList = extractTextFromElemList_merge(textList)
	
	# Remove any newlines (as they can be trusted to be syntactically important)
	mergedList = [ text.replace('\n', ' ') for text in mergedList ]
	
	return mergedList

def processMedlineFile(pubmedFile,fTitles,fHasTitlesAndAbstracts,fPubYear,fJournals):
	for event, elem in etree.iterparse(pubmedFile, events=('start', 'end', 'start-ns', 'end-ns')):
		if (event=='end' and elem.tag=='MedlineCitation'):
			# Find the elements for the PubMed ID, and publication date information
			pmid = elem.findall('./PMID')
			journalTitleElements = elem.findall('./Article/Journal/Title')
			journalTitleISOElements = elem.findall('./Article/Journal/ISOAbbreviation')
			yearFields = elem.findall('./Article/Journal/JournalIssue/PubDate/Year')
			medlineDateFields = elem.findall('./Article/Journal/JournalIssue/PubDate/MedlineDate')

			# Try to extract the pmidID
			pmidText = ''
			if len(pmid) > 0:
				pmidText = " ".join( [a.text.strip() for a in pmid if a.text ] )

			# Try to extract the publication date
			pubYear = "Unknown"
			if len(yearFields) > 0:
				pubYear = yearFields[0].text
			if len(medlineDateFields) > 0:
				pubYear = medlineDateFields[0].text[0:4]

			# Extract the title of paper
			titleElements = elem.findall('./Article/ArticleTitle')
			
			# Extract the abstract from the paper
			abstractElements = elem.findall('./Article/Abstract/AbstractText')

			title = " ".join(extractTextFromElemList(titleElements))
			journalTitle = " ".join(extractTextFromElemList(journalTitleElements))
			journalISOTitle = " ".join(extractTextFromElemList(journalTitleISOElements))

			hasTitle = len(titleElements) > 0
			hasAbstract = len(abstractElements) > 0

			#print hasTitle, hasAbstract, pubYear, journalTitle, journalISOTitle, title

			title01 = 1 if hasTitle else 0
			abstract01 = 1 if hasAbstract else 0

			fTitles.write(title + "\n")
			fHasTitlesAndAbstracts.write("%d\t%d\n" % (title01,abstract01))
			fPubYear.write(pubYear + "\n")
			fJournals.write("%s\t%s\n" % (journalTitle,journalISOTitle))

			#sys.exit(0)

def main():
	parser = argparse.ArgumentParser(description='Tool to summarize PubMed XML corpus')
	parser.add_argument('--i',type=str,required=True,help="Pubmed XML file")
	parser.add_argument('--oTitles',type=str,required=True,help="File containing article titles")
	parser.add_argument('--oHasTitlesAndAbstracts',type=str,required=True,help="File containing counts of titles and abstracts")
	parser.add_argument('--oPubYear',type=str,required=True,help="File containing counts of publication years")
	parser.add_argument('--oJournals',type=str,required=True,help="File containing counts of journals")

	args = parser.parse_args()

	fTitles = codecs.open(args.oTitles,'w','utf-8')
	fHasTitlesAndAbstracts = codecs.open(args.oHasTitlesAndAbstracts,'w','utf-8')
	fPubYear = codecs.open(args.oPubYear,'w','utf-8')
	fJournals = codecs.open(args.oJournals,'w','utf-8')

	processMedlineFile(args.i,fTitles,fHasTitlesAndAbstracts,fPubYear,fJournals)

if __name__ == '__main__':
	main()
