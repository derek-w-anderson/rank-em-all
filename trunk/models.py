from google.appengine.ext import db

class Team(db.Model):
   location = db.StringProperty()
   nickname = db.StringProperty()
   last_updated = db.DateTimeProperty(auto_now=True)

class Record(db.Model):
   year = db.IntegerProperty()
   team = db.ReferenceProperty(Team, collection_name="records")
   wins = db.IntegerProperty()
   losses = db.IntegerProperty()
   ties = db.IntegerProperty()
   dvoa = db.StringProperty()
   last_updated = db.DateTimeProperty(auto_now=True)
        
class Matchup(db.Model):
   year = db.IntegerProperty()
   week = db.IntegerProperty()
   team = db.ReferenceProperty(Team, collection_name="matchups")
   score = db.IntegerProperty()
   opp_team = db.StringProperty()
   opp_score = db.IntegerProperty()
   kickoff = db.StringProperty()
   at_home = db.BooleanProperty()
   result = db.StringProperty()
   last_updated = db.DateTimeProperty(auto_now=True)
    
class Ranking(db.Model):
   year = db.IntegerProperty()
   week = db.IntegerProperty()
   rank = db.IntegerProperty()
   team = db.ReferenceProperty(Team, collection_name="rankings")
   user = db.UserProperty()
   updated_by_user = db.BooleanProperty()
   last_updated = db.DateTimeProperty(auto_now=True)
    
class AverageRanking(db.Model):
   year = db.IntegerProperty()
   week = db.IntegerProperty()
   rank = db.FloatProperty()
   team = db.ReferenceProperty(Team, collection_name="averages")
   last_updated = db.DateTimeProperty(auto_now=True)
   
class UserProfile(db.Model):
   user = db.UserProperty()
   nickname = db.StringProperty()
   display_avg = db.BooleanProperty()
   display_dvoa = db.BooleanProperty()
   last_updated = db.DateTimeProperty(auto_now=True)
   
class AppSetting(db.Model):
	value = db.StringProperty()
	
	