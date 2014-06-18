#!/bin/sh
echo "recursively removing *.pyc"
find . -type f -name *.pyc -delete
echo "recursively removing .DS_Store"
find . -type f -name .DS_Store -delete
echo "recursively removing aptana temp files .tmp_*"
find . -type f -name .tmp_* -delete