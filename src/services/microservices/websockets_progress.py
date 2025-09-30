from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import asyncio
import json

from src.services.core_services import CoreServices

class WebSocketManager:
    """Administrador de conexiones WebSocket por identificador de libro.
    Mantiene conjuntos de conexiones activas por book_id y provee métodos para:
    - aceptar y registrar conexiones (connect),
    - eliminar conexiones (disconnect),
    - enviar datos de progreso en formato JSON a todas las conexiones de un libro y limpiar las desconectadas (broadcast_progress).
    Atributos:
        active_connections (Dict[int, Set[WebSocket]]): conexiones activas agrupadas por book_id.
    """
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, book_id: int):
        await websocket.accept()
        if book_id not in self.active_connections:
            self.active_connections[book_id] = set()
        self.active_connections[book_id].add(websocket)

    def disconnect(self, websocket: WebSocket, book_id: int):
        if book_id in self.active_connections:
            self.active_connections[book_id].discard(websocket)
            if not self.active_connections[book_id]:
                del self.active_connections[book_id]

    async def broadcast_progress(self, book_id: int, progress_data: dict):
        if book_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[book_id]:
                try:
                    await connection.send_json(progress_data)
                except:
                    disconnected.add(connection)
            
            for conn in disconnected:
                self.disconnect(conn, book_id)

ws_manager = WebSocketManager()

class GeminiWebSocketRouter:
    def __init__(self, services: CoreServices) -> None:
        self.services = services

    async def websocket_endpoint(self, websocket: WebSocket, book_id: int):
        await ws_manager.connect(websocket, book_id)
        try:
            while True:
                await websocket.receive_text()
                await asyncio.sleep(0.1)
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket, book_id)