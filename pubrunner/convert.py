import argparse
import xml.etree.cElementTree as etree
import codecs
from six.moves.html_parser import HTMLParser
import re
import tempfile
import bioc
import pymarc
import shutil
import six
import unicodedata


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

def getMetaInfoForPMCArticle(articleElem):
	# Attempt to extract the PubMed ID, PubMed Central IDs and DOIs
	pmidText = ''
	pmcidText = ''
	doiText = ''
	article_id = articleElem.findall('./front/article-meta/article-id') + articleElem.findall('./front-stub/article-id')
	for a in article_id:
		if a.text and 'pub-id-type' in a.attrib and a.attrib['pub-id-type'] == 'pmid':
			pmidText = a.text.strip().replace('\n',' ')
		if a.text and 'pub-id-type' in a.attrib and a.attrib['pub-id-type'] == 'pmc':
			pmcidText = a.text.strip().replace('\n',' ')
		if a.text and 'pub-id-type' in a.attrib and a.attrib['pub-id-type'] == 'doi':
			doiText = a.text.strip().replace('\n',' ')
			
	# Attempt to get the publication date
	pubdates = articleElem.findall('./front/article-meta/pub-date') + articleElem.findall('./front-stub/pub-date')
	pubYear = ""
	if len(pubdates) >= 1:
		pubYear = pubdates[0].find("year").text.strip().replace('\n',' ')
			
	return pmidText,pmcidText,doiText,pubYear

def processMedlineFile(pubmedFile):
	yearRegex = re.compile(r'(18|19|20)\d\d')
	for event, elem in etree.iterparse(pubmedFile, events=('start', 'end', 'start-ns', 'end-ns')):
		if (event=='end' and elem.tag=='MedlineCitation'):
			# Find the elements for the PubMed ID, and publication date information
			pmidFields = elem.findall('./PMID')
			yearFields = elem.findall('./Article/Journal/JournalIssue/PubDate/Year')
			medlineDateFields = elem.findall('./Article/Journal/JournalIssue/PubDate/MedlineDate')
			journalTitleFields = elem.findall('./Article/Journal/Title')
			journalTitleISOFields = elem.findall('./Article/Journal/ISOAbbreviation')

			# Try to extract the pmidID
			pmid = ''
			if len(pmidFields) > 0:
				pmid = " ".join( [a.text.strip() for a in pmidFields if a.text ] )

			# Try to extract the publication date
			pubYearText = ''
			if len(yearFields) > 0:
				pubYearText = yearFields[0].text
			if len(medlineDateFields) > 0:
				pubYearText = medlineDateFields[0].text[0:4]

			pubYear = None
			if not pubYearText is None:
				regexSearch = re.search(yearRegex,pubYearText)
				if regexSearch:
					pubYear = regexSearch.group()

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
			
			journalTitle = " ".join(extractTextFromElemList(journalTitleFields))
			journalISOTitle = " ".join(extractTextFromElemList(journalTitleISOFields))

			document = {}
			document["pmid"] = pmid
			document["pubYear"] = pubYear
			document["title"] = titleText
			document["abstract"] = abstractText
			document["journal"] = journalTitle
			document["journalISO"] = journalISOTitle

			yield document
		

			# Important: clear the current element from memory to keep memory usage low
			elem.clear()

