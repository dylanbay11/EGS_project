# visualization

import streamlit as st
import pandas as pd
import plotly.express as px

# url = 'https://github.com/dylanbay11/FreeGames_app/blob/main/wide_final.csv'
# df = pd.read_csv(url, header = True, sep = ",")

# cached URL option:
# @st.cache_data
# def load_data():
#     url = "https://github.com/dylanbay11/FreeGames_app/blob/main/nodesc.csv"
#     return pd.read_csv(url, na_values=['', 'NA', 'NaN', None]) 
# df = load_data()

df = pd.read_csv("~/Desktop/dshw/EGS_project/nodesc.csv")

# begin streamlit stuff
st.title("Epic Games Store Giveaways")

# df

nice_df = df.iloc[:, [3, 4, 5, 6, 10, 11, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]]
nice_df.set_index("Number", inplace = True)
nice_df.columns = ["Game Name", "Start Date", "End Date", "IntPrice", "Full Price", "Action",
                   "Adventure", "Puzzle", "RPG", "Shooter", "Strategy", "Survival", "OSX", "Windows", "Singleplayer", "Multiplayer"]
nice_df.iloc[:, [0,1,2,4]]
nice_df.iloc[:, [11, 12, 0, 5,6,7,8,9,10,13,14,15]]

nice_df['Start Date'] = pd.to_datetime(nice_df['Start Date'])  # Convert 'Start Date' column to datetime format
nice_df['IntPrice'] = nice_df['IntPrice'] / 100  # Divide 'IntPrice' by 100

# Aggregate prices for games with the same start date
nice_df_agg = nice_df.groupby('Start Date')['IntPrice'].sum().reset_index()

# Create a line chart using Plotly Express
fig = px.line(nice_df_agg, x='Start Date', y='IntPrice', title='Total Dollar Value Per Giveaway, Over Time')

# Display the line chart in Streamlit
st.plotly_chart(fig)




# Create sidebar title
st.sidebar.title("Game Statistics")

# Sidebar Pie chart for Multiplayer vs Singleplayer vs Missing/None
# Calculate counts
# multiplayer_count = nice_df['Multiplayer'].notna().sum()
# singleplayer_count = nice_df['Singleplayer'].notna().sum()
# missing_count = len(nice_df) - multiplayer_count - singleplayer_count

# # Create Pie chart
# fig1 = px.pie(names=['Multiplayer', 'Singleplayer', 'Missing/None'],
#               values=[multiplayer_count, singleplayer_count, missing_count],
#               title='Percentage of Total Games by Gameplay Type')
# st.sidebar.plotly_chart(fig1, use_container_width=True)

# Sidebar Pie chart for OSX vs Windows vs BOTH
# Calculate counts
osx_count = nice_df['OSX'].notna().sum()
windows_count = nice_df['Windows'].notna().sum()
both_count = nice_df[(nice_df['OSX'].notna()) & (nice_df['Windows'].notna())].shape[0]

# Create Pie chart
fig2 = px.pie(names=['OSX', 'Windows', 'Both'],
              values=[osx_count, windows_count, both_count],
              title='Percentage of Total Games by Operating System Compatibility')
st.sidebar.plotly_chart(fig2, use_container_width=True)



# Extract month and year from 'Start Date' column
nice_df['MonthYear'] = nice_df['Start Date'].dt.to_period('M')

# Group by 'MonthYear' and count the number of games released in each month-year bin
games_per_month_year = nice_df.groupby('MonthYear').size().reset_index(name='TotalGames')

# Convert 'MonthYear' to string
games_per_month_year['MonthYear'] = games_per_month_year['MonthYear'].astype(str)

# Create main chart title
st.title("Total Games Released by Month-Year")

# Create bar chart using Plotly Express
fig3 = px.bar(games_per_month_year, x='MonthYear', y='TotalGames',
             labels={'MonthYear': 'Month-Year', 'TotalGames': 'Total Games Released'},
             title='Total Games Released by Month-Year')
st.plotly_chart(fig3)




# Game search section
st.subheader("Game Search - Look up a game's details!")
search_query = st.text_input("Enter game name:")

# Check if a search query has been entered
if search_query:
    search_query_lower = search_query.lower()
    game_info = df[df['Name'].str.lower().str.contains(search_query_lower, case=False)]
    if not game_info.empty:
        for idx, row in game_info.iterrows():
            st.write(f"Game: {row['Name']}, Link: {row['Link']}")
    else:
        st.write(f"No game found containing '{search_query}'")



# Tag selection section
st.subheader("Tag Selection")
selected_tag = st.selectbox("Select a tag:", nice_df.columns[4:])  # tags start from the here on 
tag_counts = nice_df[selected_tag].value_counts()

# Create a pie chart to visualize the distribution of games with and without the selected tag
fig4 = px.pie(names=tag_counts.index, values=tag_counts.values,
             title=f"Distribution of Games with and without the tag '{selected_tag}'")
st.plotly_chart(fig4)
    