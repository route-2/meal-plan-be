import openai
import os
import json
from dotenv import load_dotenv
from app.database import index

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_meal_plan(user_data: dict):
    """ Generate a meal plan with calorie details per meal. """

    home_ingredients = f"Consider these available ingredients: {', '.join(user_data.available_ingredients)}." \
        if user_data.available_ingredients else ""

    prompt = f"""
    Create a meal plan with {user_data.calories} CALORIES per day for a {user_data.diet} diet 
    to {user_data.sub_goal} weight, strictly adhering to a {user_data.food_preference} preference 
    and including {user_data.cuisine}. Exclude these ingredients strictly: {user_data.exclude_ingredients}. 
    {home_ingredients}

    **STRICT FORMAT**:
    - List **exactly** 6 options for **Breakfast, Lunch, and Dinner**.
    - Each meal **MUST** include estimated **calories** (e.g., "Oatmeal with banana - 350 kcal").
    - No extra descriptions, just the **meal name and calories**.

    **EXAMPLE OUTPUT FORMAT**:
    Breakfast:
    1. Scrambled eggs with spinach - 320 kcal
    2. Avocado toast with whole grain bread - 280 kcal
    ...
    Lunch:
    1. Grilled salmon with quinoa - 550 kcal
    2. Greek salad with chickpeas - 400 kcal
    ...
    Dinner:
    1. Chicken stir-fry with vegetables - 600 kcal
    2. Stuffed bell peppers with ground turkey - 480 kcal
    """

    client = openai.OpenAI()

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a structured meal planning assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content
    

def store_meal_plan(user_id: str, meal_plan: str):
    """Generate an embedding for the meal plan and store it in Pinecone."""
    embedding_response = client.embeddings.create(  
        model="text-embedding-3-large",
        input=meal_plan
    )
    
    embedding = embedding_response.data[0].embedding

    index.upsert([(user_id, embedding, {"meal_plan": meal_plan})])
    return {"message": "Meal plan stored successfully"}

def get_past_meals(user_id: str):
    """Retrieve the most similar past meal plan for personalization."""
    try:
        if not user_id:
            return "No past meal plans found."

        
        results = index.query(
            namespace="meal-plans",
            id=user_id,  
            include_metadata=True
        )

        if "matches" in results and results["matches"]:
            return results["matches"][0]["metadata"].get("meal_plan", "No past meal plans found.")

        return "No past meal plans found."

    except Exception as e:
        print(f" Pinecone query error: {e}")
        return "No past meal plans found."


def generate_rag_meal_plan(user_data):
    """ Generate a meal plan using past meals and user preferences """
    
    prompt = f"""
    Given the following user preferences:
    - Diet: {user_data["diet"]}
    - Cuisine: {", ".join(user_data["cuisinePreference"])}
    - Food Preference {user_data["foodPreference"]}
    - Allergies: {user_data["includeIngredients"]}
    - Budget: {user_data["budget"]}
    - Ingredients at home: {user_data["ingredientsAtHome"]}

    Generate a meal plan ensuring variety, balanced nutrition, and calorie details.
    """

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a meal planning assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    meal_plan = response.choices[0].message.content

    return meal_plan