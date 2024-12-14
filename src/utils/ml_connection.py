import httpx
from src.core import settings


async def StartAnalize(event_id: int, video_path: str):
    try:
        url = settings.ml_connection_url + "upload/"
        async with httpx.AsyncClient() as client:
            # Открываем файл в асинхронном режиме
            with open(video_path, "rb") as file:
                # Параметры запроса
                data = {'event_id': event_id}
                files = {'file': (video_path.split("/")[-1], file, "video/mp4")}
                
                # Отправляем POST-запрос
                response = await client.post(url, data=data, files=files)
                
                # Проверяем успешность запроса
                response.raise_for_status()
                
                # Возвращаем JSON-ответ
                return response.json()
    except httpx.RequestError as e:
        print(f"Ошибка при отправке запроса: {e}")
        return {"error": str(e)}
    except FileNotFoundError:
        print(f"Файл не найден: {video_path}")
        return {"error": f"File not found: {video_path}"}
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return {"error": f"Ошибка: {str(e)}"}


