"""
FIFA World Cup data pipeline

     Author: Daniel Vazquez

      To do: > Automate AWS upload
             > Considering changing 'Date of Birth' column to just 'DOB'

      ALERT: If loading to MSSQL, go to line 1190 and change server name,
             as well as line 1193 for any connection permissions.
"""

# -----------------------------------------------------------------------------

# Import libraries
from bs4 import BeautifulSoup as bs
import sqlalchemy as sa
from io import StringIO
import pandas as pd
import numpy as np
import unicodedata
import requests
import time
import re
import os

def main():
    
    # Define dataset storage
    rosters_ds = []
    groups_ds = []
    matches_ds = []
    tournament_df = []
    teams_df = []
    players_df =[]

    # Define years and tournament edition names
    years =  [y for y in range(1930,2023,4) if y not in [1942,1946]]
    wc_editions = ['Uruguay 1930','Italy 1934','France 1938','Brazil 1950','Switzerland 1954','Sweden 1958','Chile 1962','England 1966',
                   'Mexico 1970','West Germany 1974','Argentina 1978','Spain 1982','Mexico 1986','Italy 1990','USA 1994','France 1998',
                   'Korea/Japan 2002','Germany 2006','South Africa 2010','Brazil 2014','Russia 2018','Quatar 2022']
    #wc_editions = []

    # Start program timer
    time_start = time.perf_counter()

    # Scrape online data ------------------------------------------------------

    scraper(rosters_ds, groups_ds, matches_ds, years, wc_editions)

    # Combine all df's --------------------------------------------------------

    rosters_ds = pd.concat(rosters_ds)
    groups_ds = pd.concat(groups_ds)
    matches_ds = pd.concat(matches_ds)
    print('Data sets complete')

    # Read csv's --------------------------------------------------------------

    #rosters_ds, groups_ds, matches_ds, tournament_df, teams_df, players_df = \
    #    read_csv_data(rosters_ds, groups_ds, matches_ds, tournament_df, teams_df, players_df)

    # Formatting schema -------------------------------------------------------

    rosters_ds, groups_ds, matches_ds, tournament_df, teams_df, players_df = \
        build_db_schema(rosters_ds, groups_ds, matches_ds, wc_editions, tournament_df, teams_df, players_df)

    # Export results to csv files ---------------------------------------------

    to_csv(rosters_ds, groups_ds, matches_ds, tournament_df, teams_df, players_df) # Save data sets to .csv's

    # SQL Server integration --------------------------------------------------

    to_sql(rosters_ds, groups_ds, matches_ds, tournament_df, teams_df, players_df)

    # -------------------------------------------------------------------------

    print('Done')

    # Finish timer
    time_end = time.perf_counter()
    print(f'Elapsed time: {time_end - time_start:0.4f} seconds')

def scraper(rosters_ds, groups_ds, matches_ds, years, wc_editions): 

    # Define eras by qualifying team quantity
    teams32 = [y for y in range(1998, 2023, 4)] 
    teams24 = [y for y in range(1982, 1995, 4)] 
    teams16 = [y for y in range(1954, 1979, 4)]

    # Scrapping tournament data -----------------------------------------------

    for year, edition in zip(years, wc_editions):
        
        squads_soup, matches_soup = get_data(year, edition)

        roster_scraper(squads_soup, year, edition, teams16, teams24, teams32, rosters_ds)    
        if year in [1934,1938]: pass # '34 and '38 editions had no group stage
        else: groups_scraper(matches_soup, year, edition, teams16, teams24, teams32, groups_ds)   
        matches_scraper(matches_soup, year, edition, teams16, teams24, teams32, matches_ds)

    return rosters_ds, groups_ds, matches_ds

def get_data(year, edition): 

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'}
    
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

