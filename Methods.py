from time import sleep
import configparser
from random import randrange

class Row():
  def __init__(self, number_of_bells):
    self.positions = [None for ndx in range(number_of_bells)]
    self.call_go = False
    self.call_thats_all = False
    self.call_bob = False
    self.call_single = False
    self.call_stand = False
  
class Extent():
  LEAD_TYPE_PLAIN = 'P'
  LEAD_TYPE_BOB = 'B'
  LEAD_TYPE_SINGLE = 'S'
  
  def __init__(self, method, extent_id, cover = True, intro_courses = 1, extent_courses = 1):
    self.name = method.extent_name(extent_id)
    self.length = method.extent_length(extent_id) * extent_courses
    self.definition = method.extent_definition(extent_id)
    # If the extent is mutable it can be shift shuffled
    # The sections that can be shifted are delimited by '-' characters so will be split, shifted and then stuck togather
    if method.extent_mutable(extent_id):
        # Remove all formatting spaces
        self.definition = self.definition.replace(' ', '')
        # Break into sections
        sections = self.definition.split('-')
        for ndx in range(len(sections)):
            s = sections[ndx]
            # Decide how many shifts to perform on the section
            shifts = randrange(len(s))
            for shift in range(shifts):
                s = s[-1] + s[0:-1]
            sections[ndx] = s
        # Reassemble the sections
        self.definition = ''.join(sections)
    # The number of bells being rung is the number of bells in the method plus the optional cover
    self.number_of_bells = method.number_of_bells()
    self.cover = cover
    if self.cover:
      self.number_of_bells += 1
    
    # A reference to the parent method is only needed for dumping to text
    self.method = method
    
    self.rows = []

    # The last lead is 'plain' to force a plain start in the first lead
    last_lead = Extent.LEAD_TYPE_PLAIN
    for courses in range(extent_courses):
      # Build the course
      for lead in self.definition:
        Extent._add_lead_start(last_lead, self.rows, method, self.length, cover)
        if lead in ('p', 'P'):
          Extent._add_plain(self.rows, method, self.length, cover)
          last_lead = Extent.LEAD_TYPE_PLAIN
        elif lead in ('b', 'B'):
          Extent._add_bob(self.rows, method, self.length, cover)
          last_lead = Extent.LEAD_TYPE_BOB
        elif lead in ('s', 'S'):
          Extent._add_single(self.rows, method, self.length, cover)
          last_lead = Extent.LEAD_TYPE_SINGLE
    
    # Add the intro rounds and the Go Method call to the last backstroke of the intro
    intro = []
    for ndx in range(intro_courses):
      Extent._add_round(intro, self.number_of_bells)
    intro[((intro_courses - 1) * 2) + 1].call_go = True
    self.rows = intro + self.rows
    
    # Add That's All to the second to last row of the extent
    self.rows[len(self.rows) - 2].call_thats_all = True
        
    # If the extent ended on a back stroke add the extra half round
    if len(self.rows) % 2 != 0:
      Extent._add_half_round(self.rows, self.number_of_bells)
    
    # Add the final rounds and the call to Stand
    Extent._add_round(self.rows, self.number_of_bells)
    self.rows[len(self.rows) - 2].call_stand = True
    
  def _add_half_round(rows, bells):
    row = Row(bells)
    for ndx in range(bells):
      row.positions[ndx] = ndx + 1
    rows.append(row)

  def _add_round(rows, bells):
    Extent._add_half_round(rows, bells)
    Extent._add_half_round(rows, bells)

  def _add_lead_start(last_lead, rows, method, length, cover):
    if last_lead == Extent.LEAD_TYPE_PLAIN:
      Extent._apply(rows, method.number_of_bells(), method.plain_start, length, cover)
    elif last_lead == Extent.LEAD_TYPE_BOB:
      Extent._apply(rows, method.number_of_bells(), method.bob_start, length, cover)
    elif last_lead == Extent.LEAD_TYPE_SINGLE:
      Extent._apply(rows, method.number_of_bells(), method.single_start, length, cover)

  def _add_plain(rows, method, length, cover):
    Extent._apply(rows, method.number_of_bells(), method.tracks, length, cover)
    Extent._apply(rows, method.number_of_bells(), method.plain, length, cover)

  def _add_bob(rows, method, length, cover):
    Extent._apply(rows, method.number_of_bells(), method.tracks, length, cover)
    # Call the Bob at the beginning of the last row BEFORE the Bob
    rows[len(rows) - 1].call_bob = True
    Extent._apply(rows, method.number_of_bells(), method.bob, length, cover)

  def _add_single(rows, method, length, cover):
    Extent._apply(rows, method.number_of_bells(), method.tracks, length, cover)
    # Call the Single at the beginning of the last row BEFORE the Single
    rows[len(rows) - 1].call_single = True
    Extent._apply(rows, method.number_of_bells(), method.single, length, cover)

  def _apply(rows, number_of_bells, work, length, cover):
    prev = len(rows) - 1
    bells = number_of_bells
    if cover:
      bells += 1
    
    if len(work) > 0:
      for ndx in range(len(work[0])):
          if length > len(rows):
              row = Row(bells)
              if cover:
                row.positions[bells -1] = bells
              rows.append(row)

      for track in range(number_of_bells):
          if prev < 0:
              bell = track + 1
          else:
              bell = rows[prev].positions[track]
          curr = prev + 1
          for t in work[track]:
              if curr < length:
                  rows[curr].positions[t - 1] = bell
                  curr += 1
