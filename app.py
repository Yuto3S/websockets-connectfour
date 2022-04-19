#!/usr/bin/env python

import asyncio
import json

import websockets
from connect4 import PLAYER1, PLAYER2, Connect4


async def handler(websocket):
    """Add the game logic"""
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

    """ Transmit from server to browser

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
    # await websocket.send(json.dumps(event)) """

    # async for message in websocket:
    #     print(message)


async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
