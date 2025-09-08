# Development Environment Setup

## Overview

This guide helps you set up the Sage AI Comptable application for local development.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Git

## Development Workflow

### 1. Clone and Setup

```bash
git clone https://github.com/mrabia/sage-ai-comptable.git
cd sage-ai-comptable
git checkout dev
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the development environment template:
```bash
cp .env.development .env
```

Edit `.env` with your actual credentials:
- `OPENAI_API_KEY`: Your OpenAI API key
- `SAGE_CLIENT_ID`: Your Sage Business Cloud client ID
- `SAGE_CLIENT_SECRET`: Your Sage Business Cloud client secret

### 4. Database Setup

```bash
cd backend
flask db upgrade
```

### 5. Frontend Setup

```bash
cd frontend
npm install
```

### 6. Running the Application

**Backend (Terminal 1):**
```bash
cd backend
python src/main.py
```

**Frontend (Terminal 2):**
```bash
cd frontend
npm start
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

## Development Branch Workflow

- **Development work**: Always work on the `dev` branch
- **Testing**: Test locally before pushing to `dev`
- **Deployment**: When ready, the `dev` branch will be merged to `main` for Railway deployment

## Environment Differences

- **Development**: Uses SQLite database, debug mode enabled
- **Production**: Uses PostgreSQL, optimized for Railway deployment

## Troubleshooting

### Common Issues

1. **Database connection errors**: Ensure SQLite file permissions are correct
2. **AI agent errors**: Verify OPENAI_API_KEY is set correctly
3. **Sage API errors**: Check SAGE_CLIENT_ID and SAGE_CLIENT_SECRET

### Getting Help

If you encounter issues during development, check:
1. Environment variables are set correctly
2. All dependencies are installed
3. Database migrations are up to date

