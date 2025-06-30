import pandas as pd


## Please check the comfor_index  file first for an explanation of the formular.

def normalize_cloud_coverage(value):
    if value <= 10:
        return 10.0
    elif value <= 24:
        return 8 + (10 - 8) * (24 - value) / (24 - 10)
    elif value <= 49:
        return 5 + (8 - 5) * (49 - value) / (49 - 25)
    elif value <= 90:
        return 2 + (5 - 2) * (90 - value) / (90 - 50)
    else:
        return max(0, 0 + (2 - 0) * (100 - value) / (100 - 90))

def normalize_uv_index(value):
    if value <= 2:
        return value * 2  # up to 4
    elif value <= 5:
        return 4 + (8 - 4) * (value - 2) / (5 - 2)
    elif value <= 7:
        return 8 + (10 - 8) * (value - 5) / (7 - 5)
    elif value <= 10:
        return 10.0
    else:
        return 10.0

def normalize_visibility(value):
    if value > 30000:
        return 10.0
    elif value > 10000:
        return 9 + (10 - 9) * (value - 10000) / (30000 - 10000)
    elif value > 4000:
        return 3 + (8 - 3) * (value - 4001) / (10000 - 4001)
    elif value > 1000:
        return 1 + (2 - 1) * (value - 1001) / (4000 - 1001)
    else:
        return 0.0

def normalize_rain(value):
      ## the gap between 8 and 9 represent the unwilliness to have rain
    if value == 0.0:
        return 10.0
    elif value <= 0.9:
        return 9.0
    elif value <= 10:
        return max(5, 8 - (value - 1) * (3/9))  # 8 to 5
    elif value <= 30:
        return max(1, 5 - (value - 11) * (4/19))  # 5 to 1
    else:
        return 0.0

def normalize_snow(present):
      ## we need to revisit this logic here, in some rare case what if someone would like a bit of snow? This can be like a easter egg function for the broswer mode. 
    return 10.0 if not present else 0.0

def classify_sunny_level(score):
    if score >= 9:
        return 'Very Sunny'
    elif score >= 7:
        return 'Sunny'
    elif score >= 5:
        return 'Partly Sunny'
    elif score >= 3:
        return 'Mostly Cloudy'
    else:
        return 'Overcast'

def calculate_sunny_score(row):
    cloud = normalize_cloud_coverage(row['cloud_coverage'])
    uv = normalize_uv_index(row['uv_index'])
    vis = normalize_visibility(row['visibility_m'])
    rain = normalize_rain(row['rain_mm'])
    snow = normalize_snow(row['snow_present'])

    final_score = round((cloud + uv + vis + rain + snow) / 5, 2)
    level = classify_sunny_level(final_score)

    return pd.Series({
        'Cloud_Score': round(cloud, 2),
        'UV_Score': round(uv, 2),
        'Visibility_Score': round(vis, 2),
        'Rain_Score': round(rain, 2),
        'Snow_Score': round(snow, 2),
        'Sunny_Score': final_score,
        'Sunny_Level': level
    })

# # Example batch
# data = [
#     {'location': 'Loc1', 'cloud_coverage': 12, 'uv_index': 6, 'visibility_m': 25000, 'rain_mm': 0.0, 'snow_present': False},
#     {'location': 'Loc2', 'cloud_coverage': 15, 'uv_index': 7, 'visibility_m': 30000, 'rain_mm': 0.0, 'snow_present': False},
#     {'location': 'Loc3', 'cloud_coverage': 8,  'uv_index': 5, 'visibility_m': 15000, 'rain_mm': 0.2, 'snow_present': False},
#     {'location': 'Loc4', 'cloud_coverage': 5,  'uv_index': 8, 'visibility_m': 45000, 'rain_mm': 0.0, 'snow_present': False},
# ]

# df = pd.DataFrame(data)
# results = df.apply(calculate_sunny_score, axis=1)
# df_final = pd.concat([df, results], axis=1)

# print(df_final[['location', 'Sunny_Score', 'Sunny_Level', 'Cloud_Score', 'UV_Score', 'Visibility_Score', 'Rain_Score', 'Snow_Score']])
