import webapp2 as web
from urllib2 import urlopen
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users
from datetime import datetime
from time import strftime, gmtime
from xml.dom import minidom
from constants import *
from models import *
from views import *

class CacheUpdater(web.RequestHandler):
   def get(self):
      current_year = datetime.now().year

      # Clear the cache:
      cleared = memcache.flush_all()
      
      # Repopulate the cache:
      if cleared:
         get_teams(reload=True)
         get_records(current_year, reload=True)
         
         for week in range(1, CURRENT_WEEK+1):
            get_matchups(current_year, week, reload=True)
         
         for team in get_teams():
            get_team_info(current_year, team.key().name(), reload=True)
      
         self.response.headers['Content-Type'] = 'text/plain'
         self.response.out.write('Cache updated successfully.')
      
      else:
         self.response.headers['Content-Type'] = 'text/plain'
         self.response.out.write('Cache could not be cleared.')
         

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
            )
         copied_ranking.rank = ranking.rank
         copied_ranking.put()

      # Update the average ranking:
      teams = Team.all().order('nickname')
      for team in teams:
         rankings = team.rankings.filter('year =', to_year).filter('week =', to_week)
         if rankings:
            avg = AverageRanking.get_or_insert(
               str(to_year)+'-'+str(to_week)+'-'+team.key().name(), # 2011-8-ARI
               year=to_year,
               week=to_week,
               team=team
            )
            sum = 0
            for ranking in rankings:
               sum += ranking.rank
            avg.rank = round(sum / float(rankings.count()), 1)
            avg.put()

      # Update the cache:
      get_avg_rankings(to_year, to_week, reload=True)
            
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.out.write('Rankings copied successfully.')


class AverageRankingCalculator(web.RequestHandler):
   def get(self):
      current_year = datetime.now().year
      week = int(self.request.get('week'))

      teams = Team.all().order('nickname')
      for team in teams:
         rankings = team.rankings.filter('year =', current_year).filter('week =', week)
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
      offset = 4 * (60 * 60)  # adjusts kickoff time to ET
      current_year = datetime.now().year

      teams = {}
      for week in range(1, CURRENT_WEEK+1):
         url = API_URL % (current_year, week)
         xml = minidom.parse(urlopen(url))

         for matchup in xml.getElementsByTagName('matchup'):
            kickoff = int(matchup.getAttribute('kickoff')) - offset
            team1 = matchup.getElementsByTagName('team')[0]
            team1_id = team1.getAttribute('id')
            team2 = matchup.getElementsByTagName('team')[1]
            team2_id = team2.getAttribute('id')

            if not teams.has_key(team1_id): teams[team1_id] = {}
            if not teams.has_key(team2_id): teams[team2_id] = {}
            if not teams[team1_id].has_key('weeks'): teams[team1_id]['weeks'] = {}
            if not teams[team1_id].has_key('win'):   teams[team1_id]['win'] = 0
            if not teams[team1_id].has_key('loss'):  teams[team1_id]['loss'] = 0
            if not teams[team1_id].has_key('tie'):   teams[team1_id]['tie'] = 0
            if not teams[team2_id].has_key('weeks'): teams[team2_id]['weeks'] = {}
            if not teams[team2_id].has_key('win'):   teams[team2_id]['win'] = 0
            if not teams[team2_id].has_key('loss'):  teams[team2_id]['loss'] = 0
            if not teams[team2_id].has_key('tie'):   teams[team2_id]['tie'] = 0

            teams[team1_id]['weeks'][week] = {
               'score': 0,
               'opp_team': team2_id,
               'opp_score': 0,
               'kickoff': strftime("%a %I:%M %p ET", gmtime(kickoff)),
               'at_home': True if team1.getAttribute('isHome') == '1' else False,
               'result': None
            }
            teams[team2_id]['weeks'][week] = {
               'score': 0,
               'opp_team': team1_id,
               'opp_score': 0,
               'kickoff': strftime("%a %I:%M %p ET", gmtime(kickoff)),
               'at_home': True if team2.getAttribute('isHome') == '1' else False,
               'result': None
            }
            if int(matchup.getAttribute('gameSecondsRemaining')) == 0:
               teams[team1_id]['weeks'][week]['score'] = int(team1.getAttribute('score'))
               teams[team1_id]['weeks'][week]['opp_score'] = int(team2.getAttribute('score'))
               teams[team2_id]['weeks'][week]['score'] = int(team2.getAttribute('score'))
               teams[team2_id]['weeks'][week]['opp_score'] = int(team1.getAttribute('score'))

               if int(team1.getAttribute('score')) > int(team2.getAttribute('score')):
                  teams[team1_id]['weeks'][week]['result'] = 'W'
                  teams[team1_id]['win'] += 1
                  teams[team2_id]['weeks'][week]['result'] = 'L'
                  teams[team2_id]['loss'] += 1

               elif int(team1.getAttribute('score')) < int(team2.getAttribute('score')):
                  teams[team1_id]['weeks'][week]['result'] = 'L'
                  teams[team1_id]['loss'] += 1
                  teams[team2_id]['weeks'][week]['result'] = 'W'
                  teams[team2_id]['win'] += 1

               else:
                  teams[team1_id]['weeks'][week]['result'] = 'T'
                  teams[team1_id]['tie'] += 1
                  teams[team2_id]['weeks'][week]['result'] = 'T'
                  teams[team2_id]['tie'] += 1

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
      
      # Update the cache:
      self.redirect('/tasks/update_cache')


