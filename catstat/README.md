               _       _        _   
      ___ __ _| |_ ___| |_ __ _| |_ 
     / __/ _` | __/ __| __/ _` | __|
    | (_| (_| | |_\__ \ || (_| | |_ 
     \___\__,_|\__|___/\__\__,_|\__|
                                    
# catstat

catstat draws graphs based on the state of the cluster managed by catgrid

## Requirements

- python **3.6+**
- catgrid

## Installation

    git clone https://github.com/dvolk/catstat
    cd catstat
    virtualenv -p python3.6 env
    source env/bin/activate
    pip3 install flask requests matplotlib

## Configure

catstat has no configuration.

When started, it will serve a single svg graph at http://127.0.0.1:8000/draw

This graph is updated every 60 seconds and data is kept for 1440 ticks (or 1
day, assuming you run it the whole time).

Data is persisted between restarts by writing it to stat.txt every 10 minutes.