def roster_scraper(squads_soup, year, edition, teams16, teams24, teams32, rosters_ds): 

    # Scrapping player data ---------------------------------------------------

    # Import rosters
    tables = squads_soup.select('table.sortable.wikitable.plainrowheaders')
    rosters = pd.read_html(StringIO(str(tables))) # Create list of dataframes (df)

    # 2002 page has reference tags on the headers that need to be removed
    if year == 2002:
        for i in rosters:
            i.columns = [re.sub(r'\[\d+\]','', col) for col in i.columns]

    df = pd.concat(rosters) # Merge all df's in 'rosters' list into one df

    # Import player nationalities ---------------------------------------------

    Country = [] # Participating countries

    if year in [1934,1938]: countries = squads_soup.find_all('h2')
    else: countries = squads_soup.find_all('h3')

    # Import countries
    for i in countries:
        a = i.get_text()
        it = a.replace('[edit]', '')
        Country.append(it)

    # Removing unnecessary data
    if year == 1994: Country = Country[:-2]
    elif year in [2010, 2018, 2002]: Country = Country[:-5]
    elif year in [2006]: Country = Country[:-1]
    elif year == 2014: Country = Country[:-4]
    elif year == 2022: Country = Country[:-7]
    elif year in [1998, 1990]: Country = Country[:-3]
    elif year in [1934,1938]: Country = Country[1:-3]
    
    # Add players' nationalities
    if year == 1930:
        absences = [16 if i in ['France','United States','Belgium'] else
                    17 if i in ['Mexico','Yugoslavia','Bolivia'] else 
                    15 if i == 'Romania' else 20 if i == 'Peru' else
                    19 if i == 'Chile' else 22 for i in Country]
        df['Country'] = np.repeat(Country, absences).tolist()
    elif year == 1934:
        absences = [18 if i == 'Argentina' else 20 if i == 'Egypt' else
                    21 if i == 'Sweden' else 19 if i == 'United States'
                    else 22 for i in Country]
        df['Country'] = np.repeat(Country, absences).tolist()
    elif year == 1938:
        absences = [17 if i == 'Dutch East Indies' else 15 if i == 'Cuba'
                    else 22 for i in Country]
        df['Country'] = np.repeat(Country, absences).tolist()
    elif year == 1950: # 22 players per team. Multiple teams presented incomplete rosters.
        absences = [20 if i == 'Bolivia' else 21 if i == 'Sweden' else
                    18 if i == 'United States' else 21 if i == 'England'
                    else 22 for i in Country]
        df['Country'] = np.repeat(Country, absences).tolist()
    elif year in teams16 and year not in [1954,1970]: # 22 players per team.
        df['Country'] = np.repeat(Country, 22).tolist()
    elif year == 1954: # 22 player per team. South Korea presented 20.
        df['Country'] = np.repeat(Country, [20 if i in ['South Korea'] else 22 for i in Country]).tolist()
    elif year == 1970: # 22 players per team. Morocco presented 19
        df['Country'] = np.repeat(Country, [19 if i in ['Morocco'] else 22 for i in Country]).tolist()
    elif year in teams24 and year not in [1982,1990]: # 22 players per team.
        df['Country'] = np.repeat(Country, 22).tolist()
    elif year == 1982: # 22 players per team. El Salvador presented 20
        df['Country'] = np.repeat(Country, [20 if i in ['El Salvador'] else 22 for i in Country]).tolist()
    elif year == 1990: # 22 players per team. England and Argentina replaced a player (injury)
        df['Country'] = np.repeat(Country, [23 if i in ['England','Argentina'] else 22 for i in Country]).tolist()
    elif year in teams32 and year not in [1998, 2022]: # 23 players per team.
        df['Country'] = np.repeat(Country, 23).tolist()
    elif year == 1998: # 22 players per team. South Africa presented 23 due to injuries.
        df['Country'] = np.repeat(Country, [23 if i == 'South Africa' else 22 for i in Country]).tolist()
    elif year == 2022: # 26 players per team. Iran presented 25 players instead of 26.
        df['Country'] = np.repeat(Country, [25 if i == 'Iran' else 26 for i in Country]).tolist()

    # Format DOB --------------------------------------------------------------
    
    # Separating age from date of birth
    age_regex = r'^(.*?)\s*\(age[ds]?\s+(\d+)\)'
    extracted = df['Date of birth (age)'].str.extract(age_regex)
    extracted.columns = ['Date of Birth', 'Age']

    # Glue the results back on (Nuclear Option to avoid that reindexing error)
    df = pd.concat([df.drop(columns=['Date of Birth', 'Age'], errors='ignore'), extracted], axis=1)

    # If 'Date of Birth' is null but the original column is NOT null
    # These are our 5 year-only rogues!
    rogue_mask = df['Date of Birth'].isna() & df['Date of birth (age)'].notna()

    # Standardize "Unknown" to actual NaNs so they are counted correctly
    df.loc[df['Date of birth (age)'].str.contains('Unknown', case=False, na=False), 'Date of birth (age)'] = np.nan

    # Add the filler date to only those 5 rows
    # We use .loc to safely update the values
    df.loc[rogue_mask, 'Date of Birth'] = df.loc[rogue_mask, 'Date of birth (age)'].astype(str) + "-01-01"
                                                                         
    # Converting date format for date of birth
    # Clean up any weird non-breaking spaces or hidden HTML artifacts
    df['Date of Birth'] = df['Date of Birth'].str.replace(r'\xa0', ' ', regex=True).str.strip()
    
    #  Convert date to datetime objects
    # 'errors=coerce' turns unparseable dates into NaT (Not a Time) instead of crashing
    df['Date of Birth'] = pd.to_datetime(df['Date of Birth'], errors='coerce', format='mixed')
    
    # Fill in the Blanks for "Day Month Year" (Ronaldo). This only touches rows that are still NaT (Not a Time)
    is_nat = df['Date of Birth'].isna()
    df.loc[is_nat, 'Date of Birth'] = pd.to_datetime(
        df.loc[is_nat, 'Date of birth (age)'].str.extract(r'^(.*?)\s*\(aged')[0], 
        dayfirst=True, errors='coerce')
    
    # Format Date as standard DB string (YYYY-MM-DD)
    df['Date of Birth'] = df['Date of Birth'].dt.strftime('%Y-%m-%d')
    
    # Failed date conversion check
    null_dates = df[df['Date of Birth'].isna()]
    if not null_dates.empty:
        print(f"Warning: {len(null_dates)} birthdates failed to convert in {edition}")
        #print(df.loc[null_dates.index, 'Date of birth (age)'])
        # Fill failed dated with None's
        df['Date of Birth'] = df['Date of Birth'].where(df['Date of Birth'].notna(), None)
        # Data validation check
        og_nulls = df['Date of birth (age)'].isna().sum()
        final_nulls = df['Date of Birth'].isna().sum()
        if og_nulls == final_nulls:
            print(f'Approved: All {final_nulls} failures are confirmed original missing values.')
        else: 
            print(f'Warning: Original {og_nulls} and final {final_nulls} nulls do not match.')
            print('Check for conversion mismatches for rogue entries.')

    # Drop original 'Date of Birth (age)' column
    df = df.drop(columns=['Date of birth (age)'])

    # Table formatting --------------------------------------------------------
    
    # Separating captain status from names
    captain_regex = r'\s\((?:c|captain)\)'
    df['Captain'] = df['Player'].str.contains(captain_regex, case=False, regex=True)
    df['Player'] = df['Player'].str.replace(captain_regex, '', case=False, regex=True)

    # Add tournament to every players' entry
    
    if year == 1930:
        df['Tournament'] = [edition]*(22*13-45) # 22 players * 13 teams - 45 absences
    elif year == 1934:
        df['Tournament'] = [edition]*(22*16-10) # 22 players * 16 teams - 10 absences
    elif year == 1938:
        df['Tournament'] = [edition]*(22*15-12) # 22 players * 15 teams - 12 absences
    elif year == 1950:
        df['Tournament'] = [edition]*(22*13-8) # 22 players * 13 teams - 8 absences
    elif year in teams16 and year not in [1954,1970]:
        df['Tournament'] = [edition]*(22*16) # 22 players * 16 teams
    elif year == 1954:
        df['Tournament'] = [edition]*(22*16-2) # 22 players * 16 teams - 2 absences
    elif year == 1970:
        df['Tournament'] = [edition]*(22*16-3) # 22 players * 16 teams - 3 absences
    elif year in teams24 and year not in [1982,1990]:
        df['Tournament'] = [edition]*(22*24) # 22 players * 24 teams
    elif year == 1982:
        df['Tournament'] = [edition]*(22*24-2) # 22 players * 24 teams - 2 absences
    elif year == 1990:
        df['Tournament'] = [edition]*(22*24+2) # 22 players * 24 teams + 2 replacements
    elif year in teams32 and year not in [1998,2022]:
        df['Tournament'] = [edition]*(23*32) # 23 players * 32 teams
    elif year == 1998:
        df['Tournament'] = [edition]*(22*32+1) # 22 players * 32 teams + 1 replacement
    elif year == 2022:
        df['Tournament'] = [edition]*(26*32-1) # 26 players * 32 teams - 1 drop

    # Add Goals column
    if year == 2018 or year == 2022:
        df['Goals'] = df['Goals'].astype('Int64')
    else:
        df['Goals'] = np.nan
        df['Goals'] = df['Goals'].astype('Int64')

    # Fix column order
    col_header = ['Tournament','Player','No.','Pos.','Captain','Club','Country','Caps','Date of Birth','Age','Goals']
    cols = [col for col in df.columns if col not in col_header]
    df = df[col_header + cols]

    if year <= 1950:
        # Replace NaN or empty strings in the 'No.' column with a dash
        df['No.'] = df['No.'].fillna('-').replace('', '-')
        # Normalize dashes
        df['No.'] = df['No.'].str.replace(r'[\u2212\u2013\u2014]', '-', regex = True)
    else: pass

    # Fix names with special characters or reference links
    df['Player'] = df['Player'].str.replace(r'\[[a-zA-Z0-9]+\]|[*.]', '', regex = True)

    # fix capitalization errors in Player
    corrections = {r'\bDe\b': 'de', r'\bVan Der\b': 'Van der'}
    for og, correction in corrections.items():
        df['Player'] = df['Player'].str.replace(og, correction, regex=True)

    # fix punctuation mistakes in Player
    df['Player'] = df['Player'].apply(strip_accents)

    # Fix mispelled names in Players
    fixes = {'Gary Stevens': 'Gary M Stevens',
             'Andre Vandewyer': 'Andre Vandeweyer',
             'Abdullah Zubromawi': 'Abdullah Sulaiman Zubromawi',
             'Jose Mari Bakero': 'Jose Maria Bakero',
             'Valery Karpin': 'Valeri Karpin',
             'Vladica Popovic': 'Vladimir Popovic'}
    df['Player'] = df['Player'].replace(fixes)

    # Correcting Caps
    df['Caps'] = df['Caps'].astype(str)
    df['Caps'] = df['Caps'].str.replace(r'[-?* ]|(\.0+)|\[[a-zA-Z0-9]\]', '', regex = True)
    df['Caps'] = df['Caps'].replace('', '0').fillna('0').astype(int)

    rosters_ds.append(df) # add df to the data set
       
