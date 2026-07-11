from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.domain import LineaNegocio
from app.schemas import StockEntryCreate, StockItemOut
from app.services import stock_service

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("", response_model=list[StockItemOut])
def list_stock(
    linea_negocio: LineaNegocio | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(get_current_user),
):
    return stock_service.list_stock(db, linea_negocio)


@router.post("/entrada", response_model=StockItemOut, status_code=status.HTTP_201_CREATED)
def registrar_entrada(
    payload: StockEntryCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return stock_service.registrar_entrada(db, current_user, payload)
    except stock_service.ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
