import datetime
import sqlite3
import os
import hashlib
import click

from config import config
from models.medics import Medics
from models.patients import Patients
from models.caregivers import Caregivers
from models.credentials import Credentials
from models.treatmentplan import TreatmentPlans
from models.reports import Reports

class DatabaseOperations:

    def __init__(self):
        self.conn = sqlite3.connect(config.config["db_path"])
        self.cur = self.conn.cursor()
        self._create_new_table()

        self.n_param = 2
        self.r_param = 8
        self.p_param = 1
        self.dklen_param = 64

        self.today_date = datetime.date.today()

    def _create_new_table(self):

        self.cur.execute('''CREATE TABLE IF NOT EXISTS Credentials(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL, 
            hash_password TEXT NOT NULL,
            role TEXT CHECK(UPPER(role) IN ('MEDIC', 'PATIENT', 'CAREGIVER')) NOT NULL,
            public_key TEXT NOT NULL,
            private_key TEXT NOT NULL
            );''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS Medics(
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            lastname TEXT NOT NULL,
            birthday TEXT NOT NULL,
            specialization TEXT NOT NULL,
            mail TEXT,
            phone TEXT,
            FOREIGN KEY(username) REFERENCES Credentials(username)
            );''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS Patients(
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            lastname TEXT NOT NULL,
            birthday TEXT NOT NULL,
            birth_place TEXT NOT NULL,
            residence TEXT NOT NULL,
            autonomous INTEGER CHECK(autonomous IN (0,1)) NOT NULL,
            phone TEXT, 
            FOREIGN KEY(username) REFERENCES Credentials(username)
            );''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS Caregivers(
            username_patient TEXT NOT NULL,
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            lastname TEXT NOT NULL,
            relationship TEXT NOT NULL,
            phone TEXT,
            FOREIGN KEY(username) REFERENCES Credentials(username)
            FOREIGN KEY(username_patient) REFERENCES Patients(username)
            );''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS Reports(
            id_report INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            username_patient TEXT NOT NULL,
            username_medic TEXT NOT NULL,
            analyses TEXT NOT NULL,
            diagnosis TEXT NOT NULL,
            FOREIGN KEY(username_patient) REFERENCES Patients(username),
            FOREIGN KEY(username_medic) REFERENCES Medics(username)
            );''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS TreatmentPlans(
            id_treament_plan INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            username_patient TEXT NOT NULL,
            username_medic TEXT NOT NULL,
            description TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            FOREIGN KEY(username_patient) REFERENCES Patients(username),
            FOREIGN KEY(username_medic) REFERENCES Medics(username)
            );''')
        self.conn.commit()
    
    def register_creds(self, username, hash_password, role, public_key, private_key):
        try:
            if self.check_username(username) == 0:
                hashed_passwd = self.hash_function(hash_password)
                self.cur.execute("""
                                INSERT INTO Credentials
                                (username, hash_password, role, public_key, private_key) VALUES (?, ?, ?, ?, ?)""",
                                (
                                    username,
                                    hashed_passwd,
                                    role,
                                    public_key,
                                    private_key
                                ))
                self.conn.commit()
                return 0
            else:
                return -1  # Username already exists
        except sqlite3.IntegrityError:
            return -1

    def check_username(self, username):
        self.cur.execute("SELECT COUNT(*) FROM Credentials WHERE username = ? UNION ALL SELECT COUNT(*) FROM Patients WHERE username = ?", (username, username,))
        if self.cur.fetchone()[0] == 0: return 0
        else: return -1

    def check_unique_phone_number(self, phone):
        query_patients = "SELECT COUNT(*) FROM Patients WHERE phone = ?"
        self.cur.execute(query_patients, (phone,))
        count_patients = self.cur.fetchone()[0]

        query_medics = "SELECT COUNT(*) FROM Medics WHERE phone = ?"
        self.cur.execute(query_medics, (phone,))
        count_medics = self.cur.fetchone()[0]

        query_caregivers = "SELECT COUNT(*) FROM Caregivers WHERE phone = ?"
        self.cur.execute(query_caregivers, (phone,))
        count_caregivers = self.cur.fetchone()[0]

        if count_patients == 0 and count_medics == 0 and count_caregivers == 0:
            return 0 
        else:
            return -1  
        
    def check_unique_email(self, mail):
        query_medics = "SELECT COUNT(*) FROM Medics WHERE mail = ?"
        self.cur.execute(query_medics, (mail,))
        count_medics = self.cur.fetchone()[0]

        if count_medics == 0:
            return 0 
        else:
            return -1

    def key_exists(self, public_key, private_key):
        try:
            query = "SELECT public_key, private_key FROM Credentials WHERE public_key=? OR private_key=?"
            existing_users = self.cur.execute(query, (public_key, private_key)).fetchall()
            return len(existing_users) > 0
        except Exception as e:
            print("An error occurred:", e)
            return False 
        
    def insert_patient(self, username, name, lastname, birthday, birth_place, residence, autonomous, phone):
        try:
            self.cur.execute("""
                            INSERT INTO Patients
                            (username, name, lastname, birthday, birth_place, residence, autonomous, phone)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?) """,
                            (
                                username,
                                name, 
                                lastname,
                                birthday,
                                birth_place,
                                residence,
                                autonomous,
                                phone
                            ))
            self.conn.commit()
            return 0
        except sqlite3.IntegrityError:
            return -1
        
    def insert_report(self, username_patient, username_medic, analyses, diagnosis):
        try:
            self.cur.execute("""
                            INSERT INTO Reports
                            (date, username_patient, username_medic, analyses, diagnosis)
                            VALUES (?, ?, ?, ?, ?) """,
                            (
                                self.today_date,
                                username_patient, 
                                username_medic,
                                analyses,
                                diagnosis
                            ))
            self.conn.commit()
            return 0
        except sqlite3.IntegrityError:
            return -1
        
    def insert_treatment_plan(self, username_patient, username_medic, description, start_date, end_date):
        try:
            self.cur.execute("""
                            INSERT INTO TreatmentPlans
                            (date, username_patient, username_medic, description, start_date, end_date)
                            VALUES (?, ?, ?, ?, ?, ?) """,
                            (
                                self.today_date,
                                username_patient, 
                                username_medic,
                                description,
                                start_date,
                                end_date
                            ))
            self.conn.commit()
            return 0
        except sqlite3.IntegrityError:
            return -1
        
    def insert_medic(self, username, name, lastname, birthday, specialization, mail, phone):
        try:
            self.cur.execute("""
                            INSERT INTO Medics
                            (username, name, lastname, birthday, specialization, mail, phone) 
                            VALUES (?, ?, ?, ?, ?, ?, ?) """,
                            (
                                username,
                                name,
                                lastname,
                                birthday,
                                specialization,
                                mail,
                                phone
                            ))
            self.conn.commit()
            return 0
        except sqlite3.IntegrityError:
            return -1

    def insert_caregiver(self, username, name, lastname, username_patient, relationship, phone):
        try:
            self.cur.execute("""
                            INSERT INTO Caregivers
                            (username, name, lastname, username_patient, relationship, phone) 
                            VALUES (?, ?, ?, ?, ?, ?) """,
                            (
                                username,
                                name, 
                                lastname,
                                username_patient,
                                relationship,
                                phone
                            ))
            self.conn.commit()
            return 0
        except sqlite3.IntegrityError:
            return -1

    def check_patient_by_username(self, username): #forse non serve
            self.cur.execute("SELECT COUNT(*) FROM Patients WHERE username = ?", (username,))
            if self.cur.fetchone()[0] == 0: return 0
            else: return -1

    def get_creds_by_username(self, username):
        creds = self.cur.execute("""
                                SELECT *
                                FROM Credentials
                                WHERE username=?""", (username,)).fetchone()
        if creds is not None:
            return Credentials(*creds)
        return None

    def get_user_by_username(self, username):
        role = self.get_role_by_username(username)
        if role == 'MEDIC':
            user = self.cur.execute("""
                                    SELECT *
                                    FROM Medics
                                    WHERE Medics.username = ?""", (username,)).fetchone()
            if user is not None:
                return Medics(*user)
        elif role == 'PATIENT':
            user = self.cur.execute("""
                                    SELECT *
                                    FROM Patients
                                    WHERE Patients.username = ?""", (username,)).fetchone()
            if user is not None: 
                return Patients(*user)
        elif role == 'CAREGIVER':
            user = self.cur.execute("""
                                     SELECT *
                                     FROM Caregivers
                                     WHERE Caregivers.username = ?""", (username,)).fetchone()
            if user is not None:
                return Caregivers(*user)
        return None
    
    def get_role_by_username(self, username):
        role = self.cur.execute("""
                                SELECT role
                                FROM Credentials
                                WHERE username = ?""", (username,))
        role = self.cur.fetchone()  
        if role:
            return role[0]
        else:
            pat = self.check_patient_by_username(username)
            if pat:
                 return "PATIENT"
            else:
                return None
            
    def get_public_key_by_username(self, username):
        """
        Retrieve the public key for a given username from the Credentials table.

        Args:
            username (str): The username of the user whose public key is to be retrieved.

        Returns:
            str: The public key of the user if found, None otherwise.
        """
        try:
            self.cur.execute("SELECT public_key FROM Credentials WHERE username = ?", (username,))
            result = self.cur.fetchone()
            if result:
                return result[0]  # Return the public key
            else:
                return None  # Public key not found
        except Exception as e:
            print("An error occurred while retrieving public key:", e)
            return None

    def hash_function(self, password: str):

        """Hashes the supplied password using the scrypt algorithm.
    
        Args:
            password: The password to hash.
            n: CPU/Memory cost factor.
            r: Block size.
            p: Parallelization factor.
            dklen: Length of the derived key.
    
        Returns:
            A string containing the hashed password and the parameters used for hashing.
        """

        salt = os.urandom(16)
        digest = hashlib.scrypt(
            password.encode(), 
            salt = salt,
            n = self.n_param,
            r = self.r_param,
            p = self.p_param,
            dklen = self.dklen_param
        )
        hashed_passwd = f"{digest.hex()}${salt.hex()}${self.n_param}${self.r_param}${self.p_param}${self.dklen_param}"
        return hashed_passwd

    
    def check_credentials(self, username, password, public_key, private_key):
        creds = self.get_creds_by_username(username)
        if(creds is not None and self.check_passwd(username, password) and creds.get_public_key() == public_key and private_key == creds.get_private_key()):
            return True
        else:
            return False
    

    def check_passwd(self, username, password):

        result = self.cur.execute("""
                                SELECT hash_password
                                FROM Credentials
                                WHERE username =?""", (username,))
        hash = result.fetchone()
        if hash:
            saved_hash = hash[0]
            params = saved_hash.split('$')
            hashed_passwd = hashlib.scrypt(
                password.encode('utf-8'),
                salt=bytes.fromhex(params[1]),
                n = int(params[2]),
                r = int(params[3]),
                p = int(params[4]),
                dklen= int(params[5])
            )
        return hashed_passwd.hex() == params[0]
    

    def change_passwd(self, username, old_pass, new_pass):
        creds = self.get_creds_by_username(username)
        if creds is not None:
            new_hash = self.hash_function(new_pass)
            try:
                self.cur.execute("""
                                UPDATE Credentials
                                SET hash_password = ?
                                WHERE username = ?""", (new_hash, username))
                self.conn.commit()
                return 0
            except Exception as ex:
                raise ex
        else:
            return -1
    
    def get_treatmentplan_by_username(self, username):
        treatmentplan = self.cur.execute("""
                                    SELECT *
                                    FROM TreatmentPlans
                                    WHERE username_patient =?""", (username,)).fetchone()
        return TreatmentPlans(*treatmentplan)

    def get_medic_by_username(self, username):
        medic = self.cur.execute("""
                                    SELECT *
                                    FROM Medics
                                    WHERE username =?""", (username,)).fetchone()
        return Medics(*medic)
    
    def get_reports_list_by_username(self, username):
        reportslist = self.cur.execute("""
                                    SELECT *
                                    FROM Reports
                                    WHERE username_patient =?""", (username,))       
        return [Reports(*report) for report in reportslist]
    
    def get_treatplan_list_by_username(self, username):
        treatmentplanslist = self.cur.execute("""
                                    SELECT *
                                    FROM TreatmentPlans
                                    WHERE username_patient =?""", (username,))       
        return [TreatmentPlans(*treatmentplan) for treatmentplan in treatmentplanslist]
    
    def get_patients_for_doctor(self, username):
            query = """
                SELECT Patients.username, Patients.name, Patients.lastname
                FROM Patients
                INNER JOIN DoctorPatientRelationships ON Patients.username = DoctorPatientRelationships.patient_username
                WHERE DoctorPatientRelationships.username = ?
            """
            # OPPURE
            query2 = """
                SELECT Patients.username, Patients.name, Patients.lastname
                FROM Patients
            
                WHERE Patients.medic_id = ?
            """
            self.cur.execute(query2, (username,))
            return self.cur.fetchall()
    
    def get_patients(self):
            query = """
                SELECT *
                FROM Patients
            """
            self.cur.execute(query)
            return self.cur.fetchall()

    # def get_patient_info(self, username):
    #     query = """
    #         SELECT * FROM Patients WHERE username = ?
    #     """
    #     self.cur.execute(query, (username,))
    #     return self.cur.fetchone()
    
    # def get_caregiver_info(self, username):
    #     query = """
    #         SELECT * FROM Caregivers WHERE username = ?
    #     """
    #     self.cur.execute(query, (username,))
    #     return self.cur.fetchone()
    
    # def get_medic_info(self, username):
    #     query = """
    #         SELECT * FROM Medics WHERE username = ?
    #     """
    #     self.cur.execute(query, (username,))
    #     return self.cur.fetchone()

    # def update_profile(self, username, new_data):
        
    #     role = self.get_role_by_username(username)
    #     try:
    #         if role == 'CAREGIVER':
    #             query = """
    #                 UPDATE Caregivers
    #                 SET name = ?, lastname = ?, phone = ?
    #                 WHERE username = ?
    #             """
    #             self.cur.execute(query, (new_data['name'], new_data['lastname'], new_data['phone'], username))
    #             self.conn.commit()
    #             return 0

    #         elif role == 'PATIENT':
    #             query = """
    #                 UPDATE Patients
    #                 SET name = ?, lastname = ?, birthday = ?, birth_place = ?, residence = ?, autonomous = ?, phone = ?
    #                 WHERE username = ?
    #             """
    #             self.cur.execute(query, (new_data['name'], new_data['lastname'], new_data['birthday'], 
    #                                 new_data['birth_place'], new_data['residence'], new_data['autonomous'], 
    #                                 new_data['phone'], username))
    #             self.conn.commit()
    #             return 0
                

    #         elif role == 'MEDIC':
    #             query = """
    #                 UPDATE Medics
    #                 SET name = ?, lastname = ?, birthday = ?, specialization = ?, mail = ?, phone = ?
    #                 WHERE username = ?
    #             """
    #             self.cur.execute(query, (new_data['name'], new_data['lastname'], new_data['birthday'], new_data['specialization'], new_data['mail'], new_data['phone'], username))
    #             self.conn.commit()
    #             return 0
    #         else:
    #             print("Invalid user role!")
    #             return 
    #     except: 
    #         return -1
