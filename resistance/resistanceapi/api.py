import json
import pathlib
import sys
import traceback

import flask
import piezo_resistance
import waitress
import yaml

app = flask.Flask(__name__)

resistanceConfig = yaml.load(open("config.yaml", "r"))


def get_resistance_for_tb_sample(vcf_id):
    vcf_filename = str(pathlib.Path(resistanceConfig["vcf_location"]) / f"{vcf_id}.vcf")

    try:
        rs = piezo_resistance.get_resistance_for_tb_sample2(
            vcf_filename,
            resistanceConfig["genome_object"],
            resistanceConfig["catalogue_file"],
        )
        return json.dumps(
            {"status": "success", "data": rs, "message": {"config": resistanceConfig}}
        )
    except Exception as e:
        return json.dumps(
            {"status": "failure", "data": "", "message": traceback.format_exc()}
        )


@app.route("/api/v1/resistances/piezo/<vcf_id>")
def flask_get_resistance_for_tb_sample(vcf_id):
    return get_resistance_for_tb_sample(vcf_id)


if __name__ == "__main__":
    waitress.serve(app, listen="127.0.0.1:8990")
