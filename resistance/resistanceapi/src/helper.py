#Tutorial: http://michal.karzynski.pl/blog/2016/06/19/building-beautiful-restful-apis-using-flask-swagger-ui-flask-restplus/
import os
import json
import logging
import logging.config
from flask_restplus import Api

logger = logging.getLogger(__name__)

api = Api(version='1.0', title='ResistanceAPI', description='APIs for resistance service')

resistanceConfig = {}

class StatusCode:
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"

def configureApp(flask_app):
    configPath = os.path.normpath(os.path.join(os.path.dirname(__file__), '../config/config.json'))
    if os.path.exists(configPath):
        with open(configPath) as configFile:
            logger.info('Config file found!')
            appConfig = json.load(configFile)
            flask_app.config['SERVER_IP'] = appConfig['FLASK_SERVER_IP']
            flask_app.config['SERVER_PORT'] = appConfig['FLASK_SERVER_PORT']
            flask_app.config['SWAGGER_UI_DOC_EXPANSION'] = appConfig['RESTPLUS_SWAGGER_UI_DOC_EXPANSION']
            flask_app.config['RESTPLUS_VALIDATE'] = appConfig['RESTPLUS_VALIDATE']
            flask_app.config['RESTPLUS_MASK_SWAGGER'] = appConfig['RESTPLUS_MASK_SWAGGER']
            flask_app.config['ERROR_404_HELP'] = appConfig['RESTPLUS_ERROR_404_HELP']
            flask_app.config['FLASK_DEBUG'] = appConfig['FLASK_DEBUG']

            resistanceConfig['GENBANK_FILE'] = appConfig['GENBANK_FILE']
            resistanceConfig['CATALOGUE_FILE'] = appConfig['CATALOGUE_FILE']
            resistanceConfig['CATALOGUE_NAME'] = appConfig['CATALOGUE_NAME']
            resistanceConfig['RESISTANCE_LOG'] = appConfig['RESISTANCE_LOG']
    else:
        logger.info('No config file found! Defaul values are used')
        flask_app.config['SERVER_IP'] = '0.0.0.0'
        flask_app.config['SERVER_PORT'] = 80
        flask_app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
        flask_app.config['RESTPLUS_VALIDATE'] = True
        flask_app.config['RESTPLUS_MASK_SWAGGER'] = False
        flask_app.config['ERROR_404_HELP'] =  False
        flask_app.config['FLASK_DEBUG'] = False

        resistanceConfig['GENBANK_FILE'] = "/data/reports/resistance/data/H37rV_v2.gbk"
        resistanceConfig['CATALOGUE_FILE'] = "/data/reports/resistance/data/LID2015-RSU-catalogue-v1.0-H37rV_v2.csv"
        resistanceConfig['CATALOGUE_NAME'] = "LID2015B"
        resistanceConfig['RESISTANCE_LOG'] = "/logs/piezo-"

def configureLogging():
    configPath = os.path.normpath(os.path.join(os.path.dirname(__file__), '../config/logconfig.json'))
    if os.path.exists(configPath):
        with open(configPath, 'rt') as f:
            config = json.load(f)
            logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

def readDataFile(fileName):
    dataPath = os.path.normpath(os.path.join(os.path.dirname(__file__), '/data/reports/resistance/data/', fileName))
    if os.path.exists(dataPath):
        with open(dataPath, 'rt') as f:
            return f.read()
    else:
        return None

def getDataFileList():
    dataPath = os.path.normpath(os.path.join(os.path.dirname(__file__), '/data/reports/resistance/data/'))
    allFiles=os.listdir(dataPath)
    return allFiles

def getVcfForSample(method,sampleId):
    dataPath = ""
    if(method=="mmmoxford"):
        dataPath = os.path.normpath(os.path.join('/work/reports/resistanceapi/vcfs',sampleId,'MAPPING','2e6b7bc7-f52c-4649-8538-c984ab3894bb_R00000039','STD/basecalls',sampleId + '_v3.vcf.gz'))
    elif(method=="piezo"):
        dataPath = os.path.normpath(os.path.join('/work/reports/resistanceapi/vcfs',sampleId + '.vcf'))
    if os.path.exists(dataPath):
        return dataPath
    else:
        return None

def generateDictionary(status, data, message):
    rs = {}
    rs["status"] = status
    rs["data"] = data
    rs["message"] = message
    return rs

@api.errorhandler
def default_error_handler(e, isDebug, message = 'An unhandled exception occurred.'):
    logger.exception(message)
    if not isDebug:
        return {'message': message}, 500
