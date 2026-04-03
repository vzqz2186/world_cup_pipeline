"""
FIFA World Cup data scraper

     Author: Daniel Vazquez

      To do: > Add '50 edition
             > Test all functions work:
               - roster_scraper:  []
               - groups_scraper:  []
               - matches_scraper: []
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

def main(): # -----------------------------------------------------------------
    
    # Define lists to store dataframes
    rosters_ds = []
    groups_ds = []
    matches_ds = []

    # Define list to iterate through tournament editions
    years = [y for y in range(1954,2023,4) if y not in [1942,1946]] # [1954]
    wc_editions = ['Switzerland 1954','Sweden 1958','Chile 1962','England 1966','Mexico 1970','West Germany 1974','Argentina 1978',
                   'Spain 1982','Mexico 1986','Italy 1990','USA 1994','France 1998','Korea/Japan 2002','Germany 2006','South Africa 2010',
                   'Brazil 2014','Russia 2018','Quatar 2022']
    #  []

    # Define eras by qualifying team quantity
    teams32_era = [y for y in range(1998, 2023, 4)] 
    teams24_era = [y for y in range(1982, 1995, 4)] 
    teams16_era = [y for y in range(1954, 1979, 4)] 

    # Scrapping tournament data ----------------------------------------

    for year, edition in zip(years, wc_editions):
        
        squads_soup, matches_soup = get_data(year, edition)

        roster_scraper(squads_soup, year, edition, teams16_era, teams24_era, teams32_era, rosters_ds)    
        groups_scraper(matches_soup, year, edition, teams16_era, teams24_era, teams32_era, groups_ds)
        matches_scraper(matches_soup, year, edition, teams16_era, teams24_era, teams32_era, matches_ds)

    # Combine all df's --------------------------------------------------------

    rosters_ds = pd.concat(rosters_ds)
    groups_ds = pd.concat(groups_ds)
    matches_ds = pd.concat(matches_ds)
    print('Data sets complete.')
    #print(matches_ds) # rosters_ds, groups_ds, 

    save_to_csv(rosters_ds, groups_ds, matches_ds) # Save data sets to .csv's
    
def get_data(year, edition): # ------------------------------------------------------

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

def roster_scraper(squads_soup, year, edition, teams16_era, teams24_era, teams32_era, rosters_ds): 

    # Scrapping player data ---------------------------------------------------

    # Import rosters
    tables = squads_soup.select('table.sortable.wikitable.plainrowheaders')
    rosters = pd.read_html(StringIO(str(tables))) # Create list of dataframes (df)

    # 2002 page has reference tags on the headers that need to be removed
    if year == 2002:
        for i in rosters:
            i.columns = [re.sub(r'\[\d+\]','', col) for col in i.columns]

    df = pd.concat(rosters) # Merge all df's in 'rosters' list into one df
    #print(df)"""

    # Import player nationalities ---------------------------------------------

    Country = [] # Participating countries

    countries = squads_soup.find_all('h3')

    # Import countries
    for i in countries:
        a = i.get_text()
        it = a.replace('[edit]', '')
        Country.append(it)

    # Removing unnecessary data
    if year == 1994: Country = Country[:-2]
    elif year in [2010, 2018, 2002]: Country = Country[:-5]
    elif year == 2006: Country = Country[:-1]
    elif year == 2014: Country = Country[:-4]
    elif year == 2022: Country = Country[:-7]
    elif year in [1998, 1990]: Country = Country[:-3]
    
    #print(Country)
    
    # Add players' nationalities
    if year in teams24_era and year not in [1982,1990] or year in teams16_era and year not in [1954,1970]: # 22 players per team.
        df['Country'] = np.repeat(Country, 22).tolist()
    elif year == 1954:
        df['Country'] = np.repeat(Country, [20 if i in ['South Korea'] else 22 for i in Country]).tolist()
    elif year == 1970: # 22 players per team. Morocco presented 19
        df['Country'] = np.repeat(Country, [19 if i in ['Morocco'] else 22 for i in Country]).tolist()
    elif year == 1982: # 22 players per team. El Salvador presented 20
        df['Country'] = np.repeat(Country, [20 if i in ['El Salvador'] else 22 for i in Country]).tolist()
    elif year == 1990: # 22 players per team. England and Argentina replaced a player (injury)
        df['Country'] = np.repeat(Country, [23 if i in ['England','Argentina'] else 22 for i in Country]).tolist()
    elif year in teams32_era and year not in [1998, 2022]: # 23 players per team.
        df['Country'] = np.repeat(Country, 23).tolist()
    elif year == 1998: # 22 players per team. South Africa presented 23 due to injuries.
        df['Country'] = np.repeat(Country, [23 if i == 'South Africa' else 22 for i in Country]).tolist()
    elif year == 2022: # 26 players per team. Iran presented 25 players instead of 26.
        df['Country'] = np.repeat(Country, [25 if i == 'Iran' else 26 for i in Country]).tolist()

    #print(len(Country))

    #print(df)

    # Format table ------------------------------------------------------------
    
    # Separating age from date of birth
    df[['Date of Birth', 'Age']] = df['Date of birth (age)'].str.extract(r'^(.*?)\s*\(aged\s+(\d+)\)')

    # Converting date format for date of birth
    # Clean up any weird non-breaking spaces or hidden HTML artifacts
    df['Date of Birth'] = df['Date of Birth'].str.replace(r'\xa0', ' ', regex=True).str.strip()
    #  Convert date to datetime objects
    # 'errors=coerce' turns unparseable dates into NaT (Not a Time) instead of crashing
    df['Date of Birth'] = pd.to_datetime(df['Date of Birth'], errors='coerce')
    # Fill in the Blanks for "Day Month Year" (Ronaldo). This only touches rows that are still NaT (Not a Time)
    is_nat = df['Date of Birth'].isna()
    df.loc[is_nat, 'Date of Birth'] = pd.to_datetime(
        df.loc[is_nat, 'Date of birth (age)'].str.extract(r'^(.*?)\s*\(aged')[0], 
        dayfirst=True, errors='coerce')
    # Format Date as standard DB string (YYYY-MM-DD)
    df['Date of Birth'] = df['Date of Birth'].dt.strftime('%Y-%m-%d')
    # failed date conversion check
    null_dates = df[df['Date of Birth'].isna()]
    if not null_dates.empty:
        print(f"Warning: {len(null_dates)} birthdates failed to convert in {edition}")
        #print(df.loc[null_dates.index, 'Date of birth (age)'])
    # Fill failed dated with None's
        df['Date of Birth'] = df['Date of Birth'].where(df['Date of Birth'].notna(), None)
    df = df.drop(columns=['Date of birth (age)'])

    # Separating captain status from names
    captain_regex = r'\s\((?:c|captain)\)'
    df['Captain'] = df['Player'].str.contains(captain_regex, case=False, regex=True)
    df['Player'] = df['Player'].str.replace(captain_regex, '', case=False, regex=True)

    # Add tournament to every players' entry
    if year in teams16_era and year not in [1954,1970]:
        df['Tournament'] = [edition]*352 # 22 players * 16 teams
    elif year == 1954:
        df['Tournament'] = [edition]*(352-2) # 22 players * 16 teams - 2 absences
    elif year == 1970:
        df['Tournament'] = [edition]*(352-3) # 22 players * 16 teams - 3 absences
    elif year in teams24_era and year not in [1982,1990]:
        df['Tournament'] = [edition]*528 # 22 players * 24 teams
    elif year == 1982:
        df['Tournament'] = [edition]*(528-2) # 22 players * 24 teams - 2 absences
    elif year == 1990:
        df['Tournament'] = [edition]*(528+2) # 22 players * 24 teams + 2 replacements
    elif year in teams32_era and year not in [1998,2022]:
        df['Tournament'] = [edition]*736 # 23 players * 32 teams
    elif year == 1998:
        df['Tournament'] = [edition]*705 # 22 players * 32 teams + 1 replacement
    elif year == 2022:
        df['Tournament'] = [edition]*831 # 26 players * 32 teams - 1 drop

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

    rosters_ds.append(df) # add df to the data set"""
       
