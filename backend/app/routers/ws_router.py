from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from app.services.redis_manager import redis_manager
from app.schemas.response import SystemMessage
import asyncio
from app.services.ws_manager import ws_manager
import json

router = APIRouter()


@router.websocket("/task/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    print(f"WebSocket 尝试连接 task_id: {task_id}")

    try:
        redis_async_client = await redis_manager.get_client()
        
        # 检查任务是否存在，如果不存在则创建一个临时任务标识
        task_exists = await redis_async_client.exists(f"task_id:{task_id}")
        if not task_exists:
            print(f"Task not found, creating temporary task entry: {task_id}")
            # 创建临时任务标识，过期时间1小时
            await redis_async_client.setex(f"task_id:{task_id}", 3600, "temporary")
        
        print(f"WebSocket connected for task: {task_id}")

        # 建立 WebSocket 连接
        await ws_manager.connect(websocket)
        print(f"WebSocket connection status: {websocket.client}")

        # 订阅 Redis 频道
        pubsub = await redis_manager.subscribe_to_task(task_id)
        print(f"Subscribed to Redis channel: task:{task_id}:messages")

        # 发送连接成功消息
        await redis_manager.publish_message(
            task_id,
            SystemMessage(content="WebSocket连接已建立，等待任务开始..."),
        )

        try:
            while True:
                try:
                    msg = await pubsub.get_message(ignore_subscribe_messages=True)
                    if msg:
                        print(f"Received message: {msg}")
                        try:
                            msg_dict = json.loads(msg["data"])
                            await ws_manager.send_personal_message_json(msg_dict, websocket)
                            print(f"Sent message to WebSocket: {msg_dict}")
                        except Exception as e:
                            print(f"Error parsing message: {e}")
                            await ws_manager.send_personal_message_json(
                                {"error": str(e)}, websocket
                            )
                    await asyncio.sleep(0.1)

                except WebSocketDisconnect:
                    print("WebSocket disconnected")
                    break
                except Exception as e:
                    print(f"Error in websocket loop: {e}")
                    await asyncio.sleep(1)
                    continue

        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            try:
                await pubsub.unsubscribe(f"task:{task_id}:messages")
                print(f"Unsubscribed from Redis channel: task:{task_id}:messages")
            except Exception as e:
                print(f"Error unsubscribing: {e}")
            
            ws_manager.disconnect(websocket)
            print(f"WebSocket connection closed for task: {task_id}")
            
    except Exception as e:
        print(f"Critical WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")
        except:
            pass
