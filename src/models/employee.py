from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.models.rwmodel import RWModel as Base

class Department(Base):
    __tablename__ = 'departments'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)


class Position(Base):
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)


class Employee(Base):
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    surname = Column(String, index=True)
    patronymic = Column(String,nullable=True)
    position_id = Column(Integer, ForeignKey('positions.id'))
    department_id = Column(Integer, ForeignKey('departments.id'))

    position = relationship("Position", back_populates="employees", lazy="joined")
    department = relationship("Department", back_populates="employees", lazy="joined")
    planned_participations = relationship("PlannedParticipant", back_populates="employee", lazy="joined")
    visit_intervals = relationship("IntervalEmployee", back_populates="employee", lazy="joined")
    photos = relationship("EmployeePhoto", back_populates="employee", cascade="all,delete-orphan", lazy="joined")

Position.employees = relationship("Employee", order_by=Employee.id, back_populates="position", lazy="joined")
Department.employees = relationship("Employee", order_by=Employee.id, back_populates="department", lazy="joined")


class EmployeePhoto(Base):
    __tablename__ = 'employee_photos'

    id = Column(Integer, primary_key=True, index=True)
    photo = Column(String)
    employee_id = Column(Integer, ForeignKey('employees.id'))

    employee = relationship("Employee", back_populates="photos", lazy="joined")


Employee.photos = relationship("EmployeePhoto", order_by=EmployeePhoto.id, back_populates="employee",cascade="all, delete", lazy="joined")
