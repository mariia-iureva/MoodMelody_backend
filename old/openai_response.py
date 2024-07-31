# app/models/openai_response.py

from ..db import db
from datetime import datetime


class OpenAIResponse(db.Model):
    __tablename__ = "openai_responses"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_text = db.Column(db.Text, nullable=False)
    response_text = db.Column(db.Text, nullable=False)
    songs = db.Column(db.JSON, nullable=False)  # Storing songs as JSON
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    session_id = db.Column(db.String, db.ForeignKey("users.session_id"), nullable=False)

    # Relationship to User
    user = db.relationship("User", back_populates="responses")

    def to_dict(self):
        return {
            "id": self.id,
            "request_text": self.request_text,
            "response_text": self.response_text,
            "songs": self.songs,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data_dict):
        new_response = cls(
            request_text=data_dict["request_text"],
            response_text=data_dict["response_text"],
            songs=data_dict["songs"],
            session_id=data_dict["session_id"],
        )
        return new_response
