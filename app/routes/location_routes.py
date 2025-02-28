from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_location():
    return {"message": "Location routes are working!"}
