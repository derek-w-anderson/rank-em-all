from xml.etree.ElementTree import Element, SubElement
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users
from models import *

def get_memcache_key(prefix, year=None, week=None, user=None, team=None):
   """
   Generate a key for the cache. 
   """
   key = prefix
   if year is not None:
      key += '-' + str(year) 
   if week is not None:
      key += '-' + str(week)
   if user is not None:
      key += '-' + str(user.user_id())
   if team is not None:
      key += '-' + team
      
   return key      
            

def get_setting(name, reload=False):
   """
   Check the cache to see if there is a cached setting.
   If not, query for it and update the cache. 

   Returns:
      An application setting. 
   """
   if name is None:
      return None
   
   key = get_memcache_key('setting-'+name)
   
   setting = memcache.get(key)
   if setting is None or reload:
      setting = AppSetting.get_by_key_name(name)
      memcache.set(key, setting)

   value = setting.value
   try:
      value = int(value)
   except ValueError:
      pass # NaN might be OK
	  
   return value
   
			
def get_profile(user, reload=False):
   """
   Check the cache to see if there is a cached profile.
   If not, query for it and update the cache. 

   Returns:
      A user profile. 
   """
   if user is None:
      return None
   
   key = get_memcache_key('profile', user=user)
   
   profile = memcache.get(key)
   if profile is None or reload:
      profile = UserProfile.get_by_key_name(user.user_id())
      memcache.set(key, profile)

   return profile
     
  
def get_teams(reload=False):
   """
   Check the cache to see if there are cached teams. 
   If not, query for them and update the cache.

   Returns:
      A dictionary of NFL teams. 
   """
   key = get_memcache_key('teams')
   
   teams = memcache.get(key)
   if teams is None or reload:
      teams = Team.all().order('nickname')
      memcache.set(key, teams)
         
   return teams
  
  
def get_records(year, reload=False):
   """
   Check the cache to see if there are cached team records. 
   If not, query them and update the cache. 

   Returns:
      A dictionary of team records. 
   """
   key = get_memcache_key('records', year=year)

   records = memcache.get(key)
   if records is None or reload:
      records = {}
      for record in Record.all().filter('year =', year):
         records[record.team.key().name()] = record
      
      memcache.set(key, records)
      
   return records
  
  
def get_matchups(year, week, reload=False):
   """
   Check the cache to see if there is cached matchup info. 
   If not, query for it and update the cache. 

   Returns:
      A dictionary of team matchups. 
   """
   key = get_memcache_key('matchups', year=year, week=week)

   matchups = memcache.get(key)
   if matchups is None or reload:
      matchups = {}
      for matchup in Matchup.all().filter('year =', year).filter('week =', week):
         matchups[matchup.team.key().name()] = matchup
      
      memcache.set(key, matchups)
      
   return matchups
   
      
def get_avg_rankings(year, week, reload=False):
   """
   Check the cache to see if there are average rankings for this year/week.
   If not, call query_rankings and update the cache.

   Returns:
      A dictionary of average rankings for each team. 
   """
   key = get_memcache_key('avg_rank', year=year, week=week)
   
   avg_rankings = memcache.get(key)
   if avg_rankings is None or reload:
      avg_rankings = {}
      for average in AverageRanking.all().filter('year =', year).filter('week =', week):
         avg_rankings[average.team.key().name()] = average
                   
      memcache.set(key, avg_rankings)
                  
   return avg_rankings


def get_rankings(year, week, user, reload=False):
   """
   Check the cache to see if there are rankings for this year/week/user.
   If not, call query_rankings and update the cache.

   Returns:
      A dictionary of team rankings, records, and matchups. 
   """
   key = get_memcache_key('rank', year=year, week=week, user=user)
   
   rankings = memcache.get(key)
   if rankings is None or reload:
      rankings = query_rankings(year, week, user)
         
   return rankings
         
   
