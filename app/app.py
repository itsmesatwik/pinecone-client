from flask import Flask, render_template
import os
from dotenv import load_dotenv
from app.server import setup_routes, setup_pinecone

# Load environment variables
load_dotenv()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Initialize Pinecone client
    pc = setup_pinecone(os.getenv("PINECONE_API_KEY"))
    
    # Set up routes
    setup_routes(app, pc)
    
    # Override the index route to use the template
    @app.route('/')
    def home():
        return render_template('base.html')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000) 