def groups_scraper(matches_soup, year, edition, teams16_era, teams24_era, teams32_era, groups_ds): 

    # Import group tables
    tables = matches_soup.select('table.wikitable')
    table = [t for t in tables 
            if 'text-align:center' in str(t.get('style', '')).replace(' ', '')
            and 'Team' in t.get_text() and 'Qualification' in t.get_text() and 'Grp' not in t.get_text()]

    groups = pd.read_html(StringIO(str(table)))

    df = pd.concat(groups)
    #print(df)
    #"""
    # Add group to teams
    if year in teams16_era and year not in [1974,1978]:
        Group = ['1','2','3','4']
        df['Group'] = np.repeat(Group,4)
    elif year in [1974,1978]:
        group1 = ['1','2','3','4']
        Group1 = np.repeat(group1,4)
        group2 = ['A','B']
        Group2 = np.repeat(group2,4)
        df['Group'] = np.concat([Group1, Group2])
    elif year in teams24_era and year not in [1982]:
        Group = ['A','B','C','D','E','F']
        df['Group'] = np.repeat(Group,4)
    elif year in [1982]:
        group1 = ['1','2','3','4','5','6']
        Group1 = np.repeat(group1,4)
        group2 = ['A','B','C','D']
        Group2 = np.repeat(group2,3)
        df['Group'] = np.concat([Group1, Group2])
    elif year in teams32_era:
        Group = ['A','B','C','D','E','F','G','H']
        df['Group'] = np.repeat(Group,4)
    
    # Add Tournament
    if year in teams16_era and year not in [1974,1978]:
        df['Tournament'] = np.repeat(edition,16)
    elif year in [1974,1978]:
        df['Tournament'] = np.repeat(edition,24)
    elif year in teams24_era and year != 1982:
        df['Tournament'] = np.repeat(edition,24)
    elif year == 1982:
        df['Tournament'] = np.repeat(edition,36)
    elif year in teams32_era:
        df['Tournament'] = np.repeat(edition,32)

    # Clean up information
    df.loc[df['Qualification'].isna(), 'Qualification'] = 'Eliminated' # Reformat 'Qualification' column
    df = df.rename(columns = {'Teamvte':'Team'}) # Rename Team column
    df['Team'] = df['Team'].str.replace(' (H)', '', regex = False)

    # Some teams have a link clarifying qualification due to fair play points or . Info needs to
    # be appended to 'Qualification'
    if year <= 1970:
        df['Pts'] = df['Pts'].astype(str).str.replace(r'\s*\[a\]', '', regex=True).str.strip()
    else:
        fpp = df['Pts'].astype(str).str.contains(r'\[a\]', na=False)
        df.loc[fpp, 'Qualification'] = df.loc[fpp, 'Qualification'].astype(str) + ' (Fair Play Points)'
        df['Pts'] = df['Pts'].astype(str).str.replace(r'\s*\[a\]', '', regex=True).str.strip()
    
    # Replace special characters in GD column
    if year > 1966 and year not in [1954]:
        df['GD'] = df['GD'].str.replace(r'[\u2212\u2013\u2014]', '-', regex = True)
    else: pass

    # Reorganize df
    if year <= 1966 and year not in [1954]: # 1966 editions and prior use GR (Goal Ratio) to decide point ties
        col_header = ['Tournament', 'Group','Pos','Team','Pld','W','D','L','GF','GA','GR','Pts','Qualification']
    else: # Editions after 1966 use GD (Goal Difference) to decide point ties
        col_header = ['Tournament', 'Group','Pos','Team','Pld','W','D','L','GF','GA','GD','Pts','Qualification']
    cols = [col for col in df.columns if col not in col_header]
    df = df[col_header + cols]

    groups_ds.append(df) # Add df to the data set"""

