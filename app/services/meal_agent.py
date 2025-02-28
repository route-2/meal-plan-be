import openai
import json
from app.database import index

def generate_meal_plan(user_data):
    prompt = f"""
    Given the following user preferences:
    - Diet: {user_data["diet"]}
    - Cuisine: {user_data["cuisine"]}
    - Allergies: {user_data["allergies"]}
    - Budget: {user_data["budget"]}

    Generate a meal plan ensuring variety, balanced nutrition, and no ingredient hallucinations.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are a meal planning assistant."},
                  {"role": "user", "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]

def store_meal_plan(user_id: str, meal_plan: str):
    """Generate an embedding for the meal plan and store it in Pinecone."""
    embedding_response = openai.Embedding.create(
        model="text-embedding-3-large",
        input=meal_plan
    )
    
    embedding = embedding_response["data"][0]["embedding"]

    # Store in Pinecone with metadata
    index.upsert([(user_id, embedding, {"meal_plan": meal_plan})])
    return {"message": "Meal plan stored successfully"}

def get_past_meals(user_id: str):
    """Retrieve the most similar past meal plan for personalization."""
    results = index.query(user_id, top_k=1, include_metadata=True)
    
    if results["matches"]:
        return results["matches"][0]["metadata"]["meal_plan"]
    
    return "No past meal plans found."


def generate_rag_meal_plan(user_id: str, user_data: dict):
    past_meals = get_past_meals(user_id)

    prompt = f"""
    Given the following user preferences:
    - Diet: {user_data["diet"]}
    - Cuisine: {user_data["cuisine"]}
    - Allergies: {user_data["allergies"]}
    - Budget: {user_data["budget"]}

    Use past meal history: {past_meals}

    Generate a new meal plan ensuring variety, balanced nutrition, and no ingredient hallucinations.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are a meal planning assistant."},
                  {"role": "user", "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]
