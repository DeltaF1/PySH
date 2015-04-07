import sys
import time

import random
import copy

import hashlib
import json
import re

from threading import Thread
from Queue import Queue
from Queue import Empty
import socket

#Modules


PORT = 9000

class SocketError(Exception):
	pass

class Stop(Exception):
	pass


#Dictionary of corresponding directions
directions ={
"east":"west",
"north":"south",
"up":"down",
"in":"out",
"northwest":"southeast",
"northeast":"southwest",
}

t = 0

movements = {

"north":(0,1),
"south":(0,-1),
"west":(-1,0),
"east":(1,0),

#add more later, add third dimension?
	
}

olddirections = directions.copy()

for dir1, dir2 in olddirections.iteritems():
	#Make all directions be reversible. North leads to south, but south also leads to north
	directions[dir2]=dir1

directions["void"]="void"

#From Javier @ stackoverflow.com
def num(s):
    try:
        return int(s)
    except ValueError:
        return float(s)

#From Martijn Pieters @ stackoverflow.com
def getFromDict(dataDict, mapList):
    return reduce(lambda d, k: d[k], mapList, dataDict)

def setInDict(dataDict, mapList, value):
    getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value

def recurseDict(dataDict, func, *args):
	for key, value in dataDict.iteritems():
		if isinstance(value, dict):
			dataDict[key] = recurseDict(value, func, *args)
		else:
			dataDict[key] = func(value, *args)
	return dataDict

def randomPercent(percentage):
	random.randrange(100) < percentage*100

class EventType(type):
	d = {
	"display" : {
		"verb":"display",
		"target":"user",
		"destroy":False,
		"data": {
			"text":"An item was used!"
			}
		},
	"teleport": {
		"verb":"teleport",
		"target":"user",
		"destroy":False,
		"data": {
			"destination":"north"
			}
		},
	"create": {
		"verb":"create",
		"target":"user",
		"destroy":False,
		"data":{
			"type":"item",
			"from":"template",
			"item":15 #Dooby!,
		}
	}

	}
	def __getattr__(cls, key):
		return copy.deepcopy(cls.d[key.lower()])

	def __getitem__(cls, key):
		return getattr(cls, key)

class Events:
	__metaclass__ = EventType
	

class Timer:
	def __init__(self, f, length, *args):
		self.f = f
		self.length = length
		self.args = args

	def tick(self):
		self.length -= 1

		if self.length <= 0:
			Debug("Timer over!")
			self.f(*self.args)
			return True

		return False

def parseEvent(value):
	print("Entering parse!")
	if value and isinstance(value, basestring):
		print("It's astring!")
		if value[0] == "r":
			print("Generating something random!")
			if value[1] == "%":
				#Generate a random percentage
				try:
					parts = value[2:].split("/")
					dividend = parts[0]
					divisor = parts[1]
					return randomPercent(float(dividend)/float(divisor))
				except IndexError, TypeError:

					pass
			elif (value[1] == "["  or value[2] == "[") and value[-1] == "]":
				#generate a randome item from a list
				print("[parseEvent] Generating choice...")
				start = 2
				
				if value[2] == "[":
					start = 1
					

				parts = value[start:-1].split(";")
				choice = random.choice(parts)

				if start == 2:
					
					if value[1] == "f":
						choice = float(choice)
					elif value[1] == "i":
						choice = int(choice)

				return choice

			elif value[1] == "n":
				print("[parseEvent] Generating random number...")
				parts = value[2:].split(":")
				p1 = int(parts[0])
				p2 = int(parts[1])

				if p1 > p2:
					t = p1
					p2 = p1
					p1 = t

				return random.randrange(p1, p2)

	return value

def parseEvent(line):
	if isinstance(line, basestring):
		
		match = re.search(r"r(.?)\{(.*?)\}", line)

		if not match:
			print("no matches found in (%s), going back up the stack"%line)
			return line

		first, last = match.span()

		form = match.group(1)
		body = match.group(2)

		if body[0] == "[":
			body = body[1:-1]
			print("Stripped body to",body)

			items = body.split(";")
			choice = random.choice(items)
			try:
				if form == "i":
					choice = int(choice)
				elif form == "f":
					choice = float(choice)
			except ValueError:
				#Someone put an invalid string into the list!
				pass
			new = choice

		elif form == "%":
			
			if "/" in body:
				dividend, divsor = body.split("/")
				dividend, divisor = float(dividend), float(divisor)
				chance = dividend/divisor
			else:
				chance = float(body)


			new = randomPercent(chance)
		elif ":" in body:

			min, max = body.split(":")

			if min > max:
				temp = max
				min = max
				max = temp
			
			if form == "f":
				new = random.uniform(float(min), float(max))
			else:
				new = random.randrange(int(min), int(max))


		if line != match.group(0):
			#There's more than this random string, convert result to string
			new = str(new)
			part1 = line[:first]
			part2 = line[last:]
			newLine = part1+new+part2
			print("newLine = ",newLine)
		else:
			newLine = new
			return newLine

		return parseEvent(newLine)
	else:
		#It's not a string, move on!
		return line







