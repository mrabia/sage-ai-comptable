# Dockerfile pour le backend Sage AI Comptable
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Créer le répertoire de base de données
RUN mkdir -p src/database

# Exposer le port
EXPOSE 5001

# Variables d'environnement par défaut
ENV FLASK_APP=src.main:app
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Commande de démarrage
CMD ["python", "-c", "import sys; sys.path.insert(0, '.'); from src.main import app; app.run(host='0.0.0.0', port=5001, debug=False)"]

