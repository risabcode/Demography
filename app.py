import os

from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, abort
)


from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user
)

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

import pymysql
pymysql.install_as_MySQLdb()

from config import Config
import models
from decorators import admin_required
from datetime import datetime, timedelta

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config.from_object(Config)

# ---------- Login manager ----------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# ---------- Ensure upload folder ----------
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------- flask-login user loader ----------
@login_manager.user_loader
def load_user(user_id):
    row = models.get_user_by_id(user_id)
    if not row:
        return None
    return models.User(
        row['id'],
        row['name'],
        row['email'],
        row['role'],
        row.get('profile_photo')
    )


# ==========================
# AUTH
# ==========================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email').lower()
        password = request.form.get('password')

        if models.get_user_by_email(email):
            flash("Email already registered", "danger")
            return redirect(url_for('register'))

        photo = request.files.get('profile_photo')
        filename = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        models.create_user(
            name=name,
            email=email,
            password=password,
            role='user',
            profile_photo=filename
        )

        flash("Registration successful. Please login.", "success")
        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')

        user = models.get_user_by_email(email)
        if not user or not check_password_hash(user['password'], password):
            flash("Invalid credentials", "danger")
            return redirect(url_for('login'))

        login_user(models.User(
            user['id'],
            user['name'],
            user['email'],
            user['role'],
            user.get('profile_photo')
        ))

        flash("Login successful", "success")
        return redirect(url_for('admin_dashboard' if user['role'] == 'admin' else 'user_dashboard'))

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))


# ==========================
# USER
# ==========================
@app.route('/')
@login_required
def user_dashboard():
    forms = models.get_all_forms_by_user(current_user.id)
    tickets = models.get_tickets_by_user(current_user.id)
    return render_template('user/dashboard.html', user=current_user, forms=forms, tickets=tickets)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        photo = request.files.get('profile_photo')
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            models.update_profile_photo(current_user.id, filename)
            flash("Profile updated", "success")
            return redirect(url_for('profile'))

    return render_template('user/profile.html', user=current_user)


@app.route('/form', methods=['GET','POST'])
@app.route('/form/<int:form_id>', methods=['GET','POST'])
@login_required
def user_form(form_id=None):
    if request.method == 'POST':
        form_data = request.form.to_dict()
        if form_id:
            existing = models.get_form_by_id(form_id)
            if not existing or int(existing['user_id']) != int(current_user.id):
                flash("Invalid form selected for editing.", "danger")
                return redirect(url_for('user_dashboard'))
            models.update_form_by_id(form_id, form_data)
        else:
            models.create_or_update_form(current_user.id, form_data)

        flash("Form submitted successfully", "success")
        return redirect(url_for('user_dashboard'))

    if form_id:
        form = models.get_form_by_id(form_id)
        template = "user/edit_form.html"
    else:
        form = models.get_form_by_user(current_user.id)
        template = "user/form.html"

    return render_template(template, form=form)


@app.route('/form/<int:form_id>/delete', methods=['POST', 'GET'])
@login_required
def delete_form(form_id):
    models.delete_form(form_id, current_user.id)
    flash("Form deleted successfully.", "success")
    return redirect(url_for('user_dashboard'))


@app.route('/ticket/<int:ticket_id>/delete', methods=['POST', 'GET'])
@login_required
def delete_ticket(ticket_id):
    models.delete_ticket(ticket_id, current_user.id)
    flash("Ticket deleted successfully.", "success")
    return redirect(url_for('user_dashboard'))


@app.route('/tickets', methods=['GET', 'POST'])
@login_required
def user_tickets():
    # 🚫 Admins should NEVER use user tickets page
    if current_user.role == 'admin':
        return redirect(url_for('admin_tickets'))

    forms = models.get_all_forms_by_user(current_user.id)

    if not forms:
        flash("You must submit a form before raising a ticket.", "warning")
        return redirect(url_for('user_form'))

    if request.method == 'POST':
        form_id = request.form.get('form_id')
        subject = request.form.get('subject')
        message = request.form.get('message')

        if not form_id:
            flash("Please choose a form for this ticket.", "danger")
            return redirect(url_for('user_tickets'))

        selected_form = models.get_form_by_id(form_id)
        if not selected_form or int(selected_form['user_id']) != int(current_user.id):
            flash("Selected form is invalid.", "danger")
            return redirect(url_for('user_tickets'))

        if not subject or not message:
            flash("Subject and message are required.", "danger")
            return redirect(url_for('user_tickets'))

        try:
            models.create_ticket(
                current_user.id,
                subject,
                message,
                form_id=int(form_id)
            )
            flash("Ticket submitted successfully", "success")
        except Exception as e:
            flash(f"Could not create ticket: {e}", "danger")

        return redirect(url_for('user_tickets'))

    tickets = models.get_tickets_by_user(current_user.id)
    return render_template(
        'user/tickets.html',
        forms=forms,
        tickets=tickets
    )


