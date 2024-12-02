from datetime import datetime
from pyexpat.errors import messages
from typing import Annotated, List, Optional

from fastapi import HTTPException, Depends, APIRouter, Form, Query, Path, UploadFile, File, Body
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constant import FAIL_VALIDATION_MATCHED_EMPLOYEE, SUCCESS_DELETE_EMPLOYEE, SUCCESS_DELETE_PHOTO
from src.schemas.event import EmployeeEvent, EventListResponse, EmployeeEventListResponse, EmployeeEventStatuses
from src.services.employee import get_or_create_department, get_or_create_position, create_employee, \
    get_all_departments, get_all_positions, update_employee_partial, delete_employee_service, get_employees_with_count, \
    add_employee_photo_to_db, delete_employee_photo_from_db, get_employee_from_db, get_events_for_employee
from starlette.status import HTTP_201_CREATED, HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_204_NO_CONTENT

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.database import get_session
from src.schemas.employee import EmployeeInfo, EmployeeCreate, PositionInfo, DepartmentInfo, EmployeeUpdate, \
    EmployeeDeleteResponse, PaginatedEmployeeResponse, EmployeeInfoPhoto, PhotoDeleteResponse
from src.schemas.user import UserFromDB

router = APIRouter()


@router.get("/departments", response_model=List[DepartmentInfo],status_code=HTTP_200_OK)
async def get_departments(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    search: str | None = Query(None, description="Часть названия отдела для поиска"),
    db: AsyncSession = Depends(get_session),
):
    """
    Возвращает список всех отделов или отделов, содержащих часть названия.
    """
    return await get_all_departments(db=db, search=search)


@router.get("/positions", response_model=List[PositionInfo],status_code=HTTP_200_OK)
async def get_positions(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    search: str | None = Query(None, description="Часть названия должности для поиска"),
    db: AsyncSession = Depends(get_session),
):
    """
    Возвращает список всех должностей или должностей, содержащих часть названия.
    """
    return await get_all_positions(db=db, search=search)

@router.get("/", response_model=PaginatedEmployeeResponse)
async def list_employees(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, description="Количество сотрудников на странице"),
    search: str | None = Query(None, description="Поиск по имени, фамилии или отчеству"),
    department: str | None = Query(None, description="Название отдела для фильтрации"),
    position: str | None = Query(None, description="Название должности для фильтрации"),
    db: AsyncSession = Depends(get_session),
):
    """
    Получить список сотрудников с пагинацией, поиском и фильтрацией.
    """
    return await get_employees_with_count(
        db=db,
        page=page,
        limit=limit,
        search=search,
        department=department,
        position=position,
    )

@router.get("/{employee_id}", response_model=EmployeeInfoPhoto, status_code=HTTP_200_OK)
async def get_employee(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    employee_id: int = Path(..., description="Идентификатор сотрудника"),
    db: AsyncSession = Depends(get_session),
):
    """
    Получить информацию о сотруднике.
    """
    return await get_employee_from_db(
        db=db,
        employee_id=employee_id,
    )
def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y %H:%M")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Неверный формат даты. Ожидается формат 'ДД.ММ.ГГГГ ЧЧ:ММ', получено: {value}"
        )

@router.get("/{employee_id}/events", response_model=EmployeeEventListResponse)
async def get_employee_activity(
    employee_id: int = Path(..., description="Идентификатор сотрудника"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(10, ge=1, le=100, description="Количество элементов на странице"),
    search: Optional[str] = Query(None, description="Поиск по названию мероприятия"),
    date_from: Optional[str] = Query(
        None,
        description="Фильтр по начальной дате (формат: ДД.ММ.ГГГГ ЧЧ:ММ)",
        example="20.01.2000 12:20"
    ),
    date_to: Optional[str] = Query(
        None,
        description="Фильтр по конечной дате (формат: ДД.ММ.ГГГГ ЧЧ:ММ)",
        example="21.01.2000 15:30"
    ),
    status: Optional[EmployeeEventStatuses] = Query(None, description="Фильтр по статусу"),
    db: AsyncSession = Depends(get_session),
):
    try:
        # Преобразуем строки в datetime
        parsed_date_from = parse_datetime(date_from)
        parsed_date_to = parse_datetime(date_to)

        events_data = await get_events_for_employee(
            employee_id=employee_id,
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
            status=status
        )
        return events_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения мероприятий: {str(e)}")
@router.post("/", response_model=EmployeeInfoPhoto, status_code=HTTP_201_CREATED)
async def create_new_employee(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    name: str = Form(...),
    surname: str = Form(...),
    patronymic: str = Form(None),
    department: str = Form(...),
    position: str = Form(...),
    files: List[UploadFile] | None = File(None),
    db: AsyncSession = Depends(get_session),
):
    # Создание объекта EmployeeCreate вручную
    employee_data = EmployeeCreate(
        name=name,
        surname=surname,
        patronymic=patronymic,
        department=department,
        position=position,
    )
    new_employee = await create_employee(
        db=db,
        employee_data=employee_data,
        files=files,
    )

    return new_employee

@router.patch("/{employee_id}", response_model=EmployeeInfo)
async def edit_employee_partial(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    employee_id: int = Path(..., description="Идентификатор сотрудника"),
    employee_data: EmployeeUpdate = Depends(),
    db: AsyncSession = Depends(get_session),
):
    """
    Частично обновить данные сотрудника.
    """
    updated_employee = await update_employee_partial(db=db, employee_id=employee_id, employee_data=employee_data)
    if not updated_employee:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=FAIL_VALIDATION_MATCHED_EMPLOYEE)
    return updated_employee

@router.delete("/{employee_id}",response_model=EmployeeDeleteResponse,status_code=HTTP_200_OK)
async def remove_employee(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    employee_id: int = Path(..., description="Идентификатор сотрудника"),
    db: AsyncSession = Depends(get_session),
):
    """
    Удалить сотрудника.
    """
    success = await delete_employee_service(db=db, employee_id=employee_id)
    if not success:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=FAIL_VALIDATION_MATCHED_EMPLOYEE)
    return EmployeeDeleteResponse(message=SUCCESS_DELETE_EMPLOYEE)

@router.post("/{employee_id}/photos", response_model=EmployeeInfoPhoto, status_code=201)
async def add_photo(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    employee_id: int,
    file: UploadFile,
    db: AsyncSession = Depends(get_session)
):
    photo = await add_employee_photo_to_db(db, employee_id, file)

    return photo

@router.delete("/photos/{photo_id}", response_model=PhotoDeleteResponse, status_code=200)
async def delete_photo(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    photo_id: int,
    db: AsyncSession = Depends(get_session)
):
    photo = await delete_employee_photo_from_db(db, photo_id)

    return PhotoDeleteResponse(message=SUCCESS_DELETE_PHOTO)