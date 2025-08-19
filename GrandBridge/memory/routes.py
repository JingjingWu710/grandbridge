from flask import current_app, render_template, request, redirect, url_for, Blueprint
import os
from werkzeug.utils import secure_filename
from GrandBridge.models import db, Memory
from flask_login import current_user, login_required

memory = Blueprint('memory', __name__)


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'mp3', 'wav'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@memory.route('/memory')
@login_required
def memories():
    memories = Memory.query.filter_by(userid=current_user.id).order_by(Memory.created_at.desc()).all()
    return render_template('memory.html', memories=memories)

@memory.route('/memories_wall/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        files = request.files.getlist('file[]')
        text = request.form.get('text', '')

        for file in files:
            if file and '.' in file.filename:
                filename = secure_filename(file.filename)
                filetype = file.content_type
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                memory = Memory(filename=filename, filetype=filetype, text=text, userid=current_user.id)
                db.session.add(memory)

        db.session.commit()
        return redirect(url_for('memory.memories', id=current_user.id))

    return render_template('upload.html')