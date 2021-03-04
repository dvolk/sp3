import demjson, json

def get_report_json(report_file):
    report_lines = open(report_file).readlines()

    data = str()

    for i, report_line in enumerate(report_lines):
        report_line = report_line.strip()
        if report_line == "// Nextflow report data":
            data = report_lines[i+1][16:]
            data += report_lines[i+2][:-2]
            break

    data = data.replace("\\'", "")
        
    return json.dumps(json.JSONDecoder().decode(data), indent=4)

if __name__ == "__main__":
    print(get_report_json("/work/runs/79c44931-3396-4734-bbd1-8fabea10fd9b/report.html"))
