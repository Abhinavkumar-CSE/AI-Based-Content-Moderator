from flask import Flask, render_template, request, redirect, url_for
from text_moderator import check_text_content
from image_moderator import check_image_content
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Use an absolute path for better robustness in different environments
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file uploads to 16MB

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    """Renders the main moderation input form."""
    return render_template('index.html')

@app.route('/moderate', methods=['POST'])
def moderate():
    """
    Handles content moderation requests.
    Processes text input and/or image uploads,
    calls respective moderation functions, and renders results.
    """
    text_result = None
    image_result = None
    errors = []

    # Process text input from the form
    user_text = request.form.get('user_text') # Matches 'name="user_text"' in index.html
    if user_text:
        try:
            # Call the text moderation function
            text_result = check_text_content(user_text)
            # For debugging, print the final text result in the app console
            print(f"Final Text Result in app.py: {text_result}")
        except Exception as e:
            errors.append(f"Error processing text: {e}")
            print(f"App level error processing text: {e}") # Log the error

    # Process image upload from the form
    uploaded_file = request.files.get('image')
    if uploaded_file and uploaded_file.filename != '':
        try:
            # Secure the filename to prevent directory traversal attacks
            filename = secure_filename(uploaded_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # Save the uploaded file
            uploaded_file.save(filepath)
            
            # Call the image moderation function
            image_result = check_image_content(filepath)
            
            if image_result:
                # Store relative path for URL_for in the template
                image_result['filename'] = os.path.join('uploads', filename)
            else:
                errors.append("Image moderation returned an empty result.")
            # For debugging, print the final image result in the app console
            print(f"Final Image Result in app.py: {image_result}")
        except Exception as e:
            errors.append(f"Error processing image: {e}")
            print(f"App level error processing image: {e}") # Log the error
    elif uploaded_file and uploaded_file.filename == '':
        # Case where file input was present but no file was selected
        errors.append("No image selected for upload.")

    # If neither text nor image was provided, inform the user
    if not user_text and (not uploaded_file or uploaded_file.filename == ''):
        errors.append("Please provide text or upload an image for moderation.")
        # Redirect back to the index page with errors
        return render_template('index.html', errors=errors)

    # Render the results page with moderation outcomes and any errors
    return render_template('result.html', text_result=text_result, image_result=image_result, errors=errors)

if __name__ == '__main__':
    # Run the Flask application in debug mode
    # Debug mode provides detailed error messages in the browser
    # and reloads the server on code changes.
    # IMPORTANT: Set debug=False in a production environment.
    app.run(debug=True)

