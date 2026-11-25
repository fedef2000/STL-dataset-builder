# Paraphrasing STL descriptions with TextAttack: a trial
## In short

TextAttack is not a good way to paraphrase our descriptions. Its word-level methods (wordnet, embedding, eda) mostly produce broken or odd English, and the judge doesn't filter that out: it checks whether a paraphrase still matches the formula, not whether it is good English. Read by hand, only about a third of the paraphrases the judge calls correct read as natural English (about 25 of 74), and back-translation gives the largest share of them (about 11). Back-translation writes fluent sentences, but it rewrites the whole sentence, so it can't be told which words to keep, and it sometimes alters numbers and names. Even the good paraphrases change only one or two words, so they add little variety.

## The four methods

| Method | What it does |
|---|---|
| wordnet | replaces about 10% of the words with a synonym from WordNet, a general-purpose English thesaurus. |
| embedding | replaces about 10% of the words with a nearby word in a word-embedding space (vectors trained to keep synonyms close and antonyms apart), only if it is very similar (cosine similarity at least 0.8). |
| eda | Easy Data Augmentation: one random operation on about 10% of the words: replace with a WordNet synonym, delete, swap two words, or insert a synonym of some word at a random place. |
| backtranslation | translates the sentence into Spanish and back into English with a machine-translation model (MarianMT), so the whole sentence is rewritten. |




## Major problems

In the examples, **bold** marks the words the method put in and ~~struck~~ the words it removed.

### 1. Synonyms from the wrong meaning

WordNet and EDA take a synonym from any meaning of a word, not the one in the sentence. The formula is still matched, so the judge says correct: the judge doesn't catch this problem.

| Formula | Original | Paraphrase | Judge |
|---|---|---|---|
| `safe U[0,240] (G[0,10] target)` | the robot must satisfy each safety boundary with 99% confidence until it achieves each target boundary with 95% confidence within 240 time instants and stays in the target for 10 time instants | the robot must satisfy each ~~safety~~ **condom** boundary with 99% confidence until it achieves each target ~~boundary~~ **edge** with 95% ~~confidence~~ **trust** within 240 time instants and stays in the target for 10 time instants | correct (third model) |
| `G[0,inf] (detect_motion -> (F[0,10] activate_alert))` | it is always the case that whenever detect_motion is true then activate_alert will eventually be true at most 10 seconds after detect_motion became true | it is always the ~~case~~ **pillowcase** that whenever detect_motion is true then activate_alert will eventually be true at most 10 seconds after detect_motion ~~became~~ **suit** true | correct (third model) |

### 2. Broken grammar and word order

Word swaps, insertions and inflected forms give sentences no one would write.

| Formula | Original | Paraphrase | Judge |
|---|---|---|---|
| `G[0,1000] !robotAtWall` | Always, in the next 1000 seconds, the robot should not run into walls | Always, in the next 1000 ~~seconds,~~ **robot,** the ~~robot~~ **seconds** should not run into walls | no |
| `F[0,0.3] (z <= -0.1)` | encodes that eventually in the next 0.3 s, the quadrotor will fly above a threshold level of -0.1 m | encodes that eventually in the next 0.3 s, the quadrotor will ~~fly~~ **flying** above a threshold ~~level~~ **tiers** of -0.1 m | correct |

### 3. The quantity being constrained changes

