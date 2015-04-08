#Events

Events are pieces of data that are interpereted as code by PySH, and are used to script behaviours for any object that is a subclass of *EventEntity*.
Each *EventEntity* has a dictionary of events, indexed by *trigger*. Some triggers, such as **use** and **enter** are triggered by events in the game's code, but you can write your own that can be triggered by other events.

#What do they look like?

##Basic Structure

````json
{
"verb":"display",
"data":{     
		"text":"Test!"
	},
"target":"user",
"destroy":false 
}
````

###Verb
The verb is what action the event should be doing. The verbs currently supported are:

* Display : Send text
* rigger : Trigger another event
* Create  : Spawn a copy of an Item
* Teleport: Moves an entity, either in a direction, or to a specific room
