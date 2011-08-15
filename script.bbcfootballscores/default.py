import urllib
import urllib2
import string
import sys
import re
import time
import os
import datetime
import simplejson as json
from BeautifulSoup import BeautifulSoup, SoupStrainer
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

__ScriptName__ = "BBC Football Score Scraper"
__ScriptVersion__ = "0.1.0"
__Author__ = "el_Paraguayo"
__Website__ = ""

_A_ = xbmcaddon.Addon( "script.bbcfootballscores" )
_S_ = _A_.getSetting

isrunning = _S_("scriptrunning") == "true"
alarminterval = str(_S_("alarminterval"))
#ftupdates = int(_S_("ftupdates"))
pluginPath = _A_.getAddonInfo("path")
showchanges = _S_("showchanges") == "true"

try: watchedleagues = str(_S_("watchedleagues")).split("|")
except: watchedleagues = []

rundate = str(_S_("rundate"))
gamedate = datetime.date.today().strftime("%y%m%d")




savescores = []

#Parse command parameters - thanks to TV Tunes script for this bit of code!!
try:
    # parse sys.argv for params
    try:params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
    except:params =  dict( sys.argv[ 1 ].split( "=" ))
except:
    # no params passed
    params = {}   

class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value    
    
def getPage(url):
  user_agent = 'Mozilla/5 (Solaris 10) Gecko'
  headers = { 'User-Agent' : user_agent }
  #values = {'s' : sys.argv[1] }
  #data = urllib.urlencode(values)
  request = urllib2.Request(url)
  response = urllib2.urlopen(request)
  the_page = response.read()
  return the_page

def getScores(soupedPage):  
  results = soupedPage.findAll('li', attrs={'id':re.compile(r'liveScoresSummary')})
  #print results
  source = ''
  return results

def parseScores(results):
  games = []
  scorearray=[]
  for result in results:
    score=result.findAll('span',text=True)
    games.append((score))

  for game in games:
    score =  game[0] + " (" + game[1] + "-" + game[3] + ") " + game[4]
    scorearray.append(score)
    if game[5] == "FT":
      status = "Full Time"
      imagelink = os.path.join(pluginPath, "images", "ft.jpg")
    elif game[5] == "L":
      status = "Latest"
      imagelink = os.path.join(pluginPath, "images" ,"latest.jpg")
    elif game[5] == "HT":
      status = "Half Time"
      imagelink = os.path.join(pluginPath, "images", "ht.jpg")
    else:
      status = "Not Started"
      score =  game[0] + " (x - x) " + game[4]
      imagelink = os.path.join(pluginPath, "images" , "notstarted.jpg")
    xbmc.executebuiltin('Notification(' + status + ',' + score + ',2000,' + imagelink + ')')
    time.sleep(2)
    
  #latestscore=xbmcgui.Dialog().select("Latest Scores", scorearray)
    
def getGoalFlashes(soupedPage):
  liveSummary = soupedPage.findAll('div', attrs={'id':re.compile(r'clockwatch')})
  goalFlashes = []
  #for flash in liveSummary[0]:
  goalFlash = liveSummary[0].findAll('b', text=re.compile(r'GOALFLASH'))
  for goal in goalFlash:
    print goal
    
def getLinks():
  liveLinks = []
  linkPair=[]
  footy = getPage("http://news.bbc.co.uk/sport1/hi/football/")
  #footy = getPage("http://news.bbc.co.uk/sport1/hi/football/eng_div_1/default.stm")
  myPage = BeautifulSoup(footy)
  live=re.compile(r'\bLive')
  summary=re.compile(r'\bhappened')
  for link in myPage.findAll('a'):
    #reg_link = re.sub('\s\s+',' ', link.contents)
    #print reg_link
    #print link
    if (live.search(str(link.contents)) or summary.search(str(link.contents))):
      for attr, value in link.attrs:
        if attr=="href":
          reg_link = re.sub('\s\s+',' ', str(link.contents[0]))
          if (len(reg_link) > 6 and not reg_link == "Live Videprinter"):
            liveLinks.append([reg_link,value])
  return liveLinks

def getScrapePage():  
  liveLinks = []
  userList = []
  liveLinks = getLinks()
  for linktext, linkaddress in liveLinks:
    userList.append(linktext)
  
  choiceid = xbmcgui.Dialog().select("Select link",userList)
  link = liveLinks[choiceid][1]
  if link[:1] == "/":
    link = "http://news.bbc.co.uk" + link
  print link
  return link