def query_rankings(year, week, user):
   """
   Queries the datastore for team matchup, record, and ranking info. 
   """
   records = get_records(year, reload=True)
   matchups = get_matchups(year, week, reload=True)
            
   saved_rankings = {}
   for saved_ranking in Ranking.all().filter('year =', year).filter('week =', week).filter('user =', user): 
      saved_rankings[saved_ranking.team.key().name()] = saved_ranking
   
   prev_rankings = {}
   if week > 1:
      for prev_ranking in Ranking.all().filter('year =', year).filter('week =', week-1).filter('user =', user):      
         prev_rankings[prev_ranking.team.key().name()] = prev_ranking
         has_prev_ranks = True
         
   rankings = {}
   teams = get_teams()
   for i, team in enumerate(teams):
      team_id = team.key().name()
   
      # Get team record, net points and current streak:
      record_obj = records[team_id]
        
      record = '-'
      if record_obj: 
         record = str(record_obj.wins) + '-' + str(record_obj.losses)
         if record_obj.ties > 0:
            record += '-' + str(record_obj.ties)

      net_pts = '0'
      if record_obj:
         value = record_obj.pts_for - record_obj.pts_against
         if value > 0:
            net_pts = '<span class="green">+' + str(value) + '</span>'
         elif value < 0:
            net_pts = '<span class="red">' + str(value) + '</span>'

      streak = '-' 
      if record_obj:
         if record_obj.streak > 0:
            streak = '<span class="green">' + str(record_obj.streak) + 'W</span>'
         elif record_obj.streak < 0:
            streak = '<span class="red">' + str(abs(record_obj.streak)) + 'L</span>'
            
      dvoa = '-' if not record_obj or not record_obj.dvoa else record_obj.dvoa     
      
      # Get team matchup:
      match_obj = None if not matchups.has_key(team_id) else matchups[team_id]
      matchup = ''
      if match_obj and match_obj.result:
         #span_class = ''
         #if match_obj.result == 'W':
         #   span_class = 'green' 
         #elif match_obj.result == 'L':
         #   span_class = 'red'
         #matchup = '<span class="' + span_class + '">' + match_obj.result + '</span> ' 
         matchup += str(match_obj.score) + '-' + str(match_obj.opp_score) + ' '
      
      if match_obj and not match_obj.at_home:
         matchup += '@' + match_obj.opp_team
      elif match_obj:
         matchup += match_obj.opp_team
      else:
         matchup += 'Bye'
                     
      # Get saved ranking:  
      rank = (i + 1) if not saved_rankings.has_key(team_id) else saved_rankings[team_id].rank
      
      # Get previous week's ranking:
      prev_rank = None if not prev_rankings.has_key(team_id) else prev_rankings[team_id].rank
               
      rankings[rank] = {
         'team_id': team_id,
         'team_logo_url': team.logo_url,
         'team_name': team.location + ' ' + team.nickname,
         'prev_rank': prev_rank,
         'matchup': matchup,
         'record': record,
         'net_pts': net_pts,
         'streak': streak,
         'dvoa': dvoa
      }   
      
   # Update the cache:
   key = get_memcache_key('rank', year, week, user)
   memcache.set(key, rankings)
      
   return rankings
   
   
def get_team_info(year, team_id, reload=False):
   """
   Check the cache to see if there is cached team info. 
   If not, query for it and update the cache.

   Returns:
      An XML representation of a team. 
   """
   key = get_memcache_key('team-info', year=year, team=team_id)
   
   team_info = memcache.get(key)
   if team_info is None or reload:
      team = Team.get_by_key_name(team_id)
      if not team:
         return None
    
      team_info = Element('team')
      id = SubElement(team_info, 'id')  
      id.text = team_id
      
      name = SubElement(team_info, 'name')  
      name.text = team.location + ' ' + team.nickname
      
      # Add record:
      record = get_records(int(year))[team_id]
      wins = SubElement(team_info, 'wins')  
      wins.text = str(record.wins)
      
      losses = SubElement(team_info, 'losses')  
      losses.text = str(record.losses)
      
      ties = SubElement(team_info, 'ties')        
      ties.text = str(record.ties)

      # Add offensive/defensive ranks:
      off_pass_rank = SubElement(team_info, 'off_pass_rank')  
      off_pass_rank.text = ordinal(record.off_pass_rank)
      
      off_rush_rank = SubElement(team_info, 'off_rush_rank')  
      off_rush_rank.text = ordinal(record.off_rush_rank)
      
      def_pass_rank = SubElement(team_info, 'def_pass_rank')  
      def_pass_rank.text = ordinal(record.def_pass_rank)
      
      def_rush_rank = SubElement(team_info, 'def_rush_rank')  
      def_rush_rank.text = ordinal(record.def_rush_rank)
      
      # Add matchups:
      weeks = SubElement(team_info, 'weeks')      
      matchups = Matchup.all().filter('year =', int(year)).filter('team =', team).order('-week')
      for matchup in matchups:
         if not matchup.result:
            continue
         
         week = SubElement(weeks, 'week')
         number = SubElement(week, 'number')
         opponent = SubElement(week, 'opponent')
         result = SubElement(week, 'result')
         score = SubElement(week, 'score')
         
         number.text = str(matchup.week)
         opponent.text = matchup.opp_team if matchup.at_home else ('@' + matchup.opp_team)
         result.text = matchup.result
         score.text = str(matchup.score) + '-' + str(matchup.opp_score)
         
      memcache.set(key, team_info)
         
   return team_info

   
def ordinal(value):
   """
   Converts zero or a *postive* integer to an ordinal value.
   """
   try:
      value = int(value)
   except ValueError:
      return value

   if value % 100//10 != 1:
      if value % 10 == 1:
         ordval = u"%d%s" % (value, "st")
      elif value % 10 == 2:
         ordval = u"%d%s" % (value, "nd")
      elif value % 10 == 3:
         ordval = u"%d%s" % (value, "rd")
      else:
         ordval = u"%d%s" % (value, "th")
   else:
      ordval = u"%d%s" % (value, "th")

   return ordval