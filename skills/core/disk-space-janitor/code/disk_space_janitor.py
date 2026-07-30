import os
from datetime import timedelta, date

def clean_backups_directory(directory):
    """
    Cleans the specified directory by deleting all files that are older than 7 days.

    Parameters:
    directory (str): The path to the directory to be cleaned.

    Returns:
    int: The number of deleted files.
    """
    deleted_files = 0
    for root, dirs, files in os.walk(directory):
        if 'tmp' in root or 'octopus-backups' in root:
            # Create a datetime object and set it 7 days ago (as of today)
            seven_days_ago = date.today() - timedelta(days=7)

            for file_name in files:
                file_path = os.path.join(root, file_name)
                if os.path.isfile(file_path):
                    mtime = os.path.getmtime(file_path)
                    # Check if the last modification time is older than 7 days
                    if seven_days_ago > date.fromtimestamp(mtime):
                        try:
                            os.remove(file_path)  # Remove the file
                            deleted_files += 1
                        except Exception as e:
                            print(f"Failed to delete {file_name}: {e}")
    return deleted_files

# Example usage:
clean_backups_directory("/path/to/your/directory")  # Replace with your directory path
