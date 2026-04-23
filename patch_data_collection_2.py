with open("development/data_collection.py", "r") as f:
    content = f.read()

content = content.replace("output_path = \"../data/epic_games_data_with_api_details.csv\"", "output_path = os.path.join(data_dir, 'epic_games_data_with_api_details.csv')")

# The data_dir isn't available in main(), so let's fix that
search = """
    # Save the processed data
    output_path = "../data/epic_games_data_with_api_details.csv" # Save to top-level data folder
    try:
"""
replace = """
    # Save the processed data
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    output_path = os.path.join(data_dir, "epic_games_data_with_api_details.csv")
    try:
"""
if search in content:
    content = content.replace(search, replace)
    with open("development/data_collection.py", "w") as f:
        f.write(content)
    print("Patched output path successfully")
else:
    print("Search string not found")
