import time
import threading
import io
import json
import pathlib
import sqlite3
import logging
import subprocess

import requests
import flask
from matplotlib.backends.backend_svg import FigureCanvasSVG as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import matplotlib.dates
import waitress

con = sqlite3.connect('/db/catstat.sqlite', check_same_thread=False)
con.execute("create table if not exists catgrid_stats (time, nodes, cores, mem, free_mem, running, queued, free_disk_root, free_disk_data, free_disk_work)")

def du(d):
  for line in subprocess.check_output('df').decode().split('\n'):
    xs = line.split()
    if len(xs) >= 6 and  xs[5] == d:
      return int(xs[4].replace('%', ''))
  return 0

def stat_collector():
    global data
    i = 0
    while True:
        try:
            r = requests.get('http://127.0.0.1:6000/status').json()
            nodes = r['nodes']
            queue = r['queue']
        except:
            logging.warning("couldn't connect to catgrid")

        n_nodes = len(nodes)
        cores = sum([int(node['cores']) for node in nodes.values()])
        mem = sum([int(node['mem']) // 1024 for node in nodes.values()])
        free_mem = sum([int(node['free_mem']) // 1024 for node in nodes.values()])
        used_mem = mem - free_mem
        running = sum([len(node['jobs']) for node in nodes.values()])
        queued = len(queue)
        free_disk_root = du('/')
        free_disk_data = du('/data')
        free_disk_work = du('/work')

        now = time.time()

        con.execute("insert into catgrid_stats values (?,?,?,?,?,?,?,?,?,?)",
                    (now, n_nodes, cores, mem, free_mem, running, queued, free_disk_root, free_disk_data, free_disk_work))
        con.commit()

        time.sleep(60)


app = flask.Flask(__name__)

@app.route('/data')
def get_data():
    data = con.execute("select * from catgrid_stats order by time desc limit 1440").fetchall()

    # convert to SoA and format the time
    ret = list()
    for i in range(0, len(data[0])):
        ret.append(list())
    print(ret)
    for i,_ in enumerate(data):
        for j in range(0, len(data[i])):
            ret[j].append(data[i][j])
    for i,_ in enumerate(ret[0]):
        ret[0][i] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ret[0][i]))

    return json.dumps({'status': 'success',
                       'message': '',
                       'data': ret })

@app.route('/draw')
def draw():
    fig = Figure(figsize=(6,3), dpi=100)
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twinx()

    data = con.execute("select * from catgrid_stats").fetchall()

    data2 = list(map(list, zip(*data)))
    t = matplotlib.dates.epoch2num(data2[0])

    data_titles = ["nodes", "cores", "mem", "used_mem", "running", "queued"]

    lns = 0

    for i, col in enumerate(data2[1:]):
        if data_titles[i] in data_plot and data_titles[i] in ["mem", "used_mem"]:
            pass
            ax1.plot(t, col, label=data_titles[i], linewidth=1, linestyle=':', color=colors[i])
        elif data_titles[i] in data_plot:
            ax2.plot(t, col, label=data_titles[i], linewidth=1, linestyle='-', color=colors[i])

#    lns = sum(lns)
#    labs = [l.get_label() for l in lns]

    date_formatter = matplotlib.dates.DateFormatter("%H:%M")
    ax1.xaxis.set_major_formatter(date_formatter)
    ax2.xaxis.set_major_formatter(date_formatter)

    fig.subplots_adjust(top=0.95, bottom=0.1, left=0.07)
#    ax.yaxis.tick_right()
    ax2.legend()
#    ax1.legend(lns, labs)
    canvas = FigureCanvas(fig)
    svg_output = io.StringIO()
    canvas.print_svg(svg_output)

    response = flask.make_response(svg_output.getvalue())
    response.headers['Content-Type'] = 'image/svg+xml'
    return response

def main():
    threading.Thread(target=stat_collector).start()
    waitress.serve(app, listen='127.0.0.1:8000')

if __name__ == '__main__':
    main()
