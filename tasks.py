import logging
import webapp2 as web
from urllib2 import urlopen, URLError
from bs4 import BeautifulSoup
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users
from datetime import datetime
from time import strftime, gmtime
from xml.dom import minidom
from cache import *
from models import *
from views import *

class CacheUpdater(web.RequestHandler):
   def get(self):
      current_year = get_setting('year')
      current_week = get_setting('week')
      teams_updated = self.request.get('teams_updated')
      
      status = ''
      if teams_updated is not None and teams_updated == 'Y':
         status = 'Teams updated successfully. '
      elif teams_updated is not None and teams_updated == 'N':
         status = 'Teams were not updated. '
      
      # Clear the cache:
      cleared = memcache.flush_all()
      
      # Repopulate the cache:
      if cleared:
         get_teams(reload=True)
         get_records(current_year, reload=True)
         get_setting('median-pya', reload=True)
         
         for week in range(1, current_week+1):
            get_matchups(current_year, week, reload=True)
         
         for team in get_teams():
            get_team_info(current_year, team.key().name(), reload=True)
            
         self.response.headers['Content-Type'] = 'text/plain'
         self.response.out.write(status + 'Cache updated successfully.')
      
      else:
         self.response.headers['Content-Type'] = 'text/plain'
         self.response.out.write(status + 'Cache could not be cleared.')
         

class RankingCopier(web.RequestHandler):
   def get(self):
      from_year = int(self.request.get('from_year'))
      from_week = int(self.request.get('from_week'))
      to_year = int(self.request.get('to_year'))
      to_week = int(self.request.get('to_week'))
      
      # Copy rankings from one week to another:
      old_rankings = []
      rankings = Ranking.all().filter('year =', from_year).filter('week =', from_week)
      for ranking in rankings:
         old_rankings.append(ranking)
         
      for ranking in old_rankings:
         key_name = str(to_year)+'-'+str(to_week)+'-'+ranking.team.key().name()+'-'+str(ranking.user.user_id())
         copied_ranking = Ranking.get_or_insert(
            key_name, # 2011-8-ARI-ander1dw
            year=to_year,
            week=to_week,
            team=ranking.team,
            user=ranking.user,
            updated_by_user=False
         )
         copied_ranking.rank = ranking.rank
         copied_ranking.put()
            
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.out.write('Rankings copied successfully.')


class AverageRankingCalculator(web.RequestHandler):
   def get(self):
      current_year = get_setting('year')
      week = int(self.request.get('week'))

      teams = Team.all().order('nickname')
      for team in teams:
         rankings = team.rankings.filter('year =', current_year).filter('week =', week).filter('updated_by_user =', True)
         if rankings:
            avg = AverageRanking.get_or_insert(
               str(current_year)+'-'+str(week)+'-'+team.key().name(), # 2011-8-ARI
               year=current_year,
               week=week,
               team=team
            )
            sum = 0
            for ranking in rankings:
               sum += ranking.rank
            avg.rank = round(sum / float(rankings.count()), 1)
            avg.put()

      # Update the cache:
      get_avg_rankings(current_year, week, reload=True)
       
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.out.write('Averages calculated successfully.')


