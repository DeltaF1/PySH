<h1>Events</h1>

Events are pieces of data that are interpereted as code by PySH, and are used to script behaviours for any object that is a subclass of <i>EventEntity</i>.
Each <i>EventEntity</i> has a dictionary of events, indexed by <i>trigger</i>. Some triggers, such as *use* and *enter* are triggered by events in the game's code, but you can write your own that can be triggered by other events.

<h1>What do they look like?</h1>

<h2>Basic Structure</h2>
````json
{
"verb":"display", #Action to be taken
"data":{     
		"text":"Test!" #Additional data for the event
	},
"target":"user", #The object this event acting upon
"destroy":false #Whether this event should self destruct once fired
}
````

<h3>Verb</h3>
The verb is what action the event should be doing. The verbs currently supported are:
-Display : Send text
-Trigger : Trigger another event
-Create  : Spawn a copy of an Item
-Teleport: Moves an entity, either in a direction, or to a specific room 