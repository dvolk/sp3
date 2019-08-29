#! /usr/bin/python3.5
import argparse, os 
from helper import logger

class CompassResistance():
    @staticmethod
    def getResistanceForSample(genbank_file,catalog_file,catalogue_name,resistance_log,sample_id,vcf_file):                
        rs={}
        rs["metadata"]="TBC"
        rs["mutations"]="TBC"
        rs["effects"]="TBC"
        logger.info('Return results')
        return rs       
