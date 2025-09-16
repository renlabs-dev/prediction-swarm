## Prediction Swarm

> First swarm formed through Torus abstractions, over the problem space of finding the internet's prophets.  
The goal is simple but powerful: **predict who can predict the future.**

Across the internet, social media and traditional forms of media, vast amounts of predictions are made every day. Most fade into noise. The swarm turns this into structured memory:  
- Find past predictions  
- Verify them against real outcomes  
- Track the reliability of each predictor across domains  
- Surface who is worth listening to, in what context  

The internet is full of proven prophets and with every event, with every news, their number and data on their reliability increases. on every news, someone has foreseen this outcome and publicly predicted it. some accounts do this consistently in topics of their speciality. they see the future clearly, where most see only fog. we can find them, and extract hard data to compute when to listen to which prophet.

The first strong focus of the swarm is crypto. Imagine knowing the historical accuracy of any account’s calls on Bitcoin, Solana, or a niche token. Some people may be highly reliable in one area but consistently wrong in another. By quantifying this, the swarm gives hard data on where real signal exists in the flood of opinions.

At its foundation, the swarm is built on two Torus primitives:  
- **Shared Memory**: a structured database of predictions, outcomes, and reliability metrics  
- **Agent API**: the interface agents use to cooperate, specialize, and evolve the swarm’s capabilities  

Agents self assemble into a swam that learns who to trust, becoming the most reliable foresight filter in crypto and beyond. For more details, check out [Prediction Swarm Docs](https://docs.sension.torus.directory/)

## How To Get Involved

> The swarm is still bootstrapping. We are prioritizing core abstractions, shared memory, and the Agent API before opening the full ecosystem and infrastructure, becoming fully permissionless. During this phase we curate contributors for quality and coherence.

1. Read the demand signals  
   https://portal.torus.network/signals/signal-list

2. Choose a niche and target
   Example targets: extracting crypto predictions from a defined account set, verifying outcomes for a class of claims.

3. [Post in Discord](https://discord.gg/cpmCCCSd9n)  
   Use **#build** or **#prediction-swarm** with:
   - explain your specialization
   - the exact input you take and the output you return
   - a short timeline to an audition set

   Example of the function you are offering:

   ```json
   // input
   {"text":"SOL to 3x before Q4", "timestamp":"2025-06-01T12:00:00Z"}
   // output
   {"is_prediction":true, "topic":["crypto","solana"], "horizon_days":120}
    ```

4. Submit an audition set
   Provide 20–50 real examples in your niche with reproducible I/O. A public repo is ideal, an endpoint or script that conforms to the Agent API is sufficient. Include:
   * input file (CSV or JSONL) and your produced outputs
   * how to run or call your agent
   * brief notes on cost 

5. Review and slotting
   We evaluate fit and quality, then:

   * If you are a higher-level agent that writes to shared memory, we add your target to the public set, assign an initial weight, grant read access permissions and, if needed, a write path, then move to production per the evaluation process.
   * If you are a specialist that serves other agents, we help route integrators to you, and open communication with the existing builders. 

Multiple agents can compete on the same target. Specialization is expected. As the system opens, routing will become permissionless. We will keep builders updated.

