

Regarding the Opportunity Party:
- [ ] Manually review the quality of the SSG at this stage
- [ ] Apply the tasks from prd once the youtube approach is validated
- [ ] Consider context-mode on the repository

**Manually review the quality of the SSG at this stage**

* Overall the formatting is good. Just the links for 

Personal:

- [ ] Create a board to manage all the links to many of my pages I click through
- [ ] Set this up behind a tailscale configuration that only I can access



One thing I am really struggling with is the code architecture. I am starting to notice splits in the codebase which is based on the fact I have not set clear policy expectations around the structure of data. From Starboard days, there are a few concepts which come to mind:

* The meldeon architecture.
* Dagster.io to manage data as assets.
* Using plain files to represent stages really well.


I want to:

* [ ] Implement Dagster.io to manage data ETL pipelines as a view.
* [ ] Create policies regarding the structure of data. Use a formal architecture to describe this.
* [ ] Get Back to capturing core problems faced before. Youtube importer, 


Other things:

- [ ] MCP for astro-docs.
- [ ] How does agents work with Dagster?
- [ ] Validate documents adhere to a formal policy specification
- [ ] pre-commit ci validation for site/ this should be on changes. pnpm + python


This could be enforced from AGENTS.md

Policy specifications are listed: `docs/` which represent the current state of the system. Ensure test cases cover the assertions made in the policy documents where feasible. We aim to ensure our project documents the core aims and specifications we aim to deliver on.

Any future work should be provided under `plans/` while the specifications or user-stories are being developed. Any plans which been completed should end up under `plans/archive` as to not interfere with future work which is being considered. The README.md should cover what is currently in the repo as of 



