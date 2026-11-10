I wanted to make a networking website for all of the Jesuit highschools in America. I asked Claude “Is it too complicated to make a mock networking website for the jesuit secondary schools in the US. There are 60 schools according to wikipedia. Do you want more details yet or should we just begin going through the instructions?”  This became a taller task than expected, so for the beginning of this website it has become more of a news forum for the schools. As an alumni myself I have noticed that these schools do not have a place where all their information can be found, it is instead scattered among their respective websites. My beginning prompt to claude was this “The site is run by the Jesuit Schools Network director Jennifer LaMaster  with subsequent editors for each highschool. The editors from the highschool will be the head of alumni relations- for example Fordham Prep’s would be JP Feighery. Jennifer would have a tech team running under her as she is a the head of a big organization, so she will just oversee but the highschool editors are able to make bloglike posts on their own schools and approve alumni to join. Alumni from the jesuits schools will be reading the posts and can even reach out to alumni from the other schools. Content for these schools is scattered across a bunch of social media or hidden on the schools newspage. This gives the jesuit network a chance to connect not only with their classmate but those who share a similar education and interest in jesuit education. An editor at one school should not be able to delete other schools pages. The editors should not be able to approve or deny alumni from other schools from joining their portal once approved by their home school.”  Claude began asking me more questions about the site in our grill me session. We realized we could break this project up into eight separate tickets and began running through each. I used Sonnet 5.5 on medium for the entire project. As we got into the tickets (#2-#9), I used the skills “/implement and /code-review” to make sure each phase ran smoothly. It was going well and the private site was available. However, when I tried to log into the site I ran into errors saying that the login was incorrect, this was because Claude seeded the real cms.db with throwaway passwords using the wrong environment variable name. We only found this after all test passwords did not work. Claude checked the stored hashes against the throwaway passwords and they matched, so the database itself was fine but held the wrong passwords. So I decided that we should sign in with these different passwords instead of reseeding, and the server had not been running, so we started it and it worked. The proper fix, deleting cms.db and reseeding it with the right environment file, is still not done. To improve this site in the future I would love to have an interactive map of the United States where you could click into a specific school and see their news/alumni. I think there is a great opportunity to allow for networking across these schools since the alumni often share the same values and education. 

Other problems I ran into included a “form bug”, specifically in ticket T05 where a find-and-replace method turned `method="post"` into `method="page"` in the Page form, so Claude added a new test for that. Later on when running tests, some tests passed without checking anything and in a review we caught it, so they rewrote them as a link crawl. At the end there was a Broken link that caused the console header linked to a 404 page, so we had to fix that also. One more time Claude was wrong: on 2026-10-15, before the first deploy, it told me it had checked that “Jennifer LaMaster” was not in the published pages, but it had not run that check. It corrected itself about eight seconds later, ran the check, and found no real names on the site.

Some skills that I used that helped me throughout this project include: /setup-matt-pocock-skills, /ask-matt, /research, /grill-with-docs, /to-spec, /to-tickets, /implement (every ticket from #2), /code-review. Grill with docs is where the scope of the project got decided. For example during this I discussed with claude to only allow the editor to edit their school and see updated posts only. I noticed that I should not just agree with claude during this and would ask questions throughout. Code-review was also important because it allowed us to not run into as many problems as we routinely checked the session. 

My token budget plan (notes/token-budget-plan.md) expected about 12% of a 5-hour window per ticket and put the grill, spec and tickets on Opus. The ledger (notes/usage-ledger.csv) shows I ran everything on Sonnet 5.5, tickets T01-T07 cost 1-2% of a window each, and T08 cost 31% over 75 turns. The T08 number also includes the submission work, because the phase label was never changed after T08. The average cost was 1.0% of the weekly limit per ticket, so my estimates were far too high.

Down below is the table with my usage and models: 

Backends used

| Provider | Model | Used for | Backup provider |
|---|---|---|---|
| Anthropic | Sonnet 5.5 (`claude-sonnet-5-5`) | All sessions | None |

Usage by phase (from notes/usage-ledger.csv)

| Phase | Turns | 5-hour window spent | Weekly spent | Model |
|---|---|---|---|---|
| grill | 7 | 1.0% | 0.0% | Sonnet 5.5 |
| spec | 3 | 1.0% | 0.0% | Sonnet 5.5 |
| tickets | 3 | 1.0% | 1.0% | Sonnet 5.5 |
| T01 | 4 | 2.0% | 0.0% | Sonnet 5.5 |
| T02 | 3 | 1.0% | 0.0% | Sonnet 5.5 |
| T03 | 4 | 1.0% | 0.0% | Sonnet 5.5 |
| T04 | 3 | 2.0% | 0.0% | Sonnet 5.5 |
| T05 | 6 | 2.0% | 1.0% | Sonnet 5.5 |
| T06 | 6 | 2.0% | 0.0% | Sonnet 5.5 |
| T07 | 5 | 2.0% | 0.0% | Sonnet 5.5 |
| T08 | 75 | 31.0% | 7.0% | Sonnet 5.5 |
| unlabelled | 29 | 8.0% | 1.0% | Sonnet 5.5 |
