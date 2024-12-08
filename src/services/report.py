from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.models.event import Event, VisitInterval, PlannedParticipant, IntervalEmployee
from src.models.employee import Employee, Department, Position, EmployeePhoto
from src.schemas.employee import EmployeeInfoPhoto, PhotoInfo
from src.schemas.report import ReportResponse, EmployeeVisit, IntervalFullInfo, IntervalUnregisteredInfo
from src.schemas.event import EventInfo


async def fetch_event_statistics(event_id: int, db: AsyncSession) -> ReportResponse:
    # Получаем основную информацию о мероприятии
    event_query = await db.execute(select(Event).where(Event.id == event_id))
    event = event_query.unique().scalar_one_or_none()
    if not event:
        raise ValueError("Мероприятие не найдено")

    # Получаем участников с их департаментом, должностью и фотографиями
    participants_query = await db.execute(
        select(Employee)
        .join(PlannedParticipant, PlannedParticipant.employee_id == Employee.id)
        .outerjoin(Department, Employee.department_id == Department.id)
        .outerjoin(Position, Employee.position_id == Position.id)
        .outerjoin(EmployeePhoto, EmployeePhoto.employee_id == Employee.id)
        .where(PlannedParticipant.event_id == event_id)
    )
    participants = participants_query.unique().scalars().all()

    # Формирование списка участников
    participants_info = [
        EmployeeInfoPhoto(
            id=part.id,
            name=part.name,
            surname=part.surname,
            patronymic=part.patronymic,
            department=part.department,
            position=part.position,
            photos=[PhotoInfo(id=p.id, path=p.photo) for p in part.photos],
        )
        for part in participants
    ]

    # Формируем event_info с учётом схемы
    event_info = EventInfo(
        id=event.id,
        name=event.name,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        video=event.video,
        participants_count=len(participants),
    )

    intervals_query = await db.execute(
        select(VisitInterval)
        .options(
            selectinload(VisitInterval.employees)
            .selectinload(IntervalEmployee.employee)
            .selectinload(Employee.photos),
            selectinload(VisitInterval.employees)
            .selectinload(IntervalEmployee.employee)
            .selectinload(Employee.department),
            selectinload(VisitInterval.employees)
            .selectinload(IntervalEmployee.employee)
            .selectinload(Employee.position)
        )
        .where(VisitInterval.event_id == event_id)
    )
    intervals = intervals_query.unique().scalars().all()

    # Группируем интервалы по сотрудникам
    employee_dict = {}
    for interval in intervals:
        for emp in interval.employees:
            if emp.employee.id not in employee_dict:
                employee_dict[emp.employee.id] = {
                    "employee": emp.employee,
                    "intervals": []
                }
            employee_dict[emp.employee.id]["intervals"].append(
                IntervalFullInfo(
                    interval_id=interval.id,
                    start_datetime=interval.start_datetime,
                    end_datetime=interval.end_datetime,
                    photo=emp.photo,
                    first_spot_datetime=emp.first_spot_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    employee_info=EmployeeInfoPhoto(
                        id=emp.employee.id,
                        name=emp.employee.name,
                        surname=emp.employee.surname,
                        patronymic=emp.employee.patronymic,
                        department=emp.employee.department,
                        position=emp.employee.position,
                        photos=[PhotoInfo(id=p.id, path=p.photo) for p in emp.employee.photos],
                    )
                )
            )

    # Формируем visits
    visits = [
        EmployeeVisit(
            id=e_data["employee"].id,
            name=e_data["employee"].name,
            surname=e_data["employee"].surname,
            patronymic=e_data["employee"].patronymic,
            department=e_data["employee"].department,
            position=e_data["employee"].position,
            photos=[PhotoInfo(id=p.id, path=p.photo) for p in e_data["employee"].photos],
            intervals=e_data["intervals"]
        )
        for e_id, e_data in employee_dict.items()
    ]

    # Формируем данные о незарегистрированных
    unregistered_info = [
        IntervalUnregisteredInfo(
            interval_id=interval.id,
            start_datetime=interval.start_datetime,
            end_datetime=interval.end_datetime,
            max_unregistered=interval.max_unregistered,
            max_unregistered_photo=interval.max_unregistered_photo
        )
        for interval in intervals
    ]

    return ReportResponse(
        event_info=event_info,
        participants=participants_info,
        visits=visits,
        unregistered=unregistered_info
    )
