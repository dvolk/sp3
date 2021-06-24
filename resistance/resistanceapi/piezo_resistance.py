import os
from copy import deepcopy
from datetime import datetime

import sp3predict


def get_resistance_for_tb_sample2(vcf_file, genome_object, catalogue_file):
    return sp3predict.run(
        vcf_file, genome_object, catalogue_file, True, True, False, False
    )
