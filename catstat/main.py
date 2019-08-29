import time
import threading
import io
import json
import pathlib

import requests
import flask
from matplotlib.backends.backend_svg import FigureCanvasSVG as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import matplotlib.dates

data_titles = ["nodes", "cores", "mem", "used_mem", "running", "queued"]
colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple', 'tab:olive']
data_plot = data_titles
data = list()

def stat_collector():
    global data
    i = 0
    while True:
        r = requests.get('http://127.0.0.1:6000/status').json()
        nodes = r['nodes']
        queue = r['queue']

        n_nodes = len(nodes)
        cores = sum([int(node['cores']) for node in nodes.values()])
        mem = sum([int(node['mem']) // 1024 for node in nodes.values()])
        free_mem = sum([int(node['free_mem']) // 1024 for node in nodes.values()])
        used_mem = mem - free_mem
        running = sum([len(node['jobs']) for node in nodes.values()])
        queued = len(queue)

        now = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())

        print(f'{now} - nodes: {n_nodes}, cores: {cores}, mem: {mem}, free_mem: {free_mem}, running: {running}, queued: {queued}')
        data.append([time.time(), n_nodes, cores, mem, used_mem, running, queued])

        data = data[-1440:]

        # every 10 minutes, write to file
        if i >= 9:
            with open(f'stats.txt', 'w') as f:
                f.write(json.dumps(data))
            i = 0
        else:
            i = i + 1

        time.sleep(60)


app = flask.Flask(__name__)

@app.route('/draw')
def draw():
    fig = Figure(figsize=(6,3), dpi=100)
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twinx()

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
    if pathlib.Path('stats.txt').is_file():
        with open('stats.txt', 'r') as f:
            global data
            data = json.loads(f.read())

    threading.Thread(target=stat_collector).start()
    app.run(port=8000)

if __name__ == '__main__':
    main()