Words that carry the formula (numbers, the formula's names, temporal and logical words) were frozen, but descriptions often name a signal in plain English, a name that isn't in the formula, so it can be replaced.

| Formula | Original | Paraphrase | Judge |
|---|---|---|---|
| `G[0,36] (rpm < 4000)` | in the next 36 seconds, engine speed should always be less than 4000 | in the next 36 seconds, engine ~~speed~~ **acceleration** should always be less than 4000 | wrong (third model) |
| `G[0,36] (rpm < 4000)` | in the next 36 seconds, engine speed should always be less than 4000 | in the next 36 seconds, engine ~~speed~~ **upper** should always be less than 4000 | wrong (third model) |

### 4. Back-translation is fluent but can't be controlled

It rewrites the whole sentence, so no word can be frozen: intervals, names and objects can change.

| Formula | Original | Paraphrase | Judge |
|---|---|---|---|
| `F[0,1] (x > 0.4)` | within the time interval [0,1] the value of sensor x would become larger than 0.4 | within the time interval ~~[0,1]~~ **[0.1]** the value of ~~sensor x~~ **the x-sensor** would ~~become larger~~ **be greater** than 0.4 | ambiguous (third model) |
| `F[0,0.3] (z <= -0.1)` | encodes that eventually in the next 0.3 s, the quadrotor will fly above a threshold level of -0.1 m | ~~encodes~~ **code** that eventually in the ~~next~~ **following** 0.3 s, the ~~quadrotor~~ **square** will fly above a threshold level of -0.1 m | undecided (all three models differ) |
| `G[0,inf] (detect_motion -> (F[0,10] activate_alert))` | it is always the case that whenever detect_motion is true then activate_alert will eventually be true at most 10 seconds after detect_motion became true | ~~it~~ is always the case that ~~whenever~~ **every time** detect_motion is true then activate_alert **eventually** will ~~eventually~~ be true at ~~most~~ **the maximum** 10 seconds after ~~detect_motion~~ **detection_motion** became true | wrong |

### 5. Little variety

The word methods change about 10% of the words (one to three in our descriptions), so a paraphrase is a near copy of the original; some descriptions had nothing that could be changed.

| Formula | Original | Paraphrase | Judge |
|---|---|---|---|
| `G[0,36] (rpm < 4000)` | in the next 36 seconds, engine speed should always be less than 4000 | in the next 36 seconds, **the** engine speed should always be less than 4000 | correct |

## Every paraphrase

For each description: its formula, the original, and the paraphrase of each method. Under the table, the judges' reasons for the paraphrases not labelled correct.

### W2221585980:F1:D1

Formula: `G[0,30] (!puncturing -> (f <= f_max))`

Original: The force applied to the patient by the end effector is always less than a given threshold, except for the puncturing subtask. Formally, assuming that the operation time is 30 seconds

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | wrong | The ~~force~~ **pressure** applied to the patient by the end effector is always less than a ~~given threshold,~~ **precondition doorsill,** except for the puncturing subtask. Formally, assuming that the operation time is 30 seconds |
| embedding | correct (third model) | The force applied to the ~~patient~~ **ailing** by the end effector is always less than a given threshold, except for the puncturing subtask. ~~Formally,~~ **Official,** assuming that the ~~operation~~ **functioning** time is 30 seconds |
| eda (synonym) | wrong | The ~~force~~ **strength** applied to the patient by the end effector is always less than a ~~given~~ **return** threshold, except for the puncturing subtask. Formally, ~~assuming~~ **arrogate** that the operation time is 30 seconds |
| backtranslation | wrong | The force applied to the patient by the ~~end~~ **final** effector is always ~~less~~ **lower** than a given threshold, except for the ~~puncturing subtask.~~ **subset of the score.** Formally, assuming that the ~~operation~~ **operating** time is 30 seconds |

<details><summary>Why the judges said so</summary>

- **wordnet: wrong**
  - gemini-3.8-flash, wrong: The description accurately captures the logic and time window, but uses 'pressure' instead of 'force'.
  - gpt-6-luna, wrong: It gives the bounded rule and puncturing exception, but substitutes pressure for force and leaves the threshold unspecified.
  - claude-sonnet-5.5, correct: It states that the force stays below the threshold at all times in a 30 s horizon except during puncturing, which matches the formula, with garbled wording.
- **eda: wrong**
  - gemini-3.8-flash, wrong: The description captures the formula structure and bounds, but uses 'strength' instead of 'force'.
  - gpt-6-luna, wrong: It gives the bounded rule and puncturing exception, but substitutes strength for force and leaves the threshold unspecified.
  - claude-sonnet-5.5, correct: Always below the threshold except during puncturing, within 30 s, matching the formula.
- **backtranslation: wrong**
  - gemini-3.8-flash, wrong: The condition on puncturing is mistranslated into an unrecognizable phrase.
  - gpt-6-luna, wrong: It states the bounded force rule but gives a different exception and leaves the threshold unspecified.
  - claude-sonnet-5.5, no: The exception condition is garbled and does not refer to puncturing, so the !puncturing condition has no clear counterpart.

</details>

### W2221585980:F9:D1

Formula: `G[0,36] (rpm < 4000)`

Original: in the next 36 seconds, engine speed should always be less than 4000

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | wrong (third model) | in the next 36 seconds, engine ~~speed~~ **upper** should always be less than 4000 |
| embedding | wrong (third model) | in the next 36 seconds, engine ~~speed~~ **acceleration** should always be less than 4000 |
| eda (deletion) | ambiguous | in the next 36 seconds, engine ~~speed~~ should always be less than 4000 |
| backtranslation | correct | in the next 36 seconds, **the** engine speed should always be less than 4000 |

<details><summary>Why the judges said so</summary>

- **wordnet: wrong**
  - gemini-3.8-flash, wrong: The description misnames the signal as 'engine upper' instead of engine speed.
  - gpt-6-luna, no: The description refers to a different or unclear quantity rather than engine speed.
  - claude-sonnet-5.5, wrong: The temporal structure matches, but the signal is garbled as "engine upper" rather than engine speed.
- **embedding: wrong**
  - gemini-3.8-flash, wrong: The description incorrectly specifies engine acceleration instead of engine speed.
  - gpt-6-luna, no: The description specifies acceleration instead of engine speed.
  - claude-sonnet-5.5, wrong: The signal is wrong: acceleration is not engine speed.
- **eda: ambiguous**
  - gemini-3.8-flash, ambiguous: The description names 'engine' rather than the specific variable engine speed.
  - gpt-6-luna, ambiguous: The timing and threshold match, but “engine” leaves the measured quantity unclear.
  - claude-sonnet-5.5, ambiguous: The time bound and threshold match, but the quantity being bounded is left unspecified.

</details>

### W2256658272:F4:D1

Formula: `G[0,inf] ((w_min <= w) && (w <= w_max))`

Original: allow w to lie in an interval [w_min,w_max] at all times

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | ~~allow~~ **leave** w to lie in an interval [w_min,w_max] at all times |
| embedding | correct | allow w to ~~lie~~ **lies** in an interval [w_min,w_max] at all times |
| eda (insertion) | correct | allow w to **At** lie in an interval [w_min,w_max] at all times |
| backtranslation | correct | allow w to ~~lie~~ **be** in an interval [w_min,w_max] at all times |

### W2470448410:F5:D1

Formula: `F[0,0.3] (z <= -0.1)`

Original: encodes that eventually in the next 0.3 s, the quadrotor will fly above a threshold level of -0.1 m

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | encodes that eventually in the next 0.3 s, the quadrotor will ~~fly~~ **rainfly** above a threshold ~~level~~ **stratum** of -0.1 m |
| embedding | correct | encodes that eventually in the next 0.3 s, the quadrotor will ~~fly~~ **flying** above a threshold ~~level~~ **tiers** of -0.1 m |
| eda (insertion) | correct | **cypher** encodes that eventually in the next 0.3 s, the quadrotor will fly above a threshold level of -0.1 m |
| backtranslation | undecided (all three models differ) | ~~encodes~~ **code** that eventually in the ~~next~~ **following** 0.3 s, the ~~quadrotor~~ **square** will fly above a threshold level of -0.1 m |

<details><summary>Why the judges said so</summary>

- **backtranslation: undecided**
  - gemini-3.8-flash, ambiguous: The description mistranslates quadrotor as 'square', but otherwise accurately describes the formula.
  - gpt-6-luna, no: It gives the matching eventual threshold condition and time bound but attributes the condition to a different entity.
  - claude-sonnet-5.5, wrong: It names the wrong subject, 'square', but the temporal structure and threshold match the formula. The subject is a typo-like corruption, so the described entity differs from the quadrotor.

</details>

### W2531762107:P13:D1

Formula: `G[0,T_c - tau_2 - tau_3) (gamma_cs -> (F[tau_1,tau_2) G[0,tau_3) gamma_es))`

Original: during the next T_c - tau_2 - tau_3 time units, whenever gamma_cs is true, then gamma_es will be true at least once from the next tau_1 to tau_2 time units and maintain to be true for tau_3 time units

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | during the next T_c - tau_2 - tau_3 time units, whenever gamma_cs is true, then gamma_es will be true at least once from the next tau_1 to tau_2 time units and ~~maintain~~ **preserve** to be true for tau_3 time units |
| embedding | correct | during the next T_c - tau_2 - tau_3 time units, whenever gamma_cs is true, then gamma_es will be true at least once from the next tau_1 to tau_2 time units and ~~maintain~~ **sustain** to be true for tau_3 time units |
| eda (synonym) | correct (third model) | during the next T_c - tau_2 - tau_3 time units, whenever gamma_cs is true, then gamma_es will be true at least once from the next tau_1 to tau_2 time units and ~~maintain~~ **observe** to be true for tau_3 time units |
| backtranslation | correct | during the next T_c - tau_2 - tau_3 time units, ~~whenever~~ **each time** gamma_cs is true, then gamma_es will be true at least once from the next tau_1 to tau_2 time units and ~~maintain to be~~ **keep it** true for tau_3 time units |

### W2531762107:P9:D1

Formula: `G[0,tau_1) F[0,tau_2) phi_t1`

Original: during the next tau_1 time units, phi_t1 is performed at least once in every tau_2 time units

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | during the next tau_1 time units, phi_t1 is ~~performed~~ **do** at least once in every tau_2 time units |
| embedding | correct | during the next tau_1 time units, phi_t1 is ~~performed~~ **accomplished** at least once in every tau_2 time units |
| eda (insertion) | correct | during the next tau_1 time units, phi_t1 is **whole** performed at least once in every tau_2 time units |
| backtranslation | correct (third model) | during the ~~next tau_1~~ **following tau_1, phi_t1** time ~~units, phi_t1~~ **units** is performed at least once in ~~every~~ **each** tau_2 time ~~units~~ **unit** |

### W2941720440:F1:D2

Formula: `G[0,inf] varphi`

Original: satisfaction of the formula at all times

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | no (third model) | satisfaction of the ~~formula~~ **convention** at all times |
| embedding | correct (third model) | satisfaction of the ~~formula~~ **formulas** at all times |
| eda (synonym) | no (third model) | satisfaction of the ~~formula~~ **convention** at all times |
| backtranslation | — | *(nothing changed)* |

<details><summary>Why the judges said so</summary>

- **wordnet: no**
  - gemini-3.8-flash, ambiguous: The description vaguely states satisfaction of a convention at all times without identifying varphi.
  - gpt-6-luna, no: The description does not identify the specification formula as the condition that must hold.
  - claude-sonnet-5.5, no: It only loosely names a convention being satisfied at all times, which does not correspond to the specification formula varphi.
- **eda: no**
  - gemini-3.8-flash, ambiguous: The description vaguely states satisfaction of a convention at all times without identifying varphi.
  - gpt-6-luna, no: The description does not identify the specification formula as the condition that must hold.
  - claude-sonnet-5.5, no: It only loosely names a convention being satisfied at all times, which does not correspond to the specification formula varphi.

</details>

### W2965407852:P6:D1

Formula: `G[0,inf] !((G[0,t1] (!pi_i_coll && W_i_s && (!D_i_s \|\| (E_i_s > epsilon_err)))) && (F(t1,t2] pi_i_coll))`

Original: there should not be a period of t1 where a visible object is not accurately detected and no collision occurs, followed immediately by a period of length t2 - t1 that contains a collision

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | ambiguous | there should not be a period of t1 where a visible object is not accurately ~~detected~~ **find** and no collision occurs, followed immediately by a period of length t2 - t1 that ~~contains~~ **arrest** a ~~collision~~ **hit** |
| embedding | ambiguous | there should not be a period of t1 where a visible object is not accurately ~~detected~~ **detects** and no collision occurs, followed immediately by a period of length t2 - t1 that ~~contains~~ **therein** a ~~collision~~ **crashed** |
| eda (insertion) | correct (third model) | there should not be a period of t1 where a visible object is not **A** accurately detected and no collision occurs, **hit** followed immediately by a period of length t2 - t1 that contains a collision |
| backtranslation | correct (third model) | there should ~~not~~ be ~~a~~ **no t1** period ~~of t1 where~~ **during which** a visible object is not accurately detected and no collision occurs, followed immediately by a ~~period of length~~ t2 - t1 ~~that contains~~ **length period containing** a collision |

<details><summary>Why the judges said so</summary>

- **wordnet: ambiguous**
  - gemini-3.8-flash, ambiguous: The description accurately captures the temporal logic structure and intervals but uses garbled wording for the collision condition.
  - gpt-6-luna, ambiguous: It appears to describe the prohibited sequence, but the accuracy condition and later collision are imprecisely stated.
  - claude-sonnet-5.5, ambiguous: It covers all parts of the formula, but the garbled wording leaves the collision part unclear.
- **embedding: ambiguous**
  - gemini-3.8-flash, ambiguous: The structure and conditions are represented, but the final collision clause contains nonsensical phrasing.
  - gpt-6-luna, ambiguous: It describes the prohibited sequence, but leaves the accuracy criterion imprecise.
  - claude-sonnet-5.5, correct: Every part of the formula has a counterpart, and the garbling does not change the meaning.

</details>

### W2995364870:P9:D1

Formula: `G[0,n] !alarm`

Original: the violations of the safety conditions remain completely stealthy only up to the duration n of the attack (we recall that ⟦P9⟧G[0,n] (!alarm)⟦/P9⟧ is satisfied with probability 0.99)

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | the ~~violations~~ **trespass** of the ~~safety~~ **safe** conditions remain completely stealthy only up to the duration n of the ~~attack~~ **attempt** (we recall that ⟦P9⟧G[0,n] (!alarm)⟦/P9⟧ is satisfied with probability 0.99) |
| embedding | correct | the ~~violations~~ **offence** of the safety conditions remain completely stealthy only up to the duration n of the ~~attack~~ **storming** (we recall that ⟦P9⟧G[0,n] (!alarm)⟦/P9⟧ is satisfied with ~~probability~~ **likely** 0.99) |
| eda (synonym) | correct | the violations of the safety ~~conditions~~ **status** remain completely stealthy only up to the duration n of the ~~attack~~ **assault** (we ~~recall~~ **retrieve** that ⟦P9⟧G[0,n] (!alarm)⟦/P9⟧ is satisfied with probability 0.99) |
| backtranslation | undecided (all three models differ) | ~~the~~ violations of ~~the safety~~ **security** conditions remain completely ~~stealthy only up to~~ **secret until** the duration n of the attack ~~(we recall~~ **(remember** that ~~⟦P9⟧G[0,n] (!alarm)⟦/P9⟧~~ **the probability** is ~~satisfied with probability~~ 0.99) |

<details><summary>Why the judges said so</summary>

- **backtranslation: undecided**
  - gemini-3.8-flash, ambiguous: The description conveys that conditions remain secret (no alarm) until duration n, but is slightly ambiguous on how secrecy is formulated without the explicit formula text.
  - gpt-6-luna, correct: The description says security violations remain secret, meaning no alarm is raised, until duration n of the attack.
  - claude-sonnet-5.5, no: It talks vaguely about violations staying secret until n and has no clear counterpart to the alarm never being raised.

</details>

### W3014403430:F1:D1

Formula: `varphi_I && (varphi_S U[0,inf] varphi_O)`

Original: all maximal solutions phi to H_cl starting from the initial set I eventually reach the goal set O, while staying within the safe set S

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | all maximal solutions phi to H_cl starting from the initial ~~set~~ **specify** I eventually reach the goal ~~set~~ **circle** O, while staying within the safe set S |
| embedding | correct | all maximal solutions phi to H_cl starting from the initial set I eventually reach the ~~goal~~ **objectives** set O, while staying within the ~~safe~~ **segura** set S |
| eda (synonym) | correct | all maximal solutions phi to H_cl starting from the initial set I eventually reach the goal ~~set~~ **localise** O, while staying within the safe ~~set~~ **located** S |
| backtranslation | correct (third model) | all ~~maximal~~ **the maximum** solutions **from** phi to H_cl ~~starting~~ from the initial set ~~I eventually~~ **to the end** reach the ~~goal~~ **target** set O, while ~~staying~~ **remaining** within the ~~safe~~ **safety** set S |

### W3083205847:P12:D2

Formula: `G[0,H] varphi_i`

Original: the requirement is met during the whole evolution of the system w.r.t. the time horizon H

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | the requirement is met during the ~~whole~~ **all** evolution of the system w.r.t. the time horizon H |
| embedding | correct | the requirement is met during the ~~whole~~ **entirety** evolution of the system w.r.t. the time horizon H |
| eda (swap) | correct (third model) | the requirement is met during the ~~whole~~ **w** evolution of the system ~~w.r.t.~~ **whole.r.t.** the time horizon H |
| backtranslation | correct | the requirement is met ~~during~~ **throughout** the ~~whole~~ evolution of the **w.r.t.** system ~~w.r.t.~~ the time horizon H |

### W3122631132:P2:D1

Formula: `F[a,b] varphi`

Original: states that varphi is true at some point within [a,b] time units

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | ~~states~~ **submit** that varphi is true at some point within [a,b] time units |
| embedding | — | *(nothing changed)* |
| eda (synonym) | correct | ~~states~~ **State** that varphi is true at some point within [a,b] time units |
| backtranslation | — | *(nothing changed)* |

### W3198638775:F1:D1

Formula: `F[0,1] (x > 0.4)`

Original: within the time interval [0,1] the value of sensor x would become larger than 0.4

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | within the time interval [0,1] the value of sensor x would ~~become~~ **go** larger than 0.4 |
| embedding | correct | within the time interval [0,1] the value of sensor x would ~~become~~ **becoming** larger than 0.4 |
| eda (swap) | no (third model) | within the time interval ~~[0,1]~~ **[sensor,1]** the value of ~~sensor~~ **0** x would become larger than 0.4 |
| backtranslation | ambiguous (third model) | within the time interval ~~[0,1]~~ **[0.1]** the value of ~~sensor x~~ **the x-sensor** would ~~become larger~~ **be greater** than 0.4 |

<details><summary>Why the judges said so</summary>

- **eda: no**
  - gemini-3.8-flash, wrong: The description garbles the bounds and signal name into an incorrect statement.
  - gpt-6-luna, no: The interval bound and the signal condition differ from the formula.
  - claude-sonnet-5.5, no: The interval and signal are garbled, so the description does not match the formula's bounds [0,1] and signal x.
- **backtranslation: ambiguous**
  - gemini-3.8-flash, wrong: The time interval is stated incorrectly as [0.1] rather than [0,1].
  - gpt-6-luna, ambiguous: It describes the threshold condition and an eventual occurrence, but the stated time interval is ambiguous.
  - claude-sonnet-5.5, ambiguous: The interval is malformed, and the description may be a typo for [0,1], but it is unclear whether it is eventually or always, so the fit is ambiguous.

</details>

### W3210726654:F1:D1

Formula: `safe U[0,240] (G[0,10] target)`

Original: the robot must satisfy each safety boundary with 99% confidence until it achieves each target boundary with 95% confidence within 240 time instants and stays in the target for 10 time instants

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct (third model) | the robot must satisfy each ~~safety~~ **condom** boundary with 99% confidence until it achieves each target ~~boundary~~ **edge** with 95% ~~confidence~~ **trust** within 240 time instants and stays in the target for 10 time instants |
| embedding | correct | the ~~robot~~ **robots** must satisfy each safety ~~boundary~~ **restrict** with 99% confidence until it achieves each target ~~boundary~~ **limiting** with 95% confidence within 240 time instants and stays in the target for 10 time instants |
| eda (deletion) | correct | the robot must satisfy each safety ~~boundary~~ with 99% confidence until it achieves each target ~~boundary~~ with 95% confidence within 240 time ~~instants~~ and stays in the target for 10 time instants |
| backtranslation | correct | the robot must ~~satisfy~~ **meet** each safety ~~boundary~~ **limit** with 99% confidence until ~~it achieves~~ **reaching** each target ~~boundary~~ **limit** with 95% confidence within 240 **moments of** time ~~instants~~ and ~~stays~~ **remain** in the target for 10 **moments of** time ~~instants~~ |

### W4391019804:P7:D1

Formula: `F[t_a,t_b] mu`

Original: \\exists t'in[t_a,t_b],h( x(t'))>=0

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | no (third model) | ~~\\exists~~ **\\be** t'in[t_a,t_b],h( x(t'))>=0 |
| embedding | correct | ~~\\exists~~ **\\exist** t'in[t_a,t_b],h( x(t'))>=0 |
| eda (swap) | no | \\exists ~~t'in[t_a,t_b],h( x(t'))>=0~~ **x[t_a,t_b],h( t'in(t'))>=0** |
| backtranslation | correct | ~~\\exists t'in[t_a,t_b],h( x(t'))>=0~~ **\\existing t'in[t_a,t_b],h(x(t'))>=0** |

