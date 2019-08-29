dockerImageName=oxfordmmm/resistanceapi
dockerpid=`docker ps -a | grep $dockerImageName | grep "Up" | awk -F " " '{ print $1 }'`
if [[ $dockerpid != "" ]];then
   docker kill $dockerpid
fi
docker pull $dockerImageName
docker run  -v ~/DataFromDocker/Resistance/vcfs:/vcfs -v ~/DataFromDocker/Resistance/logs:/logs -d -p 8989:8989 --rm $dockerImageName