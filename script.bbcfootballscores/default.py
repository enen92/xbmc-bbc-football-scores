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
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import urllib2
import string
import sys
import re
import time
import os
import datetime
from BeautifulSoup import BeautifulSoup

if sys.version_info >=  (2, 7):
    import json as json
else:
    import simplejson as json 

import xbmc
import xbmcgui
# import xbmcplugin
import xbmcaddon

from match import League

########################################################################
__ScriptName__ = "BBC Football Score Scraper"
__ScriptVersion__ = "0.2.0"
__Author__ = "el_Paraguayo"
__Website__ = "https://github.com/elParaguayo/"
########################################################################

# Set the addon environment
_A_ = xbmcaddon.Addon( "script.bbcfootballscores" )
_S_ = _A_.getSetting

# Load some user settings
alarminterval = str(_S_("alarminterval"))
pluginPath = _A_.getAddonInfo("path")
showchanges = _S_("showchanges") == "true"

try: 
    watchedleagues = json.loads(str(_S_("watchedleagues")))
except: 
    watchedleagues = []

rundate = str(_S_("rundate"))
gamedate = datetime.date.today().strftime("%y%m%d")
leaguedata = League()

# Parse command parameters
# Thanks to TV Tunes script for this bit of code!!
try:
    # parse sys.argv for params
    try:
        params = dict(arg.split("=") for arg in sys.argv[1].split("&"))
    except:
        params =  dict(sys.argv[1].split("="))
except:
    # no params passed
    params = {}   

  
# Some basic utilities for the script
def debuglog(message):
    '''Send DEBUG level notices to XBMC's log.'''
    xbmc.log("%s: %s" % ("BBC Football Scores",
                         message),
                         level=xbmc.LOGDEBUG)
    
def getPage(url):
    '''Basic function to return web page.'''
    page = None
    try:
        user_agent = 'Mozilla/5 (Solaris 10) Gecko'
        headers = { 'User-Agent' : user_agent }
        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        page = response.read()
    except:
        pass
        
    return page

def isRunning():
    '''Flag for determining if score script is running.'''
    return _S_("scriptrunning") == "true"

def showMenu():
    '''Set up our main menu.'''
    
    # Create list of menu items
    userchoice = []
    userchoice.append("Select leagues")
    if not isRunning():
        userchoice.append("Start")
    else:
        userchoice.append("Show scores")
        userchoice.append("Stop")
    userchoice.append("Settings")
    userchoice.append("Cancel")
    
    # Display the menu  
    inputchoice = xbmcgui.Dialog().select("BBC football scores", 
                                           userchoice)
    # Process menu actions
    
    # User wants to get list of leagues    
    if userchoice[inputchoice] == "Select leagues":
        selectLeagues()
    
    # User wants to start script and begin receiving updates
    elif userchoice[inputchoice] == "Start":
        saveLeagues(watchedleagues)
        cancelAlarm()
        setAlarm()
        showScores()

    # Get list of current scores in selected leagues
    elif userchoice[inputchoice] == "Show scores":
        saveLeagues(watchedleagues)
        if isRunning():
            listalarm = True
            cancelAlarm()
        else:
            listalarm = False

        showScoreList(listalarm)

    # Stop receiving updates
    elif userchoice[inputchoice] == "Stop":
        cancelAlarm()
 
    # Edit user preferences
    elif userchoice[inputchoice] == "Settings":
        _A_.openSettings()


def selectLeagues():
    '''Get list of available leagues and allow user to select those
       leagues from which they want to receive updates.
    '''
    
    # Get list of leagues
    myleaguedata = leaguedata.getLeagues()

    finishedSelection = False

    # Start loop - will be exited once user confirms selection or
    # cancels
    while not finishedSelection:
        userchoice = []
        myleagues = False
        leagues = []

        # Loop through leagues
        for league in myleaguedata:
        
            try:
                leagues.append([league["name"],int(league["id"])])
                
                # Mark the league if it's one the user has previously
                # selected
                if int(league["id"]) in watchedleagues:
                    userchoice.append("*" + league["name"])
                    myleagues = True
                else:
                    userchoice.append(league["name"])
            
            # Hopefully we don't end up here...
            except:
              userchoice.append("Error loading data")
        
        userchoice.append("Done")
      
        # Display the list
        inputchoice = xbmcgui.Dialog().select("Choose league(s)", 
                                              userchoice)
        
        
        # Hmmm, might need to get rid of the "global" declaration
        # I know these are frowned upon!
        global watchedleagues
        if (inputchoice >=0 and not userchoice[inputchoice] == "Done" 
            and not userchoice[inputchoice] == "Error loading data"):
            
            print "WatchedLeagues:", str(watchedleagues)
            if leagues[inputchoice][1] in watchedleagues:
                watchedleagues.remove(leagues[inputchoice][1])
            else:  
                watchedleagues.append(leagues[inputchoice][1])
                
        elif userchoice[inputchoice] == "Done":
            saveLeagues(watchedleagues)
            finishedSelection = True
            showMenu()
            
        elif inputchoice == -1:
            finishedSelection = True
            showMenu()
            

