import os
import json
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Path to the folder containing the JSON files
json_dir = os.path.join(os.getcwd(), 'tmp_json')
blacklist_dir = os.path.join(os.getcwd(), 'blacklists')  # Correct path to blacklist directory

# A temporary storage for the last added link (in-memory storage)
last_blacklisted_link = None

@app.route('/')
def index():
    # Get a list of all JSON filenames in the tmp_json directory
    files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    return render_template('index.html', files=files)

@app.route('/links/<filename>')
def links(filename):
    # Load the selected JSON file
    file_path = os.path.join(json_dir, filename)
    if not os.path.exists(file_path):
        return "File not found!", 404

    # Open and parse the selected JSON file
    with open(file_path) as f:
        data = json.load(f)

    # Organize links by categories (daily_links)
    all_links = data.get('daily_links', {})
    return render_template('links_page.html', all_links=all_links, filename=filename)

@app.route('/add_to_blacklist', methods=['POST'])
def add_to_blacklist():
    global last_blacklisted_link
    link = request.form.get('link')  # Get the link from the form submission

    # Get the current date formatted as YYYY_MM_DD
    date_str = datetime.now().strftime('%Y_%m_%d') 

    # Define the blacklist file path with date-based naming convention
    blacklist_file = os.path.join(blacklist_dir, f"blklst_{date_str}.json")

    # Read the current blacklist (or create if it doesn't exist)
    if os.path.exists(blacklist_file):
        with open(blacklist_file, 'r') as f:
            data = json.load(f)
            blacklist = data.get("blacklisted_links", [])
    else:
        blacklist = []

    # Check if the link is already in the blacklist
    if link in blacklist:
        return jsonify({"message": "Link already blacklisted", "status": "error"})

    # Add the link to the blacklist
    blacklist.append(link)

    # Save the updated blacklist to the file with the correct format
    with open(blacklist_file, 'w') as f:
        json.dump({"blacklisted_links": blacklist}, f, indent=4)

    # Store the last added link and its date in memory for undo
    last_blacklisted_link = {"link": link, "date": date_str}

    return jsonify({"message": "Link added to blacklist", "status": "success"})


@app.route('/undo_blacklist', methods=['POST'])
def undo_blacklist():
    global last_blacklisted_link

    # Check if there's a recent action to undo
    if not last_blacklisted_link:
        return jsonify({"message": "No recent action to undo", "status": "error"})

    # Get the link and date of the last blacklisted link
    link = last_blacklisted_link['link']
    date_str = last_blacklisted_link['date']

    # Define the blacklist file path
    blacklist_file = os.path.join(blacklist_dir, f"blklst_{date_str}.json")

    # Check if the blacklist file exists
    if not os.path.exists(blacklist_file):
        return jsonify({"message": "Blacklist file not found", "status": "error"})

    try:
        # Read the current blacklist
        with open(blacklist_file, 'r') as f:
            data = json.load(f)
            blacklist = data.get("blacklisted_links", [])

        # Remove the last blacklisted link
        blacklist = [item for item in blacklist if item != link]

        # Save the updated blacklist to the file
        with open(blacklist_file, 'w') as f:
            json.dump({"blacklisted_links": blacklist}, f, indent=4)

        # Clear the last blacklisted link from memory
        last_blacklisted_link = None

        return jsonify({"message": "Last blacklisted link removed", "status": "success"})

    except json.JSONDecodeError:
        return jsonify({"message": "Error reading blacklist file. It may be corrupted.", "status": "error"})
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}", "status": "error"})



if __name__ == '__main__':
    app.run(debug=True)
