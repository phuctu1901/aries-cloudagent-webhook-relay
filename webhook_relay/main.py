#!/usr/bin/env python3

import argparse
import asyncio
import aiohttp
from aiohttp import web
import json
import logging
from uuid import uuid4

from .lib import *

app = web.Application()
app.msg_queue = ClearableQueue()
routes = web.RouteTableDef()

def setup_cli_args():
  parser = argparse.ArgumentParser(
      prog='webhook-receiver',
      description="collects and cache's aca-py webhook calls until requested by controller."
  )
  
  parser.add_argument(
      '-l', '--log',
      action='store',
      choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
      default='INFO',
      help='the log level'
  )

  parser.add_argument(
      '--api-key',
      action='store',
      help='if passed, this will be used as the API key (one will be generated by default).'
  )

  parser.add_argument(
      '--host',
      '-H',
      action='store',
      default='0.0.0.0',
      help='the host the receiver will run on'
  )
  parser.add_argument(
      '--port',
      '-p',
      action='store',
      default=8080,
      help='the port the receiver will run on'
  )
  return parser.parse_args()



async def on_ws_connection(request):
  ws = web.WebSocketResponse()
  await ws.prepare(request)

  # this is a workaround since client side ws api's
  # to not all provide decent header interfaces.
  client_headers = json.loads(await ws.receive_json())

  auth = client_headers.get('auth', None)
  if auth is None:
      logging.warning('denied connection attempt because no authorization key was provided')
      await ws.close(code=aiohttp.WSCloseCode.PROTOCOL_ERROR)
      return

  # if fastForward not provided, default to False
  fast_forward = False if client_headers.get('fastForward', None) is None else client_headers['fastForward']

  if auth != args.api_key:
    logging.warning(f'denied connection attempt with invalid api key {auth}')
    await ws.close(code=aiohttp.WSCloseCode.PROTOCOL_ERROR)
    return

  if not fast_forward:
    await app.msg_queue.clear()

  while not ws.closed:
    msg = await request.app.msg_queue.get()
    ws.receive_json
    await ws.send_str(msg.to_json())

  return ws

@routes.post('/topic/connections/')
async def connections_handler(request):
  logging.debug('received connection event')
  msg = Message(Topic.CONNECTIONS, await request.json())
  await request.app.msg_queue.put(msg)
  return web.Response(status=200)

@routes.post('/topic/basicmessages/')
async def basicmessages_handler(request):
  logging.debug('received basic-message event')
  msg = Message(Topic.BASICMESSAGES, await request.json())
  await request.app.msg_queue.put(msg)
  return web.Response(status=200)

@routes.post('/topic/issue_credential/')
async def issue_credential_handler(request):
  logging.debug('received issue-credential event')
  msg = Message(Topic.ISSUE_CREDENTIAL, await request.json())
  await request.app.msg_queue.put(msg)
  return web.Response(status=200)

@routes.post('/topic/present_proof/')
async def present_proofs_handler(request):
  logging.debug('received present-proof event')
  msg = Message(Topic.PRESENT_PROOF, await request.json())
  await request.app.msg_queue.put(msg)
  return web.Response(status=200)


def main():
  args = setup_cli_args()
  logging.basicConfig(level=args.log, format='%(levelname)s - %(message)s')
  logging.info(f'log level: {args.log}')

  app.add_routes(routes)  # add routes

  if args.api_key is None:
      args.api_key = str(uuid4())
      logging.info('--api-key flag not provided')
      logging.info(f'generated api key: {args.api_key}')
  else:
    logging.info(f'using api key: {args.api_key}')

  logging.info(f'ws exposed at: ws://{args.host}:{args.port}/ws')

  app.add_routes([web.get('/ws', on_ws_connection)])  # add websocket route

  web.run_app(app, host=args.host, port=args.port)