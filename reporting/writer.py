import sys
import os
import re
import time
import json
import importlib
from glob import glob
import logging
from device_kit_market_simulations.utils._make_iterencode import _make_iterencode


logger = logging.getLogger(__name__)


class JSONEncoder(json.JSONEncoder):
  ''' Hook into json encoding process:
        "...to recognize other objects, subclass and implement a default() method with another method
        that returns a serializable object for o if possible, otherwise it should call the superclass
        implementation (to raise TypeError)." -- https://docs.python.org/3/library/json.html#encoders-and-decoders.
  '''
  def default(self, o):
    ''' "For example, to support arbitrary iterators, you could implement default like this:" '''
    if isinstance(o, object) and hasattr(o, 'to_dict'):
      try:
        d = o.to_dict()
        d['_type'] = o.__module__ + '.' + o.__class__.__name__
        return d
      except TypeError:
        pass
    try:
      return o.tolist()
    except Exception:
      pass
    try:
      return list(o)
    except Exception:
      pass
    return json.JSONEncoder.default(self, o)


def JSONDecoderObjectHook(o):
  ''' "object_hook is an optional function that will be called with the result of any object literal decoded (a dict)." '''
  if '_type' in o:
    _type = o['_type']
    del o['_type']
    (_module, _class) = _type.rsplit('.', 1)
    type_class = getattr(importlib.import_module(_module), _class)
    logger.debug('DecoderHook() found _type. Calling %s' % (str(type_class),))
    if hasattr(type_class, 'from_dict'):
      return type_class.from_dict(o)
    else:
      return type_class(**o)
  return o


class NetworkWriter():
  ''' Serialize the network and save consumption matrix at every call to update. Given the network
  (which includes all it's agents) only the consumption matrix is needed to replay the scenario completely.
  '''
  output_dir = None
  network = None
  meta = None
  indent = 2

  def __init__(self, network, output_dir=None, meta=None):
    ''' Init network writer.
    `network` is a Network type to dump when update() is called.
    `output_dir` optional output directory, otherwise a tmp dir is created.
    `meta` a hash of any meta info about the network that should be stored.
    '''
    self.network = network
    self.output_dir = output_dir if output_dir else '/tmp/{id}-network'.format(id=network.id)
    self.indent = self._get_indent()
    if not os.path.isdir(self.output_dir):
      os.mkdir(self.output_dir)
    if meta:
      with open(self.output_dir + '/meta.json', 'w') as f:
        json.dump(meta, f)

  def update(self, network, event):
    filename_tmpl = '{dir}/network-{step}.json'
    if event in ['after-init', 'after-step']:
      filename = filename_tmpl.format(
        dir=self.output_dir,
        step=self.network.steps
      )
      logger.info('Writing %s', filename)
      with open(filename, 'w') as f:
        json.dump(self.network, f, indent=self.indent, cls=JSONEncoder)

  def close(self):
    logger.info('Writer storing simulation raw data to %s' % (self.output_dir,))

  @classmethod
  def _get_indent(cls):
    ''' Hack to replace built in json encoder to handle arrays a dict indentation separately '''
    v = sys.version_info
    indent = None
    if v.major == 3 and 4 <= v.minor <= 6:
      json.encoder._make_iterencode = _make_iterencode
      indent = (2, None)
    return indent


class NetworkReader():
  ''' Read Networks serialized to JSON format by NetworkWriter. '''
  output_dir = None
  meta = None
  files = []

  def __init__(self, output_dir):
    if not os.path.isdir(output_dir):
      raise ValueError('Not a directory %s' % (output_dir))
    self.output_dir = output_dir
    if os.path.isfile(self.output_dir + '/meta.json'):
      with open(self.output_dir + '/meta.json', 'r') as f:
        self.meta = json.load(f)
    self._glob()

  def __len__(self):
    return len(self.files)

  def __iter__(self):
    for filename in self.files:
      with open(filename, 'r') as f:
        yield json.load(f, object_hook=JSONDecoderObjectHook)

  def get(self, i):
    with open(self.files[i], 'r') as f:
      return json.load(f, object_hook=JSONDecoderObjectHook)

  def first(self):
    with open(self.files[0], 'r') as f:
      return json.load(f, object_hook=JSONDecoderObjectHook)

  def last(self):
    with open(self.files[len(self)-1], 'r') as f:
      return json.load(f, object_hook=JSONDecoderObjectHook)

  def _glob(self):
    sort_key = lambda f: int(re.match('.*-(\d+)\.json$', f).groups()[0])
    self.files = sorted(glob(self.output_dir + '/network-*.json'), key=sort_key)
