import os
import requests

# Weather condition codes from your list
weather_codes = [
    113, 116, 119, 122, 143, 176, 179, 182, 185, 200,
    227, 230, 248, 260, 263, 266, 281, 284, 293, 296,
    299, 302, 305, 308, 311, 314, 317, 320, 323, 326,
    329, 332, 335, 338, 350, 353, 356, 359, 362, 365,
    368, 371, 374, 377, 386, 389, 392, 395
]

# Pretend to be a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://www.weatherapi.com/'
}

# Create output directory
os.makedirs("weather_icons", exist_ok=True)

# Download with headers
for code in weather_codes:
    url = f"https://cdn.weatherapi.com/weather/64x64/day/{code}.png"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        with open(f"weather_icons/{code}.png", "wb") as f:
            f.write(response.content)
        print(f"Downloaded icon for code {code}")
    else:
        print(f"Failed to download icon for code {code}, status: {response.status_code}")