class EventEntity(object):
	def __init__(self, events = {}):
		self.events = events
	
	def addEvent(self, trigger, event, position = -1):
		if trigger not in self.events:
			self.events[trigger] = []

		#Note-to-self: I can make a "Portal" ths way

		#Portal = Item("portal", "")
		#Portal.addEvent("use", Event.Teleport, 0)
		#Portal.addEvent("use", Event.Display)

		self.events[trigger].insert(position, event)

	def trigger(self, tr, entity, *args):
		if "aliases" in self.events:
			for trigger in self.events["aliases"]:
					
					if tr in self.events["aliases"][trigger]:
						tr = trigger
						break

		if tr in self.events:
			Debug("We have events for this trigger!")



			events = self.events[tr]
			
			for event in events:
				if "blacklist" in event:
					if entity.id in event["blacklist"]:
						#We've already done this and aren't allowed again.
						Debug("Not firing event, entity in blacklist!")
						return False
				Debug("Firing event, with verb of "+event["verb"]+"!")
				e = copy.deepcopy(event)
				
				print("Old-e = "+str(e))
				e=recurseDict(e, parseEvent)
				print("New-e = "+str(e))

				if "fire" in e:
					if not e["fire"]:continue

				f = getattr(self, "do_"+e["verb"])
				if "time" in e:
					Debug("[EventEntity.trigger] Starting timer!")
					timers.append(Timer(f, e["time"], e, entity, *args))
				else:
					Debug("[EventEntity.trigger] Running immediately!")
					f(e, entity, *args)
				if e["destroy"]: events.remove(e)
				if "blacklist" in e:
					e["blacklist"].append(entity.id)
	
	def do_display(self, e, entity, *args):
		Debug("Doing display!")

		Debug("Types:  self : {0}, e : {1}, entity : {2} ".format(str(type(self)), str(type(e)), str(type(entity))))

		Debug("Getting text!")
		text = e["data"]["text"].format(entity.name)
		
		Debug("Getting target name!")
		target = e["target"]
		
		Debug("Getting target entity!")
		if target == "user":
			entity.send(text)
		elif target == "room":
			if type(self) == Room:
				self.broadcast(text)
			else:
				entity.room.broadcast(text)
		elif target == "roomEx":
			exclusion = [entity]
			if len(args):
				exclusion.append(args[0])
			entity.room.broadcast(text, exclusion)
		elif target == "target":
			args[0].send(text)

		elif target == "global":
			#Ummmm....
			#Figure something out...
			pass
		Debug("Displaying done...")
	
	def do_attack(self, e, entity, *args):
		target = e["target"]

		num = random.random(e["data"]["min"], e["data"]["max"])

		if target == "target":
			#args[0].damage(num, entity)
			args[0].send("You were hit for %i by %s"%(num, entity.name))

	def do_teleport(self, e, entity, *args):
		
		#Ignore Target for now. We will eventually add support for other things being tped
		
		destination = e["data"]["destination"]
		
		if destination in directions:
			#We've got a valid movement
			entity.move(destination, quiet = e["data"]["quiet"])
		else:
			#Just a teleport to a room, specified by id
			rooms[destination].addPlayer(entity, quiet = e["data"]["quiet"])

	def do_trigger(self, e, entity, *args):
		Debug("Doing verb 'trigger'")
		trigger = e["data"]["trigger"]
		target = e["target"]
		Debug("Triggering a trigger of '"+trigger+"'")

		if target == "user":
			eTrigger = entity
		elif target == "self":
			eTrigger = self
		elif type(target) == int:
			eTrigger = items[target]
		else:
			eTrigger = entity.room.getEntity(target)

		eEntityName = e["data"]["entity"]

		if eEntityName == "user":
			eEntity = entity
		elif eEntityName == "self":
			eEntity = self
		elif eEntityName == "target":
			eEntity = eTrigger 
		elif type(eEntityName) == int:
			eEntity = items[eEntityName]
		else:
			eEntity = entity.room.getEntity(eEntityName)
		
		if not eEntity:
			#We didn't supply an entity (really a player...) to be "triggering" the other entity
			return False	
		
		
		eTrigger.trigger(trigger, eEntity)

	def do_create(self, e, entity, *args):
		type = e["data"]["type"]


		if type == "item":
			if e["data"]["from"] == "template":
				base = items[e["data"]["item"]]

				s = base.toJSON()
				s["id"] = Item.class_counter + 1

				new = Item.fromJSON(s)

				items[new.id] = new

				if e["target"] == "user":
					entity.inventory.append(new)
			
def convertMessages(dataDict, key, value):
	dataDict[key] = value.format("{player}", "{dir}")


class Room(EventEntity):
	"""
	The container for all entities (Players, NPCS, items)

	Responsible for moving players between instances of itself.
	"""
	counter = 1
	def __init__(self, name="Room", desc=""):
		self.name=name
		self.desc=desc
		self.players=[]
		self.items=[]
		self.id = Room.counter
		Room.counter +=1
		
		EventEntity.__init__(self)
		
		self.messages = {
			"enter":
				{
					"default":"{player} enters from the {dir}",
					"up":"{player} enters from above",
					"down":"{player} enter from below"
				},
			"exit":
				{
					"default":"{player} leaves to the {dir}",
					"up":"{player} ascends",
					"down":"{player} descends"
				}
			}
		
		self.exits = directions.copy()
		
		#self.exits will now be a dictionary with keys of every possible directions, and values of None
		for k in self.exits:
			self.exits[k] = None
		
	def setName(self, name):
		self.name=name
		
	def setDesc(self, desc):
		self.desc=desc

	def getEntity(self, name):
		"""
		Return a player or other entity in the room of a given name
		"""
		name = name.lower()
		for i in self.players:
			if i.name.lower()==name or name in i.aliases:
				return i
			
		for i in self.items:
			if i.name.lower()==name or name in i.aliases:
				return i

		return None
	
	def broadcast(self, message, player=None):
		
		for i in self.players:
			if i == player or type(player) == list and i in player:continue
			i.send(message.format(self=i.name))
		
	def look(self, player):
		"""
		Returns a string describing the room, to be sent to the player when they enter a room or type "look" with no arguments
		"""
		message = ""
		message+=self.name+"\n"
		message+="\n"
		message+=self.desc

				
		#print players
		if len(self.players) > 1:
			message+="\r\n"*2

			for i in self.players:
				if i!=player:
					#Append the "standing" message of the player. This can be edited per player, so that each player has a unique attitude and presence
					message+=(i.name+" "+i.messages["standing"]+" ")

		return message
			
	def addPlayer(self, player, dir = "void", quiet = False):
		"""
		
		Adds the specified player to this room, as if they are moving in 'dir' direction from the previous room to this one

		ex:
			r1.addPlayer(p1, "wesr")

			means that the player is travelling west from thier previous room to this one.
		
		"""
		if player.room:
			player.room.removePlayer(player, dir, quiet)
		player.room = self
		
		self.players.append(player)
		
		player.send(self.look(player))
		
		if not quiet:
			#A room's messages are format strings, with the player's name and direction passed as arguments. For example : "{player} walks through the doorway to the {dir}"
			msg = self.messages["enter"]

			aDir = directions[dir]
			
			if aDir in msg:
				enterMsg = msg[aDir]
			else:
				enterMsg = msg["default"]

			#Debug("enterMsg = "+enterMsg)
			self.broadcast(enterMsg.format(player=player.name, dir=aDir), player)
				
		self.trigger("enter", player)
		
		
	def removePlayer(self, player, dir, quiet):
		if player in self.players:
			self.players.remove(player)

			if not quiet:
				msg = self.messages["exit"]		   

				if dir in msg:
					exitMsg = msg[dir]
				else:
					exitMsg = msg["default"]
				
				self.broadcast(exitMsg.format(player=player.name, dir=dir))
	
	def addRoom(self, room, dir, recip = True):
		"""

		Creates a link from this room to another, via the direction 'dir'.

		If 'recip' is set to True, then there will be a reciprocal link created from the other room to this one, via the opposite direction 
		
		"""
		self.exits[dir] = room
		if recip:
			room.exits[directions[dir]] = self


	def removeRoom(self, dir, recip=True):
		if recip:
			self.exits[dir].exits[directions[dir]]=None
		self.exits[dir]=None
		
	def addItem(self, item):
		if item.room:
			item.room.items.remove(item)
		item.room=self
		self.items.append(item)

	def setMessage(self, name, value):
		Debug("Running Room.setMessage!")
		names = name.split(".")

		setInDict(self.messages, names, value)
		
	def toJSON(self):
		s = {"name":self.name, "desc":self.desc, "items":[], "exits":{}, "messages":self.messages, "events":self.events}
		
		for i in self.items:
			s["items"].append(i.id)
			
		for i in self.exits:
			if self.exits[i]:
				s["exits"][i] = self.exits[i].id
		
		return s


	@classmethod
	def fromJSON(cls, s):
		r = cls(s["name"], s["desc"])
		
		r.events = s["events"]
		r.items = s["items"]
		r.messages = s["messages"]
			
		return r

