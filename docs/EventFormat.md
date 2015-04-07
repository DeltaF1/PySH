<h1>Events</h1>

Events are pieces of data that are interpereted as code by PySH, and are used to script behaviours for any object that is a subclass of <i>EventEntity</i>.
Each <i>EventEntity</i> has a dictionary of events, indexed by <i>trigger</i>. Some triggers, such as *use* and *enter* are triggered by events in the game's code, but you can write your own that can be triggered by other events.

<h1>What do they look like?</h1>

<h2>Basic Structure</h2>
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

<h3>Verb</h3>
The verb is what action the event should be doing. The verbs currently supported are:
<ul>
	<li>Display : Send text</li>
	<li>rigger : Trigger another event</li>
	<li>Create  : Spawn a copy of an Item</li>
	<li>Teleport: Moves an entity, either in a direction, or to a specific room</li>
</ul>