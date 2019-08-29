set -e

sudo -s

apt update
sleep 5
apt install -y singularity-container
sleep 5

echo 'bind path = /work' >> /etc/singularity/singularity.conf
echo 'bind path = /data' >> /etc/singularity/singularity.conf

mkdir /data && mkdir /work && chown ubuntu:ubuntu /data /work

mount -t cifs //teststorageaccount777.file.core.windows.net/files /data -o vers=3.0,username=teststorageaccount777,password=Nh/H72VGKPCsPbV6hvSYAq0P+Ocy/H9SG22kIgoIMTX18e858PaEzkC57e6b0TsH++U/skPkBtgjKRUAwo9iug==,dir_mode=0777,file_mode=0777,serverino,ro,mfsymlinks
mount -t cifs //teststorageaccount777.file.core.windows.net/files2 /work -o vers=3.0,username=teststorageaccount777,password=Nh/H72VGKPCsPbV6hvSYAq0P+Ocy/H9SG22kIgoIMTX18e858PaEzkC57e6b0TsH++U/skPkBtgjKRUAwo9iug==,dir_mode=0777,file_mode=0777,serverino,mfsymlinks
