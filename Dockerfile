FROM python:3.12-slim
 
WORKDIR /app
 
# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy app files
COPY app.py .
COPY sim_rules.py .
COPY color_overrides.py .
COPY map_colors.py .
 
EXPOSE 8000
 
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
