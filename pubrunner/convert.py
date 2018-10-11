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
import calendar
import json

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

	# Remove repeated commands and commas next to periods
	text = re.sub(',(\s*,)*',',',text)
	text = re.sub('(,\s*)*\.','.',text)
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
	monthMapping = {}
	for i,m in enumerate(calendar.month_name):
		monthMapping[m] = i
	for i,m in enumerate(calendar.month_abbr):
		monthMapping[m] = i

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
	pubYear,pubMonth,pubDay = None,None,None
	if len(pubdates) >= 1:
		mostComplete,completeness = None,0
		for pubdate in pubdates:
			pubYear_Field = pubdate.find("./year")
			if not pubYear_Field is None:
				pubYear = pubYear_Field.text.strip().replace('\n',' ')
			pubSeason_Field = pubdate.find("./season")
			if not pubSeason_Field is None:
				pubSeason = pubSeason_Field.text.strip().replace('\n',' ')
				monthSearch = [ c for c in (list(calendar.month_name) + list(calendar.month_abbr)) if c != '' and c in pubSeason ]
				if len(monthSearch) > 0:
					pubMonth = monthMapping[monthSearch[0]]
			pubMonth_Field = pubdate.find("./month")
			if not pubMonth_Field is None:
				pubMonth = pubMonth_Field.text.strip().replace('\n',' ')
			pubDay_Field = pubdate.find("./day")
			if not pubDay_Field is None:
				pubDay = pubDay_Field.text.strip().replace('\n',' ')

			thisCompleteness = sum(not x is None for x in [pubYear,pubMonth,pubDay])
			if thisCompleteness > completeness:
				mostComplete = pubYear,pubMonth,pubDay
		pubYear,pubMonth,pubDay = mostComplete
					
	journal = articleElem.findall('./front/journal-meta/journal-title') + articleElem.findall('./front/journal-meta/journal-title-group/journal-title') + articleElem.findall('./front-stub/journal-title-group/journal-title')
	assert len(journal) <= 1
	journalText = " ".join(extractTextFromElemList(journal))
	
	journalISOText = ''
	journalISO = articleElem.findall('./front/journal-meta/journal-id') + articleElem.findall('./front-stub/journal-id')
	for field in journalISO:
		if 'journal-id-type' in field.attrib and field.attrib['journal-id-type'] == "iso-abbrev":
			journalISOText = field.text

	return pmidText,pmcidText,doiText,pubYear,pubMonth,pubDay,journalText,journalISOText

def getJournalDateForMedlineFile(elem,pmid):
	yearRegex = re.compile(r'(18|19|20)\d\d')

	monthMapping = {}
	for i,m in enumerate(calendar.month_name):
		monthMapping[m] = i
	for i,m in enumerate(calendar.month_abbr):
		monthMapping[m] = i

	# Try to extract the publication date
	pubDateField = elem.find('./MedlineCitation/Article/Journal/JournalIssue/PubDate')
	medlineDateField = elem.find('./MedlineCitation/Article/Journal/JournalIssue/PubDate/MedlineDate')

	assert not pubDateField is None, "Couldn't find PubDate field for PMID=%s" % pmid

	medlineDateField = pubDateField.find('./MedlineDate')
	pubDateField_Year = pubDateField.find('./Year')
	pubDateField_Month = pubDateField.find('./Month')
	pubDateField_Day = pubDateField.find('./Day')

	pubYear,pubMonth,pubDay = None,None,None
	if not medlineDateField is None:
		regexSearch = re.search(yearRegex,medlineDateField.text)
		if regexSearch:
			pubYear = regexSearch.group()
		monthSearch = [ c for c in (list(calendar.month_name) + list(calendar.month_abbr)) if c != '' and c in medlineDateField.text ]
		if len(monthSearch) > 0:
			pubMonth = monthSearch[0]
	else:
		if not pubDateField_Year is None:
			pubYear = pubDateField_Year.text
		if not pubDateField_Month is None:
			pubMonth = pubDateField_Month.text
		if not pubDateField_Day is None:
			pubDay = pubDateField_Day.text

	if not pubYear is None:
		pubYear = int(pubYear)
		if not (pubYear > 1700 and pubYear < 2100):
			pubYear = None

	if not pubMonth is None:
		if pubMonth in monthMapping:
			pubMonth = monthMapping[pubMonth]
		pubMonth = int(pubMonth)
	if not pubDay is None:
		pubDay = int(pubDay)

	return pubYear,pubMonth,pubDay

