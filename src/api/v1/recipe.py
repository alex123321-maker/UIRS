from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_session
from src.api.dependencies.auth import get_current_user
from src.schemas.recipe import RecipeCreate, RecipeFullOut
from src.schemas.user import UserFromDB
from src.services.recipe import create_recipe_service
import json

router = APIRouter()

@router.post("/", response_model=RecipeFullOut, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    # JSON со всеми полями рецепта
    recipe_data: Annotated[str, Form(...)] ,
    # Опционально превью
    preview_image: UploadFile | None = File(),
    stage_images: Annotated[list[UploadFile] | None, File()] = [],

    db: AsyncSession = Depends(get_session),
    current_user: UserFromDB = Depends(get_current_user),
):
    """
    Создать новый рецепт вместе с этапами, ингредиентами, тегами и фото.
    Принимаем recipe_data (JSON) и файлы:
    - preview_image — обложка (превью)
    - stage_images — список файлов для этапов.(В порядке, соответствующему их этапам)
    ```json
    {
      "title": "Борщ",
      "description": "Традиционный рецепт приготовления борща.",
      "calories": 250.0,
      "is_published": true, Если True, то пользователь сразу опубликует свой рецепт. (должны быть кнопка просто сохранить где это поле false)
      "difficulty": "MEDIUM",
      "stages": [
        {
          "title": "Подготовка ингредиентов",
          "order_index": 1,
          "description": "Моем, чистим и нарезаем овощи.",
          "minutes": 15
        },
        {
          "title": "Варка бульона",
          "order_index": 2,
          "description": "Закладываем мясо в кастрюлю, добавляем воду и варим 40 минут, периодически снимая пену.",
          "minutes": 40
        }
      ],
      "ingredients": [
        {
          "ingredient_id": 10,
          "unit_id": 2,
          "quantity": 500
        },
        {
          "ingredient_id": 15,
          "unit_id": 3,
          "quantity": 2.5
        }
      ],
      "tags": [2, 5]
    }
    ```
    """

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


    stage_files_map = {}
    if stage_images and len(stage_images) == len(recipe_in.stages):
        for i, stage in enumerate(recipe_in.stages):
            stage_files_map[stage.order_index] = stage_images[i]

    # 4. Создаём рецепт
    new_recipe = await create_recipe_service(
        db=db,
        recipe_in=recipe_in,
        user_id=current_user.id,
        preview_image=preview_image,
        stage_images=stage_files_map
    )

    return new_recipe