def processPMCFile(pmcFile):
	with open(pmcFile, 'r') as openfile:

		# Skip to the article element in the file
		for event, elem in etree.iterparse(openfile, events=('start', 'end', 'start-ns', 'end-ns')):
			if (event=='end' and elem.tag=='article'):
			
				pmidText,pmcidText,doiText,pubYear = getMetaInfoForPMCArticle(elem)

				# We're going to process the main article along with any subarticles
				# And if any of the subarticles have distinguishing IDs (e.g. PMID), then
				# that'll be used, otherwise the parent article IDs will be used
				subarticles = [elem] + elem.findall('./sub-article')
				
				for articleElem in subarticles:
					if articleElem == elem:
						# This is the main parent article. Just use its IDs
						subPmidText,subPmcidText,subDoiText,subPubYear = pmidText,pmcidText,doiText,pubYear
					else:
						# Check if this subarticle has any distinguishing IDs and use them instead
						subPmidText,subPmcidText,subDoiText,subPubYear = getMetaInfoForPMCArticle(articleElem)
						if subPmidText=='' and subPmcidText == '' and subDoiText == '':
							subPmidText,subPmcidText,subDoiText = pmidText,pmcidText,doiText
						if subPubYear == '':
							subPubYear = pubYear
							
					# Extract the title of paper
					title = articleElem.findall('./front/article-meta/title-group/article-title') + articleElem.findall('./front-stub/title-group/article-title')
					assert len(title) <= 1
					titleText = extractTextFromElemList(title)
					titleText = [ removeWeirdBracketsFromOldTitles(t) for t in titleText ]
					
					# Get the subtitle (if it's there)
					subtitle = articleElem.findall('./front/article-meta/title-group/subtitle') + articleElem.findall('./front-stub/title-group/subtitle')
					subtitleText = extractTextFromElemList(subtitle)
					subtitleText = [ removeWeirdBracketsFromOldTitles(t) for t in subtitleText ]
					
					# Extract the abstract from the paper
					abstract = articleElem.findall('./front/article-meta/abstract') + articleElem.findall('./front-stub/abstract')
					abstractText = extractTextFromElemList(abstract)
					
					journal = articleElem.findall('./front/journal-meta/journal-title-group/journal-title') + articleElem.findall('./front-stub/journal-title-group/journal-title')
					assert len(journal) <= 1
					journalText = " ".join(extractTextFromElemList(journal))
					
					journalISOText = ''
					journalISO = articleElem.findall('./front/journal-meta/journal-id') + articleElem.findall('./front-stub/journal-id')
					for field in journalISO:
						if 'journal-id-type' in field.attrib and field.attrib['journal-id-type'] == "iso-abbrev":
							journalISOText = field.text
					
					# Extract the full text from the paper as well as supplementaries and floating blocks of text
					articleText = extractTextFromElemList(articleElem.findall('./body'))
					backText = extractTextFromElemList(articleElem.findall('./back'))
					floatingText = extractTextFromElemList(articleElem.findall('./floats-group'))
					
					document = {'pmid':subPmidText, 'pmcid':subPmcidText, 'doi':subDoiText, 'pubYear':subPubYear, 'journal':journalText, 'journalISO':journalISOText}

					textSources = {}
					textSources['title'] = titleText
					textSources['subtitle'] = subtitleText
					textSources['abstract'] = abstractText
					textSources['article'] = articleText
					textSources['back'] = backText
					textSources['floating'] = floatingText

					for k in textSources.keys():
						tmp = textSources[k]
						tmp = [ t for t in tmp if len(t) > 0 ]
						tmp = [ htmlUnescape(t) for t in tmp ]
						tmp = [ removeBracketsWithoutWords(t) for t in tmp ]
						textSources[k] = tmp

					document['textSources'] = textSources
					yield document
			
				# Less important here (compared to abstracts) as each article file is not too big
				elem.clear()

def trimSentenceLengths(text):
	MAXLENGTH = 90000
	return ".".join( line[:MAXLENGTH] for line in text.split('.') )

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
			textSource = trimSentenceLengths(textSource)
			passage = bioc.BioCPassage()
			passage.text = textSource
			passage.offset = offset
			offset += len(textSource)
			biocDoc.add_passage(passage)

	biocWriter.writedocument(biocDoc)

def pubmedxml2bioc(pubmedxmlFilename, biocFilename):
	with bioc.iterwrite(biocFilename) as writer:
		for pmDoc in processMedlineFile(pubmedxmlFilename):
			biocDoc = bioc.BioCDocument()
			biocDoc.id = pmDoc["pmid"]
			biocDoc.infons['title'] = " ".join(pmDoc["title"])
			biocDoc.infons['pmid'] = pmDoc["pmid"]
			biocDoc.infons['year'] = pmDoc["pubYear"]
			biocDoc.infons['journal'] = pmDoc["journal"]
			biocDoc.infons['journalISO'] = pmDoc["journalISO"]
	
			offset = 0
			for section in ["title","abstract"]:
				for textSource in pmDoc[section]:
					textSource = trimSentenceLengths(textSource)
					passage = bioc.BioCPassage()
					passage.infons['section'] = section
					passage.text = textSource
					passage.offset = offset
					offset += len(textSource)
					biocDoc.add_passage(passage)

			writer.writedocument(biocDoc)

def pmcxml2bioc(pmcxmlFilename, biocFilename):
	with bioc.iterwrite(biocFilename) as writer:
		for pmcDoc in processPMCFile(pmcxmlFilename):
			biocDoc = bioc.BioCDocument()
			biocDoc.id = pmcDoc["pmid"]
			biocDoc.infons['title'] = " ".join(pmcDoc["textSources"]["title"])
			biocDoc.infons['pmid'] = pmcDoc["pmid"]
			biocDoc.infons['pmcid'] = pmcDoc["pmcid"]
			biocDoc.infons['doi'] = pmcDoc["doi"]
			biocDoc.infons['year'] = pmcDoc["pubYear"]
			biocDoc.infons['journal'] = pmcDoc["journal"]
			biocDoc.infons['journalISO'] = pmcDoc["journalISO"]

			offset = 0
			for groupName,textSourceGroup in pmcDoc["textSources"].items():
				for textSource in textSourceGroup:
					textSource = trimSentenceLengths(textSource)
					passage = bioc.BioCPassage()
					passage.infons['section'] = groupName
					passage.text = textSource
					passage.offset = offset
					offset += len(textSource)
					biocDoc.add_passage(passage)

			writer.writedocument(biocDoc)

