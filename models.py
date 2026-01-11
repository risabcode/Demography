import MySQLdb
import MySQLdb.cursors
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================
# DATABASE CONNECTION
# ==========================
def get_db():
    """
    Return a new DB connection using DictCursor so fetchone()/fetchall() return dicts.
    """
    return MySQLdb.connect(
        host=current_app.config['MYSQL_HOST'],
        user=current_app.config['MYSQL_USER'],
        passwd=current_app.config['MYSQL_PASSWORD'],
        db=current_app.config['MYSQL_DB'],
        cursorclass=MySQLdb.cursors.DictCursor
    )


# ==========================
# USER MODEL (Flask-Login)
# ==========================
class User(UserMixin):
    def __init__(self, id, name, email, role, profile_photo=None):
        self.id = str(id)
        self.name = name
        self.email = email
        self.role = role
        self.profile_photo = profile_photo


# ==========================
# USER OPERATIONS
# ==========================
def create_user(name, email, password, role='user', profile_photo=None):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO users (name, email, password, role, profile_photo)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (name, email, generate_password_hash(password), role, profile_photo)
    )
    db.commit()
    cur.close()
    db.close()


def get_user_by_email(email):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    cur.close()
    db.close()
    return user


def get_user_by_id(user_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    cur.close()
    db.close()
    return user


def verify_password(hash_value, password):
    return check_password_hash(hash_value, password)


def update_profile_photo(user_id, filename):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE users SET profile_photo=%s WHERE id=%s",
        (filename, user_id)
    )
    db.commit()
    cur.close()
    db.close()


def get_all_users():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cur.fetchall()
    cur.close()
    db.close()
    return users


# ==========================
# USER FORMS
# ==========================
def create_form(user_id, data):
    """
    Insert a new user form.
    `data` is a dict-like object with keys matching column names.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO user_forms (
            user_id, full_name, phone, age, gender, dob,
            aadhar_number, pan_number,
            qualification, university, passing_year,
            father_name, mother_name, family_members, marital_status,
            address, city, state, pincode, status
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            user_id,
            data.get('full_name'), data.get('phone'), data.get('age'),
            data.get('gender'), data.get('dob'),
            data.get('aadhar_number'), data.get('pan_number'),
            data.get('qualification'), data.get('university'), data.get('passing_year'),
            data.get('father_name'), data.get('mother_name'),
            data.get('family_members'), data.get('marital_status'),
            data.get('address'), data.get('city'), data.get('state'), data.get('pincode'),
            data.get('status') or 'pending'
        )
    )
    db.commit()
    cur.close()
    db.close()


def update_form_by_id(form_id, data):
    """
    Update an existing form by its ID.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute(
        """
        UPDATE user_forms SET
            full_name=%s, phone=%s, age=%s, gender=%s, dob=%s,
            aadhar_number=%s, pan_number=%s,
            qualification=%s, university=%s, passing_year=%s,
            father_name=%s, mother_name=%s, family_members=%s, marital_status=%s,
            address=%s, city=%s, state=%s, pincode=%s,
            status=%s
        WHERE id=%s
        """,
        (
            data.get('full_name'), data.get('phone'), data.get('age'),
            data.get('gender'), data.get('dob'),
            data.get('aadhar_number'), data.get('pan_number'),
            data.get('qualification'), data.get('university'), data.get('passing_year'),
            data.get('father_name'), data.get('mother_name'),
            data.get('family_members'), data.get('marital_status'),
            data.get('address'), data.get('city'), data.get('state'), data.get('pincode'),
            data.get('status') or 'pending',
            form_id
        )
    )
    db.commit()
    cur.close()
    db.close()


def create_or_update_form(user_id, data):
    """
    Backwards-compatible helper:
    - If a form exists for the user (any), update the most recent one.
    - Otherwise, create a new form.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id FROM user_forms WHERE user_id=%s ORDER BY created_at DESC LIMIT 1", (user_id,))
    exists = cur.fetchone()
    if exists:
        form_id = exists['id']
        cur.execute(
            """
            UPDATE user_forms SET
                full_name=%s, phone=%s, age=%s, gender=%s, dob=%s,
                aadhar_number=%s, pan_number=%s,
                qualification=%s, university=%s, passing_year=%s,
                father_name=%s, mother_name=%s, family_members=%s, marital_status=%s,
                address=%s, city=%s, state=%s, pincode=%s,
                status='pending'
            WHERE id=%s
            """,
            (
                data.get('full_name'), data.get('phone'), data.get('age'),
                data.get('gender'), data.get('dob'),
                data.get('aadhar_number'), data.get('pan_number'),
                data.get('qualification'), data.get('university'), data.get('passing_year'),
                data.get('father_name'), data.get('mother_name'),
                data.get('family_members'), data.get('marital_status'),
                data.get('address'), data.get('city'), data.get('state'), data.get('pincode'),
                form_id
            )
        )
    else:
        # Insert a new form
        cur.execute(
            """
            INSERT INTO user_forms (
                user_id, full_name, phone, age, gender, dob,
                aadhar_number, pan_number,
                qualification, university, passing_year,
                father_name, mother_name, family_members, marital_status,
                address, city, state, pincode, status
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                user_id,
                data.get('full_name'), data.get('phone'), data.get('age'),
                data.get('gender'), data.get('dob'),
                data.get('aadhar_number'), data.get('pan_number'),
                data.get('qualification'), data.get('university'), data.get('passing_year'),
                data.get('father_name'), data.get('mother_name'),
                data.get('family_members'), data.get('marital_status'),
                data.get('address'), data.get('city'), data.get('state'), data.get('pincode'),
                'pending'
            )
        )
    db.commit()
    cur.close()
    db.close()