def getPubmedEntryDate(elem,pmid):
	pubDateFields = elem.findall('./PubmedData/History/PubMedPubDate')
	allDates = {}
	for pubDateField in pubDateFields:
		assert 'PubStatus' in pubDateField.attrib
		#if 'PubStatus' in pubDateField.attrib and pubDateField.attrib['PubStatus'] == "pubmed":
		pubDateField_Year = pubDateField.find('./Year')
		pubDateField_Month = pubDateField.find('./Month')
		pubDateField_Day = pubDateField.find('./Day')
		pubYear = int(pubDateField_Year.text)
		pubMonth = int(pubDateField_Month.text)
		pubDay = int(pubDateField_Day.text)

		dateType = pubDateField.attrib['PubStatus']
		if pubYear > 1700 and pubYear < 2100:
			allDates[dateType] = (pubYear,pubMonth,pubDay)

	if len(allDates) == 0:
		return None,None,None

	if 'pubmed' in allDates:
		pubYear,pubMonth,pubDay = allDates['pubmed']
	elif 'entrez' in allDates:
		pubYear,pubMonth,pubDay = allDates['entrez']
	elif 'medline' in allDates:
		pubYear,pubMonth,pubDay = allDates['medline']
	else:
		pubYear,pubMonth,pubDay = list(allDates.values())[0]

	return pubYear,pubMonth,pubDay