<details><summary>Why the judges said so</summary>

- **wordnet: no**
  - gemini-3.8-flash, correct: The description mathematically expresses the semantics of the 'eventually' operator over [t_a, t_b] where \\be stands for \\exists, matching F[t_a,t_b] mu assuming mu corresponds to the predicate h(x) >= 0.
  - gpt-6-luna, no: It gives the predicate and interval but does not clearly express the eventuality required by the formula.
  - claude-sonnet-5.5, no: The text lacks an existential quantifier, so the eventually operator has no clear counterpart.
- **eda: no**
  - gemini-3.8-flash, no: The description contains garbled and nonsensical mathematical notation.
  - gpt-6-luna, no: Its quantified object and stated condition do not match the formula's eventual predicate.
  - claude-sonnet-5.5, no: The expression is garbled and does not coherently express existence of a time in the interval.

</details>

### W4394907173:F2:D1

Formula: `F[0,2] (x > 0)`

Original: specifies that there exists a time instant t between 0 and 2 such that xt > 0

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | ~~specifies~~ **specialize** that there exists a time instant t between 0 and 2 such that xt > 0 |
| embedding | correct | specifies that there ~~exists~~ **exist** a time instant t between 0 and 2 such that xt > 0 |
| eda (swap) | correct | **that** specifies ~~that~~ there exists a time instant t between 0 and 2 such that xt > 0 |
| backtranslation | correct | specifies that there ~~exists a~~ **is an instantaneous** time ~~instant~~ t between 0 and 2 ~~such~~ **so** that xt > 0 |