def getScoreString(match):
    '''Provide a tidy string object showing match score.
       e.g. Chelsea 3 - 1 Everton (L)
    '''
    score = "%s %s - %s %s (%s)" % (match["hometeam"],
                                    match["homescore"],
                                    match["awayscore"],
                                    match["awayteam"],
                                    match["status"])
    return score
        
def saveLeagues(leaguelist):
    '''Save the list of chosen leagues.
       Saved in JSON format.
    '''
    rawdata = json.dumps(leaguelist)
    _A_.setSetting(id="watchedleagues",value=rawdata)
  
def setAlarm():
    '''Sets an alarm to run the script at the time specified by the
       user's preferences.
       Calls the script with the "alarm" flag so that menus are not
       shown.
    '''
    xbmc.executebuiltin('%s(%s,%s(%s,%s),%s,%s)' % ("AlarmClock",
                                                    "bbcfootballalarm",
                                                    "RunScript",
                                                    "script.bbcfootballscores",
                                                    "alarm=True",
                                                    alarminterval,
                                                    "true"))

    _A_.setSetting(id="scriptrunning",value="true")
    #~ global isrunning
    #~ isrunning = True
    _A_.setSetting(id="rundate",value=gamedate)
  
def cancelAlarm():
    '''Cancel the alarm so no more score updates are provided.'''
    xbmc.executebuiltin('CancelAlarm(bbcfootballalarm,true)')
    _A_.setSetting(id="scriptrunning",value="false")
  
def getStatusInfo(match):
    '''Process the match info.'''
    debuglog("Processing match: %s" % (str(match)))
    statuscode = match["status"]
    statuschange = False
    
    # Has there been a goal?
    if goalScored(match):
        debuglog("Gooooooooooaaaaaaaaaaallllllllll!")
        imagelink = os.path.join(pluginPath, "images", "goal.jpg")
        statuschange = True
        statustext = "Goal!"
        
    # If it's full time, set the appropriate image
    elif statuscode == "FT":
        debuglog("Full time.")
        imagelink = os.path.join(pluginPath, "images", "ft.jpg")
        statustext = "Full Time"
        
    # If the game is playing, set the appropriate image
    elif statuscode == "L":
        debuglog("Latest score")
        imagelink = os.path.join(pluginPath, "images" ,"latest.jpg")
        statustext = "Latest"
        
    # If it's half time, set the appropriate image
    elif statuscode == "HT":
        debuglog("Half time")
        imagelink = os.path.join(pluginPath, "images", "ht.jpg")
        statustext = "Half Time"
        
    # Anything else means the game probably hasn't started
    else:
        debuglog("Not started.")
        imagelink = os.path.join(pluginPath, "images" , "notstarted.jpg")
        statustext = "Fixture (" + statuscode + ")"

    # Has the match status changed?
    if statuschanged(match):
        statuschange = True
    
    return statustext, imagelink, statuschange

def goalScored(match):
    '''Has a goal been scored?'''
    goal = False
    
    # Look up match scores from those saved at last update
    matchname = match["hometeam"] + match["awayteam"]
    
    try:
        myHome = int(myMatches[matchname]['homescore'])
        myAway = int(myMatches[matchname]['awayscore'])
    except:
        myHome = 0
        myAway = 0
  
    # If it's a different day and the goals are bigger than 0
    # then Goooooooooooooaaaaaaaaaallllllllllll!
    if not sameDay and (int(match["homescore"]) >0 
                         or int(match["awayscore"]) >0):
        goal = True
        
    # or if it is the same day but either the the home score or away
    # score is different then Gooooooooooaaaaaaaaaalllllllllll!
    elif sameDay:
        if not (myHome == int(match["homescore"]) 
                and myAway == int(match["awayscore"])):
            goal = True
    
    debuglog("Saved score %s-%s. Current score %s-%s" % (myHome,
                                                         myAway,
                                                         match["homescore"],
                                                         match["awayscore"]))
    
    # return Gooooooooooaaaaaaaaaallllllllll!
    return goal
  
def statuschanged(match):
    '''Has the status changed? E.g. HT -> L?'''
    statuschange = False
    
    # Look up status from previously saved data
    matchname = match["hometeam"]+ match["awayteam"]
    try:
        myStatus = myMatches[matchname]['status']
    except:
        # if we can't find match then make up a status
        myStatus = "X"

    # Has the status changed?
    if sameDay and not myStatus == match["status"]:
        statuschange = True
    elif not sameDay:
        statuschange = True

    debuglog("Saved status: %s. Current status: %s" % (myStatus,
                                                    match["status"]))

    return statuschange
  
  
