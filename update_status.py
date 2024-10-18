import sqlite3
import json
import sys
import os

DB_FILE = json.load(open("../config.json"))["DB_FILE"]

def update_config_status(trace, config, status, result=None, duration=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''UPDATE configs SET status = ?, result = ?, duration = ?
                      WHERE trace = ? AND frequency = ? AND ifetch_buffer_size = ? AND 
                      decode_buffer_size = ? AND dispatch_buffer_size = ? AND rob_size = ? AND directory = ?''',
                   (status, result, duration, trace, config["Frequency"], config["iFetchBufferSize"], 
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
    status = sys.argv[7]
    result = sys.argv[8] if len(sys.argv) > 8 else None
    duration = sys.argv[9] if len(sys.argv) > 9 else None

    if len(sys.argv) < 7:
        print("Invalid number of arguments.")

    update_config_status(trace, config, status, result, duration)