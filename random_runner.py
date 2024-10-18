import random
import json
import subprocess
import sys
from datetime import datetime
import time
import math
import os
import re
import sqlite3

# Configuration parameters
SIM_INSTRUCTIONS = json.load(open("../config.json"))["SIM_INSTRUCTIONS"]
DB_FILE = json.load(open("../config.json"))["DB_FILE"]
TRACES_TO_RUN = json.load(open("../config.json"))["TRACES_TO_RUN"]
TRACES_OFFSET = json.load(open("../config.json"))["TRACES_OFFSET"]
TRACE_DIR = json.load(open("../config.json"))["TRACE_DIR"]
WALL_TIME = json.load(open("../config.json"))["WALL_TIME"]
MEM_SIZE_PER_JOB_MB = json.load(open("../config.json"))["MEM_SIZE_PER_JOB_MB"]

# SLURM template for running ChampSim as a batch job
SLURM_TEMPLATE = """#!/bin/bash
#SBATCH --job-name=champsim_{trace}_{iter}   # Job name
#SBATCH --ntasks=1                         # Run a single task
#SBATCH --time={dur}                    # Time limit hrs:min:sec
#SBATCH --output={output_location}  # Standard output and error log
#SBATCH --mem={mem}MB                      # Job memory request

module load GCCcore CMake git  # Load necessary modules
cd {repo_path}  # Navigate to the correct ChampSim repo

# Get time before running the program
start_time=$(date +%s)
python3 update_status.py {trace} {freq} {ifetch} {decode} {dispatch} {rob} True running

# Run ChampSim and check its exit status
./bin/run_champsim -w 0 --simulation-instructions {sim_instructions} {trace_fp} --json {json_output}
run_status=$?

end_time=$(date +%s)
duration_secs=$((end_time - start_time))
duration_mins=$(echo "scale=2; $duration_secs / 60" | bc)

# Determine if the run was successful based on the exit status
if [ $run_status -eq 0 ]; then
    result="Success"
else
    result="Failure"
fi

# Call update_status.py with the result
echo "Command: python3 update_status.py {trace} {freq} {ifetch} {decode} {dispatch} {rob} True completed $result $duration_mins"
python3 update_status.py {trace} {freq} {ifetch} {decode} {dispatch} {rob} False completed $result $duration_mins

# Remove the batch script
rm {repo_path}/batch/batch_script_{trace}.sh
"""

# Initialize the database which stores already run configurations
def initialize_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS configs (
                        trace TEXT NOT NULL,
                        sim_instructions INTEGER,
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
                        directory TEXT,
                        timestamp TEXT,
                        status TEXT,
                        result TEXT,
                        duration REAL,
                        additional_info TEXT,
                        PRIMARY KEY (trace, frequency, ifetch_buffer_size, decode_buffer_size, dispatch_buffer_size)
                    )''')
    conn.commit()
    conn.close()

# Decode the encoded configuration to human-readable format
def decode(act_encoded, mappers):
    act_decoded = {}
    parameter_keys = list(mappers["mappers"].keys())
    if isinstance(act_encoded, dict):
        for key in parameter_keys:
            act_decoded[key] = mappers["mappers"][key][str(act_encoded[key])]

    return act_decoded

# Save the configuration to the database
def save_config_to_db(trace, config, additional_info=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check if the configuration is already in the database
    cursor.execute('''SELECT COUNT(*) FROM configs WHERE trace = ? AND 
                      frequency = ? AND ifetch_buffer_size = ? AND decode_buffer_size = ? AND 
                      dispatch_buffer_size = ? AND rob_size = ?''', 
                   (trace, config["Frequency"], config["iFetchBufferSize"], config["DecodeBufferSize"], 
                    config["DispatchBufferSize"], config["ROBSize"]))
    count = cursor.fetchone()[0]

    if count == 0:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "pending"  # Start with "pending" status
        # Insert the configuration into the database
        cursor.execute('''INSERT INTO configs (trace, sim_instructions, frequency, ifetch_buffer_size, decode_buffer_size, 
                          dispatch_buffer_size, rob_size, lq_size, sq_size, fetch_width, decode_width, 
                          dispatch_width, execute_width, lq_width, sq_width, retire_width, scheduler_size, 
                          branch_predictor, btb, dib_window_size, dib_sets, dib_ways, l1i_sets, l1i_ways, 
                          l1i_rq_size, l1i_wq_size, l1i_pq_size, l1i_mshr_size, l1i_prefetcher, 
                          l1d_sets, l1d_ways, l1d_rq_size, l1d_wq_size, l1d_pq_size, l1d_mshr_size, 
                          l1d_prefetcher, directory, timestamp, status, result, duration, additional_info)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (trace, SIM_INSTRUCTIONS, config["Frequency"], config["iFetchBufferSize"], config["DecodeBufferSize"],
                        config["DispatchBufferSize"], config["ROBSize"], config["LQSize"], config["SQSize"],
                        config["FetchWidth"], config["DecodeWidth"], config["DispatchWidth"], config["ExecuteWidth"],
                        config["LQWidth"], config["SQWidth"], config["RetireWidth"], config["SchedulerSize"],
                        config["BranchPredictor"], config["BTB"], config["DIBWindowSize"], config["DIBSets"], 
                        config["DIBWays"], config["L1ISets"], config["L1IWays"], config["L1IRQSize"], config["L1IWQSize"], 
                        config["L1IPQSize"], config["L1IMSHRSize"], config["L1IPrefetcher"], config["L1DSets"], 
                        config["L1DWays"], config["L1DRQSize"], config["L1DWQSize"], config["L1DPQSize"], 
                        config["L1DMSHRSize"], config["L1DPrefetcher"], os.getcwd().split("/")[-1],
                        timestamp, status, None, None, additional_info))
        conn.commit()

    conn.close()
    return count == 0 

