"""
Клиент для работы с API бэкенда
"""
import requests
from typing import Optional, Dict, List, Any

class APIClient:
    """Клиент для взаимодействия с API бэкенда"""
    
    def __init__(self, base_url: str = "https://passplay.ru"):
        self.base_url = base_url.rstrip('/')
        self.pc_key: Optional[str] = None
    
    def set_key(self, pc_key: str):
        """Устанавливает ключ ПК для аутентификации"""
        self.pc_key = pc_key
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Выполняет HTTP запрос к API"""
        url = f"{self.base_url}/api{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, timeout=30)
            else:
                raise ValueError(f"Неподдерживаемый метод: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка API запроса: {e}")
            raise
    
    def get_games(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получает список игр"""
        params = {}
        if search:
            params['search'] = search
        
        return self._make_request('GET', '/games', params=params)
    
    def get_game(self, game_id: int) -> Dict[str, Any]:
        """Получает информацию об игре"""
        return self._make_request('GET', f'/games/{game_id}')
    
    def start_rental(self, game_id: int, duration_hours: int = 1) -> Dict[str, Any]:
        """Начинает аренду игры"""
        if not self.pc_key:
            raise ValueError("Ключ ПК не установлен")
        
        data = {
            "pcKey": self.pc_key,
            "gameId": game_id,
            "durationHours": duration_hours
        }
        
        return self._make_request('POST', '/club/rental/start', data=data)
    
    def get_2fa_code(self, session_id: Optional[int] = None) -> Dict[str, Any]:
        """Получает код двухфакторной авторизации"""
        if not self.pc_key:
            raise ValueError("Ключ ПК не установлен")
        
        data = {
            "pcKey": self.pc_key
        }
        
        if session_id:
            data["sessionId"] = session_id
        
        return self._make_request('POST', '/club/rental/2fa', data=data)
    
    def get_active_rental(self) -> Dict[str, Any]:
        """Получает активную аренду"""
        if not self.pc_key:
            raise ValueError("Ключ ПК не установлен")
        
        params = {
            "pcKey": self.pc_key
        }
        
        return self._make_request('GET', '/club/rental/active', params=params)
    
    def end_rental(self, session_id: Optional[int] = None) -> Dict[str, Any]:
        """Завершает аренду"""
        if not self.pc_key:
            raise ValueError("Ключ ПК не установлен")
        
        data = {
            "pcKey": self.pc_key
        }
        
        if session_id:
            data["sessionId"] = session_id
        
        return self._make_request('POST', '/club/rental/end', data=data)

