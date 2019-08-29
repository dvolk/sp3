# Fetch API
## Description

Fetch API is a Restful web API, which downloads files from different providers given some identifier

Currently, it supports two providers:

### ena1

Downloads valid paired Fastq files from the ENA (data name is any type of accession, e.g. project accession or sample accession)

### local1

Downloads local filesystem files (essentially only creates symlinks)

## Dependencies

python3, flask, pandas, requests

## Installation

    pip install -r requirements.txt
    mkdir logs

## Configuration

Fetch API is configured in fetch_api.yaml. An example of the configuration may be found in fetch_api.yaml-example

## Running

    python3 api.py
    
runs the API on port localhost:5001

## Endpoints

### /api/fetch/{kind}/new/{name}

Adds fetch to queue

Files are downloaded to disk in the background and symlinked into a flat "input" directory, ready for consumption by nextflow

Optional query parameters:

- fetch_type: all, metadata (default: all)
- fetch_range: comma separated ranges or single numbers of samples to fetch, e.g. 1-3,5,7-11,15

Returns:
- guid of fetch

### /api/fetch/{kind}/delete/{guid}

- delete files that are fetched by this guid, except files that are in other guids
- change the state of the fetch to 'deleted' in the database.

### /api/fetch/stop/{guid}

- marks the fetch with guid for stopping. The download will be stopped after the current file being downloaded finishes. The fetch will be set to failure state.

### /api/fetch/status

Retrieves the status of all runs
 
### /api/fetch/status_sample/{guid}

Retrieves the status of run with guid
 
### /api/fetch/log/{guid}

Retrievevs the log of run with guid, including the metadata of the files downloaded.
