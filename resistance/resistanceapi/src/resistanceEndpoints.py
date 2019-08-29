from flask import request
from flask_restplus import Resource, reqparse
from helper import api, logger, readDataFile, getVcfForSample, generateDictionary, StatusCode, resistanceConfig,getDataFileList
from PiezoResistance import *
from CompassResistance import *

ns = api.namespace('resistances', description='Endpoints for TB resistance')

method_arguments = reqparse.RequestParser()
method_arguments.add_argument('type', choices=["piezo","mmmoxford","gatk"])
@ns.route('/<string:method>/<string:id>')
@api.response(404, 'Vcf file or method not found.')
class ResistanceItemWithMethod(Resource):
    @api.expect(method_arguments,validate=True)
    def get(self, method, id):
        """Interpreting resistance prediction for a TB sample using different methods."""
        logger.info("Interpreting resistance prediction for a TB sample: " + id)            
        vcfPath = getVcfForSample(method,id)    
        if(vcfPath is None):
            return generateDictionary(StatusCode.ERROR,"","Either the sample Id or the method is not valid or the vcf file of the sample does not exist")
        if (method == "piezo"):
            rs = PiezoResistance.getResistanceForSample(resistanceConfig['GENBANK_FILE'],resistanceConfig['CATALOGUE_FILE'],
            resistanceConfig['CATALOGUE_NAME'],resistanceConfig['RESISTANCE_LOG'],id,vcfPath)
            return generateDictionary(StatusCode.SUCCESS,rs,"")
        elif (method == "mmmoxford"):
            rs = CompassResistance.getResistanceForSample('GENBANK_FILE','CATALOGUE_FILE','CATALOGUE_NAME','RESISTANCE_LOG',id,vcfPath)
            return generateDictionary(StatusCode.SUCCESS,rs,"Not implemented yet")
        elif (method == "gatk"):
            return generateDictionary(StatusCode.SUCCESS,vcfPath,"Not implemented yet")        
        return generateDictionary(StatusCode.ERROR,"","Resistance method not valid")

@ns.route('/data')
class ResistanceDataList(Resource):        
    def get(self):
        """Returning list of files supporting the resistance service."""        
        return generateDictionary(StatusCode.SUCCESS,getDataFileList(),"")

@ns.route('/data/<string:filename>')
@api.response(404, 'Resistance data file not found.')
class ResistanceData(Resource):    
    def get(self,filename):
        """Returning a data file supporting the resistance service. Run the /resistances/data to see the list of files"""
        logger.info("Data file: " + filename)        
        rs = readDataFile(filename)
        if (rs is not None):
            return generateDictionary(StatusCode.SUCCESS,rs,"")        
        else:
            return generateDictionary(StatusCode.ERROR,"","Invalid filename")