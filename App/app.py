from flask import Flask, render_template, redirect, request, url_for, flash, jsonify, session, g, send_file
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
import os
from models import get_db, create_tables, User
from form import RegistrationForm, LoginForm, ChatInputForm,UpdateProfileForm, ChangePasswordForm
from fly_chat import generate_ticket_pdf, search_flights, table_generator
from dotenv import load_dotenv
import mysql.connector
from fpdf import FPDF
from datetime import datetime
from nltk.chat.util import Chat, reflections

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
Session(app)

csrf = CSRFProtect(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(id=user['id'], nom=user['nom'], prenom=user['prenom'], email=user['email'], password=user['password'])
    return None

@app.before_request
def before_request():
    g.db = get_db()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/')
def base():
    return render_template('accueil.html', title='Accueil')

@app.route('/accueil')
@login_required
def home():
    form = ChatInputForm()
    user_name = current_user.nom
    return render_template('home.html', title='FlyhatBot', form=form, user_name=user_name)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute('INSERT INTO users (nom, prenom, email, password) VALUES (%s, %s, %s, %s)', (form.nom.data, form.prenom.data, form.email.data, hashed_password))
            db.commit()
            flash('Votre compte a bien été créé. Vous pouvez vous connecter.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Email déjà utilisé. Veuillez en choisir un autre.', 'danger')
        finally:
            cursor.close()
    return render_template('register.html', title='Inscription', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (form.email.data,))
        user = cursor.fetchone()
        if user and bcrypt.check_password_hash(user['password'], form.password.data):
            cursor.execute('SELECT COUNT(*) AS count FROM active_sessions WHERE user_id = %s', (user['id'],))
            active_sessions_count = cursor.fetchone()['count']
            if active_sessions_count >= 2:
                flash('Vous avez atteint la limite de sessions actives.', 'danger')
                return redirect(url_for('login'))
            login_user(User(id=user['id'], nom=user['nom'], prenom=user['prenom'], email=user['email'], password=user['password']), remember=True)
            cursor.execute('INSERT INTO active_sessions (user_id, session_id) VALUES (%s, %s)', (user['id'], session.sid))
            db.commit()
            flash('Vous êtes connecté !', 'success')
            return redirect(url_for('home'))
        else:
            flash('Erreur: Email ou mot de passe incorrect ! Veuillez réessayer.', 'danger')
        cursor.close()
    return render_template('login.html', title='Connexion', form=form)

@app.route('/logout')
@login_required
def logout():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM active_sessions WHERE user_id = %s AND session_id = %s', (current_user.id, session.sid))
    db.commit()
    cursor.close()
    logout_user()
    flash('Vous avez été déconnecté avec succès !', 'info')
    return redirect(url_for('base'))

pairs = [
    [r"\b(bonjour|salut|coucou)\b", ["Bonjour, comment puis-je vous aider à réserver un vol aujourd'hui ?", "Salut, comment puis-je vous assister avec vos réservations de vol ?"]],
    [r"je m'appelle (.*)", ["Bonjour %1, comment puis-je vous aider à réserver un vol aujourd'hui ?"]],
    [r"je veux aller à (.*)", ["D'accord, où partez-vous ?"]],
    [r"je pars de (.*)", ["Quand souhaitez-vous partir ? (format AAAA-MM-JJ)"]],
    [r"je pars le (.*)", ["Avez-vous une préférence pour une compagnie aérienne ? Si non, dites 'non'."]],
    [r"je préfère (.*)", ["Recherche de vols avec %1..."]],
    [r"non", ["Recherche de vols sans préférence de compagnie aérienne..."]],
    [r"(.*) vols de (.*) à (.*)", ["Je vais chercher des vols de %2 à %3 pour vous..."]],
    [r"au revoir|bye", ["Au revoir ! N'hésitez pas à revenir pour plus d'assistance avec vos réservations de vol."]],
    [r"(.*)", ["Je suis désolé, je ne comprends pas votre question. Pouvez-vous reformuler ou demander de l'aide pour la réservation de vols ?"]]
]

chatbot = Chat(pairs, reflections)


@app.route('/chat', methods=['POST', 'GET'])
@login_required
def chat():
    if request.method == 'GET':
        form = ChatInputForm()
        return render_template('home.html', form=form)
    user_input = request.form['message'].lower()
    user_id = current_user.id

    if 'conversation' not in session:
        session['conversation'] = {}

    if user_id not in session['conversation']:
        session['conversation'][user_id] = {
            'stage': 'init',
            'origin': None,
            'destination': None,
            'day': None,
            'airline': None,
            'flights': [],
            'selected_flight': None
        }

    convo = session['conversation'][user_id]

    if convo['stage'] == 'init':
        if 'je veux aller à' in user_input:
            convo['destination'] = user_input.split('à')[-1].strip()
            convo['stage'] = 'awaiting_origin'
            response = "Où partez-vous ?"
        else:
            response = chatbot.respond(user_input)
            if response is None:
                response = "Je suis désolé, je ne comprends pas votre demande. Pouvez-vous préciser où vous voulez aller ?"

    elif convo['stage'] == 'awaiting_origin':
        convo['origin'] = user_input.split('de')[-1].strip()
        convo['stage'] = 'awaiting_day'
        response = "Quand souhaitez-vous partir ? (format AAAA-MM-JJ)"

    elif convo['stage'] == 'awaiting_day':
        convo['day'] = user_input.split('le')[-1].strip()
        convo['stage'] = 'awaiting_airline'
        response = "Avez-vous une préférence pour une compagnie aérienne ? Si non, dites 'non'."

    elif convo['stage'] == 'awaiting_airline':
        convo['airline'] = None if user_input == 'non' else user_input.split('préféré')[-1].strip()
        convo['stage'] = 'showing_flights'
        flights = search_flights(convo['origin'], convo['destination'], convo['day'], convo['airline'])
        convo['flights'] = flights
        if flights:
            response = f"Voici les vols correspondants à votre recherche :<br>"
            response += table_generator(flights) + "<br> Veuillez entrer le numéro du vol que vous souhaitez réserver."
        else:
            response = "Aucun vol trouvé pour ces critères. Veuillez réessayer."
            convo['stage'] = 'init'

    elif convo['stage'] == 'showing_flights':
        try:
            flight_index = int(user_input) - 1
            if 0 <= flight_index < len(convo['flights']):
                selected_flight = convo['flights'][flight_index]
                convo['selected_flight'] = {k: str(v) if not isinstance(v, (int, float, str)) else v for k, v in selected_flight.items()}
                response = f"Vous avez sélectionné le vol {selected_flight['FLIGHT_NUMBER']} de {selected_flight['ORIGIN_AIRPORT']} à {selected_flight['DESTINATION_AIRPORT']} le {selected_flight['YEAR']}-{selected_flight['MONTH']:02d}-{selected_flight['DAY']:02d} avec {selected_flight['AIRLINE_NAME']} ({selected_flight['AIRLINE']}) pour {selected_flight['PRICE']} EUR. Souhaitez-vous confirmer cette réservation ? (oui/non)"
                convo['stage'] = 'confirming_reservation'
            else:
                response = "Numéro de vol invalide. Veuillez entrer un numéro de vol valide."
        except ValueError:
            response = "Numéro de vol invalide. Veuillez entrer un numéro de vol valide."

    elif convo['stage'] == 'confirming_reservation':
        if user_input == 'oui':
            selected_flight = convo['selected_flight']
            reservation_date = datetime.utcnow()
            ticket_path = generate_ticket_pdf(current_user, selected_flight, reservation_date)
            db = get_db()
            cursor = db.cursor()
            cursor.execute('INSERT INTO reservations (user_id, flight_number, reservation_date, ticket_path) VALUES (%s, %s, %s, %s)', 
                           (user_id, selected_flight['FLIGHT_NUMBER'], reservation_date, ticket_path))
            db.commit()
            cursor.close()
            response = f"Votre vol a été réservé avec succès ! Détails du vol : {selected_flight}<br>"
            response += f"<a href='/download_ticket/{user_id}/{selected_flight['FLIGHT_NUMBER']}'>Télécharger le billet</a>"
            convo['stage'] = 'init'
        else:
            response = "Réservation annulée. Puis-je vous aider avec autre chose ?"
            convo['stage'] = 'init'

    session.modified = True
    return jsonify({"response": response})

@app.route('/download_ticket/<int:user_id>/<string:flight_number>', methods=['GET'])
@login_required
def download_ticket(user_id, flight_number):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute('SELECT ticket_path FROM reservations WHERE user_id = %s AND flight_number = %s', (user_id, flight_number))
    reservation = cursor.fetchone()
    cursor.close()
    if reservation:
        ticket_path = reservation['ticket_path']
        if os.path.exists(ticket_path):
            return send_file(ticket_path, as_attachment=True, download_name=f"ticket_{flight_number}.pdf")
        else:
            flash('Ticket non trouvé.', 'danger')
            return redirect(url_for('home'))
    else:
        flash('Réservation non trouvée.', 'danger')
        return redirect(url_for('home'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    update_form = UpdateProfileForm(nom=current_user.nom, prenom=current_user.prenom, email=current_user.email)
    password_form = ChangePasswordForm()
    
    if update_form.validate_on_submit() and 'update_form' in request.form:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE users SET nom=%s, prenom=%s, email=%s WHERE id=%s', (update_form.nom.data, update_form.prenom.data, update_form.email.data, current_user.id))
        db.commit()
        cursor.close()
        flash('Profil mis à jour avec succès.', 'success')
        return redirect(url_for('profile'))

    if password_form.validate_on_submit() and 'password_form' in request.form:
        hashed_password = bcrypt.generate_password_hash(password_form.password.data).decode('utf-8')
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE users SET password=%s WHERE id=%s', (hashed_password, current_user.id))
        db.commit()
        cursor.close()
        flash('Mot de passe mis à jour avec succès.', 'success')
        return redirect(url_for('profile'))

    reservations = current_user.get_reservations()
    return render_template('profile.html', update_form=update_form, password_form=password_form, reservations=reservations)

if __name__ == '__main__':
    with app.app_context():
        create_tables()
    app.run(debug=True)
