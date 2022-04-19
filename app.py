#!/usr/bin/env python

import asyncio
import json
import secrets

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


""" PART 1
async def handler(websocket):
    ### Add the game logic
    game = Connect4()
    player = PLAYER1
    async for message in websocket:
        message = json.loads(message)

        if message["type"] != "play":
            event = {
                "type": "error",
                "message": "Client should only send 'play' events",
            }
        else:
            try:
                column = message["column"]
                row = game.play(player, column)
                player = PLAYER2 if (player == PLAYER1) else PLAYER1
                event = {
                    "type": "play",
                    "player": player,
                    "column": column,
                    "row": row,
                }
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
            await websocket.send(json.dumps(event))

    ### Transmit from server to browser

    # for player, column, row in [
    #     (PLAYER1, 3, 0),
    #     (PLAYER2, 3, 1),
    #     (PLAYER1, 4, 0),
    #     (PLAYER2, 4, 1),
    #     (PLAYER1, 2, 0),
    #     (PLAYER2, 1, 0),
    #     (PLAYER1, 5, 0),
    # ]:
    #     event = {
    #         "type": "play",
    #         "player": player,
    #         "column": column,
    #         "row": row,
    #     }
    #     await websocket.send(json.dumps(event))
    #     await asyncio.sleep(0.5)
    #
    # event = {
    #     "type": "win",
    #     "player": PLAYER1,
    # }
    # await websocket.send(json.dumps(event))

    # async for message in websocket:
    #     print(message)
"""


async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
