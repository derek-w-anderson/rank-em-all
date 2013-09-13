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
         xml = minidom.parse(urlopen(url))

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

      #dvoa_rankings = self.get_dvoa_rankings(current_year)
      
      for team_id in teams.keys():
         team = teams[team_id]
         team_obj = Team.get_by_key_name(team_id)

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
         record.off_pass_rank = team['off_pass_rank']
         record.off_rush_rank = team['off_rush_rank']
         record.def_pass_rank = team['def_pass_rank']
         record.def_rush_rank = team['def_rush_rank']
         
         #if dvoa_rankings is not None:
         #   record.dvoa = dvoa_rankings[team_id][1] 
            
         record.put()

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
        
   def get_dvoa_rankings(self, year):
      acronym_mapping = {}
      acronym_mapping['NE']  = 'NEP'
      acronym_mapping['SEA'] = 'SEA'
      acronym_mapping['DEN'] = 'DEN'
      acronym_mapping['SF']  = 'SFO'
      acronym_mapping['GB']  = 'GBP'
      acronym_mapping['CHI'] = 'CHI'
      acronym_mapping['NYG'] = 'NYG'
      acronym_mapping['HOU'] = 'HOU'
      acronym_mapping['BAL'] = 'BAL'
      acronym_mapping['WAS'] = 'WAS'
      acronym_mapping['ATL'] = 'ATL'
      acronym_mapping['CIN'] = 'CIN'
      acronym_mapping['DET'] = 'DET'
      acronym_mapping['TB']  = 'TBB'
      acronym_mapping['PIT'] = 'PIT'
      acronym_mapping['CAR'] = 'CAR'    
      acronym_mapping['DAL'] = 'DAL'    
      acronym_mapping['MIN'] = 'MIN'    
      acronym_mapping['STL'] = 'STL'    
      acronym_mapping['MIA'] = 'MIA'    
      acronym_mapping['BUF'] = 'BUF'    
      acronym_mapping['NO']  = 'NOS'  
      acronym_mapping['SD']  = 'SDC'    
      acronym_mapping['NYJ'] = 'NYJ'    
      acronym_mapping['CLE'] = 'CLE'    
      acronym_mapping['PHI'] = 'PHI'    
      acronym_mapping['ARI'] = 'ARI'    
      acronym_mapping['IND'] = 'IND'   
      acronym_mapping['TEN'] = 'TEN'   
      acronym_mapping['OAK'] = 'OAK'   
      acronym_mapping['JAC'] = 'JAC'   
      acronym_mapping['KC']  = 'KCC'  
      
      url = 'http://www.footballoutsiders.com/stats/teameff%d' % (year)
      try:
         html = BeautifulSoup(urlopen(url))
         tables = html.find_all('table', class_="stats")
         if not tables:
            raise URLError(404, 'Missing DVOA tables')        
      except URLError:
         return None
        
      dvoa_rankings = {}
      for row in tables[0].find_all('tr'):
         cells = row.find_all('td')
         rank = cells[0].string
         if rank is not None:
            team = cells[1].string
            dvoa = cells[2].string
            dvoa_rankings[acronym_mapping[team]] = (rank, dvoa)
            
      return dvoa_rankings

      
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
      
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.out.write('Settings loaded successfully.')
      