if [ "$1" = "" ]
then
	echo "Please specify a version for this docker e.g. 3.1.2"
	exit 0;
fi
rm -fr requirements.txt
rm -fr src
rm -fr config
rm -fr data
cp -r ../requirements.txt .
cp -r ../config config
cp -r ../src src
cp -r ../data data
docker_acc="oxfordmmm"
docker_name="resistanceapi"
docker image build -t "${docker_acc}/${docker_name}" .
docker tag "${docker_acc}/${docker_name}:latest" "${docker_acc}/${docker_name}:v$1"
docker push "${docker_acc}/${docker_name}"