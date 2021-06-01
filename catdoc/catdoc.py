import json, datetime

import argh
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
import PIL.Image

styles = getSampleStyleSheet()
brand_org = ""

def first_page(canvas, doc):
    if brand_org == "PHE":
        canvas.drawImage("/home/ubuntu/sp3/catdoc/PublicHealthEngland.jpg", 7*mm, 277*mm, width=16*mm, height=1*cm)
    else:
        canvas.drawImage("/home/ubuntu/sp3/catdoc/logo.png", 7*mm, 277*mm, width=2*cm, height=1*cm)

    canvas.setFont('Helvetica', 20)
    canvas.drawString(30*mm, 280*mm, "Oxford SP3 Sample Analysis Report")
    canvas.setFont('Helvetica', 12)

    add_page_number(canvas, doc)

def add_page_number(canvas, doc):
    page_num = canvas.getPageNumber()
    time_str = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    canvas.drawString(140*mm, 7*mm, time_str)
    text = f"Page {page_num}"
    canvas.drawRightString(200*mm, 7*mm, text)
    canvas.drawRightString(200*mm, 280*mm, text)

def go(report_json_path, pdf_out_path, brand=""):
    global brand_org
    brand_org = brand
    with open(report_json_path) as f:
        data = json.loads(f.read())

    margin = 0.5
    doc = SimpleDocTemplate(pdf_out_path, pagesize=A4, showBoundary=0, leftMargin=margin*cm, rightMargin=margin*cm, topMargin=margin*cm, bottomMargin=2*margin*cm)
    elements = list()
    top_para_style = ParagraphStyle('top_para', fontSize=14)
    elements.append(Spacer(0, 20*mm))
    elements.append(Paragraph(f"Sample name: {data.get('dataset_id')}", top_para_style))
    elements.append(Spacer(0, 3*mm))
    elements.append(Paragraph(f"Pipeline run ID: {data.get('run_uuid')}", top_para_style))
    elements.append(Spacer(0, 3*mm))

    i = 0

    if 'catpile_metadata' in data:
        i += 1
        elements.append(Paragraph(f"{i}. Submission metadata", styles["Heading2"]))
        tbl = data["catpile_metadata"]["data"]
        del tbl["original_file_sha512"]
        del tbl["clean_file_sha512"]
        del tbl["original_file_sha1"]
        del tbl["clean_file_sha1"]
        del tbl["original_file_md5"]
        del tbl["clean_file_md5"]
        del tbl["subindex"]
        del tbl["sample_filename"]
        data_ = list(tbl.items())
        data_ = data_[3:] + data_[0:3]
        data_.insert(0, ["Field", "Value"])
        t = Table(data_, hAlign='LEFT')
        t.setStyle(TableStyle( [('GRID', (0,0), (-1,-1), 0.25, colors.grey)] ))
        elements.append(t)

    if 'kraken2_speciation' in data:
        i += 1
        elements.append(Paragraph(f"{i}. Kraken2", styles["Heading2"]))
        tbl = data["kraken2_speciation"]["data"]
        tbldata = []
        for k1, v1 in tbl.items():
            if type(v1) == dict:
                continue
            if k1 == "Warnings":
                continue
            for v2 in v1:
                if type(v2) == dict:
                    tbldata.append([k1, v2["name"], v2["percentage"], v2["reads"]])
        tbldata.insert(0, ["Type", "Identified", "Coverage", "Reads"])
        t = Table(tbldata, hAlign='LEFT')
        t.setStyle(TableStyle( [('GRID', (0,0), (-1,-1), 0.25, colors.grey)] ))
        elements.append(t)

    if 'mykrobe_speciation' in data:
        i += 1
        elements.append(Paragraph(f"{i}. Mykrobe", styles["Heading2"]))
        tbl = data["mykrobe_speciation"]["data"]
        data_ = list()
        data_.append(["Type", "Identified", "Coverage", "Median depth"])
        if type(tbl["phylo_group"]) == dict:
            for k,v in tbl["phylo_group"].items():
                data_.append(["Phylo group", k, v["percent_coverage"], v["median_depth"]])
        if type(tbl["species"]) == dict:
            for k,v in tbl["species"].items():
                data_.append(["Species", k, v["percent_coverage"], v["median_depth"]])
        if type(tbl["sub_complex"]) == dict:
            for k,v in tbl["sub_complex"].items():
                data_.append(["Sub-complex", k, v["percent_coverage"], v["median_depth"]])
        t = Table(data_, hAlign='LEFT')
        t.setStyle(TableStyle( [('GRID', (0,0), (-1,-1), 0.25, colors.grey)] ))
        elements.append(t)

        elements.append(Paragraph("Lineages", styles["Heading3"]))
        if "lineages" in tbl:
            for k1 in tbl["lineages"]:
                data_ = [["Calls", "Variant name", "Coverage", "Median depth", "Min non-zero depth", "Kmer count", "Klen"]]
                for k,v in tbl[k1].items():
                    k2 = list(v.keys())[0]
                    v2 = list(v.values())[0]
                    row = [k, k2, v2["percent_coverage"], v2["median_depth"], v2["min_non_zero_depth"], v2["kmer_count"], v2["klen"]]
                    data_.append(row)
                t = Table(data_, hAlign='LEFT')
                t.setStyle(TableStyle( [('GRID', (0,0), (-1,-1), 0.25, colors.grey)] ))
                elements.append(Paragraph(k1, styles["Heading4"]))
                elements.append(t)

    if 'samtools_qc' in data:
        i += 1
        elements.append(Paragraph(f"{i}. Samtools QC", styles["Heading2"]))
        tbl = data["samtools_qc"]["data"]
        data_ = list(tbl.items())
        data_.insert(0, ["Field", "Value"])
        t = Table(data_, hAlign='LEFT')
        t.setStyle(TableStyle( [('GRID', (0,0), (-1,-1), 0.25, colors.grey)] ))
        elements.append(t)

    if 'pick_reference' in data:
        i += 1
        s = data["pick_reference"]["data"]
        elements.append(Paragraph(f"{i}. Mapped reference", styles["Heading2"]))
        elements.append(Paragraph(f"Reference: {s['pick_taxid']}"))

    if 'resistance' in data:
        i += 1
        elements.append(Paragraph(f"{i}. Resistance", styles["Heading2"]))
        elements.append(Paragraph("Drugs", styles["Heading3"]))
        tbl = data["resistance"]["data"]
        data_ = [list(tbl["prediction_ex"].keys()),
                 list(tbl["prediction_ex"].values())]
        t = Table(data_, hAlign='LEFT')
        t.setStyle(TableStyle( [('GRID', (0,0), (-1,-1), 0.25, colors.grey)] ))
        elements.append(t)
        pred_drug_names = ['INH', 'RIF', 'PZA', 'EMB', 'AMI', 'KAN', 'LEV', 'STM']
        data_ = [["Gene mutation", "Change", "GT conf", "Drug", "Support"]]
        for item in tbl["mutations"]:
            if item["mutation_name"][-1] not in ['z', 'Z'] and item['mutation_name'][0] != item['mutation_name'][-1]:
                for d in data['resistance']['data']['res_rev_index'][item['gene_name'] + '_' + item['mutation_name']]:
                    if d['source'] != 'phylosnp':
                        if d['drug_name'] in pred_drug_names:
                            data_.append([ item['gene_name'] + '_' + item['mutation_name'],
                                           item['ref'] + ' → ' + item['alt'],
                                           item.get('gt_conf'),
                                           d['drug_name'],
                                           d['source'] ])
        t = Table(data_, hAlign='LEFT')
        t.setStyle(TableStyle( [('GRID', (0,0), (-1,-1), 0.25, colors.grey)] ))
        elements.append(Paragraph("Mutations", styles["Heading3"]))
        elements.append(t)

    try:
        if 'run_distmatrix' in data:
            i += 1
            s = list(data["run_distmatrix"]["data"]["samples"].values())[0]
            elements.append(Paragraph(f"{i}. FASTA", styles["Heading2"]))
            elements.append(Paragraph(f"Sample FASTA information", styles["Heading3"]))
            elements.append(Paragraph(f"Header: {s['header']}"))
            elements.append(Paragraph(f"Bases: {s['size']}"))
            elements.append(Paragraph(f"Sequence md5: {s['seq_md5']}"))
            elements.append(Paragraph(f"Base counts: {s['counts']['N']} N, {s['counts']['T']} T, {s['counts']['C']} C, {s['counts']['G']} G, {s['counts']['A']} A"))
            elements.append(Paragraph(f"FASTA distances within run", styles["Heading3"]))
            data_ = list(s['neighbours'].items())
            data_.insert(0, ["Neighbour", "Distance"])
            t = Table(data_, hAlign='LEFT')
            t.setStyle(TableStyle( [('GRID', (0,0), (-1,-1), 0.25, colors.grey)] ))
            elements.append(t)
    except:
        pass

    doc.build(elements, onFirstPage=first_page, onLaterPages=add_page_number)

if __name__ == "__main__":
    argh.dispatch_command(go)
