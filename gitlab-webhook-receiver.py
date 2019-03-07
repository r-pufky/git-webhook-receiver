#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# Config File Format:
#
# {GIT REPO URL}:
#   command: String command to execute.
#   token: String webhook repository token.
#   background: {True|False} to run command in the background.

import json
import yaml
from subprocess import Popen, PIPE, STDOUT
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
import sys
import logging

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level=logging.DEBUG,
                    stream=sys.stdout)

HEADER_CONTENT_LENGTH = 'Content-Length'
HEADER_TOKEN = 'X-Gitlab-Token'
CONFIG_COMMAND = 'command'
CONFIG_TOKEN = 'gitlab_token'
CONFIG_BACKGROUND = 'background'
JSON_PROJECT = 'project'
JSON_PROJECT_NAME = 'name'

class ReceiverHeader(object):
  """ Encapsulate processed received headers. """

  def __init__(self):
    """ Initialize recieved headers. """
    self.token = None
    self.payload = None
    self.project = None
    self.params = {}


class RequestHandler(BaseHTTPRequestHandler):
  """A POST request handler."""

  def ParseHeaders(self):
    """ Parse JSON headers.

    Returns:

    """
    headers = ReceiverHeader()
    headers.token = self.headers[HEADER_TOKEN]
    headers.payload = self.rfile.read(int(self.headers[HEADER_CONTENT_LENGTH]))

    if len(headers.payload) > 0:
      headers.params = json.loads(headers.payload.decode('utf-8'))

    try:
      headers.project = headers.params[JSON_PROJECT][JSON_PROJECT_NAME]
    except KeyError as err:
      logging.error('No project provided by the JSON payload.')
      raise

    return headers

  # Attributes (only if a config YAML is used)
  # command, gitlab_token, foreground
  def get_info_from_config(self, project, config):
    # get command and token from config file
    self.command = config[project][CONFIG_COMMAND]
    self.gitlab_token = config[project][CONFIG_TOKEN]
    self.foreground = CONFIG_BACKGROUND in config[project] and not config[project][CONFIG_BACKGROUND]
    logging.info('Load project %s and run command %s.', project, self.command)

  def do_token_mgmt(self, request_token, json_payload):
    # Check if the gitlab token is valid
    if request_token == self.gitlab_token:
      logging.info('Start executing %s' % self.command)
      try:
        # run command in background
        p = Popen(self.command, stdin=PIPE)
        p.stdin.write(json_payload);
        if self.foreground:
          p.communicate()
        self.send_response(200, 'OK')
      except OSError as err:
        self.send_response(500, 'OSError')
        logging.error('Command could not run successfully.')
        logging.error(err)
    else:
      logging.error('Not authorized, Token not authorized.')
      self.send_response(401, 'Token not authorized.')

  def do_POST(self):
    logging.info('Hook received.')
    try:
      headers = self.ParseHeaders()
    except KeyError as err:
      self.send_response(500, 'KeyError')
      self.end_headers()
      return

    try:
      self.get_info_from_config(headers.project, config)
      self.do_token_mgmt(headers.token, headers.payload)
    except KeyError as err:
      self.send_response(500, 'KeyError')
      if err == headers.project:
        logging.error('Project %s not found in %s.', headers.project, args.cfg.name)
      elif err == CONFIG_COMMAND:
        logging.error('Key %s not found in %s.', CONFIG_COMMAND, args.cfg.name)
      elif err == CONFIG_TOKEN:
        logging.error('Key %s not found in %s.', CONFIG_TOKEN, args.cfg.name)
    finally:
      self.end_headers()


def get_parser():
  """Get a command line parser."""
  parser = ArgumentParser(description=__doc__,
                          formatter_class=ArgumentDefaultsHelpFormatter)

  parser.add_argument('--addr',
                      dest='addr',
                      default='0.0.0.0',
                      help='Address to listen on.')
  parser.add_argument('--port',
                      dest='port',
                      type=int,
                      default=8666,
                      metavar='PORT',
                      help='Port to listen on.')
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument('--cfg',
                     dest='cfg',
                     type=FileType('r'),
                     help='Path to the config file.')
  return parser


def main(addr, port):
  """Start a HTTPServer which waits for requests."""
  httpd = HTTPServer((addr, port), RequestHandler)
  httpd.serve_forever()


if __name__ == '__main__':
  parser = get_parser()
  args = parser.parse_args()

  if args.cfg:
    config = yaml.load(args.cfg)

  main(args.addr, args.port)
