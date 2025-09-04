# Sage AI Comptable

Application IA comptable avec intégration Sage Business Cloud Accounting

## 🚀 Fonctionnalités

- **Agent IA Comptable** : Assistant intelligent spécialisé en comptabilité
- **Intégration Sage Business Cloud** : Connexion directe avec votre compte Sage
- **12 Outils Sage** : Gestion complète des clients, factures, produits, rapports
- **Traitement de documents** : Analyse automatique de factures, relevés bancaires
- **Interface moderne** : Application web responsive avec React + Tailwind CSS

## 🛠️ Technologies

### Frontend
- **React 18** avec Vite
- **Tailwind CSS** pour le design
- **Lucide React** pour les icônes
- **Context API** pour la gestion d'état

### Backend
- **Flask** avec Python 3.9+
- **CrewAI** pour l'agent IA
- **SQLAlchemy** pour la base de données
- **JWT** pour l'authentification
- **OAuth2** pour l'intégration Sage

## 🔧 Configuration Railway

### Variables d'environnement requises

```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://api.openai.com/v1

# Sage Business Cloud API
SAGE_CLIENT_ID=your_sage_client_id
SAGE_CLIENT_SECRET=your_sage_client_secret

# Base de données (automatique sur Railway)
DATABASE_URL=postgresql://...
```

## 📦 Déploiement

L'application est configurée pour un déploiement automatique sur Railway :

1. **Push sur GitHub** → Déploiement automatique
2. **Build automatique** → Frontend + Backend
3. **URLs fixes** → Plus de domaines changeants
4. **HTTPS automatique** → Sécurisé par défaut

## 🎯 Utilisation

1. **Connexion** avec vos identifiants
2. **Intégration Sage** via OAuth2
3. **Chat avec l'Agent IA** pour vos questions comptables
4. **Upload de documents** pour analyse automatique
5. **Gestion complète** de votre comptabilité

## 🔐 Sécurité

- **JWT Authentication** pour les sessions
- **OAuth2** pour l'intégration Sage
- **CORS** configuré pour la sécurité
- **Variables d'environnement** pour les secrets

## 📊 Agent IA

L'agent comptable dispose de 12 outils Sage :
- Gestion des clients et fournisseurs
- Création et suivi des factures
- Analyse des bilans et comptes de résultat
- Traitement automatique de documents
- Import/export de données comptables

## 🚀 URLs de Production

- **Application** : https://sage-ai-comptable.railway.app
- **API** : https://sage-ai-comptable.railway.app/api

---

**Développé avec ❤️ pour automatiser votre comptabilité**

