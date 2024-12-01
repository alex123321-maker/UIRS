from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, column
from sqlalchemy.orm import relationship
from src.models.rwmodel import RWModel as Base


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    start_datetime = Column(DateTime)
    end_datetime = Column(DateTime)
    video = Column(String, nullable=True)

    visit_intervals = relationship(
        "VisitInterval",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="joined"
    )

    participants = relationship(
        "PlannedParticipant",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="joined"
    )



class PlannedParticipant(Base):
    __tablename__ = 'planned_participants'

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id'))
    employee_id = Column(Integer, ForeignKey('employees.id'))

    event = relationship("Event", back_populates="participants", lazy="joined")
    employee = relationship("Employee", back_populates="planned_participations", lazy="joined")




class VisitInterval(Base):
    __tablename__ = 'visitinterval'

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id'))
    start_datetime= Column(DateTime)
    end_datetime= Column(DateTime)

    max_unregistered = Column(Integer, default=0)
    max_unregistered_photo = Column(String, nullable=True)
    order = Column(Integer)

    employees = relationship(
        "IntervalEmployee",
        back_populates="interval",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    event = relationship("Event", back_populates="visit_intervals")



class IntervalEmployee(Base):
    __tablename__ = 'interval_employee'

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete="CASCADE"))
    interval_id = Column(Integer, ForeignKey('visitinterval.id', ondelete="CASCADE"))
    first_spot_datetime = Column(DateTime)
    photo = Column(String)

    interval = relationship("VisitInterval", back_populates="employees")
    employee = relationship("Employee", back_populates="visit_intervals")


