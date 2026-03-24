# FIFA World Cup Data Scrapper Project

This program scrapes data from FIFA World Cup tournaments from 2002 to 2022 from their respective Wikipedia entries. The Python script pulls data for participating players, tournament group and team stats, and fixtures. It then cleans up the data and organizes them into 3 clean data sets:

- **squads_ds** contains the rosters of all participating teams, as well as player information.
- **matches_ds** contains match information from all stages of the tournament.
- **groups_ds** contains groups and team stats information such as wins, losses, goal difference, points, etc...

The program follows the following procedure:

    1. Access the html code for the websites to scrap using the BeautifulSoup libraries.
    2. Scrap different data from tables and lists in the html code to fill lists used 
       from completing pandas dataframes. The tables contain information on:

        a. Team groups
        b. Participating countries
        c. Players' birthdays
        d. Match locations
        e. Players' birthdays
        f. Match dates and times
        g. Match results
        h. Match home and away sides
        i. Match groups and stages
        j. Penalty results

    3. Save all scrapped dataframes to csv files.
    
After scrapping the data, SQL is used to clean the obtained tables. The changes are the following:

    1. Calculate the players' age at the start of the tournament and create a new column to store that data.
    2. Separate the 'captain' label from certain players' names and create a column detailing which players
       are team captains.
    3. Replace the abbreviations in the 'Pos' field with the full names of the player positions.
    4. Separate the goals in 'Result' field into their own columns and add a new column to label the match
       winner.
    5. Add a column that flags games that had a penalty kick round.

All files (csv's and scripts) are in the files section of this page. The following tasks are also planned to add to the project.
- Scrap data for match location and date.
- Scrap penalty kick scores.
