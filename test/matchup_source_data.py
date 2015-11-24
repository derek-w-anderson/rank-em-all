import pprint
from urllib2 import urlopen, URLError
from datetime import datetime
from time import strftime, gmtime
from xml.dom import minidom

offset = 4 * (60 * 60)  # adjusts kickoff time to ET
current_year = 2015
current_week = 11
api_url = 'http://football.myfantasyleague.com/%d/export?TYPE=nflSchedule&W=%d'

teams = {}
for week in range(1, current_week+1):
   url = api_url % (current_year, week)
   response = urlopen(url)
   xml = minidom.parse(response)

   for matchup in xml.getElementsByTagName('matchup'):
      kickoff = int(matchup.getAttribute('kickoff')) - offset
      
      team1 = matchup.getElementsByTagName('team')[0]
      team1_id = team1.getAttribute('id')
      if not teams.has_key(team1_id): teams[team1_id] = {}
      if not teams[team1_id].has_key('weeks'): teams[team1_id]['weeks'] = {}
      if not teams[team1_id].has_key('win'):   teams[team1_id]['win'] = 0
      if not teams[team1_id].has_key('loss'):  teams[team1_id]['loss'] = 0
      if not teams[team1_id].has_key('tie'):   teams[team1_id]['tie'] = 0
      if not teams[team1_id].has_key('pts_for'):     teams[team1_id]['pts_for'] = 0
      if not teams[team1_id].has_key('pts_against'): teams[team1_id]['pts_against'] = 0
      if not teams[team1_id].has_key('streak'):      teams[team1_id]['streak'] = 0
      if not teams[team1_id].has_key('off_pass_rank'): teams[team1_id]['off_pass_rank'] = 0 
      if not teams[team1_id].has_key('off_rush_rank'): teams[team1_id]['off_rush_rank'] = 0 
      if not teams[team1_id].has_key('def_pass_rank'): teams[team1_id]['def_pass_rank'] = 0 
      if not teams[team1_id].has_key('def_rush_rank'): teams[team1_id]['def_rush_rank'] = 0 
      
      team2 = matchup.getElementsByTagName('team')[1]
      team2_id = team2.getAttribute('id')
      if not teams.has_key(team2_id): teams[team2_id] = {}            
      if not teams[team2_id].has_key('weeks'): teams[team2_id]['weeks'] = {}
      if not teams[team2_id].has_key('win'):   teams[team2_id]['win'] = 0
      if not teams[team2_id].has_key('loss'):  teams[team2_id]['loss'] = 0
      if not teams[team2_id].has_key('tie'):   teams[team2_id]['tie'] = 0
      if not teams[team2_id].has_key('pts_for'):     teams[team2_id]['pts_for'] = 0
      if not teams[team2_id].has_key('pts_against'): teams[team2_id]['pts_against'] = 0
      if not teams[team2_id].has_key('streak'):      teams[team2_id]['streak'] = 0
      if not teams[team2_id].has_key('off_pass_rank'): teams[team2_id]['off_pass_rank'] = 0 
      if not teams[team2_id].has_key('off_rush_rank'): teams[team2_id]['off_rush_rank'] = 0 
      if not teams[team2_id].has_key('def_pass_rank'): teams[team2_id]['def_pass_rank'] = 0 
      if not teams[team2_id].has_key('def_rush_rank'): teams[team2_id]['def_rush_rank'] = 0 
      
      teams[team1_id]['weeks'][week] = {
         'score': 0,
         'opp_team': team2_id,
         'opp_score': 0,
         'kickoff': strftime("%a %I:%M %p ET", gmtime(kickoff)),
         'at_home': True if team1.getAttribute('isHome') == '1' else False,
         'result': None
      }
      teams[team1_id]['off_pass_rank'] = int(team1.getAttribute('passOffenseRank') or "0")
      teams[team1_id]['off_rush_rank'] = int(team1.getAttribute('rushOffenseRank') or "0")
      teams[team1_id]['def_pass_rank'] = int(team1.getAttribute('passDefenseRank') or "0")
      teams[team1_id]['def_rush_rank'] = int(team1.getAttribute('rushDefenseRank') or "0")
      
      teams[team2_id]['weeks'][week] = {
         'score': 0,
         'opp_team': team1_id,
         'opp_score': 0,
         'kickoff': strftime("%a %I:%M %p ET", gmtime(kickoff)),
         'at_home': True if team2.getAttribute('isHome') == '1' else False,
         'result': None
      }
      teams[team2_id]['off_pass_rank'] = int(team2.getAttribute('passOffenseRank') or "0")
      teams[team2_id]['off_rush_rank'] = int(team2.getAttribute('rushOffenseRank') or "0")
      teams[team2_id]['def_pass_rank'] = int(team2.getAttribute('passDefenseRank') or "0")
      teams[team2_id]['def_rush_rank'] = int(team2.getAttribute('rushDefenseRank') or "0")
      
      if int(matchup.getAttribute('gameSecondsRemaining')) == 0:
         teams[team1_id]['weeks'][week]['score'] = int(team1.getAttribute('score'))
         teams[team1_id]['weeks'][week]['opp_score'] = int(team2.getAttribute('score'))
         teams[team1_id]['pts_for'] += int(team1.getAttribute('score'))
         teams[team1_id]['pts_against'] += int(team2.getAttribute('score'))
         
         teams[team2_id]['weeks'][week]['score'] = int(team2.getAttribute('score'))
         teams[team2_id]['weeks'][week]['opp_score'] = int(team1.getAttribute('score'))
         teams[team2_id]['pts_for'] += int(team2.getAttribute('score'))
         teams[team2_id]['pts_against'] += int(team1.getAttribute('score'))
         
         if int(team1.getAttribute('score')) > int(team2.getAttribute('score')):
            teams[team1_id]['weeks'][week]['result'] = 'W'
            teams[team1_id]['win'] += 1
            teams[team1_id]['streak'] = (teams[team1_id]['streak'] + 1) if (teams[team1_id]['streak'] >= 0) else 1
            
            teams[team2_id]['weeks'][week]['result'] = 'L'
            teams[team2_id]['loss'] += 1
            teams[team2_id]['streak'] = (teams[team2_id]['streak'] - 1) if (teams[team2_id]['streak'] <= 0) else -1

         elif int(team1.getAttribute('score')) < int(team2.getAttribute('score')):
            teams[team1_id]['weeks'][week]['result'] = 'L'
            teams[team1_id]['loss'] += 1
            teams[team1_id]['streak'] = (teams[team1_id]['streak'] - 1) if (teams[team1_id]['streak'] <= 0) else -1
            
            teams[team2_id]['weeks'][week]['result'] = 'W'
            teams[team2_id]['win'] += 1
            teams[team2_id]['streak'] = (teams[team2_id]['streak'] + 1) if (teams[team2_id]['streak'] >= 0) else 1

         else:
            teams[team1_id]['weeks'][week]['result'] = 'T'
            teams[team1_id]['tie'] += 1
            teams[team1_id]['streak'] = 0
            
            teams[team2_id]['weeks'][week]['result'] = 'T'
            teams[team2_id]['tie'] += 1
            teams[team2_id]['streak'] = 0

   response.close()

pp = pprint.PrettyPrinter(indent=4)
pp.pprint(teams)


      