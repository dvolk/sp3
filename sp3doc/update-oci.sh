#! /bin/bash

# Stop services, daemon reload and restart
echo "stopping services"
if [ -f "/home/ubuntu/catsgo/buckets.txt" ]
then
    # Stopping watchers
    cat /home/ubuntu/catsgo/buckets.txt | while read line
    do
        systemctl --user stop dir_watcher@${line//,}.service
    done
fi
systemctl --user stop run_watcher@oxforduni-ncov2019-artic-nf-illumina.service
systemctl --user stop run_watcher@oxforduni-ncov2019-artic-nf-nanopore.service

# Stopping sp3 services
systemctl --user stop catcloud-oracle
systemctl --user stop catdap
systemctl --user stop catdownload
systemctl --user stop catfetch
systemctl --user stop catgrid
systemctl --user stop catstat
systemctl --user stop cattag
systemctl --user stop catpile
systemctl --user stop catweb

# Check SP3 version
echo "checking SP3 version"
pushd /home/ubuntu/sp3
CURRENT_SP3_VERSION=$(git describe --tags)
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/gitlab_key -o StrictHostKeyChecking=no' git fetch --all --tags
LATEST_SP3_VERSION=$(git tag -l --sort=-v:refname "v*" | head -n 1)
if [ "${CURRENT_SP3_VERSION}" != "${LATEST_ENV_VERSION}" ]
then
    echo "updating sp3 to $LATEST_SP3_VERSION"
    git checkout ${LATEST_SP3_VERSION}
fi
popd

# Check if containers env version has changed
echo "checking container environment"
CURRENT_ENV_VERSION=$(ls /data/images/aln2type_*.sif | awk -F_ '{print $NF}' | sed 's/\.[^.]*$//')
LATEST_ENV_VERSION=$(curl -s -L -I -o /dev/null -w '%{url_effective}' https://github.com/GenomePathogenAnalysisService/SARS-COV-2_environments/releases/latest | xargs basename)
if [ "${CURRENT_ENV_VERSION}" != "${LATEST_ENV_VERSION}" ]
then
    echo "updating containers to $LATEST_ENV_VERSION"
    # Move old images
    sudo mkdir -p /data/images/old_versions/${CURRENT_ENV_VERSION}
    sudo mv /data/images/*.sif /data/images/old_versions/${CURRENT_ENV_VERSION}
    sudo mv /data/images/*.simg /data/images/old_versions/${CURRENT_ENV_VERSION}
    sudo mv /data/images/*.img /data/images/old_versions/${CURRENT_ENV_VERSION}

    # Download new images
    oci os object bulk-download -bn artic_images --download-dir /tmp --overwrite --auth instance_principal --prefix ${LATEST_ENV_VERSION}

    # Move pipeline images to /data
    sudo mv /tmp/*/*.sif /data/images/
    sudo mv /tmp/*/*.simg /data/images/
    sudo mv /tmp/*/*.img /data/images/
    sudo chown root:root /data/images/*.sif
    sudo chown root:root /data/images/*.simg
    sudo chown root:root /data/images/*.img
fi

# Check COVID pipeline version
echo "Checking COVID pipeline version"
pushd /data/pipelines/ncov2019-artic-nf
CURRENT_COVID_ENV=$(git describe --tags)
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/gitlab_key -o StrictHostKeyChecking=no' sudo git fetch --all --tags
LATEST_COVID_ENV=$(git tag -l --sort=-v:refname "sp3env-v*" | head -n 1)
if [ "${CURRENT_COVID_ENV}" != "${LATEST_COVID_ENV}" ]
then
    echo "updating pipeline to $LATEST_COVID_ENV"
    sudo git checkout ${LATEST_COVID_ENV}
fi
popd

# Check CATSGO
echo "checking CATSGO version"
pushd /home/ubuntu/catsgo
CURRENT_CATSGO_VERSION=$(git describe --tags)
LATEST_CATSGO_VERSION=$(curl -s -L -I -o /dev/null -w '%{url_effective}' https://github.com/oxfordmmm/catsgo/releases/latest | xargs basename)
if [ "${CURRENT_CATSGO_VERSION}" != "${LATEST_CATSGO_VERSION}" ]
then
    echo "updating CATSGO to $LATEST_CATSGO_VERSION"
    GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/gitlab_key -o StrictHostKeyChecking=no' git fetch --all  --tags
    git checkout ${LATEST_CATSGO_VERSION}
fi
popd

# Restart sp3 services
systemctl --user daemon-reload
systemctl --user restart catdap
systemctl --user restart catdownload
systemctl --user restart catfetch
systemctl --user restart catgrid
systemctl --user restart catstat
systemctl --user restart cattag
systemctl --user restart catpile
systemctl --user restart catweb
systemctl --user restart catcloud-oracle

# Restart watchers
systemctl --user restart run_watcher@oxforduni-ncov2019-artic-nf-illumina.service
systemctl --user restart run_watcher@oxforduni-ncov2019-artic-nf-nanopore.service
if [ -f "/home/ubuntu/catsgo/buckets.txt" ]
then
    cat /home/ubuntu/catsgo/buckets.txt | while read line
    do
        systemctl --user restart dir_watcher@${line//,}.service
    done
fi