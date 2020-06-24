# catpile

## Description

- stores SP3 metadata

- links pipeline runs to data fetch

- listens on localhost port 22000

## Running

systemctl --user start catpile

## Routes reference

- /get_runs_for_fetch/<fetch_uuid>

Get all pipeline runs deriving from that fetch

- /get_fetch_for_run/<pipeline_run_uuid>

Get fetch for that pipeline run

- /get_sp3_data_for_fetch/<fetch_uuid>

Get SP3 metadata for fetch uuid

- /get_sp3_data_for_run/<pipeline_run_uuid>

Get SP3 metadata for pipeline run uuid

- /get_sp3_data_for_run_sample/<pipeline_run_uuid>/<sample_name>

Get SP3 metadata for single pipeline run sample

- /fetch_to_run' (POST)

Link pipeline run to fetch

- /load_sp3_data' (POST)

Submit fetch filepath. Catpile tries to find sp3data.csv and loads metadata from it