def processMedlineFile(pubmedFile):
	for event, elem in etree.iterparse(pubmedFile, events=('start', 'end', 'start-ns', 'end-ns')):
		if (event=='end' and elem.tag=='PubmedArticle'): #MedlineCitation'):
			# Try to extract the pmidID
			pmidField = elem.find('./MedlineCitation/PMID')
			assert not pmidField is None
			pmid = pmidField.text

			journalYear,journalMonth,journalDay = getJournalDateForMedlineFile(elem,pmid)
			entryYear,entryMonth,entryDay = getPubmedEntryDate(elem,pmid)

			jComparison = tuple ( 9999 if d is None else d for d in [ journalYear,journalMonth,journalDay ] )
			eComparison = tuple ( 9999 if d is None else d for d in [ entryYear,entryMonth,entryDay ] )
			if jComparison < eComparison: # The PubMed entry has been delayed for some reason so let's try the journal data
				pubYear,pubMonth,pubDay = journalYear,journalMonth,journalDay
			else:
				pubYear,pubMonth,pubDay = entryYear,entryMonth,entryDay

			# Extract the authors
			authorElems = elem.findall('./MedlineCitation/Article/AuthorList/Author')
			authors = []
			for authorElem in authorElems:
				forename = authorElem.find('./ForeName')
				lastname = authorElem.find('./LastName')
				collectivename = authorElem.find('./CollectiveName')

				name = None
				if forename is not None and lastname is not None and forename.text is not None and lastname.text is not None:
					name = "%s %s" % (forename.text, lastname.text)
				elif lastname is not None and lastname.text is not None:
					name = lastname.text
				elif forename is not None and forename.text is not None:
					name = forename.text
				elif collectivename is not None and collectivename.text is not None:
					name = collectivename.text
				else:
					raise RuntimeError("Unable to find authors in Pubmed citation (PMID=%s)" % pmid)
				authors.append(name)

			chemicals = []
			chemicalElems = elem.findall('./MedlineCitation/ChemicalList/Chemical/NameOfSubstance')
			for chemicalElem in chemicalElems:
				chemID = chemicalElem.attrib['UI']
				name = chemicalElem.text
				#chemicals.append((chemID,name))
				chemicals.append("%s|%s" % (chemID,name))
			chemicalsTxt = "\t".join(chemicals)

			meshHeadings = []
			meshElems = elem.findall('./MedlineCitation/MeshHeadingList/MeshHeading')
			for meshElem in meshElems:
				descriptorElem = meshElem.find('./DescriptorName')
				meshID = descriptorElem.attrib['UI']
				majorTopicYN = descriptorElem.attrib['MajorTopicYN']
				name = descriptorElem.text
				#meshHeading = {'Descriptor':name,'MajorTopicYN':majorTopicYN,'ID':meshID,'Qualifiers':[]}
				meshHeading = "Qualifier|%s|%s|%s" % (meshID,majorTopicYN,name)

				qualifierElems = meshElem.findall('./QualifierName')
				for qualifierElem in qualifierElems:
					meshID = qualifierElem.attrib['UI']
					majorTopicYN = qualifierElem.attrib['MajorTopicYN']
					name = qualifierElem.text
					qualifier = {'Descriptor':name,'MajorTopicYN':majorTopicYN,'ID':meshID}
					#meshHeading['Qualifiers'].append(qualifier)
					meshHeading += "%%Descriptor|%s|%s|%s" % (meshID,majorTopicYN,name)

				meshHeadings.append(meshHeading)
			meshHeadingsTxt = "\t".join(meshHeadings)
					
			# Extract the title of paper
			title = elem.findall('./MedlineCitation/Article/ArticleTitle')
			titleText = extractTextFromElemList(title)
			titleText = [ removeWeirdBracketsFromOldTitles(t) for t in titleText ]
			titleText = [ t for t in titleText if len(t) > 0 ]
			titleText = [ htmlUnescape(t) for t in titleText ]
			titleText = [ removeBracketsWithoutWords(t) for t in titleText ]
			
			# Extract the abstract from the paper
			abstract = elem.findall('./MedlineCitation/Article/Abstract/AbstractText')
			abstractText = extractTextFromElemList(abstract)
			abstractText = [ t for t in abstractText if len(t) > 0 ]
			abstractText = [ htmlUnescape(t) for t in abstractText ]
			abstractText = [ removeBracketsWithoutWords(t) for t in abstractText ]
			
			journalTitleFields = elem.findall('./MedlineCitation/Article/Journal/Title')
			journalTitleISOFields = elem.findall('./MedlineCitation/Article/Journal/ISOAbbreviation')
			journalTitle = " ".join(extractTextFromElemList(journalTitleFields))
			journalISOTitle = " ".join(extractTextFromElemList(journalTitleISOFields))

			document = {}
			document["pmid"] = pmid
			document["pubYear"] = pubYear
			document["pubMonth"] = pubMonth
			document["pubDay"] = pubDay
			document["title"] = titleText
			document["abstract"] = abstractText
			document["journal"] = journalTitle
			document["journalISO"] = journalISOTitle
			document["authors"] = authors
			document["chemicals"] = chemicalsTxt
			document["meshHeadings"] = meshHeadingsTxt

			yield document
		

			# Important: clear the current element from memory to keep memory usage low
			elem.clear()

