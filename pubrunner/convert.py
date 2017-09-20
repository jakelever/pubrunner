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
import unicodedata

def writeMarcXMLRecordToBiocFile(record,biocWriter):
	metadata = record['008'].value()
	language = metadata[35:38]
	if language != 'eng':
		return

	recordid = record['001'].value()

	title = record.title()
	textSources = [title]

	abstract = None
	if '520' in record and 'a' in record['520']:
		abstract = record['520']['a']
		textSources.append(abstract)

	#print recordid, language, title, abstract
	biocDoc = bioc.BioCDocument()
	biocDoc.id = recordid

	offset = 0
	for textSource in textSources:
		if isinstance(textSource,six.string_types):
			passage = bioc.BioCPassage()
			passage.text = textSource
			passage.offset = offset
			offset += len(textSource)
			biocDoc.add_passage(passage)

	biocWriter.writedocument(biocDoc)

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

def cleanupText(text):
	# Remove some "control-like" characters (left/right separator)
	text = text.replace(u'\u2028',' ').replace(u'\u2029',' ')
	text = "".join(ch for ch in text if unicodedata.category(ch)[0]!="C")
	text = "".join(ch if unicodedata.category(ch)[0]!="Z" else " " for ch in text)
	return text.strip()

# Unescape HTML special characters e.g. &gt; is changed to >
htmlParser = HTMLParser()
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

	# Remove no-break spaces
	mergedList = [ cleanupText(text) for text in mergedList ]
	
	return mergedList

def processMedlineFile(pubmedFile):
	for event, elem in etree.iterparse(pubmedFile, events=('start', 'end', 'start-ns', 'end-ns')):
		if (event=='end' and elem.tag=='MedlineCitation'):
			# Find the elements for the PubMed ID, and publication date information
			pmid = elem.findall('./PMID')
			yearFields = elem.findall('./Article/Journal/JournalIssue/PubDate/Year')
			medlineDateFields = elem.findall('./Article/Journal/JournalIssue/PubDate/MedlineDate')

			# Try to extract the pmidID
			pmidText = ''
			if len(pmid) > 0:
				pmidText = " ".join( [a.text.strip() for a in pmid if a.text ] )

			# Try to extract the publication date
			pubYear = 0
			if len(yearFields) > 0:
				pubYear = yearFields[0].text
			if len(medlineDateFields) > 0:
				pubYear = medlineDateFields[0].text[0:4]

			# Extract the title of paper
			title = elem.findall('./Article/ArticleTitle')
			titleText = extractTextFromElemList(title)
			titleText = [ removeWeirdBracketsFromOldTitles(t) for t in titleText ]
			titleText = [ t for t in titleText if len(t) > 0 ]
			titleText = [ htmlUnescape(t) for t in titleText ]
			titleText = [ removeBracketsWithoutWords(t) for t in titleText ]
			
			# Extract the abstract from the paper
			abstract = elem.findall('./Article/Abstract/AbstractText')
			abstractText = extractTextFromElemList(abstract)
			abstractText = [ t for t in abstractText if len(t) > 0 ]
			abstractText = [ htmlUnescape(t) for t in abstractText ]
			abstractText = [ removeBracketsWithoutWords(t) for t in abstractText ]

			document = {}
			document["pmid"] = pmidText
			document["pubYear"] = pubYear
			document["titleText"] = titleText
			document["abstractText"] = abstractText

			yield document
		

			# Important: clear the current element from memory to keep memory usage low
			elem.clear()

def generateCorpusFromPubmed(pubmedFile):
	corpus = kindred.Corpus()
	for doc in processMedlineFile(pubmedFile):
		for t in doc["titleText"]:
			d = kindred.Document(t,entities=[],sourceIDs={'pmid':doc["pmid"]})
			corpus.addDocument(d)
		for t in doc["abstractText"]:
			d = kindred.Document(t,entities=[],sourceIDs={'pmid':doc["pmid"]})
			corpus.addDocument(d)

	parser = kindred.Parser()
	parser.parse(corpus)

	return corpus

def pubmedxml2bioc(pubmedxmlFilename, biocFilename):
	with bioc.iterwrite(biocFilename) as writer:
		for pmDoc in processMedlineFile(pubmedxmlFilename):
			biocDoc = bioc.BioCDocument()
			biocDoc.id = pmDoc["pmid"]
			#print biocDoc.id
	
			offset = 0
			for textSource in pmDoc["titleText"] + pmDoc["abstractText"]:
				passage = bioc.BioCPassage()
				passage.text = textSource
				passage.offset = offset
				offset += len(textSource)
				biocDoc.add_passage(passage)

			writer.writedocument(biocDoc)
	    #for document in collection.documents:
	     #       writer.writedocument(document)

def bioc2txt(biocFilename, txtFilename):
	with bioc.iterparse(biocFilename) as parser, codecs.open(txtFilename,'w','utf-8') as outF:
		for biocDoc in parser:
			for passage in biocDoc.passages:
				outF.write(passage.text)
				outF.write("\n\n")

def marcxml2bioc(marcxmlFilename,biocFilename):
	with open(marcxmlFilename,'rb') as inF, bioc.iterwrite(biocFilename) as writer:
		def marcxml2bioc_helper(record):
			writeMarcXMLRecordToBiocFile(record,writer)

		pymarc.map_xml(marcxml2bioc_helper,inF)
def main():
	acceptedInFormats = ['bioc','pubmedxml','marcxml']
	acceptedOutFormats = ['bioc','txt']

	parser = argparse.ArgumentParser(description='Tool to convert corpus between different formats')
	parser.add_argument('--i',type=str,required=True,help="Document or directory of documents to convert")
	parser.add_argument('--iFormat',type=str,required=True,help="Format of input corpus. Options: %s" % "/".join(acceptedInFormats))
	parser.add_argument('--o',type=str,required=True,help="Where to store resulting converted docs")
	parser.add_argument('--oFormat',type=str,required=True,help="Format for output corpus. Options: %s" % "/".join(acceptedOutFormats))

	args = parser.parse_args()

	inFormat = args.iFormat.lower()
	outFormat = args.oFormat.lower()

	assert inFormat in acceptedInFormats, "%s is not an accepted input format. Options are: %s" % (inFormat, "/".join(acceptedInFormats))
	assert outFormat in acceptedOutFormats, "%s is not an accepted output format. Options are: %s" % (outFormat, "/".join(acceptedOutFormats))

	print("Starting conversion of %s." % args.i)
	with tempfile.NamedTemporaryFile() as temp:
		if inFormat == 'bioc':
			shutil.copyfile(args.i,temp.name)
		elif inFormat == 'pubmedxml':
			pubmedxml2bioc(args.i,temp.name)
		elif inFormat == 'marcxml':
			marcxml2bioc(args.i,temp.name)
		else:
			raise RuntimeError("Unknown input format: %s" % inFormat)

		if outFormat == 'bioc':
			shutil.copyfile(temp.name,args.o)
		elif outFormat == 'txt':
			bioc2txt(temp.name,args.o)
		else:
			raise RuntimeError("Unknown output format: %s" % outFormat)
	print("Output to %s complete." % args.o)

