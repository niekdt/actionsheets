# actionsheets

**Actionsheets** is an open-source (hobby) project with a different take on cheatsheets. 
Standard cheatsheets are great for getting started, but don't get into the details for advanced or complex use cases. 
This is where actionsheets come in.

This Python package provides a large collection of code snippets, and can render them in the form of _actionsheets_. Actionsheets are grouped look-up tables by action/intended outcome, and a code snippet to achieve it.
The package is intended for (new) developers to quickly look-up how to perform common actions for the given topic, but also contains some more advanced actions.

The package can print actionsheets in the console with coloring and syntax highlighting, but ideally, the package is used by other (better) front-end implementations. See the [streamlit dashboard](https://github.com/niekdt/actionsheets-streamlit) implementation, for example.

## How do actionsheets differ from cheatsheets?
- Actionsheets are expressed in terms of a desired *action* or result, and the code snippet(s) to achieve it.
  - This is a more natural way to look up code snippets. Especially useful for beginners.
- Actions may be complex or comprise multiple steps.
  - Actions are not limited to the direct functionality provided by the package API. 
  - Cheatsheets typically lack more advanced compound use cases.
- Code snippets are data; enabling dynamic generation of sheets depending on user queries
  - Sheets can therefore be more feature-complete, as they do not need fit on a single page.
    
This way of organizing sheets is especially useful for packages or functions with powerful versatile functionality, where merely listing the API does not cover the full capabilities. 

## Contributing
Actionsheets are defined using [TOML](https://toml.io/) files. 
This makes it very easy to define a hierarchy of code snippets in a readable way.

Defining a code snippet belonging to the _Create_ section of the respective actionsheet file is as simple as:
```toml
[create.list]
what = "Define a list"
code = "x = ['apple', 'pear', 'banana']"
details = "You can define as many items as you like"
```

For submitting code snippets or complete actionsheets, submit a PR to [actionsheets on Github](https://github.com/niekdt/actionsheets).

## Motivation
My motivation for building this curated database of code snippet is out of frustration of the worsening state of the internet in quickly finding short answers to straightforward queries.

- Many website have the code snippet(s) buried between tons of irrelevant text just for SEO optimization.
- The quality of (accepted) answers on Stackoverflow is severely lacking for some programming languages:
  - Answers are out of date
  - Answers are overly complicated, inefficient, or nonfunctional (contributions by beginners)
  - For the future, this also means that the answers by any LLM are going to have the same issues. 
- The answer on the site was for a different question
- The answer on the site was for a more narrow question
- With the increasing usage of LLMs, the problem of bloated low-quality answer results will only get worse.
     
