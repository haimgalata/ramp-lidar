"""Algorithm library listing (drives the left sidebar in the UI)."""
from typing import List

from fastapi import APIRouter

from app.algorithms.registry import list_algorithms
from app.models.schemas import AlgorithmDef

router = APIRouter(tags=["algorithms"])


@router.get("/algorithms", response_model=List[AlgorithmDef])
def get_algorithms():
    return [
        AlgorithmDef(id=a.id, name=a.name, description=a.description, parameters=a.parameters)
        for a in list_algorithms()
    ]
