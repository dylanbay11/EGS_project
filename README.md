# EGS_project
Analyzing details from the Epic Games Store ongoing giveaways, with the goal of creating a streamlit app to visualize some of this data.

Details about the process and eventually the results to be found on [my blog](https://github.com/dylanbay11/blog_home). Take a look!

Created for my Data Science class, Winter 2024.

# Navigation and File Identification
Roughly chronologically, the important data and code is distributed as follows:
- Original files `df_scraped.csv` + `df_api.csv` = `df_joined.csv`; where as of 7 Mar 2024 and using `working_scraper.ipynb` the EGS API and a website tracking free EGS releases were accessed and scraped respectively into the core dataframe. `scraper_next.ipynb` and `scraper_wip.ipynb` are simply legacy variants and will soon be deleted
- Improved `df_complete.csv`, plus `all.csv` -> `all_withtags.csv`; where after identifying missing data with `missings.R`, filled in the data with better name matching API calls, then code to grab and format game tags, all primarily with `second_scraper.ipynb`.
- A (sadly somewhat rushed) `nodesc.csv` and variously formatted copies `wide-final`; created via `tags_added.ipynb` to properly format the tags as a dictionary but also dropping descriptions and furthermore manually encoding a few specific tags of interest
- The current frontier: possibly misnamed `reviewget.ipynb` which plans to more fully plumb the API, or even automatically label tags
- Misc files: various `*.png` which are from the EGS API wrapper docs, as reminders; a brainstorming doc with to-do list, wishlist, and ideas for a more finished, presentable streamlit app and visualizations (tentatively, `EGS.py`)

