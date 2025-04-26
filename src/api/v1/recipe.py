from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
from fastapi.params import Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_session
from src.api.dependencies.auth import get_current_user, get_current_user_optional
from src.api.dependencies.pagination import PaginationParams, get_pagination_params
from src.schemas.common import PaginatedResponse
from src.schemas.recipe import RecipeCreate, RecipeFullOut, DifficultyEnum
from src.schemas.user import UserFromDB
from src.services.recipe import create_recipe_service, get_recipe_by_id, get_recipes_list_service, \
    get_my_recipes_service
import json

router = APIRouter()
@router.post("/", response_model=RecipeFullOut, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    recipe_data: Annotated[str, Form(...)],
    preview_image: UploadFile | None = File(),
    stage_images: Annotated[list[UploadFile] | None, File()] = [],
    db: AsyncSession = Depends(get_session),
    current_user: UserFromDB = Depends(get_current_user),
) -> RecipeFullOut:
    """
    Создать новый рецепт вместе с этапами, ингредиентами, тегами и фото.

    ### Формат поля `recipe_data` (JSON):
    Возможные значения difficulty: EASY, MEDIUM, HARD
    ```json
    {
        "title": "Жареная картошка",
        "description": "Классический рецепт жареной картошки с луком",
        "calories": 320.5,
        "is_published": true,
        "difficulty": "EASY",
        "stages": [
            {
                "title": "Нарезка картошки",
                "order_index": 0,
                "description": "Нарежьте картофель дольками",
                "minutes": 5
            },
            {
                "title": "Жарка",
                "order_index": 1,
                "description": "Обжаривайте картофель на сковороде до золотистой корочки",
                "minutes": 15
            }
        ],
        "ingredients": [
            {
                "ingredient_id": 1,
                "unit_id": 2,
                "quantity": 300.0
            },
            {
                "ingredient_id": 2,
                "unit_id": 3,
                "quantity": 50.0
            }
        ],
        "tags": [1, 3]
    }
    ```

    ### Пояснения:
    - `preview_image` — изображение для обложки (опционально)
    - `stage_images` — список изображений для этапов (опционально, порядок должен соответствовать `order_index`)
    - `tags` — список ID существующих тегов
    - `ingredients` — список объектов, указывающих ID ингредиента, единицу измерения и количество

    Если `is_published` = `true`, рецепт будет сразу опубликован и получит `published_at`.
    """

    import json

    # 1. Парсим JSON
    try:
        parsed_data = json.loads(recipe_data)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Неверный формат JSON"
        )

    # 2. Валидируем через Pydantic
    recipe_in = RecipeCreate.model_validate(parsed_data)

    # 3. Привязываем файлы к соответствующим шагам (по order_index)
    stage_files_map = {}
    if stage_images and len(stage_images) == len(recipe_in.stages):
        for i, stage in enumerate(recipe_in.stages):
            stage_files_map[stage.order_index] = stage_images[i]

    # 4. Открываем транзакцию здесь (убираем транзакцию из сервиса)
    async with db.begin():
        new_recipe = await create_recipe_service(
            db=db,
            recipe_in=recipe_in,
            user_id=current_user.id,
            preview_image=preview_image,
            stage_images=stage_files_map
        )
    return new_recipe


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
