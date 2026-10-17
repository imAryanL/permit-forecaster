# Machine learning study guide for the permit forecaster

Ten short lessons, in the order the project needs them. Each one says what the idea is, where it shows up in this project, what to look up, and questions to check yourself.

## How to use this

1. Read one lesson the day you need it. Don't read ahead by more than a week.
2. Spend 20 to 30 minutes on the "look up" item.
3. Build that piece of the project.
4. Answer the "check yourself" questions out loud or to Claude, without notes. If you can't, reread and try again.

The scikit-learn user guide and the pandas "getting started" pages are the only references you need. Both are free.

---

## Lesson 1: rows, features and the target (week 1)

**The idea.** A model learns from a table. Each row is one example. The columns it looks at are the features. The column it predicts is the target.

**In this project.** Each row is one permit.

| city | permit type | cost | month | wait in days |
|---|---|---|---|---|
| Orlando | Roof | 18,000 | March | 12 |
| Miami | Remodel | 85,000 | July | 96 |

City, permit type, cost and month are features. Wait in days is the target.

**Look up.** pandas: loading a table and selecting columns.

**Check yourself**
- What is one row in your data?
- Which column is the target, and how do you compute it from two dates?

## Lesson 2: the baseline (week 1)

**The idea.** Before training anything, make the simplest reasonable prediction. Later, the model has to beat it. Without a baseline, a score means nothing.

**In this project.** For a roof permit in Orlando, predict the median wait of roof permits in Orlando over the previous 90 days.

**Why the median, not the average.** A few permits take hundreds of days. They drag the average up, but the median stays at the typical case.

**Look up.** pandas `groupby` with `median`, and the SQL versions: `GROUP BY` and `PERCENTILE_CONT`.

**Check yourself**
- Waits of 5, 6, 7, 8 and 200 days: what is the median, and what is the average?
- Why is "predict the median" a fair opponent for your model?

## Lesson 3: train and test, split by time (week 2)

**The idea.** A model always scores well on data it trained on. To know how it will do on new data, hide some data during training and score it only on that.

**In this project.** You are predicting future permits, so train on older months and test on the newest ones. A random split would let the model learn from permits filed after the ones it is tested on.

**Data leakage.** A feature leaks when it contains information you would not have at prediction time. Orlando's number of review rounds is only known after approval, so it cannot be a feature.

**Look up.** scikit-learn user guide: "Cross-validation", the part on time series.

**Check yourself**
- If you train through June and test on July to September, which permits must not be in training?
- Name one column in the Orlando data that would leak the answer.

## Lesson 4: decision trees and gradient boosting (week 2)

**The idea.** A decision tree predicts by asking yes or no questions in a chain, such as "is the cost above 50,000?" and then "is it Miami?". Each path ends in a prediction.

Gradient boosting builds many small trees one after another. Each new tree focuses on what the earlier trees got wrong. The final prediction adds them all up.

**In this project.** The forecast model is gradient boosting. It handles mixed columns (numbers and categories) well and needs little tuning.

**Look up.** scikit-learn `HistGradientBoostingRegressor`.

**Check yourself**
- Explain a decision tree to a non-programmer in two sentences.
- What does each new tree in boosting try to fix?

## Lesson 5: percentile forecasts and pinball loss (week 2)

**The idea.** One number hides the risk. A percentile forecast says "half finish within 21 days, 9 in 10 within 60."

**Pinball loss** scores a percentile forecast. For the 90th percentile:
- If the real wait is above your forecast, the penalty is 0.9 times the gap.
- If the real wait is below your forecast, the penalty is 0.1 times the gap.

Example with a forecast of 60 days: a real wait of 80 costs 0.9 x 20 = 18. A real wait of 30 costs 0.1 x 30 = 3. Being too low is punished nine times harder, which pushes the forecast high enough to cover 9 in 10 cases.

**Coverage** is the plain-language check: of all test permits, what share really finished within the 90th-percentile forecast? It should be close to 90%.

**In this project.** You train one model each for the 50th, 80th and 90th percentiles and report pinball loss and coverage against the baseline.

**Look up.** scikit-learn `HistGradientBoostingRegressor` with `loss="quantile"`, and `mean_pinball_loss`.

**Check yourself**
- Your 90th-percentile forecast is 40 days and the real wait is 50. What is the pinball loss?
- Your coverage comes out at 70%. Is the forecast too high or too low?

## Lesson 6: overfitting (week 2)

**The idea.** A model overfits when it memorizes the training data, noise included. The sign is a strong training score and a much weaker test score.

**In this project.** Compare the model's score on training months and test months. A large gap means it is overfitting. Fewer or shallower trees usually help.

**Check yourself**
- Training error is 4 days and test error is 15 days. What is happening?
- Why can't you detect overfitting without a test set?

## Lesson 7: measuring the LLM's labels (week 5)

**The idea.** An LLM's output is only useful if you know how often it is right. You find out by comparing it with answers you trust.

**In this project.** You hand-label about 300 descriptions. The LLM labels the same 300. Agreement is the share where it matches you. You also look at which categories it confuses.

**Check yourself**
- The LLM matches you on 264 of 300. What is the agreement?
- Why must you label the 300 before seeing the LLM's answers?

## Lesson 8: turning text into numbers with TF-IDF (week 6)

**The idea.** Models need numbers, not words. TF-IDF gives each word in a description a score: higher if the word appears in that description, lower if the word is common across all descriptions.

**In this project.** In "TEAR OFF & RE-ROOF 32 SQ SHINGLE", the words "re-roof" and "shingle" score high because they are distinctive. A word that appears in nearly every description scores close to zero.

**Look up.** scikit-learn `TfidfVectorizer`.

**Check yourself**
- Why does a word that appears in every description get a low score?
- What does one row look like after TF-IDF?

## Lesson 9: the text classifier and how to score it (week 6)

**The idea.** Logistic regression learns a weight for each word and each category, then picks the category with the highest total. You can read the weights to see which words drive each decision.

**Scoring a classifier**
- Accuracy: the share it got right overall.
- Precision for "roof": of the ones it called roof, how many really were.
- Recall for "roof": of all the real roofs, how many it found.

Example: it calls 20 descriptions "roof" and 16 really are, so precision is 80%. There were 25 real roofs, so recall is 16 of 25, or 64%.

**In this project.** You train the classifier on the LLM's labels and score it on your 300 hand labels.

**Look up.** scikit-learn `LogisticRegression` and `classification_report`.

**Check yourself**
- A classifier calls everything "roof". What are its recall and precision for roof likely to be?
- Why score it on your hand labels and not on the LLM's labels?

## Lesson 10: did the new feature help? (week 6)

**The idea.** To know whether something improves a model, train it twice, with and without that one thing, and compare on the same test data. Change only one thing at a time.

**In this project.** Train the forecast model with the work category and without it. The difference in pinball loss is how much the LLM step is worth. If it is close to zero, say so in the README.

**Check yourself**
- Why must both versions use the same test months?
- The category improves the forecast by 1%. How would you describe that result honestly?

---

## What you can skip for this project

Neural networks, deep learning, the calculus behind training, clustering, and large-scale tuning. None of them are needed here.
