#!/bin/bash

set -euxo pipefail

foodonDir=foodon
diseaseontologyFile=doid.obo

git clone https://github.com/FoodOntology/foodon.git $foodonDir

python extractFoodOnTerms.py --owlFiles $foodonDir/imports/langual_import.owl,$foodonDir/imports/ncbitaxon_import.owl,$foodonDir/imports/foodon_product_import.owl,$foodonDir/imports/product_type_import.owl --outFile food.json

wget -O $diseaseontologyFile http://purl.obolibrary.org/obo/doid.obo
python generateDiseaseTerms.py --diseaseOntologyFile $diseaseontologyFile --outFile disease.json

rm -fr $foodonDir $diseaseontologyFile

