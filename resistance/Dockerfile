# Docker file for Set up ResistanceAPI
# To build: docker build -t resistance .
# To run: docker run -v /vcfs:/vcfs -v /logs:/logs -v /data:/data -d -p 8990:8990 --rm resistance

FROM python:3.6.3

LABEL version="1.0.0" \
      description="Oxford MMM Drug Resistance" \
      maintainer="crookscs.it@ndm.ox.ac.uk" \
      dockerhub="oxfordmmm/resistance:v1.0.0"

WORKDIR /resistance

COPY gemucator gemucator
COPY snpit snpit
COPY piezo piezo
COPY resistanceapi resistanceapi

RUN pip3 install datreant tqdm pandas

RUN cd gemucator && python setup.py install --user
RUN cd snpit && python setup.py install --user
RUN cd piezo && python setup.py install --user
RUN cd resistanceapi && pip3 install -r requirements.txt

WORKDIR /resistance/resistanceapi

EXPOSE 8990

CMD ["python", "src/main.py"]





