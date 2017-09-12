#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
****************************************************
 example.py
 Author: Damion Dooley

 This is an example script that shows how to load an ontology and its include files using rdflib,
 and how to query it by sparql queries below.

 Example command line when run in a folder under main ontology file.

 python example.py ../genepio.owl

 RDFLib sparql ISSUE: Doing a binding x on a (?x as ?y) expression bug leads to no such field being output.

**************************************************** 
""" 

import re
import json
from pprint import pprint
import optparse
import sys
import os
import argparse

import rdflib
#import rdflib.plugins.sparql as sparql
import rdfextras; rdfextras.registerplugins() # so we can Graph.query()

# Do this, otherwise a warning appears on stdout: No handlers could be found for logger "rdflib.term"
import logging; logging.basicConfig(level=logging.ERROR) 
from collections import defaultdict

try: #Python 2.7
	from collections import OrderedDict
except ImportError: # Python 2.6
	from ordereddict import OrderedDict


CODE_VERSION = '0.0.0'

def stop_err( msg, exit_code=1 ):
	sys.stderr.write("%s\n" % msg)
	sys.exit(exit_code)

class MyParser(optparse.OptionParser):
	"""
	Allows formatted help info.  From http://stackoverflow.com/questions/1857346/python-optparse-how-to-include-additional-info-in-usage-output.
	"""
	def format_epilog(self, formatter):
		return self.epilog

class Ontology(object):
	"""
	Read in an ontology and its include files. Run Sparql 1.1 queries which retrieve:
	- ontology defined fields, including preferred label and definition 

	"""

	def __init__(self,main_ontology_file):

		self.graph=rdflib.Graph()

		self.struct = OrderedDict()
		# JSON-LD @context markup, and as well its used for a prefix encoding table.
		# Many of these are genepio.owl specific and can be dropped for use with other ontologies.
		self.struct['@context'] = {		#JSON-LD markup
			'ifm':'http://purl.obolibrary.org/obo/GENEPIO/IFM#',  # Must be ordered 1st or obo usurps.
			'obo':'http://purl.obolibrary.org/obo/',
			'owl':'http://www.w3.org/2002/07/owl/',
			'evs':'http://ncicb.nci.nih.gov/xml/owl/EVS/',
			'sio':'http://semanticscience.org/resource/',
			'ndf-rt':'http://evs.nci.nih.gov/ftp1/NDF-RT/NDF-RT.owl#',
			'xmls':'http://www.w3.org/2001/XMLSchema#',
			'vcard':'http://www.w3.org/2006/vcard/ns#',
			'mesh':'http://purl.bioontology.org/ontology/MESH/',
			'typon':'http://purl.phyloviz.net/ontology/typon#',
			'vcf':'http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#',
			'eo':'http://epidemiology_ontology.owl#',
			'bibo':'http://purl.org/ontology/bibo/',
			'efo':'http://www.ebi.ac.uk/efo/',
			'oboInOwl': 'http://www.geneontology.org/formats/oboInOwl#'
		}
		self.struct['specifications'] = {}

		main_ontology_file = self.check_folder(main_ontology_file, "Ontology file")
		if not os.path.isfile(main_ontology_file):
			stop_err('Please check the OWL ontology file path')			

		print "PROCESSING " + main_ontology_file + " ..."
		# Load main ontology file into RDF graph
		self.graph.parse(main_ontology_file)
		# Add each ontology include file (must be in XML/RDF format)
		self.ontologyIncludes()

		# Get stuff under OBI data_representational_model
		root_term = rdflib.URIRef(self.expandId('obo:OBI_0000658'))
		specBinding={'root': root_term} 
		self.struct['specifications'] = self.doQueryTable('tree', specBinding)
	
	############################## UTILITIES ###########################

	def extractId(self, URI):
		# If a URI has a recognized value from @context, create shortened version
		if '/' in URI or r'#' in URI: 
			(prefix, myid) = URI.rsplit('#',1) if '#' in URI else URI.rsplit(r'/',1) # Need '#' first!
			for key, value in self.struct['@context'].iteritems():
				if value[0:-1] == prefix: return key+":"+myid
			
		return URI 


	def expandId(self, URI):
		# If a URI has a recognized prefix, create full version
		if ':' in URI: 
			(prefix, myid) = URI.rsplit(':',1)
			for key, value in self.struct['@context'].iteritems():
				if key == prefix: return value+myid
			
		return URI 


	def ontologyIncludes(self):
		"""
		Detects all the import files in a loaded OWL ontology graph and adds them to the graph.
		Currently assumes imports are sitting in a folder called "imports" in parent folder of this script. 
		"""
		imports = self.graph.query("""
			SELECT distinct ?import_file
			WHERE {?s owl:imports ?import_file.}
			ORDER BY (?import_file)
		""")		

		print("It has %s import files ..." % len(imports))

		for result_row in imports: # a rdflib.query.ResultRow
			file = result_row.import_file.rsplit('/',1)[1]
			try:
				if os.path.isfile( "../imports/" + file):
					self.graph.parse("../imports/" + file)	
				else:
					print ('WARNING:' + "../imports/" + file + " could not be loaded!  Does its ontology include purl have a corresponding local file? \n")

			except rdflib.exceptions.ParserError as e:
				print (file + " needs to be in RDF OWL format!")			


	def doQueryTable(self, query_name, initBinds = {}):
		"""
		Given a sparql 1.1 query, returns a list of objects, one for each row result
		Simplifies XML/RDF URI http://... reference down to a known ontology entity code defined in 
		"""

		query = self.queries[query_name]

		try:
			result = self.graph.query(query, initBindings=initBinds) #, initBindings=initBindings
		except Exception as e:
			print ("\nSparql query [%s] parsing problem: %s \n" % (query_name, str(e) ))
			return None

		# Can't get columns by row.asdict().keys() because columns with null results won't be included in a row.
		# Handles "... SELECT DISTINCT (?something as ?somethingelse) ?this ?and ?that WHERE ....""
		#columns = re.search(r"(?mi)\s*SELECT(\s+DISTINCT)?\s+((\?\w+\s+|\(\??\w+\s+as\s+\?\w+\)\s*)+)\s*WHERE", query)
		#columns = re.findall(r"\s+\?(?P<name>\w+)\)?", columns.group(2))

		STRING_DATATYPE = rdflib.term.URIRef('http://www.w3.org/2001/XMLSchema#string')
		table = []
		for ptr, row in enumerate(result):
			rowdict = row.asdict()
			newrowdict = {}

			for column in rowdict:

				# Each value has a datatype defined by RDF Parser: URIRef, Literal, BNode
				value = rowdict[column]
				valType = type(value) 
				if valType is rdflib.term.URIRef : 
					newrowdict[column] = self.extractId(value)  # a plain string

				elif valType is rdflib.term.Literal :
					literal = {'value': value.replace('\n',r'\n')} # Text may include carriage returns; escape to json
					#_invalid_uri_chars = '<>" {}|\\^`'

					if hasattr(value, 'datatype'): #rdf:datatype
						#Convert literal back to straight string if its datatype is simply xmls:string
						if value.datatype == None or value.datatype == STRING_DATATYPE:
							literal = literal['value']
						else:
							literal['datatype'] = self.extractId(value.datatype)															

					elif hasattr(value, 'language'): # e.g.  xml:lang="en"
						#A query Literal won't have a language if its the result of str(?whatever) !
						literal['language'] = self.extractId(value.language)
					
					else: # WHAT OTHER OPTIONS?
						literal = literal['value']

					newrowdict[column] = literal

				elif valType is rdflib.term.BNode:
					"""
					Convert a variety of BNode structures into something simple.
					E.g. "(province or state or territory)" is a BNode structure coded like
					 	<owl:someValuesFrom> 
							<owl:Class>
								<owl:unionOf rdf:parseType="Collection">
                    			   <rdf:Description rdf:about="&resource;SIO_000661"/> 
                    			   <rdf:Description rdf:about="&resource;SIO_000662"/>
                    			   ...
                    """
                    # Here we fetch list of items in disjunction
					disjunction = self.graph.query(
						"SELECT ?id WHERE {?datum owl:unionOf/rdf:rest*/rdf:first ?id}", 
						initBindings={'datum': value} )		
					results = [self.extractId(item[0]) for item in disjunction] 
					newrowdict['expression'] = {'datatype':'disjunction','data':results}

					newrowdict[column] = value

				else:

					newrowdict[column] = {'value': 'unrecognized column [%s] type %s for value %s' % (column, type(value), value)}

			table.append(newrowdict)

		return table



	def get_command_line(self):
		"""
		*************************** Parse Command Line *****************************
		"""
		parser = MyParser(
			description = 'GenEpiO JSON field specification generator.  See https://github.com/GenEpiO/genepio',
			usage = 'jsonimo.py [ontology file path] [options]*',
			epilog="""  """)
		
		# Standard code version identifier.
		parser.add_option('-v', '--version', dest='code_version', default=False, action='store_true', help='Return version of this code.')

		return parser.parse_args()


	def check_folder(self, file_path, message = "Directory for "):
		"""
		Ensures file folder path for a file exists.
		It can be a relative path.
		"""
		if file_path != None:

			path = os.path.normpath(file_path)
			if not os.path.isdir(os.path.dirname(path)): 
				# Not an absolute path, so try default folder where script launched from:
				path = os.path.normpath(os.path.join(os.getcwd(), path) )
				if not os.path.isdir(os.path.dirname(path)):
					stop_err(message + "[" + path + "] does not exist!")			
					
			return path
		return None


	""" 
	Add these PREFIXES to Protege Sparql query window if you want to test a query there:

	PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> PREFIX owl: <http://www.w3.org/2002/07/owl#>
	PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> PREFIX obo: <http://purl.obolibrary.org/obo/>
	PREFIX xmls: <http://www.w3.org/2001/XMLSchema#>
	""" 
	namespace = { 
		'owl': rdflib.URIRef('http://www.w3.org/2002/07/owl#'),
		'rdfs': rdflib.URIRef('http://www.w3.org/2000/01/rdf-schema#'),
		'obo': rdflib.URIRef('http://purl.obolibrary.org/obo/'),
		'rdf': rdflib.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
		'xmls': rdflib.URIRef('http://www.w3.org/2001/XMLSchema#'),
		'oboInOwl': rdflib.URIRef('http://www.geneontology.org/formats/oboInOwl#')
	}

	queries = {
		##################################################################
		# Generic TREE "is a" hierarchy from given root.
		# FUTURE: ADD SORTING OPTIONS, CUSTOM ORDER.
		#
		'tree': rdflib.plugins.sparql.prepareQuery("""
			SELECT DISTINCT ?id ?parent ?label ?uiLabel ?definition ?synonym ?exactSynonym ?comment
			WHERE {	
				?parent rdfs:subClassOf* ?root.
				?id rdfs:subClassOf ?parent.
				OPTIONAL {?id rdfs:label ?label}.
				OPTIONAL {?id obo:GENEPIO_0000006 ?uiLabel}.
				OPTIONAL {?id obo:IAO_0000115 ?definition.}
				OPTIONAL {?id oboInOwl:hasSynonym ?synonym}.
				OPTIONAL {?id oboInOwl:hasExactSynonym ?exactSynonym}.
				OPTIONAL {?id rdfs:comment ?comment}.
			}
			ORDER BY ?parent ?label ?uiLabel
		""", initNs = namespace),

		# ################################################################
		# ... add other queries here in same formula as above, 
		# including a unique name like 'tree'

}

if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Tool for extracting term list from FoodOn')
	parser.add_argument('--owlFiles',type=str,required=True,help='Comma-delimited list of OWL files to load')
	parser.add_argument('--outFile',type=str,required=True,help='File to dump out JSON term list')
	args = parser.parse_args()
	
	termList = defaultdict(set)
	for owlFile in args.owlFiles.split(','):
		genepio = Ontology(owlFile)
		table = genepio.doQueryTable('tree')
		for t in table:
			if "comment" in t and "This term is for CLASSIFICATION ONLY" in t["comment"]:
				continue

			tid = t["id"]
			for textField in ["label","synonym","exactSynonym"]:
				if textField in t:
					termList[tid].add(t[textField])
		#with open('table.json','w') as outF:
		#	json.dump(table,outF,indent=2,sort_keys=True)

	termList = { k:sorted(list(termList[k])) for k in termList.keys() }

	with open(args.outFile,'w') as f:
		json.dump(termList,f,indent=2,sort_keys=True)

