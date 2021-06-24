import requests


def get_neighbours(pipeline_run_uuid, sample_name, distance):
    combine_name = pipeline_run_uuid + "_" + sample_name
    ret = requests.get(
        f"https://persistence.mmmoxford.uk/api_cw_get_neighbours/{combine_name}/{distance}"
    )
    try:
        ret = ret.json()
    except:
        print("fail whale: {res.text}")
        ret = ret.text
    return ret


def trim_neighbours(neighbours, target_neighbours):
    while True:
        # find max
        max_d = -1
        for x in neighbours:
            if int(x[1]) > max_d:
                max_d = int(x[1])
        # remove max neighbours
        for x in neighbours:
            if int(x[1]) == max_d:
                neighbours.remove(x)
                if len(neighbours) == target_neighbours:
                    return neighbours


def nifty_neighbours(
    pipeline_run_uuid,
    sample_name,
    target_neighbours=50,
    initial_distance=50,
    max_distance=400,
    trim=False,
):
    neighbours = list()
    distance = initial_distance
    while True:
        neighbours = get_neighbours(pipeline_run_uuid, sample_name, distance)
        if type(neighbours) is str:
            return neighbours
        if len(neighbours) >= target_neighbours or distance >= max_distance:
            if trim:
                return trim_neighbours(neighbours, target_neighbours)
            else:
                return neighbours
        distance = distance * 2
