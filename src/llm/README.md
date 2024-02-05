# ChatGPT PFV

## Introduction

## Baseline

* https://github.com/spdustin/ChatGPT-AutoExpert/
* https://github.com/linexjlin/GPTs/blob/main/prompts/Grimoire.md
* https://github.com/friuns2/Leaked-GPTs/blob/main/README.md

## Techniques used

### Global techniques

* Be very specific about the instruction and task you want the model to perform. The more descriptive and detailed the prompt is, the better the results. This is particularly important when you have a desired outcome or style of generation you are seeking. There aren't specific tokens or keywords that lead to better results. It's more important to have a good format and descriptive prompt. In fact, providing examples in the prompt is very effective to get desired output in specific formats. (https://www.promptingguide.ai)

* The length of the prompt as there are limitations regarding how long the prompt can be. Thinking about how specific and detailed you should be. Including too many unnecessary details is not necessarily a good approach. The details should be relevant and contribute to the task at hand. (https://www.promptingguide.ai)

* Avoid Impreciseness (few, many, some, etc.) and Ambiguity (it, this, that, etc.) (https://www.promptingguide.ai)

* Another common tip when designing prompts is to avoid saying what not to do but **say what to do instead**.

### Specific techniques

* Zero-shot learning: https://www.promptingguide.ai/techniques/zeroshot + https://arxiv.org/pdf/2109.01652.pdf
    * When zero-shot doesn't work, it's recommended to provide demonstrations or examples in the prompt which leads to few-shot prompting. In the next section, we demonstrate few-shot prompting.
    
* Chain-of-Thought (CoT) Prompting: https://www.promptingguide.ai/techniques/cot
    * One recent idea that came out more recently is the idea of zero-shot CoT (Kojima et al. 2022) that essentially involves adding "Let's think step by step" to the original prompt. -> This automatic process can still end up with mistakes in generated chains. 

* Automatic Chain-of-Thought (Auto-CoT): https://www.promptingguide.ai/techniques/cot#automatic-chain-of-thought-auto-cot
    * Auto-CoT consists of two main stages:
        1.  question clustering: partition questions of a given dataset into a few clusters
        2.  demonstration sampling: select a representative question from each cluster and generate its reasoning chain using Zero-Shot-CoT with simple heuristics

* Self-Consistency: https://www.promptingguide.ai/techniques/consistency
```
Q: There were nine computers in the server room. Five more computers were installed each day, from
monday to thursday. How many computers are now in the server room?
A: There are 4 days from monday to thursday. 5 computers were added each day. That means in total 4 * 5 =
20 computers were added. There were 9 computers in the beginning, so now there are 9 + 20 = 29 computers.
The answer is 29.

Q: Michael had 58 golf balls. On tuesday, he lost 23 golf balls. On wednesday, he lost 2 more. How many
golf balls did he have at the end of wednesday?
A: Michael initially had 58 balls. He lost 23 on Tuesday, so after that he has 58 - 23 = 35 balls. On
Wednesday he lost 2 more so now he has 35 - 2 = 33 balls. The answer is 33.

Q: Olivia has $23. She bought five bagels for $3 each. How much money does she have left?
A: She bought 5 bagels for $3 each. This means she spent $15. She has $8 left.

Q: When I was 6 my sister was half my age. Now I’m 70 how old is my sister?
A:
```
```
When I was 6 my sister was half my age, so she was 3. Now I am 70, so she is 70 - 3 = 67. The answer is 67.
```

* Generated Knowledge Prompting : https://www.promptingguide.ai/techniques/knowledge
    * ability to incorporate knowledge or information to help the model make more accurate predictions.
    * model also be used to generate knowledge before making a prediction, generate knowledge to be used as part of the prompt

* Prompt Chaining: https://www.promptingguide.ai/techniques/prompt_chaining
    * a task is split into subtasks with the idea to create a chain of prompt operations.

* Tree of Thoughts (ToT): https://www.promptingguide.ai/techniques/tot
    *  generalizes over chain-of-thought prompting and encourages exploration over thoughts that serve as intermediate steps for general problem solving with language models.

```
Imagine three different experts are answering this question. All experts will write down 1 step of their thinking, then share it with the group. Then all experts will go on to the next step, etc. If any expert realises they're wrong at any point then they leave. The question is...

Simulate three brilliant, logical experts collaboratively answering a question. Each one verbosely explains their thought process in real-time, considering the prior explanations of others and openly acknowledging mistakes. At each step, whenever possible, each expert refines and builds upon the thoughts of others, acknowledging their contributions. They continue until there is a definitive answer to the question. For clarity, your entire response should be in a markdown table. The question is...

Identify and behave as three different experts that are appropriate to answering this question.
All experts will write down the step and their thinking about the step, then share it with the group.
Then, all experts will go on to the next step, etc.
At each step all experts will score their peers response between 1 and 5, 1 meaning it is highly unlikely, and 5 meaning it is highly likely.
If any expert is judged to be wrong at any point then they leave.
After all experts have provided their analysis, you then analyze all 3 analyses and provide either the consensus solution or your best guess solution.
The question is...
```

* PAL (Program-Aided Language Models): https://www.promptingguide.ai/techniques/pal
    * Coined, program-aided language models (PAL), it differs from chain-of-thought prompting in that instead of using free-form text to obtain solution it offloads the solution step to a programmatic runtime such as a Python interpreter.

Large Language Models are Zero-Shot Reasoners: https://arxiv.org/abs/2205.11916

https://github.com/gpt-engineer-org/gpt-engineer/blob/main/gpt_engineer/preprompts/file_format

https://towardsdatascience.com/how-to-write-expert-prompts-for-chatgpt-gpt-4-and-other-language-models-23133dc85550#5e4e

https://gptstore.ai/plugins