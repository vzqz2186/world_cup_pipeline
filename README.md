# FIFA World Cup Data Engineering Pipeline

**Author:** Daniel Vazquez\
**Status:** Active development\
**Language:** Python\
**Libraries:** Pandas, BeautifulSoup, Requests, SQLAlchemy, Unidecode\
**Database:** Microsoft SQL Server

Hosted here is a robust Python-based data pipeline designed extract historical FIFA World Cup data (1930–2022) from the web, structure and normalize the data onto pandas DataFrames, and load it into a relational SQL Server database.

## Database Schema Architecture

The target database (FIFAWCDB) enforces strict relational integrity across 5 core tables, utilizing composite keys to handle tournament-specific entities:

- **Tournaments_Master**: Historical tournament metadata.
- **Teams_Master**: Unified catalog of competing nations (including a generated relational anchor for Draw matches).
- **Players_Master**: Master registry tracking players uniquely by an engineered natural hash key combining Country, Name, and Date of Birth to prevent identity collisions.
- **Matches**: Match-by-match metrics using custom MS SQL dialect precision types (TIME(0)) for pristine storage.
- **Rosters / Groups**: Child bridge tables using Composite Primary Keys to track multi-tournament call-ups and tournament stages seamlessly.

## Data Quality and Engineering Highlights

* **Complex Date Normalization:** Implemented an aggressive RegEx and type-coercion cleaning pipeline in the scraping layer.
* **HTML Structural Adaptability:** Features a resilient scraping logic that navigates shifting Wikipedia templates.
* **Edge Case Management:** Automatically identifies and handles edge cases (such as the 1938 Walkover game) and structural anomalies in the data (such as footnotes, missing appereances, inconsistent data types), ensuring match statistics like attendance, referees, and winners are correctly nullified rather than filled with garbage data.
* **Unicode & Type Safety:** Standardizes specialized characters (En/Em dashes) and ensures numeric fields are cleaned of commas and strings to maintain strict integer/float types for SQL compatibility.
* **Text & Accent Normalization:** Integrated unicodedata NKFD normalization to strip accents globally and applied historical name translation mapping to enforce strict string alignment.

## Usage
```
# Clone the repository
git clone https://github.com/vzqz2186/world-cup-pipeline.git

# install dependencies
pip install beautifulsoup4 requests pandas sqlalchemy pyodbc

# Run the pipeline
python fifa_wc_madness.py
```

## Roadmap
- [ ] **Cloud Migration:** Update pipeline to load cleaned dataframes into **AWS S3** and **Amazon Redshift**.
- [ ] **2026 Expansion:** Add support for the 48-team tournament format.