def groups_scraper(matches_soup, year, edition, teams16, teams24, teams32, groups_ds): 

    # Import group tables
    tables = matches_soup.select('table.wikitable')
    table = [t for t in tables 
            if 'text-align:center' in str(t.get('style', '')).replace(' ', '')
            and 'Team' in t.get_text() and 'Qualification' in t.get_text() and 'Grp' not in t.get_text()]

    if year == 1950: # 1950 edition had a final group stage instead of a knockout round.
        df_groups = pd.concat(pd.read_html(StringIO(str(table)))) # create df for regular group stage
        df_groups = df_groups.rename(columns = {'Qualification': 'Result'}) # Rename column
        ftable = [t for t in tables 
            if 'text-align:center' in str(t.get('style', '')).replace(' ', '')
            and 'Team' in t.get_text() and 'Final result' in t.get_text() and 'Grp' not in t.get_text()]
        df_final = pd.concat(pd.read_html(StringIO(str(ftable)))) # create df for final stage
        df_final = df_final.rename(columns = {'Final result': 'Result'})
        wc1950 = [df_groups,df_final]
        df = pd.concat(wc1950, ignore_index=True) # concat both df's
    else: # Procedure for every other edition.
        df = pd.concat(pd.read_html(StringIO(str(table))))
        df = df.rename(columns = {'Qualification': 'Result'})

    # Add group to teams
    if year == 1930:
        Group = ['1','2','3','4']
        df['Group'] = np.repeat(Group, [4 if i == '1' else 3 for i in Group]).tolist()
    elif year == 1950:
        Group = ['1','2','3','4','Final']
        df['Group'] = np.repeat(Group, [3 if i == '3' else 2 if i == '4' else 4 for i in Group]).tolist()
    elif year in teams16 and year not in [1974,1978]:
        Group = ['1','2','3','4']
        df['Group'] = np.repeat(Group,4)
    elif year in [1974,1978]:
        group1 = ['1','2','3','4']
        Group1 = np.repeat(group1,4)
        group2 = ['A','B']
        Group2 = np.repeat(group2,4)
        df['Group'] = np.concat([Group1, Group2])
    elif year in teams24 and year not in [1982]:
        Group = ['A','B','C','D','E','F']
        df['Group'] = np.repeat(Group,4)
    elif year in [1982]:
        group1 = ['1','2','3','4','5','6']
        Group1 = np.repeat(group1,4)
        group2 = ['A','B','C','D']
        Group2 = np.repeat(group2,3)
        df['Group'] = np.concat([Group1, Group2])
    elif year in teams32:
        Group = ['A','B','C','D','E','F','G','H']
        df['Group'] = np.repeat(Group,4)
    
    # Add Tournament
    if year == 1930:
        df['Tournament'] = np.repeat(edition,13)
    elif year == 1950:
        df['Tournament'] = np.repeat(edition,17)
    elif year in teams16 and year not in [1974,1978]:
        df['Tournament'] = np.repeat(edition,16)
    elif year in [1974,1978]:
        df['Tournament'] = np.repeat(edition,24)
    elif year in teams24 and year != 1982:
        df['Tournament'] = np.repeat(edition,24)
    elif year == 1982:
        df['Tournament'] = np.repeat(edition,36)
    elif year in teams32:
        df['Tournament'] = np.repeat(edition,32)

    # Clean up information
    df.loc[df['Result'].isna(), 'Result'] = 'Eliminated' # Reformat 'Qualification' column
    df = df.rename(columns = {'Teamvte':'Team'}) # Rename Team column
    df['Team'] = df['Team'].str.replace(r'\s\([HC]\)', '', regex = True)

    # Some teams have a link clarifying qualification due to fair play points or . Info needs to
    # be appended to 'Qualification'
    if year <= 1970:
        df['Pts'] = df['Pts'].astype(str).str.replace(r'\s*\[a\]', '', regex=True).str.strip()
    else:
        fpp = df['Pts'].astype(str).str.contains(r'\[a\]', na=False)
        df.loc[fpp, 'Result'] = df.loc[fpp, 'Result'].astype(str) + ' (Fair Play Points)'
        df['Pts'] = df['Pts'].astype(str).str.replace(r'\s*\[a\]', '', regex=True).str.strip()
    
    # Format 'GD' column
    # Replace regex dashes with regular ones (-),strip plus signs (+), fill nulls with 0's, and convert to int.
    if year not in [1934,1938,1958,1962,1966]:
        df['GD'] = df['GD'].str.replace(r'[\u2212\u2013\u2014]', '-', regex = True)\
            .str.replace('+', '', regex=False).fillna(0).astype(int)
    else: df['GD'] = 0

    # Standardize 'Result' column
    standard = {
        'Advance to the knockout stage':'Advanced',
        'Advance to knockout stage':'Advanced',
        'Advanced to knockout stage':'Advanced',
        'Advance to second round':'Advanced',
        'Advance to final round':'Advanced',
        'Advance to match for third place':'Advanced',
        'Advance to final':'Advanced',
        'Advance to knockout stage (Fair Play Points)':'Advanced',
        'Eliminated (Fair Play Points)':'Eliminated',
        'Eliminated':'Eliminated',
        'Champions':'Champions'}

    df['Result'] = df['Result'].map(standard)

    # Add Stage column signaling when a second group stage was implemented.
    if year in [1950, 1974, 1978, 1982]:
        conditions = [df['Group'].astype(str).str.contains('[1-6]'),
                      df['Group'].astype(str).str.contains('[a-zA-Z]')]
        choices = [1,2]
        df['GSRound'] = np.select(conditions, choices)
    else:
        df['GSRound'] = [1] * len(df['Group'])

    # Reorganize df
    if year <= 1966 and year not in [1930,1950,1954]: # 1966 edition and some prior ones use GR (Goal Ratio) to decide point ties
        col_header = ['Tournament', 'Group','GSRound','Pos','Team','Pld','W','D','L','GF','GA','GR','Pts','Result']
    else: # Editions after 1966 use GD (Goal Difference) to decide point ties
        col_header = ['Tournament', 'Group','GSRound','Pos','Team','Pld','W','D','L','GF','GA','GD','Pts','Result']
    cols = [col for col in df.columns if col not in col_header]
    df = df[col_header + cols]

    groups_ds.append(df) # Add df to the data set"""

