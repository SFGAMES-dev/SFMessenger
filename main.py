import asyncio
import json
import websockets
import os
import signal

# Словарь для хранения всех подключенных клиентов по их уникальным ID
clients = {}

# Обработчик нового WebSocket-соединения
async def handler(websocket):
    # Каждому новому клиенту присваивается уникальный ID на основе его объекта
    user_id = str(id(websocket))
    clients[user_id] = websocket
    print(f"Новый клиент подключился: {user_id}")

    # Отправляем клиенту его уникальный ID
    await websocket.send(json.dumps({"type": "id", "userId": user_id}))

    try:
        # Слушаем сообщения от клиента
        async for message_str in websocket:
            try:
                message = json.loads(message_str)
                message_type = message.get("type")

                # Обрабатываем различные типы сообщений
                if message_type == "signal":
                    target_id = message.get("target")
                    payload = message.get("payload")
                    if target_id in clients:
                        print(f"Пересылаем сигнал от {user_id} к {target_id}")
                        await clients[target_id].send(json.dumps({
                            "type": "signal",
                            "source": user_id,
                            "payload": payload
                        }))
                    else:
                        print(f"Целевой клиент {target_id} не найден.")
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Целевой пользователь не в сети."
                        }))

            except json.JSONDecodeError:
                print(f"Получено некорректное JSON-сообщение: {message_str}")
    
    finally:
        # Удаляем клиента из словаря при отключении
        if user_id in clients:
            del clients[user_id]
        print(f"Клиент отключился: {user_id}")
        # Оповещаем остальных клиентов об отключении
        for client_id, client_ws in clients.items():
            await client_ws.send(json.dumps({
                "type": "user-disconnected",
                "userId": user_id
            }))

# Функция, которая будет запускать сервер
async def main():
    # Render предоставляет порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 8000))
    # Запускаем WebSocket-сервер на общедоступном адресе
    server = await websockets.serve(handler, "0.0.0.0", port)
    print(f"Сервер запущен и слушает на порту {port}")

    # Добавляем обработчик для graceful shutdown
    loop = asyncio.get_event_loop()
    stop = loop.create_future()
    # Регистрируем обработчик для сигналов SIGTERM и SIGINT (Ctrl+C)
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    
    # Ожидаем завершения
    await stop
    server.close()
    await server.wait_closed()
    print("Сервер остановлен.")

# Запуск основной функции
if __name__ == "__main__":
    asyncio.run(main())
