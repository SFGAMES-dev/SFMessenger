import asyncio
import json
import os
import websockets

# Словарь для хранения всех подключенных клиентов
clients = {}

async def register(websocket):
    """Регистрирует нового клиента и назначает ему уникальный ID."""
    client_id = str(websocket.remote_address[1])  # Используем порт как ID
    clients[client_id] = websocket
    print(f"Новый клиент подключился: {client_id}")
    await websocket.send(json.dumps({"type": "id", "userId": client_id}))
    return client_id

async def unregister(websocket, client_id):
    """Удаляет клиента при отключении."""
    if client_id in clients:
        del clients[client_id]
        print(f"Клиент отключился: {client_id}")
        # Оповещаем остальных клиентов
        message = json.dumps({"type": "user-disconnected", "userId": client_id})
        await asyncio.gather(*[client.send(message) for client in clients.values()])

async def handler(websocket):
    """Обрабатывает все сообщения от клиента."""
    client_id = await register(websocket)
    try:
        async for message_str in websocket:
            try:
                message = json.loads(message_str)
                message_type = message.get("type")

                if message_type == "signal":
                    target_id = message.get("target")
                    payload = message.get("payload")
                    if target_id in clients:
                        print(f"Пересылка сигнала от {client_id} к {target_id}")
                        await clients[target_id].send(json.dumps({
                            "type": "signal",
                            "source": client_id,
                            "payload": payload
                        }))
                    else:
                        print(f"Целевой клиент {target_id} не найден.")
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Целевой пользователь не в сети."
                        }))
                elif message_type == "text-message":
                    # Пересылка текстового сообщения всем, кроме отправителя
                    message_payload = json.dumps({
                        "type": "text-message",
                        "userId": client_id,
                        "text": message.get("text")
                    })
                    await asyncio.gather(*[
                        client.send(message_payload) 
                        for client_id, client in clients.items() 
                        if client is not websocket
                    ])
            except json.JSONDecodeError:
                print(f"Получено некорректное JSON-сообщение от {client_id}")
    finally:
        await unregister(websocket, client_id)

async def main():
    """Основная функция для запуска сервера."""
    # Получаем порт из переменной окружения или используем 8000 по умолчанию
    port_str = os.environ.get("PORT")
    if port_str and port_str.isdigit():
        port = int(port_str)
    else:
        port = 8000
    
    # Создаем и запускаем WebSocket-сервер
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"Сервер запущен и слушает на порту {port}")
        await asyncio.Future()  # Бесконечно ждем, пока сервер не будет остановлен

if __name__ == "__main__":
    asyncio.run(main())