def processPMCFile(pmcFile):
	with open(pmcFile, 'r') as openfile:

		# Skip to the article element in the file
		for event, elem in etree.iterparse(openfile, events=('start', 'end', 'start-ns', 'end-ns')):
			if (event=='end' and elem.tag=='article'):
			
				pmidText,pmcidText,doiText,pubYear,pubMonth,pubDay,journal,journalISO = getMetaInfoForPMCArticle(elem)

				# We're going to process the main article along with any subarticles
				# And if any of the subarticles have distinguishing IDs (e.g. PMID), then
				# that'll be used, otherwise the parent article IDs will be used
				subarticles = [elem] + elem.findall('./sub-article')
				
				for articleElem in subarticles:
					if articleElem == elem:
						# This is the main parent article. Just use its IDs
						subPmidText,subPmcidText,subDoiText,subPubYear,subPubMonth,subPubDay,subJournal,subJournalISO = pmidText,pmcidText,doiText,pubYear,pubMonth,pubDay,journal,journalISO
					else:
						# Check if this subarticle has any distinguishing IDs and use them instead
						subPmidText,subPmcidText,subDoiText,subPubYear,subPubMonth,subPubDay,subJournal,subJournalISO = getMetaInfoForPMCArticle(articleElem)
						if subPmidText=='' and subPmcidText == '' and subDoiText == '':
							subPmidText,subPmcidText,subDoiText = pmidText,pmcidText,doiText
						if subPubYear == None:
							subPubYear = pubYear
							subPubMonth = pubMonth
							subPubDay = pubDay
						if subJournal == None:
							subJournal = journal
							subJournalISO = journalISO
							
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

					
					# Extract the full text from the paper as well as supplementaries and floating blocks of text
					articleText = extractTextFromElemList(articleElem.findall('./body'))
					backText = extractTextFromElemList(articleElem.findall('./back'))
					floatingText = extractTextFromElemList(articleElem.findall('./floats-group'))
					
					document = {'pmid':subPmidText, 'pmcid':subPmcidText, 'doi':subDoiText, 'pubYear':subPubYear, 'pubMonth':subPubMonth, 'pubDay':subPubDay, 'journal':journal, 'journalISO':journalISO}

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

def uimaxmi2bioc(xmiFilename, biocFilename):
	tree = etree.parse(xmiFilename)
	root = tree.getroot()

	metadataNode = root.find('{http:///de/tudarmstadt/ukp/dkpro/core/api/metadata/type.ecore}DocumentMetaData')
	documentTitle = metadataNode.attrib['documentTitle']

	contentNode = root.find('{http:///uima/cas.ecore}Sofa')
	content = contentNode.attrib['sofaString']

	with bioc.iterwrite(biocFilename) as writer:
		biocDoc = bioc.BioCDocument()
		biocDoc.id = None
		biocDoc.infons['title'] = documentTitle

		passage = bioc.BioCPassage()
		passage.infons['section'] = 'article'
		passage.text = content
		passage.offset = 0
		biocDoc.add_passage(passage)

		writer.writedocument(biocDoc)


def pubmedxml2bioc(pubmedxmlFilename, biocFilename):
	with bioc.iterwrite(biocFilename) as writer:
		for pmDoc in processMedlineFile(pubmedxmlFilename):
			biocDoc = bioc.BioCDocument()
			biocDoc.id = pmDoc["pmid"]
			biocDoc.infons['title'] = " ".join(pmDoc["title"])
			biocDoc.infons['pmid'] = pmDoc["pmid"]
			biocDoc.infons['year'] = pmDoc["pubYear"]
			biocDoc.infons['month'] = pmDoc["pubMonth"]
			biocDoc.infons['day'] = pmDoc["pubDay"]
			biocDoc.infons['journal'] = pmDoc["journal"]
			biocDoc.infons['journalISO'] = pmDoc["journalISO"]
			biocDoc.infons['authors'] = ", ".join(pmDoc["authors"])
			biocDoc.infons['chemicals'] = pmDoc['chemicals']
			biocDoc.infons['meshHeadings'] = pmDoc['meshHeadings']
	
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


