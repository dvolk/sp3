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
DEBIAN_FRONTEND=noninteractive apt install -o Dpkg::Options::='--force-confold' --force-yes -fuy \
	       nfs-common \
	       build-essential \
	       libssl-dev \
	       uuid-dev \
	       libgpgme11-dev \
	       squashfs-tools \
	       libseccomp-dev \
	       pkg-config
sleep 5
# install singularity (no binary release???)

export VERSION=1.14.12 OS=linux ARCH=amd64 && \
    wget https://dl.google.com/go/go$VERSION.$OS-$ARCH.tar.gz && \
    sudo tar -C /usr/local -xzvf go$VERSION.$OS-$ARCH.tar.gz && \
    rm go$VERSION.$OS-$ARCH.tar.gz

echo 'export PATH=/usr/local/go/bin:$PATH' >> ~/.bashrc && \
    source ~/.bashrc

export PATH=/usr/local/go/bin:$PATH
PATH=/usr/local/go/bin:$PATH

export VERSION=3.7.1 &&
    wget https://github.com/hpcng/singularity/releases/download/v${VERSION}/singularity-${VERSION}.tar.gz && \
    tar -xzf singularity-${VERSION}.tar.gz && \
    cd singularity

./mconfig && \
    make -C builddir && \
    sudo make -C builddir install

sleep 5

echo 'bind path = /work' >> /usr/local/etc/singularity/singularity.conf
echo 'bind path = /data' >> /usr/local/etc/singularity/singularity.conf

echo '10.0.1.2:/data /data nfs defaults,noatime,ro 0 0' >> /etc/fstab
echo '10.0.1.2:/work /work nfs defaults,noatime,rw 0 0' >> /etc/fstab

mkdir /data && mkdir /work && chown ubuntu:ubuntu /data /work

mount -a