def matches_scraper(matches_soup, year, edition, teams16, teams24, teams32, matches_ds): 

    # Define lists
    Tournament = []
    HomeTeam = []
    Score = []
    HomeScore = []
    AwayScore = []
    AwayTeam = []
    ExtraTime = []
    GoldenGoal = []
    Penalties = []
    HomePKs = []
    AwayPKs = []
    Referee = []
    Venue = []
    City = []
    Attendance = []
    Date = []
    Time = []
    Stage = []
    Group = []    
    Winner = []

    # Group stage data scrap --------------------------------------------------

    if year == 1990: # Import tables containing all group matches data for 1990
        gs_matches = matches_soup.find_all('table', attrs = {
                                                'style':'width:100%',
                                                'cellspacing':'1'})
        for g in gs_matches:
            rows = g.find_all('tr')
            for row in rows:
                # Float date value (value is treated as a row avobe more than one match sometimes)
                if not row.get('style') and row.find('td'):
                    td_e = row.find('td')
                    date = td_e.text.strip()
                elif row.get('style') == "font-size:90%":
                    cells = row.find_all('td', recursive = False)
                    if len(cells) >= 4:
                        # Import date
                        Date.append(date)
                        # Import home team
                        td_a = row.find('td', align="right")
                        HomeTeam.append(td_a.find('a').text.strip() if td_a and td_a.find('a') else None)
                        # Import match score
                        td_b = row.find('td', align="center")
                        Score.append(td_b.find('b').text.strip() if td_b and td_b.find('b') else None)
                        # Import away team
                        td_c = cells[2]
                        AwayTeam.append(td_c.find('span').find('a').text.strip()
                                        if td_c.find('span') and td_c.find('span').find('a') else None)
                        # Import Venue
                        td_d = cells[3]
                        links = td_d.find_all('a')
                        concatenated_links = ", ".join([link.text.strip() for link in links])
                        Venue.append(concatenated_links)
                        # Add tournamen
                        Tournament.append(edition)
                        # No knockout stage game deciders on group stage
                        ExtraTime.append(False); GoldenGoal.append(False); Penalties.append(False); 
                        HomePKs.append(None); AwayPKs.append(None)
                        # Fill the coluimns with no data with empty values
                        Referee.append(None); Attendance.append(None); Time.append(None); Winner.append(None)
                        # Add match stage
                        Stage.append('Group Stage')
                        # Add Group game was played on
                        group = (['A']*6+['B']*6+['C']*6+['D']*6+['E']*6+['F']*6)[len(Stage)-1]
                        Group.append(group)
        # Fill Home and Away scores
        for i in Score: HomeScore.append(i[0]); AwayScore.append(i[2])
    else: pass
    
    match_info = matches_soup.find_all('div', attrs = {'itemscope': True, 
                                       'itemtype': 'http://schema.org/SportsEvent',
                                       'class': 'footballbox'})

    # Import data from footballbox tables
    # Path: div -> tr -> th -> span -> a
    for match in match_info:

        # Create tournament column
        Tournament.append(edition)

        # Import home team
        home_team = match.select_one('th.fhome')
        HomeTeam.append(home_team.get_text(" ", strip = True))

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
        away_team = match.select_one('th.faway')
        AwayTeam.append(away_team.get_text(" ", strip = True))

        # Import dates
        date = match.select_one('div.fleft div.fdate')
        Date.append(date.get_text(strip = True))

        # Import time
        if 'w/o' in score_text:
            Time.append(np.nan)
        else:
            time = match.select_one('div.fleft div.ftime')
            if time:
                Time.append(time.get_text(strip = True)[:5])
            else:
                Time.append(np.nan)

        # Import Attendance
        if 'w/o' in score_text:
            crowd = Attendance.append(np.nan)
        else:
            crowd = match.select_one('div.fright div:nth-of-type(2)')
            if crowd:
                Attendance.append(crowd.get_text(strip = True).replace('Attendance: ', ''))
            else:
                Attendance.append(np.nan)

        # Import referee
        if 'w/o' in score_text:
            Referee.append(np.nan)
        else:
            ref = match.select_one('div.fright div:nth-of-type(3)')
            if ref:
                raw_text = ref.get_text(strip=True)
                clean_name = re.sub(r'^(Referee|Ref):\s*', '', raw_text, flags=re.IGNORECASE)
                clean_name = re.sub(r'\s*\(.*\)', '', clean_name).strip()
                Referee.append(clean_name)
            else:
                Referee.append(np.nan)

        # Import venue and city
        place = match.select_one('div.fright div[itemprop="location"] span')
        location = place.find_all('a')
        if len(location) >= 2:
            Venue.append(location[0].get_text(strip = True))
            City.append(location[1].get_text(strip = True))
        elif year == 1930:
            Venue.append(location[0].get_text(strip = True))
            City.append('Montevideo')
        else:
            Venue.append(location[0].get_text(strip = True)) if location else np.nan
            City.append(np.nan)

        # Add match stage
        if year == 1930:
            if len(Stage) < 15: Stage.append('Group Stage')
            elif len(Stage) < 17: Stage.append('Semi-finals')
            else: Stage.append('Final')
        elif year == 1934:
            if len(Stage) < 8: Stage.append('Round of 16')
            elif len(Stage) < 12: Stage.append('Quarter-finals')
            elif len(Stage) == 12: Stage.append('QF Replay')
            elif len(Stage) < 15: Stage.append('Semi-finals')
            elif len(Stage) == 15: Stage.append('Thirs Place Match')
            else: Stage.append('Final')
        elif year == 1938:
            if len(Stage) < 8: Stage.append('Round of 16')
            elif len(Stage) < 10: Stage.append('R16 Replay')
            elif len(Stage) < 14: Stage.append('Quarter-finals')
            elif len(Stage) < 15: Stage.append('QF Replay')
            elif len(Stage) < 17: Stage.append('Semi-finals')
            elif len(Stage) == 17: Stage.append('Third Place Match')
            else: Stage.append('Final')
        elif year == 1950:
            if len(Stage) < 16: Stage.append('Group Stage')
            else: Stage.append('Final Stage')
        elif year in teams16 and year not in [1954,1958,1974,1978]:
            if len(Stage) < 24: Stage.append('Group Stage')
            elif len(Stage) < 28: Stage.append('Quarter-finals')
            elif len(Stage) < 30: Stage.append('Semi-finals')
            elif len(Stage) == 30: Stage.append('Third Place Match')
            else: Stage.append('Final')
        elif year == 1954:
            if len(Stage) < 18: Stage.append('Group Stage')
            elif len(Stage) < 22: Stage.append('Quarter-finals')
            elif len(Stage) < 24: Stage.append('Semi-finals')
            elif len(Stage) == 24: Stage.append('Third Place Match')
            else: Stage.append('Final')
        elif year == 1958:
            if len(Stage) < 27: Stage.append('Group Stage')
            elif len(Stage) < 31: Stage.append('Quarter-finals')
            elif len(Stage) < 33: Stage.append('Semi-finals')
            elif len(Stage) == 33: Stage.append('Third Place Match')
            else: Stage.append('Final')
        elif year in [1974,1978]:
            if len(Stage) < 24: Stage.append('Group Stage 1')
            elif len(Stage) < 36: Stage.append('Group Stage 2')
            elif len(Stage) == 36: Stage.append('Third Place Match')
            else: Stage.append('Final')
        elif year in teams24 and year not in [1982,1990]:
            if len(Stage) < 36: Stage.append('Group Stage')
            elif len(Stage) < 44: Stage.append('Round of 16')
            elif len(Stage) < 48: Stage.append('Quarter-finals')
            elif len(Stage) < 50: Stage.append('Semi-finals')
            elif len(Stage) == 50: Stage.append('Third Place Match')
            else: Stage.append('Final')
        elif year == 1982:
            if len(Stage) < 36: Stage.append('Group Stage 1')
            elif len(Stage) < 48: Stage.append('Group Stage 2')
            elif len(Stage) < 50: Stage.append('Semi-finals')
            elif len(Stage) == 50: Stage.append('Third Place Match')
            else: Stage.append('Final')
        elif year == 1990:
            if len(Stage) < 36: Stage.append('Group Stage')
            elif len(Stage) < 44: Stage.append('Round of 16')
            elif len(Stage) < 48: Stage.append('Quarter-finals')
            elif len(Stage) < 50: Stage.append('Semi-finals')
            elif len(Stage) == 50: Stage.append('Third Place Match')
            else: Stage.append('Final')
        elif year in teams32:
            if len(Stage) < 48: Stage.append('Group Stage')
            elif len(Stage) < 56: Stage.append('Round of 16')
            elif len(Stage) < 60: Stage.append('Quarter-finals')
            elif len(Stage) < 62: Stage.append('Semi-finals')
            elif len(Stage) == 62: Stage.append('Third Place Match')
            else: Stage.append('Final')

        # Add group the game was played in
        if year == 1930:
            if len(Group) < 6: Group.append('1')
            elif len(Group) < 9: Group.append('2')
            elif len(Group) < 12: Group.append('3')
            elif len(Group) < 15: Group.append('4')
            else: Group.append(np.nan)
        elif year in [1934,1938]:
            Group.append(np.nan)
        elif year == 1950:
            if len(Group) < 6: Group.append('1')
            elif len(Group) < 12: Group.append('2')
            elif len(Group) < 15: Group.append('3')
            elif len(Group) == 15: Group.append('4')
            elif len(Group) > 15: Group.append('Final')
        elif year in teams16 and year not in [1954,1958,1974,1978]:
            if len(Group) < 6: Group.append('1')
            elif len(Group) < 12:  Group.append('2')
            elif len(Group) < 18: Group.append('3')
            elif len(Group) < 24: Group.append('4')
            else: Group.append(np.nan)
        elif year == 1954:
            if len(Group) < 4: Group.append('1')
            elif len(Group) < 8:  Group.append('2')
            elif len(Group) == 8:  Group.append('2 Play-off')
            elif len(Group) < 13: Group.append('3')
            elif len(Group) < 17: Group.append('4')
            elif len(Group) == 17: Group.append('4 Play-off')
            else: Group.append(np.nan)
        elif year == 1958:
            if len(Group) < 6: Group.append('1')
            elif len(Group) == 6: Group.append('1 Play-off')
            elif len(Group) < 13:  Group.append('2')
            elif len(Group) < 19: Group.append('3')
            elif len(Group) == 19: Group.append('3 Play-off')
            elif len(Group) < 26: Group.append('4')
            elif len(Group) == 26: Group.append('4 Play-off')
            else: Group.append(np.nan)
        elif year in [1974,1978]:
            if len(Group) < 6: Group.append('1')
            elif len(Group) < 12:  Group.append('2')
            elif len(Group) < 18: Group.append('3')
            elif len(Group) < 24: Group.append('4')
            elif len(Group) < 30: Group.append('A')
            elif len(Group) < 36: Group.append('B')
            else: Group.append(np.nan)
        elif year in teams24 and year not in [1982]:
            if len(Group) < 6: Group.append('A')
            elif len(Group) < 12:  Group.append('B')
            elif len(Group) < 18: Group.append('C')
            elif len(Group) < 24: Group.append('D')
            elif len(Group) < 30: Group.append('E')
            elif len(Group) < 36: Group.append('F')
            else: Group.append(np.nan)
        elif year == 1982:
            if len(Group) < 6: Group.append('1')
            elif len(Group) < 12:  Group.append('2')
            elif len(Group) < 18: Group.append('3')
            elif len(Group) < 24: Group.append('4')
            elif len(Group) < 30: Group.append('5')
            elif len(Group) < 36: Group.append('6')
            elif len(Group) < 39: Group.append('A')
            elif len(Group) < 42: Group.append('B')
            elif len(Group) < 45: Group.append('C')
            elif len(Group) < 48: Group.append('D')
            else: Group.append(np.nan)
        elif year in teams32:
            if len(Group) < 6: Group.append('A')
            elif len(Group) < 12:  Group.append('B')
            elif len(Group) < 18: Group.append('C')
            elif len(Group) < 24: Group.append('D')
            elif len(Group) < 30: Group.append('E')
            elif len(Group) < 36: Group.append('F')
            elif len(Group) < 42: Group.append('G')
            elif len(Group) < 48: Group.append('H')
            else: Group.append(np.nan)
            
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
        'HomeTeam': HomeTeam,
        'AwayTeam': AwayTeam,
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
        'Venue': Venue,
        'City': City,
        'Attendance': Attendance,
        'Date': Date,
        'Time': Time,
    }

    # Turn dictionary into dataframe
    df = pd.DataFrame.from_dict(df)

    # Fill up winner column ---------------------------------------------------
    conditions = [
    (df['HomeScore'] > df['AwayScore']),
    (df['AwayScore'] > df['HomeScore']),
    (df['Penalties'] & (df['HomePKs'] > df['AwayPKs'])),
    (df['Penalties'] & (df['AwayPKs'] > df['HomePKs']))]

    # Choices
    choices = [df['HomeTeam'], df['AwayTeam'], df['HomeTeam'], df['AwayTeam']]

    # Fill the winner column, default to 'Draw'
    df['Winner'] = np.select(conditions, choices, default='Draw')
    # 1938 contains a 'walkover' game. There was no winner because there was no game.
    df.loc[df['Score'].str.contains('w/o', case=False, na=False), 'Winner'] = np.nan

    # Format df ---------------------------------------------------------------

    # Clean UNIX characters from Time column
    df['Time'] = df['Time'].str.replace(r'\u00a0', '', regex = True)

    # Clean Attendance references and Score dashes
    df['Attendance'] = df['Attendance'].str.replace(r'\[\d+\]', '', regex=True).str.strip()
    df['Score'] = df['Score'].str.replace(r'[\u2013\u2014]', '-', regex = True)

    # Remove commas from Attendance column
    df['Attendance'] = df['Attendance'].str.replace(',','').fillna(0).astype(int)

    # Removes the hidden ISO date metadata: (1954-07-04)
    df['Date'] = df['Date'].str.replace(r'\(\d{4}-\d{2}-\d{2}\)', '', regex=True).str.strip()

    # Also, handle that '&nbsp;' (non-breaking space) which often shows up as '\xa0'
    df['Date'] = df['Date'].str.replace(r'\xa0', ' ', regex=True)

    #  Convert date to datetime objects
    # 'errors=coerce' turns unparseable dates into NaT (Not a Time) instead of crashing
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    # Format Date as standard DB string (YYYY-MM-DD)
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

    # failed date conversion check
    null_dates = df[df['Date'].isna()]
    if not null_dates.empty:
        print(f"Warning: {len(null_dates)} dates failed to convert in {edition}")

    matches_ds.append(df) # Add df to the data set
    
