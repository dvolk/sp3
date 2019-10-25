#
# Download nfnvm pipeline
#
sudo git clone https://gitlab.com/ModernisingMedicalMicrobiology/nfnvm /data/pipelines/nfnvm

sudo wget 'https://files.mmmoxford.uk/f/55e9c548c85e4f888fe3/?dl=1' -O /data/images/nfnvm-v0.1.0.img
sudo wget 'https://files.mmmoxford.uk/f/75430cb06ab84155a607/?dl=1' -O /data/references/references.nfnvm.tar
sudo mkdir /data/inputs/uploads/nfnvm_test
sudo wget 'https://files.mmmoxford.uk/f/deb29333eb4a4eaea5b9/?dl=1' -O /data/inputs/uploads/nfnvm_test/F4_BC07.fastq.gz
sudo wget 'https://files.mmmoxford.uk/f/f3b2456f5ae446c18930/?dl=1' -O /data/inputs/uploads/nfnvm_test/F10_BC01.fastq.gz
sudo wget 'https://files.mmmoxford.uk/f/465a946aeb6d41d7b3f8/?dl=1' -O /data/inputs/uploads/nfnvm_test/F11_BC01.fastq.gz

sudo tar xf /data/references/references.nfnvm.tar -C /data/references

sudo rm /data/references/references.nfnvm.tar

sudo chown -R root:root /data/references/nfnvm
sudo chmod a-w -R /data/references/nfnvm
