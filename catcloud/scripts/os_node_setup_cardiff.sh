set -e

sudo -s

apt update
sleep 5
apt install -y singularity-container nfs-common
sleep 5

echo 'bind path = /work' >> /etc/singularity/singularity.conf
echo 'bind path = /data' >> /etc/singularity/singularity.conf

echo '192.168.9.9:/data /data nfs defaults,noatime,ro 0 0' >> /etc/fstab
echo '192.168.9.9:/work /work nfs defaults,noatime,rw 0 0' >> /etc/fstab

mkdir /data && mkdir /work && chown ubuntu:ubuntu /data /work

mount -a
