#!/bin/bash
set -eux

dir=$1
out=$2

find $dir -type f |\
xargs cat |\
cut -f 3 -d $'\t' |\
tr '[:upper:]' '[:lower:]' |\
awk ' { dict[$0]=dict[$0]+1; } END { for (id in dict) print dict[id]"\t"id; } ' |\
sort -k1,1n > $out

