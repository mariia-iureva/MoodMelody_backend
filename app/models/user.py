from ..db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), unique=True, nullable=False)
    access_token = db.Column(db.String(), nullable=False)
    refresh_token = db.Column(db.String(), nullable=False)

    def __init__(self, session_id, access_token, refresh_token):
        self.session_id = session_id
        self.access_token = access_token
        self.refresh_token = refresh_token