class MatchupAndRecordUpdater(web.RequestHandler):   
   def get(self):
      teams_updated = False
      offset = 4 * (60 * 60)  # adjusts kickoff time to ET
      current_year = get_setting('year')
      current_week = get_setting('week')
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
                  
      # Get passing stats:
      passing_stats = self.get_passing_stats(current_year)
      if passing_stats and len(passing_stats) == 32:
         all_pya = sorted(passing_stats.values())
         median_pya = (all_pya[15] + all_pya[16]) / 2.0
      
         setting = AppSetting.get_by_key_name('median-pya')
         setting.value = str(median_pya)
         setting.put()
      
      for team_id in teams.keys():
         team = teams[team_id]
         team_obj = Team.get_by_key_name(team_id)

         # Calculate strength of victory:
         opp_wins = 0
         opp_games = 0
         for week in team['weeks'].keys():
            matchup = team['weeks'][week]
            if not matchup['result'] or (matchup['score'] < matchup['opp_score']):
               continue
            opp_team = teams[matchup['opp_team']]
            opp_wins += opp_team['win'] + (opp_team['tie'] / 2.0)
            opp_games += opp_team['win'] + opp_team['loss'] + opp_team['tie']
         
         sov = None if not opp_games > 0 else opp_wins / float(opp_games)

         # Calculate strength of schedule:
         opp_wins = 0
         opp_games = 0
         for week in team['weeks'].keys():
            matchup = team['weeks'][week]
            if not matchup['result']:
               continue
            opp_team = teams[matchup['opp_team']]
            opp_wins += opp_team['win'] + (opp_team['tie'] / 2.0)
            opp_games += opp_team['win'] + opp_team['loss'] + opp_team['tie']
         
         sos = None if not opp_games > 0 else opp_wins / float(opp_games)
         
         # Get passing yards per attempt:
         pya = None
         if passing_stats:
            pya = passing_stats[team_id]
         
         # Update the team record object
         record = Record.get_or_insert(
            str(current_year)+'-'+team_id, # 2011-ARI
            year=current_year,
            team=team_obj,
         )
         record.wins = team['win']
         record.losses = team['loss']
         record.ties = team['tie']
         record.pts_for = team['pts_for']
         record.pts_against = team['pts_against']
         record.streak = team['streak']
         record.sov = sov
         record.sos = sos
         record.pya = pya
         record.off_pass_rank = team['off_pass_rank']
         record.off_rush_rank = team['off_rush_rank']
         record.def_pass_rank = team['def_pass_rank']
         record.def_rush_rank = team['def_rush_rank']           
         record.put()

         # Update team matchups
         for week in team['weeks'].keys():
            matchup = Matchup.get_or_insert(
               str(current_year)+'-'+str(week)+'-'+team_id, # 2011-8-ARI
               year=current_year,
               week=week,
               team=team_obj,
               opp_team=team['weeks'][week]['opp_team'],
               kickoff=team['weeks'][week]['kickoff'],
               at_home=team['weeks'][week]['at_home']
            )
            matchup.score = team['weeks'][week]['score']
            matchup.opp_score = team['weeks'][week]['opp_score']
            matchup.result = team['weeks'][week]['result']            
            matchup.put()
            teams_updated = True
      
      # Update the cache:
      self.redirect('/tasks/update_cache?teams_updated='+('Y' if teams_updated else 'N'))

   def get_passing_stats(self, current_year):
      acronym_mapping = {}
      acronym_mapping['New England']  = 'NEP'
      acronym_mapping['Seattle'] = 'SEA'
      acronym_mapping['Denver'] = 'DEN'
      acronym_mapping['San Francisco']  = 'SFO'
      acronym_mapping['Green Bay']  = 'GBP'
      acronym_mapping['Chicago'] = 'CHI'
      acronym_mapping['NY Giants'] = 'NYG'
      acronym_mapping['Houston'] = 'HOU'
      acronym_mapping['Baltimore'] = 'BAL'
      acronym_mapping['Washington'] = 'WAS'
      acronym_mapping['Atlanta'] = 'ATL'
      acronym_mapping['Cincinnati'] = 'CIN'
      acronym_mapping['Detroit'] = 'DET'
      acronym_mapping['Tampa Bay']  = 'TBB'
      acronym_mapping['Pittsburgh'] = 'PIT'
      acronym_mapping['Carolina'] = 'CAR'    
      acronym_mapping['Dallas'] = 'DAL'    
      acronym_mapping['Minnesota'] = 'MIN'    
      acronym_mapping['St. Louis'] = 'STL'    
      acronym_mapping['Miami'] = 'MIA'    
      acronym_mapping['Buffalo'] = 'BUF'    
      acronym_mapping['New Orleans']  = 'NOS'  
      acronym_mapping['San Diego']  = 'SDC'    
      acronym_mapping['NY Jets'] = 'NYJ'    
      acronym_mapping['Cleveland'] = 'CLE'    
      acronym_mapping['Philadelphia'] = 'PHI'    
      acronym_mapping['Arizona'] = 'ARI'    
      acronym_mapping['Indianapolis'] = 'IND'   
      acronym_mapping['Tennessee'] = 'TEN'   
      acronym_mapping['Oakland'] = 'OAK'   
      acronym_mapping['Jacksonville'] = 'JAC'   
      acronym_mapping['Kansas City']  = 'KCC' 
   
      url = 'http://espn.go.com/nfl/statistics/team/_/stat/passing/year/' + str(current_year)
      passing_stats = None
      try:
         html = BeautifulSoup(urlopen(url))
         
         h1 = html.find('h1')
         if not h1 or h1.string[-4:] != str(current_year):
            raise URLError('Current year stats not available')
         
         table = html.find(id='my-teams-table').find('table', {'class': 'tablehead'})
         if not table:
            raise URLError('Missing stat table')    

         passing_stats = {}
         rows = table.find_all('tr')
         for row in rows[1:]:
            cells = row.find_all('td')
            team_name = cells[1].string
            
            if cells[5].string != '0':
               # NY/A - net yards gained per pass attempt [pass yards / (passing attempts + sacks)]
               passing_stats[acronym_mapping[team_name]] = int(cells[5].string) / float(int(cells[2].string) + int(cells[10].string))
            else:
               passing_stats[acronym_mapping[team_name]] = 0.0
      except:
         logging.error('Could not load passing stats from ESPN.com')

      return passing_stats


