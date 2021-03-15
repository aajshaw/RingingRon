import PySimpleGUI as sg

from tower import Tower
from Config import Config
from Methods import Method

class PlayableExtent():
    def __init__(self, method, extent_key):
        self.method = method
        self.extent_key = extent_key
    
    def __str__(self):
        return self.method.extent_name(self.extent_key)
    
    def name(self):
        return self.method.extent_name(self.extent_key)
    
    def coverable(self):
        return self.method.coverable()
    
    def number_of_bells(self):
        return self.method.number_of_bells()
    
    def method_name(self):
        return self.method.name
    
    def extent_id(self):
        return self.extent_key

def methods_and_extents(mcf_list):
  method_list = []
  
  for mcf in mcf_list:
    mi = Method(('./data/' + mcf[1] + '.mcf'))
    mi.extents = []
    method_list.append(mi)
    extent_id = 1
    while mi.extent_exists(extent_id):
      extent = PlayableExtent(mi, 'EXTENT-' + str(extent_id))
      mi.extents.append(extent)
      extent_id += 1
  
  return method_list

if __name__ == "__main__":
  def method_change(window, values):
    window['-EXTENT-'].update(value = '', values = values['-METHOD-'].extents, disabled = False, readonly = True)
    method = values['-METHOD-']
    if method.coverable():
      window['-ADD_COVER-'].update(value = True, disabled = False)
    else:
      window['-ADD_COVER-'].update(value = False, disabled = True)
  
  def extent_change(window, values):
    pass
    
  config = Config('ringingron.ini')
  
  tower = None
  
  method_list = methods_and_extents(config.items('MCF'))
  
  layout = [ [sg.Text('Enter Tower ID'), sg.Input(key = '-TOWER_ID-', size = (12, 1), enable_events = True), sg.Text('', size = (50, 1),key = '-TOWER_NAME-')],
             [sg.Text('Select method'), sg.Combo(method_list, key = '-METHOD-', enable_events = True, readonly = True)],
             [sg.Text('Select extent'), sg.Combo([], size = (50, 1), key = '-EXTENT-', enable_events = True, readonly = True, disabled = True)],
             [sg.Text('Set pace of rounds'),
              sg.Slider(key = '-PACE-', range = (2.0, 5.0), default_value = 0.5 * 6, resolution = 0.1, orientation = 'h', enable_events = True),
              sg.Checkbox('Add cover bell', key = '-ADD_COVER-', default = False, enable_events = True, disabled = True)],
              [sg.Button('Look To Ron'), sg.Button("Stop Ringing Ron", disabled = True), sg.Button('Exit')] ] 

  window = sg.Window('Ringing Ron', layout)
  
  while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Exit':
      if tower:
        # All down the pub then
        if tower.is_ron_ready():
          tower.stand_down()
        tower = None
      break
    elif event == '-TOWER_ID-':
      id = values['-TOWER_ID-']
      for ndx in range(min(len(id), 9)):
        if id[ndx] not in '123456789':
          id = id[:ndx]
          window['-TOWER_ID-'].update(id)
          break
      if len(id) > 9:
        id = id[:9]
        window['-TOWER_ID-'].update(id)
      if len(id) == 9:
        tower = Tower(int(id), window)
        if tower.valid():
          window['-TOWER_NAME-'].update(tower.name)
          tower.set_pace(values['-PACE-'])
        else:
          sg.popup_ok('Invalid tower ID')
          tower = None
      elif tower:
        if tower.ron_in_tower():
          tower.ron_leaves()
        tower = None
        window['-TOWER_NAME-'].update('Enter tower ID')
    elif event == '-METHOD-':
      method_change(window, values)
    elif event == '-EXTENT-':
      extent_change(window, values)
    elif event == '-PACE-':
      if tower:
        tower.set_pace(values['-PACE-'])
    elif event == 'Look To Ron':
      # Wake Ron up and tell him what method to ring
      if not tower or not tower.valid():
        sg.popup_ok('Tower ID required')
      elif not values['-METHOD-']:
        sg.popup_ok('Select a method')
      elif not values['-EXTENT-']:
        sg.popup_ok('Select an extent')
      else:
        tower.add_method_extent(values['-METHOD-'], values['-EXTENT-'].extent_id(), values['-ADD_COVER-'])
        tower.wait_for_look_to()
        window['Look To Ron'].update(disabled = True)
        window['Stop Ringing Ron'].update(disabled = False)
    elif event == 'Stop Ringing Ron':
      # Tell Ron to stop ringing
      tower.stand_down()
      window['Look To Ron'].update(disabled = False)
      window['Stop Ringing Ron'].update(disabled = True)
    elif event == '-Ron Stands Back-':
      window['Look To Ron'].update(disabled = False)
      window['Stop Ringing Ron'].update(disabled = True)
