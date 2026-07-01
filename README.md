## GAME DESCRIPTION:
The players of this game are placed in a maze with enemy AI referred to as ghosts. Players must escape this maze while avoiding the ghosts. If a player is captured by a ghost, the player can no longer continue the game. The game will end when either all remaining players have escaped or all players have been captured. 
<br>
<br>
There are two roles a player can have at the start of the game: <br>
1. **The spiritualist** can see where the ghosts are, but cannot see the maze layout. <br>
2. **The explorer** can see the maze layout and where the exit is, but cannot see where the ghosts are. <br>
Both roles have the ability to see the players. The explorer and spiritualists must guide each other to reach the exit.<br>
<br>
If a player gets caught or escapes, they will be in spectator mode for the rest of the game, and will be able to see both the maze walls and ghosts, but cannot move.
<br>
<br>
The mazes are completely randomly generated.  A chat feature is implemented to help the players with communication. After the game ends, all players are returned to the lobby
<br>
<br>
<br>
<br>

## HOW TO RUN:

(run clients and servers in separate terminals)

**1. Run Server:** `py -m server.server`

<br>

**2. Run Client(s):** `py -m client.app`
