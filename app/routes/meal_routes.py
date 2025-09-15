# app/routes/meal_routes.py
from fastapi import APIRouter, HTTPException, Request
from app.services.meal_agent import generate_rag_meal_plan

router = APIRouter()

@router.post("/generate")
async def generate_meal_plan_route(request: Request):
    try:
        body = await request.json()
        print("Received meal plan request:", body)

        meal_plan = generate_rag_meal_plan(body)
        if not meal_plan:
            raise HTTPException(status_code=500, detail="Meal plan generation failed.")

        return {"meal_plan": meal_plan}
    except HTTPException:
        raise
    except Exception as e:
        # Print detailed exception during dev
        import traceback
        traceback.print_exc()
        print("Error generating meal plan:", e)
        raise HTTPException(status_code=500, detail=str(e))
