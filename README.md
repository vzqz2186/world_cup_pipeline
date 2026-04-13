# FIFA World Cup Data Engineering Pipeline

**Author:** Daniel Vazquez

**Status:** Active development (Data Ingestion Phase)

Hosted here is a robust Python-based web scraper and data cleaning pipeline designed to extract and standardize historical FIFA World Cup data (1930–2022). This project goes beyond simple scraping by implementing advanced data validation and transformation logic to ensure the dataset is "Database Ready" for SQL Server and AWS environments.

This pipeline achieves the following:

* **Complex Date Normalization:** Implements regex-based extraction to handle varying Wikipedia date formats, standardizing all to ISO-8601 `YYYY-MM-DD` while maintaining an audit trail of null values.
* **HTML Structural Adaptability:** Features a resilient scraping logic that navigates shifting Wikipedia templates.
* **Edge Case Management:** Automatically identifies and handles "Walkovers" (e.g., 1938 Sweden vs. Austria), ensuring match statistics like attendance, referees, and winners are correctly nullified rather than filled with garbage data.
* **Unicode & Type Safety:** Standardizes specialized characters (En/Em dashes) and ensures numeric fields are cleaned of commas and strings to maintain strict integer/float types for SQL compatibility.

## Data Architecture

The pipeline generates three primary datasets, structured for a relational schema:

1.  **squads_ds**: Full rosters including Player Name, Position, Birth Date (standardized), Club, and Captaincy status.
2.  **groups_ds**: Group stage standings, points, and qualification status.
3.  **matches_ds**: Comprehensive match records including:
    * Home/Away teams, scores, and calculated Winners.
    * Match Stage, Attendance, Stadium, and Hosting City.
    * Special outcomes: Extra Time (a.e.t), Golden Goals, and Penalty results.

## Tech Features

- **Python 3.x**
- **BeautifulSoup4:** Precise DOM navigation using CSS selectors.
- **Pandas & NumPy:** For complex data transformation and `NaN` management.
- **Regex (re):** For pattern matching in inconsistent string formats.

## Getting started

**Prerequisites**

Ensure Python 3.x is installed along with the following libraries:
- beautifulsoup4
- requests
- pandas
- numpy

## Usage

```
# Clone the repository
git clone https://github.com/vzqz2186/world-cup-scraper.git

# Run the pipeline
python fifa_wc_scraper.py
```

## Roadmap

- [ ] **Relational Modeling:** Implement Primary and Foreign Key mapping (Player IDs, Team IDs).
- [ ] **SQL Server Integration:** Write the automated ingestion script using `SQLAlchemy`.
- [ ] **Cloud Migration:** Build a pipeline to load cleaned dataframes into **AWS S3** and **Amazon Redshift**.
- [ ] **2026 Expansion:** Add support for the 48-team tournament format.
