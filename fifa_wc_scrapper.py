"""
FIFA World Cup data scraper

     Author: Daniel Vazquez

      To do: > Add '94 edition
             > Test all functions work:
               - roster_scraper:  []
               - groups_scraper:  []
               - matches_scraper: [YES]
             > Possibly add more editions
             > Automate SQL Server upload                
"""

# -----------------------------------------------------------------------------

# Import libraries
from bs4 import BeautifulSoup as bs
from io import StringIO
import pandas as pd
import numpy as np
import requests
import re
import os

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'}

def main(): # -----------------------------------------------------------------
    
    # Define lists to store dataframes
    rosters_ds = []
    groups_ds = []
    matches_ds = []

    # Define list to iterate through tournament editions
    years = [y for y in range(1994, 2023, 4) if y not in [1942, 1946]] # [1994]
    wc_editions = ['USA 1994','France 1998','Korea/Japan 2002','Germany 2006','South Africa 2010','Brazil 2014','Russia 2018','Quatar 2022'] # 

    # Define eras
    modern_era = [y for y in range(1998, 2023, 4)] 
    classic_era = [1994]

    # Scrapping tournament data ----------------------------------------

    for year, edition in zip(years, wc_editions):
        
        squads_soup, matches_soup = get_cs_data(year, edition)

        roster_scraper(squads_soup, year, edition, modern_era, classic_era, rosters_ds)    
        groups_scraper(matches_soup, year, edition, modern_era, classic_era, groups_ds)
        matches_scraper(matches_soup, year, edition, modern_era, classic_era, matches_ds)

    # -------------------------------------------------------------------------

    # Combine all df's into one
    rosters_ds = pd.concat(rosters_ds)
    groups_ds = pd.concat(groups_ds)
    matches_ds = pd.concat(matches_ds)
    print('Data sets complete.')
    #print(rosters_ds)

    save_to_csv(rosters_ds, groups_ds, matches_ds) # Save data sets to .csv's
    
def get_cs_data(year, edition): # ------------------------------------------------------

    print(f'Obtaining {edition} data...')

    # Define URLs
    squads_url = f'https://en.wikipedia.org/wiki/{year}_FIFA_World_Cup_squads'
    wc_url = f'https://en.wikipedia.org/wiki/{year}_FIFA_World_Cup'

    # Obtain html from squads' webpage
    page = requests.get(squads_url, headers = headers)
    squads_soup = bs(page.content, 'html.parser')

    # Obtain html from results and groups webpage
    page2 = requests.get(wc_url, headers = headers)
    matches_soup = bs(page2.content, 'html.parser')

    return squads_soup, matches_soup

