from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Path, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_session
from src.api.dependencies.auth import get_current_user
from src.schemas.comment import CommentCreate, CommentUpdate, CommentOut, DeletedComment
from src.services.comment import (
    get_comments_for_recipe,
    create_comment,
    update_comment,
    delete_comment,
)

router = APIRouter()

@router.get("/", response_model=List[Union[CommentOut, DeletedComment]])
async def list_comments(
    recipe_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_session)
) -> List[Union[CommentOut, DeletedComment]]:
    comments = await get_comments_for_recipe(db, recipe_id)
    out: List[Union[CommentOut, DeletedComment]] = []
    for c in comments:
        if c.deleted:
            out.append( DeletedComment(
                id=c.id,
                reply_to=c.reply_to
            ))
        else:
            out.append(CommentOut.model_validate(c))
    return out

@router.post("/", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def add_comment(
    data: CommentCreate,
    recipe_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user),
) -> CommentOut:
    async with db.begin():
        comment = await create_comment(db, recipe_id, current_user.id, data)
    return CommentOut.model_validate(comment)

@router.patch("/{comment_id}", response_model=CommentOut)
async def edit_comment(
    data: CommentUpdate,
    recipe_id: int = Path(..., ge=1),
    comment_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user),
) -> CommentOut:
    comment = await update_comment(db, comment_id, current_user.id, data)
    return CommentOut.model_validate(comment)

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_comment(
    recipe_id: int = Path(..., ge=1),
    comment_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user),
) -> None:
    async with db.begin():
        await delete_comment(db, comment_id, current_user.id)