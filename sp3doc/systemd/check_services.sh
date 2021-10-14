#!/bin/bash
services=(catdap catdownload catfetch catgrid catstat cattag catpile catweb catcloud-oracle run_watcher@oxforduni-ncov2019-artic-nf-illumina.service run_watcher@oxforduni-ncov2019-artic-nf-nanopore.service) 

for serv in ${services[@]}
do
    echo "$serv - $(systemctl --user show -p ActiveState $serv | cut -f 2 -d =)" 
done

if [ -f "/home/ubuntu/catsgo/buckets.txt" ]
then
    cat /home/ubuntu/catsgo/buckets.txt | while read line
    do
        serv=dir_watcher@${line//,}.service
        echo "$serv - $(systemctl --user show -p ActiveState $serv | cut -f 2 -d =)" 
    done
fi