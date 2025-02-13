import asyncio
import json
import sys
import uuid
import os
import datetime
import pathlib
import websockets

# 信令消息类型定义
SEND_TYPE_REG = '1001'            # 注册后发送用户id及房间信息
SEND_TYPE_ROOM_INFO = '1002'       # 发送房间信息
SEND_TYPE_JOINED_ROOM = '1003'     # 新加入房间通知
SEND_TYPE_NEW_CANDIDATE = '1004'   # offer
SEND_TYPE_NEW_CONNECTION = '1005'  # new connection
SEND_TYPE_CONNECTED = '1006'       # 连接确认
SEND_TYPE_NICKNAME_UPDATED = '1007' # 昵称更新通知

RECEIVE_TYPE_NEW_CANDIDATE = '9001'
RECEIVE_TYPE_NEW_CONNECTION = '9002'
RECEIVE_TYPE_CONNECTED = '9003'
RECEIVE_TYPE_KEEPALIVE = '9999'
RECEIVE_TYPE_UPDATE_NICKNAME = '9004'

# 加载房间密码配置（room_pwd.json 需放在服务器运行目录下）
ROOM_PWD_FILE = 'room_pwd.json'
room_pwd = {}
if os.path.exists(ROOM_PWD_FILE):
    try:
        with open(ROOM_PWD_FILE, 'r', encoding='utf-8') as f:
            room_pwd_config = json.load(f)
        # room_pwd: { roomId: {"pwd": <pwd>, "turns": <turns>} }
        for item in room_pwd_config:
            room_pwd[item["roomId"]] = {"pwd": item["pwd"], "turns": item.get("turns")}
        room_ids = list(room_pwd.keys())
        print(f"加载房间数据: {', '.join(room_ids)}")
    except Exception as e:
        print(f"加载 {ROOM_PWD_FILE} 失败: {e}")
else:
    print(f"{ROOM_PWD_FILE} 不存在，未加载房间数据")

# 全局用户存储，键为用户ID，值为包含 ip、roomId 及 websocket 的字典
users = {}

def log(*args):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{now}]", *args)

async def send(socket, type_, data):
    msg = json.dumps({"type": type_, "data": data})
    await socket.send(msg)

def parse_path(path):
    # path 格式： /roomId/pwd 或其他
    segments = path.strip('/').split('/')
    roomId = None
    pwd = None
    if len(segments) >= 1 and segments[0] and len(segments[0]) <= 32:
        roomId = segments[0].strip()
    if len(segments) >= 2 and segments[1] and len(segments[1]) <= 32:
        pwd = segments[1].strip()
    # 兼容旧版本：若 roomId 为 'ws' 则置空
    if roomId == 'ws':
        roomId = None
    if roomId == '':
        roomId = None
    return roomId, pwd

def validate_room(roomId, pwd):
    if roomId and roomId in room_pwd:
        if not pwd or room_pwd[roomId]["pwd"].lower() != pwd.lower():
            return None, None
        return roomId, room_pwd[roomId].get("turns")
    return None, None

def register_user(ip, roomId, socket):
    # 简单生成一个唯一用户ID
    user_id = str(uuid.uuid4())[:8]
    users[user_id] = {"ip": ip, "roomId": roomId, "socket": socket, "nickname": user_id}
    return user_id

def unregister_user(user_id):
    if user_id in users:
        del users[user_id]

def get_user_list(ip, roomId):
    # 返回同一ip和roomId下的所有用户（或全部用户）
    user_list = []
    for uid, info in users.items():
        # 如果 roomId 不为空，则仅返回相同房间下的用户
        if roomId:
            if info["roomId"] == roomId:
                user_list.append({"id": uid, "nickname": info.get("nickname", uid), "socket": info["socket"]})
        else:
            user_list.append({"id": uid, "nickname": info.get("nickname", uid), "socket": info["socket"]})
    return user_list

async def handler(websocket, path):
    # 获取客户端请求 IP
    headers = websocket.request_headers
    ip = headers.get('x-forwarded-for') or headers.get('x-real-ip') or websocket.remote_address[0]

    roomId, pwd = parse_path(path)
    turns = None
    if roomId:
        roomId, turns = validate_room(roomId, pwd)
        if not roomId:
            log(f"{ip} 尝试连接房间【{path}】，但验证失败，视为公有房间")
    current_id = register_user(ip, roomId, websocket)
    log(f"{current_id}@{ip}{'/' + roomId if roomId else ''} connected")

    # 向客户端发送注册信息
    await send(websocket, SEND_TYPE_REG, {"id": current_id, "roomId": roomId, "turns": turns})
    # 向当前连接发送房间内其他用户信息
    user_list = get_user_list(ip, roomId)
    await send(websocket, SEND_TYPE_ROOM_INFO, [{"id": u["id"], "nickname": u["nickname"]} for u in user_list])
    # 给当前用户发送加入房间通知
    await send(websocket, SEND_TYPE_JOINED_ROOM, {"id": current_id})

    try:
        async for msg in websocket:
            try:
                message = json.loads(msg)
            except Exception as e:
                log("无效JSON", msg)
                continue

            uid = message.get("uid")
            targetId = message.get("targetId")
            type_ = message.get("type")
            data = message.get("data")

            if not type_ or not uid or not targetId:
                continue

            # 互找发送者和接收者信息
            sender = users.get(uid)
            target = users.get(targetId)
            if not sender or not target:
                continue

            if type_ == RECEIVE_TYPE_NEW_CANDIDATE:
                # 转发 candidate
                await send(target["socket"], SEND_TYPE_NEW_CANDIDATE, {"targetId": uid, "candidate": data.get("candidate")})
                continue

            if type_ == RECEIVE_TYPE_NEW_CONNECTION:
                await send(target["socket"], SEND_TYPE_NEW_CONNECTION, {"targetId": uid, "offer": data.get("targetAddr")})
                continue

            if type_ == RECEIVE_TYPE_CONNECTED:
                await send(target["socket"], SEND_TYPE_CONNECTED, {"targetId": uid, "answer": data.get("targetAddr")})
                continue

            if type_ == RECEIVE_TYPE_KEEPALIVE:
                # 心跳，无需处理
                continue

            if type_ == RECEIVE_TYPE_UPDATE_NICKNAME:
                # 更新昵称（简单实现：直接覆盖）
                new_name = data.get("nickname")
                if new_name:
                    sender["nickname"] = new_name
                    # 可向房间内所有用户转发昵称更新通知
                    for u in get_user_list(ip, roomId):
                        await send(u["socket"], SEND_TYPE_NICKNAME_UPDATED, {"id": uid, "nickname": new_name})
                continue

            # 其他类型可按需添加

        # end async for

    except websockets.exceptions.ConnectionClosedError:
        log("客户端已断开", current_id)
    except Exception as e:
        log("发生错误", e)
    finally:
        unregister_user(current_id)
        # 向房间内其他用户更新房间信息
        for u in get_user_list(ip, roomId):
            await send(u["socket"], SEND_TYPE_ROOM_INFO, [{"id": user["id"], "nickname": user["nickname"]} for user in get_user_list(ip, roomId)])
        log(f"用户 {current_id} 已断开连接")

async def main():
    # 启动时可通过命令行传入端口，默认使用 8081
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    async with websockets.serve(handler, "localhost", PORT):
        log(f"信令服务器已启动: ws://localhost:{PORT}")
        await asyncio.Future()  # 持续运行

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("服务器已关闭")