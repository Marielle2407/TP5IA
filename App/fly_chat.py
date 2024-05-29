from io import BytesIO
from fpdf import FPDF
import mysql.connector
from dotenv import load_dotenv
import os
import tempfile
from datetime import datetime


# Charger les variables d'environnement
load_dotenv()

db_config = {
    'user': os.getenv('username_data'),
    'password': os.getenv('password'),
    'host': 'localhost',
    'database': 'site'
}
# Fonction pour vérifier si une chaîne est un code IATA
def is_iata_code(string):
    return len(string) == 3 and string.isalpha()

# Fonction pour rechercher le code IATA d'une ville
def get_iata_code(city_name):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT IATA FROM airports WHERE city LIKE %s", (city_name,))
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    return result['IATA'] if result else None

def get_airport_name(iata_code):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT CITY FROM airports WHERE IATA LIKE %s", (iata_code,))
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    return result['CITY'] if result else None
# Fonction pour rechercher le nom de la compagnie aérienne
def get_airline_name(iata_code):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT AIRLINE FROM airlines WHERE IATA_CODE LIKE %s", (iata_code,))

    result = cursor.fetchone()
    cursor.close()
    connection.close()
    return result['AIRLINE'] if result else None

# Fonction de recherche de vols
def search_flights(origin, destination, day, airline=None):
    if not is_iata_code(origin):
        origin = get_iata_code(origin)
    if not is_iata_code(destination):
        destination = get_iata_code(destination)

    if not origin or not destination:
        return []

    query = "SELECT * FROM vols WHERE ORIGIN_AIRPORT=%s AND DESTINATION_AIRPORT=%s"
    params = [origin, destination]
    if day:
        year, month, day = map(int, day.split('-'))
        query += " AND YEAR=%s AND MONTH=%s AND DAY=%s"
        params.extend([year, month, day])
    if airline:
        query += " AND AIRLINE=%s"
        params.append(airline)

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, params)
    flights = cursor.fetchall()
    cursor.close()
    connection.close()
    
    # Ajouter les noms des compagnies aériennes
    for flight in flights:
        flight['AIRLINE_NAME'] = get_airline_name(flight['AIRLINE'])
        flight['ORIGIN_NAME'] = get_airport_name(flight['ORIGIN_AIRPORT'])
        flight['DESTINATION_NAME'] = get_airport_name(flight['DESTINATION_AIRPORT'])

    return flights


def format_time(time):
    """Formate une heure au format HHMM en HH:MM"""
    time = int(time)
    hours = time // 100
    minutes = time % 100
    return f"{hours:02d}:{minutes:02d}"





def table_generator(vols):
    response = """
    <table class='table table-striped table-bordered'>
        <thead class='thead-dark'>
            <tr>
                <th>Numéro</th>
                <th>Identifiant du Vol</th>
                <th>Départ</th>
                <th>Arrivée</th>
                <th>Date</th>
                <th>Compagnie</th>
                <th>Prix</th>
            </tr>
        </thead>
        <tbody>
    """
    if isinstance(vols, list) and len(vols) == 0:
        pass
    for i, vol in enumerate(vols):
        departure_time = format_time(vol['SCHEDULED_DEPARTURE'])
        arrival_time = format_time(vol['SCHEDULED_ARRIVAL'])
        response += f"""
            <tr>
                <td>{i + 1}</td>
                <td>{vol['FLIGHT_NUMBER']}</td>
                <td>{vol['ORIGIN_AIRPORT']} ({vol['ORIGIN_NAME']}) à {departure_time}</td>
                <td>{vol['DESTINATION_AIRPORT']} ({vol['DESTINATION_NAME']}) à {arrival_time}</td>
                <td>{vol['DAY']:02d}-{vol['MONTH']:02d}-{vol['YEAR']}</td>
                <td>{vol['AIRLINE_NAME']} ({vol['AIRLINE']})</td>
                <td>{vol['PRICE']} EUR</td>
            </tr>
        """
    response += "</tbody></table><br>"
    return response
def generate_ticket_pdf(user, flight, reservation_date):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    logo_path ='../static/img/logoFly.png'

    if os.path.exists(logo_path):
        print("lea c'est ici")
        pdf.image(logo_path, 10, 8, 33)

    pdf.cell(200, 10, txt="Détails de la réservation", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Nom: {user.nom} {user.prenom}", ln=True)
    pdf.cell(200, 10, txt=f"Email: {user.email}", ln=True)
    pdf.cell(200, 10, txt=f"Vol: {flight['FLIGHT_NUMBER']}", ln=True)
    pdf.cell(200, 10, txt=f"Départ: {flight['ORIGIN_AIRPORT']} ({flight['ORIGIN_NAME']}) à {format_time(flight['SCHEDULED_DEPARTURE'])}", ln=True)
    pdf.cell(200, 10, txt=f"Arrivée: {flight['DESTINATION_AIRPORT']} ({flight['DESTINATION_NAME']}) à {format_time(flight['SCHEDULED_ARRIVAL'])}", ln=True)
    pdf.cell(200, 10, txt=f"Date: {flight['DAY']:02d}-{flight['MONTH']:02d}-{flight['YEAR']}", ln=True)
    pdf.cell(200, 10, txt=f"Compagnie: {flight['AIRLINE_NAME']} ({flight['AIRLINE']})", ln=True)
    pdf.cell(200, 10, txt=f"Prix: {flight['PRICE']} EUR", ln=True)
    pdf.cell(200, 10, txt=f"Reservation Date: {reservation_date.strftime('%Y-%m-%d %H:%M:%S')}", ln=True)

    ticket_dir = os.path.join('media', 'tickets')
    if not os.path.exists(ticket_dir):
        os.makedirs(ticket_dir)
        
    reservation_date_str = reservation_date.strftime('%Y%m%d_%H%M%S')
    ticket_filename = f"ticket_{user.id}_{flight['FLIGHT_NUMBER']}_{reservation_date_str}.pdf"
    ticket_path = os.path.join(ticket_dir, ticket_filename)

    pdf.output(ticket_path)
    return ticket_path