class Item(EventEntity):
	
	class_counter = 0
	def __init__(self, name, desc = "It's... a thing...", aliases = []):
		self.name=name
		self.room=None
		self.desc = desc
		self.id = Item.class_counter
		Item.class_counter += 1

		#Aliases are the other names that a player can use to refer to the item. For example, a chair could be referred to as "chair", "la-z-boy", or "seat"
		self.aliases = aliases
		
		EventEntity.__init__(self)
		
		#if rooted is set to False, then the player can pick up this item and add it to their inventory
		self.rooted = True
		self.messages = {
			"rooted":"It's rooted to the spot!",
			"useTarget":"You use the {0} on {1}.",
			"use":"You use the {0}."
			}
		
		#events = {"get":[events...], "use":[events...]}

	
	def setMessage(self, name, val):
		self.messages[name]=val
		
	def setDesc(self, desc):
		self.desc = desc
	
	'''
	def use(self, player, target=None):
		verb = self.action["verb"]
		
		if verb == "move":
			
	'''
	def get(self, player):
		if self.rooted:
			return False
		else:
			self.room.items.remove(self)
			self.room = None
			return True
	
	def look(self, player):

		return self.desc
		
	def toJSON(self):
		s = {"name":self.name, "desc":self.desc, "aliases":self.aliases, "messages":self.messages, "events":self.events, "id":self.id}
		
		if self.rooted:
			s["rooted"] = 1
		else:
			s["rooted"] = 0
		
		return s
	
	@classmethod
	def fromJSON(cls, s):
		i = cls(s["name"], s["desc"])
		i.aliases = s["aliases"]
		i.messages = s["messages"]
		i.rooted = s["rooted"]
		
		i.events = s["events"]
		
		return i

class TextIO:
	"""
	A base class for all player IO operations. The sendRaw() and receive() functions are overwritten by subclasses for each specific method of IO 
	"""
	class_counter = 0
	def __init__(self):
		#Keep a running tally of how many TextIO instances there are. Mainly for debug purposes.
		self.id = TextIO.class_counter
		TextIO.class_counter+=1
		
	def send(self, message):
		self.sendRaw(message+"\n")
		
	def close(self):
		pass

class SocketIO(TextIO):
	"""
	IO Class for communication via an internet Socket.
	"""
	def __init__(self, socket):
		TextIO.__init__(self)
		self.sock = socket

	def receive(self, prompt):
		self.sendRaw(prompt)
		return self.sock.recv(1024)
		
		
	def sendRaw(self, message):
		self.sock.send(message)
		
	def close(self):
		self.sock.close()

class TerminalIO(TextIO):
	"""
	IO Class for communication via stdout and stdin
	"""
	def sendRaw(self, message):
		sys.stdout.write(message)

	def receive(self, prompt):
		return raw_input(prompt)

class DummyIO(TextIO):
	"""
	IO Class for NPCs, may be expanded later to interface with an AI module
	"""
	def sendRaw(self, message):
		pass

	def receive(self, prompt):
		return ""

class TextHandler(object):
	def __init__(self):
		self.commands = []
		#Get the name of our class, and remove the "Handler" part. i.e. MainHandler -> "Main"
		self.name = self.__class__.__name__.replace("Handler", "")
		for c in commands:
			#If this command should be accesable from this handler level
			if c.scope == "all" or self.name in c.scope:
				self.commands.append(c)
				
		
	def preParse(self, cString, args):
		self.player = cString["player"]
		Debug("[TextHandler.parse] args = "+str(args))
		self.handlerArgs = args
		self.command = cString["name"]
		self.args = cString["args"]

	def duringParse(self, cString, args):
		ran = False
		for c in self.commands:
			c.handler = self
			if c.check(cString):
				ran = True
				break
		
		if not ran:
			Debug("Player attempted to use the command '"+self.command+"'")
			self.player.send("Invalid command! Try 'help'")

	def postParse(self, cString, args):
		prompt = ""
		if len(self.player.handlers) == 1:
			prompt = ">"
		else:
			for i in self.player.handlers:
				if i[0] != "Main":
					prompt += i[0].lower() + ">"

		self.player.sendRaw(prompt)

		self.player = None
		self.args = None

	def parse(self, cString, args):
		
		self.preParse(cString, args)

		self.duringParse(cString, args)
		
		self.postParse(cString, args)
	
	def releaseHandler(self):
		_ = self.player.handlers.pop()
	
	def requestHandler(self, handler, args):
		self.player.handlers.append([handler, args])
	
