from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.models.rwmodel import RWModel as Base


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    start_datetime = Column(DateTime)
    end_datetime = Column(DateTime)


class PlannedParticipant(Base):
    __tablename__ = 'planned_participants'

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id'))
    employee_id = Column(Integer, ForeignKey('employees.id'))

    event = relationship("Event", back_populates="participants")
    employee = relationship("Employee", back_populates="planned_participations")


Event.participants = relationship("PlannedParticipant", order_by=PlannedParticipant.id, back_populates="event")


class Visit(Base):
    __tablename__ = 'visits'

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id'))
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)
    visit_datetime = Column(DateTime)
    photo = Column(String)

    event = relationship("Event", back_populates="visits")
    employee = relationship("Employee", back_populates="visits")


Event.visits = relationship("Visit", order_by=Visit.id, back_populates="event")
