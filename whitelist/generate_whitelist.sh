#!/bin/bash

: > executables_files.txt
echo "Seaching all executables"
# Find all executables
find / -type f -executable -print >> executables_files.txt
#libraries
find /usr/lib/  -type f -name "*.so*" >> executables_files.txt 
find /lib/udev/ -type f -name "*.rules*" >> executables_files.txt #files that store udev rules that define how devices are identified by the kernel. >> executables_files.txt #files used by kernel
#individual files measured by IMA:
echo "/etc/ld.so.cache" >> executables_files.txt


echo "Getting they dependences"
: > dependencesFiles.txt
# Get file dependences
while read -r line; do
   ldd $line 1>> dependencesFiles.txt 2>/dev/null #lists the libraries used by the executables

done < executables_files.txt


echo "Filtering dependences"
cat dependencesFiles.txt | cut -d">" -f2 | awk '{$1=$1;print}' | cut -d "(" -f1 | sort | uniq -u > dependencesFilesUniq.txt


echo "Measuring the files"
: > imageBase.txt
# Measure all files collected
while read -r line;do
	sha256=`sha256sum $line | cut -d ' ' -f1`
	sha1=`sha1sum $line | cut -d ' ' -f1` 
	md5=`md5sum $line | cut -d ' ' -f1` 
	echo "md5:$md5 sha256:$sha256 sha1:$sha1 $line" >> imageBase.txt
done < executables_files.txt  

while read -r line;do
	sha256=`sha256sum $line | cut -d ' ' -f1`
	sha1=`sha1sum $line | cut -d ' ' -f1` 
	md5=`md5sum $line | cut -d ' ' -f1` 
	echo "md5:$md5 sha256:$sha256 sha1:$sha1 $line" >> imageBase.txt
done < dependencesFilesUniq.txt  



rm -rf executables_files.txt dependencesFiles.txt dependencesFilesUniq.txt


