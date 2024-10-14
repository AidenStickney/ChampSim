import random
import json
import subprocess
import sys
from datetime import datetime
import time
import os
import sqlite3

SIM_INSTRUCTIONS = 1000000
DB_FILE = "ChampSim/champsim_configs.db"
TRACE_DIR = "traces"

# Initialize the database which stores already run configurations
def initialize_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS configs (
                        trace TEXT NOT NULL,
                        frequency INTEGER,
                        ifetch_buffer_size INTEGER,
                        decode_buffer_size INTEGER,
                        dispatch_buffer_size INTEGER,
                        rob_size INTEGER,
                        lq_size INTEGER,
                        sq_size INTEGER,
                        fetch_width INTEGER,
                        decode_width INTEGER,
                        dispatch_width INTEGER,
                        execute_width INTEGER,
                        lq_width INTEGER,
                        sq_width INTEGER,
                        retire_width INTEGER,
                        scheduler_size INTEGER,
                        branch_predictor TEXT,
                        btb TEXT,
                        dib_window_size INTEGER,
                        dib_sets INTEGER,
                        dib_ways INTEGER,
                        l1i_sets INTEGER,
                        l1i_ways INTEGER,
                        l1i_rq_size INTEGER,
                        l1i_wq_size INTEGER,
                        l1i_pq_size INTEGER,
                        l1i_mshr_size INTEGER,
                        l1i_prefetcher TEXT,
                        l1d_sets INTEGER,
                        l1d_ways INTEGER,
                        l1d_rq_size INTEGER,
                        l1d_wq_size INTEGER,
                        l1d_pq_size INTEGER,
                        l1d_mshr_size INTEGER,
                        l1d_prefetcher TEXT,
                        timestamp TEXT,
                        status TEXT,
                        result TEXT,
                        pid INTEGER,
                        duration REAL,
                        additional_info TEXT,
                        PRIMARY KEY (trace, frequency, ifetch_buffer_size, decode_buffer_size, dispatch_buffer_size)
                    )''')
    conn.commit()
    conn.close()

# Decode the encoded configuration to human-readable format
def decode(act_encoded, mappers):
    act_decoded = {}
    if isinstance(act_encoded, dict):
        act_decoded["Frequency"] = mappers["frequency_mapper"][str(act_encoded["Frequency"])]
        act_decoded["iFetchBufferSize"] = mappers["ifetch_buffer_size_mapper"][
            str(act_encoded["iFetchBufferSize"])
        ]
        act_decoded["DecodeBufferSize"] = mappers["decode_buffer_size_mapper"][
            str(act_encoded["DecodeBufferSize"])
        ]
        act_decoded["DispatchBufferSize"] = mappers["dispatch_buffer_size_mapper"][
            str(act_encoded["DispatchBufferSize"])
        ]
        act_decoded["ROBSize"] = mappers["rob_size_mapper"][str(act_encoded["ROBSize"])]
        act_decoded["LQSize"] = mappers["lq_size_mapper"][str(act_encoded["LQSize"])]
        act_decoded["SQSize"] = mappers["sq_size_mapper"][str(act_encoded["SQSize"])]
        act_decoded["FetchWidth"] = mappers["fetch_width_mapper"][str(act_encoded["FetchWidth"])]
        act_decoded["DecodeWidth"] = mappers["decode_width_mapper"][str(act_encoded["DecodeWidth"])]
        act_decoded["DispatchWidth"] = mappers["dispatch_width_mapper"][
            str(act_encoded["DispatchWidth"])
        ]
        act_decoded["ExecuteWidth"] = mappers["execute_width_mapper"][str(act_encoded["ExecuteWidth"])]
        act_decoded["LQWidth"] = mappers["lq_width_mapper"][str(act_encoded["LQWidth"])]
        act_decoded["SQWidth"] = mappers["sq_width_mapper"][str(act_encoded["SQWidth"])]
        act_decoded["RetireWidth"] = mappers["retire_width_mapper"][str(act_encoded["RetireWidth"])]
        act_decoded["SchedulerSize"] = mappers["scheduler_size_mapper"][
            str(act_encoded["SchedulerSize"])
        ]
        act_decoded["BranchPredictor"] = mappers["branch_predictor_mapper"][
            str(act_encoded["BranchPredictor"])
        ]
        act_decoded["BTB"] = mappers["btb_mapper"][str(act_encoded["BTB"])]

        act_decoded["DIBWindowSize"] = mappers["window_size_mapper"][str(act_encoded["DIBWindowSize"])]
        act_decoded["DIBSets"] = mappers["dib_sets_mapper"][str(act_encoded["DIBSets"])]
        act_decoded["DIBWays"] = mappers["dib_ways_mapper"][str(act_encoded["DIBWays"])]

        act_decoded["L1ISets"] = mappers["l1i_sets_mapper"][str(act_encoded["L1ISets"])]
        act_decoded["L1IWays"] = mappers["l1i_ways_mapper"][str(act_encoded["L1IWays"])]
        act_decoded["L1IRQSize"] = mappers["l1i_rq_size_mapper"][str(act_encoded["L1IRQSize"])]
        act_decoded["L1IWQSize"] = mappers["l1i_wq_size_mapper"][str(act_encoded["L1IWQSize"])]
        act_decoded["L1IPQSize"] = mappers["l1i_pq_size_mapper"][str(act_encoded["L1IPQSize"])]
        act_decoded["L1IMSHRSize"] = mappers["l1i_mshr_size_mapper"][str(act_encoded["L1IMSHRSize"])]
        act_decoded["L1IPrefetcher"] = mappers["l1i_prefetcher_mapper"][
            str(act_encoded["L1IPrefetcher"])
        ]

        act_decoded["L1DSets"] = mappers["l1d_sets_mapper"][str(act_encoded["L1DSets"])]
        act_decoded["L1DWays"] = mappers["l1d_ways_mapper"][str(act_encoded["L1DWays"])]
        act_decoded["L1DRQSize"] = mappers["l1d_rq_size_mapper"][str(act_encoded["L1DRQSize"])]
        act_decoded["L1DWQSize"] = mappers["l1d_wq_size_mapper"][str(act_encoded["L1DWQSize"])]
        act_decoded["L1DPQSize"] = mappers["l1d_pq_size_mapper"][str(act_encoded["L1DPQSize"])]
        act_decoded["L1DMSHRSize"] = mappers["l1d_mshr_size_mapper"][str(act_encoded["L1DMSHRSize"])]
        act_decoded["L1DPrefetcher"] = mappers["l1d_prefetcher_mapper"][
            str(act_encoded["L1DPrefetcher"])
        ]

    return act_decoded

# Save the configuration to the database
def save_config_to_db(trace, config, additional_info=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "pending"  # Start with "pending" status

    cursor.execute('''SELECT COUNT(*) FROM configs WHERE trace = ? AND 
                      frequency = ? AND ifetch_buffer_size = ? AND decode_buffer_size = ? AND 
                      dispatch_buffer_size = ? AND rob_size = ?''', 
                   (trace, config["Frequency"], config["iFetchBufferSize"], config["DecodeBufferSize"], 
                    config["DispatchBufferSize"], config["ROBSize"]))
    
    count = cursor.fetchone()[0]

    if count == 0:
        # Insert a new configuration with detailed parameters, timestamp, and status
        cursor.execute('''INSERT INTO configs (trace, frequency, ifetch_buffer_size, decode_buffer_size, 
                          dispatch_buffer_size, rob_size, lq_size, sq_size, fetch_width, decode_width, 
                          dispatch_width, execute_width, lq_width, sq_width, retire_width, scheduler_size, 
                          branch_predictor, btb, dib_window_size, dib_sets, dib_ways, l1i_sets, l1i_ways, 
                          l1i_rq_size, l1i_wq_size, l1i_pq_size, l1i_mshr_size, l1i_prefetcher, 
                          l1d_sets, l1d_ways, l1d_rq_size, l1d_wq_size, l1d_pq_size, l1d_mshr_size, 
                          l1d_prefetcher, timestamp, status, result, pid, duration, additional_info)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (trace, config["Frequency"], config["iFetchBufferSize"], config["DecodeBufferSize"],
                        config["DispatchBufferSize"], config["ROBSize"], config["LQSize"], config["SQSize"],
                        config["FetchWidth"], config["DecodeWidth"], config["DispatchWidth"], config["ExecuteWidth"],
                        config["LQWidth"], config["SQWidth"], config["RetireWidth"], config["SchedulerSize"],
                        config["BranchPredictor"], config["BTB"], config["DIBWindowSize"], config["DIBSets"], 
                        config["DIBWays"], config["L1ISets"], config["L1IWays"], config["L1IRQSize"], config["L1IWQSize"], 
                        config["L1IPQSize"], config["L1IMSHRSize"], config["L1IPrefetcher"], config["L1DSets"], 
                        config["L1DWays"], config["L1DRQSize"], config["L1DWQSize"], config["L1DPQSize"], 
                        config["L1DMSHRSize"], config["L1DPrefetcher"], timestamp, status, None, None, None, additional_info))
        conn.commit()

    conn.close()
    return count == 0 

