# 文件: app.py
import os
from aiohttp import web
import logging

# 配置日志，方便在 fly logs 中查看信息
logging.basicConfig(level=logging.INFO)

# 这是用于健康检查的函数
async def health_check(request):
    return web.Response(text="OK\n")

# 这是处理 WebSocket 连接的函数 (已升级)
async def websocket_handler(request):
    # 创建一个 WebSocket 响应对象
    ws = web.WebSocketResponse()
    # "准备" 握手并建立连接
    await ws.prepare(request)

    # 当有新连接时，将其添加到共享集合中
    request.app['websockets'].add(ws)
    logging.info(f"新客户端连接，当前总数: {len(request.app['websockets'])}")

    try:
        # 循环等待并处理来自客户端的消息
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                logging.info(f"收到来自 {id(ws)} 的消息: {msg.data}，准备广播给其他人")
                # 收到消息后，遍历集合，将消息广播给除发送者外的所有其他客户端
                for client_ws in request.app['websockets']:
                    # (核心修改) 增加一个判断，确保不会把消息发回给发送者自己
                    if client_ws != ws and not client_ws.closed:
                        await client_ws.send_str(msg.data)
            elif msg.type == web.WSMsgType.ERROR:
                logging.error(f"WebSocket 连接出现异常 {ws.exception()}")

    finally:
        # 当连接断开时，无论正常或异常，都从集合中移除
        request.app['websockets'].remove(ws)
        logging.info(f"客户端 {id(ws)} 断开，当前总数: {len(request.app['websockets'])}")

    return ws

async def start_web_app():
    # 创建 aiohttp 应用实例
    app = web.Application()
    
    # 在应用启动时，创建一个集合(set)来存储所有激活的WebSocket连接
    app['websockets'] = set()

    # 添加路由
    app.add_routes([
        web.get('/healthz', health_check),
        web.get('/ws', websocket_handler),
    ])
    return app

# 当这个文件作为主程序运行时，启动服务器
if __name__ == "__main__":
    app = start_web_app()
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)