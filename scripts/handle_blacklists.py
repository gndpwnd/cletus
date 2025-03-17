import os
import json
import urllib.parse


def is_blacklisted(link, directory='blacklists'):
    # Get all files in the directory that start with 'blklst_' and end with '.json'
    files = [f for f in os.listdir(directory) if f.startswith('blklst_') and f.endswith('.json')]
    
    # Process each file in the blacklist directory
    for file_name in files:
        file_path = os.path.join(directory, file_name)
        
        # Read the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        # Check if 'blacklisted_links' key exists and is not empty
        if 'blacklisted_links' in data and data['blacklisted_links']:
            # Check if the provided link starts with any of the blacklisted links
            for blacklisted_link in data['blacklisted_links']:
                if link.startswith(blacklisted_link):
                    return True
    
    # If no match is found
    return False

# Function to clean URLs according to the provided rules
def clean_url(url):
    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc
    path = parsed_url.path
    
    # Ensure the URL has the 'https://' prefix
    if not parsed_url.scheme:
        url = 'https://' + url
    
    # If path is empty or just '/', return domain with a '/'
    if not path or path == '/':
        return f"https://{domain}/"
    
    # Remove the trailing slash (if present) and split by '/'
    path_parts = path.strip('/').split('/')
    
    # If the link does not end with a '/', remove parts after the last '/'
    if path.endswith('/'):
        if len(path_parts) >= 2:
            return f"https://{domain}/{path_parts[0]}/{path_parts[1]}/"
        else:
            return f"https://{domain}/{path_parts[0]}/"
    else:
        # Truncate everything after the last directory if it does not end with a '/'
        return f"https://{domain}/{path_parts[0]}/"

# Function to process all JSON files in a directory
def clean_blacklists(directory):
    # Get all files in the directory that start with 'blklst_' and end with '.json'
    files = [f for f in os.listdir(directory) if f.startswith('blklst_') and f.endswith('.json')]
    
    # Process each file
    for file_name in files:
        file_path = os.path.join(directory, file_name)
        
        # Read the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        # Check if 'blacklisted_links' key exists in the JSON data
        if 'blacklisted_links' in data:
            # Clean the URLs in the 'blacklisted_links' list
            cleaned_links = [clean_url(link) for link in data['blacklisted_links']]
            
            # Ensure all links are unique by converting the list to a set and back to a list
            unique_links = list(set(cleaned_links))
            data['blacklisted_links'] = unique_links
        
        # Save the cleaned data back to the same file
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
        print(f"Processed and cleaned: {file_name}")

# Directory containing the blacklist JSON files
#directory = 'blacklists/'

# Call the function to process the files in the directory
#clean_blacklists(directory)