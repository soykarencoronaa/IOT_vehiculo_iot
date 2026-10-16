
# app/websocket/websocket_manager.py

import asyncio
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self.conexiones: list[WebSocket] = []
        self.bloqueo = asyncio.Lock()

    async def conectar(self, websocket: WebSocket):
        await websocket.accept()

        async with self.bloqueo:
            self.conexiones.append(websocket)

    async def desconectar(self, websocket: WebSocket):
        async with self.bloqueo:
            if websocket in self.conexiones:
                self.conexiones.remove(websocket)

    async def enviar_a_todos(self, mensaje: dict):
        async with self.bloqueo:
            conexiones = list(self.conexiones)

        desconectados = []

        for websocket in conexiones:
            try:
                await websocket.send_json(mensaje)
            except Exception:
                desconectados.append(websocket)

        for websocket in desconectados:
            await self.desconectar(websocket)


manager = WebSocketManager()
