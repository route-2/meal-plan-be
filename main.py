# from fastapi import FastAPI
# import redis

# app = FastAPI()  # ✅ Define the FastAPI app first

# # Initialize Redis
# redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# @app.get("/")
# def read_root():
#     return {"message": "Meal Planner Backend Running!"}

# @app.get("/user/{chat_id}")
# def get_user_state(chat_id: str):
#     user_data = redis_client.get(f"user:{chat_id}")  # Check for main user data
#     location_data = redis_client.get(f"user:{chat_id}:location")  # Check for location

#     if user_data:
#         return {"user_state": user_data}
#     elif location_data:
#         return {"location": location_data}  # ✅ Now it correctly returns location if found
#     else:
#         return {"message": "No user state found"}


# @app.post("/user/{chat_id}")
# def update_user_state(chat_id: str, data: dict):
#     redis_client.setex(f"user:{chat_id}", 86400, str(data))  # Store for 24 hours
#     return {"message": "User state updated"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

from fastapi import FastAPI
from app.routes import meal_routes, grocery_routes, location_routes, user_routes
import redis
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # your frontend origin(s)
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

@app.get("/")
def read_root():
    return {"message": "Meal Planner Backend Running!"}
