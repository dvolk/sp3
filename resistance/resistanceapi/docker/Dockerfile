#Learn from https://github.com/TrienDo/flask-example/blob/master/Dockerfile
#Can create different config files for different environments later -> deploy docker for different envs
FROM python:3.6.3  
LABEL maintainer="MMM Oxford <crookcs.it@ndm.ox.ac.uk>"
#Install dependencies
RUN git clone https://github.com/philipwfowler/gemucator.git && \
    cd gemucator && \
    python setup.py install --user

RUN git clone https://github.com/philipwfowler/snpit.git && \
    cd snpit && \
    python setup.py install --user

RUN pip3 install PyVCF pandas datreant

RUN git clone https://github.com/philipwfowler/piezo.git && \
    cd piezo && \    
    python setup.py install --user

WORKDIR /resistanceapi
COPY ./requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt
#Copy config and src folder (config folder could be mounted in the future)
COPY ./data /data
COPY ./config /config
COPY ./src /resistanceapi
ENTRYPOINT ["gunicorn"]
CMD ["-w", "3", "-b", "0.0.0.0:8989","main:app"]