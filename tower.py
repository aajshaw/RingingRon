import urllib
import requests

import socketio

from threading import Thread
from time import sleep

import PySimpleGUI as sg

from Methods import Method, Extent

class Tower:
  def __init__(self, tower_id, gui):
    self.tower_id = tower_id
    self._gui = gui
    self._load_tower_info(tower_id)
    self._client = None
    self._ron = None
    self._method = None
    self._extent = None
    self._bell_assignments = {}
    self._stop_ron = False
    self._thread = None
    self._look_to_called = False
    self._pace = 3.0
    
  def add_method_extent(self, method, extent_id, add_cover):
    self._method = method
    self._extent = Extent(method, extent_id, cover = add_cover)
    self._bell_assignments = {}
    for ndx in range(self._extent.number_of_bells):
      self._bell_assignments[ndx + 1] = None
  
  def remove_method_extent(self):
    self._method = None
    self._extent = None
    
  def set_pace(self, pace):
    self._pace = pace
  
  def wait_for_look_to(self):
    self._stop_ron = False
    self._look_to_called = False
    self._ron_called_thats_all = False
    self._ron_called_stand_next = False
    self._thread = Thread(target = Tower.ron, args = (self, ))
    self._thread.start()
  
  def stand_down(self):
    self._stop_ron = True
  
  def is_ron_ready(self):
    return not self._stop_ron
    
  def ron(tower):
    tower.enter()
    
    # Get list of assigned ropes
    tower._announce()
    
    # Set to hand stroke so we have a consistent start
    tower._set_to_handstroke()
    
    # Wait for 'Look To' from Ringing Room or Ron being told to stand down
    while tower.is_ron_ready() and not tower._look_to_called:
      sleep(0.1)
    
    # 'Look to' has been called, give it time to play the audio
    sleep(2.8)
    
    stroke = False
    for row in tower._extent.rows:
      if tower._stop_ron:
        break
        
      stroke = not stroke
      
      # Handle handstroke gap
      if stroke:
        sleep(tower._pace / tower._extent.number_of_bells)
        
      tower._handle_calls(row)
      
      for strike in row.positions:
        if tower._stop_ron:
          break
          
        if not tower._bell_assignments[strike]:
          tower._send('c_bell_rung', {'bell': strike, 'tower_id': tower.tower_id, 'stroke': stroke})
        sleep(tower._pace / tower._extent.number_of_bells)
    
    tower._bell_asignments = {}
    
    tower._farewell()
    
    tower.leave()
    
  def _handle_calls(self, row):
    if row.call_go:
      self._call('Go')
    if row.call_bob:
      self._call('Bob')
    if row.call_single:
      self._call('Single')
    if row.call_thats_all:
      self._ron_called_thats_all = True
      self._call("That's all")
    if row.call_stand:
      self._ron_called_stand_next = True
      self._call('Stand next')
    
  def _call(self, call):
    self._send('c_call', {'call': call, 'tower_id': self.tower_id})
  
  def ron_in_tower(self):
    return self._ron is not None
  
  def valid(self):
    return self._valid
    
  def enter(self):
    # connect socketio etc
    self._client = socketio.Client()
    self._client.connect(self._load_balancing_url)

    self._client.on('s_assign_user', self._on_assign_user)
    self._client.on("s_call", self._on_call)
    self._client.on("s_user_left", self._on_user_left)
    
  def leave(self):
    # Give it a bit of time to receive any messages resulting from telling the server Ron is leaving
    sleep(0.1)
    
    self._client.disconnect()
    self._client = None
  
  def _announce(self):
    ''' Ron announces himself and asks for current state of play '''
    self._send("c_join", {"anonymous_user": True, "tower_id": self.tower_id})
    self._send('c_request_global_state', {"tower_id": self.tower_id})
    
    # Make sure we have the right number of bells
    self._send('c_size_change', {'new_size': self._extent.number_of_bells, 'tower_id': self.tower_id})
    self._look_to_called = False
    
  def _farewell(self):
    ''' Ron is off to the pub '''
    self._stand_back_ron()
    self._send('c_user_left', {'tower_id': self.tower_id})
    
  def _on_call(self, data):
    if data['call'] == 'Look to':
      self._look_to_called = True
    elif data['call'] == "That's all":
      if not self._ron_called_thats_all:
        self._stand_back_ron()
    elif data['call'] == 'Stand next':
      if not self._ron_called_stand_next:
        self._stand_back_ron()

  def _on_assign_user(self, data):
    if data['user']:
      self._bell_assignments[data['bell']] = data['user']
    else:
      self._bell_assignments[data['bell']] = None
  
  def _on_user_left(self, data):
    ''' Should get this singal when Ron leaves but not happening '''
    pass

  def _set_to_handstroke(self):
    self._send("c_set_bells", {"tower_id": self.tower_id})
  
  def _stand_back_ron(self):
    self._gui.write_event_value('-Ron Stands Back-', 'Call from tower')
    self._stop_ron = True
  
  def _load_tower_info(self, tower_id):
    # Lots of interesting stuff in the tower parameters
    url = urllib.parse.urljoin('https://ringingroom.com', str(tower_id))
    response = requests.get(url)
    if response.status_code == requests.codes.ok:
      html = response.text
      looking_for = 'window.tower_parameters = {'
      ndx = html.index(looking_for)
      params = html[ndx + len(looking_for):]
      ndx = params.index('}')
      params = params[:ndx]
      self.name = Tower._extract(params, 'name')
      self._load_balancing_url = Tower._extract(params, 'server_ip')
      self._valid = True
    else:
      self.name = 'No such tower'
      self._load_balancing_url = None
      self._valid = False
    
  def _extract(params, id):
    # Find the id, the string required will be in double quotes after a colon/space
    ndx = params.index(id + ': "')
    value = params[ndx + len(id) + 3:]
    # Everything up to the closing double quote
    ndx = value.index('"')
    value = value[:ndx]
    
    return value

  def _send(self, event, data):
    self._client.emit(event, data)