def get_form_by_user(user_id):
    """
    Return the most recent form for a given user (or None).
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM user_forms WHERE user_id=%s ORDER BY created_at DESC LIMIT 1", (user_id,))
    form = cur.fetchone()
    cur.close()
    db.close()
    return form


def get_all_forms_by_user(user_id):
    """
    Fetch all forms submitted by a specific user, ordered newest-first.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT *
        FROM user_forms
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (user_id,))
    forms = cur.fetchall()
    cur.close()
    db.close()
    return forms


def get_form_by_id(form_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM user_forms WHERE id=%s", (form_id,))
    form = cur.fetchone()
    cur.close()
    db.close()
    return form


def get_all_forms():
    """
    Admin: fetch all forms along with user name/email.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT uf.*, u.name AS user_name, u.email AS user_email
        FROM user_forms uf
        JOIN users u ON uf.user_id = u.id
        ORDER BY uf.created_at DESC
    """)
    forms = cur.fetchall()
    cur.close()
    db.close()
    return forms


def update_form_status(form_id, status, remark):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE user_forms SET status=%s, admin_remark=%s WHERE id=%s",
        (status, remark, form_id)
    )
    db.commit()
    cur.close()
    db.close()


# ==========================
# TICKETS
# ==========================
def create_ticket(user_id, subject, message, form_id=None):
    """
    Create a ticket associated to a form.
    If form_id is provided it will be used; otherwise the user's latest form will be used.
    Raises ValueError if no form is available.
    """
    db = get_db()
    cur = db.cursor()

    if form_id is None:
        cur.execute("SELECT id FROM user_forms WHERE user_id=%s ORDER BY created_at DESC LIMIT 1", (user_id,))
        f = cur.fetchone()
        if not f:
            cur.close()
            db.close()
            raise ValueError("User has no form; cannot create ticket without an associated form.")
        form_id = f['id']

    # Insert ticket
    cur.execute(
        """
        INSERT INTO tickets (user_id, form_id, subject, message)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, form_id, subject, message)
    )
    db.commit()
    cur.close()
    db.close()


def get_tickets_by_user(user_id):
    """
    Get tickets for a user, including the associated form's basic info.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT t.*, uf.full_name AS form_full_name, uf.id AS form_id
        FROM tickets t
        JOIN user_forms uf ON t.form_id = uf.id
        WHERE t.user_id=%s
        ORDER BY t.created_at DESC
    """, (user_id,))
    tickets = cur.fetchall()
    cur.close()
    db.close()
    return tickets


def get_ticket_by_id(ticket_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT t.*, u.name AS user_name, u.email AS user_email, uf.full_name AS form_full_name, uf.id AS form_id
        FROM tickets t
        JOIN users u ON t.user_id = u.id
        JOIN user_forms uf ON t.form_id = uf.id
        WHERE t.id=%s
    """, (ticket_id,))
    ticket = cur.fetchone()
    cur.close()
    db.close()
    return ticket


def get_all_tickets():
    """
    Admin: return all tickets joined with user + form info.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT t.id, t.user_id, t.form_id, t.subject, t.message, t.status, t.admin_response, t.created_at, t.updated_at,
               u.name AS user_name, u.email AS user_email,
               uf.full_name AS form_full_name
        FROM tickets t
        JOIN users u ON t.user_id = u.id
        JOIN user_forms uf ON t.form_id = uf.id
        ORDER BY t.created_at DESC
    """)
    tickets = cur.fetchall()
    cur.close()
    db.close()
    return tickets


def update_ticket_status(ticket_id, status, admin_response):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE tickets SET status=%s, admin_response=%s WHERE id=%s",
        (status, admin_response, ticket_id)
    )
    db.commit()
    cur.close()
    db.close()


# ==========================
# ADMIN STATS
# ==========================
def get_stats(time_from=None):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) AS total FROM users")
    users = cur.fetchone()['total']

    # optional time filter
    time_clause = ""
    params = ()
    if time_from:
        time_clause = "WHERE created_at >= %s"
        params = (time_from,)

    cur.execute(f"SELECT status, COUNT(*) AS count FROM user_forms {time_clause} GROUP BY status", params)
    forms = cur.fetchall()

    cur.execute(f"SELECT status, COUNT(*) AS count FROM tickets {time_clause} GROUP BY status", params)
    tickets = cur.fetchall()

    cur.close()
    db.close()

    return {"users": users, "forms": forms, "tickets": tickets}

def get_all_forms_admin():
    """
    Admin: fetch all forms with user name & email
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT 
            uf.*,
            u.name AS user_name,
            u.email AS user_email
        FROM user_forms uf
        JOIN users u ON uf.user_id = u.id
        ORDER BY uf.created_at DESC
    """)
    forms = cur.fetchall()
    cur.close()
    db.close()
    return forms


def get_all_forms(time_from=None):
    db = get_db()
    cur = db.cursor()
    query = "SELECT * FROM user_forms"
    params = []
    if time_from:
        query += " WHERE created_at >= %s"
        params.append(time_from)
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    forms = cur.fetchall()
    cur.close()
    db.close()
    return forms

def get_all_forms_time_filtered(time_from):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT *
        FROM user_forms
        WHERE created_at >= %s
        ORDER BY created_at DESC
    """, (time_from,))
    forms = cur.fetchall()
    cur.close()
    db.close()
    return forms



def get_all_tickets(time_from=None):
    db = get_db()
    cur = db.cursor()
    query = "SELECT * FROM tickets"
    params = []
    if time_from:
        query += " WHERE created_at >= %s"
        params.append(time_from)
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    tickets = cur.fetchall()
    cur.close()
    db.close()
    return tickets
