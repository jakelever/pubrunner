
.PHONY: default
default:all

FOODON = /projects/bioracle/jake/pubrunnerTmp/.pubrunner/resources/FOODON
DISEASE_ONTOLOGY = /projects/bioracle/jake/pubrunnerTmp/.pubrunner/resources/DISEASE_ONTOLOGY

pubmed_files  := $(wildcard /projects/bioracle/jake/pubrunnerTmp/.pubrunner/resources/PUBMED_TWOFILES/*.xml)
convertedBioc = $(pubmed_files:/projects/bioracle/jake/pubrunnerTmp/.pubrunner/resources/PUBMED_TWOFILES/%.xml=bioc/%.bioc)

food.json:
	python extractFoodOnTerms.py --owlFiles $(FOODON)/imports/langual_import.owl,$(FOODON)/imports/ncbitaxon_import.owl,$(FOODON)/imports/foodon_product_import.owl,$(FOODON)/imports/product_type_import.owl --outFile food.json

disease.json:
	python generateDiseaseTerms.py --diseaseOntologyFile $(DISEASE_ONTOLOGY)/doid.obo --outFile disease.json

bioc/%.bioc: /projects/bioracle/jake/pubrunnerTmp/.pubrunner/resources/PUBMED_TWOFILES/%.xml
	pubrunner_convert --i $< --iFormat pubmedxml --o $@ --oFormat bioc

cooccurrences = $(convertedBioc:bioc/%.bioc=tmpDir/%.cooccurrences)
tmpDir/%.cooccurrences: bioc/%.bioc food.json disease.json
	python cooccurrenceExtractor.py --biocFile $< --wordlist1 food.json --wordlist2 disease.json --outFile $@



merged: tmpDir $(pubmed_files) $(convertedBioc) $(cooccurrences)
	python combineCooccurrences.py --inDir $< --outFile $@

.PHONY: all
all: merged