@app.route('/tickets/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    ticket = models.get_ticket_by_id(ticket_id)
    if not ticket:
        abort(404)

    if current_user.role != 'admin' and int(ticket['user_id']) != int(current_user.id):
        flash("You don't have permission to view this ticket.", "danger")
        return redirect(url_for('user_dashboard'))

    return render_template('user/view_ticket.html', ticket=ticket)


# ==========================
# ADMIN
# ==========================
@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = models.get_stats()
    # Get latest 10 forms to show in "Recent Forms" (sorted by created_at desc if available)
    try:
        all_forms = models.get_all_forms()
        # Sort safely by created_at if present, otherwise keep original order
        sorted_forms = sorted(all_forms, key=lambda x: x.get('created_at', datetime.min), reverse=True)
    except Exception:
        sorted_forms = models.get_all_forms() or []

    # Build a lightweight preview for the dashboard table (avoid heavy nested data)
    forms_preview = []
    for f in sorted_forms[:10]:
        user_row = None
        try:
            user_row = models.get_user_by_id(f.get('user_id'))
        except Exception:
            user_row = None
        forms_preview.append({
            'id': f.get('id'),
            'email': user_row.get('email') if user_row else f.get('email') or '',
            'status': f.get('status', 'unknown')
        })

    return render_template('admin/dashboard.html', stats=stats, forms=forms_preview)


@app.route('/admin/users')
@admin_required
def admin_users():
    users = models.get_all_users()
    return render_template('admin/users.html', users=users)


@app.route('/admin/forms')
@admin_required
def admin_forms():
    forms = models.get_all_forms_admin()

    open_forms = []
    in_progress_forms = []
    resolved_forms = []

    for f in forms:
        status = (f.get('status') or 'open').lower()

        if status in ['open', 'pending']:
            open_forms.append(f)
        elif status in ['in_progress', 'processing']:
            in_progress_forms.append(f)
        else:
            resolved_forms.append(f)

    return render_template(
        'admin/forms.html',
        open_forms=open_forms,
        in_progress_forms=in_progress_forms,
        resolved_forms=resolved_forms
    )



@app.route('/admin/forms/<int:form_id>/update', methods=['POST'])
@admin_required
def admin_form_update(form_id):
    data = request.form.to_dict()

    status = data.pop('status', None)
    admin_remark = data.pop('admin_remark', None)

    # update full form
    models.update_form_by_id(form_id, data)

    # update admin-only fields
    models.update_form_status(form_id, status, admin_remark)

    flash("Form updated successfully", "success")
    return redirect(url_for('admin_form_detail', form_id=form_id))


# NEW: admin form detail view (GET) + show a quick update form (POST handled by admin_form_update)
@app.route('/admin/forms/<int:form_id>')
@admin_required
def admin_form_detail(form_id):
    form = models.get_form_by_id(form_id)
    if not form:
        abort(404)

    user_row = None
    try:
        user_row = models.get_user_by_id(form.get('user_id'))
    except Exception:
        user_row = None

    return render_template('admin/form_detail.html', form=form, user=user_row)


@app.route('/admin/tickets', methods=['GET', 'POST'])
@admin_required
def admin_tickets():
    if request.method == 'POST':
        models.update_ticket_status(
            request.form.get('ticket_id'),
            request.form.get('status'),
            request.form.get('admin_response')
        )
        flash("Ticket updated", "success")
        return redirect(url_for('admin_tickets'))

    tickets = models.get_all_tickets()
    return render_template('admin/tickets.html', tickets=tickets)


# ==========================
# API & FILES
# ==========================
from collections import defaultdict

@app.route('/api/admin/stats')
@admin_required
def api_admin_stats():
    days = request.args.get('days', 7, type=int)
    since_date = datetime.now() - timedelta(days=days)

    stats = models.get_stats(time_from=since_date)

    forms = models.get_all_forms(time_from=since_date)
    tickets = models.get_all_tickets(time_from=since_date)

    daily_forms_dict = defaultdict(int)
    daily_tickets_dict = defaultdict(int)

    for f in forms:
        created = f.get('created_at')
        if isinstance(created, datetime):
            date_str = created.strftime('%Y-%m-%d')
        else:
            # if stored as string, attempt a parse; fallback to today
            try:
                date_str = datetime.strptime(created, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
            except Exception:
                date_str = datetime.now().strftime('%Y-%m-%d')
        daily_forms_dict[date_str] += 1

    for t in tickets:
        created = t.get('created_at')
        if isinstance(created, datetime):
            date_str = created.strftime('%Y-%m-%d')
        else:
            try:
                date_str = datetime.strptime(created, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
            except Exception:
                date_str = datetime.now().strftime('%Y-%m-%d')
        daily_tickets_dict[date_str] += 1

    daily_forms = []
    daily_tickets = []
    for i in range(days):
        day = (since_date + timedelta(days=i)).strftime('%Y-%m-%d')
        daily_forms.append({'date': day, 'count': daily_forms_dict.get(day, 0)})
        daily_tickets.append({'date': day, 'count': daily_tickets_dict.get(day, 0)})

    return jsonify({
        "users": stats.get("users", 0),
        "forms": stats.get("forms", []),
        "tickets": stats.get("tickets", []),
        "dailyForms": daily_forms,
        "dailyTickets": daily_tickets
    })


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ==========================
# RUN
# ==========================
if __name__ == '__main__':
    app.run(debug=True)
