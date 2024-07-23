from ..db import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String, unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to OpenAIResponse
    responses = db.relationship('OpenAIResponse', back_populates='user')

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data_dict):
        new_user = cls(
            session_id=data_dict["session_id"]
        )
        return new_user
