import webapp2 as web
import urllib2 
import jinja2
import logging
import os
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users
from datetime import datetime
from xml.dom import minidom
from constants import *
from models import *
from cache import *
from tasks import *

logging.getLogger().setLevel(logging.DEBUG)

jinja_environment = jinja2.Environment(
   loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class RankingPage(web.RequestHandler):
   def get(self):
      current_year = datetime.now().year
      week = self.request.get('week')
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
         
      # Make sure user is in session:
      user = users.get_current_user()
      if not user:
         self.redirect(users.create_login_url(self.request.uri), abort=True)
      
      # Get user's profile (may not exist):
      profile = get_profile(user)
      display_avg = False if not profile else profile.display_avg
      
      # Get team info:
      rankings = get_rankings(current_year, week, user)
      avg_rankings = None if not display_avg else get_avg_rankings(current_year, week)
         
      template = jinja_environment.get_template('index.html')
      self.response.out.write(template.render({
         'rankings': rankings,
         'avg_rankings': avg_rankings,
         'has_prev_ranks': True if rankings[1]['prev_rank'] is not None else False,
         'display_avg': display_avg,
         'current_week': CURRENT_WEEK,
         'selected_week': week,
         'export_cell': str(chr(98+week)).upper(),
         'status': self.request.get('status'),
         'last_updated': DEPLOY_DATE
      }))     
          
  
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
         
      # Make sure user is in session:
      user = users.get_current_user()
      if not user:
         self.redirect(users.create_login_url(self.request.uri), abort=True)
         
      teams = get_teams()

      # Save submitted rankings:
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

      # Update average rankings:            
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
      get_rankings(current_year, week, user, reload=True)
      get_avg_rankings(current_year, week, reload=True)
         
      self.redirect('/rank?week='+str(week)+'&status=saved')

  
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
         
         # Update the cache:
         get_profile(user, reload=True)
            
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
   ('/tasks/copy_rankings', RankingCopier),
   ('/tasks/update_cache', CacheUpdater)
]
app = web.WSGIApplication(urls, debug=False)
