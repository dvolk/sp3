# Resistance

Use ResistanceApi and other related package for drug resistance 

This repo uses three git submodules:
    
[gemucator](https://github.com/philipwfowler/gemucator.git)

[piezo](https://github.com/philipwfowler/piezo)

[resistanceapi](https://gitlab.com/MMMCloudPipeline/resistanceapi.git)

## Get Code
    git clone https://gitlab.com/MMMCloudPipeline/resistance
    cd resistance
    git submodule init
    git submodule update

## Install & Run
    0. Make a virtual enviornment
        virtualenv -p python3 env
        bash
        source env/bin/activate
        export PYTHONPATH=~/.local/lib/python3.6/site-packages/
        
    1. Install submodule gemucator
        cd gemucator && \
        python setup.py install --user
        cd ..

    2. Install submodule piezo
        pip3 install datreant tqdm pyvcf pandas
        cd piezo && \    
        python setup.py install --user
        cd ..

    3. Install submodule resistanceapi
        cd resistanceapi && \
        pip3 install -r requirements.txt
        cd ..

    4. Create data, logs and vcfs folder
        sudo mkdir -p /work/logs/reports/resistanceapi
        sudo chown [user]:[group] /work/logs/reports/resistanceapi
        sudo mkdir -p /work/reports/resistanceapi/vcfs
        sudo chown [user]:[group] /work/reports/resistanceapi/vcfs
        sudo mkdir -p /data/reports/resistance/data
        sudo chown [user]:[group] /data/reports/resistance/data

        sudo cp -r piezo/config/*.* /data/reports/resistance/data
        cp [clockwork final vcfs] to /work/reports/resistanceapi/vcfs

    6. Start Resistance API
        cd resistanceapi
        python src/main.py
        
## Test resistance api endpoints
    curl -X GET "http://localhost:8990/api/v1/resistances/data" -H  "accept: application/json"
    curl -X GET "http://localhost:8990/api/v1/resistances/data/genelist.txt" -H  "accept: application/json"
    curl -X GET "http://localhost:8990/api/v1/resistances/piezo/ERS2394073?type=piezo" -H  "accept: application/json"
    
## Test resistance api work with 13 VCFs and check the json result

    1. Start resistance api: python3 resistanceapi/src/main.py
    2. Have the test files ({01-13}.vcf files under piezo/examples) ready in /vcfs
    3. Install nose in your virtual env: pip3 install nose requests
    4. Run nosetests tests, expected standard output:
    
    docker@ubuntu-docker:~/Code/resistance$ source ~/VirtualEnvs/drug/bin/activate
    (drug) docker@ubuntu-docker:~/Code/resistance$ nosetests tests
    ...............
    ----------------------------------------------------------------------
    Ran 17 tests in 96.209s
    OK
    
    To run a specific test:
    nosetests tests/test_api.py:test_data_json
    
## Update Catalogue
    
    1. Copy catalog from piezo/config to /data folder 
    2. Change config resistanceapi/config/config.json
    3. Restart resistanceapi    
        

## Docker Deployment
    
    docker pull oxfordmmm/resistance:{tag}
    docker run -v /vcfs:/vcfs -v /logs:/logs -v /data:/data -d -p 8990:8990 --rm oxfordmmm/resistance:{tag}
    
Note: Host has folder: /vcfs, /data and /logs (ref: Install & Run, step 5)

