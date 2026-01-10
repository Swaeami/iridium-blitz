#!/usr/bin/env python3
"""
Hysteria2 API Client
Provides interface to interact with Hysteria2 server API
"""

import requests
from dataclasses import dataclass
from typing import Dict, List, Optional


class Hysteria2Error(Exception):
    """Exception raised for Hysteria2 API errors."""
    pass


@dataclass
class ClientStatus:
    """Represents a client's online status."""
    is_online: bool
    connections: int = 0
    tx_bytes: int = 0
    rx_bytes: int = 0


class Hysteria2Client:
    """Client for interacting with Hysteria2 server API."""
    
    def __init__(self, base_url: str, secret: str, timeout: int = 10):
        """
        Initialize Hysteria2 API client.
        
        Args:
            base_url: Base URL of the Hysteria2 API (e.g., 'http://127.0.0.1:25413')
            secret: API authentication secret from config
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.secret = secret
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': secret,
            'Content-Type': 'application/json'
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an API request."""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('timeout', self.timeout)
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise Hysteria2Error(f"API request failed: {e}")
    
    def get_online_clients(self) -> Dict[str, ClientStatus]:
        """
        Get list of online clients with their status.
        
        Returns:
            Dict mapping username to ClientStatus
        """
        try:
            response = self._request('GET', '/traffic')
            data = response.json()
            
            result = {}
            for username, stats in data.items():
                result[username] = ClientStatus(
                    is_online=True,
                    connections=stats.get('connCount', 1),
                    tx_bytes=stats.get('tx', 0),
                    rx_bytes=stats.get('rx', 0)
                )
            return result
            
        except Exception as e:
            raise Hysteria2Error(f"Failed to get online clients: {e}")
    
    def get_traffic(self) -> Dict[str, dict]:
        """
        Get traffic statistics for all users.
        
        Returns:
            Dict mapping username to traffic stats
        """
        try:
            response = self._request('GET', '/traffic')
            return response.json()
        except Exception as e:
            raise Hysteria2Error(f"Failed to get traffic: {e}")
    
    def get_traffic_stats(self, clear: bool = False) -> Dict[str, dict]:
        """
        Get traffic statistics for all users with optional clear.
        
        Args:
            clear: If True, clears the traffic stats after retrieval
            
        Returns:
            Dict mapping username to traffic stats
        """
        try:
            params = {'clear': 'true'} if clear else {}
            response = self._request('GET', '/traffic', params=params)
            return response.json()
        except Exception as e:
            raise Hysteria2Error(f"Failed to get traffic stats: {e}")
    
    def kick_clients(self, usernames: List[str]) -> bool:
        """
        Kick (disconnect) specified clients.
        
        Args:
            usernames: List of usernames to kick
            
        Returns:
            True if successful
        """
        try:
            # Hysteria2 expects POST to /kick with list of usernames
            response = self._request('POST', '/kick', json=usernames)
            return response.status_code == 200
        except Exception as e:
            raise Hysteria2Error(f"Failed to kick clients: {e}")
    
    def kick_client(self, username: str) -> bool:
        """
        Kick a single client.
        
        Args:
            username: Username to kick
            
        Returns:
            True if successful
        """
        return self.kick_clients([username])
    
    def get_user_traffic(self, username: str) -> Optional[dict]:
        """
        Get traffic for a specific user.
        
        Args:
            username: Username to get traffic for
            
        Returns:
            Traffic dict or None if user not found
        """
        traffic = self.get_traffic()
        return traffic.get(username)
    
    def is_user_online(self, username: str) -> bool:
        """
        Check if a user is currently online.
        
        Args:
            username: Username to check
            
        Returns:
            True if user is online
        """
        try:
            online_clients = self.get_online_clients()
            return username in online_clients
        except:
            return False

