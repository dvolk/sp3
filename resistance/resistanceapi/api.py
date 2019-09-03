import json
import sys
import traceback
import pathlib

import yaml
import flask

import piezo_resistance

app = flask.Flask(__name__)

resistanceConfig = yaml.load(open('config.yaml', 'r'))

def get_resistance_for_tb_sample(vcf_id):
    vcf_filename = str(pathlib.Path(resistanceConfig['vcf_location']) / f"{vcf_id}.vcf")

    try:
        rs = piezo_resistance.get_resistance_for_tb_sample(resistanceConfig['genbank_file'],
                                                           resistanceConfig['catalogue_file'],
                                                           resistanceConfig['catalogue_name'],
                                                           resistanceConfig['resistance_log'],
                                                           vcf_id,
                                                           vcf_filename)
        return json.dumps({ 'status': 'success',
                            'data': rs,
                            'message': '' })
    except Exception as e:
        return json.dumps({ 'status': 'failure',
                            'data': '',
                            'message': traceback.format_exc() })

@app.route('/api/v1/resistances/piezo/<vcf_id>')
def flask_get_resistance_for_tb_sample(vcf_id):
    return get_resistance_for_tb_sample(vcf_id)

if __name__ == "__main__":
    app.run(port=8990, debug=True)
