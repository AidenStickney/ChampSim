import sqlite3
import json
import sys
import os
from datetime import datetime

DB_FILE = json.load(open("../config.json"))["DB_FILE"]

def update_config_status(trace, config, timestamp, status, result=None, duration=None, additional_info=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if (timestamp == "False"):
        cursor.execute('''UPDATE configs SET status = ?, result = ?, duration = ?, additional_info = ?
                        WHERE trace = ? AND frequency = ? AND ifetch_buffer_size = ? AND 
                        decode_buffer_size = ? AND dispatch_buffer_size = ? AND rob_size = ? AND directory = ?''',
                    (status, result, duration, additional_info, trace, config["Frequency"], config["iFetchBufferSize"], 
                        config["DecodeBufferSize"], config["DispatchBufferSize"], config["ROBSize"], os.getcwd().split("/")[-1]))
    else:
        local_time = datetime.now()
        cursor.execute('''UPDATE configs SET status = ?, result = ?, duration = ?, timestamp = ?, additional_info = ?
                     WHERE trace = ? AND frequency = ? AND ifetch_buffer_size = ? AND 
                     decode_buffer_size = ? AND dispatch_buffer_size = ? AND rob_size = ? AND directory = ?''',
                   (status, result, duration, local_time.strftime('%Y-%m-%d %H:%M:%S'), additional_info, trace, config["Frequency"], config["iFetchBufferSize"], 
                    config["DecodeBufferSize"], config["DispatchBufferSize"], config["ROBSize"], os.getcwd().split("/")[-1]))
    conn.commit()
    conn.close()

# Pass as arguments to command line
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

    if len(sys.argv) < 7:
        print("Invalid number of arguments.")

    print("Updating configuration status...")
    update_config_status(trace, config, timestamp, status, result, duration, additional_info)