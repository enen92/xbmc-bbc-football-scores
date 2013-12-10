'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

import urllib2
import re
from BeautifulSoup import BeautifulSoup


'''
    This is a class that reads the BBC website and pulls out the live
    football scores.

    The class has two main methods:
        1) getLeagues(): This provides a list of all leagues that are
           available on the BBC site. NB this does not mean that there
           are live games playing.
           Each league is a dict containing "name" and "id" values.

        2) getScores(): Returns a dict containing the ID of the league
           and a list of current scores from the chosen league.
           
           Each match is a dict for home team, away team, 
           home score, away score and status.
           
           The dict has 2 keys:
                "league": the league ID
                "matches": the list of match dicts
           
           List of matches is empty no matches found for the selected
           league.
'''


class League:

    # The "accordion" is the box on the side of the BBC sport page.
    # This has its own source code which means we don't have to query
    # large pages to get our data.
    accordionlink = ("http://polling.bbc.co.uk/sport/shared/"
                     "football/accordion/partial/collated")

    def getPage(self, url):
        page = None
        try:
            user_agent = 'Mozilla/5 (Solaris 10) Gecko'
            headers = {'User-Agent': user_agent}
            request = urllib2.Request(url)
            response = urllib2.urlopen(request)
            page = response.read()
        except:
            pass

        return page

    def getLeagues(self):
        '''getLeagues(): This provides a list of all leagues that are
           available on the BBC site. NB this does not mean that there
           are live games playing.
           Each league is a dict containing "name" and "id" values.
        '''
        leagues = []
        raw = BeautifulSoup(self.getPage(self.accordionlink))

        # Loop through all the competitions being played today
        for option in raw.findAll("option"):

            # Create a dict for each league
            league = {}

            # Get the name of the league
            league["name"] = option.text

            # Get the ID of the league 
            # (we need this to look up results)
            league["id"] = option.get("value")

            # Add this to our list of leagues
            leagues.append(league)

        return leagues

    def getScores(self, league):
        '''getScores(): Returns a dict containing the ID of the league
           and a list of current scores from the chosen league.
           
           Each match is a dict for home team, away team, 
           home score, away score and status.
           
           The dict has 2 keys:
                "league": the league ID
                "matches": the list of match dicts
           
           List of matches is empty no matches found for the selected
           league.
        '''
        scores = {}
        scores["league"] = league
        scoreslist = []
        accordionlink = "%s?%s=%s" % (self.accordionlink,
                                      "selectedCompetitionId",
                                      league)
        try:
        
            raw = BeautifulSoup(self.getPage(accordionlink))

            matches = raw.find("div",
                            {"class": "accordion-container live-today"})

            if not matches is None:
                for match in matches.findAll("li"):
                    matchdetail = {}
                    matchdetail["hometeam"] = match.find("span", 
                                            {"class": "home-team"}).text
                    matchdetail["awayteam"] = match.find("span", 
                                            {"class": "away-team"}).text
                    
                    restatus = re.compile(r"\bstatus\b")
                    matchdetail["status"] = match.find("span", 
                                  {"class": restatus}).find("abbr").text

                    score = match.find("span", 
                                    {"class": "result"}).text.split(" ")
                    try:
                        matchdetail["homescore"] = int(score[0].strip())
                        matchdetail["awayscore"] = int(score[2].strip())
                    except:
                        matchdetail["homescore"] = 0
                        matchdetail["awayscore"] = 0

                    scoreslist.append(matchdetail)

        except:
            
            scoreslist = []

        scores["matches"] = scoreslist

        return scores