class MainHandler(TextHandler):
	
	def releaseHandler(self):
		#We can't release this handler, it's the main one and there's nothing to fall back on
		Debug("Command '"+self.command+"'' tried to release MainHandler!")
		return False
	'''
	def do_look(self):

		target = self.player.room
		if self.args:
			name = self.args[0]
			name = name.lower()
			newtarget = target.getEntity(name)
			if name == "me":
		
				newtarget = self.player
		
			if not newtarget:
				newtarget = self.player.getItem(name)
				if not newtarget:
					self.player.send("You can't see that!")
					return
				target = newtarget
			else:
				
				target=newtarget

		self.player.send(target.look(self.player))
	'''

class TestHandler(TextHandler):
	pass

class EditHandler(TextHandler):
	pass

class EditEventHandler(TextHandler):
	def duringParse(self, cString, args):
		e = args[1]

		command = cString["name"]

		joined = ' '.join(cString["args"])
		if joined and joined[0] == "#":
			try:
				joined = int(joined[1:])
			except IndexError:
				pass
			except TypeError:
				pass
		if command == "exit":
			events = args[0].events
			tr = e.pop("_TRIGGER")
			if tr not in events:
				events[tr] = []
			events[tr].append(e)
			self.releaseHandler()

		elif command == "trigger":
			e["_TRIGGER"] = joined

		else:

			setInDict(e, command.split("."), joined)


class Levels:
	#Enum for Permission levels.
	Normal, Builder, Elevated, Super = range(4)
	
	#Normal now equals 0, Builder = 1, etc.
class Player(EventEntity):

	"""
	Base class for all characters in the world. Exhibts the same interface as TextIO, such as send and receive. Has a name attribute that can be used to identify it.
	"""
	counter = 0
	def __init__(self, name, io):
		self.name=name
		self.aliases = []
		
		parts = name.split()
		self.aliases.append(parts[0])
		
		self.desc = "A plain, uninteresting person."
		self.room = None
		self.io=io
		
		EventEntity.__init__(self)
		
		self.npc = 0
		
		self.id = Player.counter
		Player.counter+=1
		
		self.inventory = []
		self.handlers = [["Main", None]]
		
		#If the player is an admin or super admin, then this attribute to be a higher level
		self.level = Levels.Normal
		self.messages = {
			"standing" : "is standing here.",
			"rooted": "{0} stares at you as you unsuccessfully attempt to grab onto them."
			}
	def look(self, player):

		return self.desc
	
	def setMessage(self, name, value):
		if name in self.messages:
			self.messages[name]=value

	def setDesc(self, desc):
		self.desc = desc
		
	def move(self, dir, quiet = False):
		r = self.room.exits[dir]

		if r:
			r.addPlayer(self, dir, quiet)

	def send(self, message):
		try:
			self.io.send(message)
		except Exception, e:
			print e
			raise SocketError
	def sendRaw(self, message):
		self.io.sendRaw(message)

	def receive(self, prompt=""):
		try:
			return self.io.receive(prompt).strip("\r\n")
		except Exception, e:
			print e
			raise SocketError
			
	def close(self):
		self.io.close()
		self.room.removePlayer(self, "void")
		
	def get(self, player):
		return False
	
	def getItem(self, name):
		name = name.lower()
		for i in self.inventory:
			if i.name.lower() == name or name in i.aliases:
				return i

		return None

	def toJSON(self):
		s = {"name":self.name, "desc":self.desc, "room":self.room.id, "inventory":[], "npc":self.npc, "level":self.level, "messages":self.messages, "aliases":self.aliases, "events":self.events}
	
		for item in self.inventory:
			s["inventory"].append(item.id)
		
		return s
		
	@classmethod
	def fromJSON(cls, s, cls2=None):
		#Let us pass in another class to use
		cls = cls2 or cls
		p = cls(s["name"], DummyIO())
		p.level = s["level"]
		p.desc = s["desc"]
		for i in s["messages"]:
			p.messages[i] = s["messages"][i]
		p.aliases = s["aliases"]
		
		p.events = s["events"]
		
		p.inventory = s["inventory"]
			
		return p

class NPC(Player):
	def __init__(self, name, io = DummyIO()):
		Player.__init__(self, name, io)
		self.npc = 1
		
	def close(self):
		self.io.close()
		#Don't remove us from the room after puppeting is over!
		
	@classmethod
	#PROBLEM BELOW
	def fromJSON(cls, s):
		p = Player.fromJSON(s, cls)
		p.npc = 1
		
		return p
		
def commandString(player, text):
	#function to take text input from the player and break it into a command name and arguments
	s = {"player":player, "name":"", "args":[]}
	if text:
		parts = text.split()
		if parts:
			s["name"]=parts[0]
			if len(parts) > 1:
				s["args"] = parts[1:]
	return s

def decodeWorld(string):
	playerS = string["players"]
	roomS = string["rooms"]
	itemS = string["items"]

	items = {}
	lastid = 0
	for i in itemS:
		s = itemS[i]
		i = int(i)



		if i > lastid:
			lastid = i

		item = Item.fromJSON(s)
		item.id = i
		items[i] = item

	Item.class_counter = lastid + 1

        #Define "fromJSON" method for Rooms, Players, Items
	
	rooms = {}
	for i in roomS:
		s = roomS[i]
		i = int(i)
		r = Room.fromJSON(s)
		r.id = i
		
		newitems = []
		for item in r.items:
			if type(item) == int:
				newitems.append(items[item])
				items[item].room = r
			else:
				newitems.append(Item.fromJSON(item))
		r.items = newitems

		rooms[i]=r
		
		for d in s["exits"]:
			r.exits[d] = s["exits"][d]
	
	lastid = 0
	for id, i in rooms.iteritems():
		if id > lastid: lastid = id
		for d in i.exits:
			#If there is a room in this direction
			if i.exits[d]:
				#Get the Room instance associated with that id
				i.exits[d] = rooms[i.exits[d]]
	
	Room.counter = lastid + 1
	
	lastid = 0
	players = {}
	for i in playerS:
		s = playerS[i]
		
		if s["npc"]:
			p = NPC.fromJSON(s)
		else:
			p = Player.fromJSON(s)
		
		
		p.id = int(i)
		
		if p.id > lastid: lastid = p.id
		
		newitems = []

		for item in p.inventory:
			if type(item) == int:
				newitems.append(items[item])
			else:
				#legacy
				newitems.append(Item.fromJSON(item))

		p.inventory = newitems

		r = rooms[s["room"]]
		p.room = r
		
		if p.npc:
			p.room.addPlayer(p)
		
		players[s["name"]] = p
	
	Player.counter = lastid + 1
	
	return rooms, players, string["login"], items

