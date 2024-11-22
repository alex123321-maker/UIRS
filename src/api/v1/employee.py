from pyexpat.errors import messages
from typing import Annotated, List

from fastapi import HTTPException, Depends, APIRouter, Form, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constant import FAIL_VALIDATION_MATCHED_EMPLOYEE, SUCCESS_DELETE_EMPLOYEE
from src.services.employee import get_or_create_department, get_or_create_position, create_employee, \
    get_all_departments, get_all_positions, update_employee_partial, delete_employee_service, get_employees_with_count
from starlette.status import HTTP_201_CREATED, HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_204_NO_CONTENT

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.database import get_session
from src.schemas.employee import EmployeeInfo, EmployeeCreate, PositionInfo, DepartmentInfo, EmployeeUpdate, \
    EmployeeDeleteResponse, PaginatedEmployeeResponse
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

@router.post("/", response_model=EmployeeInfo, status_code=HTTP_201_CREATED)
async def create_new_employee(
    auth_user: Annotated[UserFromDB, Depends(get_current_user)],
    employee_create: EmployeeCreate = Form(...),
    db: AsyncSession = Depends(get_session),
):
    new_employee = await create_employee(
        db=db,
        employee_data=employee_create,
    )

    # Возвращаем данные о сотруднике
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