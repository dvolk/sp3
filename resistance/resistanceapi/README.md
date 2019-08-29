# Resistance API

Resistance API provide apis for resistance related task. It is written in Python with Flask (for restful APIs) and flask_restplus (for generating document for restful APIs)

# Dependencies
    git clone https://github.com/philipwfowler/gemucator.git && \
    cd gemucator && \
    python setup.py install --user

    git clone https://github.com/philipwfowler/snpit.git && \
    cd snpit && \
    python setup.py install --user

    git clone https://github.com/philipwfowler/piezo.git && \
    cd piezo && \    
    python setup.py install --user

# Install
    git clone https://gitlab.com/MMMCloudPipeline/resistanceapi.git

    cd resistanceapi

    pip3 install -r requirements.txt

    create and give write permission to /logs folder

# Run with python built-in server
    python src/main.py

# Test
    Later
# Access
    * Default: http://localhost:8990/api/v1
    * This entry point provides a list of available APIs and how to use them

# Deployment with Docker (Note docker version will run on port 8989 in stead)
    Go to the docker folder
    * Run bash createDocker.sh [VERSION/TAG]
    * Run bash pullAndRunDocker.sh to run the app  
    The above command will mount two folders ~/DataFromDocker/Resistance/vcfs and ~/DataFromDocker/Resistance/logs to the docker so resistanceapi can access vcf input files and write logs. The folder which contains all vcf files should be mount to ~/DataFromDocker/Resistance/vcfs in advance

    The config folder can also be mounted to change the default config inside the docker.