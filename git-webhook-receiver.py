#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# Config File Format:
#
# {GIT REPO URL}:
#   command: String command to execute.
#   secret: String webhook repository token.
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


class ReceiverHeader(object):
  """ Encapsulate processed received headers.

  Attributes:
    CONTENT_LENGTH: String header for content length.
    TOKEN: String header for token.
    PROJECT: String key for project in JSON headers.
    PROJECT_NAME: String key for project name in JSON headers.
    token: String request token.
    payload: Filehandle like object containing all JSON header content.
    project: String project name for update.
    params: Dictionary of parsed JSON header content.
  """
  CONTENT_LENGTH = 'Content-Length'
  TOKEN = 'secret'
  PROJECT = 'repository'
  PROJECT_NAME = 'html_url'

  def __init__(self):
    """ Initialize recieved headers. """
    self.token = None
    self.payload = None
    self.project = None
    self.params = {}


class ProjectConfig(object):
  """ Composed config object.

  Attributes:
    COMMAND: String key for command in config.
    TOKEN: String key for token in config.
    BACKGROUND: String key for background in config.
    command: String command to execute.
    token: String authorized token.
    foreground: Boolean True if command should be executed in the foreground.
  """
  COMMAND = 'command'
  TOKEN = 'secret'
  BACKGROUND = 'background'

  def __init__(self):
    """ Initialize config. """
    self.command = None
    self.token = None
    self.foreground = False


class RequestHandler(BaseHTTPRequestHandler):
  """A POST request handler."""

  def ParseHeaders(self):
    """ Parse JSON headers.

    Returns:
      ReceiverHeader object containing parsed headers.

    Raises:
      KeyError: if project name cannot be parsed from received headers.
    """
    headers = ReceiverHeader()
    headers.payload = self.rfile.read(int(self.headers[headers.CONTENT_LENGTH]))

    if len(headers.payload) > 0:
      headers.params = json.loads(headers.payload.decode('utf-8'))

    # gitea has token in payload, not headers.
    try:
      headers.token = headers.params[headers.TOKEN]
    except KeyError as err:
      try:
        headers.token = self.headers[headers.TOKEN]
      except KeyError as err:
        logging.error('Token not found.')
        raise

    try:
      headers.project = headers.params[headers.PROJECT][headers.PROJECT_NAME]
    except KeyError as err:
      logging.error('No project provided by the JSON payload.')
      raise

    return headers

  def ParseConfig(self, project):
    """ Parse config file for specific project.

    Args:
      project: String requested project.

    Returns:
      ProjectConfig object containing parsed configuration data for project.

    Raises:
      KeyError: If the requested key is not found in the config file.
    """
    pconfig = ProjectConfig()
    try:
      pconfig.command = config[project][pconfig.COMMAND]
      pconfig.token = config[project][pconfig.TOKEN]
      pconfig.foreground = (pconfig.BACKGROUND in config[project] and
                            not config[project][pconfig.BACKGROUND])
    except KeyError as err:
      if err == project:
        logging.error('Project %s not found in %s.', project, args.cfg.name)
      elif err == pconfig.COMMAND:
        logging.error('Key %s not found in %s.', pconfig.COMMAND, args.cfg.name)
      elif err == pconfig.TOKEN:
        logging.error('Key %s not found in %s.', pconfig.TOKEN, args.cfg.name)

    logging.info('Loaded project %s and run command %s.',
                 project,
                 pconfig.command)
    return pconfig

  def ProcessRequest(self, headers):
    """ Process request and execute command. """
    pconfig = self.ParseConfig(headers.project)

    if headers.token == pconfig.token:
      logging.info('Start executing %s' % pconfig.command)
      try:
        p = Popen(pconfig.command, stdin=PIPE)
        if pconfig.foreground:
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
      self.ProcessRequest(headers)
    except KeyError as err:
      self.send_response(500, 'KeyError')
    finally:
      self.end_headers()


def Parser():
  """Generate CLI Arguments."""
  parser = ArgumentParser(description=__doc__,
                          formatter_class=ArgumentDefaultsHelpFormatter)

  parser.add_argument('-a', '--address',
                      dest='addr',
                      default='0.0.0.0',
                      help='Address to listen on.')
  parser.add_argument('-p', '--port',
                      dest='port',
                      type=int,
                      default=8666,
                      metavar='PORT',
                      help='Port to listen on.')
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument('-c', '--config',
                     dest='cfg',
                     type=FileType('r'),
                     help='Path to the config file.')
  return parser


def main(addr, port):
  """Start a HTTPServer which waits for requests."""
  httpd = HTTPServer((addr, port), RequestHandler)
  httpd.serve_forever()


if __name__ == '__main__':
  args = Parser().parse_args()

  if args.cfg:
    config = yaml.load(args.cfg)

  main(args.addr, args.port)
