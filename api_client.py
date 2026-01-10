"""
Клиент для работы с API бэкенда
"""
import requests
from typing import Optional, Dict, List, Any

class ActiveRentalError(Exception):
    """Исключение для случая, когда у ПК уже есть активная аренда"""
    pass

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
        except requests.exceptions.HTTPError as e:
            # Пытаемся получить детали ошибки из ответа
            error_details = None
            error_msg = None
            status_code = None
            
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                try:
                    error_data = e.response.json()
                    error_details = error_data
                    if isinstance(error_data, dict):
                        error_msg = error_data.get('message') or error_data.get('error') or str(e)
                        print(f"Ошибка API ({status_code}): {error_msg}")
                        print(f"Полный ответ сервера: {error_data}")
                        # Пробрасываем исключение с полным сообщением
                        raise Exception(f"{status_code} {error_msg}")
                except (ValueError, AttributeError):
                    # Если не JSON, выводим текст ответа
                    error_text = e.response.text[:1000] if hasattr(e.response, 'text') else str(e)
                    error_msg = error_text
                    print(f"Ошибка API ({status_code}): {error_text}")
                    raise Exception(f"{status_code} Server Error: {error_text}")
            
            # Если не удалось получить детали
            raise Exception(f"{status_code or 'Unknown'} HTTP Error: {str(e)}")
            
            print(f"Ошибка API запроса: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Статус: {e.response.status_code}")
                print(f"Ответ: {e.response.text[:500]}")
            raise
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
    
    def start_rental(self, game_id: int, duration_hours: int = 1, auto_end_active: bool = True) -> Dict[str, Any]:
        """Начинает аренду игры
        
        Args:
            game_id: ID игры
            duration_hours: Длительность аренды в часах
            auto_end_active: Автоматически завершать активную аренду при ошибке (по умолчанию True)
        """
        if not self.pc_key:
            raise ValueError("Ключ ПК не установлен")
        
        data = {
            "pcKey": self.pc_key,
            "gameId": game_id,
            "durationHours": duration_hours
        }
        
        try:
            return self._make_request('POST', '/club/rental/start', data=data)
        except Exception as e:
            error_msg = str(e).lower()
            
            # Проверяем, это ли ошибка об активной аренде (400 Bad Request)
            # Сообщение: "У этого ПК уже есть активная аренда. Завершите текущую сессию перед началом новой."
            is_active_rental_error = (
                ("400" in str(e) or "bad request" in error_msg) and
                ("активная аренда" in error_msg or 
                 "active rental" in error_msg or
                 "уже есть активная" in error_msg or
                 "завершите текущую" in error_msg or
                 "already has active" in error_msg)
            )
            
            if is_active_rental_error:
                if auto_end_active:
                    # Пробрасываем специальное исключение для обработки
                    raise ActiveRentalError("У этого ПК уже есть активная аренда")
                else:
                    raise e
            else:
                raise e
    
    def get_2fa_code(self, session_id: Optional[int] = None) -> Dict[str, Any]:
        """Получает код двухфакторной авторизации
        
        Args:
            session_id: ID сессии аренды (опционально, если не указан - бэкенд найдет активную сессию сам)
        """
        if not self.pc_key:
            raise ValueError("Ключ ПК не установлен")
        
        data = {
            "pcKey": self.pc_key
        }
        
        # Бэкенд ожидает sessionId (не rentalId!)
        # Если sessionId не указан, бэкенд сам найдет активную сессию для этого ключа
        if session_id is not None:
            # Убеждаемся, что session_id является числом (int)
            try:
                session_id_int = int(session_id) if session_id else None
                if session_id_int is not None:
                    data["sessionId"] = session_id_int
            except (ValueError, TypeError):
                # Если не удалось преобразовать в число, не передаем sessionId
                # Бэкенд сам найдет активную сессию
                pass
        
        # Логируем данные запроса для отладки
        print(f"Запрос 2FA на {self.base_url}/api/club/rental/2fa с данными: {data}")
        
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

