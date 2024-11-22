from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.exc import NoResultFound
from fastapi import HTTPException
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import count

from src.models import Employee, Department, Position
from src.schemas.employee import EmployeeCreate, EmployeeInfo, PositionInfo, DepartmentInfo, EmployeeUpdate, \
    PaginatedEmployeeResponse

async def cleanup_unused_department_or_position(db: AsyncSession):
    """
    Удалить отделы и должности, которые больше не используются.
    """
    # Удалить неиспользуемые отделы
    stmt_departments = delete(Department).where(
        ~Department.employees.any()
    )
    await db.execute(stmt_departments)

    # Удалить неиспользуемые должности
    stmt_positions = delete(Position).where(
        ~Position.employees.any()
    )
    await db.execute(stmt_positions)

    # Подтвердить изменения
    await db.commit()


async def get_or_create_department(db: AsyncSession, department_name: str) -> DepartmentInfo:
    """
    Получить или создать отдел по названию.
    """
    stmt = select(Department).where(Department.name == department_name)
    department = (await db.execute(stmt)).scalar_one_or_none()

    if not department:
        department = Department(name=department_name)
        db.add(department)
        await db.commit()
        await db.refresh(department)
    return DepartmentInfo.model_validate(department)


async def get_or_create_position(db: AsyncSession, position_name: str) -> PositionInfo:
    """
    Получить или создать должность по названию.
    """
    stmt = select(Position).where(Position.name == position_name)
    position = (await db.execute(stmt)).scalar_one_or_none()

    if not position:
        position = Position(name=position_name)
        db.add(position)
        await db.commit()
        await db.refresh(position)
    return PositionInfo.model_validate(position)


async def create_employee(
    db: AsyncSession,
    employee_data: EmployeeCreate,
) -> EmployeeInfo:
    """
    Создать нового сотрудника с проверкой отдела и должности.
    """
    department = await get_or_create_department(db, employee_data.department)

    position = await get_or_create_position(db, employee_data.position)

    # Создать сотрудника
    new_employee = Employee(
        name=employee_data.name,
        surname=employee_data.surname,
        patronymic=employee_data.patronymic,
        department_id=department.id,
        position_id=position.id,
    )
    db.add(new_employee)
    await db.commit()
    await db.refresh(new_employee)

    await db.refresh(new_employee, attribute_names=["department", "position"])
    return EmployeeInfo(
        id = new_employee.id,
        name =new_employee.name,
        surname = new_employee.surname,
        patronymic = new_employee.patronymic,
        department=DepartmentInfo.model_validate(new_employee.department),
        position=PositionInfo.model_validate(new_employee.position),
    )


async def get_all_departments(db: AsyncSession, search: str | None = None) -> List[DepartmentInfo]:
    """
    Получить список всех отделов или отфильтрованных по части названия.
    """
    query = select(Department)
    if search:
        query = query.where(Department.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    departments = result.scalars().all()

    # Преобразуем модели в схемы
    return [DepartmentInfo.model_validate(department) for department in departments]


async def get_all_positions(db: AsyncSession, search: str | None = None) -> List[PositionInfo]:
    """
    Получить список всех должностей или отфильтрованных по части названия.
    """
    query = select(Position)
    if search:
        query = query.where(Position.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    positions = result.scalars().all()

    # Преобразуем модели в схемы
    return [PositionInfo.model_validate(position) for position in positions]

async def update_employee_partial(db: AsyncSession, employee_id: int, employee_data: EmployeeUpdate) -> EmployeeInfo | None:
    """
    Частично обновить данные сотрудника.
    """
    stmt = select(Employee).where(Employee.id == employee_id)
    employee = (await db.execute(stmt)).scalar_one_or_none()
    if not employee:
        return None

    # Обновить только переданные данные
    if employee_data.name is not None:
        employee.name = employee_data.name
    if employee_data.surname is not None:
        employee.surname = employee_data.surname
    if employee_data.patronymic is not None:
        employee.patronymic = employee_data.patronymic

    # Проверить или создать отдел
    if employee_data.department:
        department = await get_or_create_department(db=db, department_name = employee_data.department)
        employee.department_id = department.id

    # Проверить или создать должность
    if employee_data.position:
        position = await get_or_create_position(db=db, position_name = employee_data.position)
        employee.position_id = position.id


    await db.commit()
    await db.refresh(employee)

    # Удалить отдел или должность, если они больше не используются
    await cleanup_unused_department_or_position(db=db)
    await db.refresh(employee, attribute_names=["department", "position"])

    return EmployeeInfo(
        id = employee.id,
        name =employee.name,
        surname = employee.surname,
        patronymic = employee.patronymic,
        department=DepartmentInfo.model_validate(employee.department),
        position=PositionInfo.model_validate(employee.position),
    )

async def delete_employee_service(db: AsyncSession, employee_id: int) -> bool | None:
    """
    Удалить пользователя по id.
    """
    employee = await db.get(Employee, employee_id)
    if employee is None:
        return None

    await db.delete(employee)
    await db.commit()
    return True

async def get_employees_with_count(
    db: AsyncSession,
    page: int,
    limit: int,
    search: str | None = None,
    department: str | None = None,
    position: str | None = None,
) -> PaginatedEmployeeResponse:
    """
    Получить список сотрудников с пагинацией, поиском и фильтрацией, а также общее количество записей.
    """
    query = select(Employee).options(
        joinedload(Employee.department),
        joinedload(Employee.position)
    )

    # Поиск по ФИО
    if search:
        search = f"%{search}%"
        query = query.where(
            Employee.name.ilike(search) |
            Employee.surname.ilike(search) |
            Employee.patronymic.ilike(search)
        )

    # Фильтрация по отделу
    if department:
        query = query.join(Department).where(Department.name == department)

    # Фильтрация по должности
    if position:
        query = query.join(Position).where(Position.name == position)

    # Подсчёт общего количества записей
    total_count_query = select(func.count()).select_from(query.subquery())
    total_count_result = await db.execute(total_count_query)
    total_count = total_count_result.scalar()

    # Пагинация
    paginated_query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(paginated_query)
    employees = result.scalars().all()

    return PaginatedEmployeeResponse(
        total=total_count,
        employees=[EmployeeInfo.model_validate(employee) for employee in employees],
    )