import json

import flask

import piezo_resistance

app = flask.Flask(__name__)

resistanceConfig = { 'genbank_file': "/data/reports/resistance/data/H37rV_v3.gbk",
                     'catalogue_file': "/data/reports/resistance/data/CRYPTICv1.0-RSU-catalogue-H37rV_v3.csv",
                     'catalogue_name': "CRYPTICv1.0",
                     'resistance_log':  "/logs/piezo-" }

@app.route('/api/v1/resistances/piezo/<vcf_id>')
def get_resistance_for_tb_sample(vcf_id):
    vcf_filename = f"/work/reports/resistanceapi/vcfs/{vcf_id}.vcf"

    rs = piezo_resistance.get_resistance_for_tb_sample(resistanceConfig['genbank_file'],
                                                       resistanceConfig['catalogue_file'],
                                                       resistanceConfig['catalogue_name'],
                                                       resistanceConfig['resistance_log'],
                                                       vcf_id,
                                                       vcf_filename)
    return json.dumps({ 'status': 'success',
                        'data': rs,
                        'message': '' })

if __name__ == "__main__":
    app.run(port=8990, debug=True)