def roster_scraper(squads_soup, year, edition, modern_era, classic_era, rosters_ds): # -----------------

    # Scrapping player data ---------------------------------------------------

    # Import rosters
    tables = squads_soup.find_all('table', attrs = {'class':'wikitable'})
    rosters = pd.read_html(StringIO(str(tables))) # Create list of dataframes (df)

    # Removing unnecessary data (extra tables)
    if year == 1994:
        rosters = rosters[:-1]
    elif year == 2018 or year == 2010:
        rosters = rosters[:-4]
    elif year == 2014:
        rosters = rosters[:-3]
    elif year == 2006:
        rosters = rosters[:-3]
    elif year == 2002 or year == 1998:
        rosters = rosters[:-2]
        # 2002 page has reference tags on the headers that need to be removed
        for i in rosters:
            i.columns = [re.sub(r'\[\d+\]','', col) for col in i.columns]
    elif year == 2022:
        rosters = rosters[:-6]

    #print(rosters)

    df = pd.concat(rosters) # Merge all df's in 'rosters' list into one df
    #print(df)

    # Import player nationalities ---------------------------------------------

    Country = [] # Participating countries

    countries = squads_soup.find_all('h3')

    # Import countries
    for i in countries:
        a = i.get_text()
        it = a.replace('[edit]', '')
        Country.append(it)

    # Removing unnecessary data
    if year == 1994:
        Country = Country[:-2]
    elif year == 2010 or year == 2018 or year == 2002:
        Country = Country[:-5]
    elif year == 2006:
        Country = Country[:-1]
    elif year == 2014:
        Country = Country[:-4]
    elif year == 2022:
        Country = Country[:-7]
    elif year == 1998:
        Country = Country[:-3]
    
    #print(Country)

    # Add players' nationalities
    if year in classic_era:
        Country = np.repeat(Country, 22).tolist()
    elif year in modern_era and year != 1998 and year != 2022:
        Country = np.repeat(Country, 23).tolist()
    elif year == 1998: # 1998 edition had a squad size of 22 per team. South Africa presented 23 due to injuries.
        Country = np.repeat(Country, [23 if i == 'South Africa' else 22 for i in Country]).tolist()
    elif year == 2022: # 2022 edition increased team size from 23 to 26. Iran presented 25 players instead of 26.
        Country = np.repeat(Country, [25 if i == 'Iran' else 26 for i in Country]).tolist()
    elif year in modern_era and year != 1998 and year != 2022:
        Country = np.repeat(Country, 23).tolist()

    #print(len(Country))
    #print(len(df))

    df['Country'] = Country # Add 'Country' column to df
    #print(df)

    #"""# Format table ------------------------------------------------------------
    
    # Separating age from date of birth
    df[['DateOfBirth', 'Age']] = df['Date of birth (age)'].str.extract(r'^(.*)\s\(aged\s(\d+)\)')
    df = df.drop(columns=['Date of birth (age)'])

    # Separating captain status from names
    captain_regex = r'\s\((?:c|captain)\)'
    df['Captain'] = df['Player'].str.contains(captain_regex, case=False, regex=True)
    df['Player'] = df['Player'].str.replace(captain_regex, '', case=False, regex=True)

    # Add tournament to every players' entry
    if year in classic_era: # 22 players per team * 24 teams
        tournament = [edition] * 528
    elif year == 1998: # 22 players per team * 32 teams + 1 replacement
        tournament = [edition] * 705
    elif year == 2022: # 26 players per team * 32 teams - 1 drop
        tournament = [edition] * 831
    elif year in modern_era and year != 1998 and year != 2022:
        tournament = [edition] * 736 # 23 players per team * 32 teams

    df['Tournament'] = tournament # Add 'Tournament' column to df

    # Add Goals column
    if year == 2018 or year == 2022:
        df['Goals'] = df['Goals'].astype('Int64')
        #df = df.iloc[:, [0, 1, 2, 6, 5, 4, 9, 3, 7, 10, 8]]
    else:
        df['Goals'] = np.nan
        df['Goals'] = df['Goals'].astype('Int64')
        #df = df.iloc[:, [0, 1, 2, 6, 5, 4, 9, 3, 7, 10, 8]]

    # Fix column order
    col_header = ['Tournament','Player','No.','Pos.','Captain','Club','Country','Caps','DateOfBirth','Age','Goals']
    cols = [col for col in df.columns if col not in col_header]
    df = df[col_header + cols]

    rosters_ds.append(df) # add df to the data set"""
       
