import mysql.connector
from flask import g
import os
from flask_login import  UserMixin

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host="localhost",
            user=os.getenv('username_data'),
            password=os.getenv('password'),
            database="site"
        )
    return g.db

def create_tables():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nom VARCHAR(100) NOT NULL,
            prenom VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            session_id VARCHAR(100) NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            flight_number VARCHAR(255) NOT NULL,
            reservation_date DATETIME NOT NULL,
            ticket_path VARCHAR(255),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    db.commit()
    cursor.close()

class User(UserMixin):
    def __init__(self, id, nom, prenom, email, password):
        self.id = id
        self.nom = nom
        self.prenom = prenom
        self.email = email
        self.password = password

    def get_reservations(self):
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM reservations WHERE user_id = %s', (self.id,))
        reservations = cursor.fetchall()
        cursor.close()
        return reservations
