import os
import json
import urllib.parse
from urllib.parse import urlparse
from datetime import datetime


# Define the function to generate markdown files from json data
def generate_markdown_from_json(morning_run, json_dir, output_dir):

    article_counter = 1

    # Get all json files from the directory
    json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]

    # Iterate over each JSON file
    for json_file in json_files:
        category = json_file.split('_')[1].replace('.json', '')  # Extract category from filename
        json_path = os.path.join(json_dir, json_file)

        # Read the json data
        with open(json_path, 'r') as file:
            data = json.load(file)

        # Get today's date
        today_date = datetime.today().strftime('%Y-%m-%d')

        # Determine if articles are from the morning or evening
        title_mor_suffix = "MOR" if morning_run else "EVE"

        # Access the 'daily_links' section in the data
        daily_links = data.get("daily_links", {})

        # **Skip creating markdown if no websites exist in JSON**
        if not daily_links:
            print(f"Skipping {category}: No websites found.")
            continue  

        # Initialize markdown content list and sets for uniqueness checks
        markdown_sections = []
        seen_links = set()
        seen_headlines = set()

        # Iterate through the websites and their respective articles in 'daily_links'
        for website, articles in daily_links.items():
            if not articles:  # **Skip website if it has no articles**
                print(f"Skipping {website}: No articles found.")
                continue  

            website_markdown = f"# {website}\n\n"
            website_markdown += f"<details>\n" \
                                f"<summary>View Articles</summary>\n" \
                                f"<br>\n"

            # Track whether this website has any unique articles
            website_has_content = False

            # Iterate through each article (which is a dictionary)
            for index, article in enumerate(articles):
                headline = article.get('headline')
                link = article.get('link')

                # Check if headline and link are valid and unique in the current markdown content
                if headline and link and link not in seen_links and headline not in seen_headlines:
                    seen_links.add(link)
                    seen_headlines.add(headline)

                    # Prepend the 12ft proxy URL
                    proxied_link = f"https://12ft.io/{link}"
                    
                    search_q = urlparse(link).netloc + " " + headline
                    google_search_link = f"https://www.google.com/search?q={urllib.parse.quote_plus(search_q)}"

                    # Add a checkbox for each article
                    checkbox_html = f"<input type='checkbox' name='article_{article_counter}' value='{link}' />"

                    website_markdown += f"\n{checkbox_html} {article_counter} - <a href='{google_search_link}' target='_blank' rel='noopener noreferrer'>Search - </a> <a href='{proxied_link}' target='_blank' rel='noopener noreferrer'>{headline}</a><br>\n"

                    website_has_content = True  # Mark that this website has valid content

                    article_counter += 1

            website_markdown += f"\n</details>\n\n"

            # Add website markdown only if it has valid articles
            if website_has_content:
                markdown_sections.append(website_markdown)

        # **Skip creating markdown file if no websites have valid content**
        if not markdown_sections:
            print(f"Skipping {category}: No valid articles found.")
            continue  

        # Construct final markdown content
        markdown_content = f"+++ \n" \
                           f"author = \"cletus\"\n" \
                           f"title = \"{category} - {today_date} - {title_mor_suffix}\"\n" \
                           f"date = \"{today_date}\"\n" \
                           f"description = \"{category} news for today\"\n" \
                           f"tags = [\n" \
                           f"    \"{category}\",\n" \
                           f"]\n" \
                           f"+++\n\n"

        markdown_content += "\n".join(markdown_sections)  # Add website content

        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        category = category.replace(" ", "-").lower()

        # Create the output markdown file with UTF-8 encoding
        mor_prefix = "mor_" if morning_run else "eve_"
        output_file_path = os.path.join(output_dir, f"{mor_prefix}{category}_{today_date}.md")

        # Write the markdown content to the file
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            output_file.write(markdown_content)

        print(f"Generated: {output_file_path}")

# Set the paths to your json directory and output markdown directory
json_directory = 'tmp_json'
output_directory = 'content/posts'

# Generate markdown files
# generate_markdown_from_json(json_directory, output_directory)
