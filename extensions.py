import os
from database import Database
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

load_dotenv()

# Initialize database - support Render persistent disk
DB_PATH = os.environ.get('DATABASE_PATH', 'data/sales_trainer.db')
db = Database(DB_PATH)

# Initialize other extensions
limiter = Limiter(key_func=get_remote_address)
mail = Mail()
