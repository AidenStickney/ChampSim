import sqlite3
import json
import sys
import os
from datetime import datetime
import requests

DB_FILE = json.load(open("../config.json"))["DB_FILE"]
API_ENDPOINT = json.load(open("../config.json"))["API_ENDPOINT"]
UPDATE_API = json.load(open("../config.json"))["UPDATE_API"] 

def update_local_db(trace, config, timestamp, status, result=None, duration=None, additional_info=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    directory = os.getcwd().split("/")[-1]

    timestamp_value = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if timestamp != "False" else None

    if timestamp == "False":
        cursor.execute('''UPDATE configs SET status = ?, result = ?, duration = ?, additional_info = ?
                          WHERE trace = ? AND frequency = ? AND ifetch_buffer_size = ? AND 
                          decode_buffer_size = ? AND dispatch_buffer_size = ? AND rob_size = ? AND directory = ?''',
                       (status, result, duration, additional_info, trace, config["Frequency"], config["iFetchBufferSize"], 
                        config["DecodeBufferSize"], config["DispatchBufferSize"], config["ROBSize"], directory))
    else:
        cursor.execute('''UPDATE configs SET status = ?, result = ?, duration = ?, timestamp = ?, additional_info = ?
                          WHERE trace = ? AND frequency = ? AND ifetch_buffer_size = ? AND 
                          decode_buffer_size = ? AND dispatch_buffer_size = ? AND rob_size = ? AND directory = ?''',
                       (status, result, duration, timestamp_value, additional_info, trace, config["Frequency"], 
                        config["iFetchBufferSize"], config["DecodeBufferSize"], config["DispatchBufferSize"], config["ROBSize"], directory))

    conn.commit()
    conn.close()

def fetch_additional_config_from_db(trace, config):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''SELECT lq_size, sq_size, fetch_width, decode_width, dispatch_width, execute_width, lq_width,
                      sq_width, retire_width, scheduler_size, branch_predictor, btb, dib_window_size, dib_sets,
                      dib_ways, l1i_sets, l1i_ways, l1i_rq_size, l1i_wq_size, l1i_pq_size, l1i_mshr_size, l1i_prefetcher,
                      l1d_sets, l1d_ways, l1d_rq_size, l1d_wq_size, l1d_pq_size, l1d_mshr_size, l1d_prefetcher 
                      FROM configs 
                      WHERE trace = ? AND frequency = ? AND ifetch_buffer_size = ? AND decode_buffer_size = ? AND 
                      dispatch_buffer_size = ? AND rob_size = ? AND directory = ?''',
                   (trace, config["Frequency"], config["iFetchBufferSize"], config["DecodeBufferSize"], 
                    config["DispatchBufferSize"], config["ROBSize"], os.getcwd().split("/")[-1]))

    result = cursor.fetchone()
    conn.close()

    if result:
        fields = ["lq_size", "sq_size", "fetch_width", "decode_width", "dispatch_width", "execute_width", "lq_width",
                  "sq_width", "retire_width", "scheduler_size", "branch_predictor", "btb", "dib_window_size", "dib_sets",
                  "dib_ways", "l1i_sets", "l1i_ways", "l1i_rq_size", "l1i_wq_size", "l1i_pq_size", "l1i_mshr_size", 
                  "l1i_prefetcher", "l1d_sets", "l1d_ways", "l1d_rq_size", "l1d_wq_size", "l1d_pq_size", "l1d_mshr_size", 
                  "l1d_prefetcher"]
        return dict(zip(fields, result))
    return None

def update_remote_api(trace, config, timestamp, status, result=None, duration=None, additional_info=None):
    additional_config = fetch_additional_config_from_db(trace, config)
    
    if additional_config is None:
        print("Configuration details not found in local database.")
        return

    data = {
        "trace": trace,
        "sim_instructions": 700000000,
        "frequency": config["Frequency"],
        "ifetch_buffer_size": config["iFetchBufferSize"],
        "decode_buffer_size": config["DecodeBufferSize"],
        "dispatch_buffer_size": config["DispatchBufferSize"],
        "rob_size": config["ROBSize"],
        "lq_size": additional_config["lq_size"],
        "sq_size": additional_config["sq_size"],
        "fetch_width": additional_config["fetch_width"],
        "decode_width": additional_config["decode_width"],
        "dispatch_width": additional_config["dispatch_width"],
        "execute_width": additional_config["execute_width"],
        "lq_width": additional_config["lq_width"],
        "sq_width": additional_config["sq_width"],
        "retire_width": additional_config["retire_width"],
        "scheduler_size": additional_config["scheduler_size"],
        "branch_predictor": additional_config["branch_predictor"],
        "btb": additional_config["btb"],
        "dib_window_size": additional_config["dib_window_size"],
        "dib_sets": additional_config["dib_sets"],
        "dib_ways": additional_config["dib_ways"],
        "l1i_sets": additional_config["l1i_sets"],
        "l1i_ways": additional_config["l1i_ways"],
        "l1i_rq_size": additional_config["l1i_rq_size"],
        "l1i_wq_size": additional_config["l1i_wq_size"],
        "l1i_pq_size": additional_config["l1i_pq_size"],
        "l1i_mshr_size": additional_config["l1i_mshr_size"],
        "l1i_prefetcher": additional_config["l1i_prefetcher"],
        "l1d_sets": additional_config["l1d_sets"],
        "l1d_ways": additional_config["l1d_ways"],  
        "l1d_rq_size": additional_config["l1d_rq_size"],
        "l1d_wq_size": additional_config["l1d_wq_size"],
        "l1d_pq_size": additional_config["l1d_pq_size"],
        "l1d_mshr_size": additional_config["l1d_mshr_size"],
        "l1d_prefetcher": additional_config["l1d_prefetcher"],
        "directory": os.getcwd().split("/")[-1],
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S') if timestamp != "False" else None,
        "status": status,
        "result": result,
        "duration": duration,
        "additional_info": additional_info,
    }

    method = 'POST' if status == "running" else 'PUT'
    response = requests.request(method, API_ENDPOINT, json=data)

    if response.status_code in [200, 201]:
        print(f"Successfully updated configuration on remote API with {method}.")
    else:
        print(f"Failed to update configuration on remote API. Status code: {response.status_code}, Response: {response.text}")

if __name__ == "__main__":
    trace = sys.argv[1]
    config = {
        "Frequency": int(sys.argv[2]),
        "iFetchBufferSize": int(sys.argv[3]),
        "DecodeBufferSize": int(sys.argv[4]),
        "DispatchBufferSize": int(sys.argv[5]),
        "ROBSize": int(sys.argv[6])
    }
    timestamp = sys.argv[7]
    status = sys.argv[8]
    result = sys.argv[9] if len(sys.argv) > 9 else None
    duration = sys.argv[10] if len(sys.argv) > 10 else None
    additional_info = sys.argv[11] if len(sys.argv) > 11 else None

    if len(sys.argv) < 8:
        print("Invalid number of arguments.")
    else:
        print("Updating configuration status in local database...")
        update_local_db(trace, config, timestamp, status, result, duration, additional_info)

        if UPDATE_API:
            print("Updating configuration status on remote API...")
            update_remote_api(trace, config, timestamp, status, result, duration, additional_info)