### W4403799341:F1:D1

Formula: `G[0,inf] (detect_motion -> (F[0,10] activate_alert))`

Original: it is always the case that whenever detect_motion is true then activate_alert will eventually be true at most 10 seconds after detect_motion became true

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct (third model) | it is always the ~~case~~ **pillowcase** that whenever detect_motion is true then activate_alert will eventually be true at most 10 seconds after detect_motion ~~became~~ **suit** true |
| embedding | correct | it is always the ~~case~~ **example** that whenever detect_motion is true then activate_alert will eventually be true at most 10 seconds after detect_motion ~~became~~ **came** true |
| eda (swap) | correct (third model) | it is always the **whenever that** case ~~that whenever~~ detect_motion is true then activate_alert will eventually be true at most 10 seconds after detect_motion became true |
| backtranslation | wrong | ~~it~~ is always the case that ~~whenever~~ **every time** detect_motion is true then activate_alert **eventually** will ~~eventually~~ be true at ~~most~~ **the maximum** 10 seconds after ~~detect_motion~~ **detection_motion** became true |

<details><summary>Why the judges said so</summary>

- **backtranslation: wrong**
  - gemini-3.8-flash, wrong: The description uses an incorrect variable name ('detection_motion') for the trigger signal.
  - gpt-6-luna, wrong: It otherwise gives the same rule, but names a different signal as the timing reference.
  - claude-sonnet-5.5, correct: It states always, every time detect_motion then activate_alert within at most 10 seconds, matching the formula.

