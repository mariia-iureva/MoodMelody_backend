from ..db import db
from datetime import datetime

class SearchHistory(db.Model):
    __tablename__ = "search_history"

    id = db.Column(db.Integer, primary_key=True)
    spotify_user_id = db.Column(db.String(255))
    search_query = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.now)
    spotify_link = db.Column(db.String(255))

    # Relationship to User
    # user = db.relationship('User', back_populates='search_histories')

    def __init__(self, spotify_user_id, search_query, spotify_link):
        self.spotify_user_id = spotify_user_id
        self.search_query = search_query
        self.spotify_link = spotify_link