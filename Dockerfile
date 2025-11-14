FROM python:3.11-slim

WORKDIR /app

# Copy backend files
COPY backend/ ./backend/

# Install dependencies
RUN pip install --upgrade pip setuptools wheel

# Install backend requirements without heavy NLP packages
COPY backend/requirements.txt ./backend/requirements.txt
RUN cd backend && pip install -r requirements.txt

# Expose port (Railway will inject $PORT)
EXPOSE 8000

# Start command: Run uvicorn with 4 workers
CMD cd backend && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4
