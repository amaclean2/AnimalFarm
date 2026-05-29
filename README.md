# Agents meet needs

## Agents are mobile

Agents can move around their world and explore their surroundings. They have a simple understanding of their environment. They can see and make decisions about the things around them. Agents can't move over each other. If two run into each other, then they make a decision to go around each other. There's water in the world that the food tends to grow around, but agents are worse at moving in the water than on land so they use up energy more quickly.

### How agents navigate

Agents use A* pathfinding to reach their current goal. When planning a path, A* treats all currently occupied tiles as blocked, so agents naturally route around each other rather than through them.

If an agent's next planned step is taken by the time they move (another agent got there first), they replan A* immediately on the same tick using the updated occupied set. If both attempts fail — the agent is fully surrounded — a deterministic tiebreaker resolves the deadlock: agents alternate waiting vs. advancing each tick based on their ID and the current tick count, so two blocked agents don't mirror each other indefinitely.

Agents are processed hungriest-first each tick, so the most food-deprived agents claim tiles before others plan around them.

## Agents are fed

### V1

There is food in the world. Agents can navigate around and gather food where they find it. Once they have established a home, they carry food back to stockpile it there rather than eating it on the spot.

#### How food spawns

Food grows in clusters near rivers. When a food item is consumed, a new one regrows after a delay, scattered near the consumed tile using a Gaussian distribution — biased toward water and existing food clusters, never on river tiles. Rivers kill food as they flow over it.

#### How agents find food

Agents see food within their vision range. When food is visible, they navigate toward the nearest item. When no food is in range, they remember the last food they saw and return to that location. If memory is exhausted too (they arrived and found nothing), they fall back to random exploration.

#### Eating vs. stockpiling

Before an agent has established a home, stepping on food restores health to full immediately. Once an agent has a home, it picks up food and carries it back rather than eating in place. Dropping food at home counts as eating and restores health to full.

#### How hunger affects priorities

Agents weigh tasks by urgency. A hungry agent (below 80% health) treats food as high priority. A sated agent (above 80%) still seeks food but at lower priority — other tasks like mating can compete. A desperate agent (below 50% health) ignores mating entirely and focuses only on food. These thresholds shift the relative pull of food vs. social goals without hard-switching between states.

### V2

**Dependent on predator/prey model**

Food can be hunted and gathered. Each item of food contains different caloric values and are different difficulties to obtain. Finding and stalking prey is going to be more difficult and more rare than finding some berries in a bush. The berries don't satisfy as well as a hunted prey will, though.

## Agents are rested

### V1

Agents have an amount of energy that lasts them roughly one day. When they run out of energy they go to sleep and stand still for a few frames to rest. Once they've rested, they can continue gathering food.

### V2

**Dependent on social behavior**

Agents have different predilections for activities at different times of the day. First thing in the morning agents will want to get up and eat, then work on their tasks for the day whether it's hunting prey, foraging, or working on their shelter or any of their other tasks. In the afternoon, they want to gather and satisfy social desires, before going to sleep. The agents develop community patterns.

## Agents aren't thirsty

### V1

Agents don't have a good way to gather water so they need to make frequent stops to get a drink. Throughout the day agents get thirsty and need to find a source of water to refresh themselves.

### V2

Agents establish ways to gather and hold onto water, but also find more things to do with the water. They use it to prepare food, build better shelters as well as consume it.

## Agents are healthy

There's a chance agents can get sick from their food, water, or other agents. In this case, agents ability to rest decreases dramatically and if they are completely depleated, they can die

## Agents are warm

## Agents aren't injured

## Agents are safe

There are predators in the world and agents have to establish patterns and defenses to avoid them
