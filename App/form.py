

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import get_db



class ChatInputForm(FlaskForm):
    message = StringField('Message', validators=[DataRequired()])
    submit = SubmitField('Envoyer')

class RegistrationForm(FlaskForm):
    """
    Formulaire d'inscription au chatbot
    """
    nom = StringField('Nom', validators=[DataRequired(message="Ce champ est obligatoire.")])
    prenom = StringField('Prénom', validators=[DataRequired(message="Ce champ est obligatoire.")])
    email = StringField('Email', validators=[DataRequired(message="Ce champ est obligatoire."), Email(message="Adresse email invalide.")])
    password = PasswordField('Mot de passe', validators=[DataRequired(message="Ce champ est obligatoire.")])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(message="Ce champ est obligatoire."), EqualTo('password', message="Les mots de passe doivent correspondre.")])
    submit = SubmitField("S'inscrire")

class LoginForm(FlaskForm):
    """
    Formulaire de connexion au chatbot
    """
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')


# form.py


class UpdateProfileForm(FlaskForm):
    nom = StringField('Nom', validators=[DataRequired()])
    prenom = StringField('Prenom', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Mettre à jour')

class ChangePasswordForm(FlaskForm):
    password = PasswordField('Nouveau mot de passe', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Changer le mot de passe')