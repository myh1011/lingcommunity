from sqlalchemy import Column, Integer, ForeignKey, Table
from app.db.database import Base

page_tags = Table(
    'page_tags',
    Base.metadata,
    Column('page_id', Integer, ForeignKey('pages.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)