import os
import requests
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs, urlparse
from typing import Optional, Dict, Any, List
import json

class SageOAuth2Service:
    """Service pour gérer l'authentification OAuth2 avec Sage Business Cloud Accounting"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        
        # URLs Sage OAuth2
        self.auth_url = "https://www.sageone.com/oauth2/auth/central"
        self.token_url = "https://oauth.accounting.sage.com/token"
        self.api_base_url = "https://api.accounting.sage.com/v3.1"
    
    def generate_pkce_pair(self) -> tuple[str, str]:
        """Génère une paire code_verifier et code_challenge pour PKCE"""
        # Générer code_verifier (43-128 caractères)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Générer code_challenge (SHA256 hash du code_verifier)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_authorization_url(self, state: Optional[str] = None, scope: str = "full_access", 
                            country: Optional[str] = None) -> tuple[str, str, str]:
        """
        Génère l'URL d'autorisation pour rediriger l'utilisateur vers Sage
        
        Returns:
            tuple: (authorization_url, state, code_verifier)
        """
        if not state:
            state = secrets.token_urlsafe(32)
        
        code_verifier, code_challenge = self.generate_pkce_pair()
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': scope,
            'state': state,
            'filter': 'apiv3.1',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        
        if country:
            params['country'] = country
        
        authorization_url = f"{self.auth_url}?{urlencode(params)}"
        
        return authorization_url, state, code_verifier
    
    def exchange_code_for_token(self, authorization_code: str, code_verifier: str) -> Dict[str, Any]:
        """
        Échange le code d'autorisation contre un token d'accès
        
        Args:
            authorization_code: Code d'autorisation reçu du callback
            code_verifier: Code verifier utilisé pour PKCE
            
        Returns:
            Dict contenant access_token, refresh_token, expires_in, etc.
        """
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code_verifier': code_verifier
        }
        
        response = requests.post(self.token_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            
            # Calculer l'heure d'expiration
            expires_in = token_data.get('expires_in', 300)  # 5 minutes par défaut
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            token_data['expires_at'] = expires_at.isoformat()
            
            return token_data
        else:
            raise Exception(f"Erreur lors de l'échange du code: {response.status_code} - {response.text}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Rafraîchit le token d'accès en utilisant le refresh token
        
        Args:
            refresh_token: Token de rafraîchissement
            
        Returns:
            Dict contenant le nouveau access_token et refresh_token
        """
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(self.token_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            
            # Calculer l'heure d'expiration
            expires_in = token_data.get('expires_in', 300)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            token_data['expires_at'] = expires_at.isoformat()
            
            return token_data
        else:
            raise Exception(f"Erreur lors du rafraîchissement du token: {response.status_code} - {response.text}")
    
    def is_token_expired(self, expires_at: str) -> bool:
        """
        Vérifie si le token a expiré
        
        Args:
            expires_at: Date d'expiration au format ISO
            
        Returns:
            bool: True si le token a expiré
        """
        try:
            expiry_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            # Ajouter une marge de 1 minute pour éviter les erreurs de timing
            return datetime.utcnow() >= (expiry_time - timedelta(minutes=1))
        except:
            return True  # En cas d'erreur, considérer comme expiré
    
    def get_valid_token(self, credentials: Dict[str, Any]) -> Optional[str]:
        """
        Récupère un token d'accès valide, en le rafraîchissant si nécessaire
        
        Args:
            credentials: Dictionnaire contenant les credentials Sage
            
        Returns:
            str: Token d'accès valide ou None si impossible
        """
        access_token = credentials.get('access_token')
        refresh_token = credentials.get('refresh_token')
        expires_at = credentials.get('expires_at')
        
        if not access_token:
            return None
        
        # Vérifier si le token a expiré
        if expires_at and self.is_token_expired(expires_at):
            if refresh_token:
                try:
                    # Rafraîchir le token
                    new_token_data = self.refresh_access_token(refresh_token)
                    return new_token_data.get('access_token')
                except Exception as e:
                    print(f"Erreur lors du rafraîchissement du token: {e}")
                    return None
            else:
                return None
        
        return access_token
    
    def make_authenticated_request(self, method: str, endpoint: str, credentials: Dict[str, Any],
                                 business_id: Optional[str] = None, **kwargs) -> requests.Response:
        """
        Effectue une requête authentifiée vers l'API Sage
        
        Args:
            method: Méthode HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint de l'API (sans le base URL)
            credentials: Credentials Sage de l'utilisateur
            business_id: ID du business Sage (optionnel)
            **kwargs: Arguments supplémentaires pour requests
            
        Returns:
            requests.Response: Réponse de l'API
        """
        access_token = self.get_valid_token(credentials)
        if not access_token:
            raise Exception("Token d'accès invalide ou expiré")
        
        headers = kwargs.get('headers', {})
        headers.update({
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        })
        
        if business_id:
            headers['X-Business'] = business_id
        
        kwargs['headers'] = headers
        
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        
        response = requests.request(method, url, **kwargs)
        return response
    
    def get_user_businesses(self, credentials: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Récupère la liste des businesses de l'utilisateur
        
        Args:
            credentials: Credentials Sage de l'utilisateur
            
        Returns:
            List[Dict]: Liste des businesses
        """
        try:
            response = self.make_authenticated_request('GET', 'businesses', credentials)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('$items', [])
            else:
                raise Exception(f"Erreur lors de la récupération des businesses: {response.status_code} - {response.text}")
        
        except Exception as e:
            raise Exception(f"Erreur lors de la récupération des businesses: {str(e)}")
    
    def test_connection(self, credentials: Dict[str, Any]) -> bool:
        """
        Test la connexion à l'API Sage
        
        Args:
            credentials: Credentials Sage de l'utilisateur
            
        Returns:
            bool: True si la connexion fonctionne
        """
        try:
            businesses = self.get_user_businesses(credentials)
            return len(businesses) >= 0  # Même 0 business est une connexion valide
        except:
            return False

