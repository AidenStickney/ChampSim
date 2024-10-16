import os
import shutil
import sqlite3

output_folder = 'output'
DB_FILE = "../champsim_configs.db"

folders_to_delete = []
files_to_delete = []

if os.path.exists(output_folder):
    for item in os.listdir(output_folder):
        item_path = os.path.join(output_folder, item)
        if os.path.isdir(item_path):
            folders_to_delete.append(item_path)

current_directory = os.getcwd()
for file_name in os.listdir(current_directory):
    if file_name.startswith('output_') and file_name.endswith('.log'):
        file_path = os.path.join(current_directory, file_name)
        files_to_delete.append(file_path)

if len(folders_to_delete) > 0:
  print("The following folders will be deleted:")
  for folder in folders_to_delete:
      print(f" - {folder}")
else:
  print("No folders to delete.")

if len(files_to_delete) > 0:
  print("\nThe following files will be deleted:")
  for file in files_to_delete:
      print(f" - {file}")
else:
  print("No files to delete.")

confirm = 'no'

if len(folders_to_delete) == 0 and len(files_to_delete) == 0:
  confirm = input("\nNo folders or files to delete. Do you want to proceed with database cleaning? (yes/no): ").strip().lower()
else:
  confirm = input("\nDo you want to proceed with deletion? (yes/no): ").strip().lower()

if confirm == 'yes':
    for folder in folders_to_delete:
        shutil.rmtree(folder)
        print(f"Deleted folder: {folder}")
    
    for file in files_to_delete:
        os.remove(file)
        print(f"Deleted file: {file}")

    if len(folders_to_delete) > 0 or len(files_to_delete) > 0:
        print("\nDeletion completed successfully.")

    if os.path.exists(DB_FILE):
        try:
            def clean_database():
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()

                cursor.execute("DELETE FROM configs")
                conn.commit()

                print("Database cleaned successfully.")
                conn.close()

            clean_database()

        except Exception as e:
            print(f"An error occurred while cleaning the database: {e}")

else:
    print("Deletion aborted.")
