import pandas as pd
import plotly.express as px
import os

def load_and_clean_data(filepath):
    """
    Loads and cleans dataset for visualizations.

    Args:
        filepath (str): Path to the CSV dataset.

    Returns:
        pd.DataFrame: A cleaned DataFrame ready for plotting.
    """
    # Load data and skip the row containing totals (row index 1 in standard pandas read_csv if header=0)
    # The first row of data (after header) seems to be totals
    df = pd.read_csv(filepath, skiprows=[1])

    # Clean 'GG' column
    df['is_good_game'] = df['GG'].apply(lambda x: True if str(x).strip() == '⭐' else False)

    # Clean 'Start' column to datetime
    df['Start Date'] = pd.to_datetime(df['Start'], errors='coerce')
    df['Start Year'] = df['Start Date'].dt.year

    return df

def visualize_good_games(df, output_dir):
    """
    Generates and saves a stacked bar chart of 'good games' per year.

    Args:
        df (pd.DataFrame): The cleaned dataset.
        output_dir (str): The directory path to save the resulting HTML plot.
    """
    # Group by year and count good games vs total games
    yearly_stats = df.groupby('Start Year').agg(
        Total_Games=('Games', 'count'),
        Good_Games=('is_good_game', 'sum')
    ).reset_index()

    yearly_stats['Other_Games'] = yearly_stats['Total_Games'] - yearly_stats['Good_Games']

    # Melt for stacked bar chart
    melted = yearly_stats.melt(id_vars=['Start Year', 'Total_Games'],
                               value_vars=['Good_Games', 'Other_Games'],
                               var_name='Game Type', value_name='Count')

    melted['Game Type'] = melted['Game Type'].map({'Good_Games': 'Good Game', 'Other_Games': 'Standard Game'})

    fig = px.bar(melted, x='Start Year', y='Count', color='Game Type',
                 title='Epic Games Store Giveaways: Good Games per Year',
                 labels={'Start Year': 'Year', 'Count': 'Number of Games'},
                 barmode='stack',
                 color_discrete_map={'Good Game': 'gold', 'Standard Game': 'lightgray'})

    fig.write_html(os.path.join(output_dir, 'good_games_per_year.html'))
    print(f"Saved good_games_per_year.html to {output_dir}")

def visualize_duplicates(df, output_dir):
    """
    Generates and saves a horizontal bar chart showing the most duplicated games.

    Args:
        df (pd.DataFrame): The cleaned dataset.
        output_dir (str): The directory path to save the resulting HTML plot.
    """
    # Count how often each game appears
    # Drop rows where 'Games' is null
    games_clean = df.dropna(subset=['Games'])

    duplicate_counts = games_clean['Games'].value_counts().reset_index()
    duplicate_counts.columns = ['Game Name', 'Count']

    # Filter for games given away more than once
    duplicates_only = duplicate_counts[duplicate_counts['Count'] > 1]

    # Sort by count
    duplicates_only = duplicates_only.sort_values(by='Count', ascending=True)

    # If there are too many, take top 20
    if len(duplicates_only) > 20:
        duplicates_only = duplicates_only.tail(20)

    fig = px.bar(duplicates_only, x='Count', y='Game Name', orientation='h',
                 title='Top Duplicated Games in Epic Games Store Giveaways',
                 labels={'Count': 'Number of Times Given Away', 'Game Name': 'Game'})

    # Set x-axis tick step to 1
    fig.update_layout(xaxis=dict(tickmode='linear', tick0=1, dtick=1))

    fig.write_html(os.path.join(output_dir, 'top_duplicated_games.html'))
    print(f"Saved top_duplicated_games.html to {output_dir}")

def main():
    """Main function to load data, generate standard visualizations, and save them."""
    data_path = 'data/epic_free_games_with_api_details.csv'
    output_dir = 'development'

    if not os.path.exists(data_path):
        print(f"Data file not found at {data_path}. Attempting alternative path...")
        data_path = '../data/epic_free_games_with_api_details.csv'
        if not os.path.exists(data_path):
            raise FileNotFoundError("Could not find the dataset.")
        output_dir = '.'

    print(f"Loading data from {data_path}...")
    df = load_and_clean_data(data_path)

    print("Generating visualizations...")
    visualize_good_games(df, output_dir)
    visualize_duplicates(df, output_dir)
    print("Done!")

if __name__ == '__main__':
    main()
