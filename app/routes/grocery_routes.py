from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_grocery():
    return {"message": "Grocery routes are working!"}
