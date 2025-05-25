   from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
   from flask_sqlalchemy import SQLAlchemy
   from werkzeug.security import generate_password_hash, check_password_hash
   import os

   app = Flask(__name__)
   app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agrimoves.db'
   app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
   app.config['SECRET_KEY'] = 'change_this_to_a_secure_random_key_1234'
   db = SQLAlchemy(app)

   # Models
   class User(db.Model):
       id = db.Column(db.Integer, primary_key=True)
       username = db.Column(db.String(80), unique=True, nullable=False)
       password_hash = db.Column(db.String(128), nullable=False)

       def set_password(self, password):
           self.password_hash = generate_password_hash(password)

       def check_password(self, password):
           return check_password_hash(self.password_hash, password)

   class ContactFormSubmission(db.Model):
       id = db.Column(db.Integer, primary_key=True)
       name = db.Column(db.String(100), nullable=False)
       email = db.Column(db.String(100), nullable=False)
       message = db.Column(db.Text, nullable=False)

       def to_dict(self):
           return {"id": self.id, "name": self.name, "email": self.email, "message": self.message}

   @app.before_first_request
   def create_tables():
       db.create_all()

   def is_logged_in():
       return 'user_id' in session

   def current_username():
       if is_logged_in():
           user = User.query.filter_by(id=session['user_id']).first()
           if user:
               return user.username
       return None

   @app.route('/')
   def home():
       return render_template('index.html', logged_in=is_logged_in(), username=current_username())

   @app.route('/contact', methods=['GET'])
   def contact():
       return render_template('contact.html', logged_in=is_logged_in(), username=current_username())

   @app.route('/submit_form', methods=['POST'])
   def submit_form():
       name = request.form.get('name', '').strip()
       email = request.form.get('email', '').strip()
       message = request.form.get('message', '').strip()
       if not name or not email or not message:
           flash('All fields are required!', 'danger')
           return redirect(url_for('contact'))

       submission = ContactFormSubmission(name=name, email=email, message=message)
       db.session.add(submission)
       db.session.commit()
       flash('Thank you for your message!', 'success')
       return redirect(url_for('thank_you'))

   @app.route('/thank_you')
   def thank_you():
       return render_template('thank_you.html', logged_in=is_logged_in(), username=current_username())

   @app.route('/register', methods=['GET', 'POST'])
   def register():
       if is_logged_in():
           flash('You are already logged in.', 'info')
           return redirect(url_for('home'))
       if request.method == 'POST':
           username = request.form.get('username', '').strip()
           password = request.form.get('password', '').strip()
           confirm_password = request.form.get('confirm_password', '').strip()

           if not username or not password or not confirm_password:
               flash('Please fill in all fields.', 'danger')
               return redirect(url_for('register'))
           if password != confirm_password:
               flash('Passwords do not match.', 'danger')
               return redirect(url_for('register'))
           if User.query.filter_by(username=username).first():
               flash('Username already exists.', 'danger')
               return redirect(url_for('register'))

           new_user = User(username=username)
           new_user.set_password(password)
           db.session.add(new_user)
           db.session.commit()

           flash('Registration successful! Please log in.', 'success')
           return redirect(url_for('login'))
       return render_template('register.html', logged_in=is_logged_in())

   @app.route('/login', methods=['GET', 'POST'])
   def login():
       if is_logged_in():
           flash('You are already logged in.', 'info')
           return redirect(url_for('home'))
       if request.method == 'POST':
           username = request.form.get('username', '').strip()
           password = request.form.get('password', '').strip()
           if not username or not password:
               flash('Please provide both username and password.', 'danger')
               return redirect(url_for('login'))
           user = User.query.filter_by(username=username).first()
           if user and user.check_password(password):
               session['user_id'] = user.id
               flash(f'Welcome, {username}!', 'success')
               return redirect(url_for('home'))
           flash('Invalid username or password.', 'danger')
           return redirect(url_for('login'))
       return render_template('login.html', logged_in=is_logged_in())

   @app.route('/logout')
   def logout():
       session.pop('user_id', None)
       flash('You have been logged out.', 'success')
       return redirect(url_for('home'))

   @app.route('/api/submissions', methods=['GET'])
   def api_submissions():
       if not is_logged_in():
           return jsonify({"error": "Unauthorized"}), 401
       submissions = ContactFormSubmission.query.all()
       return jsonify([s.to_dict() for s in submissions])

   if __name__ == '__main__':
       app.run(debug=True)
   