def matches_scraper(matches_soup, year, edition, teams16_era, teams24_era, teams32_era, matches_ds): # -------------------

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
    Location = []
    Attendance = []
    Date = []
    Time = []
    Stage = []
    Group = []    
    Winner = []

    # Group stage data scrap --------------------------------------------------
    #"""
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
                        # Import location
                        td_d = cells[3]
                        links = td_d.find_all('a')
                        concatenated_links = ", ".join([link.text.strip() for link in links])
                        Location.append(concatenated_links)
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

    #"""
    
    match_info = matches_soup.find_all('div', attrs = {'itemscope': True, 
                                       'itemtype': 'http://schema.org/SportsEvent',
                                       'class': 'footballbox'})

    # Import data from footballbox tables
    # Path: div -> tr -> th -> span -> a
    for match in match_info:
        # Create tournament column
        Tournament.append(edition)
        # Import home team
        home_team = match.select_one('th.fhome span a')
        HomeTeam.append(home_team.get_text(strip = True))
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
        AwayTeam.append(away_team.get_text(strip = True))
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
        if year in teams16_era and year not in [1958,1974,1978]:
            if len(Stage) < 24: Stage.append('Group Stage')
            elif len(Stage) < 28: Stage.append('Quarter-finals')
            elif len(Stage) < 30: Stage.append('Semi-finals')
            elif len(Stage) == 30: Stage.append('Third Place Match')
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
        elif year in teams24_era and year not in [1982,1990]:
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
            if len(Stage) < 44: Stage.append('Round of 16')
            elif len(Stage) < 48: Stage.append('Quarter-finals')
            elif len(Stage) < 50: Stage.append('Semi-finals')
            elif len(Stage) == 50: Stage.append('Third Place Match')
            else: Stage.append('Final')
        elif year in teams32_era:
            if len(Stage) < 48: Stage.append('Group Stage')
            elif len(Stage) < 56: Stage.append('Round of 16')
            elif len(Stage) < 60: Stage.append('Quarter-finals')
            elif len(Stage) < 62: Stage.append('Semi-finals')
            elif len(Stage) == 62: Stage.append('Third Place Match')
            else: Stage.append('Final')
        # Add group the game was played in
        if year in teams16_era and year not in [1958,1974,1978]:
            if len(Group) < 6: Group.append('Group 1')
            elif len(Group) < 12:  Group.append('Group 2')
            elif len(Group) < 18: Group.append('Group 3')
            elif len(Group) < 24: Group.append('Group 4')
            else: Group.append('NaN')
        elif year == 1958:
            if len(Group) < 6: Group.append('Group 1')
            elif len(Group) == 6: Group.append('Group 1 Play-off')
            elif len(Group) < 13:  Group.append('Group 2')
            elif len(Group) < 19: Group.append('Group 3')
            elif len(Group) == 19: Group.append('Group 3 Play-off')
            elif len(Group) < 26: Group.append('Group 4')
            elif len(Group) == 26: Group.append('Group 4 Play-off')
            else: Group.append('NaN')
        elif year in [1974,1978]:
            if len(Group) < 6: Group.append('Group 1')
            elif len(Group) < 12:  Group.append('Group 2')
            elif len(Group) < 18: Group.append('Group 3')
            elif len(Group) < 24: Group.append('Group 4')
            elif len(Group) < 30: Group.append('Group A')
            elif len(Group) < 36: Group.append('Group B')
            else: Group.append('NaN')
        elif year in teams24_era and year not in [1982,1990]:
            if len(Group) < 6: Group.append('Group A')
            elif len(Group) < 12:  Group.append('Group B')
            elif len(Group) < 18: Group.append('Group C')
            elif len(Group) < 24: Group.append('Group D')
            elif len(Group) < 30: Group.append('Group E')
            elif len(Group) < 36: Group.append('Group F')
            else: Group.append('NaN')
        elif year == 1982:
            if len(Group) < 6: Group.append('Group 1')
            elif len(Group) < 12:  Group.append('Group 2')
            elif len(Group) < 18: Group.append('Group 3')
            elif len(Group) < 24: Group.append('Group 4')
            elif len(Group) < 30: Group.append('Group 5')
            elif len(Group) < 36: Group.append('Group 6')
            elif len(Group) < 39: Group.append('Group A')
            elif len(Group) < 42: Group.append('Group B')
            elif len(Group) < 45: Group.append('Group C')
            elif len(Group) < 48: Group.append('Group D')
            else: Group.append('NaN')
        elif year == 1990:
            Group.append('NaN')
        elif year in teams32_era:
            if len(Group) < 6: Group.append('Group A')
            elif len(Group) < 12:  Group.append('Group B')
            elif len(Group) < 18: Group.append('Group C')
            elif len(Group) < 24: Group.append('Group D')
            elif len(Group) < 30: Group.append('Group E')
            elif len(Group) < 36: Group.append('Group F')
            elif len(Group) < 42: Group.append('Group G')
            elif len(Group) < 48: Group.append('Group H')
            else: Group.append('NaN')
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
        Winner.append(None)#"""

    #"""
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
        'Location': Location,
        'Attendance': Attendance,
        'Date': Date,
        'Time': Time,
    }
    
    # Turn dictionary into dataframe
    df = pd.DataFrame.from_dict(df)
    #print(df)

    # Fill up winner column
    conditions = [
    (df['HomeScore'] > df['AwayScore']),
    (df['AwayScore'] > df['HomeScore']),
    (df['Penalties'] & (df['HomePKs'] > df['AwayPKs'])),
    (df['Penalties'] & (df['AwayPKs'] > df['HomePKs']))
    ]

    # Choices
    choices = [df['HomeTeam'], df['AwayTeam'], df['HomeTeam'], df['AwayTeam']]

    # Fill the winner column, default to 'Draw'
    df['Winner'] = np.select(conditions, choices, default='Draw')

    # Clean Attendance references and Score dashes
    df['Attendance'] = df['Attendance'].str.replace(r'\[\d+\]', '', regex=True).str.strip()
    df['Score'] = df['Score'].str.replace(r'[\u2013\u2014]', '-', regex = True)
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

    matches_ds.append(df) # Add df to the data set"""

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

