#!/bin/bash
set -ex

command=./pubrunner/openminted.py
hostinput=$PWD/input
hostoutput=$PWD/output
containerinput=/input
containeroutput=/output

inputFormat=uimaxmi
outputFormat=bioc

mkdir -p $hostinput
mkdir -p $hostoutput

cd $hostinput
wget https://openminted.github.io/releases/xmiExamples/XMIsamplesNew.zip
unzip XMIsamplesNew.zip
rm typesystem.xml
rm XMIsamplesNew.zip
cd -

docker run -v $hostinput:$containerinput -v $hostoutput:$containeroutput jakelever/pubrunner $command --input $containerinput --output $containeroutput --param:inputFormat $inputFormat --param:outputFormat $outputFormat