</details>

### W4405182083:P4:D1

Formula: `G[a,b] (f_x > tau)`

Original: f_x > tau is always true in the interval [a,b]

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | — | *(nothing changed)* |
| embedding | — | *(nothing changed)* |
| eda | — | *(nothing changed)* |
| backtranslation | — | *(nothing changed)* |

### W4412164746:P9:D1

Formula: `(F[0,T] g_1) && (G[0,T] !g_2)`

Original: eventually reaching g_1 and always avoiding g_2 within time interval [0,T]

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | undecided (all three models differ) | eventually ~~reaching~~ **strain** g_1 and always avoiding g_2 within time interval [0,T] |
| embedding | correct | eventually reaching g_1 and always ~~avoiding~~ **forestall** g_2 within time interval [0,T] |
| eda (deletion) | wrong (third model) | eventually reaching g_1 and always ~~avoiding~~ g_2 within time interval [0,T] |
| backtranslation | correct | ~~eventually reaching~~ **finally reach** g_1 and always ~~avoiding~~ **avoid** g_2 within **the** time interval [0,T] |

<details><summary>Why the judges said so</summary>

- **wordnet: undecided**
  - gemini-3.8-flash, ambiguous: The description uses the nonsensical verb 'strain' instead of attain/reach, but clearly attempts to describe reaching g_1 and avoiding g_2 within [0,T].
  - gpt-6-luna, no: It does not clearly state the formula’s eventual g_1 condition.
  - claude-sonnet-5.5, correct: It says g_1 is eventually reached and g_2 is always avoided within [0,T], which matches the formula.
