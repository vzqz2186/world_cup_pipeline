# FIFA World Cup Data Scraper

Author: Daniel Vazquez

Version: 3.03

A robust Python-based web scraper designed to extract comprehensive historical data from FIFA World Cup tournaments (currently supporting 2002–2022). The script targets Wikipedia’s highly organized football entry pages to build structured datasets for sports analysis, machine learning, or historical record-keeping.

The scraper also fixes inconsistent table structures across different years, special Unicode characters in scores, and varying squad sizes.

## Extracted Data

Three data sets are generated from this script:

1. **squads_ds**: Full rosters including Player Name, Position, Age, Date of Birth, Captaincy status, Club, and Goals.
2. **groups_ds**: Group stage standings, points, goal differences, and qualification status (including Fair Play Points logic).
3. **matches_ds**: Detailed match results including:
    - Home/Away teams and scores.
    - Match Stage (Group, Round of 16, etc.).
    - Attendance, Stadium Location, and Referees.
    - Special outcomes: Extra Time (a.e.t.), Golden Goals (g.g.), and Penalty
      Shootout results.

## Tech Features

- **BeautifulSoup4 & CSS Selectors:** Utilizes precise pathing to extract data nested within complex Wikipedia templates.
- **Regex Data Cleaning:**
    - Extracts numeric scores from text (e.g., "3–1").
    - Cleans Unicode "En Dashes" (\u2013) and "Em Dashes" (\u2014) into standard ASCII hyphens.
    - Separates Captain status and Age from raw strings.
- **Advanced Logic:** Calculates a definitive Winner column by comparing regular-time scores and, if necessary, penalty shootout results.
- **Scalability:** Modular loop structure that iterates through tournament editions, making it easy to add future or older tournaments.

## Getting started

**Prerequisites**

Ensure Python 3.x is installed along with the following libraries:
- beautifulsoup4
- requests
- pandas
- numpy

**File Structure**

The script automatically organizes its output.

**Usage**

Simply run the script. The console will provide real-time updates as it processes each tournament edition.

## Roadmap / To-Do

- Add 1998 edition.
- Add function to automate upload to a SQL Server database.
- Add support for the expanded 8-team 2026 format.
- Add support for Early Era (1930-1950) and Classic Era (1954-1994) editions.