# Update the status of the configuration in the database
def update_config_status(trace, config, status, result=None, pid=None, duration=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''UPDATE configs SET status = ?, result = ?, pid = ?, duration = ?
                      WHERE trace = ? AND frequency = ? AND ifetch_buffer_size = ? AND 
                      decode_buffer_size = ? AND dispatch_buffer_size = ? AND rob_size = ?''',
                   (status, result, pid, duration, trace, config["Frequency"], config["iFetchBufferSize"], 
                    config["DecodeBufferSize"], config["DispatchBufferSize"], config["ROBSize"]))
    
    conn.commit()
    conn.close()

# Select a configuration for the architecture
def select_config(trace):
    with open('ChampSim/mappers.json', 'r') as json_file:
        mappers = json.load(json_file)
        act_encoded = {}

        found_good_value = False
        while not found_good_value:
            # Generate random architecture configuration
            act_encoded["Frequency"] = random.randint(0, len(mappers["frequency_mapper"].keys()) - 1)
            act_encoded["iFetchBufferSize"] = random.randint(0, len(mappers["ifetch_buffer_size_mapper"].keys()) - 1)
            act_encoded["DecodeBufferSize"] = random.randint(0, len(mappers["decode_buffer_size_mapper"].keys()) - 1)
            act_encoded["DispatchBufferSize"] = random.randint(0, len(mappers["dispatch_buffer_size_mapper"].keys()) - 1)
            act_encoded["ROBSize"] = random.randint(0, len(mappers["rob_size_mapper"].keys()) - 1)
            act_encoded["LQSize"] = random.randint(0, len(mappers["lq_size_mapper"].keys()) - 1)
            act_encoded["SQSize"] = random.randint(0, len(mappers["sq_size_mapper"].keys()) - 1)
            act_encoded["FetchWidth"] = random.randint(0, len(mappers["fetch_width_mapper"].keys()) - 1)
            act_encoded["DecodeWidth"] = random.randint(0, len(mappers["decode_width_mapper"].keys()) - 1)
            act_encoded["DispatchWidth"] = random.randint(0, len(mappers["dispatch_width_mapper"].keys()) - 1)
            act_encoded["ExecuteWidth"] = random.randint(0, len(mappers["execute_width_mapper"].keys()) - 1)
            act_encoded["LQWidth"] = random.randint(0, len(mappers["lq_width_mapper"].keys()) - 1)
            act_encoded["SQWidth"] = random.randint(0, len(mappers["sq_width_mapper"].keys()) - 1)
            act_encoded["RetireWidth"] = random.randint(0, len(mappers["retire_width_mapper"].keys()) - 1)
            act_encoded["SchedulerSize"] = random.randint(0, len(mappers["scheduler_size_mapper"].keys()) - 1)
            act_encoded["BranchPredictor"] = random.randint(0, len(mappers["branch_predictor_mapper"].keys()) - 1)
            act_encoded["BTB"] = random.randint(0, len(mappers["btb_mapper"].keys()) - 1)
            
            act_encoded["DIBWindowSize"] = random.randint(0, len(mappers["window_size_mapper"].keys()) - 1)
            act_encoded["DIBSets"] = random.randint(0, len(mappers["dib_sets_mapper"].keys()) - 1)
            act_encoded["DIBWays"] = random.randint(0, len(mappers["dib_ways_mapper"].keys()) - 1)
            
            act_encoded["L1ISets"] = random.randint(0, len(mappers["l1i_sets_mapper"].keys()) - 1)
            act_encoded["L1IWays"] = random.randint(0, len(mappers["l1i_ways_mapper"].keys()) - 1)
            act_encoded["L1IRQSize"] = random.randint(0, len(mappers["l1i_rq_size_mapper"].keys()) - 1)
            act_encoded["L1IWQSize"] = random.randint(0, len(mappers["l1i_wq_size_mapper"].keys()) - 1)
            act_encoded["L1IPQSize"] = random.randint(0, len(mappers["l1i_pq_size_mapper"].keys()) - 1)
            act_encoded["L1IMSHRSize"] = random.randint(0, len(mappers["l1i_mshr_size_mapper"].keys()) - 1)
            act_encoded["L1IPrefetcher"] = random.randint(0, len(mappers["l1i_prefetcher_mapper"].keys()) - 1)
            
            act_encoded["L1DSets"] = random.randint(0, len(mappers["l1d_sets_mapper"].keys()) - 1)
            act_encoded["L1DWays"] = random.randint(0, len(mappers["l1d_ways_mapper"].keys()) - 1)
            act_encoded["L1DRQSize"] = random.randint(0, len(mappers["l1d_rq_size_mapper"].keys()) - 1)
            act_encoded["L1DWQSize"] = random.randint(0, len(mappers["l1d_wq_size_mapper"].keys()) - 1)
            act_encoded["L1DPQSize"] = random.randint(0, len(mappers["l1d_pq_size_mapper"].keys()) - 1)
            act_encoded["L1DMSHRSize"] = random.randint(0, len(mappers["l1d_mshr_size_mapper"].keys()) - 1)
            act_encoded["L1DPrefetcher"] = random.randint(0, len(mappers["l1d_prefetcher_mapper"].keys()) - 1)
        
            additional_info = ""

            # Saves configuration with non-decoded values
            found_good_value = save_config_to_db(trace, act_encoded, additional_info)

        print("Found a good configuration")
        act_decoded = decode(act_encoded, mappers)
        write_to_json(act_decoded, trace)
        return act_encoded

# Write the configuration to a JSON file for ChampSim
def write_to_json(action, trace):
    champsim_ctrl_file = "champsim_config_" + trace + "_" + str(os.getpid()) + ".json"
    with open("ChampSim/starter_champsim_config.json", "r+") as JsonFile:
        data = json.load(JsonFile)
        data["ooo_cpu"][0]["frequency"] = action["Frequency"]
        data["ooo_cpu"][0]["ifetch_buffer_size"] = action["iFetchBufferSize"]
        data["ooo_cpu"][0]["decode_buffer_size"] = action["DecodeBufferSize"]
        data["ooo_cpu"][0]["dispatch_buffer_size"] = action["DispatchBufferSize"]
        data["ooo_cpu"][0]["rob_size"] = action["ROBSize"]
        data["ooo_cpu"][0]["lq_size"] = action["LQSize"]
        data["ooo_cpu"][0]["sq_size"] = action["SQSize"]
        data["ooo_cpu"][0]["fetch_width"] = action["FetchWidth"]
        data["ooo_cpu"][0]["decode_width"] = action["DecodeWidth"]
        data["ooo_cpu"][0]["dispatch_width"] = action["DispatchWidth"]
        data["ooo_cpu"][0]["execute_width"] = action["ExecuteWidth"]
        data["ooo_cpu"][0]["lq_width"] = action["LQWidth"]
        data["ooo_cpu"][0]["sq_width"] = action["SQWidth"]
        data["ooo_cpu"][0]["retire_width"] = action["RetireWidth"]
        data["ooo_cpu"][0]["scheduler_size"] = action["SchedulerSize"]
        data["ooo_cpu"][0]["branch_predictor"] = action["BranchPredictor"]
        data["ooo_cpu"][0]["btb"] = action["BTB"]

        data["DIB"]["window_size"] = action["DIBWindowSize"]
        data["DIB"]["sets"] = action["DIBSets"]
        data["DIB"]["ways"] = action["DIBWays"]

        data["L1I"]["sets"] = action["L1ISets"]
        data["L1I"]["ways"] = action["L1IWays"]
        data["L1I"]["rq_size"] = action["L1IRQSize"]
        data["L1I"]["wq_size"] = action["L1IWQSize"]
        data["L1I"]["pq_size"] = action["L1IPQSize"]
        data["L1I"]["mshr_size"] = action["L1IMSHRSize"]
        data["L1I"]["prefetcher"] = action["L1IPrefetcher"]

        data["L1D"]["sets"] = action["L1DSets"]
        data["L1D"]["ways"] = action["L1DWays"]
        data["L1D"]["rq_size"] = action["L1DRQSize"]
        data["L1D"]["wq_size"] = action["L1DWQSize"]
        data["L1D"]["pq_size"] = action["L1DPQSize"]
        data["L1D"]["mshr_size"] = action["L1DMSHRSize"]
        data["L1D"]["prefetcher"] = action["L1DPrefetcher"]
        with open("ChampSim/champsim_configs/" + champsim_ctrl_file, "w+") as JsonFile:
            json.dump(data, JsonFile, indent=4)

# Run the ChampSim program with the selected configuration
def run_program(iter, action_dict, trace):
    def current_datetime_to_numeric_representation():
        reference_datetime = datetime(2022, 1, 1)
        current_datetime = datetime.now()
        total_seconds = (current_datetime - reference_datetime).total_seconds()
        return total_seconds

    name = trace + "_" + str(os.getpid())
    binary_name = f"champsim_{trace}_" + str(os.getpid())
    trace_fp = f"traces/{trace}"
    # Configure the program with the selected configuration
    print("Configuring ChampSim with provided configuration")
    process = subprocess.Popen(
        ["./config.sh", "champsim_configs/champsim_config_" + trace + "_" + str(os.getpid()) + ".json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=(os.getcwd() + "/ChampSim")
    )
    out, err = process.communicate()
    if err.decode() == "":
        outstream = out.decode()
    else:
        print(err.decode())
        sys.exit()
    # Compile ChampSim
    print("Compiling ChampSim")
    process = subprocess.Popen(
        ["make", "BINARY_NAME=" + binary_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=(os.getcwd() + "/ChampSim")
    )
    out, err = process.communicate()
    if "error" not in err.decode():
        outstream = out.decode()
    else:
        print(err.decode())
        print(action_dict)
        sys.exit()
    print("Done configuring/making config")
    output_json_dir = f"output/json_long_{trace}_" + str(os.getpid())
    output_logs_dir = f"output/logs_long_{trace}_" + str(os.getpid())
    if not os.path.exists("ChampSim/" + output_json_dir):
        os.makedirs("ChampSim/" + output_json_dir)
    if not os.path.exists("ChampSim/" + output_logs_dir):
        os.makedirs("ChampSim/" + output_logs_dir)
    start_time = time.time()
    # Run the program with the selected configuration
    print("Running ChampSim with provided configuration and trace")
    update_config_status(trace, action_dict, "running", pid=os.getpid())
    process = subprocess.Popen(
        [
            "./bin/" + binary_name,
            "-w",
            "0",
            "--simulation-instructions",
            str(SIM_INSTRUCTIONS),
            trace_fp,
            "--json",
            f"{output_json_dir}/{name}.json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=(os.getcwd() + "/ChampSim")
    )
    out, err = process.communicate()
    print("Done running program, time to run:", (time.time() - start_time) / 60)
    update_config_status(trace, action_dict, "completed", result="Success", pid=os.getpid(), duration=(time.time() - start_time) / 60)
    if err.decode() == "":
        outstream = out.decode()
    else:
        update_config_status(trace, action_dict, "error", result=err.decode())
        print(err.decode())
        print(print(action_dict))
    if len(outstream) < 100:
        print(outstream)
    # Store the output to a text and JSON files
    txt_file_path = f"ChampSim/{output_logs_dir}/{name}.txt"
    with open(txt_file_path, "w+") as txt_file:
        txt_file.write(outstream)

    print("Done storing everything")

# TODO: Get traces from specified directory
traces = [
    "481.wrf-1170B.champsimtrace.xz"
]

def main():
    random.shuffle(traces)
    initialize_db()

    for trace in traces:
        for i in range(1):
            try:
                print("Trace:", trace)
                print("Selecting configuration...")
                action_dict = select_config(trace)
                run_program(iter, action_dict, trace)
            except KeyboardInterrupt:
                sys.exit()
            except Exception as ex:
                print("ERROR:", ex)
                continue

if __name__ == "__main__":
    main()