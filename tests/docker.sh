#!/bin/bash
set -ex

command=./pubrunner/openminted/convert.py
hostinput=$PWD/input
hostoutput=$PWD/output
containerinput=/input
containeroutput=/output

inputformat=uimaxmi
outputformat=bioc

mkdir -p $hostinput
mkdir -p $hostoutput

cd $hostinput
wget https://openminted.github.io/releases/xmiExamples/XMIsamplesNew.zip
unzip XMIsamplesNew.zip
rm typesystem.xml
rm XMIsamplesNew.zip
cd -

echo "Running conversion component"
docker run -v $hostinput:$containerinput -v $hostoutput:$containeroutput jakelever/pubrunner $command --input $containerinput --output $containeroutput --param:inputformat $inputformat --param:outputformat $outputformat


command=./pubrunner/openminted/run.py
githubrepo=https://github.com/jakelever/Ab3P/

echo "Running run component"
docker run -v $hostinput:$containerinput -v $hostoutput:$containeroutput jakelever/pubrunner $command --input $containerinput --output $containeroutput --param:githubrepo $githubrepo

command=./pubrunner/openminted/download.py
resource=PMCOA_TWOJOURNALS

echo "Running download component"
docker run -v $hostinput:$containerinput -v $hostoutput:$containeroutput jakelever/pubrunner $command --output $containeroutput --param:resource $resource

