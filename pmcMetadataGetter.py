import argparse
import xml.etree.cElementTree as etree
import calendar

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
		pubYear_Field = pubdates[0].find("./year")
		if not pubYear_Field is None:
			pubYear = pubYear_Field.text.strip().replace('\n',' ')
		pubSeason_Field = pubdates[0].find("./season")
		if not pubSeason_Field is None:
			pubSeason = pubSeason_Field.text.strip().replace('\n',' ')
			monthSearch = [ c for c in (list(calendar.month_name) + list(calendar.month_abbr)) if c != '' and c in pubSeason ]
			if len(monthSearch) > 0:
				pubMonth = monthMapping[monthSearch[0]]
		pubMonth_Field = pubdates[0].find("./month")
		if not pubMonth_Field is None:
			pubMonth = pubMonth_Field.text.strip().replace('\n',' ')
		pubDay_Field = pubdates[0].find("./day")
		if not pubDay_Field is None:
			pubDay = pubDay_Field.text.strip().replace('\n',' ')

			
	return pmidText,pmcidText,doiText,pubYear,pubMonth,pubDay

def processPMCFile(pmcFile):
	with open(pmcFile, 'r') as openfile:

		# Skip to the article element in the file
		for event, elem in etree.iterparse(openfile, events=('start', 'end', 'start-ns', 'end-ns')):
			if (event=='end' and elem.tag=='article'):
			
				pmidText,pmcidText,doiText,pubYear,pubMonth,pubDay = getMetaInfoForPMCArticle(elem)
				print(pmidText,pmcidText,doiText,pubYear,pubMonth,pubDay)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Get metadata for PMCOA files for use with grouping')
	parser.add_argument('--pmcoaFile',required=True,type=str,help='Path to PMCOA file')
	args = parser.parse_args()

	processPMCFile(args.pmcoaFile)

