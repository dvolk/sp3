               _             _     _ 
      ___ __ _| |_ __ _ _ __(_) __| |
     / __/ _` | __/ _` | '__| |/ _` |
    | (_| (_| | || (_| | |  | | (_| |
     \___\__,_|\__\__, |_|  |_|\__,_|
                   |___/              

# A grid scheduler for humans

## Description

catgrid is configurationless, agentless grid scheduler with a web api.

When a node is added catgrid connects to it over ssh and records the number
of cores and the amount of memory it has.

jobs are queued and then run as long as there is a node with an available
core and enough memory to run the job.

The only way to interact with catgrid is through a web api. The following
operations are provided:

- adding a node
- removing a node
- queueing a job
- checking job result
- terminating a job
- status information on nodes and jobs

## Requirements

- python **3.6+**
- flask 
- paramiko

Compute nodes must be accessible over ssh without password challenges. PKI is
recommended but it's up to you :)

## Installation

    git clone https://gitlab.com/dvolk/hypergrid
    cd hypergrid
    pip install -r requirements.txt

## API endpoints

- POST /submit 

post json dict with name, script, working_dir and mem. Returns job uuid

- GET /terminate/{job_id}

Terminate (or remove from queue) job with job id

- GET /output/(uuid)

returns (return code, stdout, stderr) of job, or nothing if it's still running)

- GET /add_node/(name)

Adds a node. Name must be resolvable

- GET /remove_node/(name)

Removes a node. Waits for jobs to finish. Disables adding new jobs to node.

- GET /status

Information on nodes and running jobs    

## Example

    python3 hypergrid.py node01 node02 node03

starts catgrid and adds 3 initial nodes
