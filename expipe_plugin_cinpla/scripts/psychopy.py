from expipe_plugin_cinpla.imports import *
import os
import json


def _process_psychopy(action, action_id, jsonpath):
    '''
    keys = ["image", "sparsenoise", "grating", "sparsenoise", "movie"]
    valuekeys = ["duration", "image", "phase", "spatial_frequency", "frequency", "orientation", "movie"]
    {"image": {"duration": 0.25, "image": "..\\datasets\\converted_images\\image0004.png"}}
    {"sparsenoise": {"duration": 0.25, "image": "..\\datasets\\sparse_noise_images\\image0022.png"}}
    {"grating": {"duration": 0.25, "phase": 0.5, "spatial_frequency": 0.16, "frequency": 0, "orientation": 120}}
    {"movie": {"movie": "..\\datasets\\converted_movies\\segment1.mp4"}}
    {"grating": {"phase": "f*t", "duration": 2.0, "spatial_frequency": 0.04, "frequency": 4, "orientation": 225}}
    {"grayscreen" : {"duration": 300.}}
    '''


    print("Converting PsychoPy data to exdir format")

    # Reader json into function
    json_data = []
    with open(jsonpath, 'r') as f:
        for line in f.readlines():
            json_line = line.replace("'", '"')
            try:
                json_data.append(json.loads(json_line))
            except json.JSONDecodeError:
                print("Skipping line. The line is not in json format:\n{}".format(line))

    # Define exdir project
    action = project.actions[action_id]
    exdir_path = _get_data_path(action)
    exdir_file = exdir.File(exdir_path, plugins=exdir.plugins.quantities)
    epochs = exdir_file.require_group("epochs")
    psychopy = epochs.require_group("psychopy")

    # Get epoch dataset from json
    keys = json_data.keys()
    data_type_setsize = len(set(keys))
    if data_type_setsize == 1:
        key = keys()[0]
        psychopy.require_dataset('timestamp', data=time[key])
        psychopy.require_dataset('duration', data=duration[key])
        psychopy.require_dataset('orrientation', data=orrientation[key])

    elif data_type_setsize > 1:
        for key in json_data.keys():
            psychopy.require_dataset('timestamp', data=time[key])
            psychopy.require_dataset('duration', data=duration[key])
            psychopy.require_dataset('orrientation', data=orrientation[key])

    print("Done. The data is located in {}".format(exdir_path))