def encodeWorld(rooms, players, login, items = {}):
	playerS = {}
	itemS = {}

	for name, p in players.iteritems():
		s = p.toJSON()
		
		playerS[str(p.id)] = s
		

		
	roomS = {}
	for id, r in rooms.iteritems():
		s = r.toJSON()
		
		roomS[str(id)] = s

	for id, i in items.iteritems():
		itemS[str(id)] = i.toJSON()

	
	return {"rooms":roomS, "players":playerS, "login":login, "items":itemS}



commands = []

class Command(object):
	"""
	Base class for all commands. Subclass this in order to have your command be a viable command to run.
	"""
	def __init__(self):
		
		#Change this if this command should only be run by admins or super admins
		self.level = Levels.Normal
		self.aliases=[]
		
		#Change this to a list containing the scopes that this command can be run in
		#i.e. self.scope = ["Main", "Combat"]
		self.scope = ["Main"]
		
		self.doc = ""
		self.init()

		if not self.doc:
			self.doc = self.name+" <args>"
	def check(self, string):
		self.player = string["player"]
		if string["name"] ==self.name or string["name"] in self.aliases:
			if self.player.level >= self.level:
				error = self.run(string)
				if error == "format":
					if type(self.doc) == list:
						self.player.send("Please format your command like this:")
						for i in self.doc:
							self.player.send(i)
					else:
						self.player.send("Please format your command like this: '"+self.doc+"'")

			else:
				self.player.send("ERROR: Insufficient permissions")

			return True
		else:
			return False

	def run(self, string):
		pass

class LookCommand(Command):

	def init(self):
		self.name = "look"
		self.aliases=["examine", "x"]
		self.doc = "look or look <name> or look me"
	def run(self, string):
		args=string["args"]
		target = self.player.room
		if args:
			name = args[0]
			name = name.lower()
			newtarget = target.getEntity(name)
			if name == "me":
		
				newtarget = self.player
		
			if not newtarget:
				newtarget = self.player.getItem(name)
				if not newtarget:
					self.player.send("You can't see that!")
					return
				target = newtarget
			else:
				
				target=newtarget

		self.player.send(target.look(self.player))

class RunCommand(Command):
	def init(self):
		self.name="run"
		self.level = Levels.Super
		
	def run(self, args):
		args = args["args"]
		
		#Exec takes a string, and interprets it as python code. This command could potentially break a sever, so it is only accesible by super admins.
		exec(" ".join(args))

class MoveCommand(Command):
	def init(self):
		self.name = "move"
		self.aliases = directions.copy().keys()
		self.doc = ["move <dir>", "<dir>"]
	def run(self, string):
		args = string["args"]
		

		if string["name"] == self.name:
			if not args: return "format"
			dir = args[0]
			if dir not in self.aliases: return "format"
		else:
			dir = string["name"]

		self.player.move(dir)

class TakeCommand(Command):
	def init(self):
		self.name="take"
		self.aliases = ["grab","get"]
		self.doc = "take <name>"
	def run(self, string):
		args = string["args"]

		if args:
			target = self.player.room.getEntity(args[0])

			if target:
				item = target.get(self.player)

				if item:
					self.player.send("You picked up "+target.name+"!")
					target.trigger("get", self.player)
					self.player.inventory.append(target)
				else:
					self.player.send(target.messages["rooted"].format(target.name))

			else:
				self.player.send("You can't see anything called that...")
		else:
			return "format"
class DropCommand(Command):
	def init(self):
		self.name = "drop"
		self.doc = "drop <name>"
	def run(self, string):
		args = string["args"]
		
		if args:
			name = args[0]
			name = name.lower()
			item = self.player.getItem(name)

			if item:
				self.player.room.addItem(item)
				self.player.send("You drop "+item.name)
				self.player.room.broadcast(self.player.name+" drops "+item.name, self.player)
				self.player.inventory.remove(item)

			else:
				self.player.send("You don't have that!")
		else:
			self.player.send("Please supply the name of an item to drop!")

class UseCommand(Command):
	def init(self):
		self.name = "use"
		self.aliases = ["open","enter"]
	
	def run(self, string):
		args = string["args"]
		
		if args:
			name = args[0].lower()

			entity = self.player.room.getEntity(name)
			
			entity  = entity or self.player.getItem(name)

			target = None
			if len(args) >= 3:
				if args[1] == "on":
					name = args[2].lower()
					target = self.player.room.getEntity(name)
					if not target:
						target = self.player.getItem(name)

			if entity:
				entity.trigger(string["name"], self.player, target)
	
running = True

class StopCommand(Command):
	def init(self):
		self.name="stop"
		self.level = Levels.Super

	def run(self, string):
		#Say that when the variable "running" is referenced in this scope, reference the global variable instead.
		global running
		running = False

class ModCommand(Command):
	def init(self):
		self.name = "mod"
		self.aliases = ["op"]
		self.level = Levels.Super
		self.doc = "mod <player>"

	def run(self, string):
		if string["args"]:
			name = string["args"][0]
			
			for i in clients:
				if i.player.name == name:
					i.player.level = Levels.Elevated
					return
			
			self.player.send("No player found of name '%s'"%name)
		else:
			return "format"