- **eda: wrong**
  - gemini-3.8-flash, wrong: The description omits the negation of g_2, stating that g_2 should always hold rather than being avoided.
  - gpt-6-luna, no: The description reverses the g_2 condition.
  - claude-sonnet-5.5, wrong: The description drops the negation on g_2, so it contradicts the formula.

</details>

### arxiv_1404.0087:F1:D1

Formula: `F[0,2] varphi`

Original: varphi will hold within two time units from now

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | — | *(nothing changed)* |
| embedding | — | *(nothing changed)* |
| eda | — | *(nothing changed)* |
| backtranslation | wrong (third model) | ~~varphi~~ **Varphi** will ~~hold~~ **keep** within two **units of** time ~~units~~ from now **on** |

<details><summary>Why the judges said so</summary>

- **backtranslation: wrong**
  - gemini-3.8-flash, wrong: The description uses 'keep', implying a globally/always operator instead of the eventually operator in the formula.
  - gpt-6-luna, no: The description gives a continuous-holding requirement rather than the formula’s eventuality requirement.
  - claude-sonnet-5.5, wrong: The description has a counterpart for the time bound 2 but conveys a persistent 'keep' meaning (always) instead of eventually.

</details>

### arxiv_2207.00627:F16:D1

Formula: `G[0,1000] !robotAtWall`

Original: Always, in the next 1000 seconds, the robot should not run into walls

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | Always, in the next 1000 seconds, the robot should not ~~run~~ **streak** into walls |
| embedding | correct | Always, in the next 1000 seconds, the robot should not ~~run~~ **running** into walls |
| eda (swap) | no | Always, in the next 1000 ~~seconds,~~ **robot,** the ~~robot~~ **seconds** should not run into walls |
| backtranslation | correct | Always, in the next 1000 seconds, the robot should not run ~~into~~ **against the** walls |

<details><summary>Why the judges said so</summary>

- **eda: no**
  - gemini-3.8-flash, no: The description garbles the words, making the subject and time bounds nonsensical.
  - gpt-6-luna, no: The wording makes the time bound and the subject of the avoidance condition unclear.

</details>

### arxiv_2508.04438:P3:D1

Formula: `G[x,y] rho`

Original: true if and only if rho is true at all sampled times between and including t_n + x and t_n + y

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct (third model) | true if and only if rho is true at all ~~sampled~~ **sample** times between and ~~including~~ **include** t_n + x and t_n + y |
| embedding | correct (third model) | true if and only if rho is true at all ~~sampled~~ **sampling** times between and ~~including~~ **containing** t_n + x and t_n + y |
| eda (deletion) | ambiguous (third model) | true if and only if rho is true at all ~~sampled~~ times between and ~~including~~ t_n + x and t_n + y |
| backtranslation | wrong (third model) | true if ~~and~~ **y** only if rho is true ~~at~~ **in** all ~~sampled~~ **sampling** times between ~~and~~ **y** including t_n + x and t_n + y |

<details><summary>Why the judges said so</summary>

- **eda: ambiguous**
  - gemini-3.8-flash, ambiguous: The description conveys that rho must hold at all times between t_n + x and t_n + y, though the phrasing is slightly garbled and omits endpoint inclusion.
  - gpt-6-luna, correct: It correctly says that ρ must hold at all times between the stated bounds.
  - claude-sonnet-5.5, ambiguous: It conveys the always over the interval, but inclusion of the endpoints is unclear.
- **backtranslation: wrong**
  - gemini-3.8-flash, ambiguous: The description describes the semantics of the formula, but has severe typographical errors substituting 'y' for 'and'.
  - gpt-6-luna, wrong: It includes an all-times condition on ρ over the interval, but restricts it to samples and adds an unrelated condition on y.
  - claude-sonnet-5.5, wrong: The core idea of rho holding at all sampling times in the interval is present, but the text is garbled and reads as 'true if y only if', which does not match the formula's meaning.

</details>

### arxiv_2509.08610:P2:D1

Formula: `F[l,u] varphi`

Original: requires varphi to be satisfied eventually within l and u steps

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | ~~requires~~ **demand** varphi to be satisfied eventually within l and u steps |
| embedding | correct | ~~requires~~ **require** varphi to be satisfied eventually within l and u steps |
| eda (swap) | correct (third model) | ~~requires~~ **steps** varphi to be satisfied eventually within l and u ~~steps~~ **requires** |
| backtranslation | correct | requires varphi to be **eventually** satisfied ~~eventually~~ within **the steps of** l and u ~~steps~~ |

### arxiv_2511.16765:F1:D1

Formula: `G[0,30] (TankHeight <= 8)`

Original: the water level must not exceed 8 for 30 s of simulation time

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | undecided (all three models differ) | the water ~~level~~ **degree** must not exceed 8 for 30 s of simulation time |
| embedding | correct | the water level must not exceed 8 for 30 s of ~~simulation~~ **simulated** time |
| eda (insertion) | wrong (third model) | the **moldiness** water level must not exceed 8 for 30 s of simulation time |
| backtranslation | ambiguous | the water level ~~must~~ **shall** not exceed 8 ~~for~~ **in** 30 ~~s~~ **seconds** of simulation time |

<details><summary>Why the judges said so</summary>

