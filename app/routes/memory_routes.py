from fastapi import APIRouter
from app.controllers.memory_controller import MemoryController

router = APIRouter()

router.post("/add")(MemoryController.add_memory)
router.post("/retrieve")(MemoryController.get_memory)