def getJSONFixtures():
  jsonresult = getPage('http://news.bbc.co.uk//sport/hi/english/static/football/statistics/collated/live_scores_summary_all.json')
  #myjson = os.path.join(pluginPath, "examplejson.txt")
  #f = open(myjson, "r")
  #jsonresult = f.read()
  
  fixtures = json.loads(jsonresult)
  return fixtures
  
def showMenu():
  global isrunning
  isrunning = _S_("scriptrunning") == "true"
  fixtures = getJSONFixtures()

  inputchoice = 0
  userchoice = []
  while True:
      myleagues = False
      leagues = []
      userchoice = []
      for league in fixtures["competition"]:
        # if int(league["id"]) == shieldid:
          # for match in league["match"]:
            # print league["name"] + ": " + match["homeTeam"]["name"] + " " + match["homeTeam"]["score"] + " - " + match["awayTeam"]["score"] + " " + match["awayTeam"]["name"]
        try:
          leagues.append([league["name"],league["id"]])
          if league["id"] in watchedleagues:
            userchoice.append("*" + league["name"])
            myleagues = True
          else:
            userchoice.append(league["name"])
        except:
          userchoice.append("No matches today")
      if myleagues:
        userchoice.append("Show score list")
        userchoice.append("Start")
      if isrunning:
        userchoice.append("Stop")
      userchoice.append("Settings")
      userchoice.append("Cancel")
      
      inputchoice = xbmcgui.Dialog().select("Choose competition", userchoice)
      global watchedleagues
      if (inputchoice >=0 and not userchoice[inputchoice] == "Start" and not userchoice[inputchoice] == "Stop" and not userchoice[inputchoice] == "Cancel" and not userchoice[inputchoice] == "Settings" and not userchoice[inputchoice] == "Show score list" and not userchoice[inputchoice] == "No matches today"):
        if leagues[inputchoice][1] in watchedleagues:
          watchedleagues.remove(leagues[inputchoice][1])
        else:  
          watchedleagues.append(leagues[inputchoice][1])
      elif userchoice[inputchoice] == "Start":
        saveLeagues(watchedleagues)
        cancelAlarm()
        setAlarm()
        showScores()
        #showScoreList()
        break
      elif userchoice[inputchoice] == "Show score list":
        saveLeagues(watchedleagues)
        if isrunning:
          listalarm = True
          cancelAlarm()
        else:
          listalarm = False
        
        showScoreList(listalarm)
        break
      elif userchoice[inputchoice] == "Stop":
        cancelAlarm()
        break
      elif userchoice[inputchoice] == "Settings":
        _A_.openSettings()
        #setFavouriteTeam(fixtures)
        break
      else:
        break

def getScoreString(match):
  score = match["homeTeam"]["name"] + " " + match["homeTeam"]["score"] + " - " + match["awayTeam"]["score"] + " " + match["awayTeam"]["name"]
  return score
        
def setFavouriteTeam(fixtures):
  teamlist = []
  for league in fixtures["competition"]:
    for match in league["match"]:
      teamlist.append(match["homeTeam"]["name"])
      teamlist.append(match["awayTeam"]["name"])
  myteam = xbmcgui.Dialog().select("Pick team", sorted(teamlist))

      
def saveLeagues(leaguelist):
  delimited = "|".join(leaguelist)
  _A_.setSetting(id="watchedleagues",value=delimited)
  
def setAlarm():
  xbmc.executebuiltin('AlarmClock(bbcfootballscorealarm,RunScript(script.bbcfootballscores,alarm=True),' + alarminterval + ',true)')
  _A_.setSetting(id="scriptrunning",value="true")
  global isrunning
  isrunning = True
  _A_.setSetting(id="rundate",value=gamedate)
  
def cancelAlarm():
  xbmc.executebuiltin('CancelAlarm(bbcfootballscorealarm,true)')
  _A_.setSetting(id="scriptrunning",value="false")
  global isrunning
  isrunning = False
  