class KickCommand(Command):
	def init(self):
		self.name = "kick"
		self.level = Levels.Elevated
		
	def run(self, string):
		args = string["args"]
		if args:
			name = args[0]
			
			for i in clients:
				if i.player.name == name:
					if i.player.level < self.player.level:
						i.quit()
					else:
						self.player.send("Can't kick someone with equal or higher privileges!")
					return
			
			self.player.send("No player found of name '%s'"%name)
		else:
			return "format"

class SayCommand(Command):
	def init(self):
		self.name = "say"
		self.aliases = ["talk"]
		
	def run(self, string):
		args = string["args"]
		if args:
			self.player.room.broadcast(self.player.name+' says "'+' '.join(args)+'"')


class BuildCommand(Command):
	def init(self):
		self.name = "build"
		self.aliases = ["create", "spawn"]
		self.level = Levels.Builder
		self.doc = ["build 'room' <direction> <name> <desc>", "build 'item' <name> [desc]"]
	def run(self, string):
		args = string["args"]
		if args:
			try:
				t = args[0]
				if t == "room":
					direction = args[1]
					
					if self.player.room.exits[direction]:
						if self.player.level < Levels.Elevated:
							self.player.send("Can't overwrite existing rooms!")
							return
					
					r = Room(args[2], ' '.join(args[3:-1]))
					self.player.room.addRoom(r, direction)
					#put in initializer? idk...
					rooms[r.id] = r
				elif t == "item":
					if len(args) > 2:
						i = Item(args[1], args[2])
					else:
						i = Item(args[1])
					
					self.player.room.addItem(i)
					items[i.id] = i

			except IndexError:
				return "format"


class ViewJSON(Command):
	def init(self):
		self.name = "json"
		self.aliases = ["inspect"]
		self.level = Levels.Builder
		
	def run(self, string):
		args = string["args"]
		if args:
			name = args[0]
			
			if name == "here":
				entity = self.player.room
			elif name == "self" or name == "me":
				entity = self.player
			else:
				entity = self.player.room.getEntity(name)
			
			if entity:
				self.player.send(json.dumps(entity.toJSON(), indent=4, sort_keys=True))

class EmoteCommand(Command):
	def init(self):
		self.name = "emote"
	
	def run(self, string):
		args = string["args"]
		if args:
			self.player.room.broadcast(self.player.name+" "+' '.join(args))
class TimeCommand(Command):
	def init(self):
		self.name = "@time"
		self.level = Levels.Elevated
	
	def run(self, string):
		self.player.send("The server has been running for {0} seconds.".format(t/100.0))
			

class PasswordCommand(Command):
	def init(self):
		self.name = "@password"

	def run(self, string):
		args = string["args"]
		if args:
			old = args[0]
			new = args[1]
			if old == new:
				self.player.send("Please choose a *different* password")
				return
			code = hashlib.md5(self.player.name+old).hexdigest()
			name = login[code]
			if name == self.player.name:
			
				newCode = hashlib.md5(self.player.name+new).hexdigest()
				#Below code could reveal a password... :/
				try:
					_ = login[newCode]
					Debug("MD5 has broken! Contact System Administrator! Hell on earth! Hell on Earth!")
					for c in clients:
						if c.player.level == Levels.Super:
							c.player.send("MD5 HAS BROKEN! ABORT! ABORT!")
					self.player.send("Congratulations! You have performed a cryptographic miracle!")
					self.player.close()
				except KeyError:
					login[newCode]=self.player.name
					_ = login.pop(code, None)
			else:
				self.player.send("Incorrect old password!")

class WhoCommand(Command):
	def init(self):
		self.name = "who"
		
	def run(self, string):
		self.player.send("The following players are online:")
		for c in clients:
			if c.player.name != "_LOGIN":
				self.player.send(c.player.name)				

class HelpCommand(Command):
	def init(self):
		self.name = "help"
		self.aliases = ["?"]
		self.scope = "all"
		self.level = -1
		
	def run(self, string):
		args = string["args"]

		if args:
			name = args[0]

			self.player.send("I'll get to making a good help system eventually...")

			for c in self.handler.commands:
				if c.name == name or name in c.aliases:
					self.player.send(c.name[0].upper()+c.name[1:])
					if type(c.doc) == list:
						for i in c.doc:
							self.player.send(i)

					else:
						self.player.send(c.doc)
					break
		else:
			self.player.send("Available commands:")
			for name in self.handler.commands:
				
				self.player.send(name.name)

class BackupCommand(Command):
	def init(self):
		self.name = "backup"
		self.scope = "all"
		self.level = Levels.Elevated
		self.doc = "backup <filename>"
		self.blacklist = ["main.py", "world.json", "worldTest.json"]

	def run(self, string):
		args = string["args"]

		if args:
			filename = args[0]
			if filename in self.blacklist:
				self.player.send("You can't overwrite that file!")
				return
			else:
				Debug("Backing up world to "+filename)
				f = open(filename, "w")
				json.dump(encodeWorld(rooms, players, login, items), f, sort_keys = True, indent = 4)
				f.close()
				Debug("World backed up!")
				self.player.send("World saved!")
		else:
			return "format"

class EditCommand(Command):
	def init(self):
		self.name = "edit"
		self.scope = ["Main"]
		
		
	def run(self, string):
		args = string["args"]

		if args:
			name = args[0]
			target = None
			if name == "me":
				target = self.player
			else:
				if self.player.level >= Levels.Builder:
					if name== "here":
						target = self.player.room
					else:
						target = self.player.room.getEntity(name)
				else:
					self.player.send("If you're not a builder, you can only edit yourself!")
					return False

			if target:

				self.handler.requestHandler("Edit", target)
			else:
				self.player.send("You don't see that!")
		else:
			return "format"

class EditNameCommand(Command):
	def init(self):
		self.name = "name"
		self.scope = ["Edit"]
		self.level = Levels.Builder

	def run(self, string):
		args = string["args"]

		if args:
			newname = args[0]
			Debug("newname = "+newname)

			Debug("Editing name!")

			Debug("handlerArgs = "+str(self.handler.handlerArgs))

			self.handler.handlerArgs.name = newname

