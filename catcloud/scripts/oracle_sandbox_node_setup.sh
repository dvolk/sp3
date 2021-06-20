set -e

sudo -s

for i in {8..63}; do
    if [ -e /dev/loop$i ]; then continue; fi;
    mknod /dev/loop$i b 7 $i;
    chown --reference=/dev/loop0 /dev/loop$i;
    chmod --reference=/dev/loop0 /dev/loop$i;
done

apt -qq update
DEBIAN_FRONTEND=noninteractive apt -qq install -o Dpkg::Options::='--force-confold' --force-yes -fuy \
	       nfs-common \
	       squashfs-tools

# install singularity (debian unstable packages)
wget -q 'https://objectstorage.uk-london-1.oraclecloud.com/n/lrbvkel2wjot/b/sp3_deps/o/containernetworking-plugins_0.9.0-1%2Bb5_amd64.deb'
dpkg -i containernetworking-plugins_0.9.0-1+b5_amd64.deb 1>&2 2>/dev/null
wget -q 'https://objectstorage.uk-london-1.oraclecloud.com/n/lrbvkel2wjot/b/sp3_deps/o/singularity-container_3.5.2%2Bds1-1_amd64.deb'
dpkg -i singularity-container_3.5.2+ds1-1_amd64.deb 1>&2 2>/dev/null

echo 'bind path = /work' >> /etc/singularity/singularity.conf
echo 'bind path = /data' >> /etc/singularity/singularity.conf

echo '10.0.1.2:/data /data nfs defaults,noatime,ro 0 0' >> /etc/fstab
echo '10.0.1.2:/work /work nfs defaults,noatime,rw 0 0' >> /etc/fstab

mkdir /data && mkdir /work && chown ubuntu:ubuntu /data /work

mount -a