class TeamLoader(web.RequestHandler):
   def get(self):
      Team.get_or_insert('ARI', location='Arizona', nickname='Cardinals')
      Team.get_or_insert('BAL', location='Baltimore', nickname='Ravens')
      Team.get_or_insert('ATL', location='Atlanta', nickname='Falcons')
      Team.get_or_insert('DET', location='Detroit', nickname='Lions')
      Team.get_or_insert('BUF', location='Buffalo', nickname='Bills')
      Team.get_or_insert('CIN', location='Cincinatti', nickname='Bengals')
      Team.get_or_insert('IND', location='Indianapolis', nickname='Colts')
      Team.get_or_insert('TEN', location='Tennessee', nickname='Titans')
      Team.get_or_insert('MIA', location='Miami', nickname='Dolphins')
      Team.get_or_insert('NYJ', location='New York', nickname='Jets')
      Team.get_or_insert('CLE', location='Cleveland', nickname='Browns')
      Team.get_or_insert('HOU', location='Houston', nickname='Texans')
      Team.get_or_insert('JAC', location='Jacksonville', nickname='Jaguars')
      Team.get_or_insert('MIN', location='Minnesota', nickname='Vikings')
      Team.get_or_insert('CHI', location='Chicago', nickname='Bears')
      Team.get_or_insert('CAR', location='Carolina', nickname='Panthers')
      Team.get_or_insert('TBB', location='Tampa Bay', nickname='Buccaneers')
      Team.get_or_insert('KCC', location='Kansas City', nickname='Chiefs')
      Team.get_or_insert('DEN', location='Denver', nickname='Broncos')
      Team.get_or_insert('DAL', location='Dallas', nickname='Cowboys')
      Team.get_or_insert('NYG', location='New York', nickname='Giants')
      Team.get_or_insert('SEA', location='Seattle', nickname='Seahawks')
      Team.get_or_insert('STL', location='St. Louis', nickname='Rams')
      Team.get_or_insert('SFO', location='San Francisco', nickname='49ers')
      Team.get_or_insert('NEP', location='New England', nickname='Patriots')
      Team.get_or_insert('PIT', location='Pittsburgh', nickname='Steelers')
      Team.get_or_insert('PHI', location='Philadeplhia', nickname='Eagles')
      Team.get_or_insert('WAS', location='Washington', nickname='Redskins')
      Team.get_or_insert('GBP', location='Green Bay', nickname='Packers')
      Team.get_or_insert('SDC', location='San Diego', nickname='Chargers')
      Team.get_or_insert('OAK', location='Oakland', nickname='Raiders')
      Team.get_or_insert('NOS', location='New Orleans', nickname='Saints')

      # Update the cache:
      get_teams(reload=True)
      
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.out.write('Teams loaded successfully.')
