Science of Computer Programming

------------------------------

# Reviewer #1

## Summary

The report presents PANTHER, a framework for testing and formally verifying properties for distributed network protocols. What makes PANTHER unique is that it allows for more control over time-based factors in a network (e.g. latency), enabling the testing and verification of time-dependent properties, and provides a framework for verifying and testing customisable protocols of varying sizes.

## Points on the report

Some aspects of the paper were confusing. It feels like the authors tried to put too much into a small page limit. E.g., the diagram on page 5 is very large and not well explained - I felt like it did not contribute to my understanding of the tool. I only understood better what the tool is doing after having a look at the FORTE paper cited. I believe that this should not be a requirement. The 6 pages should be understandable as a standalone document. As suggestions, I would recommend to the authors to remove the contents of pages 5-6, and could instead give further insight into what has been achieved with the tool (examples/case studies/reproducible results - would pick one of these and give more detail, let the reader understand by example).

Having a section titled "Illustrative example", which does not describe any example at all, seems pointless. If you are not going to use space on an example, just add a sentence in the intro saying, "Examples can be found in our online documentation"; then you can make better use of the space. That being said, I believe going through an example is a very valid use of space.

The abstract says that "the framework enables a stateful fuzzer plugin", but this is later mentioned to be future work. Which one is correct?

Some sentences were unclear, please give the report a proofread.

Overall, the paper gave me a vague idea of what the tool can achieve. It does not talk about what *has* been achieved with the tool, what research was conducted using this tool, what novel results have come out of it, or any results that could be reproduced by running the tool.

## Points on the tool

### Installation

The local installation guide did not work for me. I got this error: ERROR: panther_net-*.whl is not a valid wheel filename.

The pip installation worked fine.

### Quick start

I feel like the quick start could be improved. Firstly, using this tool for the first time, I do not know what to make of the input file or how to interpret the output, and the quick start leaves me more confused. What extension should the sample configuration have? What is the config file doing? What experiment are we setting up in the quick start? Should the experiment terminate? What kind of output should I get so I know that it executed correctly?

### Suggestions

I encourage the authors to expand on the quick start guide. Let the user know what they are setting up and what outputs they should be expecting. If you don't want to explain all the config file at this point that's fine, but let the user know that you will explain it later.

### Minor

The command `panther --experiment-config experiment-config/experiment_config.yaml;` runs the experiment defined in experiment-config, which is different to the one given in the quick start guide.

--------

The next few sections describe what is included in the project, but I still don't know how to use them.

--------

### Documentation

- The main GitHub readme links to the documentation page elniak.github.io/PANTHER, which yields a 404 error for me. Luckily, I did find the actual link, which is <https://elniak.github.io/PANTHER/home.html>.

### Experiment Guide

- The path to the sample config file in 'setting up an experiment' is incorrect. There is no 'config' folder.
- The `panther build-docker-images` command is undefined.
- The `panther validate-config --config config/experiment_config.yaml` is incorrect. From the help command, I deduced that the command should instead be `panther --validate-config --experiment-config experiment-config/experiment_config.yaml`
- The command for running experiments is also incorrect.

The interpreting results section is not helpful. I encourage the authors to provide info on how to understand the output files.

------

The documentation is not helping me to understand how to use the tool. It seems to be riddled with inconsistencies, which is only making it more difficult. I would be happy to further review the 'Development' section of the documentation once the authors make a pass through the docs, correct the inconsistencies and make it accessible for anyone who's not used the tool before. As it stands, after reading the tool report, the main readme, and following through multiple pages of the documentation, I still do not know how to use the tool or understand any of its outputs.

# Reviewer #2

Thank you for submitting "PANTHER: Pluginizable Testing Environment for Network Protocols". Your work presents a significant contribution to the field of network protocol testing and formal verification.

I recommend accepting your paper after the revision.

------

For the revision, I would like you to provide:

- a detailed performance evaluation section, including benchmarks and comparisons to existing frameworks.
- additional case studies demonstrating the framework's applicability to different protocols and real-world scenarios would strengthen the submission.

Reviewers' comments:
