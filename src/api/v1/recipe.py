from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
from fastapi.params import Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path as FilePath

from src.api.dependencies.database import get_session
from src.api.dependencies.auth import get_current_user, get_current_user_optional
from src.api.dependencies.pagination import PaginationParams, get_pagination_params
from src.schemas.common import PaginatedResponse
from src.schemas.recipe import RecipeCreate, RecipeFullOut, DifficultyEnum
from src.schemas.user import UserFromDB
from src.services.recipe import create_recipe_service, get_recipe_by_id, get_recipes_list_service, \
    get_my_recipes_service, update_recipe_service
import json

router = APIRouter()

from src.schemas.recipe import RecipeUpdate


@router.post(
    "/",
    response_model=RecipeFullOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый рецепт",
)
async def create_recipe(
    recipe_data: Annotated[str, Form(..., description="JSON с параметрами нового рецепта")],
    preview_image: UploadFile | None = File(
        None, description="Изображение-обложка (опционально)"
    ),
    stage_images: Annotated[
        list[UploadFile] | None,
        File(description="Файлы для этапов; имя файла без расширения = order_index этапа")
    ] = None,
    db: AsyncSession = Depends(get_session),
    current_user: UserFromDB = Depends(get_current_user),
) -> RecipeFullOut:
    """
    Создает новый рецепт и возвращает полный объект.

    **Авторизация**: требуется Bearer-токен в заголовке `Authorization: Bearer <token>`

    ### Multipart-формат:
    - **recipe_data** (string, required): JSON со следующими полями:
      - `title` (string, 1–255 символов)
      - `description` (string, optional)
      - `calories` (number, optional)
      - `servings` (integer ≥1, default=1)
      - `difficulty` (enum: `EASY`/`MEDIUM`/`HARD`, default=`EASY`)
      - `is_published` (boolean, default=false)
      - `tags` (array[int], optional)
      - `ingredients` (array[object], optional):
        - `ingredient_id`: integer
        - `unit_id`: integer
        - `quantity`: number
      - `stages` (array[object], optional):
        - `title`: string
        - `order_index`: integer
        - `minutes`: integer
        - `description`: string, optional
    - **preview_image** (file, optional): картинка-обложка
    - **stage_images** (file[], optional): файлы для этапов; имя файла (stem) = `order_index`

    ### Пример recipe data:
    {
           "title": "Жареная картошка с грибами",
           "description": "Сытный и ароматный гарнир на каждую неделю",
           "calories": 420.5,
           "servings": 4,
           "difficulty": "MEDIUM",
           "is_published": true,
           "tags": [1, 3, 7],
           "ingredients": [
             {"ingredient_id": 1, "unit_id": 2, "quantity": 300.0},
             {"ingredient_id": 5, "unit_id": 3, "quantity": 150.5},
             {"ingredient_id": 9, "unit_id": 2, "quantity": 50.0}
           ],
           "stages": [
             {
               "title": "Подготовка грибов",
               "order_index": 0,
               "minutes": 10,
               "description": "Промыть и нарезать грибы"
             },
             {
               "title": "Жарка картофеля",
               "order_index": 1,
               "minutes": 15,
               "description": "Обжарить на подсолнечном масле"
             },
             {
               "title": "Соединение и тушение",
               "order_index": 2,
               "minutes": 10,
               "description": "Добавить грибы, посолить, потушить"
             }
           ]
         }

    ### Успешный ответ (201 Created):
    ```json
    {
      "id": 10,
      "title": "Жареная картошка",
      "description": "Вкусно",
      "calories": 250.0,
      "servings": 2,
      "difficulty": "EASY",
      "is_published": true,
      "created_at": "2025-05-07T12:00:00Z",
      "published_at": "2025-05-07T12:00:00Z",
      "photo_url": "/media/10/preview.jpg",
      "author": { "id": 5, "login": "user1" },
      "likes_count": 0,
      "is_liked_by_me": null,
      "ingredients": [ /* ... */ ],
      "stages": [ /* ... */ ],
      "tags": [ /* ... */ ]
    }
    ```

    ### Возможные ошибки:
    - **400 Bad Request** — неверный JSON, отсутствие обязательных полей или несуществующие `tag_id`/`ingredient_id`.
    - **401 Unauthorized** — нет токена или он недействителен.
    - **403 Forbidden** — нет прав (не ваш пользователь).
    """
    try:
        data = json.loads(recipe_data)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неверный JSON в recipe_data")
    recipe_in = RecipeCreate.model_validate(data)

    # Маппим stage_images по order_index, взятому из имени файла
    stage_map: dict[int, UploadFile] = {}
    if stage_images:
        for file in stage_images:
            try:
                idx = int(FilePath(file.filename).stem)
            except ValueError:
                continue
            stage_map[idx] = file

    # Создаём
    async with db.begin():  # начинаем транзакцию
        recipe = await create_recipe_service(
            db=db,
            recipe_in=recipe_in,
            user_id=current_user.id,
            preview_image=preview_image,
            stage_images=stage_map,
        )
    return recipe

@router.patch(
    "/{recipe_id}",
    response_model=RecipeFullOut,
    status_code=status.HTTP_200_OK,
    summary="Частично обновить рецепт",
)
async def patch_recipe(
    recipe_id: Annotated[int, Path(..., description="ID рецепта для обновления")],
    recipe_data: Annotated[str, Form(..., description="JSON с полями для обновления")],
    preview_image: UploadFile | None = File(
        None, description="Новая обложка (опционально)"
    ),
    stage_images: Annotated[
        list[UploadFile] | None,
        File(description="Файлы для этапов; имя файла (stem) = order_index этапа")
    ] = None,
    db: AsyncSession = Depends(get_session),
    current_user: UserFromDB = Depends(get_current_user),
) -> RecipeFullOut:
    """
    Частичное обновление существующего рецепта.

    **Авторизация**: требуется Bearer-токен владельца рецепта.

    ### Параметры:
    - **recipe_id** (path, int): ID рецепта, которым вы владеете.
    - **recipe_data** (form-data, string): JSON с любыми полями из модели `RecipeUpdate`:
      - `title`, `description`, `calories`, `servings`, `difficulty`, `is_published`
      - Если пользователь хочет изменить что угодно в этих полях `tags`, `ingredients`, `stages`, то ты должен передать сразу все элементы дыже если он изменил тоолько один из них.Например ты хочешь изменить название второго этапа, тебе нужно отправить как при создании все этапы.

    - **preview_image** (file, optional): заменить обложку.
    - **stage_images** (file[], optional): файлы для этапов; имя файла без расширения = `order_index`.

    ### Пример запроса:
    ```bash
    curl -X PATCH "https://api.example.com/recipes/10" \
      -H "Authorization: Bearer <token>" \
      -F 'recipe_data={
           "title":"Новое название",
           "servings":4,

         }' \
      -F "stage_images=@0.jpg"
    ```

    ### Успешный ответ (200 OK):
    Возвращает объект `RecipeFullOut` с актуальными полями, включая
    `servings`, `author`, `likes_count`, `is_liked_by_me`, а также обновлённые `ingredients`, `stages`, `tags`.

    ### Возможные ошибки:
    - **400 Bad Request** — некорректный JSON или данные.
    - **401 Unauthorized** — неавторизован.
    - **403 Forbidden** — не ваш рецепт.
    - **404 Not Found** — рецепт не найден.
    """
    try:
        data = json.loads(recipe_data)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Неверный JSON в recipe_data")
    update_in = RecipeUpdate.model_validate(data)

    # Маппим файлы этапов
    stage_map: dict[int, UploadFile] = {}
    if stage_images:
        for file in stage_images:
            try:
                idx = int(FilePath(file.filename).stem)
            except ValueError:
                continue
            stage_map[idx] = file

    # Обновляем
    async with db.begin():  # одна транзакция на всё
        recipe = await update_recipe_service(
            db=db,
            recipe_id=recipe_id,
            user_id=current_user.id,
            data=update_in,
            preview_image=preview_image,
            stage_images=stage_map,
        )
    return recipe

@router.get(
    "/my",
    response_model=PaginatedResponse[RecipeFullOut],
    status_code=status.HTTP_200_OK,
    summary="Получить свои рецепты",
    description="""
Возвращает список рецептов, созданных текущим пользователем.

### Фильтрация:
- `is_published` — только опубликованные (`true`), только черновики (`false`) или все (`null`)

### Сортировка:
- По дате публикации (сначала новые или сначала старые), по умолчанию — сначала новые (`desc`)

### Пагинация:
- `page` — номер страницы
- `limit` — элементов на странице
"""
)
async def get_my_recipes(
    db: AsyncSession = Depends(get_session),
    current_user: UserFromDB = Depends(get_current_user),
    pagination: PaginationParams = Depends(get_pagination_params),
    is_published: Optional[bool] = Query(None, description="Фильтрация по публикации: true/false/не указано"),
    sort_order: Optional[str] = Query("desc", regex="^(asc|desc)$", description="Порядок сортировки по дате публикации")
) -> PaginatedResponse[RecipeFullOut]:
    page, limit = pagination.page, pagination.limit

    recipes, total = await get_my_recipes_service(
        db=db,
        user_id=current_user.id,
        page=page,
        limit=limit,
        is_published=is_published,
        sort_order=sort_order,
    )

    return PaginatedResponse(
        items=recipes,
        results=total,
        current_page=page,
        total_pages=(total // limit + int(total % limit != 0)),
    )


@router.get("/{recipe_id}", response_model=RecipeFullOut,status_code=status.HTTP_200_OK)
async def get_recipe(
    recipe_id: int = Path(...),
    db: AsyncSession = Depends(get_session),
    optional_user: Optional[UserFromDB] = Depends(get_current_user_optional),

)-> RecipeFullOut:

    return await get_recipe_by_id(db=db, id=recipe_id,user_id=optional_user.id if optional_user is not None else None )

@router.get(
    "/",
    response_model=PaginatedResponse[RecipeFullOut],
    status_code=status.HTTP_200_OK,
    summary="Получить список рецептов",
    description="""
Возвращает список рецептов с поддержкой фильтрации, сортировки и пагинации.

### Фильтрация:
- `title` — фильтрация по части названия (поиск по подстроке).
- `author_id` — фильтрация по автору (ID пользователя).
- `licked` — показать только лайкнутые мною рецепты.(для не авторизованных пользователей ошибка) 
- `difficulty` — фильтрация по сложности (EASY, MEDIUM, HARD).
- `tag_ids` — фильтрация по тегам. Если передано несколько ID, вернутся только рецепты, содержащие **все указанные теги**.
- `ingredient_ids` — фильтрация по ингредиентам. Если передано несколько ID, вернутся только рецепты, содержащие **все указанные ингредиенты**.

### Сортировка:
- `sort_by` — поле для сортировки (`date` или `calories`).
- `sort_order` — направление сортировки (`asc` или `desc`). По умолчанию: `desc`.

### Пагинация:
- `page` — номер страницы (начиная с 1).
- `limit` — количество рецептов на странице.
"""
)
async def get_recipes_list(
    db: AsyncSession = Depends(get_session),
    pagination: PaginationParams = Depends(get_pagination_params),
    title: Optional[str] = Query(
        None, description="Часть названия рецепта для поиска (без учёта регистра)"
    ),
    author_id: Optional[int] = Query(
        None, description="ID автора рецепта"
    ),
    difficulty: Optional[DifficultyEnum] = Query(
        None, description="Сложность рецепта: EASY, MEDIUM или HARD"
    ),
    tag_ids: Optional[List[int]] = Query(
        None, description="Список ID тегов. Вернутся только рецепты, содержащие все эти теги."
    ),
    ingredient_ids: Optional[List[int]] = Query(
        None, description="Список ID ингредиентов. Вернутся только рецепты, содержащие все эти ингредиенты."
    ),
    sort_by: Optional[str] = Query(
        None, regex="^(date|calories)?$", description="Поле сортировки: date или calories"
    ),
    sort_order: Optional[str] = Query(
        "desc", regex="^(asc|desc)$", description="Порядок сортировки: asc (по возрастанию) или desc (по убыванию)"
    ),
    liked: bool = Query(False, description="Показать только лайкнутые мною рецепты"),
    optional_user: Optional[UserFromDB] = Depends(get_current_user_optional),
) -> PaginatedResponse[RecipeFullOut]:
    """
    Эндпоинт возвращает список рецептов с возможностью гибкой фильтрации, сортировки и пагинации.
    """
    page, limit = pagination.page, pagination.limit

    recipes, total = await get_recipes_list_service(
        db=db,
        page=page,
        limit=limit,
        title=title,
        author_id=author_id,
        difficulty=difficulty,
        liked_by_me=liked,
        tag_ids=tag_ids,
        ingredient_ids=ingredient_ids,
        sort_by=sort_by,
        sort_order=sort_order,
        user_id=(optional_user.id if optional_user else None),
    )

    return PaginatedResponse(
        items=recipes,
        results=total,
        current_page=page,
        total_pages=(total // limit + int(total % limit != 0)),
    )