def groups_scraper(matches_soup, year, edition, modern_era, classic_era, groups_ds): # ---------------------

    # Import group tables
    tables = matches_soup.find_all('table', attrs = {'class':'wikitable'})
    groups = pd.read_html(StringIO(str(tables)))

    # Remove unnecessary data (extra tables)
    if year == 1994: groups = groups[3:-5]
    elif year == 1998: groups = groups[14:-5]
    elif year == 2002: groups = groups[13:-5]
    elif year == 2006: groups = groups[14:-6]
    elif year == 2010: groups = groups[6:-6]
    elif year == 2014: groups = groups[9:-8]
    elif year == 2018: groups = groups[6:-9]
    elif year == 2022: groups = groups[14:-3]

    #print(groups)
    
    df = pd.concat(groups)
    #print(df)
    #"""
    # Add group to teams
    if year in classic_era:
        Group = ['A','B','C','D','E','F']
    elif year in modern_era:
        Group = ['A','B','C','D','E','F','G','H']
    df['Group'] = np.repeat(Group, 4)
    
    # Add Tournament
    if year in classic_era:
        df['Tournament'] = np.repeat(edition,24)
    elif year in modern_era:
        df['Tournament'] = np.repeat(edition,32)

    # Clean up information
    df.loc[df['Qualification'].isna(), 'Qualification'] = 'Eliminated' # Reformat 'Qualification' column
    df = df.rename(columns = {'Teamvte':'Team'}) # Rename Team column
    df['Team'] = df['Team'].str.replace(' (H)', '', regex = False)

    # Some teams have a link clarifying qualification due to fair play points. Info needs to
    # be appended to 'Qualification'
    fpp = df['Pts'].astype(str).str.contains(r'\[a\]', na=False)
    df.loc[fpp, 'Qualification'] = df.loc[fpp, 'Qualification'].astype(str) + ' (Fair Play Points)'
    df['Pts'] = df['Pts'].astype(str).str.replace(r'\s*\[a\]', '', regex=True).str.strip()
    
    # Replace special characters in GD column
    df['GD'] = df['GD'].str.replace(r'[\u2212\u2013\u2014]', '-', regex = True)

    # Reorganize df
    col_header = ['Tournament', 'Group','Pos','Team','Pld','W','D','L','GF','GA','GD','Pts','Qualification']
    cols = [col for col in df.columns if col not in col_header]
    df = df[col_header + cols]

    groups_ds.append(df) # Add df to the data set"""

def matches_scraper(matches_soup, year, edition, modern_era, classic_era, matches_ds): # -------------------

    # Define lists
    Tournament = []      # WORKS FOR '02-'22
    Home = []            # WORKS FOR '02-'22
    Score = []           # WORKS FOR '02-'22
    HomeScore = []       # WORKS FOR '02-'22
    AwayScore = []       # WORKS FOR '02-'22
    Away = []            # WORKS FOR '02-'22
    ExtraTime = []       # WORKS FOR '02-'22
    GoldenGoal = []      # WORKS FOR '02-'22
    Penalties = []       # WORKS FOR '02-'22
    HomePKs = []         # WORKS FOR '02-'22
    AwayPKs = []         # WORKS FOR '02-'22
    Referee = []         # WORKS FOR '02-'22
    Location = []        # WORKS FOR '02-'22
    Attendance = []      # WORKS FOR '02-'22
    Date = []            # WORKS FOR '94-'22
    Time = []            # WORKS FOR '94-'22
    
    Winner = []

    # Group stage data scrap --------------------------------------------------

    # Import tables containing all group matches data
    match_info = matches_soup.find_all('div', attrs = {'itemscope': True, 
                                           'itemtype': 'http://schema.org/SportsEvent',
                                           'class': 'footballbox'})

    #<div itemscope itemtype="http://schema.org/SportsEvent" class="footballbox" style="color:inherit">
    #<div itemprop="location" itemscope itemtype="http://schema.org/Place">

    # Import data from footballbox tables
    # Path: div -> tr -> th -> span -> a
    for match in match_info:
        # Create tournament column
        Tournament.append(edition)
        # Import home team
        home_team = match.select_one('th.fhome span a')
        Home.append(home_team.get_text(strip = True))
        # Import match score
        score = match.select_one('th.fscore')
        score_text = score.get_text(strip = True)
        Score.append(score_text)
        # Split match score into two separate lists
        goals = re.findall(r'\d+', score_text)
        if len(goals) == 2:
            HomeScore.append(goals[0].strip())
            AwayScore.append(goals[1].strip())
        else:
            HomeScore.append(None)
            AwayScore.append(None)
        # Import away team
        away_team = match.select_one('th.faway span a')
        Away.append(away_team.get_text(strip = True))
        # Import dates
        date = match.select_one('div.fleft div.fdate')
        Date.append(date.get_text(strip = True))
        # Import time
        time = match.select_one('div.fleft div.ftime')
        Time.append(time.get_text(strip = True)[:5])
        # Import location
        place = match.select_one('div.fright div[itemprop="location"] span a')
        Location.append(place.get_text(strip = True))
        # Import Attendance
        crowd = match.select_one('div.fright div:nth-of-type(2)')
        Attendance.append(crowd.get_text(strip = True).replace('Attendance: ', ''))
        # Import referee
        ref = match.select_one('div.fright div:nth-of-type(3) a')
        Referee.append(ref.get_text(strip = True))
        # Add match stage
        if year in modern_era:
            Stage = (['Group Stage']*48+['Round of 16']*8+['Quarter-finals']*4+
                     ['Semi-finals']*2+['Third Place Match']*1+['Final']*1)
        elif year in classic_era:
            Stage = (['Group Stage']*36+['Round of 16']*8+['Quarter-finals']*4+
                     ['Semi-finals']*2+['Third Place Match']*1+['Final']*1)
        # Add group the game was played in
        if year in modern_era:
            Group = (['A']*6+['B']*6+['C']*6+['D']*6+['E']*6+
                     ['F']*6+['G']*6+['H']*6+['NaN']*16)
        elif year in classic_era:
            Group = (['A']*6+['B']*6+['C']*6+['D']*6+['E']*6+
                     ['F']*6+['NaN']*16)
        # Signal if the game went to extra time
        if 'a.e.t.' in score_text.lower():
            ExtraTime.append(True)
        else:
            ExtraTime.append(False)
        # Signal if the game was won by golden goal
        if 'g.g.' in score_text.lower():
            GoldenGoal.append(True)
        else:
            GoldenGoal.append(False)
        # Add penalties scores (if applicable)
        PK_check = match.find_all('tr', class_= 'fgoals')
        if len(PK_check) > 1:
            PKs = PK_check[1] # penalies are stored in the second <tr class="fgoals">
            PK_score = PKs.get_text(strip = True)
            PK_goals = re.findall(r'\d+', PK_score)
            if len(PK_goals) >=2: #
                Penalties.append(True); HomePKs.append(PK_goals[0]); AwayPKs.append(PK_goals[1])
            else:
                Penalties.append(False); HomePKs.append(None); AwayPKs.append(None)
        else:
            Penalties.append(False); HomePKs.append(None); AwayPKs.append(None)
        # Add winner column
        Winner.append(None)