def to_csv(rosters_ds, groups_ds, matches_ds, tournament_df, teams_df, players_df):

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
    
    # Save master tables if they exist
    if isinstance(tournament_df,list) and not tournament_df: pass
    else:
        tournament_df.to_csv(os.path.join(csv_path,'FIFA_wc_tournaments_master.csv'),
                        index = False, encoding = 'utf-8-sig')
    if isinstance(teams_df,list) and not teams_df: pass
    else:
        teams_df.to_csv(os.path.join(csv_path,'FIFA_wc_teams_master.csv'),
                        index = False, encoding = 'utf-8-sig')
    if isinstance(players_df,list) and not players_df: pass
    else:
        players_df.to_csv(os.path.join(csv_path,'FIFA_wc_players_master.csv'),
                        index = False, encoding = 'utf-8-sig')
        
    print('Saved')

def read_csv_data(rosters_ds, groups_ds, matches_ds, tournament_df, teams_df, players_df):

    # Define path where to grab the csv's from
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_folder = 'csv_files'
    csv_path = os.path.join(script_dir, csv_folder)

    rosters_ds = pd.read_csv(os.path.join(csv_path,'FIFA_wc_players.csv'))
    groups_ds = pd.read_csv(os.path.join(csv_path,'FIFA_wc_groups.csv'))
    matches_ds = pd.read_csv(os.path.join(csv_path,'FIFA_wc_matches.csv'))

    tournament_df = pd.read_csv(os.path.join(csv_path,'FIFA_wc_tournaments_master.csv'))
    teams_df = pd.read_csv(os.path.join(csv_path,'FIFA_wc_teams_master.csv'))
    players_df = pd.read_csv(os.path.join(csv_path,'FIFA_wc_players_master.csv'))

    print('csv files loaded')

    return rosters_ds, groups_ds, matches_ds, tournament_df, teams_df, players_df

