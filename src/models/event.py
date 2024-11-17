from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.models.rwmodel import RWModel as Base


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    start_datetime = Column(DateTime)
    end_datetime = Column(DateTime)
    video = Column(String, nullable=True)


class PlannedParticipant(Base):
    __tablename__ = 'planned_participants'

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id'))
    employee_id = Column(Integer, ForeignKey('employees.id'))

    event = relationship("Event", back_populates="participants")
    employee = relationship("Employee", back_populates="planned_participations")


Event.participants = relationship("PlannedParticipant", order_by=PlannedParticipant.id, back_populates="event")


class VisitInterval(Base):
    __tablename__ = 'visitinterval'

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id'))
    start_datetime= Column(DateTime)
    end_datetime= Column(DateTime)

    photo = Column(String, nullable=True)
    order = Column(Integer)

    employees = relationship("IntervalEmployee", back_populates="interval")

    event = relationship("Event", back_populates="visit_interval")


Event.visit_interval = relationship("VisitInterval", order_by=VisitInterval.order, back_populates="event")

class IntervalEmployee(Base):
    __tablename__ = 'interval_employee'

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id'))
    interval_id = Column(Integer, ForeignKey('visitinterval.id'))
    photo = Column(String)

    interval = relationship("VisitInterval", back_populates="employees")

    employee = relationship("Employee", back_populates="visit_intervals")


