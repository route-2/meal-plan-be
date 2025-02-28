def generate_grocery_list(meal_plan):
    prompt = f"""
    Convert this meal plan into a structured grocery list:
    
    {meal_plan}

    Step 1: Identify ingredients needed for all meals.
    Step 2: Combine duplicate ingredients and round up quantities.
    Step 3: Remove unnecessary words like "chopped", "minced", "sliced".
    
    Output only the list in the format:
    Eggs: 12
    Milk: 1
    Bread: 2
    """

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are a structured grocery list generator."},
                  {"role": "user", "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]