class Method():
  def __init__(self, file):
    self.definition = configparser.ConfigParser()
    self.definition.optionxform = str # Don't want keys to be lower cased
    
    self.definition.read(file)
    self.name = self.definition.get('INFO', 'name')

    self.tracks = {}
    for key in self.definition['TRACKS']:
      self.tracks[int(key) - 1] = [int(v) for v in self.definition['TRACKS'][key].split()]

    # Just in case a method is added where the Bobs and singles have an
    # effect across the end of a lead and into the start of the next lead. To account for
    # this the concept of the start of a lead being different depending on the previous
    # lead was introduced. The PLAIN_START, BOB_START and SINGLE_START sections of the
    # definition files are optional as they are not necessary for most mothods
    self.plain_start = {}
    if self.definition.has_section('PLAIN_START'):
      for key in self.definition['PLAIN_START']:
        self.plain_start[int(key) - 1] = [int(v) for v in self.definition['PLAIN_START'][key].split()]
      
    self.plain = {}
    if self.definition.has_section('PLAIN'):
      for key in self.definition['PLAIN']:
        self.plain[int(key) - 1] = [int(v) for v in self.definition['PLAIN'][key].split()]

    self.bob_start = {}
    if self.definition.has_section('BOB_START'):
      for key in self.definition['BOB_START']:
        self.bob_start[int(key) - 1] = [int(v) for v in self.definition['BOB_START'][key].split()]
      
    self.bob = {}
    if self.definition.has_section('BOB'):
      for key in self.definition['BOB']:
        self.bob[int(key) - 1] = [int(v) for v in self.definition['BOB'][key].split()]

    self.single_start = {}
    if self.definition.has_section('SINGLE_START'):
      for key in self.definition['SINGLE_START']:
        self.single_start[int(key) - 1] = [int(v) for v in self.definition['SINGLE_START'][key].split()]
      
    self.single = {}
    if self.definition.has_section('SINGLE'):
      for key in self.definition['SINGLE']:
        self.single[int(key) - 1] = [int(v) for v in self.definition['SINGLE'][key].split()]

  def __str__(self):
      return self.name
  
  def get_name(self):
    return self.name
  
  def extent_exists(self, extent_id):
    key = 'EXTENT-' + str(extent_id)
    return key in self.definition
    
  def number_of_bells(self):
    return self.definition.getint('INFO', 'bells')
    
  def coverable(self):
    return self.definition.getboolean('INFO', 'coverable', fallback = False)
    
  def extent_name(self, key):
    return self.definition.get(key, 'NAME')
  
  def extent_length(self, key):
    return self.definition.getint(key, 'LENGTH')

  def extent_size(self, key, cover, intros, courses):
      bells = self.number_of_bells()
      if self.coverable() and cover:
          bells += 1
          
      size = self.extent_length(key) * bells * courses
      size += intros * bells * 2
      size += bells * 2 # Always two extro rounds
      
      return size
  
  def extent_definition(self, key):
    return self.definition.get(key, 'DEFINITION')

  def extent_mutable(self, key):
    return self.definition.getboolean(key, 'MUTABLE', fallback = False)
    
