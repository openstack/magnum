#!/usr/bin/env python

# Copyright 2015 SmartBear Software
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Swagger generic API client. This client handles the client-
server communication, and is invariant across implementations. Specifics of
the methods and models for each application are generated from the Swagger
templates."""

import __builtin__

import sys
import os
import re
import requests
import urllib
import urllib2
import httplib
import json
import datetime
import mimetypes
import random
import string

from magnum.common import utils

from oslo_utils import importutils


class ApiClient(object):
  """Generic API client for Swagger client library builds

  Attributes:
    host: The base path for the server to call
    headerName: a header to pass when making calls to the API
    headerValue: a header value to pass when making calls to the API
  """
  def __init__(self, host=None, headerName=None, headerValue=None):
    self.defaultHeaders = {}
    if (headerName is not None):
      self.defaultHeaders[headerName] = headerValue
    self.host = host
    self.cookie = None
    self.boundary = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(30))
    # Set default User-Agent.
    self.user_agent = 'Python-Swagger'

  @property
  def user_agent(self):
    return self.defaultHeaders['User-Agent']

  @user_agent.setter
  def user_agent(self, value):
    self.defaultHeaders['User-Agent'] = value

  def setDefaultHeader(self, headerName, headerValue):
    self.defaultHeaders[headerName] = headerValue

  def callAPI(self, resourcePath, method, queryParams, postData,
              ca_cert=None, cert=None, key=None, headerParams=None, files=None):

    url = self.host + resourcePath

    mergedHeaderParams = self.defaultHeaders.copy()
    if headerParams:
        mergedHeaderParams.update(headerParams)
    headers = {}
    if mergedHeaderParams:
      for param, value in mergedHeaderParams.iteritems():
        headers[param] = ApiClient.sanitizeForSerialization(value)

    if self.cookie:
      headers['Cookie'] = ApiClient.sanitizeForSerialization(self.cookie)

    data = None

    if queryParams:
      # Need to remove None values, these should not be sent
      sentQueryParams = {}
      for param, value in queryParams.items():
        if value is not None:
          sentQueryParams[param] = ApiClient.sanitizeForSerialization(value)
      url = url + '?' + urllib.urlencode(sentQueryParams)

    if method in ['GET']:
      #Options to add statements later on and for compatibility
      pass

    elif method in ['POST', 'PUT', 'DELETE']:
      if postData:
        postData = ApiClient.sanitizeForSerialization(postData)
        if 'Content-type' not in headers:
          headers['Content-type'] = 'application/json'
          data = json.dumps(postData)
        elif headers['Content-type'] == 'multipart/form-data':
          data = self.buildMultipartFormData(postData, files)
          headers['Content-type'] = 'multipart/form-data; boundary={0}'.format(self.boundary)
          headers['Content-length'] = str(len(data))
        else:
            data = urllib.urlencode(postData)

    else:
      raise Exception('Method ' + method + ' is not recognized.')

    utils.raise_exception_invalid_scheme(url)

    response = requests.request(method, url=url, headers=headers, data=data,
                                cert=(cert, key), verify=ca_cert)
    if 'Set-Cookie' in response.headers:
      self.cookie = response.headers['Set-Cookie']
    try:
      data = json.loads(response.content)
    except ValueError:  # PUT requests don't return anything
      data = None

    return data

  def toPathValue(self, obj):
    """Convert a string or object to a path-friendly value
    Args:
        obj -- object or string value
    Returns:
        string -- quoted value
    """
    if type(obj) == list:
      return ','.join(obj)
    else:
      return str(obj)

  @staticmethod
  def sanitizeForSerialization(obj):
    """
    Sanitize an object for Request.

    If obj is None, return None.
    If obj is str, int, long, float, bool, return directly.
    If obj is datetime.datetime, datetime.date convert to string in iso8601 format.
    If obj is list, santize each element in the list.
    If obj is dict, return the dict.
    If obj is swagger model, return the properties dict.
    """
    if isinstance(obj, type(None)):
      return None
    elif isinstance(obj, (unicode, str, int, long, float, bool, file)):
      return obj
    elif isinstance(obj, list):
      return [ApiClient.sanitizeForSerialization(subObj) for subObj in obj]
    elif isinstance(obj, (datetime.datetime, datetime.date)):
      return obj.isoformat()
    else:
      if isinstance(obj, dict):
        objDict = obj
      else:
        # Convert model obj to dict except attributes `swaggerTypes`, `attributeMap`
        # and attributes which value is not None.
        # Convert attribute name to json key in model definition for request.
        objDict = {obj.attributeMap[key]: val
                   for key, val in obj.__dict__.iteritems()
                   if key != 'swaggerTypes' and key != 'attributeMap' and val is not None}
      return {key: ApiClient.sanitizeForSerialization(val)
              for (key, val) in objDict.iteritems()}

  def buildMultipartFormData(self, postData, files):
    def escape_quotes(s):
      return s.replace('"', '\\"')

    lines = []

    for name, value in postData.items():
      lines.extend((
        '--{0}'.format(self.boundary),
        'Content-Disposition: form-data; name="{0}"'.format(escape_quotes(name)),
        '',
        str(value),
      ))

    for name, filepath in files.items():
      f = open(filepath, 'r')
      filename = filepath.split('/')[-1]
      mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
      lines.extend((
        '--{0}'.format(self.boundary),
        'Content-Disposition: form-data; name="{0}"; filename="{1}"'.format(escape_quotes(name), escape_quotes(filename)),
        'Content-Type: {0}'.format(mimetype),
        '',
        f.read()
      ))

    lines.extend((
      '--{0}--'.format(self.boundary),
      ''
    ))
    return '\r\n'.join(lines)

  def deserialize(self, obj, objClass):
    """Deserialize a JSON string into an object.

    Args:
        obj -- string or object to be deserialized
        objClass -- class literal for deserialzied object, or string
            of class name
    Returns:
        object -- deserialized object"""

    # Have to accept objClass as string or actual type. Type could be a
    # native Python type, or one of the model classes.
    if type(objClass) == str:
      if 'list[' in objClass:
        match = re.match('list\[(.*)\]', objClass)
        subClass = match.group(1)
        return [self.deserialize(subObj, subClass) for subObj in obj]

      classname = objClass
      if classname in {'int', 'float', 'long', 'dict', 'list', 'str', 'bool'}:
        objClass = getattr(__builtin__, classname)
      elif classname == 'datetime':
        objClass = self.__parse_string_to_datetime
      else:  # not a native type, must be model class
        model = ('magnum.common.pythonk8sclient.client.models.%s.%s' %
                 (classname, classname))
        objClass = importutils.import_class(model)
    else:
      classname = None

    if ((getattr(objClass, '__module__', None) == __builtin__.__name__) or
        (classname == 'datetime')):
      return objClass(obj)

    instance = objClass()

    for attr, attrType in instance.swaggerTypes.iteritems():
        if obj is not None and instance.attributeMap[attr] in obj and type(obj) in [list, dict]:
          value = obj[instance.attributeMap[attr]]
          if attrType in {'str', 'int', 'long', 'float', 'bool'}:
            attrType = getattr(__builtin__, attrType)
            try:
              value = attrType(value)
            except UnicodeEncodeError:
              value = unicode(value)
            except TypeError:
              value = value
            setattr(instance, attr, value)
          elif (attrType == 'datetime'):
            setattr(instance, attr, self.__parse_string_to_datetime(value))
          elif 'list[' in attrType:
            match = re.match('list\[(.*)\]', attrType)
            subClass = match.group(1)
            subValues = []
            if not value:
              setattr(instance, attr, None)
            else:
              for subValue in value:
                subValues.append(self.deserialize(subValue, subClass))
            setattr(instance, attr, subValues)
          else:
            setattr(instance, attr, self.deserialize(value, attrType))
    return instance

  def __parse_string_to_datetime(self, string):
    """
    Parse datetime in string to datetime.

    The string should be in iso8601 datetime format.
    """
    try:
        from dateutil.parser import parse
        return parse(string)
    except ImportError:
        return string
