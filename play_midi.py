"""
MIDI Play
Originated: 19363
    Author: Curtis Geiger
Adapted: 21363
    Author: Steven Petrick

MIDI interpetation and play functionality
Meant to be threaded via server JavaScript to perform MIDI play
"""
import mido
import sys
import json
import time
from math import floor

import board
import busio
import digitalio
import adafruit_tlc5947

# Key Offset refers to the note difference between MIDI Start(C0) and Piano Start(A0)
KEY_OFFSET = 9

# The global PWM minimum for default usage if piano is not calibrated
PWM_MIN = 2048

# Calibration file name and location - CSV
calFile = 'key_calibrations.txt'


def reset_key():
    SCK = board.SCK
    MOSI = board.MOSI
    LATCH = digitalio.DigitalInOut(board.D5)

    # Initialize SPI bus.
    spi = busio.SPI(clock=SCK, MOSI=MOSI)

    # Initialize TLC5947
    tlc5947 = adafruit_tlc5947.TLC5947(spi, LATCH, auto_write=False,
                                       num_drivers=4)
    for x in range(88):
        tlc5947[x] = 0
    tlc5947.write()
    # need to add a command to reset actuator


def gen_calibration_file():
    """
    Generates a calibration file with assumed PWM minimums give by the global
    :return:
    """
    file = open(calFile, 'r')
    for num in range(88):
        file.write(str(num)+","+str(PWM_MIN)+"\n")
    file.close()


def read_calibration_file():
    """
    Returns a dict of minimum note values (PWM) and arranges them based on their note location
    :return: noteMinList - list of notes and their minimum PWM activation strengths
    """
    noteMinDict = dict()
    file = open(calFile, 'r')
    for line in file.readlines():
        stripLine = line.rstrip()
        if line != "":
            noteMinDict[int(stripLine.split[","][0])] = int(stripLine.split[","][1])
    file.close()
    return noteMinDict


