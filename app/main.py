from flask import Flask, request, render_template, flash, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import os
import uuid
import logging
from typing import List

from .config import Config
from .utils.audacity_handler import AudioProcessor  # Ensure correct import path

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Validate file upload
        if 'file' not in request.files:
            logger.warning('No file part in the request')
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Check if filename is empty
        if file.filename == '':
            logger.warning('No selected file')
            flash('No selected file')
            return redirect(request.url)
        
        # Validate file type
        if file and file.filename.lower().endswith('.mp3'):
            try:
                # Generate unique filename
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{unique_id}_{secure_filename(file.filename)}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Save uploaded file
                file.save(filepath)
                logger.info(f"File saved successfully: {filepath}")
                
                # Process audio
                processor = AudioProcessor()
                output_files = processor.process_audio(filepath)
                
                # Log output files
                logger.info(f"Generated segments: {output_files}")
                
                # Prepare segment paths for template
                segment_paths = [
                    os.path.basename(segment) 
                    for segment in output_files
                ]
                
                return render_template(
                    'result.html', 
                    output_files=segment_paths,
                    original_filename=filename
                )
            
            except Exception as e:
                # Comprehensive error logging
                logger.error(f"Error processing file: {str(e)}", exc_info=True)
                flash(f'Error processing file: {str(e)}')
                return redirect(request.url)
        
        else:
            # Invalid file type
            logger.warning(f'Invalid file type: {file.filename}')
            flash('Please upload an MP3 file')
            return redirect(request.url)
    
    return render_template('index.html')

@app.route('/segments/<filename>')
def serve_segment(filename):
    """
    Serve audio segment files
    
    Args:
        filename (str): Name of the segment file
    
    Returns:
        Flask response with audio segment file
    """
    try:
        segments_dir = os.path.join(
            app.config['UPLOAD_FOLDER'], 
            'segments'  # Adjust based on your segment storage strategy
        )
        return send_from_directory(segments_dir, filename)
    
    except FileNotFoundError:
        logger.error(f"Segment file not found: {filename}")
        flash('Segment file not found')
        return redirect(url_for('upload_file'))

@app.errorhandler(500)
def handle_500(error):
    """
    Custom 500 error handler
    
    Args:
        error: Flask error object
    
    Returns:
        Rendered error template
    """
    logger.error(f"Server Error: {str(error)}", exc_info=True)
    return render_template('error.html', error=str(error)), 500

@app.errorhandler(404)
def handle_404(error):
    """
    Custom 404 error handler
    
    Args:
        error: Flask error object
    
    Returns:
        Rendered error template
    """
    logger.warning(f"Page Not Found: {str(error)}")
    return render_template('error.html', error='Page Not Found'), 404

if __name__ == '__main__':
    # Additional configuration for development
    app.secret_key = os.urandom(24)  # For flash messages
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=True
    )