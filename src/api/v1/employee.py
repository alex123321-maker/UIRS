from pyexpat.errors import messages
from typing import Annotated, List

from fastapi import HTTPException, Depends, APIRouter, Form, Query, Path, UploadFile, File, Body
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constant import FAIL_VALIDATION_MATCHED_EMPLOYEE, SUCCESS_DELETE_EMPLOYEE, SUCCESS_DELETE_PHOTO
from src.services.employee import get_or_create_department, get_or_create_position, create_employee, \
    get_all_departments, get_all_positions, update_employee_partial, delete_employee_service, get_employees_with_count, \
    add_employee_photo_to_db, delete_employee_photo_from_db, get_employee_from_db
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