def getStatusInfo(match):
  statuscode = match["statusCode"]
  statuschange = False
  if goalScored(match):
    imagelink = os.path.join(pluginPath, "images", "goal.jpg")
    statuschange = True
    statustext = "Goal!"
  elif statuscode == "FT":
    imagelink = os.path.join(pluginPath, "images", "ft.jpg")
    statustext = "Full Time"
  elif statuscode == "L":
    imagelink = os.path.join(pluginPath, "images" ,"latest.jpg")
    statustext = "Latest"
  elif statuscode == "HT":
    imagelink = os.path.join(pluginPath, "images", "ht.jpg")
    statustext = "Half Time"
  else:
    imagelink = os.path.join(pluginPath, "images" , "notstarted.jpg")
    statustext = "Fixture (" + statuscode + ")"

  if statuschanged(match):
    statuschange = True
    
  return statustext, imagelink, statuschange

def goalScored(match):
  goal = False
  matchname = match["homeTeam"]["name"] + match["awayTeam"]["name"]
  try:
    myHome = int(myMatches[matchname]['homeScore'])
    myAway = int(myMatches[matchname]['awayScore'])
  except:
    myHome = 0
    myAway = 0
  
  if not sameDay and (int(match["homeTeam"]["score"]) >0 or int(match["awayTeam"]["score"]) >0):
    goal = True
  elif sameDay:
      if not (myHome == int(match["homeTeam"]["score"]) and myAway == int(match["awayTeam"]["score"])):
        goal = True
  
  return goal
  
def statuschanged(match):
  statuschange = False
  matchname = match["homeTeam"]["name"] + match["awayTeam"]["name"] 
  try:
    myStatus = myMatches[matchname]['status']
  except:
    myStatus = "X"
  
  if sameDay and not myStatus == match["statusCode"]:
    statuschange = True
  elif not sameDay:
    statuschange = True
    
  return statuschange
  
  
def matchStatus(match):
  status = []
  status.append(match["homeTeam"]["name"] + match["awayTeam"]["name"])
  status.append(match["homeTeam"]["score"])
  status.append(match["awayTeam"]["score"])
  status.append(match["statusCode"])
  return status
  
def showScores():
  fixtures = getJSONFixtures()
  myleagues = _A_.getSetting("watchedleagues").split("|")
  for league in fixtures["competition"]:
    if league["id"] in myleagues:
      for match in league["match"]:
        score = getScoreString(match)
        leaguename = league["name"]
        statustext, statusimage, statuschange = getStatusInfo(match)
        if ((showchanges and statuschange) or not showchanges):
          xbmc.executebuiltin('Notification(' + statustext + ',' + score + ',2000,' + statusimage + ')')
          time.sleep(2)
        global savescores
        savescores.append(matchStatus(match))

def showScoreList(listalarm):
  scorelist = []        
  fixtures = getJSONFixtures()
  myleagues = _A_.getSetting("watchedleagues").split("|")
  for league in fixtures["competition"]:
    if league["id"] in myleagues:
      for match in league["match"]:
        score = getScoreString(match) + " (" + match["statusCode"] + ")"
        scorelist.append(score)
  latestscores = xbmcgui.Dialog().select("Latest scores",scorelist)
  if listalarm: setAlarm()
        
def saveScores():
  savestring = ""
  for savematch in savescores:
    savestring += savematch[0] + "|" + savematch[1] + "|" + savematch[2] + "|" + savematch[3] + "&"
  _A_.setSetting(id="savescores", value=savestring[:len(savestring)-1])
    
def getSavedScores():
  savedscores = str(_S_("savescores"))
  if len(savedscores) >0 :
    a = AutoVivification()
    for savedMatch in savedscores.split("&"):
      matchDetails = savedMatch.split("|")
      Teams = matchDetails[0]
      Home = matchDetails[1]
      Away = matchDetails[2]
      Status = matchDetails[3]
      a[Teams]['homeScore'] = Home
      a[Teams]['awayScore'] = Away
      a[Teams]['status'] = Status
  else:
    a = {}
  return a  


if rundate == gamedate:
  sameDay = True
  myMatches = getSavedScores()
else:
  sameDay = False  
        
if params.get("alarm", False):
  setAlarm()
  showScores()
  saveScores()
else:
  showMenu()
  saveScores()
        
  
#soup = getPage(getScrapePage())
#soup = getPage("http://news.bbc.co.uk/sport1/hi/football/9472266.stm")
#scorePage = BeautifulSoup(soup)
#latestScores = getScores(scorePage)
#parseScores(latestScores)
#getGoalFlashes(scorePage)
#linkStrainer=SoupStrainer('a')
#getLinks(scorePage)



