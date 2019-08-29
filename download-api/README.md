# Download API
## Description

Download API is a restful web API which translates requests for files into web server urls

## Dependencies

python3, flask, pyyaml

## Configuration

edit config.yaml. E.g.:

    output_url_prefix: "https://download-api.mmmoxford.uk/files/"
    output_path_prefix: "/mnt/disk2/output/"


## Running 

    python3 api.py

## nginx configuration

configure nginx to serve files. E.g.:

    server {
        location /api {
            proxy_pass http://127.0.0.1:5003;
        }

        location /files {
            alias /mnt/disk2/output;
        }
    }

## Endpoints

### /api/download/{download_type}/{user}/{workflow}/{project}/{file_path}

returns the web url where the file may be downloaded