allowedSubsections = {"abbreviations","additional information","analysis","author contributions","authors' contributions","authors’ contributions","background","case report","competing interests","conclusion","conclusions","conflict of interest","conflicts of interest","consent","data analysis","data collection","discussion","ethics statement","funding","introduction","limitations","material and methods","materials","materials and methods","measures","method","methods","participants","patients and methods","pre-publication history","related literature","results","results and discussion","statistical analyses","statistical analysis","statistical methods","statistics","study design","summary","supplementary data","supplementary information","supplementary material","supporting information"}
def pmcxml2bioc(pmcxmlFilename, biocFilename):
	try:
		with bioc.iterwrite(biocFilename) as writer:
			for pmcDoc in processPMCFile(pmcxmlFilename):
				biocDoc = bioc.BioCDocument()
				biocDoc.id = pmcDoc["pmid"]
				biocDoc.infons['title'] = " ".join(pmcDoc["textSources"]["title"])
				biocDoc.infons['pmid'] = pmcDoc["pmid"]
				biocDoc.infons['pmcid'] = pmcDoc["pmcid"]
				biocDoc.infons['doi'] = pmcDoc["doi"]
				biocDoc.infons['year'] = pmcDoc["pubYear"]
				biocDoc.infons['month'] = pmcDoc["pubMonth"]
				biocDoc.infons['day'] = pmcDoc["pubDay"]
				biocDoc.infons['journal'] = pmcDoc["journal"]
				biocDoc.infons['journalISO'] = pmcDoc["journalISO"]

				offset = 0
				for groupName,textSourceGroup in pmcDoc["textSources"].items():
					subsection = None
					for textSource in textSourceGroup:
						textSource = trimSentenceLengths(textSource)
						passage = bioc.BioCPassage()

						subsectionCheck = textSource.lower().strip('01234567890. ')
						if subsectionCheck in allowedSubsections:
							subsection = subsectionCheck

						passage.infons['section'] = groupName
						passage.infons['subsection'] = subsection
						passage.text = textSource
						passage.offset = offset
						offset += len(textSource)
						biocDoc.add_passage(passage)

				writer.writedocument(biocDoc)
	except etree.ParseError:
		raise RuntimeError("Parsing error in PMC xml file: %s" % pmcxmlFilename)	

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

def convertFilesFromFilelist(listFile,inFormat,outFile,outFormat,idFilterListfile=None):
	with open(listFile) as f:
		inFiles = json.load(f)

	idFilterfiles = None
	if idFilterListfile:
		with open(idFilterListfile) as f:
			idFilterfiles = json.load(f)

	convertFiles(inFiles,inFormat,outFile,outFormat,idFilterfiles)

acceptedInFormats = ['bioc','pubmedxml','marcxml','pmcxml','uimaxmi']
acceptedOutFormats = ['bioc','txt']
def convertFiles(inFiles,inFormat,outFile,outFormat,idFilterfiles=None):
	outBiocHandle,outTxtHandle = None,None

	if outFormat == 'bioc':
		outBiocHandle = bioc.BioCEncoderIter(outFile)
	elif outFormat == 'txt':
		outTxtHandle = codecs.open(outFile,'w','utf-8')

	if idFilterfiles is None:
		idFilterfiles = [ None for _ in inFiles ]

	print("Converting %d files to %s" % (len(inFiles),outFile))
	for inFile,idFilterfile in zip(inFiles,idFilterfiles):
		if idFilterfile is None:
			idFilter = None
		else:
			with open(idFilterfile) as f:
				idFilter = set([ line.strip() for line in f ])


		with tempfile.NamedTemporaryFile() as temp:
			if inFormat == 'bioc':
				shutil.copyfile(inFile,temp.name)
			elif inFormat == 'pubmedxml':
				pubmedxml2bioc(inFile,temp.name)
			elif inFormat == 'marcxml':
				marcxml2bioc(inFile,temp.name)
			elif inFormat == 'pmcxml':
				pmcxml2bioc(inFile,temp.name)
			elif inFormat == 'uimaxmi':
				uimaxmi2bioc(inFile,temp.name)
			else:
				raise RuntimeError("Unknown input format: %s" % inFormat)

			if outFormat == 'bioc':
				mergeBioc(temp.name,outBiocHandle,idFilter)
			elif outFormat == 'txt':
				bioc2txt(temp.name,outTxtHandle,idFilter)
			else:
				raise RuntimeError("Unknown output format: %s" % outFormat)
	print("Output to %s complete" % outFile)

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

