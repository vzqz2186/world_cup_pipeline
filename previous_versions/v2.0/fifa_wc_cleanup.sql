/*
FIFA World Cup data set cleaning

     Author: Daniel Vazquez
Description: The following scripts are used to clean up the tables obtained
             from data scrapping rosters and fixtures from FIFA World Cup
			 tournaments. It also serves as data exploration for stats from
			 previous tournaments.

			 Steps:
			   1. Data Cleaning
				  a. Create 'Age' field in FIFA_wc_players
				  b. Separate 'Captain' label from FIFA_wc_players
				  c. Replace 'Pos' data for the true position names in
				     FIFA_wc_players.
				  d. Separate goals in 'Result' field and add a new field for
				     match winner.
				  e. Add field to flag games that had a penalty kick round.
*/

-- USE world_cups;
-- SELECT * FROM FIFA_wc_groups;
-- SELECT * FROM FIFA_wc_players;
-- SELECT * FROM FIFA_wc_matches;

-- a. Create 'Age' field in 'Players' table -------------------------------- 80

ALTER TABLE FIFA_wc_players
ADD Age char(2);
-- Update the 'Age' field to the players current age at the start of the
-- tournament.
UPDATE FIFA_wc_players
SET Age = CASE
	WHEN Tournament = 'Korea/Japan 2002'
	    THEN DATEDIFF(year, Date_of_Birth, CAST('2002-05-31' AS Date))
	WHEN Tournament = 'Germany 2006' 
		THEN DATEDIFF(year, Date_of_Birth, CAST('2006-06-09' AS Date))
	WHEN Tournament = 'South Africa 2010'
		THEN DATEDIFF(year, Date_of_Birth, CAST('2010-06-11' AS Date))
	WHEN Tournament = 'Brazil 2014'
		THEN DATEDIFF(year, Date_of_Birth, CAST('2014-06-12' AS Date))
	WHEN Tournament = 'Russia 2018'
		THEN DATEDIFF(year, Date_of_Birth, CAST('2018-06-14' AS Date))
	END FROM FIFA_wc_players;

-- b. Separate 'Captain' string from Players ------------------------------- 80

ALTER TABLE FIFA_wc_players
ADD Captain varchar(3)
-- Populate the 'Captain' field by checking whether players are marked as
-- team captain or not in the 'Player' field.
UPDATE FIFA_wc_players
SET Captain = CASE 
                WHEN Player LIKE '%(captain)%' THEN 'Yes'
				WHEN Player LIKE '%(c)%' THEN 'Yes'
				ELSE 'No'
		      END FROM FIFA_wc_players;
-- Remove the 'captain' flag from the 'Player' field.
UPDATE FIFA_wc_players
SET Player = CASE
    WHEN Player LIKE '%(captain)%'
		THEN REPLACE(Player, '(Captain)', '')
	WHEN Player LIKE '%(c)%'
		THEN REPLACE(Player, '(c)', '')
	ELSE Player
	END FROM FIFA_wc_players;

-- c. Replace 'Player_position' data for the true position names ----------- 80

UPDATE FIFA_wc_players
SET Pos = CASE
            WHEN Pos = 'GK' THEN 'Goalkeeper'
			WHEN Pos = 'DF' THEN 'Defender'
			WHEN Pos = 'MF' THEN 'Midfielder'
			WHEN Pos = 'FW' THEN 'Forward'
		  END FROM FIFA_wc_players;

-- d. Separate 'Result' and add 'Winner' field ----------------------------- 80

-- Create Score and winner columns
ALTER TABLE FIFA_wc_matches
ADD Home_Score int
ALTER TABLE FIFA_wc_matches
ADD Away_Score int
ALTER TABLE FIFA_wc_matches
ADD Winner varchar(50)

-- Populate score columns
UPDATE FIFA_wc_matches
SET Home_Score = SUBSTRING(Result,1,1)
UPDATE FIFA_wc_matches
SET Away_Score = SUBSTRING(Result,5,1)

-- Populate winner
UPDATE FIFA_wc_matches
SET Winner = CASE
             WHEN Home_Score > Away_Score THEN Home
			 WHEN Home_Score < Away_Score THEN Away
			 WHEN Home_Score = Away_Score THEN 'Tie'
			 END

-- e. Add field to flag games that had a penalty kick round ---------------- 80

-- Create columnn
ALTER TABLE FIFA_wc_matches
ADD PKs varchar(3)

-- Populate column
UPDATE FIFA_wc_matches
SET PKs = CASE
          WHEN Result LIKE '%(a.e.t.)%'
		      THEN CASE
			      WHEN Winner = 'Tie' THEN 'Yes'
                  ELSE 'N/A'
				  END
		  ELSE 'N/A'
		  END

-- Delete Result column
ALTER TABLE FIFA_wc_matches
DROP COLUMN Result
