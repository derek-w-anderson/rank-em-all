import webapp2 as web
import urllib2 
import jinja2
import os
from google.appengine.ext import db
from google.appengine.api import users
from datetime import datetime
from xml.dom import minidom
from constants import *
from models import *
from tasks import *

jinja_environment = jinja2.Environment(
   loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class RankingPage(web.RequestHandler):
   def get(self):
      current_year = datetime.now().year
      week = self.request.get('week')
      has_prev_ranks = False
      display_avg = False
      
      # Check parameters:
      if not week:
         week = CURRENT_WEEK 
      else:
         try:
            week = int(week)
            if week < 1 or week > CURRENT_WEEK:
               raise ValueError
         except ValueError:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('Bad parameter.')
            return
         
      user = users.get_current_user()
      if user:
         profile = UserProfile.get_by_key_name(user.user_id())
         if profile:
            display_avg = profile.display_avg 

         rankings = {}
         teams = Team.all().order('nickname')
         for i, team in enumerate(teams):
            # Get team record:
            record_obj = team.records.filter('year =', current_year).get()
            record = str(record_obj.wins) + '-' + str(record_obj.losses)
            if (record_obj.ties > 0):
               record += '-' + str(record_obj.ties)
            
            # Get team matchup:
            match_obj = team.matchups.filter('year =', current_year).filter('week =', week).get()
            matchup = ''
            if match_obj and match_obj.result:
               span_class = ''
               if match_obj.result == 'W':
                  span_class = 'green' 
               elif match_obj.result == 'L':
                  span_class = 'red'
               matchup = '<span class="' + span_class + '">' + match_obj.result + '</span> ' 
               matchup += str(match_obj.score) + '-' + str(match_obj.opp_score) + ' '
            
            if match_obj and not match_obj.at_home:
               matchup += '@' + match_obj.opp_team
            elif match_obj:
               matchup += match_obj.opp_team
            else:
               matchup += 'Bye'
                           
            # Get saved ranking: 
            rank_obj = team.rankings.filter('year =', current_year).filter('week =', week).filter('user =', user).get()      
            rank = (i + 1) if not rank_obj else rank_obj.rank
            
            # Get previous week's ranking:
            prev_rank = None
            if week > 1:
               prev_rank_obj = team.rankings.filter('year =', current_year).filter('week =', week-1).filter('user =', user).get()      
               if prev_rank_obj:
                  prev_rank = prev_rank_obj.rank
                  has_prev_ranks = True
            
            # Get average ranking:
            avg_rank_obj = team.averages.filter('year =', current_year).filter('week =', week).get()
            average = float(i + 1) if not avg_rank_obj else avg_rank_obj.rank
            
            rankings[rank] = {
               'team_id': team.key().name(),
               'team_name': team.location + ' ' + team.nickname,
               'prev_rank': prev_rank,
               'average': average,
               'record': record,
               'matchup': matchup
            }            
         template = jinja_environment.get_template('index.html')
         self.response.out.write(template.render({
            'rankings': rankings,
            'has_prev_ranks': has_prev_ranks,
            'display_avg': display_avg,
            'current_week': CURRENT_WEEK,
            'selected_week': week,
            'export_cell': str(chr(98+week)).upper(),
            'status': self.request.get('status'),
            'last_updated': DEPLOY_DATE
         }))
            
      else:
         self.redirect(users.create_login_url(self.request.uri))
  
   def post(self):
      current_year = datetime.now().year
      week = self.request.get('week')
      
      # Check parameters:
      if not week:
         week = CURRENT_WEEK 
      else:
         try:
            week = int(week)
            if week < 1 or week > CURRENT_WEEK:
               raise ValueError
         except ValueError:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('Bad parameter.')
            return
            
      user = users.get_current_user()
      if user:
         teams = Team.all().order('nickname')

         # Store submitted rankings:
         for team in teams:
            key_name = str(current_year)+'-'+str(week)+'-'+team.key().name()+'-'+str(user.user_id())
            ranking = Ranking.get_or_insert(
               key_name, # 2011-8-ARI-ander1dw
               year=current_year,
               week=week,
               team=team,
               user=user
            )
            submitted_rank = self.request.POST['hidden-'+team.key().name()]
            if not submitted_rank:
               submitted_rank = -1
            else:
               try:
                  submitted_rank = int(submitted_rank)
                  if submitted_rank < 1 or submitted_rank > 32:
                     raise ValueError
               except ValueError:
                  submitted_rank = -1
            ranking.rank = submitted_rank 
            ranking.put()

         # Update the average ranking:            
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
            
         self.redirect('/rank?week='+str(week)+'&status=saved')
            
      else:
         self.redirect(users.create_login_url(self.request.uri))
  
  
class DisplayAverageUpdater(web.RequestHandler):
   def post(self):
      user = users.get_current_user()
      week = self.request.POST['week']
      display_avg = self.request.POST['display_avg']

      # Check parameters:
      if not user or not week or not display_avg:
         self.response.headers['Content-Type'] = 'text/plain'
         self.response.out.write('Bad POST data.')
         return
         
      try:
         week = int(week)
         if week < 1 or week > CURRENT_WEEK:
            raise ValueError
            
         if display_avg not in ('Y', 'N'):
            raise ValueError
          
         profile = UserProfile.get_or_insert(user.user_id(), user=user)
         profile.display_avg = ('Y' == display_avg)
         profile.put()
            
      except ValueError:
         self.response.headers['Content-Type'] = 'text/plain'
         self.response.out.write('Bad parameter.')
         return
      
      self.redirect('/rank?week='+str(week))
  
  
urls = [
   ('/rank', RankingPage),
   ('/update_display_avg', DisplayAverageUpdater),
   ('/tasks/update_teams', MatchupAndRecordUpdater),
   ('/tasks/load_teams', TeamLoader),
   ('/tasks/calculate_averages', AverageRankingCalculator),
   ('/tasks/copy_rankings', RankingCopier)
]
app = web.WSGIApplication(urls, debug=False)
