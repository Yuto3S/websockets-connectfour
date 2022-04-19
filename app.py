#!/usr/bin/env python

import asyncio
import json
import secrets
import os
import signal

import websockets
from connect4 import PLAYER1, PLAYER2, Connect4

JOIN = {}
WATCH = {}


async def error(websocket, message):
    event = {
        "type": "error",
        "message": message,
    }
    await websocket.send(json.dumps(event))


async def start(websocket):
    game = Connect4()
    connected = {websocket}

    join_key = secrets.token_urlsafe(12)
    JOIN[join_key] = game, connected

    watch_key = secrets.token_urlsafe(12)
    WATCH[watch_key] = game, connected

    try:
        event = {
            "type": "init",
            "join": join_key,
            "watch": watch_key,
        }
        await websocket.send(json.dumps(event))

        print(f"First player started game {id(game)}.")
        await play(websocket, game, PLAYER1, connected)
    finally:
        del JOIN[join_key]
        del WATCH[watch_key]


async def join(websocket, join_key):
    try:
        game, connected = JOIN[join_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    connected.add(websocket)
    try:
        await replay(websocket, game)
        print(f"Second player joined the game {id(game)}.")
        await play(websocket, game, PLAYER2, connected)
    finally:
        connected.remove(websocket)


async def watch(websocket, watch_key):
    try:
        game, connected = WATCH[watch_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    connected.add(websocket)
    try:
        await replay(websocket, game)
        print(f"Spectactor joined the game {id(game)}.")
        await websocket.wait_closed()
    finally:
        connected.remove(websocket)


async def play(websocket, game, player, connected):
    async for message in websocket:
        message = json.loads(message)
        try:
            column = message["column"]
            row = game.play(player, column)
            event = {
                "type": "play",
                "player": player,
                "column": column,
                "row": row,
            }
            for connected_player in connected:
                await connected_player.send(json.dumps(event))
        except RuntimeError as e:
            event = {
                "type": "error",
                "message": f"Move is illegal: {e}",
            }
            await websocket.send(json.dumps(event))

        if game.winner:
            event = {
                "type": "win",
                "player": player,
            }
            websockets.broadcast(connected, json.dumps(event))


async def replay(websocket, game):
    for player, column, row in game.moves:
        event = {
            "type": "play",
            "player": player,
            "column": column,
            "row": row,
        }
        await websocket.send(json.dumps(event))


async def handler(websocket):
    message = await websocket.recv()
    event = json.loads(message)
    assert event["type"] == "init"

    if "join" in event:
        await join(websocket, event["join"])
    elif "watch" in event:
        await watch(websocket, event["watch"])
    else:
        await start(websocket)


async def main():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    port = int(os.environ.get("PORT", "8001"))
    async with websockets.serve(handler, "", port):
        await stop


if __name__ == "__main__":
    asyncio.run(main())