# Create dataframe
    df = {
        'Tournament': Tournament,
        'Stage': Stage,
        'Group': Group,
        'Home': Home,
        'Away': Away,
        'Score': Score,
        'HomeScore': HomeScore,
        'AwayScore': AwayScore,
        'ExtraTime': ExtraTime,
        'GoldenGoal': GoldenGoal,
        'Penalties': Penalties,
        'HomePKs': HomePKs,
        'AwayPKs': AwayPKs,
        'Winner': Winner,
        'Referee': Referee,
        'Location': Location,
        'Attendance': Attendance,
        'Date': Date,
        'Time': Time
    }
    
    # Turn dictionary into dataframe
    df = pd.DataFrame.from_dict(df)
    
    # Fill up winner column
    conditions = [
    (df['HomeScore'] > df['AwayScore']),
    (df['AwayScore'] > df['HomeScore']),
    (df['Penalties'] & (df['HomePKs'] > df['AwayPKs'])),
    (df['Penalties'] & (df['AwayPKs'] > df['HomePKs']))
    ]

    # Choices
    choices = [df['Home'], df['Away'], df['Home'], df['Away']]

    # Fill the winner column, default to 'Draw'
    df['Winner'] = np.select(conditions, choices, default='Draw')
    # Replace Spacial dash with regular dash
    df['Score'] = df['Score'].str.replace(r'[\u2013\u2014]', '-', regex = True)

    matches_ds.append(df) # Add df to the data set

def save_to_csv(rosters_ds, groups_ds, matches_ds):

    # Define directory to save CSVs to
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_folder = 'csv_files'
    csv_path = os.path.join(script_dir, csv_folder)

    print('Saving...')

    # Save full data sets to csv files
    rosters_ds.to_csv(os.path.join(csv_path,'FIFA_wc_players.csv'),
                      index = False, encoding = 'utf-8-sig')
    groups_ds.to_csv(os.path.join(csv_path,'FIFA_wc_groups.csv'),
                     index = False, encoding = 'utf-8-sig')
    matches_ds.to_csv(os.path.join(csv_path,'FIFA_wc_matches.csv'),
                      index = False, encoding = 'utf-8-sig')

    print('Done')

main()
