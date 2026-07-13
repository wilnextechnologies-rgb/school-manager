from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import os, csv, io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'YOUR_NEON_CONNECTION_STRING'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def admin_required(f):
    @wraps(f)
    @login_required
    def wrap(*args, **kwargs):
        if current_user.role != 'Admin':
            flash('Access denied. Admin only.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return wrap

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Teacher')
    full_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SchoolSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school_name = db.Column(db.String(200), nullable=False, default='My School')
    school_address = db.Column(db.Text, nullable=True)
    school_phone = db.Column(db.String(50), nullable=True)
    school_email = db.Column(db.String(120), nullable=True)
    school_motto = db.Column(db.String(200), nullable=True)
    principal_name = db.Column(db.String(100), nullable=True)
    principal_title = db.Column(db.String(100), nullable=True, default='Principal')
    city = db.Column(db.String(100), nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    po_box = db.Column(db.String(100), nullable=True)
    term_begins = db.Column(db.String(20), nullable=True)
    closing_date = db.Column(db.String(20), nullable=True)


class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    section = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    students = db.relationship('Student', backref='class_', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admission_number = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    date_of_birth = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    marks = db.relationship('Mark', backref='student', lazy=True, cascade='all, delete-orphan')
    password_hash = db.Column(db.String(200), nullable=True)
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return self.password_hash and check_password_hash(self.password_hash, password)

class ExamType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    term = db.Column(db.String(20), nullable=True)
    max_marks = db.Column(db.Float, nullable=False, default=100)
    subject_count = db.Column(db.Integer, nullable=False, default=5)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    marks = db.relationship('Mark', backref='exam_type', lazy=True)

class GradeSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    grade = db.Column(db.String(5), nullable=False)
    min_percentage = db.Column(db.Float, nullable=False)
    max_percentage = db.Column(db.Float, nullable=False)
    performance_level = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    points = db.Column(db.Float, nullable=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    teacher = db.Column(db.String(100), nullable=True)

class SubjectAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    teacher_name = db.Column(db.String(100), nullable=False)
    subject = db.relationship('Subject', backref='assignments')
    class_ = db.relationship('Class', backref='subject_assignments')

class Mark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    exam_type_id = db.Column(db.Integer, db.ForeignKey('exam_type.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    max_marks = db.Column(db.Float, nullable=False, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(500), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.String(20), nullable=True)
    class_ = db.relationship('Class', backref='assignments')
    subject = db.relationship('Subject', backref='assignment_list')

    teacher = db.relationship('User', backref='assignments')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_school_settings():
    s = SchoolSettings.query.first()
    if not s:
        s = SchoolSettings(school_name='My School')
        db.session.add(s)
        db.session.commit()
    gs = GradeSetting.query.order_by(GradeSetting.min_percentage.desc()).all()
    return dict(school=s, grade_settings=gs)

def create_default_admin():
    if not User.query.filter_by(role='Admin').first():
        a = User(username='admin', email='admin@school.com', role='Admin', full_name='System Administrator')
        a.set_password('admin123')
        db.session.add(a)
        db.session.commit()

def seed_subjects():
    if Subject.query.count() == 0:
        for s in ['Mathematics', 'English', 'Science', 'Social Studies', 'Kiswahili', 'Agriculture', 'Pre-Technical', 'CRE', 'Creative Arts']:
            db.session.add(Subject(name=s))
        db.session.commit()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form.get('username')).first()
        if u and u.check_password(request.form.get('password')):
            login_user(u)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if request.form.get('password') != request.form.get('confirm_password'):
            flash('Passwords do not match', 'danger')
            return render_template('signup.html')
        username = request.form.get('username').strip()
        if User.query.filter_by(username=username).first():
            flash('Username exists', 'danger')
            return render_template('signup.html')
        email = request.form.get('email', '').strip()
        if email == '': email = None
        u = User(username=username, email=email, full_name=request.form.get('full_name'), role=request.form.get('role', 'Teacher'))
        u.set_password(request.form.get('password'))
        db.session.add(u); db.session.commit()
        flash('Account created!', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user(); flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html',
        student_count=Student.query.count(),
        teacher_count=User.query.filter_by(role='Teacher').count(),
        class_count=Class.query.count(),
        exam_count=ExamType.query.count())

@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        adm = request.form.get('admission_number', '').strip()
        s = Student.query.filter_by(admission_number=adm).first()
        if s:
            session['student_id'] = s.id
            flash('Welcome ' + s.full_name + '!', 'success')
            return redirect(url_for('student_dashboard'))
        flash('Invalid admission number', 'danger')
    return render_template('student_login.html')

@app.route('/student-dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))
    s = Student.query.get(session['student_id'])
    assignments = Assignment.query.filter_by(class_id=s.class_id).order_by(Assignment.created_at.desc()).all()
    return render_template('student_dashboard.html', student=s, assignments=assignments)

@app.route('/student-logout')
def student_logout():
    session.pop('student_id', None)
    return redirect(url_for('student_login'))
@app.route('/school-settings', methods=['GET', 'POST'])
@admin_required
def school_settings():
    s = SchoolSettings.query.first()
    if not s: s = SchoolSettings(school_name='My School'); db.session.add(s); db.session.commit()
    if request.method == 'POST':
        for f in ['school_name', 'school_address', 'school_phone', 'school_email', 'school_motto', 'principal_name', 'principal_title', 'city', 'po_box', 'term_begins', 'closing_date']:
            setattr(s, f, request.form.get(f, getattr(s, f)))
        if 'logo' in request.files:
            fl = request.files['logo']
            if fl and fl.filename and fl.filename.strip():
                fn = secure_filename(fl.filename); fl.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
                s.logo_url = url_for('static', filename='uploads/' + fn)
        db.session.commit(); flash('Settings saved!', 'success')
        return redirect(url_for('school_settings'))
    return render_template('school_settings.html', settings=s)

@app.route('/students', methods=['GET', 'POST'])
@admin_required
def students():
    if request.method == 'POST':
        s = Student(admission_number=request.form.get('admission_number'),
            first_name=request.form.get('first_name'), last_name=request.form.get('last_name'),
            email=request.form.get('email'), phone=request.form.get('phone'),
            address=request.form.get('address'), date_of_birth=request.form.get('date_of_birth'),
            gender=request.form.get('gender'), class_id=request.form.get('class_id'))
        if request.form.get('password', '').strip():
            s.set_password(request.form.get('password'))
        db.session.add(s); db.session.commit()
        flash('Student registered!', 'success')
        return redirect(url_for('students'))
    return render_template('students.html', students=Student.query.order_by(Student.created_at.desc()).all(), classes=Class.query.all())

@app.route('/students/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_student(id):
    s = Student.query.get_or_404(id)
    if request.method == 'POST':
        for f in ['admission_number', 'first_name', 'last_name', 'email', 'phone', 'address', 'date_of_birth', 'gender', 'class_id']:
            setattr(s, f, request.form.get(f, getattr(s, f)))
        if request.form.get('password', '').strip():
            s.set_password(request.form.get('password'))
        db.session.commit(); flash('Student updated!', 'success')
        return redirect(url_for('students'))
    return render_template('edit_student.html', student=s, classes=Class.query.all())

@app.route('/students/delete/<int:id>')
@admin_required
def delete_student(id):
    try:
        Mark.query.filter_by(student_id=id).delete()
        db.session.delete(Student.query.get_or_404(id))
        db.session.commit(); flash('Student deleted.', 'success')
    except Exception as e:
        db.session.rollback(); flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('students'))

@app.route('/teachers', methods=['GET', 'POST'])
@admin_required
def teachers():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form.get('username')).first():
            flash('Username exists', 'danger'); return redirect(url_for('teachers'))
        email = request.form.get('email', '').strip()
        if email == '': email = None
        t = User(username=request.form.get('username'), email=email, full_name=request.form.get('full_name'), role='Teacher')
        t.set_password(request.form.get('password'))
        db.session.add(t); db.session.commit()
        flash('Teacher registered!', 'success')
        return redirect(url_for('teachers'))
    return render_template('teachers.html', teachers=User.query.filter_by(role='Teacher').all())

@app.route('/teachers/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_teacher(id):
    t = User.query.get_or_404(id)
    if request.method == 'POST':
        t.full_name = request.form.get('full_name'); t.email = request.form.get('email')
        t.username = request.form.get('username')
        if request.form.get('password', '').strip(): t.set_password(request.form.get('password'))
        db.session.commit(); flash('Teacher updated!', 'success')
        return redirect(url_for('teachers'))
    return render_template('edit_teacher.html', teacher=t)

@app.route('/teachers/delete/<int:id>')
@admin_required
def delete_teacher(id):
    t = User.query.get_or_404(id)
    if t.role == 'Admin': flash('Cannot delete Admin account.', 'danger'); return redirect(url_for('teachers'))
    db.session.delete(t); db.session.commit(); flash('Teacher deleted.', 'success')
    return redirect(url_for('teachers'))

@app.route('/classes', methods=['GET', 'POST'])
@admin_required
def classes():
    if request.method == 'POST':
        db.session.add(Class(name=request.form.get('name'), section=request.form.get('section')))
        db.session.commit(); flash('Class created!', 'success')
        return redirect(url_for('classes'))
    return render_template('classes.html', classes=Class.query.all())

@app.route('/classes/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_class(id):
    c = Class.query.get_or_404(id)
    if request.method == 'POST':
        c.name = request.form.get('name'); c.section = request.form.get('section')
        db.session.commit(); flash('Class updated!', 'success')
        return redirect(url_for('classes'))
    return render_template('edit_class.html', class_=c)

@app.route('/exams', methods=['GET', 'POST'])
@admin_required
def exams():
    if request.method == 'POST':
        db.session.add(ExamType(name=request.form.get('name'), term=request.form.get('term'),
            max_marks=request.form.get('max_marks', 100), subject_count=request.form.get('subject_count', 5),
            description=request.form.get('description')))
        db.session.commit(); flash('Exam created!', 'success')
        return redirect(url_for('exams'))
    return render_template('exams.html', exams=ExamType.query.order_by(ExamType.term).all())

@app.route('/exams/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_exam(id):
    e = ExamType.query.get_or_404(id)
    if request.method == 'POST':
        e.name = request.form.get('name'); e.term = request.form.get('term')
        e.max_marks = request.form.get('max_marks', 100); e.subject_count = request.form.get('subject_count', 5)
        e.description = request.form.get('description')
        db.session.commit(); flash('Exam updated!', 'success')
        return redirect(url_for('exams'))
    return render_template('edit_exam.html', exam=e)

@app.route('/exams/delete/<int:id>')
@admin_required
def delete_exam(id):
    Mark.query.filter_by(exam_type_id=id).delete()
    db.session.delete(ExamType.query.get_or_404(id)); db.session.commit(); flash('Exam deleted.', 'success')
    return redirect(url_for('exams'))

@app.route('/grades', methods=['GET', 'POST'])
@admin_required
def grades():
    if request.method == 'POST':
        db.session.add(GradeSetting(grade=request.form.get('grade'),
            min_percentage=request.form.get('min_percentage'), max_percentage=request.form.get('max_percentage'),
            performance_level=request.form.get('performance_level'), description=request.form.get('description'),
            points=request.form.get('points', 0)))
        db.session.commit(); flash('Grade added!', 'success')
        return redirect(url_for('grades'))
    return render_template('grades.html', grades=GradeSetting.query.order_by(GradeSetting.min_percentage.desc()).all())

@app.route('/grades/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_grade(id):
    g = GradeSetting.query.get_or_404(id)
    if request.method == 'POST':
        g.grade = request.form.get('grade'); g.min_percentage = request.form.get('min_percentage')
        g.max_percentage = request.form.get('max_percentage'); g.performance_level = request.form.get('performance_level')
        g.description = request.form.get('description'); g.points = request.form.get('points', 0)
        db.session.commit(); flash('Grade updated!', 'success')
        return redirect(url_for('grades'))
    return render_template('edit_grade.html', grade=g)

@app.route('/grades/delete/<int:id>')
@admin_required
def delete_grade(id):
    db.session.delete(GradeSetting.query.get_or_404(id)); db.session.commit(); flash('Grade deleted.', 'success')
    return redirect(url_for('grades'))

@app.route('/subjects', methods=['GET', 'POST'])
@admin_required
def subjects():
    if request.method == 'POST':
        db.session.add(Subject(name=request.form.get('name'))); db.session.commit(); flash('Subject added!', 'success')
        return redirect(url_for('subjects'))
    return render_template('subjects.html', subjects=Subject.query.all())

@app.route('/subjects/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_subject(id):
    s = Subject.query.get_or_404(id)
    if request.method == 'POST':
        s.name = request.form.get('name'); s.teacher = request.form.get('teacher')
        db.session.commit(); flash('Subject updated!', 'success')
        return redirect(url_for('subjects'))
    return render_template('edit_subject.html', subject=s)

@app.route('/subjects/delete/<int:id>')
@admin_required
def delete_subject(id):
    Mark.query.filter_by(subject_id=id).delete()
    db.session.delete(Subject.query.get_or_404(id)); db.session.commit(); flash('Subject deleted.', 'success')
    return redirect(url_for('subjects'))

@app.route('/marks', methods=['GET', 'POST'])
@login_required
def marks():
    if request.method == 'POST':
        eid = request.form.get('exam_type_id'); cid = request.form.get('class_id'); sid = request.form.get('subject_id')
        for st in Student.query.filter_by(class_id=cid).all():
            v = request.form.get(f'marks_{st.id}')
            if v and v.strip():
                ex = Mark.query.filter_by(student_id=st.id, exam_type_id=eid, subject_id=sid).first()
                if ex: ex.marks_obtained = float(v)
                else: db.session.add(Mark(student_id=st.id, exam_type_id=eid, subject_id=sid, marks_obtained=float(v), max_marks=ExamType.query.get(eid).max_marks))
        db.session.commit(); flash('Marks saved!', 'success')
        return redirect(url_for('marks'))
    return render_template('marks_entry.html', exams=ExamType.query.all(), classes=Class.query.all(), subjects=Subject.query.all())

@app.route('/api/students-by-class/<int:class_id>')
@login_required
def api_students_by_class(class_id):
    return jsonify([{'id': s.id, 'name': s.full_name, 'admission': s.admission_number} for s in Student.query.filter_by(class_id=class_id).all()])

@app.route('/api/get-marks/<int:student_id>/<int:exam_id>/<int:subject_id>')
@login_required
def api_get_marks(student_id, exam_id, subject_id):
    m = Mark.query.filter_by(student_id=student_id, exam_type_id=exam_id, subject_id=subject_id).first()
    return jsonify({'marks_obtained': m.marks_obtained if m else None})

@app.route('/merit-list', methods=['GET', 'POST'])
@login_required
def merit_list():
    results = None; se = None; sc = None
    all_subjects = Subject.query.all()
    if request.method == 'POST':
        eid = request.form.get('exam_id'); cid = request.form.get('class_id')
        se = ExamType.query.get(eid); sc = Class.query.get(cid)
        data = []
        for st in Student.query.filter_by(class_id=cid).all():
            sm = {}; to = 0; tm = 0; total_points = 0
            for subj in all_subjects:
                m = Mark.query.filter_by(student_id=st.id, exam_type_id=eid, subject_id=subj.id).first()
                if m:
                    pct = round((m.marks_obtained / m.max_marks * 100)) if m.max_marks > 0 else 0
                    g = GradeSetting.query.filter(GradeSetting.min_percentage <= pct, GradeSetting.max_percentage >= pct).order_by(GradeSetting.min_percentage.desc()).first()
                    grade_name = g.grade if g else 'N/A'; grade_points = g.points if g and g.points else 0
                    sm[subj.id] = {'marks': int(m.marks_obtained), 'grade': grade_name, 'points': grade_points}
                    to += m.marks_obtained; tm += m.max_marks; total_points += grade_points
                else: sm[subj.id] = None
            if sm:
                pct = round((to / tm * 100)) if tm > 0 else 0
                g = GradeSetting.query.filter(GradeSetting.min_percentage <= pct, GradeSetting.max_percentage >= pct).order_by(GradeSetting.min_percentage.desc()).first()
                data.append({'student': st, 'subject_marks': sm, 'total_obtained': round(to, 2), 'total_max': round(tm, 2),
                    'percentage': round(pct, 2), 'total_points': total_points, 'grade': g.grade if g else 'N/A', 'performance': g.performance_level if g else 'N/A'})
        data.sort(key=lambda x: x['total_obtained'], reverse=True)
        rk = 0; pv = None
        for i, d in enumerate(data):
            if d['total_obtained'] != pv: rk = i + 1
            d['rank'] = rk; pv = d['total_obtained']
        results = data
    return render_template('merit_list.html', results=results, exams=ExamType.query.all(), classes=Class.query.all(), selected_exam=se, selected_class=sc, all_subjects=all_subjects)

@app.route('/merit-list/print/<int:exam_id>/<int:class_id>')
@login_required
def merit_list_print(exam_id, class_id):
    se = ExamType.query.get_or_404(exam_id); sc = Class.query.get_or_404(class_id)
    all_subjects = Subject.query.all(); data = []
    for st in Student.query.filter_by(class_id=class_id).all():
        sm = {}; to = 0; tm = 0; total_points = 0
        for subj in all_subjects:
            m = Mark.query.filter_by(student_id=st.id, exam_type_id=exam_id, subject_id=subj.id).first()
            if m:
                pct = round((m.marks_obtained / m.max_marks * 100)) if m.max_marks > 0 else 0
                g = GradeSetting.query.filter(GradeSetting.min_percentage <= pct, GradeSetting.max_percentage >= pct).order_by(GradeSetting.min_percentage.desc()).first()
                grade_name = g.grade if g else 'N/A'; grade_points = g.points if g and g.points else 0
                sm[subj.id] = {'marks': int(m.marks_obtained), 'grade': grade_name, 'points': grade_points}
                to += m.marks_obtained; tm += m.max_marks; total_points += grade_points
            else: sm[subj.id] = None
        if sm:
            pct = round((to / tm * 100)) if tm > 0 else 0
            g = GradeSetting.query.filter(GradeSetting.min_percentage <= pct, GradeSetting.max_percentage >= pct).order_by(GradeSetting.min_percentage.desc()).first()
            data.append({'student': st, 'subject_marks': sm, 'total_obtained': round(to, 2), 'percentage': round(pct, 2), 'total_points': total_points, 'grade': g.grade if g else 'N/A'})
    data.sort(key=lambda x: x['total_obtained'], reverse=True)
    rk = 0; pv = None
    for i, d in enumerate(data):
        if d['total_obtained'] != pv: rk = i + 1
        d['rank'] = rk; pv = d['total_obtained']
    return render_template('merit_list_print.html', results=data, exam=se, class_=sc, all_subjects=all_subjects)

def get_grade_for_percentage(percentage):
    return GradeSetting.query.filter(GradeSetting.min_percentage <= percentage, GradeSetting.max_percentage >= percentage).order_by(GradeSetting.min_percentage.desc()).first()

@app.route('/report-card', methods=['GET', 'POST'])
@login_required
def report_card():
    rd = None; si = None; es = []
    total_marks = 0; out_of_marks = 0; rank = 0; total_students = 0; term_display = ''; current_year = ''
    if request.method == 'POST':
        si = Student.query.get(request.form.get('student_id'))
        eids = [e for e in [request.form.get('exam1_id'), request.form.get('exam2_id'), request.form.get('exam3_id')] if e and e.strip()]
        es = ExamType.query.filter(ExamType.id.in_(eids)).all()
        sd = []
        for subj in Subject.query.all():
            r = {'subject': subj, 'exams': {}}; t = 0
            for ex in es:
                m = Mark.query.filter_by(student_id=si.id, exam_type_id=ex.id, subject_id=subj.id).first()
                if m:
                    pct = round((m.marks_obtained / m.max_marks * 100)) if m.max_marks > 0 else 0
                    g = get_grade_for_percentage(pct)
                    r['exams'][ex.id] = {'mark': int(m.marks_obtained), 'grade': g.grade if g else 'N/A', 'performance': g.performance_level if g else 'N/A', 'points': g.points if g and g.points else 0}
                    t += pct
                else: r['exams'][ex.id] = None
            r['average_pct'] = round(t / len(es), 2) if es else 0
            r['overall_grade_info'] = get_grade_for_percentage(r['average_pct'])
            last_exam = es[-1] if es else None
            if last_exam and r['exams'].get(last_exam.id):
                last_grade = r['exams'][last_exam.id].get('grade', 'N/A')
                gs = GradeSetting.query.filter_by(grade=last_grade).first()
                r['grade_points'] = gs.points if gs and gs.points else 0
            else: r['grade_points'] = 0
            sd.append(r)
        teacher_map = {}
        for a in SubjectAssignment.query.all(): teacher_map[f"{a.subject_id}_{a.class_id}"] = a.teacher_name
        rd = {'subjects': sd, 'exams': es}
        pathway_map = {'SOCIAL SCIENCES': ['English', 'Kiswahili', 'Social Studies', 'CRE'], 'STEM': ['Mathematics', 'Science', 'Pre-Technical', 'Agriculture'], 'ARTS AND SPORTS': ['Creative Arts']}
        pathway_data = {}
        for pathway, subjects in pathway_map.items():
            total = 0; count = 0
            for subj in Subject.query.all():
                if subj.name in subjects:
                    for ex in es:
                        m = Mark.query.filter_by(student_id=si.id, exam_type_id=ex.id, subject_id=subj.id).first()
                        if m: total += m.marks_obtained; count += 1
            pathway_data[pathway] = round(total / count) if count > 0 else 0
        end_exam = es[-1] if es else None
        total_marks = 0
        if end_exam:
            for subj in Subject.query.all():
                m = Mark.query.filter_by(student_id=si.id, exam_type_id=end_exam.id, subject_id=subj.id).first()
                if m: total_marks += m.marks_obtained
        total_marks = round(total_marks)
        out_of_marks = Subject.query.count() * 100
        rank_exam = es[-1] if es else None
        classmates = Student.query.filter_by(class_id=si.class_id).all(); total_students = len(classmates)
        class_totals = []
        for cls in classmates:
            ct = 0
            if rank_exam:
                for subj in Subject.query.all():
                    m = Mark.query.filter_by(student_id=cls.id, exam_type_id=rank_exam.id, subject_id=subj.id).first()
                    if m: ct += m.marks_obtained
            class_totals.append(ct)
        rank = 1
        for ct in class_totals:
            if ct > total_marks: rank += 1
        term_names = list(dict.fromkeys([ex.term for ex in es if ex.term]))
        term_display = ', '.join(term_names) if term_names else 'End of Year'
        current_year = datetime.now().year
    return render_template('report_card.html', report=rd, student=si, students=Student.query.all(),
        exams=ExamType.query.all(), exams_selected=es, classes=Class.query.all(),
        teacher_map=teacher_map if si else {}, pathway_data=pathway_data if si else {},
        total_marks=total_marks, out_of_marks=out_of_marks, rank=rank, total_students=total_students,
        term_display=term_display, current_year=current_year)

@app.route('/report-cards/bulk-print', methods=['POST'])
@admin_required
def bulk_report_cards_print():
    class_id = request.form.get('class_id'); exam1_id = request.form.get('exam1_id')
    exam2_id = request.form.get('exam2_id'); exam3_id = request.form.get('exam3_id')
    sc = Class.query.get_or_404(class_id)
    students = Student.query.filter_by(class_id=class_id).all()
    eids = [e for e in [exam1_id, exam2_id, exam3_id] if e and e.strip()]
    es = ExamType.query.filter(ExamType.id.in_(eids)).all()
    all_subjects = Subject.query.all()
    teacher_map = {}
    for a in SubjectAssignment.query.all(): teacher_map[f"{a.subject_id}_{a.class_id}"] = a.teacher_name
    pathway_map = {'SOCIAL SCIENCES': ['English', 'Kiswahili', 'Social Studies', 'CRE'], 'STEM': ['Mathematics', 'Science', 'Pre-Technical', 'Agriculture'], 'ARTS AND SPORTS': ['Creative Arts']}
    all_reports = []; end_exam = es[-1] if es else None
    for st in students:
        sd = []
        for subj in all_subjects:
            r = {'subject': subj, 'exams': {}}; t = 0
            for ex in es:
                m = Mark.query.filter_by(student_id=st.id, exam_type_id=ex.id, subject_id=subj.id).first()
                if m:
                    pct = round((m.marks_obtained / m.max_marks * 100)) if m.max_marks > 0 else 0
                    g = get_grade_for_percentage(pct)
                    r['exams'][ex.id] = {'mark': int(m.marks_obtained), 'grade': g.grade if g else 'N/A'}
                    t += pct
                else: r['exams'][ex.id] = None
            r['average_pct'] = round(t / len(es), 2) if es else 0
            r['overall_grade_info'] = get_grade_for_percentage(r['average_pct'])
            last_exam = es[-1] if es else None
            if last_exam and r['exams'].get(last_exam.id):
                last_grade = r['exams'][last_exam.id].get('grade', 'N/A')
                gs = GradeSetting.query.filter_by(grade=last_grade).first()
                r['grade_points'] = gs.points if gs and gs.points else 0
            else: r['grade_points'] = 0
            sd.append(r)
        total_marks = 0
        if end_exam:
            for subj in all_subjects:
                m = Mark.query.filter_by(student_id=st.id, exam_type_id=end_exam.id, subject_id=subj.id).first()
                if m: total_marks += m.marks_obtained
        total_marks = round(total_marks); out_of_marks = len(all_subjects) * 100
        pathway_data = {}
        for pathway, subjects in pathway_map.items():
            total = 0; count = 0
            for subj in all_subjects:
                if subj.name in subjects:
                    for ex in es:
                        m = Mark.query.filter_by(student_id=st.id, exam_type_id=ex.id, subject_id=subj.id).first()
                        if m: total += m.marks_obtained; count += 1
            pathway_data[pathway] = round(total / count) if count > 0 else 0
        rank_exam = es[-1] if es else None
        class_totals = []
        for cls in students:
            ct = 0
            if rank_exam:
                for subj in all_subjects:
                    m = Mark.query.filter_by(student_id=cls.id, exam_type_id=rank_exam.id, subject_id=subj.id).first()
                    if m: ct += m.marks_obtained
            class_totals.append(ct)
        rank = 1
        for ct in class_totals:
            if ct > total_marks: rank += 1
        all_reports.append({'student': st, 'subjects': sd, 'total_marks': total_marks, 'rank': rank, 'out_of_marks': out_of_marks, 'pathway_data': pathway_data})
    term_names = list(dict.fromkeys([ex.term for ex in es if ex.term]))
    term_display = ', '.join(term_names) if term_names else 'End of Year'
    current_year = datetime.now().year
    return render_template('bulk_report_cards_print.html', all_reports=all_reports, exams=es, class_=sc,
        teacher_map=teacher_map, total_students=len(students), term_display=term_display, current_year=current_year)

@app.route('/assign-teachers', methods=['GET', 'POST'])
@admin_required
def assign_teachers():
    if request.method == 'POST':
        subject_ids = request.form.getlist('subject_ids')
        c = request.form.get('class_id')
        t = request.form.get('teacher_name').strip()
        if subject_ids and c and t:
            for s in subject_ids:
                ex = SubjectAssignment.query.filter_by(subject_id=s, class_id=c).first()
                if ex: ex.teacher_name = t
                else: db.session.add(SubjectAssignment(subject_id=s, class_id=c, teacher_name=t))
            db.session.commit(); flash(f'Teacher assigned to {len(subject_ids)} subjects!', 'success')
        return redirect(url_for('assign_teachers'))
    return render_template('assign_teachers.html', assignments=SubjectAssignment.query.all(),
        subjects=Subject.query.all(), classes=Class.query.all())

@app.route('/assign-teachers/delete/<int:id>')
@admin_required
def delete_assignment(id):
    db.session.delete(SubjectAssignment.query.get_or_404(id)); db.session.commit(); flash('Removed.', 'success')
    return redirect(url_for('assign_teachers'))

@app.route('/students/import', methods=['GET', 'POST'])
@admin_required
def students_import():
    if request.method == 'POST':
        f = request.files.get('csv_file')
        if not f or not f.filename: flash('Select a CSV file', 'danger'); return redirect(url_for('students_import'))
        text = f.stream.read().decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
        reader = csv.DictReader(io.StringIO(text)); imp = 0; err = 0
        for row in reader:
            adm = row.get('ADM', row.get('ADMNO', row.get('ADM NO', ''))).strip()
            fn = row.get('NAME', row.get('STUDENT NAME', '')).strip()
            gd = row.get('GENDER', '').strip(); gr = row.get('GRADE', row.get('CLASS', '')).strip()
            if not adm or not fn: err += 1; continue
            if Student.query.filter_by(admission_number=adm).first(): err += 1; continue
            parts = fn.split(' ', 1); first = parts[0]; last = parts[1] if len(parts) > 1 else ''
            co = None
            if gr:
                co = Class.query.filter_by(name=gr).first()
                if not co: co = Class(name=gr); db.session.add(co); db.session.commit()
            gv = gd.title() if gd.upper() in ['MALE', 'FEMALE'] else None
            db.session.add(Student(admission_number=adm, first_name=first, last_name=last, gender=gv, class_id=co.id if co else None))
            imp += 1
        db.session.commit(); flash(f'Imported {imp} students. {err} errors.', 'success')
        return redirect(url_for('students_import'))
    return render_template('students_import.html')

@app.route('/marks/import', methods=['GET', 'POST'])
@login_required
def marks_import():
    if request.method == 'POST':
        eid = request.form.get('exam_id'); f = request.files.get('csv_file')
        if not f or not f.filename: flash('Select a CSV file', 'danger'); return redirect(url_for('marks_import'))
        ex = ExamType.query.get(eid)
        if not ex: flash('Invalid exam', 'danger'); return redirect(url_for('marks_import'))
        text = f.stream.read().decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
        reader = csv.DictReader(io.StringIO(text))
        sm = {'ENG': 'English', 'KISW': 'Kiswahili', 'MATHS': 'Mathematics', 'INT/SCI': 'Science',
            'SCIENCE': 'Science', 'SCIE': 'Science', 'AGRI/NUT': 'Agriculture', 'AGRI': 'Agriculture',
            'PRETECH': 'Pre-Technical', 'SOST': 'Social Studies', 'SOCIAL': 'Social Studies',
            'SST': 'Social Studies', 'CRE': 'CRE', 'CAS': 'Creative Arts'}
        imp = 0; err = 0; nf = []
        for row in reader:
            adm = row.get('ADM', row.get('ADMNO', '')).strip()
            if not adm: err += 1; continue
            st = Student.query.filter_by(admission_number=adm).first()
            if not st:
                err += 1
                if len(nf) < 5: nf.append(adm)
                continue
            for h, v in row.items():
                hh = h.strip().upper()
                if hh in sm:
                    try: mv = float(v) if v and v.strip() else None
                    except ValueError: continue
                    if mv is not None:
                        sub = Subject.query.filter_by(name=sm[hh]).first()
                        if not sub: sub = Subject(name=sm[hh]); db.session.add(sub); db.session.commit()
                        exst = Mark.query.filter_by(student_id=st.id, exam_type_id=eid, subject_id=sub.id).first()
                        if exst: exst.marks_obtained = mv
                        else: db.session.add(Mark(student_id=st.id, exam_type_id=eid, subject_id=sub.id, marks_obtained=mv, max_marks=ex.max_marks))
            imp += 1
        db.session.commit(); msg = f'Imported {imp}. Errors {err}.'
        if nf: msg += f' ADM not found: {nf}'
        flash(msg, 'success'); return redirect(url_for('marks_import'))
    return render_template('marks_import.html', exams=ExamType.query.all())

with app.app_context():
    db.create_all(); seed_subjects(); create_default_admin()

@app.route('/assignments', methods=['GET', 'POST'])
@login_required
def assignments():
    if request.method == 'POST':
        title = request.form.get('title')
        cid = request.form.get('class_id')
        sid = request.form.get('subject_id')
        due = request.form.get('due_date')
        desc = request.form.get('description')
        furl = None
        if 'file' in request.files:
            f = request.files['file']
            if f and f.filename and f.filename.strip():
                fn = secure_filename(f.filename)
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
                furl = url_for('static', filename='uploads/' + fn)
        db.session.add(Assignment(title=title, description=desc, file_url=furl,
            class_id=cid, subject_id=sid, teacher_id=current_user.id, due_date=due))
        db.session.commit()
        flash('Assignment created!', 'success')
        return redirect(url_for('assignments'))
    return render_template('assignments.html', classes=Class.query.all(),
        subjects=Subject.query.all(), assignments=Assignment.query.order_by(Assignment.created_at.desc()).all())

@app.route('/assignments/delete/<int:id>')
@login_required
def del_assignment(id):
    a = Assignment.query.get_or_404(id)
    db.session.delete(a)
    db.session.commit()
    flash('Assignment deleted.', 'success')
    return redirect(url_for('assignments'))
@app.route('/students/clear-all')
@admin_required
def clear_all_students():
    try:
        Mark.query.delete()
        Student.query.delete()
        db.session.commit()
        flash('All students and their marks have been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('students'))

@app.route('/promote-students', methods=['GET', 'POST'])
@admin_required
def promote_students():
    if request.method == 'POST':
        from_class_id = request.form.get('from_class_id')
        to_class_id = request.form.get('to_class_id')
        if from_class_id and to_class_id:
            students = Student.query.filter_by(class_id=from_class_id).all()
            count = 0
            for s in students:
                s.class_id = to_class_id
                count += 1
            db.session.commit()
            flash(f'{count} students promoted successfully!', 'success')
            return redirect(url_for('promote_students'))
    classes = Class.query.all()
    return render_template('promote_students.html', classes=classes)


if __name__ == '__main__':
    app.run()
