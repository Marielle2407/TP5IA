import os
from getpass import getpass

def create_env_file():
    secret_key = getpass("Enter your SECRET_KEY: ")
    username_data = input("Enter your username_data: ")
    password = getpass("Enter your password: ")

    env_content = f"""
SECRET_KEY='{secret_key}'
username_data='{username_data}'
password='{password}'
    """

    with open("App/.env", "w") as file:
        file.write(env_content.strip())
    with open("notebook/.env", "w") as file:
        file.write(env_content.strip())

    print("Environment file (.env) created successfully in both directories.")

def execute_to_sql():
    os.system("python NoteBook/to_sql.py")

if __name__ == "__main__":
    create_env_file()
    execute_to_sql()