- **wordnet: undecided**
  - gemini-3.8-flash, wrong: The description uses an inaccurate term for the signal but otherwise correctly describes the temporal requirement.
  - gpt-6-luna, no: The description gives the threshold and 30-second duration but refers to a different quantity than the formula.
  - claude-sonnet-5.5, ambiguous: It states the always-bound of 8 over 30 s, but the signal name 'water degree' is garbled and does not clearly match TankHeight.
- **eda: wrong**
  - gemini-3.8-flash, wrong: The description mischaracterizes the signal with the term 'moldiness'.
  - gpt-6-luna, no: The description gives the threshold and 30-second duration but refers to a different quantity than the formula.
  - claude-sonnet-5.5, wrong: The signal is described as 'moldiness water level', which does not match TankHeight.
- **backtranslation: ambiguous**
  - gemini-3.8-flash, ambiguous: Using 'in 30 seconds' is ambiguous between holding throughout the interval or at some point within it.
  - gpt-6-luna, ambiguous: The description states the level limit and indicates a 30-second period, but the duration wording is ambiguous about whether the limit must hold throughout that period.
  - claude-sonnet-5.5, ambiguous: The wording 'in 30 seconds' leaves unclear whether the bound holds throughout the whole period, though 'shall not exceed' suggests it does.

</details>

### arxiv_2603.28426:F2:D3

Formula: `(F[0,10] (phi_B \|\| phi_C)) && (G[0,10] !phi_A)`

Original: Within 10 seconds, reach B or reach C while avoiding A.

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | ambiguous | Within 10 seconds, reach B or reach C while ~~avoiding~~ **nullify** A. |
| embedding | ambiguous | Within 10 seconds, reach B or reach C while ~~avoiding~~ **averted** A. |
| eda (swap) | wrong (third model) | Within 10 seconds, ~~reach~~ **avoiding** B or reach C while ~~avoiding~~ **reach** A. |
| backtranslation | ambiguous | ~~Within~~ **In** 10 seconds, ~~reach~~ **range** B or ~~reach~~ C while avoiding A. |

<details><summary>Why the judges said so</summary>

- **wordnet: ambiguous**
  - gemini-3.8-flash, ambiguous: The description captures reaching B or C within 10 seconds while avoiding A, but uses non-standard, ambiguous wording ('nullify A').
  - gpt-6-luna, ambiguous: It describes reaching B or C within 10 seconds and avoiding A, but the scope of the avoidance is unclear.
  - claude-sonnet-5.5, ambiguous: It has reaching B or C within 10 s and an A-avoidance condition, so every part has a counterpart, though the wording is vague.
- **embedding: ambiguous**
  - gemini-3.8-flash, ambiguous: The description identifies the core properties but uses unclear phrasing for the global avoidance of A.
  - gpt-6-luna, ambiguous: It describes reaching B or C within 10 seconds and avoiding A, but the scope of the avoidance is unclear.
  - claude-sonnet-5.5, ambiguous: It covers both the F part (B or C within 10 s) and the A-avoidance part, with imprecise wording.
- **eda: wrong**
  - gemini-3.8-flash, wrong: The description inverts the reach and avoid conditions for regions B and A.
  - gpt-6-luna, no: The description reverses the condition on B and contradicts the required condition on A.
  - claude-sonnet-5.5, wrong: It reverses the roles of A and B and contradicts the formula.
- **backtranslation: ambiguous**
  - gemini-3.8-flash, ambiguous: The requirement uses ambiguous terminology ('range B or C') instead of clearly specifying reaching B or C.
  - gpt-6-luna, ambiguous: It mentions the right regions and avoiding A, but the timing and scope of those requirements are unclear.
  - claude-sonnet-5.5, ambiguous: It says B or C is reached in 10 s while A is avoided, which matches the formula structurally, but "range" is garbled and the scope is not clearly stated.

</details>

### arxiv_2604.14440:F3:D1

Formula: `F[100,200] G[0,300] (x < 0)`

Original: situations where at some time point (in this example, between the \$100^{th}\$ step and the \$200^{th}\$ step) the cart continuously stays in the region with x < 0 for some time (in this example, for 300 successive steps)

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct (third model) | situations where at some time point (in this ~~example,~~ **case,** between the \$100^{th}\$ step and the \$200^{th}\$ step) the ~~cart~~ **haul** continuously stays in the region with x < 0 for some time (in this ~~example,~~ **illustration,** for 300 successive steps) |
| embedding | correct | ~~situations~~ **circumstances** where at some time point (in this example, between the \$100^{th}\$ step and the \$200^{th}\$ step) the cart continuously stays in the region with x < 0 for some time (in this ~~example,~~ **case,** for 300 ~~successive~~ **sequential** steps) |
| eda (swap) | undecided (all three models differ) | situations where at some time point (in this ~~example,~~ **th,** between the \$100^{th}\$ step and the ~~\$200^{th}\$~~ **\$200^{example}\$** step) the cart continuously stays in the region with ~~x~~ **example** < 0 for some time (in this ~~example,~~ **x,** for 300 successive steps) |
| backtranslation | correct | situations where at some ~~time~~ point (in this example, between the **step of** \$100^{th}\$ ~~step~~ and the ~~\$200^{th}\$ step)~~ **step of \$200^{th}\$)** the cart **remains** continuously ~~stays~~ in the region with x < 0 for some time (in this example, ~~for~~ **during** 300 successive steps) |

<details><summary>Why the judges said so</summary>

- **eda: undecided**
  - gemini-3.8-flash, wrong: The text is corrupted with scrambled variable names and terms, misstating the condition as 'example < 0'.
  - gpt-6-luna, no: The description does not correctly state the cart-position condition and gives a corrupted time bound.
  - claude-sonnet-5.5, ambiguous: The structure is intact, but the garbled variable name ("example < 0") and the garbled step label make it unreliable as a description of x < 0.

</details>

