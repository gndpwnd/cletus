import os
import re
import datetime

# Directory where markdown files are stored
POSTS_DIR = "content/posts/"

# Regex pattern to match filenames in the format *_YYYY_MM_DD.md
FILENAME_PATTERN = re.compile(r".*_(\d{4})_(\d{2})_(\d{2})\.md")

# Define how many days old a file should be before deletion
DAYS_THRESHOLD = 10

def history_check(search_string):
    """Searches for a string in all markdown files in POSTS_DIR.
    
    Returns True if found, otherwise False.
    """
    for filename in os.listdir(POSTS_DIR):
        if filename.endswith(".md"):  # Ensure we're only checking markdown files
            file_path = os.path.join(POSTS_DIR, filename)
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                if search_string in content:
                    return True  # String found, return immediately

    return False  # String not found in any file


def clean_history():
    """Deletes markdown files older than 10 days based on their filename date."""
    today = datetime.date.today()
    
    for filename in os.listdir(POSTS_DIR):
        match = FILENAME_PATTERN.match(filename)
        if match:
            year, month, day = map(int, match.groups())
            file_date = datetime.date(year, month, day)
            age_days = (today - file_date).days
            
            if age_days > DAYS_THRESHOLD:
                file_path = os.path.join(POSTS_DIR, filename)
                os.remove(file_path)
                print(f"Deleted: {filename} (Age: {age_days} days)")

if __name__ == "__main__":
    delete_old_posts()