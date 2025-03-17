import requests
import random
import json
import re
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from links_dicts import link_dictionaries  # Importing link dictionaries from links_dict.py
from gen_md import generate_markdown_from_json
from handle_blacklists import is_blacklisted, clean_blacklists
from history_handle import history_check, clean_history


# Get the MORNING_RUN environment variable
# export MORNING_RUN=$( [ $(date +%H) -lt 12 ] && echo "true" || echo "false" )
morning_run = os.getenv("MORNING_RUN", "false").lower() == "true"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36"
]

def fetch_page(url):
    # Pick a random header from the list
    user_agent = random.choice(USER_AGENTS)
    
    try:
        # Send the request with randomly chosen headers to simulate a real browser
        response = requests.get(url, headers={'User-Agent': user_agent}, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        
        # Check if the response has any content
        if not response.text.strip():  # strip() removes any leading/trailing whitespace
            print(f"No content found on {url} (skipping...)")
            return None
        
        return response.text  # Return the HTML content if it has content

    except requests.exceptions.Timeout:
        print(f"Timeout: The request to {url} took too long (skipping...)")
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            print(f"401 Client Error: Forbidden for URL: {url} (skipping...)")
        else:
            print(f"HTTP Error {response.status_code} for URL: {url}")  # Print the actual HTTP error code
    except requests.exceptions.RequestException as e:
        # Catch any other requests-related exceptions
        print(f"Request Exception for URL {url}: {str(e)} (skipping...)")
    except Exception as e:
        # Catch all other errors to avoid script crashing
        print(f"An unexpected error occurred for URL {url}: {str(e)} (skipping...)")
    
    return None  # Return None if there's an error or timeout

def save_html(html, website):
    # Ensure the tmp_html directory exists
    os.makedirs("tmp_html", exist_ok=True)
    
    # Save HTML as <website>_tmp.html inside tmp_html/
    filepath = os.path.join("tmp_html", f"{website}_tmp.html")
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(html)

def clean_text(text):
    # This function can be customized to clean text if necessary
    return text.strip()

def extract_hyperlinks(filename, base_url, links, blacklists_dir):
    with open(filename, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")
    
    links_data = {}

    for a_tag in soup.find_all("a", href=True):
        text = clean_text(a_tag.get_text(strip=True))
        href = a_tag["href"]
        
        if href == base_url:  # reject the website itself without blacklisting
            continue

        # Check if the link matches any of the pre-defined websites
        for name, base_url in links.items():
            if href.startswith(base_url) or href.startswith("/"):
                if href.startswith("/"):  # Handle relative URLs
                    href = base_url.rstrip("/") + href

                # Reject URLs with double slashes after https://
                if re.search(r"https://[^/]+//", href):
                    continue  # Skip this link
                
                # Only store links with at least 5 words in text
                if len(text.split()) >= 5:
                    if name not in links_data:
                        links_data[name] = []  # Initialize list if not present
                    
                    # Ensure no duplicate headlines or links
                    if any(entry["headline"] == text or entry["link"] == href for entry in links_data[name]):
                        continue  # Skip if duplicate
                    
                    # Check if the link is blacklisted
                    if is_blacklisted(href, blacklists_dir):  # Check if the link is in the blacklist
                        continue  # Skip blacklisted links

                    if history_check(href) or history_check(text): # check if link exists in history (older markdown files)
                        continue

                    # Add the link
                    links_data[name].append({
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "headline": text,
                        "link": href
                    })
                break  # Move to the next link once a match is found
    
    return links_data

def load_existing_links(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    return {"daily_links": {}, "history_links": {}}

def update_history_links(existing_links, current_date):
    history_links = existing_links.get("history_links", {})
    
    # Remove links older than 4 weeks
    cutoff_date = datetime.now() - timedelta(weeks=4)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")
    
    for website, links in history_links.items():
        history_links[website] = [link for link in links if link["date"] >= cutoff_date_str]

    return history_links

def save_links(links_data, category_name):
    # Load existing data to append to it
    filename = f'tmp_json/links_{category_name}.json'
    existing_links = load_existing_links(filename)
    
    # Append new daily links to existing daily links
    for website, new_links in links_data.items():
        if website not in existing_links["daily_links"]:
            existing_links["daily_links"][website] = []  # Initialize list if not already there
        existing_links["daily_links"][website].extend(new_links)  # Append the new links

    # Move any non-today links to history_links
    history_links = update_history_links(existing_links, datetime.now().strftime("%Y-%m-%d"))
    
    # Append non-today links to history_links
    for website, links in links_data.items():
        for link in links:
            if link["date"] != datetime.now().strftime("%Y-%m-%d"):
                if website not in history_links:
                    history_links[website] = []
                history_links[website].append(link)
    
    # Save both sections (daily_links and history_links) to the JSON file
    existing_links["history_links"] = history_links

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(existing_links, file, indent=4)

skipped_sources = []

def main():

    if morning_run:
        print("Running in the Morning...")
    else:
        print("Running in the Evening...")

    print("Cleaning blacklists...")
    clean_blacklists
    print("Blacklist cleaned...")

    print("Cleaning old history...")
    clean_history
    print("Old history cleaned...")

    os.makedirs('tmp_json', exist_ok=True)
    # Loop through the link dictionaries imported from links_dict.py
    for category_name, links in link_dictionaries.items():
        print(f"Processing links for category: {category_name}")
        
        for website, base_url in links.items():
            print(f"Fetching page: {base_url}")
            
            # Fetch HTML content for each website
            html = fetch_page(base_url)
            if html == None:
                skipped_sources.append(base_url)
                continue
            save_html(html, website)  # Save HTML as <website>_tmp.html inside tmp_html/
            
            # Extract hyperlinks from the saved HTML file
            links_data = extract_hyperlinks(f"tmp_html/{website}_tmp.html", base_url, links, blacklists_dir="blacklists/")
            
            # Save the extracted links to a JSON file
            save_links(links_data, category_name)
            print(f"Extracted hyperlinks for {website} saved to links_{category_name}.json")
    
    # Print skipped news sources at the end
    print(f"\nTotal skipped news sources: {len(skipped_sources)}")
    if skipped_sources:
        print("Skipped news sources:")
        for source in skipped_sources:
            print(source)

    print("\n\nGenerating markdown files...")
    json_directory = 'tmp_json'
    output_directory = 'content/posts'
    generate_markdown_from_json(morning_run, json_directory, output_directory)
    print("Markdown files generated successfully!")
        
if __name__ == "__main__":
    main()