def mergeBioc(biocFilename, outBiocWriter,idFilter):
	with bioc.iterparse(biocFilename) as parser:
		for biocDoc in parser:
			if idFilter is None or biocDoc.id in idFilter:
				outBiocWriter.writedocument(biocDoc)

def bioc2txt(biocFilename, txtHandle,idFilter):
	with bioc.iterparse(biocFilename) as parser:
		for biocDoc in parser:
			if idFilter is None or biocDoc.id in idFilter:
				for passage in biocDoc.passages:
					txtHandle.write(passage.text)
					txtHandle.write("\n\n")

def marcxml2bioc(marcxmlFilename,biocFilename):
	with open(marcxmlFilename,'rb') as inF, bioc.iterwrite(biocFilename) as writer:
		def marcxml2bioc_helper(record):
			writeMarcXMLRecordToBiocFile(record,writer)

		pymarc.map_xml(marcxml2bioc_helper,inF)

acceptedInFormats = ['bioc','pubmedxml','marcxml','pmcxml']
acceptedOutFormats = ['bioc','txt']
def convertFiles(inFiles,inFormat,outFile,outFormat,idFilterfiles=None):
	outBiocHandle,outTxtHandle = None,None

	if outFormat == 'bioc':
		outBiocHandle = bioc.BioCEncoderIter(outFile)
	elif outFormat == 'txt':
		outTxtHandle = codecs.open(outFile,'w','utf-8')

	if idFilterfiles is None:
		idFilterfiles = [ None for _ in inFiles ]

	for inFile,idFilterfile in zip(inFiles,idFilterfiles):
		if idFilterfile is None:
			idFilter = None
		else:
			with open(idFilterfile) as f:
				idFilter = set([ line.strip() for line in f ])

		print("Starting conversion of %s." % inFile)
		with tempfile.NamedTemporaryFile() as temp:
			if inFormat == 'bioc':
				shutil.copyfile(inFile,temp.name)
			elif inFormat == 'pubmedxml':
				pubmedxml2bioc(inFile,temp.name)
			elif inFormat == 'marcxml':
				marcxml2bioc(inFile,temp.name)
			elif inFormat == 'pmcxml':
				pmcxml2bioc(inFile,temp.name)
			else:
				raise RuntimeError("Unknown input format: %s" % inFormat)

			if outFormat == 'bioc':
				mergeBioc(temp.name,outBiocHandle,idFilter)
			elif outFormat == 'txt':
				bioc2txt(temp.name,outTxtHandle,idFilter)
			else:
				raise RuntimeError("Unknown output format: %s" % outFormat)
	print("Output to %s complete." % outFile)

def main():
	parser = argparse.ArgumentParser(description='Tool to convert corpus between different formats')
	parser.add_argument('--i',type=str,required=True,help="Comma-delimited list of documents to convert")
	parser.add_argument('--iFormat',type=str,required=True,help="Format of input corpus. Options: %s" % "/".join(acceptedInFormats))
	parser.add_argument('--idFilters',type=str,help="Optional set of ID files to filter the documents by")
	parser.add_argument('--o',type=str,required=True,help="Where to store resulting converted docs")
	parser.add_argument('--oFormat',type=str,required=True,help="Format for output corpus. Options: %s" % "/".join(acceptedOutFormats))

	args = parser.parse_args()

	inFormat = args.iFormat.lower()
	outFormat = args.oFormat.lower()

	assert inFormat in acceptedInFormats, "%s is not an accepted input format. Options are: %s" % (inFormat, "/".join(acceptedInFormats))
	assert outFormat in acceptedOutFormats, "%s is not an accepted output format. Options are: %s" % (outFormat, "/".join(acceptedOutFormats))

	inFiles = args.i.split(',')
	if args.idFilters:
		idFilterfiles = args.idFilters.split(',')
		assert len(inFiles) == len(idFilterfiles), "There must be the same number of input files as idFilters files"
	else:
		idFilterfiles = None

	convertFiles(inFiles,inFormat,args.o,outFormat,idFilterfiles)

