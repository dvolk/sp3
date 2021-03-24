set -e

sudo -s

for i in {8..63}; do
    if [ -e /dev/loop$i ]; then continue; fi;
    mknod /dev/loop$i b 7 $i;
    chown --reference=/dev/loop0 /dev/loop$i;
    chmod --reference=/dev/loop0 /dev/loop$i;
done

apt update
sleep 5
DEBIAN_FRONTEND=noninteractive apt install -o Dpkg::Options::='--force-confold' --force-yes -fuy singularity-container nfs-common
sleep 5

echo 'bind path = /work' >> /etc/singularity/singularity.conf
echo 'bind path = /data' >> /etc/singularity/singularity.conf

echo '192.168.0.20:/data /data nfs defaults,noatime,nodiratime,ro 0 0' >> /etc/fstab
echo '192.168.0.20:/work /work nfs defaults,noatime,nodiratime,rw 0 0' >> /etc/fstab

mkdir /data && mkdir /work && chown ubuntu:ubuntu /data /work

mount -a
