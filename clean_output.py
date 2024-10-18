import os
import shutil
import json
import sys

output_folder = 'output'
batch_folder = 'batch'
binary_folder = 'bin'
DB_FILE = json.load(open("../config.json"))["DB_FILE"]

files_to_delete = []

if os.path.exists(output_folder):
    for item in os.listdir(output_folder):
        if os.path.isfile(item):
            item_path = os.path.join(output_folder, item)
            files_to_delete.append(item_path)

if os.path.exists(batch_folder):
    for item in os.listdir(batch_folder):
        if os.path.isfile(item):
            item_path = os.path.join(batch_folder, item)
            files_to_delete.append(item_path)

if os.path.exists(binary_folder):
    for item in os.listdir(binary_folder):
        if os.path.isfile(item):
            item_path = os.path.join(binary_folder, item)
            files_to_delete.append(item_path)

current_directory = os.getcwd()
for file_name in os.listdir(current_directory):
    if file_name.startswith('output_') and file_name.endswith('.log'):
        if os.path.isfile(file_name):
            file_path = os.path.join(current_directory, file_name)
            files_to_delete.append(file_path)
    if file_name.startswith('run_champsim_') and file_name.endswith('.sh'):
        if os.path.isfile(file_name):
            file_path = os.path.join(current_directory, file_name)
            files_to_delete.append(file_path)

if len(files_to_delete) > 0:
  print("\n\tThe following files will be deleted:")
  for file in files_to_delete:
      print(f"\t - {file}")
else:
  print("\tNo files to delete.")
  sys.exit()
  

confirm = 'no'

confirm = input("\n\tDo you want to proceed with deletion? (yes/no): ").strip().lower()

if confirm == 'yes':
    for file in files_to_delete:
        os.remove(file)
        print(f"\tDeleted file: {file}")

    if len(files_to_delete) > 0:
        print("\n\tDeletion completed successfully.")

else:
    print("\tDeletion aborted.")
