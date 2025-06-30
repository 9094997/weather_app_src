import pandas as pd

# -------------------------------
# Normalization functions
# -------------------------------

## here is an instruction of how to read the fomula below:
## for example for the cloud coverage index:

    # elif value <= 50:
    #     return 7 + (9 - 7) * (50 - value) / 20
    
# this paragraph represent the calculation of cloud coverage index between 30% to 50%, the full scrip can be found below. 
# 50 represent 50% cloud coverage, 7 is the lowest score for the cloud coverage range between 10% - 30%, (9-7) is the score range for 10%-30%, 9 is the highest.
# (50-value) measure the distance between the given value and the upper limit of this range, and /20 is the range between 10%-30%, it is the normlisation factor.

# The purpose of this formular is to normalised the weather parameters into an comparable system and find the location of the given value in a pre-set score range


def normalize_cloud_comfort(value):
    ##cloud coverage index
    if value <= 10:
        return 7 + (10 - 7) * (10 - value) / 10 ## too much sun and no cloud is not a good thing, there fore we have the range of 7 to 10
    elif value <= 30:
        return 9 + (10 - 9) * (30 - value) / 20
    elif value <= 50:
        return 7 + (9 - 7) * (50 - value) / 20
    elif value <= 80:
        return 4 + (7 - 4) * (80 - value) / 30
    else:
        return max(0, 0 + (4 - 0) * (100 - value) / 20)

def normalize_uv_comfort(value):
    ##uv index in relation to the comfort index
    if value <= 2:
        return 10
    elif value <= 5:
        return 8 + (10 - 8) * (5 - value) / 3
    elif value <= 7:
        return 5 + (7 - 5) * (7 - value) / 2
    elif value <= 10:
        return 3 + (5 - 3) * (10 - value) / 3
    else:
        return max(0, 0 + (3 - 0) * (12 - min(value,12)) / 2)

def normalize_visibility_comfort(value):
    ## the more the better
    if value > 30000:
        return 10
    elif value > 10000:
        return 8 + (10 - 8) * (value - 10000) / 20000
    elif value > 4000:
        return 5 + (8 - 5) * (value - 4001) / (10000 - 4001)
    elif value > 1000:
        return 2 + (5 - 2) * (value - 1001) / (4000 - 1001)
    else:
        return 0.0

def normalize_rain_comfort(value):
    ## no rain is the best, light rain is accetable
    if value == 0.0:
        return 10.0
    elif value <= 0.9:
        return 8 + (9 - 8) * (0.9 - value) / 0.9
    elif value <= 10:
        return 5 + (8 - 5) * (10 - value) / 9
    elif value <= 30:
        return 2 + (5 - 2) * (30 - value) / 19
    else:
        return max(0, 0 + (2 - 0) * (70 - min(value,70)) / 40)

def normalize_snow_comfort(present):
    ## snow is not properly considerd at the moment, we leave this function to the fucture.
    return 10.0 if not present else 1.0

def normalize_feels_like_temp(value):
    ## this is the most important factor for the comfort index
    if 20 <= value <= 26:
        return 10.0
    elif 15 <= value < 20:
        return 7 + (10 - 7) * (20 - value) / 5
    elif 26 < value <= 30:
        return 7 + (10 - 7) * (30 - value) / 4
    elif 10 <= value < 15:
        return 4 + (7 - 3) * (15 - value) / 5
    elif 30 < value <= 35:
        return 4 + (7 - 4) * (35 - value) / 5
    else:
        if value < 10:
            return max(0, 0 + (3 - 0) * (10 - value) / 10)
        else:
            return max(0, 0 + (4 - 0) * (value - 35) / 15)

def normalize_humidity_comfort(value):
    if 40 <= value <= 60:
        return 10.0
    elif 30 <= value < 40:
        return 7 + (9 - 7) * (40 - value) / 10
    elif 60 < value <= 70:
        return 7 + (9 - 7) * (70 - value) / 10
    elif 20 <= value < 30:
        return 4 + (7 - 4) * (30 - value) / 10
    elif 70 < value <= 80:
        return 4 + (7 - 4) * (80 - value) / 10
    else:
        if value < 20:
            return max(0, 0 + (4 - 0) * (20 - value) / 20)
        else:
            return max(0, 0 + (4 - 0) * (100 - min(value,100)) / 20)

# -------------------------------
# Final classification
# -------------------------------

def classify_comfort_level(score):
    if score >= 9:
        return 'Very Comfortable'
    elif score >= 7:
        return 'Comfortable'
    elif score >= 5:
        return 'Moderate'
    elif score >= 3:
        return 'Uncomfortable'
    else:
        return 'Very Uncomfortable'

# -------------------------------
# Main function for one row
# -------------------------------

def calculate_comfort_score(row):
    cloud = normalize_cloud_comfort(row['cloud_coverage'])
    uv = normalize_uv_comfort(row['uv_index'])
    vis = normalize_visibility_comfort(row['visibility_m'])
    rain = normalize_rain_comfort(row['rain_mm'])
    snow = normalize_snow_comfort(row['snow_present'])
    feels = normalize_feels_like_temp(row['feels_like_temp'])
    humidity = normalize_humidity_comfort(row['humidity'])

    final_score = round((cloud + uv + vis + rain + snow + feels + humidity) / 7, 2)
    level = classify_comfort_level(final_score)

    return pd.Series({
        'Cloud_Score': round(cloud, 2),
        'UV_Score': round(uv, 2),
        'Visibility_Score': round(vis, 2),
        'Rain_Score': round(rain, 2),
        'Snow_Score': round(snow, 2),
        'FeelsLikeTemp_Score': round(feels, 2),
        'Humidity_Score': round(humidity, 2),
        'Comfort_Score': final_score,
        'Comfort_Level': level
    })

# -------------------------------
# Example usage
# -------------------------------

# if __name__ == "__main__":
#     data = [
#         {'location': 'Loc1', 'cloud_coverage': 20, 'uv_index': 5, 'visibility_m': 25000, 'rain_mm': 0.0, 'snow_present': False, 'feels_like_temp': 22, 'humidity': 50},
#         {'location': 'Loc2', 'cloud_coverage': 80, 'uv_index': 1, 'visibility_m': 2000, 'rain_mm': 10.0, 'snow_present': True, 'feels_like_temp': -5, 'humidity': 85},
#         {'location': 'Loc3', 'cloud_coverage': 5,  'uv_index': 7, 'visibility_m': 45000, 'rain_mm': 0.5, 'snow_present': False, 'feels_like_temp': 30, 'humidity': 65},
#     ]

#     df = pd.DataFrame(data)
#     results = df.apply(calculate_comfort_score, axis=1)
#     df_final = pd.concat([df, results], axis=1)

    # print(df_final[['location', 'Comfort_Score', 'Comfort_Level',
    #                 'Cloud_Score', 'UV_Score', 'Visibility_Score',
    #                 'Rain_Score', 'Snow_Score', 'FeelsLikeTemp_Score', 'Humidity_Score']])
