# cattag

## Description

Cattag is a small service that provides a web API for adding tags to SP3 runs and samples

## Requirements

- python 3.6+
- flask

## Installation

    git clone https://gitlab.com/MMMCloudPipeline/cattag
    cd cattag
    pip3 install -r requirements.txt

## API endpoints

- /add_run_tag

POST json dict with pipeline_name, run_uuid, tag_type and tag_name

- /add_sample_tag

POST json dict with pipeline_name, run_uuid, sample_name, tag_type and tag_name

- GET /get_sample_tags_for_run/<run_uuid>

get sample tags for pipeline run_uuid