# Check if the configuration is already in the database
def check_config_in_db(config):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''SELECT COUNT(*) FROM configs WHERE
                      frequency = ? AND ifetch_buffer_size = ? AND decode_buffer_size = ? AND 
                      dispatch_buffer_size = ? AND rob_size = ?''', 
                   (config["Frequency"], config["iFetchBufferSize"], config["DecodeBufferSize"], 
                    config["DispatchBufferSize"], config["ROBSize"]))
    
    count = cursor.fetchone()[0]
    conn.close()

    if count == 0:
        return True
    else:
        return False

# Select a configuration for the architecture
def select_config():
    with open('mappers.json', 'r') as json_file:
        mappers = json.load(json_file)
        act_encoded = {}
        parameter_keys = list(mappers["mappers"].keys())
        found_good_value = False
        while not found_good_value: # Keep generating configurations until a new one is found
            # Generate random architecture configuration
            for key in parameter_keys:
                act_encoded[key] = random.randint(0, len(mappers["mappers"][key].keys()) - 1)
        
            found_good_value = check_config_in_db(act_encoded)

        # Configuration will be saved for each trace later
        print("\tFound a good configuration")
        act_decoded = decode(act_encoded, mappers)
        write_to_json(act_decoded, mappers)
        return act_encoded

# Write the configuration to a JSON file for ChampSim
def write_to_json(action, mappers):
    champsim_ctrl_file = "champsim_config.json"
    with open("starter_champsim_config.json", "r+") as JsonFile:
        data = json.load(JsonFile)
        for section, mappings in mappers["json_mappings"].items():
            for action_key, json_key in mappings.items():
                if section in data:
                    if isinstance(data[section], list): 
                        data[section][0][json_key] = action[action_key]
                    else:
                        data[section][json_key] = action[action_key]
        with open(champsim_ctrl_file, "w+") as JsonFile:
            json.dump(data, JsonFile, indent=4)

# Create a batch job for each trace
def create_batch_job(repo_path, trace, trace_fp, config):
    total_seconds = WALL_TIME * 3600
    hours = math.floor(total_seconds // 3600)
    minutes = math.floor((total_seconds % 3600) // 60)
    seconds = math.floor(total_seconds % 60)
    slurm_script = SLURM_TEMPLATE.format(
        trace=trace, 
        output_location=f"{repo_path}/output/logs_long_{trace}.log",
        iter=repo_path[-1],
        dur = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}",
        mem=MEM_SIZE_PER_JOB_MB,
        repo_path=repo_path, 
        json_output=f"{repo_path}/output/json_long_{trace}.json",
        sim_instructions=SIM_INSTRUCTIONS, 
        trace_fp=trace_fp,
        freq=config["Frequency"],
        ifetch=config["iFetchBufferSize"],
        decode=config["DecodeBufferSize"],
        dispatch=config["DispatchBufferSize"],
        rob=config["ROBSize"]
    )
    script_path = f"{repo_path}/batch/batch_script_{trace}.sh"
    with open(script_path, "w") as script_file:
        script_file.write(slurm_script)

# Indents all lines from the output of a subprocess (purely for formatting)
def run_command(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    
    if result.stdout:
        for line in result.stdout.splitlines():
            print(f"\t{line}")
    
    if result.stderr:
        for line in result.stderr.splitlines():
            print(f"\t{line}")
    
    return result

# Run the ChampSim program with the selected configuration
def setup_champsim(action_dict):
    binary_name = f"run_champsim"
    # Configure the program with the selected configuration
    print("\tConfiguring ChampSim with provided configuration")
    process = subprocess.Popen(
        ["./config.sh", "champsim_config.json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = process.communicate()
    if err.decode().strip():
        for line in err.decode().splitlines():
            print(f"\t{line}")
        sys.exit(1)
    # Display the output of the configuration process
    # if out.decode().strip():
    #     outstream = out.decode()
    #     for line in outstream.splitlines():
    #         print(f"\t{line}")
    # Compile ChampSim
    print("\tCompiling ChampSim")
    process = subprocess.Popen(
        ["make", "BINARY_NAME=" + binary_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = process.communicate()
    if "error" in err.decode().lower():
        for line in err.decode().splitlines():
            print(f"\t{line}")
        print(f"\t{action_dict}")
        sys.exit(1)
    # Display the output of the compilation process
    # if out.decode().strip():
    #     outstream = out.decode()
    #     for line in outstream.splitlines():
    #         print(f"\t{line}")
    print("\tDone configuring/making config")

# Extract the trace number from the filename (for sorting)
def extract_number_from_trace(filename):
    match = re.search(r'_(\d+)\.champsimtrace\.xz$', filename)
    return int(match.group(1)) if match else -1

def main():
    initialize_db()

    # Get the list of traces to run and sort them
    traces = os.listdir(TRACE_DIR)
    traces.sort(key=extract_number_from_trace)

    # Offset the traces to run
    traces = traces[TRACES_OFFSET:]

    # Select a configuration
    print("\tSelecting configuration...")
    action_dict = select_config()
    setup_champsim(action_dict)

    for (iter, trace) in enumerate(traces):
        if iter < TRACES_TO_RUN: # Limit the number of traces to run
            try:
                # Set up the batch job for each trace
                print("\t\tCreating batch job for trace:", trace)
                create_batch_job(os.getcwd(), trace, f"{TRACE_DIR}/{trace}", action_dict)
                save_config_to_db(trace, action_dict)
            except KeyboardInterrupt:
                sys.exit()
            except Exception as ex:
                print("\t\tERROR creating batch job for trace:", trace, "\n\t\t", ex)
                continue

if __name__ == "__main__":
    main()