from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_user():
    return {"message": "User routes are working!"}
