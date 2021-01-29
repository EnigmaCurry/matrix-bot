from sqlalchemy import create_engine, select, \
    Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import registry, relationship, Session
from dataclasses import dataclass, field
from typing import List, Optional
from collections.abc import Iterable

import os

DB_CONNECTION=os.environ.get("DB_CONNECTION", "sqlite+pysqlite:///:memory:")
engine = create_engine(DB_CONNECTION, echo=False, future=True)

mapper_registry = registry()
mapper_registry.metadata.bind = engine
def session():
    return Session(engine)

image_term_image_table = Table(
    'image_term_image', mapper_registry.metadata,
    Column('image_term', String(50), ForeignKey("image_term.term")),
    Column('image_url', String(2000), ForeignKey("image.url")))

@mapper_registry.mapped
@dataclass
class ImageRecord:
    __table__ = Table(
        "image",
        mapper_registry.metadata,
        Column("url", String(2000), primary_key=True),
        Column("path", String(500)),
        Column("source", String(50), ForeignKey("image_source.name")),
    )
    url: str
    path: str
    source: str

    @classmethod
    def search(cls, search_term: str, source: str = None):
        q = select(ImageRecord).join(ImageSource.images)
        if source:
            q = q.where(ImageSource.name == source)
        return q

@mapper_registry.mapped
@dataclass
class ImageSource:
    __table__ = Table(
        "image_source",
        mapper_registry.metadata,
        Column("name", String(50), primary_key=True),
    )
    name: str = None
    images: List[ImageRecord] = field(default_factory=list)

    __mapper_args__ = {
        "properties" : {
            "images": relationship("ImageRecord")
        }
    }

@mapper_registry.mapped
@dataclass
class ImageTerm:
    __table__ = Table(
        "image_term",
        mapper_registry.metadata,
        Column("term", String(50), primary_key=True),
    )
    term: str = field()
    images: List[ImageRecord] = field(default_factory=list)

    __mapper_args__ = {
        "properties" : {
            "images": relationship("ImageRecord", secondary=image_term_image_table)
        }
    }

    @classmethod
    def search(cls, term: str, source: str = None):
        q = select(ImageTerm)
        if source:
            q = q.join(ImageSource).where(
                ImageTerm.term == term and ImageSource.name == source)
        else:
            q = q.where(ImageTerm.term == term)
        return q

def test_data():
    with session() as s:
        s.add(ImageSource(name="matrix"))
        s.add(ImageSource(name="iconduck"))
        s.add(ImageSource(name="thenounproject"))

        img= ImageRecord("https://blog.rymcg.tech/img/logo.jpg", "/", "matrix")
        s.add(img)
        s.commit()

        term = ImageTerm("blog", images=[img])
        s.add(term)
        s.commit()

def make_db_diagram(image_path):
    from database import mapper_registry

    from sqlalchemy_schemadisplay import create_schema_graph

    graph = create_schema_graph(metadata=mapper_registry.metadata,
                                show_datatypes=False,
                                show_indexes=False,
                                rankdir="LR",
                                concentrate=False)
    graph.write_png(image_path)


mapper_registry.metadata.create_all()
test_data()

