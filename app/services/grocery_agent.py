import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set OpenAI API key
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_grocery_list(meal_plan: str):
    """ Convert meal plan into a structured grocery list """

    prompt = f"""
    Convert this meal plan into a structured grocery list:
    
    {meal_plan}

    **Rules:**
    1. Identify ingredients needed for all meals.
    2. Combine duplicate ingredients and **round up** quantities.
    3. **Remove unnecessary words** like "chopped", "minced", "sliced".
    4. Output **only** in the following format:
    
    **Example Output:**
    Eggs: 12
    Spinach: 2 
    Mushrooms: 1 
    Almond flour: 1 
    Olive oil: 1 
    
    **Do not include:** section headers (Breakfast, Lunch, Dinner), calorie counts, or extra descriptions.
    """

    client = openai.OpenAI()

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a structured grocery list generator."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content