class TeamLoader(web.RequestHandler):
   def get(self):
      Team.get_or_insert('ARI', location='Arizona', nickname='Cardinals', logo_url='//i.imgur.com/eBCLhfo.png')
      Team.get_or_insert('BAL', location='Baltimore', nickname='Ravens', logo_url='//i.imgur.com/2W8S9sk.png')
      Team.get_or_insert('ATL', location='Atlanta', nickname='Falcons', logo_url='//i.imgur.com/HOrt09X.png')
      Team.get_or_insert('DET', location='Detroit', nickname='Lions', logo_url='//i.imgur.com/nvCgKX8.png')
      Team.get_or_insert('BUF', location='Buffalo', nickname='Bills', logo_url='//i.imgur.com/jh2IILA.png')
      Team.get_or_insert('CIN', location='Cincinnati', nickname='Bengals', logo_url='//i.imgur.com/pmagTxP.png')
      Team.get_or_insert('IND', location='Indianapolis', nickname='Colts', logo_url='//i.imgur.com/xqBQRpq.png')
      Team.get_or_insert('TEN', location='Tennessee', nickname='Titans', logo_url='//i.imgur.com/HFR8qP1.png')
      Team.get_or_insert('MIA', location='Miami', nickname='Dolphins', logo_url='//i.imgur.com/JDIaapm.png')
      Team.get_or_insert('NYJ', location='New York', nickname='Jets', logo_url='//i.imgur.com/CtPkafN.png')
      Team.get_or_insert('CLE', location='Cleveland', nickname='Browns', logo_url='//i.imgur.com/hqh6UDM.png')
      Team.get_or_insert('HOU', location='Houston', nickname='Texans', logo_url='//i.imgur.com/5Yqoc4N.png')
      Team.get_or_insert('JAC', location='Jacksonville', nickname='Jaguars', logo_url='//i.imgur.com/f5rxwnC.png')
      Team.get_or_insert('MIN', location='Minnesota', nickname='Vikings', logo_url='//i.imgur.com/hrSbJ80.png')
      Team.get_or_insert('CHI', location='Chicago', nickname='Bears', logo_url='//i.imgur.com/mhknbih.png')
      Team.get_or_insert('CAR', location='Carolina', nickname='Panthers', logo_url='//i.imgur.com/TwPCje9.png')
      Team.get_or_insert('TBB', location='Tampa Bay', nickname='Buccaneers', logo_url='//i.imgur.com/XSZ4Tun.png')
      Team.get_or_insert('KCC', location='Kansas City', nickname='Chiefs', logo_url='//i.imgur.com/XJAohW1.png')
      Team.get_or_insert('DEN', location='Denver', nickname='Broncos', logo_url='//i.imgur.com/oprzcsR.png')
      Team.get_or_insert('DAL', location='Dallas', nickname='Cowboys', logo_url='//i.imgur.com/ci3roHx.png')
      Team.get_or_insert('NYG', location='New York', nickname='Giants', logo_url='//i.imgur.com/vnRA0ek.png')
      Team.get_or_insert('SEA', location='Seattle', nickname='Seahawks', logo_url='//i.imgur.com/PzKfAjA.png')
      Team.get_or_insert('STL', location='St. Louis', nickname='Rams', logo_url='//i.imgur.com/RXpnWBP.png')
      Team.get_or_insert('SFO', location='San Francisco', nickname='49ers', logo_url='//i.imgur.com/eusAn6o.png')
      Team.get_or_insert('NEP', location='New England', nickname='Patriots', logo_url='//i.imgur.com/d2x3A8w.png')
      Team.get_or_insert('PIT', location='Pittsburgh', nickname='Steelers', logo_url='//i.imgur.com/oK2OtUR.png')
      Team.get_or_insert('PHI', location='Philadelphia', nickname='Eagles', logo_url='//i.imgur.com/23CogLS.png')
      Team.get_or_insert('WAS', location='Washington', nickname='Redskins', logo_url='//i.imgur.com/bstfEdQ.png')
      Team.get_or_insert('GBP', location='Green Bay', nickname='Packers', logo_url='//i.imgur.com/jtHzuOR.png')
      Team.get_or_insert('SDC', location='San Diego', nickname='Chargers', logo_url='//i.imgur.com/DUXA4ax.png')
      Team.get_or_insert('OAK', location='Oakland', nickname='Raiders', logo_url='//i.imgur.com/EAFY79R.png')
      Team.get_or_insert('NOS', location='New Orleans', nickname='Saints', logo_url='//i.imgur.com/w1Id7n6.png')

      # Update the cache:
      get_teams(reload=True)
      
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.out.write('Teams loaded successfully.')

      
class SettingsLoader(web.RequestHandler):
   def get(self):
      AppSetting.get_or_insert('year', value='')
      AppSetting.get_or_insert('week', value='')
      AppSetting.get_or_insert('median-pya', value='')
      
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.out.write('Settings loaded successfully.')
      