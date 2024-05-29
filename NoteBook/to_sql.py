import pandas as pd
from sqlalchemy import create_engine
import dotenv
import os

dotenv.load_dotenv()

username = os.getenv('username_data')
password = os.getenv('password')
#print (username, password)

engine = create_engine(f'mysql+pymysql://{username}:{password}@localhost/site')




chunksize = 10000
for chunk in pd.read_csv("../Data/En_data.csv", chunksize=chunksize, dtype={
    'YEAR': 'int16',
    'MONTH': 'int8',
    'DAY': 'int8',
    'DAY_OF_WEEK': 'int8',
    'AIRLINE': 'category',
    'FLIGHT_NUMBER': 'int32',
    'TAIL_NUMBER': 'category',
    'ORIGIN_AIRPORT': 'category',
    'DESTINATION_AIRPORT': 'category',
    'SCHEDULED_DEPARTURE': 'int16',
    'DEPARTURE_TIME': 'float32',
    'DEPARTURE_DELAY': 'float32',
    'TAXI_OUT': 'float32',
    'WHEELS_OFF': 'float32',
    'SCHEDULED_TIME': 'float32',
    'ELAPSED_TIME': 'float32',
    'AIR_TIME': 'float32',
    'DISTANCE': 'float32',
    'WHEELS_ON': 'float32',
    'TAXI_IN': 'float32',
    'SCHEDULED_ARRIVAL': 'int16',
    'ARRIVAL_TIME': 'float32',
    'ARRIVAL_DELAY': 'float32',
    'DIVERTED': 'int8',
    'CANCELLED': 'int8',
    'CANCELLATION_REASON': 'category',  
    'AIR_SYSTEM_DELAY': 'float32',
    'SECURITY_DELAY': 'float32',
    'AIRLINE_DELAY': 'float32',
    'LATE_AIRCRAFT_DELAY': 'float32',
    'WEATHER_DELAY': 'float32',
    'PRICE': 'float32'
}):  
    chunk.to_sql('vols', con=engine, if_exists='append', index=False)


for chunk in pd.read_csv("../Data/airports.csv", chunksize=1000,  dtype={
    'IATA': 'category',
    'AIRPORT': 'category',
    'CITY': 'category',
    'STATE': 'category',
    'COUNTRY': 'category',
    'LATITUDE': 'float32',
    'LONGITUDE': 'float32'
}):
    chunk.to_sql('airports', con=engine, if_exists='append', index=False)
for chunk in pd.read_csv("../Data/airlines.csv", chunksize=1000,  dtype={
    'IATA_CODE': 'category',
    'AIRLINE': 'category'
    
}):
    chunk.to_sql('airlines', con=engine, if_exists='append', index=False)