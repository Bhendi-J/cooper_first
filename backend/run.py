from app import create_app
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)   # Run the Flask app in debug mode

