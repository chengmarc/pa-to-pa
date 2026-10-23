# persuadee-personas

One file per principal persona, `p_01.md`, `p_02.md`, ...; a run plays one game per file, so fewer files make faster
runs. The whole file goes into the persuadee's prompt in tier `t2_secretary`, so it holds only the persona: no
heading, no ids, no prices. A persona changes style and preferences, never the floor (`price_L`), which comes from the
scenario.

`index.csv` has each persona's traits for analysis: cohort (NA/CN), loss aversion and risk attitude (the moderators),
conflict style and time pressure. A row without a file is ignored. In the full set of 45 drafts, every loss aversion ×
risk attitude pair appears 5 times.

**The current files are synthetic drafts**, so the pipeline can be tested. They are to be replaced by the
de-identified profiles extracted from the interviews; keep `index.csv` in step.
