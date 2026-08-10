## Core mechanism: tabular Q-learning

- State: an agent's situation, grouped into a fixed set of buckets
- Current action choices: `drink`, `eat`, `harvest_food`, `sleep`, `seek_water`, `seek_rest`, `explore`, `mate`.
- The table, `Q(state, action)`, stores one number per state-action pair: how good that action is currently believed to be in that state.
- Reward calculation: `-(change in hunger + change in thirst + change in rest deficit + change in temperature deviation)`, computed after each action.
- Update, applied to the entry for the state and action just used: `Q(state, action) += learning_rate * (reward + discount * best_next_Q - Q(state, action))`.
  - `learning_rate`: how much one new experience shifts the stored value.
  - `discount`: how much a future reward counts compared to an immediate one.
  - `best_next_Q`: the highest table value available in the state the agent ends up in after acting.
- Action choice: for the current state, pick whichever available action has the highest table value. Some fraction of the time, given by `epsilon`, pick a different available action at random instead, to keep trying alternatives.

## Initialization: start from instinct, not zero

Initialize each agent's Q-table from the existing hardcoded urgency formulas in `urgency.py` instead of zero.

## Genome hooks

- `learning_rate`, `discount`, and `epsilon` (how often an agent takes an action other than its current highest-value one, to keep trying alternatives) become genes, not constants.
- Evolution tunes how fast and how far-sighted learning is, across generations. Within a life, the update rule above runs on top of whatever values an agent inherited.
- Tension to resolve: `design_skill_gain_variance` deliberately kept skill gain noise-driven rather than a heritable `learning_rate` gene, for a different mechanism (harvest skill). Confirm this new learning-rate gene is scoped to the reinforcement-learning system, not retroactively applied to skill gain.

## State scale

Bucketed state keeps the table sparse and small per agent regardless of world size. A 100x100 world doesn't mean 10,000 table entries, just however many distinct state buckets an agent has actually visited, capped the same way `Memory.cap` already bounds remembered positions (`agents/memory.py`).