def build_db_schema(rosters_ds, groups_ds, matches_ds, wc_editions, tournament_df, teams_df, players_df):

    print('Creating database schema...')

    # Build tournaments table -------------------------------------------------

    tournament_id = []
    tournament = []
    year = []
    host = []

    for edition in wc_editions:
        # Create IDs off the edition names
        tournament_id.append(f'{edition[:3].upper()}-{edition[-2:]}')
        # Enter corresponding edition name (For mapping purposes. Will be deleted later)
        tournament.append(edition)
        # Isolate edition years
        year.append(edition[-4:])
        # Isolate host
        host.append(edition[:-5])

    tournament_df= {'Tournament_ID': tournament_id,
                    'Tournament': tournament,
                    'Year': year,
                    'Host': host}

    # Turn dictionary into dataframe
    tournament_df = pd.DataFrame.from_dict(tournament_df)

    # print(tournament_df.head(10))
    
    # Build teams table -------------------------------------------------------

    team_id = []

    # Extract teams from groups_ds
    unique_teams = groups_ds['Team'].unique().tolist() 
    unique_teams.sort()

    for team in unique_teams:
        # Create IDs off country names
        team_id.append(team[:3].upper())
    
    # Check if any names look like structural junk instead of countries
    for team in unique_teams:
        if len(team) < 2:
            print(f"Warning: Potential junk data found: {team}")

    teams_df = {'Team_ID': team_id,
                'Team': unique_teams}

    teams_df = pd.DataFrame.from_dict(teams_df)

    # Cuba and Dutch East Indies are excluded due to 1938 (their only
    # participation) did not include a group stage.
    # Adding also a match draw entry to prevent foreign key violations.
    missing_teams = pd.DataFrame([
        {'Team': 'Cuba', 'Team_ID': 'CUB'},
        {'Team': 'Dutch East Indies', 'Team_ID': 'DEI'},
        {'Team': 'China PR', 'Team_ID': 'CPR'},
        {'Team': 'Match Drawn', 'Team_ID': 'Draw'}])
    
    teams_df = pd.concat([teams_df, missing_teams], ignore_index=True)

    # Correct conflicting Team_IDs
    corrections = {
        'Austria': 'AUT',
        'China': 'CHN',
        'Czech Republic': 'CZR',
        'Iraq': 'IRQ',
        'North Korea': 'NKO',
        'Northern Ireland': 'NIR',
        'Serbia and Montenegro': 'SAM',
        'Slovenia': 'SLN',
        'Slovakia': 'SLK',
        'South Africa': 'RSA',
        'South Korea': 'SKO',
        'United Arab Emirates': 'UAE',
        'United States': 'USA',
        'El Salvador': 'SAL',
        'FR Yugoslavia': 'FRY'}
    
    teams_df['Team_ID'] = teams_df['Team'].map(corrections).fillna(teams_df['Team_ID'])

    #with pd.option_context('display.max_rows', None, 'display.max_columns', None):
    #    print(teams_df)

    # Build players table -----------------------------------------------------

    columns_to_extract = ['Player', 'Country', 'Date of Birth']
    
    # Create dataframe based on extracted columns
    players_df = rosters_ds[columns_to_extract].drop_duplicates(subset = ['Player', 'Date of Birth']).copy()

    # Sort by country
    players_df = players_df.sort_values(by = 'Country', ascending = True)

    # print(f"Total unique players extracted: {len(players_df)}")
    # print(players_df.head(10))

    # generate player_id
    players_df['Player_ID'] = players_df.apply(create_player_id, axis = 1)

    # Duplicate player_id check
    duplicate_mask = players_df.duplicated(subset=['Player_ID'], keep=False)
    duplicates = players_df[duplicate_mask].sort_values(by='Player_ID')
    print(f"FOUND {duplicates['Player_ID'].nunique()} UNIQUE COLLIDING ID GROUPS ({len(duplicates)} TOTAL ROWS):")
    """print("="*60)
    for pid, group in duplicates.groupby('Player_ID'):
        print(f"\nColliding ID Key: '{pid}'")
        for idx, row in group.iterrows():
            # Prints name, country, and full Date of Birth to see if the dates differ slightly
            print(f"  -> Player: {row['Player']} | Country: {row['Country']} | DOB: {row['Date of Birth']}")
    print("="*60 + "\n")"""

    # Sort by country
    players_df = players_df.sort_values(by='Country')

    # Reset index
    players_df = players_df.reset_index(drop = True)

    # print("Player Master Table with IDs:")
    # print(players_df[['Player_ID', 'Player', 'Country']].head(10))

    # Map IDs onto groups_ds, rosters_ds, and matches_ds ----------------------

    # == matches_ds ==

    # Create match_ID column
    matches_ds['Match_ID'] = list(range(len(matches_ds['Tournament'])))

    # Map Tournament_ID
    matches_ds = matches_ds.merge(
        tournament_df[['Tournament_ID', 'Tournament']],
        on = 'Tournament',
        how = 'left')

    # Map HomeTeam_ID
    matches_ds = matches_ds.merge(
        teams_df[['Team_ID', 'Team']],
        left_on = 'HomeTeam', right_on = 'Team',
        how = 'left'
    ).rename(columns = {'Team_ID': 'HomeTeam_ID'})

    # Map AwayTeam_ID
    matches_ds = matches_ds.merge(
        teams_df[['Team_ID', 'Team']],
        left_on = 'AwayTeam', right_on = 'Team',
        how = 'left'
    ).rename(columns = {'Team_ID': 'AwayTeam_ID'})

    # Map WinnerTeam_ID
    matches_ds = matches_ds.merge(
        teams_df[['Team_ID', 'Team']],
        left_on = 'Winner', right_on = 'Team',
        how = 'left'
    ).rename(columns = {'Team_ID': 'Winner_ID'})

    # Force Winner and Winner_ID to be NaN for walkover matches
    matches_ds.loc[matches_ds['HomeScore'].isnull() & matches_ds['AwayScore'].isnull(), ['Winner', 'Winner_ID']] = np.nan

    # If Winner_ID is null and the game has a score (not a walkover), set ID to 'DRAW'
    matches_ds.loc[matches_ds['Winner_ID'].isnull() & matches_ds['HomeScore'].notnull(), 'Winner_ID'] = 'DRAW'

    # Extra columns cleanup
    matches_ds = matches_ds.drop(columns=['Team_x','Team_y','Team'])

    # print(matches_ds.head(5))

    # == groups_ds ==

    # Map Tournament_ID
    groups_ds = groups_ds.merge(
        tournament_df[['Tournament_ID', 'Tournament']],
        on = 'Tournament',
        how = 'left')
    
    # Map Team_ID
    groups_ds = groups_ds.merge(
        teams_df[['Team_ID', 'Team']],
        on = 'Team',
        how = 'left')
    
    # Create match_ID column
    groups_ds['Group_ID'] = list(range(len(groups_ds['Tournament'])))

    # == rosters_ds ==

    # Map Tournament_ID
    rosters_ds = rosters_ds.merge(
        tournament_df[['Tournament_ID', 'Tournament']],
        on = 'Tournament',
        how = 'left')
    
    # Map Team_ID
    rosters_ds = rosters_ds.merge(
        teams_df[['Team_ID', 'Team']],
        left_on = 'Country', right_on = 'Team',
        how = 'left')
    
    # Map Player_ID
    rosters_ds = rosters_ds.merge(
        players_df[['Player_ID', 'Player', 'Date of Birth']],
        on = ['Player', 'Date of Birth'],
        how = 'left')
    
    # Remove any duplicates
    rosters_ds = rosters_ds.drop_duplicates(subset=['Player_ID', 'Tournament_ID'])

    # Reorganize and clean data frames ----------------------------------------

    # Remove extra columns in rosters_ds
    rosters_ds = rosters_ds.drop(columns=['Team'])

    # Remove extra column in tournament_df
    tournament_df = tournament_df.drop(columns=['Tournament'])

    # Fix column order of matches_ds
    cols = ['Match_ID','Tournament_ID', 'HomeTeam_ID', 'AwayTeam_ID', 'Winner_ID'] + [c for c in matches_ds if 'ID' not in c]
    matches_ds = matches_ds[cols]

    # Fix column order of groups_ds
    cols = ['Group_ID','Team_ID','Tournament_ID'] + [c for c in groups_ds if 'ID' not in c]
    groups_ds = groups_ds[cols]

    # Fix column order of rosters_ds
    cols = ['Player_ID','Team_ID','Tournament_ID'] + [c for c in rosters_ds if 'ID' not in c]
    rosters_ds = rosters_ds[cols]

    return rosters_ds, groups_ds, matches_ds, tournament_df, teams_df, players_df

