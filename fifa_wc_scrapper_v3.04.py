"""
FIFA World Cup data scraper

     Author: Daniel Vazquez

Description: This program scraps online tables and data related to the
             rosters, teams, fixtures, and main stats for the FIFA World Cup
             tournaments from 2002 to 2022. All data is scrapped from their
             respective entries in Wikipedia. Since its very uniformally
             organized throughout all pages, it allows for easy scalability.
             The program follows the following procedure:

             1. Access the html code for the websites to scrape using the
                BeautifulSoup libraries.

             2. Scrape the html code looking for the following information:

                a. Team groups
                b. Participating countries
                c. Players' names
                d. Players' ages and birthdays
                e. Match locations
                f. Match dates
                g. Match results
                h. Match home and away sides
                i. Match groups and stages.

             3. Save all scrapped dataframes to csv files.

      To do: > Add '98 edition
             > Test all functions work:
               - roster_scraper:  []
               - groups_scraper:  []
               - matches_scraper: [YES]
             > Possibly add more editions
             > Automate SQL Server upload
             > Update GitHub repository
                 
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

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_folder = 'csv_files'
csv_path = os.path.join(script_dir, csv_folder)

def main(): # -----------------------------------------------------------------

     # Define lists
     rosters_ds = []
     groups_ds = []
     matches_ds = []
     wc_editions = ['France 1998','Korea/Japan 2002', 'Germany 2006', 'South Africa 2010', 'Brazil 2014', 'Russia 2018', 'Quatar 2022'] # 
     years = [y for y in range(1998, 2023, 4) if y not in [1942, 1946]]
     
     # Scrapping tournament data
     for year, squads, matches, edition in zip(years, wc_editions):
     
          print(f'Obtaining {edition} data...')

          # Obtain soups
          squads_soup, match_soup = get_wc_data(year)
          # Creating dataframes 
          roster_scraper(squads_soup, year, edition, rosters_ds)    
          groups_scraper(match_soup, matches, edition, groups_ds)
          matches_scraper(match_soup, matches, edition, matches_ds)
     
     # Combine all df's into one
     rosters_ds = pd.concat(rosters_ds)
     groups_ds = pd.concat(groups_ds)
     matches_ds = pd.concat(matches_ds)
     print('Data sets complete. Saving...')
     
     # Save full data sets to csv files
     rosters_ds.to_csv(os.path.join(csv_path,'FIFA_wc_players.csv'),
                 index = False, encoding = 'utf-8-sig')
     groups_ds.to_csv(os.path.join(csv_path,'FIFA_wc_groups.csv'),
                index = False, encoding = 'utf-8-sig')
     matches_ds.to_csv(os.path.join(csv_path,'FIFA_wc_matches.csv'),
                 index = False, encoding = 'utf-8-sig')
     
     print('Done')

def get_wc_data(year):

    wc_squads_url = f"https://en.wikipedia.org/wiki/{year}_FIFA_World_Cup_squads"
    wc_matches_url = f"https://en.wikipedia.org/wiki/{year}_FIFA_World_Cup"

    # Obtain html from squads' webpage
    page = requests.get(wc_squads_url, headers = headers)
    squads_soup = bs(page.content, 'html.parser')
    
    # Obtain html from results and groups webpage
    page2 = requests.get(wc_matches_url, headers = headers)
    match_soup = bs(page2.content, 'html.parser')

    return squads_soup, match_soup
    
def roster_scraper(squads_soup, year, edition, rosters_ds): # ----------------------

     # Scrapping player data --------------------------------------------------
     
     # Import rosters
     tables = squads_soup.find_all('table', attrs = {'class':'wikitable'})
     rosters = pd.read_html(StringIO(str(tables))) # Create list of dataframes (df)
     
     # Removing unnecessary data (extra tables)
     if year == 2018 or year == 2010:
        rosters = rosters[:-4]
     elif year == 2014:
        rosters = rosters[:-3]
     elif year == 2006:
        rosters = rosters[:-3]
     elif year == 2002:
        rosters = rosters[:-2]
        # 2002 page has reference tags on the headers that need to be removed
        for i in rosters:
            i.columns = [re.sub(r'\[\d+\]','', col) for col in i.columns]
     elif year == 2022:
        rosters = rosters[:-6]
     
     df = pd.concat(rosters) # Merge all df's in 'rosters' list into one df

     # Complete and format df -------------------------------------------------

     # Separating age from date of birth
     df[['Date of Birth', 'Age']] = df['Date of birth (age)'].str.extract(r'^(.*)\s\(aged\s(\d+)\)')
     df = df.drop(columns=['Date of birth (age)'])

     # Separating captain status from names
     captain_regex = r'\s\((?:c|captain)\)'
     df['Captain'] = df['Player'].str.contains(captain_regex, case=False, regex=True)
     df['Player'] = df['Player'].str.replace(captain_regex, '', case=False, regex=True)

     # Add tournament column
     count = 831 if year == 2022 else 736 # 2022 edition increased team size from 23 to 26
     tournament = [edition] * count
     df['Tournament'] = tournament

     # Rename No. and Pos. columns
     df.rename(columns = {'No.': 'Number'}, inplace = True)
     df.rename(columns = {'Pos.': 'Position'}, inplace = True)
     
     # Define lists
     Country = [] # Participating countries
     
     # Import participating countries
     countries = soup.find_all('h3')
     
     # Import countries
     for i in countries:
        a = i.get_text()
        it = a.replace('[edit]', '')
        Country.append(it)
     
     # Removing unnecessary data
     if year == 2010 or year == squads18 or year == 2002:
        Country = Country[:-5]
     elif year == 2006:
        Country = Country[:-1]
     elif year == 2014:
        Country = Country[:-4]
     elif year == 2022:
        Country = Country[:-7]

     # Add players' nationalities
     if year == 2022: # 2022 edition increased team size from 23 to 26. Iran presented 25 players instead of 26.
        Country = np.repeat(Country, [25 if i == 'Iran' else 26 for i in Country]).tolist()
     else:
        Country = np.repeat(Country, 23).tolist()
     
     df['Country'] = Country # Add 'Country' column to df
     
     # Add Goals column to tables that don't have it and fix column order
     if year == 2018 or year == 2022:
        df['Goals'] = df['Goals'].astype('Int64')
        df = df.iloc[:, [0, 1, 2, 6, 5, 4, 9, 3, 7, 10, 8]]
     else:
        df['Goals'] = np.nan
        df['Goals'] = df['Goals'].astype('Int64')
        df = df.iloc[:, [0, 1, 2, 6, 5, 4, 9, 3, 7, 10, 8]]
     
     rosters_ds.append(df) # add df to the data set
       
def groups_scraper(match_soup, matches, edition, groups_ds): # ---------------------

    # Import group tables
    tables = match_soup.find_all('table', attrs = {'class':'wikitable'})
    groups = pd.read_html(StringIO(str(tables)))

    # Remove unnecessary data (extra tables)
    if year == 2002:
        groups = groups[13:-5]
    elif year == 2006:
        groups = groups[14:-6]
    elif year == 2010:
        groups = groups[6:-6]
    elif year == 2014:
        groups = groups[9:-8]
    elif year == 2018:
        groups = groups[6:-9]
    elif year == 2022:
        groups = groups[14:-3]

    df = pd.concat(groups)    
    #print(df)
    #print(len(df))
    # Add group to teams
    Group = ['A','B','C','D','E','F','G','H']
    df['Group'] = np.repeat(Group, 4)
    
    # Add Tournament
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
     
    # Reorganize df
    col_header = ['Tournament', 'Group','Pos','Team','Pld','W','D','L','GF','GA','GD','Pts','Qualification']
    cols = [col for col in df.columns if col not in col_header]
    df = df[col_header + cols]

    groups_ds.append(df) # Add df to the data set

def matches_scraper(match_soup, matches, edition, matches_ds): # -------------------

    # Define lists
    Tournament = []
    Home = []
    Score = []
    HomeScore = []
    AwayScore = []
    Away = []
    ExtraTime = []
    GoldenGoal = []
    Penalties = []
    HomePKs = []
    AwayPKs = []
    Referee = []
    Location = []
    Attendance = []
    Date = []
    Time = []
    Stage = (['Group Stage']*48+['Round of 16']*8+
             ['Quarter-finals']*4+['Semi-finals']*2+
             ['Third Place Match']*1+['Final']*1)
    Group = (['A']*6+['B']*6+['C']*6+['D']*6+['E']*6+
             ['F']*6+['G']*6+['H']*6+['NaN']*16)
    Winner = []

    # Group stage data scrap --------------------------------------------------

    # Import tables containing all group matches data
    match_info = match_soup.find_all('div', attrs = {'itemscope': True, 
                                           'itemtype': 'http://schema.org/SportsEvent',
                                           'class': 'footballbox'})

    # Import data from footballbox tables
    # Path: div -> tr -> th -> span -> a
    # if matches == wc02:
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

    matches_ds.append(df)

main()
