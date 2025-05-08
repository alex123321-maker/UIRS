from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from src.models.comment import Comment
from src.schemas.comment import CommentCreate, CommentUpdate
from fastapi import HTTPException, status

async def get_comments_for_recipe(
    db: AsyncSession,
    recipe_id: int
) -> list[Comment]:
    # просто берём плоский список
    stmt = select(Comment).where(Comment.recipe_id == recipe_id).options(joinedload(Comment.author)).order_by(Comment.created_at)
    res  = await db.execute(stmt)
    return res.scalars().all()

async def create_comment(
    db: AsyncSession,
    recipe_id: int,
    user_id: int,
    data: CommentCreate
) -> Comment:
    new = Comment(
        text=data.text,
        rating=data.rating,
        recipe_id=recipe_id,
        author_id=user_id,
        reply_to=data.reply_to,
    )
    db.add(new)
    await db.flush()
    await db.refresh(new, attribute_names=["author"])
    return new

async def update_comment(
    db: AsyncSession,
    comment_id: int,
    user_id: int,
    data: CommentUpdate
) -> Comment:
    stmt = select(Comment).where(Comment.id == comment_id).options(joinedload(Comment.author))
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Комментарий не найден")
    if comment.author_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Это не ваш комментарий")
    if comment.deleted:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Комментарий уже удален")

    if data.text is not None:
        comment.text = data.text
    if data.rating is not None:
        comment.rating = data.rating

    await db.flush()
    await db.commit()
    return comment

async def delete_comment(
    db: AsyncSession,
    comment_id: int,
    user_id: int
) -> None:
    stmt = select(Comment).where(Comment.id == comment_id)
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Комментарий не найден")
    if comment.author_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Это не ваш комментарий")
    comment.deleted = True
    await db.flush()