def create_player_id(row):

    # Clean and split the name
    name = str(row['Player']).strip()
    parts = name.split()
    
    # Determine First and Last name parts
    # If there's only one name ('Eusebio'), treat it as the first name
    if len(parts) > 1:
        first_name = parts[0]
        last_name = parts[-1]
    else:
        first_name = parts[0]
        last_name = ""
        
    # Extract the year from the 'Date of Birth' string (assuming YYYY-MM-DD)
    dob = str(row['Date of Birth']).replace('-', '')

    # Extract country
    country = str(row['Country'])
    
    # Construct the ID: 3 chars Country, 4 chars Last (if exists), 4 chars First, then -YYYY
    id_str = f"{country[:3].upper()}-{last_name[:4].upper()}{first_name[:4].upper()}-{dob}"
    
    return id_str

def strip_accents(text):
    if not isinstance(text, str):
        return text
    # Normalize to decomposition form and filter out the accent markings
    normalized = unicodedata.normalize('NFKD', text)
    return "".join([c for c in normalized if not unicodedata.combining(c)])

def to_sql(rosters_ds, groups_ds, matches_ds, tournament_df, teams_df, players_df):

    db_name = 'FIFAWCDB'
    server = # Enter server name
    metadata_obj = sa.MetaData()

    master_url = f'mssql+pyodbc://@{server}/master?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
    engine = sa.create_engine(master_url, isolation_level='AUTOCOMMIT')

    with engine.connect() as conn: # Connect to the server
        print('Connection Secured...')

        # Create db
        conn.execute(sa.text(
            f'DROP DATABASE IF EXISTS {db_name}; CREATE DATABASE {db_name}'
        )) 
        print(f'Database {db_name} created...')

    db_url = f'mssql+pyodbc://@{server}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
    engine = sa.create_engine(db_url)

    # Create master tournaments table
    tournaments_mt = sa.Table('Tournaments_Master', metadata_obj,
        sa.Column('Tournament_ID', sa.CHAR(6), primary_key = True),
        sa.Column('Year', sa.INT, nullable = False),
        sa.Column('Host', sa.VARCHAR(20), nullable = False))
    print('Tournaments_Master table created...')

    # Create master teams table
    teams_mt = sa.Table('Teams_Master', metadata_obj,
        sa.Column('Team_ID', sa.VARCHAR(4), primary_key = True),
        sa.Column('Team', sa.VARCHAR(30), nullable = False))
    print('Teams_Master table created...')
    
    # Create master players table
    players_mt = sa.Table('Players_Master', metadata_obj,
        sa.Column('Player_ID', sa.VARCHAR(30), primary_key = True),            
        sa.Column('Player', sa.VARCHAR(100), nullable = False),
        sa.Column('Country', sa.VARCHAR(30), nullable = False),
        sa.Column('Date of Birth', sa.DATE, nullable = True))
    print('Players_Master table created...')

    #"""# Create main rosters table
    rosters = sa.Table('Rosters',metadata_obj,
        sa.Column('Player_ID', sa.VARCHAR(30), sa.ForeignKey(players_mt.c.Player_ID), primary_key=True),
        sa.Column('Tournament_ID', sa.CHAR(6), sa.ForeignKey(tournaments_mt.c.Tournament_ID), primary_key=True),
        sa.Column('Team_ID', sa.VARCHAR(4), sa.ForeignKey(teams_mt.c.Team_ID)),
        sa.Column('Tournament', sa.VARCHAR(30), nullable = False),
        sa.Column('Player', sa.VARCHAR(100), nullable = False),
        sa.Column('No.', sa.VARCHAR(3), nullable = False),
        sa.Column('Pos.', sa.CHAR(2), nullable = False),
        sa.Column('Captain', sa.VARCHAR(5), nullable = False),
        sa.Column('Club', sa.VARCHAR(100), nullable = False),
        sa.Column('Country', sa.VARCHAR(30), nullable = False),
        sa.Column('Caps', sa.INTEGER, nullable = False),
        sa.Column('Date of Birth', sa.DATE, nullable = True),
        sa.Column('Age', sa.INTEGER, nullable = True),
        sa.Column('Goals', sa.INTEGER, nullable = True))
    print('Rosters table created...')

    # Create main matches table
    matches = sa.Table('Matches', metadata_obj,
        sa.Column('Match_ID', sa.INTEGER, primary_key = True, autoincrement = False),
        sa.Column('Tournament_ID', sa.CHAR(6), sa.ForeignKey(tournaments_mt.c.Tournament_ID)),
        sa.Column('HomeTeam_ID', sa.VARCHAR(4), sa.ForeignKey(teams_mt.c.Team_ID)),
        sa.Column('AwayTeam_ID', sa.VARCHAR(4), sa.ForeignKey(teams_mt.c.Team_ID)),
        sa.Column('Winner_ID', sa.VARCHAR(4), sa.ForeignKey(teams_mt.c.Team_ID)),
        sa.Column('Tournament', sa.VARCHAR(30), nullable = False),
        sa.Column('Stage', sa.VARCHAR(20), nullable = False),
        sa.Column('Group', sa.VARCHAR(10), nullable = True),
        sa.Column('HomeTeam', sa.VARCHAR(30), nullable = False),
        sa.Column('AwayTeam', sa.VARCHAR(30), nullable = False),
        sa.Column('Score', sa.VARCHAR(30), nullable = False),
        sa.Column('HomeScore', sa.INTEGER, nullable = True),
        sa.Column('AwayScore', sa.INTEGER, nullable = True),
        sa.Column('ExtraTime', sa.VARCHAR(5), nullable = True),
        sa.Column('GoldenGoal', sa.VARCHAR(5), nullable = False),
        sa.Column('Penalties', sa.VARCHAR(5), nullable = True),
        sa.Column('HomePKs', sa.INTEGER, nullable = True),
        sa.Column('AwayPKs', sa.INTEGER, nullable = True),
        sa.Column('Winner', sa.VARCHAR(30), nullable = True),
        sa.Column('Referee', sa.VARCHAR(50), nullable = True),
        sa.Column('Venue', sa.VARCHAR(100), nullable = True),
        sa.Column('City', sa.VARCHAR(100), nullable = True),
        sa.Column('Attendance', sa.INTEGER, nullable = True),
        sa.Column('Date', sa.DATE, nullable = False),
        sa.Column('Time', sa.TIME, nullable = True))
    print('Matches table created...')

    # Create main groups table
    groups = sa.Table('Groups', metadata_obj,
        sa.Column('Group_ID', sa.INTEGER, primary_key = True, autoincrement = False),
        sa.Column('Team_ID', sa.VARCHAR(4), sa.ForeignKey(teams_mt.c.Team_ID)),
        sa.Column('Tournament_ID', sa.CHAR(6), sa.ForeignKey(tournaments_mt.c.Tournament_ID)),
        sa.Column('Tournament', sa.VARCHAR(30), nullable = False),
        sa.Column('Group', sa.VARCHAR(5), nullable = False),
        sa.Column('GSRound', sa.CHAR(1), nullable = False),
        sa.Column('Pos', sa.INTEGER, nullable = False),
        sa.Column('Team', sa.VARCHAR(30), nullable = False),
        sa.Column('Pld', sa.INTEGER, nullable = False),
        sa.Column('W', sa.INTEGER, nullable = False),
        sa.Column('D', sa.INTEGER, nullable = False),
        sa.Column('L', sa.INTEGER, nullable = False),
        sa.Column('GF', sa.INTEGER, nullable = False),
        sa.Column('GA', sa.INTEGER, nullable = False),
        sa.Column('GD', sa.INTEGER, nullable = False),
        sa.Column('Pts', sa.INTEGER, nullable = False),
        sa.Column('Result', sa.VARCHAR(50), nullable = False),
        sa.Column('GR', sa.VARCHAR(10), nullable = True))
    print('Groups table created...')

    metadata_obj.create_all(engine)

    # Load master tournaments data to SQL Server
    tournament_df.to_sql('Tournaments_Master', engine, if_exists = 'append', index = False)
    print('Tournaments_Master data processed...')

    # Load master teams data to SQL Server
    teams_df.to_sql('Teams_Master', engine, schema = 'dbo', if_exists = 'append', index = False)
    print('Teams_Master data processed...')

    # Load master players data to SQL Server
    players_df.to_sql('Players_Master', engine, schema = 'dbo', if_exists = 'append', index = False)
    print('Players_Master data processed...')

    # Load rosters data to SQL Server
    rosters_ds.to_sql('Rosters', engine, schema = 'dbo', if_exists = 'append', index = False)
    print('Rosters data processed...')

    # Load matches data to SQl server
    matches_ds.to_sql('Matches', engine, schema = 'dbo', if_exists = 'append', index = False)
    print('Matches data processed...')

    # Load groups data to SQL sever.
    groups_ds.to_sql('Groups', engine, schema = 'dbo', if_exists = 'append', index = False)
    print('Groups data processed...')

main()
