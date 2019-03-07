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
  """ Encapsulate processed received headers.

  Attributes:
    token: String request token.
    payload: Filehandle like object containing all JSON header content.
    project: String project name for update.
    params: Dictionary of parsed JSON header content.
  """

  def __init__(self):
    """ Initialize recieved headers. """
    self.token = None
    self.payload = None
    self.project = None
    self.params = {}


class ProjectConfig(object):
  """ Composed config object.

  Attributes:
    command: String command to execute.
    token: String authorized token.
    foreground: Boolean True if command should be executed in the foreground.
  """

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

  def ParseConfig(self, project):
    """ Parse config file for specific project.

    Args:
      project: String requested project.

    Returns:
      ProjectConfig object containing parsed configuration data for project.

    Raises:
      KeyError: If the requested key is not found in the config file.
    """
    project_config = ProjectConfig()
    try:
      project_config.command = config[project][CONFIG_COMMAND]
      project_config.token = config[project][CONFIG_TOKEN]
      project_config.foreground = (CONFIG_BACKGROUND in config[project] and
                                   not config[project][CONFIG_BACKGROUND])
    except KeyError as err:
      if err == project:
        logging.error('Project %s not found in %s.', project, args.cfg.name)
      elif err == CONFIG_COMMAND:
        logging.error('Key %s not found in %s.', CONFIG_COMMAND, args.cfg.name)
      elif err == CONFIG_TOKEN:
        logging.error('Key %s not found in %s.', CONFIG_TOKEN, args.cfg.name)

    logging.info('Loaded project %s and run command %s.',
                 project,
                 project_config.command)
    return project_config

  def ProcessRequest(self, headers):
    """ Process request and execute command. """
    project_config = self.ParseConfig(headers.project)

    if headers.token == project_config.token:
      logging.info('Start executing %s' % project_config.command)
      try:
        p = Popen(project_config.command, stdin=PIPE)
        if project_config.foreground:
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
