#!/bin/bash

# Get SP3 version
pushd /home/ubuntu/sp3
SP3_VERSION=$(git describe --tags --dirty)
popd

# Get catsgo version
pushd /home/ubuntu/catsgo
CATSGO_VERSION=$(git describe --tags --dirty)
popd

# Get SARS-COV-2_environment version
SARS_ENV_VERSION=$(ls /data/images/aln2type_*.sif | awk -F_ '{print $NF}' | sed 's/\.[^.]*$//')

# Get covid pipeline version
pushd /data/pipelines/ncov2019-artic-nf
COVID_PIPE_VERSION=$(git describe --tags --dirty)
popd

# Get viridian pipeline version
VIRIDIAN_VERSION=$(ls /data/images/viridian_workflow_*.img | awk -F_ '{print $NF}' | sed 's/\.[^.]*$//')

mkdir -p /home/ubuntu/release_notes
filename=/home/ubuntu/release_notes/$(date +%F_%T)_versions.txt
echo "SP3 - ${SP3_VERSION}
CATSGO - ${CATSGO_VERSION}
SARS-COV-2_environments - ${SARS_ENV_VERSION}
COVID_pipeline - ${COVID_PIPE_VERSION}
Viridian version - ${VIRIDIAN_VERSION}" >> $filename
echo "release_notes available @ ${filename}"
