from flask import current_app, render_template, request, redirect, url_for, Blueprint, flash
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

@memory.route('/memory/delete/<int:id>')
@login_required
def delete_memory(id):
    # Find the memory by ID and ensure it belongs to the current user
    memory_to_delete = Memory.query.filter_by(id=id, userid=current_user.id).first()
    
    # If memory doesn't exist or doesn't belong to the user, redirect
    if not memory_to_delete:
        # You could also flash an error message here
        return redirect(url_for('memory.memories'))
    
    # Delete the file from the filesystem if it exists
    if memory_to_delete.filename:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], memory_to_delete.filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                # Log the error or flash a warning, but continue with database deletion
                pass
    
    # Delete the memory from the database
    db.session.delete(memory_to_delete)
    db.session.commit()
    
    flash('You have successfully deleted this memory.', 'info')
    
    # Redirect back to the memories page
    return redirect(url_for('memory.memories'))