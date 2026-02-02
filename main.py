

from fastapi import FastAPI
from app.routes import meal_routes, grocery_routes, location_routes, user_routes
from app.routes.recipe_routes import router as recipe_router
from app.routes.debug_routes import router as debug_router
from app.routes.grounded_meal_routes import router as grounded_meal_router
from app.routes.memory_routes import router as memory_router


import redis
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000" , ],  # your frontend origin(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Test connection
redis_client.set("test_key", "Hello, Redis!")
print(redis_client.get("test_key"))  



# Include Routers
app.include_router(meal_routes.router, prefix="/meals", tags=["Meals"])
app.include_router(grocery_routes.router, prefix="/groceries", tags=["Groceries"])
app.include_router(location_routes.router, prefix="/location", tags=["Location"])
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(recipe_router, prefix="/recipes", tags=["Recipes"])
app.include_router(debug_router, tags=["Debug"])
app.include_router(grounded_meal_router, prefix="/meals", tags=["Meals (RAG)"])
app.include_router(memory_router, prefix="/memory", tags=["Memory"])

@app.get("/")
def read_root():
    return {"message": "Meal Planner Backend Running!"}