#~ def matchStatus(match):
    #~ status = []
    #~ status.append(match["homeTeam"]["name"] + match["awayTeam"]["name"])
    #~ status.append(match["homeTeam"]["score"])
    #~ status.append(match["awayTeam"]["score"])
    #~ status.append(match["statusCode"])
    #~ return status
  
def showScores():
    '''Main function for displaying latest scores.'''

    # List for saving matches
    matchlist = []
    matchdict = {}

    # Get the list of leagues we want scores for
    myleagues = json.loads(_A_.getSetting("watchedleagues"))
    
    # Loop through the leagues
    for myleague in myleagues:
        
        # Get the matches in the league
        matches = leaguedata.getScores(myleague)
        
        # Loop through the matches
        for match in matches["matches"]:
            
            # We need to save the match in a dictionary with a unique ID
            # matchdict = {}

            # Process the match
            statustext, statusimage, statuschange = getStatusInfo(match)
                        
            # Do we need to show an update?
            if ((showchanges and statuschange) or not showchanges):
                
                # Get the formatted match string
                score = getScoreString(match)
                
                # And display notification in xbmc
                xbmc.executebuiltin('Notification(%s,%s,2000,%s)' % (
                                                        statustext,
                                                        score, 
                                                        statusimage))
                
                # Sleep for 2 seconds
                # This shouldn't be necessary as XBMC should queue
                # the notifications
                time.sleep(2)
            
            # Create the ID
            matchid = match["hometeam"] + match["awayteam"]
            
            # Create the dict
            matchdict[matchid] = match
            
            # Add the match to our list    
            # matchlist.append(matchdict)
    
    # Save the scores (so we can check for updates when script next runs)
    saveScores(matchdict)

def showScoreList(listalarm):
    #~ scorelist = []        
    #~ fixtures = getJSONFixtures()
    #~ myleagues = _A_.getSetting("watchedleagues").split("|")
    #~ for league in fixtures["competition"]:
        #~ if league["id"] in myleagues:
            #~ for match in league["match"]:
                #~ score = getScoreString(match) + " (" + match["statusCode"] + ")"
                #~ scorelist.append(score)
    #~ latestscores = xbmcgui.Dialog().select("Latest scores",scorelist)
    #~ if listalarm: setAlarm()
    pass
  
def setWindowSummary(fixtures):
    #~ updateText = "[B]LATEST[/B] - "
    #~ myleagues = _A_.getSetting("watchedleagues").split("|")
    #~ for league in fixtures["competition"]:
        #~ if league["id"] in myleagues:
            #~ updateText = updateText + league["name"] + ": "
            #~ for match in league["match"]:
                #~ updateText = updateText + getScoreString(match) + " (" + match["statusCode"] + ")  "
  #~ 
    #~ if len(updateText) > 9:
        #~ xbmc.executebuiltin('Skin.SetString(bbcscores.summary, %s)' % (updateText))
    pass
        
def saveScores(savescores):
    '''Save the scores from the selected leagues so the script can check
       for updates when next run.
    '''
    # Convert list to a string
    savestring = json.dumps(savescores)
    
    # and save it
    _A_.setSetting(id="savescores", value=savestring)
    
def getSavedScores():
    '''Load previously saved scores.'''
    try:
        scores = json.loads(str(_S_("savescores")))
    except:
        scores = []
    return scores


########################################################################
# This is where we start!
########################################################################

debuglog("Starting script...")
debuglog("Script called with following parameters: %s" % (str(params)))

# If it's the script is running on the same day
# set appropriate flag and try to load pevious scores
if rundate == gamedate:
    sameDay = True
    myMatches = getSavedScores()
    debuglog("Loaded saved scores: %s" % str(myMatches))

# If it's a new day, we can disregard previously saved matches
else:
    sameDay = False
    myMatches = []
    debuglog("Saved scores not loaded.")  


# Was the script called from an alarm?        
if params.get("alarm", False):
    
    debuglog("Script called by alarm")
    
    # If so, set the next alarm
    setAlarm()
    # And check for new score alerts
    showScores()

else:
    
    debuglog("User called script")
    
    # If not, show the menu
    showMenu()

        
  
#soup = getPage(getScrapePage())
#soup = getPage("http://news.bbc.co.uk/sport1/hi/football/9472266.stm")
#scorePage = BeautifulSoup(soup)
#latestScores = getScores(scorePage)
#parseScores(latestScores)
#getGoalFlashes(scorePage)
#linkStrainer=SoupStrainer('a')
#getLinks(scorePage)



