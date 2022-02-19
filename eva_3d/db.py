from typing import Optional, List
import warnings

from sqlalchemy import exc as sa_exc
from sqlmodel import Field, SQLModel, create_engine, Relationship
from sqlmodel.sql.expression import select


warnings.simplefilter("ignore", category=sa_exc.SAWarning)


class BOMTable(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    items: List["BOMItem"] = Relationship(back_populates="bom_table")


class BOMItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str]
    material: str
    quantity: float
    bom_table_id: Optional[int] = Field(default=None, foreign_key="bomtable.id")
    bom_table: Optional[BOMTable] = Relationship(back_populates="items")

    @property
    def is_printable(self):
        return self.material.upper() == "PETG"


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# engine = create_engine(sqlite_url, echo=True)
engine = create_engine(sqlite_url)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def remove_page_bom(session, page_uid):
    tables = session.exec(select(BOMTable).where(BOMTable.name == page_uid)).all()
    for table in tables:
        items = session.exec(
            select(BOMItem).where(BOMItem.bom_table_id == table.id)
        ).all()
        for item in items:
            session.delete(item)
        session.delete(table)

    session.commit()