### arxiv_2605.21676:P11:D1

Formula: `G[0,T] ((23.5 <= tau_p_P_A) && (tau_p_P_A <= 24.5))`

Original: the oscillation period remains robustly within a 23.5 to 24.5-hour window for the entire simulation duration T

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | the oscillation period remains robustly within a 23.5 to 24.5-hour window for the entire ~~simulation~~ **model** duration T |
| embedding | correct | the oscillation period remains robustly within a 23.5 to 24.5-hour window for the ~~entire~~ **overall** simulation duration T |
| eda (swap) | wrong (third model) | the oscillation period remains robustly within a ~~23.5~~ **entire.5** to 24.5-hour window for the ~~entire~~ **23** simulation duration T |
| backtranslation | correct | the oscillation period remains ~~robustly~~ **robust** within a **window of** 23.5 to ~~24.5-hour window~~ **24.5 hours** for the entire **duration of the** simulation ~~duration~~ T |

<details><summary>Why the judges said so</summary>

- **eda: wrong**
  - gemini-3.8-flash, wrong: The description has corrupted words and numbers that contradict the formula.
  - gpt-6-luna, ambiguous: It appears to describe the period constraint over duration T, but its lower bound and duration wording are unclear.
  - claude-sonnet-5.5, wrong: The text is garbled and has a nonsensical lower bound and duration, so it does not state the formula's requirement.

</details>

### arxiv_2608.07289:P5:D1

Formula: `G[t_f,t_r] (v_i >= v_trip)`

Original: The data center's internal voltage v_i must stay above the power-electronics trip threshold v_trip over the fault window [t_f,t_r]

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | correct | The data center's ~~internal~~ **intimate** voltage v_i must stay above the power-electronics ~~trip~~ **tripper** threshold v_trip over the fault window [t_f,t_r] |
| embedding | correct (third model) | The data center's ~~internal~~ **interiors** voltage v_i must stay above the power-electronics ~~trip~~ **journeys** threshold v_trip over the fault window [t_f,t_r] |
| eda (insertion) | correct (third model) | The data center's internal voltage v_i must stay above the power-electronics trip **windowpane** threshold v_trip over the fault window [t_f,t_r] |
| backtranslation | correct (third model) | The ~~data center's~~ internal voltage **of the** v_i ~~must stay~~ **data center should remain** above the ~~power-electronics trip~~ **displacement** threshold **of the** v_trip **power electronics** over the ~~fault~~ **failure** window [t_f,t_r] |

### arxiv_2609.33287:F10:D1

Formula: `G[0,inf] (fan_running && fan_running)`

Original: At all times, `laundry room exhaust fan running' is active and `laundry room exhaust fan running' is active.

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | wrong (third model) | At all times, `laundry room exhaust fan ~~running'~~ **incline'** is active and `laundry room exhaust fan running' is active. |
| embedding | wrong (third model) | At all times, `laundry room exhaust fan ~~running'~~ **implementing'** is active and `laundry room exhaust fan running' is active. |
| eda (deletion) | undecided (all three models differ) | At all times, ~~`laundry~~ room exhaust fan running' is active and `laundry room exhaust fan running' is active. |
| backtranslation | correct | At all times, ~~`laundry~~ **the laundry** room exhaust fan ~~running'~~ is active and ~~`laundry~~ **the laundry** room exhaust fan ~~running'~~ is active. |

<details><summary>Why the judges said so</summary>

- **wordnet: wrong**
  - gemini-3.8-flash, wrong: The description uses a fabricated/incorrect signal name ('incline') for the first conjunct.
  - gpt-6-luna, no: The first condition differs from the formula, so the description does not state the full requirement.
  - claude-sonnet-5.5, wrong: The first conjunct refers to a different signal than fan_running.
- **embedding: wrong**
  - gemini-3.8-flash, wrong: The description uses an incorrect signal description ('implementing') for the first conjunct.
  - gpt-6-luna, no: The first condition differs from the formula, so the description does not state the full requirement.
  - claude-sonnet-5.5, wrong: The first conjunct is a different signal from the one in the formula.
- **eda: undecided**
  - gemini-3.8-flash, wrong: The first conjunct omits 'laundry' from the signal name.
  - gpt-6-luna, no: The first condition does not identify the signal required by the formula.
  - claude-sonnet-5.5, ambiguous: The structure matches, but the first signal name is garbled and only approximately matches fan_running.

</details>

### arxiv_2609.33287:F21:D1

Formula: `F[0,60] (inhibit && (F[0,10] updated))`

Original: At some point within [0, 60] seconds, reverse-motion inhibit is active and a rear-path result is updated within 10 seconds.

| Method | Judge | Paraphrase |
|---|---|---|
| wordnet | wrong (third model) | At some point within [0, 60] seconds, reverse-motion inhibit is ~~active~~ **alive** and a rear-path ~~result~~ **consequence** is updated within 10 seconds. |
| embedding | correct | At some point within [0, 60] seconds, reverse-motion inhibit is active and a rear-path ~~result~~ **results** is updated within 10 seconds. |
| eda (insertion) | correct (third model) | At some point within [0, 60] seconds, **sec** reverse-motion inhibit is active and a rear-path result is updated within 10 seconds. |
| backtranslation | correct | At some point within [0, 60] seconds, ~~reverse-motion inhibit~~ **reverse motion inhibition** is active and a ~~rear-path~~ **rear track** result is updated ~~within~~ **in** 10 seconds. |

<details><summary>Why the judges said so</summary>

- **wordnet: wrong**
  - gemini-3.8-flash, correct: The description captures all temporal operators and conditions accurately, despite a slight word substitution ('alive' for 'active').
  - gpt-6-luna, wrong: It includes both timed conditions, but changes the meanings of the inhibit and update conditions.
  - claude-sonnet-5.5, wrong: The structure matches, but the wording changes the meaning of the signals (alive vs active, consequence vs result).

</details>
