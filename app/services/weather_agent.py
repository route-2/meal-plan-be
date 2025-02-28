import requests

def get_weather_based_meal(location):
    weather_api_key = "YOUR_WEATHER_API_KEY"
    response = requests.get(f"https://api.weatherapi.com/v1/current.json?key={weather_api_key}&q={location}")
    weather_data = response.json()
    
    temp = weather_data["current"]["temp_c"]
    
    if temp < 10:
        return "Recommended: Hot soup, stews, and warm meals."
    elif temp > 30:
        return "Recommended: Light salads, cold smoothies, and hydrating foods."
    else:
        return "Recommended: Balanced home-cooked meals."