def playMidi(song_name, tempo=0):
    """
    The main MIDI playback function
    :param song_name: song in which to extract metadata from
    :param tempo: OVERWRITE tempo, 0 otherwise to set to tempo found in metadata
    :return:
    """
    mid = mido.MidiFile('midifiles/' + song_name)

    notesDict = {'songName': 'testname', 'bpm': 999, 'notes': []}
    length = 0
    notesArray = [[]]
    tickLength = 0
    VOLUME = 4
    MIN = 800

    SCK = board.SCK
    MOSI = board.MOSI
    LATCH = digitalio.DigitalInOut(board.D5)

    # Initialize SPI bus.
    spi = busio.SPI(clock=SCK, MOSI=MOSI)
    
    HBRIDGE = digitalio.DigitalInOut(board.D6)

    # Initialize TLC5947
    tlc5947 = adafruit_tlc5947.TLC5947(spi, LATCH, auto_write=False,
                                       num_drivers=4)
    for x in range(88):
        tlc5947[x] = 0
    tlc5947.write()

    for msg in mid:
        if msg.is_meta and msg.type == 'set_tempo':
            if tempo != 0: # If there is an overwriting tempo given to the function, ignore metadata
                tempo = int(msg.tempo)
            length = int(floor(mido.second2tick(mid.length,
                                                mid.ticks_per_beat,
                                                tempo)))
            tickLength = mido.tick2second(1, mid.ticks_per_beat, tempo)
            break

    print('Tick length: ' + str(tickLength))
    currentTick = 0
    notesArray[0] = [0 for x in range(90)]
    lineIncrement = 0
    for msg in mid:
        #print(msg)
        if msg.type is 'note_on' or msg.type is 'note_off':
            delayAfter = int(floor(mido.second2tick(msg.time, mid.ticks_per_beat, tempo)))
            if delayAfter == 0:
                if msg.note < 89:
                    notesArray[lineIncrement][msg.note - 12] = msg.velocity
            else:
                notesArray[lineIncrement][88] = delayAfter
                notesArray.append([0 for x in range(90)])
                for y in range(88):
                    notesArray[lineIncrement+1][y] = notesArray[lineIncrement][y]
                #notesArray.append(notesArray[lineIncrement])
                lineIncrement += 1
                notesArray[lineIncrement][88] = 0
                if msg.note < 89:
                    notesArray[lineIncrement][msg.note - 12] = msg.velocity
                    
                notesArray.append([0 for x in range(90)])
                for y in range(88) :
                    notesArray[lineIncrement+1][y] = notesArray[lineIncrement][y]
                lineIncrement += 1  
        if msg.type is 'control_change' and msg.control is 64:
            #append values to correct event in notesArray (might need to move this into above if statement).
            

        
                
                
                
            """ Old code:
                for x in range (newNote['delayAfter']):
                    if x != 0:
                        notesArray[x+currentTick] = notesArray[x+currentTick-1]
                currentTick += newNote['delayAfter']
                
            notesArray[currentTick][newNote['note'] - 1] = newNote['velocity']
            # tlc5947.write()
            notesDict['notes'].append(newNote)
            """
            
    """ ""
    with open('notes.json', 'w') as outfile:
        json.dump(notesDict, outfile)
    """

    # Velocity to PWM
    # 1-126 -> MIN PWM (2048) - 4096 | Assuming linear scale
    #           notePWM    = (((noteVel - velMin) * (PWMMax - PWMMin)) / (velMax - velMin)) + PWMMin
    # In usage: tlc5947[x] = (((line[x] - velMin) * (PWMMax - PWMMin)) / (velMax - velMin)) + PWMMin
    velMin = 1
    velMax = 127
    PWMMax = 4096
    # PWMMin is global and subject to vary depending on the note - often replaced by # in calibration file

    # Read calibration file else generate a calibration file and try again
    notesMinDict = None
    try:
        notesMinDict = read_calibration_file()
    except:
        gen_calibration_file()
        notesMinDict = read_calibration_file()
    if notesMinDict is None:
        sys.exit("Failed to read/generate calibration file. Please check file generation and reading functions.")

    startTime = time.time()
    tlc5947.write()
    time.sleep(3) # TODO: INSERT COUNTIN HERE
    for z in range(0, len(notesArray)-1, 2):
        line = notesArray[z]
        """
        tlc5947[27] = 900
        tlc5947[68] = 4000
        tlc5947.write()
        time.sleep(2)
        tlc5947[27] = 0
        tlc5947[68] = 0
        tlc5947.write()
        time.sleep(2)
        """
        
        #print(line)
        # send array to PWM IC
        for x in range(len(line) - 1):
            if line[x] != 0:
                tlc5947[x] = round((((line[x] - velMin) * (PWMMax - notesMinDict[x])) / (velMax - velMin)) + notesMinDict[x])
            else:
                tlc5947[x] = 0
        tlc5947.write()
        # time.sleep(tickLength)
        
        time.sleep(mido.tick2second(line[88], mid.ticks_per_beat, tempo) * 0.7)
        
        if notesArray[z][89] == 0 and notesArray[z+1][89] == 1: 
            # if next even actuates sustain, actuate sustain early
            HBRIDGE = 1
        
        for x in range(88):
            if notesArray[z+1][x] == 0:
                # If the note goes down, set it down early
                tlc5947[x] = notesArray[z+1][x]
        tlc5947.write()
        
        time.sleep(mido.tick2second(line[88], mid.ticks_per_beat, tempo) * 0.3)
        
    for x in range(88):
        tlc5947[x] = 0
    tlc5947.write()

reset_key()
#playMidi('bumble_bee.mid')
#playMidi('for_elise_by_beethoven.mid')
# playMidi('debussy_clair_de_lune.mid')
#playMidi('Maple_Leaf_Rag_MIDI.mid')
#playMidi('jules_mad_world.mid')
#playMidi('Pinkfong-Babyshark-Anonymous-20190203093900-nonstop2k.com.mid')
#playMidi('080-Finale.mid')
#playMidi('gwyn_by_nitro.mid')
playMidi('Westworld_Theme.mid')
#playMidi('Smash_Mouth.mid')
#playMidi('vangelis_-_chariots_of_fire_ost_bryus_vsemogushchiy.mid')
#playMidi('GameofThrones.mid')
#playMidi('Welcome_to_Jurassic_World.mid')
#playMidi('Games_of_Thrones_piano_cover_by_Lisztlovers.MID')
#playMidi('Sonic.mid')
#playMidi('Moana.mid')
#playMidi('HesaPirate.mid')
#playMidi('ChamberOfSecrets-HedwigsTheme.mid')
#playMidi('DuelOfTheFates.mid')
#playMidi('Star-Wars-Imperial-March.mid')
#playMidi('PianoMan.mid')
#playMidi('the_entertainer.mid')
#playMidi('chopin_minute.mid')