class EditDescCommand(Command):
	def init(self):
		self.name = "desc"
		self.aliases = ["describe", "description"]
		self.scope = ["Edit"]

	def run(self, string):
		args = string["args"]

		#If we're editing an externa; object
		if self.handler.handlerArgs != self.player:
			if self.player.level < Levels.Builder:
				self.player.send("You can't edit the description of anything other than yourself!")
				return False


		if args:
			if args[0] == "a+" and len(args) > 1:
				newdesc = self.handler.handlerArgs.desc + ' '.join(args[1:])
			else:
				newdesc = ' '.join(args)

			self.handler.handlerArgs.setDesc(newdesc)

class EditRootCommand(Command):
	def init(self):
		self.name = "root"
		self.level = Levels.Builder
		self.scope = ["Edit"]

	def run(self, string):
		if type(self.handler.handlerArgs) != Item:
			self.player.send("Only Items can be rooted!")
			return False

		args = string["args"]

		if args:
			self.handler.handlerArgs.rooted = int(args[0])
		else:
			self.player.send("entity.rooted = "+str(self.handler.handlerArgs.rooted))

class EditMessageCommand(Command):
	def init(self):
		self.name = "message"
		self.aliases = ["msg"]
		self.level = Levels.Builder
		self.scope = ["Edit"]
		self.doc = "message <name[.subname]> <value>"

	def run(self, string):
		args = string["args"]

		if len(args) > 1:
			self.handler.handlerArgs.setMessage(args[0], ' '.join(args[1:]))
		else:
			return "format"

class EditEventCommand(Command):
	def init(self):
		self.name = "event"
		self.level = Levels.Builder
		self.scope = ["Edit"]
		self.doc = "event [verb]"

	def run(self, string):
		args = string["args"]
		if args:
			verb = args[0]
		else:
			verb = "display"
		try:
			template = Events[verb]
		except AttributeError:
			template = Events["display"]
		template["_TRIGGER"] = "use"
		self.handler.requestHandler("EditEvent", (self.handler.handlerArgs, template))

class EditAliasesCommand(Command):
	def init(self):
		self.name = "aliases"
		self.aliases = ["alias", "al"]
		self.scope = ["Edit"]
		self.level = Levels.Builder

	def run(self, string):
		args = string["args"]

		if args:
			for i in args:
				if i not in self.handler.handlerArgs.aliases:
					self.handler.handlerArgs.aliases.append(i)

class EditExitCommand(Command):
	def init(self):
		self.name = "exit"
		self.scope = ["Edit"]

	def run(self, string):
		self.handler.releaseHandler()

class TeleportCommand(Command):
	def init(self):
		self.name = "teleport"
		self.aliases = ["tp"]
		self.level = Levels.Builder

	def run(self, string):
		pass

'''
class TestCommand(Command):
	def init(self):
		self.scope = ["Test"]
		self.name = "test"
		
	def run(self, string):
		Debug("Running Test")
		self.player.send("You did a test thing in the test handler!")
	
class TestEnterCommand(Command):
	def init(self):
		self.name = "test"
	
	def run(self, string):
		Debug("Running TestEnter")
		self.handler.requestHandler("Test", "foo")
		
class TestExitCommand(Command):
	def init(self):
		self.name = "exit"
		self.scope = ["Test"]
		
	def run(self, string):
		Debug("Running TestExit")
		self.handler.releaseHandler()
'''

for i in Command.__subclasses__():
	#Create a list of all subclasses of Command
	commands.append(i())

def Log(string):
	Log.logfile.write(string+"\r\n")

def Debug(string, log=False):
	#A function for logging events to the server, with a timestamp. The timestamp is in seconds since the server launched
	print("["+str(t/100)+"] "+string)
	if log:
		Log(string)



class PlayerThread(Thread):
	"""
	A thread that is dispatched to deal with incoming connections, retreive a saved player, and interpret the client's commands
	"""
	def __init__(self, player):
		Thread.__init__(self)
		self.player = player

		self.commands = []
		
		
		
	def run(self):
		if self.player.name == "_LOGIN":
			#Either retrieve an existing player, or create a new one
			Debug("Getting login information")
			try:
				new = False
				self.player.send(world["data"]["motd"])
				self.player.send("Enter your Character name! (type 'new' to make a new character)")
				name = self.player.receive(">")
				if name == 'new':
					new = True
					self.player.send("Pick a name for your character! This is permanent, so choose wisely!")
					name = self.player.receive(">")
					if name == 'new':
						self.player.send("Invalid name!")
						self.player.close()
						return
					for _, i in login.iteritems():
						if name == i:
							self.player.send("Name already taken! Kicking from server!")
							self.player.close()
							return
					
					self.player.send("Pick a password! (This can be changed later)")
					password = self.player.receive(">")
				else:
					self.player.send("Enter your password!")
					password = self.player.receive(">")
				
				code = hashlib.md5(name+password).hexdigest()
				oldIO = self.player.io
				"""
			try:
				self.player.send("Please enter your login code! (If you haven't made a character yet, enter the code '0000')")
				code = self.player.receive(">")
				
				oldIO = self.player.io
				
				new = "0000"
				
				if code == new:
					self.player.send("Enter a character name")
					name = self.player.receive(">")
					
					try:
						temp = players[name]
						self.player.send("Name already taken! Kicking from server!")
						self.player.close()
						return
					except KeyError:
						players[name] = self.player
						
						self.player.name = name
						newCode = ""
						while True:	
							self.player.send("Choose a login code! This will act as your usernmame/password to access your character, so keep it safe!")
							newCode = self.player.receive(">")
							if not newCode in login.keys():
								break
							self.player.send("Code already taken! Please try again!")
							
						code = newCode
						login[code] = name
					"""
				if new and code not in login:

					login[code] = name
					players[name] = Player(name, oldIO)
				try:
					Tplayer = players[login[code]]
					Debug("Tplayer.npc = "+str(Tplayer.npc))
					Debug("type(Tplayer) = "+str(type(Tplayer)))
					for c in clients:
						if c.player == Tplayer:
							self.player.send("That player is already logged in!")
							self.quit()
							Tplayer.send("[Another client has attempted to log into your account! It is reccomended that you change your password with @password]")
							return
					self.player = Tplayer
					if type(self.player) == NPC:
						#They've tried to login as an NPC
						#Only allow this from the same computer
						Debug("Puppeting attempt at NPC: "+self.player.name+", from "+str(oldIO.sock.getpeername()))
						if oldIO.sock.getpeername()[0] != '127.0.0.1':
							raise KeyError
						Debug("NPC being puppeted!")
					self.player.io = oldIO
				except KeyError:
					oldIO.send("Invalid code! Kicking from server!")
					self.quit()
					return
			except SocketError:
				Debug("Client had a socket problem!")
				self.quit()
				return
		if not self.player.room:
			Debug("Setting player.room to default of 'spawn'!")
			spawn = rooms[world["data"]["spawn"]]
			self.player.room = spawn
			spawn.addPlayer(self.player, "void")
			
		else:
			if type(self.player) == Player:
				Debug("Player.room is equal to "+str(self.player.room))
				self.player.room.addPlayer(self.player, "void")
		
		self.player.trigger("start", self.player)
		for i in self.player.inventory:
			i.trigger("start", i)
		Debug("Entering loop!")
		while running:

			

			try:
				msg = self.player.receive()
			except SocketError:
				self.quit()
				break
			#msg = raw_input("_")
			msg = commandString(self.player, msg)

			if msg["name"] == "quit":
				self.quit()
				break
			'''

			level = "main", "combat", "edit", etc...

			Handler.requestHandler(h):
				oldHandler = player.Handler
				player.handler = h
				h.parent = oldHandler

			Handler.releaseHandler():
				player.handler = player.handler.parent



			Event.put([player, level, msg])
			'''
			
			Event.put((msg, self.player.handlers[-1]))

			"""		
			for i in self.commands:
				try:
					if i.check(msg):
						break
				except Exception, e:
					Debug(str(e))
					self.player.send("There was an error completing that command!")
			"""
			#print "[Player] Ticked!"
		
		#clients.remove(self)
		Debug("Player left!")
		
	def quit(self):
		try:
			self.player.send("Goodbye!")
		except:
			pass
		
		try:
			self.player.close()
		except Exception, e:
			Debug("Couldn't close player! : "+str(e))
		
		clients.remove(self)

