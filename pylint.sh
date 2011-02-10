#! /bin/sh

files=$@
if [ -z "$files" ]; then
	files="htmltreediff"
fi
pylint --rcfile $(dirname $0)/pylintrc --reports=n $files