clients = []
			
class ServerThread(Thread):
	"""
	Thread that listens in the background for incoming connections
	"""
	def __init__(self, host='', port=9000):
		self.host = host
		self.port = port
		Thread.__init__(self)

	def run(self):
		self.connections = 0
		
		#Initialize the server
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		
		self.host = ''
		if len(sys.argv) > 2:
			self.port = int(sys.argv[2])
		
		connect = (self.host, self.port)

		Debug("Binding Server to %s : %i"%connect)
		
		self.server.bind(connect)
	
		#Begin listening for connection. The '10' means that up to 10 connections can be held in a buffer while we deal with one.
		#This should be more than sufficient, as I'm not expecting high traffic, and the following process shouldn't take very long because a new thread is spawned.
		self.server.listen(10)
		
		Debug("Ready to accept connections!")
		while running:
			clientSocket, addr = self.server.accept()
			
			Debug("Got a connection from "+str(addr)+"!", True)
			
			IO = SocketIO(clientSocket)
			
			#Create a temporary player with the name "_LOGIN", to prompt login actions
			#This player will eventually be replaces by a retrieved or newly created player
			clientPlayer = Player("_LOGIN", IO)

			pt = PlayerThread(clientPlayer)
			
			#If the main thread crashes, don't let the player threads keep the process running 
			pt.daemon = True
			
			pt.start()
			
			clients.append(pt)
			
			self.connections+=1


if __name__ == '__main__':
	
	filename = ""
	try:filename = sys.argv[1]
	except:pass

        if not filename:
                filename = raw_input("What world file should I load? (world.json): ")
                if filename:
                	if not ".json" in filename:
                		filename+=".json"

                filename = filename or "world.json"
	f = open(filename, "r")
	f2 = open(filename.strip(".json")+"Backup.json", "w")
	f2.write(f.read())
	f2.close()
	f.seek(0)
	world = json.load(f)
	rooms, players, login, items = decodeWorld(world)
	f.close()

	Log.logfile = open(str(time.time()) + "LOG.txt", "a")

	timers = []

	for index, r in rooms.iteritems():
		r.trigger("start", r)
		for i in r.items:
			i.trigger("start", i)
			
	#Directions we're letting our NPC move 
	dirs = ["west","east","north","south","up","down"]

	Event = Queue()

	server = ServerThread()

	server.daemon = True

	#Start the listening thread
	server.start()

	handlers = {}
	
	for h in TextHandler.__subclasses__():
		hI = h()
		handlers[hI.name]=hI
		
	while running:
		
		
		try:

			for timer in timers:
				if timer.tick():
					timers.remove(timer)


			#if random.randint(0, 1000) == 0:
				#Move the NPC
				#Debug("Decided to move!")
				#dir = random.choice(dirs)

				
				#players["Adam"].move(dir)

			try:
				#Debug("Getting event!")
				event = Event.get(False)
				command = event[0]
				handler = event[1]


				Debug("Command string of "+str(command))
				Debug("Handler of "+str(handler))
				
				Debug("Got Event!")

				if command:
					Debug("Attempting to parse!")

					handlers[handler[0]].parse(command, handler[1])
			except Empty:
				pass

			try:
				time.sleep(0.01)
			except KeyboardInterrupt:
				raise Stop
				
			if t%100 == 0:
				#If a second has passed, log a debug message to let us know that the main thread is still running 
				Debug("Tick!")
			t+=1
		
		except Exception, e:
			Debug(str(e))
			running = False
			break

		
	
	Debug("Saving world!", True)
	
	f = open(filename, "w")
	d = encodeWorld(rooms, players, login, items)
	d["data"] = world["data"]
	s = json.dumps(d, indent = 4, sort_keys = True)
	f.write(s)
	f.close()

	Log.logfile.close()
	
	Debug("Goodbye!")
